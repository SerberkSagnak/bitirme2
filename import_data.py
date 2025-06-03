import pandas as pd
import json
from sqlalchemy.orm import Session
from database_fixed import engine, Movie, SessionLocal
import re

def extract_genres_from_dataset():
    """MovieLens verilerinden genre bilgilerini çıkar"""
    movies = pd.read_csv('ml-100k/u.item', sep='|', encoding='latin1',
                        names=['movie_id', 'title', 'release_date', 'video_release_date',
                               'imdb_url'] + [f'genre_{i}' for i in range(19)])
    
    # Genre columnları
    genre_cols = [f'genre_{i}' for i in range(19)]
    genre_names = [
        'unknown', 'Action', 'Adventure', 'Animation', 'Children', 'Comedy', 
        'Crime', 'Documentary', 'Drama', 'Fantasy', 'Film-Noir', 'Horror', 
        'Musical', 'Mystery', 'Romance', 'Sci-Fi', 'Thriller', 'War', 'Western'
    ]
    
    return movies, genre_cols, genre_names

def import_movies_to_db():
    """Filmleri database'e import et"""
    print("🎬 Filmler database'e import ediliyor...")
    
    movies_df, genre_cols, genre_names = extract_genres_from_dataset()
    
    db = SessionLocal()
    
    try:
        for _, row in movies_df.iterrows():
            # Bu filmin genre'larını bul
            movie_genres = []
            for i, genre_col in enumerate(genre_cols):
                if row[genre_col] == 1:
                    movie_genres.append(genre_names[i])
            
            # Movie objesi oluştur
            movie = Movie(
                movie_id=row['movie_id'],
                title=row['title'],
                release_date=row['release_date'],
                imdb_url=row['imdb_url'],
                genres=json.dumps(movie_genres),  # JSON string olarak kaydet
                avg_rating=0.0,
                rating_count=0,
                popularity_score=0.0
            )
            
            db.add(movie)
        
        db.commit()
        print(f"✅ {len(movies_df)} film başarıyla import edildi!")
        
    except Exception as e:
        print(f"❌ Hata: {e}")
        db.rollback()
    finally:
        db.close()

def update_movie_stats():
    """Mevcut rating verilerinden film istatistiklerini güncelle"""
    print("📊 Film istatistikleri hesaplanıyor...")
    
    # Mevcut rating matrisini yükle
    user_movie_matrix = pd.read_pickle('user_movie_matrix.pkl')
    
    db = SessionLocal()
    
    try:
        for movie_id in user_movie_matrix.columns:
            ratings = user_movie_matrix[movie_id]
            rated_users = ratings[ratings > 0]
            
            if len(rated_users) > 0:
                avg_rating = rated_users.mean()
                rating_count = len(rated_users)
                popularity_score = avg_rating * 0.6 + (rating_count/100) * 0.4
                
                # Database'deki movie'yi bul ve güncelle
                movie = db.query(Movie).filter(Movie.movie_id == movie_id).first()
                if movie:
                    movie.avg_rating = round(avg_rating, 2)
                    movie.rating_count = rating_count
                    movie.popularity_score = round(popularity_score, 2)
        
        db.commit()
        print("✅ Film istatistikleri güncellendi!")
        
    except Exception as e:
        print(f"❌ Hata: {e}")
        db.rollback()
    finally:
        db.close()

def show_sample_movies():
    """Database'den örnek filmleri göster"""
    db = SessionLocal()
    
    try:
        movies = db.query(Movie).order_by(Movie.popularity_score.desc()).limit(10)
        
        print("\n🎬 Database'deki En Popüler 10 Film:")
        print("-" * 60)
        for movie in movies:
            genres = json.loads(movie.genres) if movie.genres else []
            print(f"🎯 {movie.title}")
            print(f"   📅 {movie.release_date} | ⭐ {movie.avg_rating} | 👥 {movie.rating_count}")
            print(f"   🎭 {', '.join(genres)}")
            print()
    
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Data import işlemi başlıyor...\n")
    
    # 1. Filmleri import et
    import_movies_to_db()
    
    # 2. İstatistikleri güncelle  
    update_movie_stats()
    
    # 3. Örnek filmleri göster
    show_sample_movies()
    
    print("\n✅ Data import tamamlandı!")