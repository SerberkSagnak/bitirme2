import os
import sqlite3

print("🔍 VERİTABANI DOSYALARI ARANIYOR...")
print("="*50)

# Mevcut dizindeki .db dosyalarını bul
db_files = [f for f in os.listdir('.') if f.endswith('.db')]

print(f"📁 Bulunan .db dosyaları: {db_files}")

for db_file in db_files:
    print(f"\n🔍 {db_file} kontrol ediliyor...")
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Tabloları listele
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print(f"  📋 Tablolar: {[table[0] for table in tables]}")
        
        # Movies tablosu varsa kayıt sayısını göster
        if ('movies',) in tables:
            cursor.execute("SELECT COUNT(*) FROM movies")
            count = cursor.fetchone()[0]
            print(f"  🎬 Movies tablosunda {count} kayıt var")
            
            # İlk 3 filmi göster
            cursor.execute("SELECT id, title, avg_rating, rating_count FROM movies LIMIT 3")
            movies = cursor.fetchall()
            for movie in movies:
                print(f"    - {movie[1]}: {movie[2]} ⭐ ({movie[3]} oy)")
        
        conn.close()
        
    except Exception as e:
        print(f"  ❌ Hata: {e}")

print("\n" + "="*50)