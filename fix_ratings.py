import sqlite3
import pandas as pd

def debug_ratings_table():
    """Ratings tablosunu detaylı incele"""
    
    conn = sqlite3.connect('movielens_100k.db')
    
    print("🔍 RATINGS TABLOSU DEBUG")
    print("=" * 50)
    
    # 1. Tablo yapısını incele
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(ratings)")
    columns = cursor.fetchall()
    
    print("📋 Ratings tablo yapısı:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")
    
    # 2. Ham veriyi incele
    cursor.execute("SELECT * FROM ratings LIMIT 5")
    raw_data = cursor.fetchall()
    
    print("\n📋 Ham ratings verisi:")
    for i, row in enumerate(raw_data):
        print(f"Row {i}: {row}")
    
    # 3. Farklı okuma yöntemleri dene
    print("\n🔧 Farklı okuma yöntemleri:")
    
    # Yöntem 1: Hex değerleri
    try:
        cursor.execute("SELECT hex(user_id), hex(movie_id), hex(rating) FROM ratings LIMIT 5")
        hex_data = cursor.fetchall()
        print("Hex values:")
        for row in hex_data:
            print(f"  {row}")
    except Exception as e:
        print(f"Hex okuma hatası: {e}")
    
    # Yöntem 2: Blob olarak oku
    try:
        cursor.execute("SELECT length(user_id), length(movie_id), length(rating) FROM ratings LIMIT 5")
        length_data = cursor.fetchall()
        print("Data lengths:")
        for row in length_data:
            print(f"  {row}")
    except Exception as e:
        print(f"Length okuma hatası: {e}")
    
    conn.close()

if __name__ == "__main__":
    debug_ratings_table()