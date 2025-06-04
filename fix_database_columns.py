import sqlite3
import pandas as pd
import numpy as np

def add_missing_columns():
    conn = sqlite3.connect('movie_recommendation.db')
    cursor = conn.cursor()
    
    try:
        # Popularity kolonu ekle
        print("📊 Adding popularity column...")
        cursor.execute("ALTER TABLE movies ADD COLUMN popularity INTEGER DEFAULT 0")
        
        # avg_rating kolonu ekle (eğer yoksa)
        print("⭐ Adding avg_rating column...")
        cursor.execute("ALTER TABLE movies ADD COLUMN avg_rating REAL DEFAULT 0.0")
        
        print("✅ Columns added successfully!")
        
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("ℹ️ Columns already exist")
        else:
            print(f"❌ Error: {e}")
    
    # Popularity ve avg_rating değerlerini hesapla
    print("🔄 Calculating popularity and avg_rating...")
    
    # Her film için rating sayısını popularity olarak kullan
    cursor.execute("""
        UPDATE movies 
        SET popularity = (
            SELECT COUNT(*) 
            FROM ratings 
            WHERE ratings.movie_id = movies.movie_id
        )
    """)
    
    # Her film için ortalama rating hesapla
    cursor.execute("""
        UPDATE movies 
        SET avg_rating = (
            SELECT COALESCE(AVG(rating), 0.0) 
            FROM ratings 
            WHERE ratings.movie_id = movies.movie_id
        )
    """)
    
    conn.commit()
    conn.close()
    
    print("✅ Database updated successfully!")

if __name__ == "__main__":
    add_missing_columns()