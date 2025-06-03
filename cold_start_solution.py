import pandas as pd
import numpy as np

# Verileri yükle
user_movie_matrix = pd.read_pickle('user_movie_matrix.pkl')
movies = pd.read_csv('ml-100k/u.item', sep='|', encoding='latin1',
                    names=['movie_id', 'title', 'release_date', 'video_release_date',
                           'imdb_url'] + [f'genre_{i}' for i in range(19)])

def get_popular_movies(n_movies=15):
    """En popüler ve kaliteli filmleri bul"""
    print("🔥 Popüler filmler hesaplanıyor...")
    
    movie_stats = []
    for movie_id in user_movie_matrix.columns:
        ratings = user_movie_matrix[movie_id]
        rated_users = ratings[ratings > 0]
        
        if len(rated_users) >= 20:  # En az 20 kişi izlemiş
            avg_rating = rated_users.mean()
            popularity = len(rated_users) 
            # Skor = %60 kalite + %40 popülerlik
            score = avg_rating * 0.6 + (popularity/100) * 0.4
            movie_stats.append((movie_id, score, avg_rating, popularity))
    
    # En yüksek skorluları döndür
    top_movies = sorted(movie_stats, key=lambda x: x[1], reverse=True)
    return top_movies[:n_movies]

def get_onboarding_movies():
    """Onboarding için farklı türlerden filmler seç"""
    popular = get_popular_movies(50)  # İlk 50'den seç
    
    # Film türlerini kontrol et ve çeşitlilik sağla
    selected_movies = []
    for movie_id, score, avg_rating, popularity in popular:
        if len(selected_movies) < 15:
            movie_title = movies[movies['movie_id'] == movie_id]['title'].values[0]
            selected_movies.append({
                'movie_id': movie_id,
                'title': movie_title,
                'avg_rating': round(avg_rating, 1),
                'popularity': popularity
            })
    
    return selected_movies

# Test edelim
print("🎬 ONBOARDING İÇİN SEÇİLEN FİLMLER:")
onboarding_movies = get_onboarding_movies()
for i, movie in enumerate(onboarding_movies, 1):
    print(f"{i:2d}. {movie['title']} (⭐{movie['avg_rating']}, 👥{movie['popularity']})")