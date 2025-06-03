import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD
from sqlalchemy.orm import Session
from database_fixed import User, Movie, Rating, SessionLocal
import json
from typing import List, Dict, Optional

class HybridRecommendationEngine:
    def __init__(self):
        self.user_movie_matrix = pd.read_pickle('user_movie_matrix.pkl')
        self.movies_df = None
        self.genre_similarity_matrix = None
        self.tfidf_matrix = None
        self.svd_model = None
        self.load_movies_data()
        self.setup_content_based()
        self.setup_collaborative_filtering()
    
    def load_movies_data(self):
        """Database'den movie verilerini yükle"""
        db = SessionLocal()
        try:
            movies = db.query(Movie).all()
            movies_data = []
            
            for movie in movies:
                genres = json.loads(movie.genres) if movie.genres else []
                movies_data.append({
                    'movie_id': movie.movie_id,
                    'title': movie.title,
                    'genres': genres,
                    'genres_str': ' '.join(genres),
                    'avg_rating': movie.avg_rating,
                    'rating_count': movie.rating_count,
                    'popularity_score': movie.popularity_score
                })
            
            self.movies_df = pd.DataFrame(movies_data)
            print(f"✅ {len(self.movies_df)} film verisi yüklendi")
            
        finally:
            db.close()
    
    def setup_content_based(self):
        """Content-based filtering için TF-IDF setup"""
        print("🔧 Content-based sistem kuruluyor...")
        
        # Genre'lara dayalı TF-IDF
        tfidf = TfidfVectorizer(stop_words='english')
        self.tfidf_matrix = tfidf.fit_transform(self.movies_df['genres_str'])
        
        # Genre benzerlik matrisi
        self.genre_similarity_matrix = cosine_similarity(self.tfidf_matrix)
        
        print("✅ Content-based sistem hazır!")
    
    def setup_collaborative_filtering(self):
        """Collaborative filtering için SVD setup"""
        print("🔧 Collaborative filtering sistem kuruluyor...")
        
        # SVD model
        self.svd_model = TruncatedSVD(n_components=50, random_state=42)
        
        # User-movie matrix'i SVD ile çarpanlarına ayır
        user_movie_filled = self.user_movie_matrix.fillna(0)
        self.user_factors = self.svd_model.fit_transform(user_movie_filled)
        self.movie_factors = self.svd_model.components_.T
        
        print("✅ Collaborative filtering sistem hazır!")
    
    def get_genre_based_recommendations(self, preferred_genres: List[str], 
                                      user_ratings: Dict[int, float] = None,
                                      n_recommendations: int = 10) -> List[Dict]:
        """Türe dayalı öneriler"""
        print(f"🎭 Türe dayalı öneriler: {preferred_genres}")
        
        # Tercih edilen türleri içeren filmleri bul
        genre_scores = []
        
        for idx, row in self.movies_df.iterrows():
            movie_genres = row['genres']
            
            # User'ın daha önce puanladığı filmler hariç
            if user_ratings and row['movie_id'] in user_ratings:
                continue
            
            # Genre match score hesapla
            genre_match_score = 0
            for genre in preferred_genres:
                if genre in movie_genres:
                    genre_match_score += 1
            
            if genre_match_score > 0:
                # Toplam skor: genre match + popularity + rating
                total_score = (
                    genre_match_score * 0.4 +  # Genre uyumu
                    (row['popularity_score'] / 10) * 0.3 +  # Popülerlik
                    row['avg_rating'] * 0.3  # Ortalama puan
                )
                
                genre_scores.append({
                    'movie_id': row['movie_id'],
                    'title': row['title'],
                    'genres': movie_genres,
                    'genre_match_score': genre_match_score,
                    'total_score': total_score,
                    'avg_rating': row['avg_rating'],
                    'popularity': row['rating_count']
                })
        
        # Skora göre sırala
        genre_scores.sort(key=lambda x: x['total_score'], reverse=True)
        
        return genre_scores[:n_recommendations]
    
    def get_content_based_recommendations(self, liked_movie_ids: List[int], 
                                        user_ratings: Dict[int, float] = None,
                                        n_recommendations: int = 10) -> List[Dict]:
        """Content-based öneriler (beğenilen filmlere benzer)"""
        print(f"📚 Content-based öneriler: {len(liked_movie_ids)} beğenilen film")
        
        if not liked_movie_ids:
            return []
        
        # Beğenilen filmlerin indices'ini bul
        liked_indices = []
        for movie_id in liked_movie_ids:
            try:
                idx = self.movies_df[self.movies_df['movie_id'] == movie_id].index[0]
                liked_indices.append(idx)
            except IndexError:
                continue
        
        if not liked_indices:
            return []
        
        # Bu filmlere benzer filmleri bul
        similarity_scores = []
        
        for i, movie_row in self.movies_df.iterrows():
            if user_ratings and movie_row['movie_id'] in user_ratings:
                continue
                
            # Beğenilen filmlerle ortalama benzerlik
            total_similarity = 0
            for liked_idx in liked_indices:
                similarity = self.genre_similarity_matrix[i][liked_idx]
                total_similarity += similarity
            
            avg_similarity = total_similarity / len(liked_indices)
            
            if avg_similarity > 0.1:  # Minimum benzerlik threshold
                total_score = (
                    avg_similarity * 0.5 +
                    (movie_row['popularity_score'] / 10) * 0.3 +
                    movie_row['avg_rating'] * 0.2
                )
                
                similarity_scores.append({
                    'movie_id': movie_row['movie_id'],
                    'title': movie_row['title'],
                    'genres': movie_row['genres'],
                    'similarity_score': avg_similarity,
                    'total_score': total_score,
                    'avg_rating': movie_row['avg_rating'],
                    'popularity': movie_row['rating_count']
                })
        
        similarity_scores.sort(key=lambda x: x['total_score'], reverse=True)
        return similarity_scores[:n_recommendations]
    
    def get_hybrid_recommendations(self, user_id: int, 
                                 preferred_genres: List[str] = None,
                                 n_recommendations: int = 10) -> Dict:
        """Hybrid öneriler (collaborative + content + genre)"""
        print(f"🔀 Hybrid öneriler kullanıcı {user_id} için")
        
        # Kullanıcının puanlamalarını al
        db = SessionLocal()
        try:
            user_ratings_db = db.query(Rating).filter(Rating.user_id == user_id).all()
            user_ratings = {}
            liked_movies = []  # 4+ puan alanlar
            
            for rating in user_ratings_db:
                movie = db.query(Movie).filter(Movie.id == rating.movie_id).first()
                if movie:
                    user_ratings[movie.movie_id] = rating.rating
                    if rating.rating >= 4.0:
                        liked_movies.append(movie.movie_id)
            
            print(f"👤 Kullanıcı {len(user_ratings)} film puanlamış, {len(liked_movies)} tanesini beğenmiş")
            
        finally:
            db.close()
        
        recommendations = {
            'genre_based': [],
            'content_based': [],
            'collaborative': [],
            'final_hybrid': []
        }
        
        # 1. Genre-based (eğer tercih belirtilmişse)
        if preferred_genres:
            recommendations['genre_based'] = self.get_genre_based_recommendations(
                preferred_genres, user_ratings, n_recommendations//2
            )
        
        # 2. Content-based (beğenilen filmlere benzer)
        if liked_movies:
            recommendations['content_based'] = self.get_content_based_recommendations(
                liked_movies, user_ratings, n_recommendations//2
            )
        
        # 3. Collaborative filtering (şimdilik popüler filmler)
        popular_unwatched = []
        for _, movie in self.movies_df.iterrows():
            if movie['movie_id'] not in user_ratings:
                popular_unwatched.append({
                    'movie_id': movie['movie_id'],
                    'title': movie['title'],
                    'genres': movie['genres'],
                    'score': movie['popularity_score'],
                    'avg_rating': movie['avg_rating'],
                    'popularity': movie['rating_count']
                })
        
        popular_unwatched.sort(key=lambda x: x['score'], reverse=True)
        recommendations['collaborative'] = popular_unwatched[:n_recommendations//3]
        
        # 4. Final Hybrid (tüm yöntemleri birleştir)
        all_recommendations = {}
        
        # Genre-based skorları ekle
        for rec in recommendations['genre_based']:
            movie_id = rec['movie_id']
            all_recommendations[movie_id] = all_recommendations.get(movie_id, 0) + rec['total_score'] * 0.4
        
        # Content-based skorları ekle  
        for rec in recommendations['content_based']:
            movie_id = rec['movie_id']
            all_recommendations[movie_id] = all_recommendations.get(movie_id, 0) + rec['total_score'] * 0.4
        
        # Collaborative skorları ekle
        for rec in recommendations['collaborative']:
            movie_id = rec['movie_id']
            all_recommendations[movie_id] = all_recommendations.get(movie_id, 0) + rec['score'] * 0.2
        
        # Final listesi oluştur
        final_list = []
        for movie_id, score in sorted(all_recommendations.items(), key=lambda x: x[1], reverse=True):
            movie_info = self.movies_df[self.movies_df['movie_id'] == movie_id].iloc[0]
            final_list.append({
                'movie_id': movie_id,
                'title': movie_info['title'],
                'genres': movie_info['genres'],
                'hybrid_score': round(score, 2),
                'avg_rating': movie_info['avg_rating'],
                'popularity': movie_info['rating_count']
            })
        
        recommendations['final_hybrid'] = final_list[:n_recommendations]
        
        return recommendations

# Test fonksiyonu
def test_advanced_recommender():
    """Gelişmiş öneri sistemini test et"""
    print("🧪 Gelişmiş öneri sistemi test ediliyor...\n")
    
    engine = HybridRecommendationEngine()
    
    # Test 1: Genre-based
    print("1️⃣ Genre-based test:")
    genre_recs = engine.get_genre_based_recommendations(['Action', 'Sci-Fi'], n_recommendations=5)
    for i, rec in enumerate(genre_recs[:3]):
        print(f"   {i+1}. {rec['title']} - {rec['genres']} (Skor: {rec['total_score']:.2f})")
    
    print("\n2️⃣ Content-based test:")
    # Star Wars ve Terminator benzeri filmler
    content_recs = engine.get_content_based_recommendations([1, 195], n_recommendations=5)
    for i, rec in enumerate(content_recs[:3]):
        print(f"   {i+1}. {rec['title']} - {rec['genres']} (Benzerlik: {rec['similarity_score']:.2f})")
    
    print("\n3️⃣ Hybrid test (test user için):")
    # Test user'ın ID'si 1 olsun
    hybrid_recs = engine.get_hybrid_recommendations(1, ['Action', 'Comedy'], n_recommendations=5)
    for i, rec in enumerate(hybrid_recs['final_hybrid'][:3]):
        print(f"   {i+1}. {rec['title']} - {rec['genres']} (Hybrid: {rec['hybrid_score']})")
    
    print("\n✅ Test tamamlandı!")

if __name__ == "__main__":
    test_advanced_recommender()