import sqlite3
import pandas as pd
import numpy as np

def fix_and_analyze_data():
    """Verileri düzelt ve analiz et"""
    
    conn = sqlite3.connect('movielens_100k.db')
    
    print("🔧 VERİ TEMİZLEME VE ANALİZ")
    print("=" * 50)
    
    # 1. Ratings verilerini düzgün oku
    try:
        # Farklı yöntemlerle dene
        ratings_df = pd.read_sql("""
            SELECT 
                CAST(user_id AS INTEGER) as user_id,
                CAST(movie_id AS INTEGER) as movie_id, 
                CAST(rating AS REAL) as rating
            FROM ratings 
            LIMIT 10
        """, conn)
        
        print("✅ Ratings verileri düzeltildi:")
        print(ratings_df)
        
    except Exception as e:
        print(f"❌ Ratings okuma hatası: {e}")
        
        # Alternatif yöntem
        ratings_df = pd.read_sql("SELECT * FROM ratings LIMIT 10", conn)
        print("📋 Ham ratings verisi:")
        print(ratings_df.dtypes)
    
    # 2. Movies verilerini kontrol et
    movies_df = pd.read_sql("""
        SELECT id, title, genres 
        FROM movies 
        WHERE genres IS NOT NULL 
        LIMIT 10
    """, conn)
    
    print("\n✅ Movies verileri:")
    print(movies_df)
    
    # 3. Genre analizi
    genre_analysis = pd.read_sql("""
        SELECT genres, COUNT(*) as count 
        FROM movies 
        WHERE genres IS NOT NULL 
        GROUP BY genres 
        ORDER BY count DESC 
        LIMIT 10
    """, conn)
    
    print("\n📊 En popüler genre kombinasyonları:")
    print(genre_analysis)
    
    conn.close()
    
    return True

if __name__ == "__main__":
    fix_and_analyze_data()