import sqlite3
import pandas as pd

def analyze_database():
    """Veritabanındaki verileri analiz et"""
    
    # Database bağlantısı
    conn = sqlite3.connect('movielens_100k.db')
    
    print("📊 VERİTABANI ANALİZİ")
    print("=" * 50)
    
    # 1. Movies tablosu
    movies_query = "SELECT COUNT(*) as count FROM movies"
    movies_count = pd.read_sql(movies_query, conn)
    print(f"🎬 Movies: {movies_count['count'].iloc[0]} adet")
    
    # 2. Ratings tablosu  
    ratings_query = "SELECT COUNT(*) as count FROM ratings"
    ratings_count = pd.read_sql(ratings_query, conn)
    print(f"⭐ Ratings: {ratings_count['count'].iloc[0]} adet")
    
    # 3. Sample ratings
    sample_ratings = pd.read_sql("SELECT * FROM ratings LIMIT 5", conn)
    print(f"\n📋 Sample Ratings:")
    print(sample_ratings)
    
    # 4. Sample movies
    sample_movies = pd.read_sql("SELECT * FROM movies LIMIT 5", conn)
    print(f"\n📋 Sample Movies:")
    print(sample_movies)
    
    conn.close()
    
    return {
        'movies_count': movies_count['count'].iloc[0],
        'ratings_count': ratings_count['count'].iloc[0]
    }

if __name__ == "__main__":
    analyze_database()