import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# Önceki fonksiyonları import et
exec(open('cold_start_solution.py').read())

class AdaptiveRecommendationSystem:
    def __init__(self):
        self.user_movie_matrix = pd.read_pickle('user_movie_matrix.pkl')
        self.movies = pd.read_csv('ml-100k/u.item', sep='|', encoding='latin1',
                                 names=['movie_id', 'title', 'release_date', 'video_release_date',
                                        'imdb_url'] + [f'genre_{i}' for i in range(19)])
        self.user_similarity = None
        
    def get_user_rating_count(self, user_ratings):
        """Kullanıcının kaç film puanladığını say"""
        return len([r for r in user_ratings.values() if r > 0])
    
    def recommend_for_new_user(self, user_ratings, n_recommendations=10):
        """
        Yeni kullanıcı için kademeli öneri sistemi
        user_ratings: {movie_id: rating} dictionary
        """
        rating_count = len([r for r in user_ratings.values() if r > 0])
        
        print(f"👤 Kullanıcı {rating_count} film puanlamış")
        
        if rating_count < 5:
            # AŞAMA 1: Popüler filmlerden öner
            print("📊 AŞAMA 1: Popüler filmler öneriliyor")
            return self._recommend_popular(user_ratings, n_recommendations)
            
        elif rating_count < 15:
            # AŞAMA 2: Content-based + Popüler karışık
            print("📊 AŞAMA 2: İçerik bazlı + Popüler öneriler")
            return self._recommend_content_based(user_ratings, n_recommendations)
            
        else:
            # AŞAMA 3: Collaborative filtering
            print("📊 AŞAMA 3: Collaborative filtering")
            return self._recommend_collaborative(user_ratings, n_recommendations)
    
    def _recommend_popular(self, user_ratings, n_recommendations):
        """Popüler filmlerden, henüz izlemediği filmler öner"""
        # Calculate popular movies directly since get_popular_movies is not defined
        movie_ratings = self.user_movie_matrix.mean().sort_values(ascending=False)
        rating_counts = (self.user_movie_matrix > 0).sum()
        
        popular_movies = []
        for movie_id in movie_ratings.index:
            avg_rating = movie_ratings[movie_id]
            popularity = rating_counts[movie_id]
            score = avg_rating * popularity
            popular_movies.append((movie_id, score, avg_rating, popularity))
        
        popular_movies = sorted(popular_movies, key=lambda x: x[1], reverse=True)[:50]
        recommendations = []
        
        for movie_id, score, avg_rating, popularity in popular_movies:
            if movie_id not in user_ratings or user_ratings[movie_id] == 0:
                movie_title = self.movies[self.movies['movie_id'] == movie_id]['title'].values[0]
                recommendations.append({
                    'movie_id': movie_id,
                    'title': movie_title,
                    'score': score,
                    'method': 'popular'
                })
                if len(recommendations) >= n_recommendations:
                    break
        
        return recommendations
# Test edelim!
recommender = AdaptiveRecommendationSystem()

# Yeni kullanıcı simülasyonu - sadece 2 film puanlamış
test_user_ratings = {
    1: 5,    # Toy Story'ye 5 puan
    50: 4,   # Star Wars'a 4 puan
}

print("🧪 TEST: Sadece 2 film puanlanmış kullanıcı")
recommendations = recommender.recommend_for_new_user(test_user_ratings, 5)

print(f"\n🎬 ÖNERİLER:")
for i, rec in enumerate(recommendations, 1):
    print(f"{i}. {rec['title']} (Skor: {rec['score']:.2f})")