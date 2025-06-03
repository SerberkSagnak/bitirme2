import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import json
from typing import List, Dict

class SimpleMLRecommender:
    def __init__(self):
        self.user_item_matrix = None
        self.item_features = None
        self.is_trained = False
        
    def prepare_data(self, ratings_data: List[Dict], movies_data: List[Dict]):
        """Veriyi hazırla"""
        # Ratings DataFrame
        ratings_df = pd.DataFrame(ratings_data)
        
        # User-Item Matrix oluştur
        self.user_item_matrix = ratings_df.pivot(
            index='user_id', 
            columns='movie_id', 
            values='rating'
        ).fillna(0)
        
        # Movies DataFrame 
        movies_df = pd.DataFrame(movies_data)
        
        # Film özelliklerini hazırla (genre-based)
        genre_features = []
        for _, movie in movies_df.iterrows():
            if movie['genres']:
                try:
                    genres = json.loads(movie['genres']) if isinstance(movie['genres'], str) else movie['genres']
                    genre_text = ' '.join(genres) if genres else ''
                except:
                    genre_text = ''
            else:
                genre_text = ''
            genre_features.append(genre_text)
        
        # TF-IDF ile genre features
        if genre_features and any(genre_features):
            tfidf = TfidfVectorizer()
            self.item_features = tfidf.fit_transform(genre_features)
        else:
            self.item_features = None
            
        self.movies_df = movies_df
        self.is_trained = True
        
        print(f"✅ ML Recommender hazırlandı!")
        print(f"📊 Users: {len(self.user_item_matrix)}")
        print(f"📊 Movies: {len(movies_df)}")
        print(f"📊 Ratings: {len(ratings_data)}")
        
    def get_user_recommendations(self, user_id: int, n_recommendations: int = 10) -> List[Dict]:
        """Kullanıcı için öneriler"""
        if not self.is_trained:
            return []
            
        try:
            # User-based collaborative filtering
            if user_id in self.user_item_matrix.index:
                user_ratings = self.user_item_matrix.loc[user_id]
                
                # Benzer kullanıcıları bul
                user_similarities = cosine_similarity([user_ratings], self.user_item_matrix)[0]
                similar_users_idx = np.argsort(user_similarities)[::-1][1:6]  # Top 5 benzer user
                
                # Önerileri hesapla
                recommendations = {}
                for similar_user_idx in similar_users_idx:
                    similar_user_id = self.user_item_matrix.index[similar_user_idx]
                    similar_user_ratings = self.user_item_matrix.loc[similar_user_id]
                    
                    for movie_id, rating in similar_user_ratings.items():
                        if rating > 0 and user_ratings[movie_id] == 0:  # Kullanıcı henüz izlememiş
                            if movie_id not in recommendations:
                                recommendations[movie_id] = []
                            recommendations[movie_id].append(rating * user_similarities[similar_user_idx])
                
                # Ortalama skorları hesapla
                movie_scores = []
                for movie_id, scores in recommendations.items():
                    avg_score = np.mean(scores)
                    movie_scores.append({
                        'movie_id': movie_id,
                        'predicted_rating': avg_score,
                        'ml_confidence': min(len(scores) / 5.0, 1.0)  # Normalize confidence
                    })
                
                # Skora göre sırala
                movie_scores.sort(key=lambda x: x['predicted_rating'], reverse=True)
                return movie_scores[:n_recommendations]
            
            else:
                # Yeni kullanıcı için popüler filmleri öner
                return self._get_popular_movies(n_recommendations)
                
        except Exception as e:
            print(f"❌ ML Recommendation error: {e}")
            return []
    
    def _get_popular_movies(self, n_recommendations: int) -> List[Dict]:
        """Popüler filmler (fallback)"""
        if not self.is_trained:
            return []
            
        # En çok puanlanan filmler
        movie_popularity = self.user_item_matrix.sum(axis=0).sort_values(ascending=False)
        popular_movies = []
        
        for movie_id, total_rating in movie_popularity.head(n_recommendations).items():
            popular_movies.append({
                'movie_id': movie_id,
                'predicted_rating': 4.0,  # Default prediction
                'ml_confidence': 0.5
            })
        
        return popular_movies
    
    def predict_rating(self, user_id: int, movie_id: int) -> float:
        """Tek film için puan tahmini"""
        if not self.is_trained or user_id not in self.user_item_matrix.index:
            return 3.5  # Default
            
        try:
            user_ratings = self.user_item_matrix.loc[user_id]
            
            # Benzer kullanıcıların bu filme verdiği puanları al
            user_similarities = cosine_similarity([user_ratings], self.user_item_matrix)[0]
            similar_ratings = []
            
            for i, similarity in enumerate(user_similarities):
                if similarity > 0.1:  # Minimum similarity threshold
                    other_user_id = self.user_item_matrix.index[i]
                    other_rating = self.user_item_matrix.loc[other_user_id, movie_id]
                    if other_rating > 0:
                        similar_ratings.append(other_rating * similarity)
            
            if similar_ratings:
                return np.mean(similar_ratings)
            else:
                return 3.5  # Default
                
        except:
            return 3.5

# Global instance
simple_ml = SimpleMLRecommender()