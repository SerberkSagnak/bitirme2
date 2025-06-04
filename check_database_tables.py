import sqlite3
import pandas as pd

def inspect_database():
    """Database'i detaylı incele"""
    print("🔍 DATABASE INSPECTION")
    print("="*50)
    
    conn = sqlite3.connect('movie_recommendation.db')
    cursor = conn.cursor()
    
    # 1. Tüm tabloları listele
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    print("📊 ALL TABLES:")
    for i, (table_name,) in enumerate(tables, 1):
        print(f"  {i}. {table_name}")
    
    # 2. Her tablo için detay
    for table_name, in tables:
        print(f"\n🏷️ TABLE: {table_name}")
        print("-" * 30)
        
        # Kolon bilgileri
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        print("📋 Columns:")
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
        
        # Kayıt sayısı
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"📊 Records: {count:,}")
        
        # İlk 3 kayıt
        if count > 0:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
            sample_data = cursor.fetchall()
            print("👀 Sample data:")
            for row in sample_data:
                print(f"  {row}")
    
    conn.close()

def find_ratings_table():
    """Ratings verilerini içeren tabloyu bul"""
    print("\n" + "="*50)
    print("🎯 FINDING RATINGS DATA")
    print("="*50)
    
    conn = sqlite3.connect('movie_recommendation.db')
    cursor = conn.cursor()
    
    # Tüm tabloları kontrol et
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cursor.fetchall()]
    
    ratings_candidates = []
    
    for table in tables:
        try:
            # Tablo yapısını kontrol et
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [col[1].lower() for col in cursor.fetchall()]
            
            # Rating benzeri kolonlar var mı?
            has_user = any('user' in col for col in columns)
            has_movie = any('movie' in col or 'item' in col for col in columns)
            has_rating = any('rating' in col or 'score' in col for col in columns)
            
            if has_user and has_movie and has_rating:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                ratings_candidates.append((table, count, columns))
                print(f"✅ Found candidate: {table} ({count:,} records)")
                print(f"   Columns: {columns}")
        
        except Exception as e:
            print(f"⚠️ Error checking {table}: {e}")
    
    conn.close()
    
    if ratings_candidates:
        # En çok kayıt olan tabloyu seç
        best_table = max(ratings_candidates, key=lambda x: x[1])
        print(f"\n🎯 BEST CANDIDATE: {best_table[0]} with {best_table[1]:,} records")
        return best_table[0], best_table[2]
    else:
        print("❌ No ratings table found!")
        return None, None

if __name__ == "__main__":
    inspect_database()
    table_name, columns = find_ratings_table()
    
    if table_name:
        print(f"\n🚀 USE THIS TABLE: {table_name}")
        print(f"📋 COLUMNS: {columns}")
    else:
        print("\n❌ Need to create ratings table or import data!")