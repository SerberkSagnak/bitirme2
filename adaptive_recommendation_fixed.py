import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# Verileri yükle
user_movie_matrix = pd.read_pickle('user_movie_matrix.pkl')
movies = pd.read_csv('ml-100k/u.item', sep='|', encoding='latin1',
                    names=['movie_id', 'title', 'release_date', 'video_release_date',
                           'imdb_url'] + [f'genre_{i}' for i in range(19)])

def get_popular_movies(n_movies=15):
    """En popüler ve kaliteli filmleri bul"""
    movie_stats = []
    for movie_id in user_movie_matrix.columns:
        ratings = user_movie_matrix[movie_id]
        rated_users = ratings[ratings > 0]
        
        if len(rated_users) >= 20:  # En az 20 kişi izlemiş
            avg_rating = rated_users.mean()
            popularity = len(rated_users) 
            score = avg_rating * 0.6 + (popularity/100) * 0.4
            movie_stats.append((movie_id, score, avg_rating, popularity))
    
    top_movies = sorted(movie_stats, key=lambda x: x[1], reverse=True)
    return top_movies[:n_movies]

class AdaptiveRecommendationSystem:
    def __init__(self):
        self.user_movie_matrix = user_movie_matrix
        self.movies = movies
        
    def recommend_for_new_user(self, user_ratings, n_recommendations=10):
        rating_count = len([r for r in user_ratings.values() if r > 0])
        print(f"👤 Kullanıcı {rating_count} film puanlamış")
        
        if rating_count < 5:
            print("📊 AŞAMA 1: Popüler filmler öneriliyor")
            return self._recommend_popular(user_ratings, n_recommendations)
        else:
            print("📊 AŞAMA 2+: Gelişmiş öneriler (sonraki adımda)")
            return self._recommend_popular(user_ratings, n_recommendations)
    
    def _recommend_popular(self, user_ratings, n_recommendations):
        popular_movies = get_popular_movies(50)
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

# Test
recommender = AdaptiveRecommendationSystem()

test_user_ratings = {
    1: 5,    # Toy Story'ye 5 puan
    50: 4,   # Star Wars'a 4 puan
}

print("🧪 TEST: Sadece 2 film puanlanmış kullanıcı")
recommendations = recommender.recommend_for_new_user(test_user_ratings, 5)

print(f"\n🎬 ÖNERİLER:")
for i, rec in enumerate(recommendations, 1):
    print(f"{i}. {rec['title']} (Skor: {rec['score']:.2f})")