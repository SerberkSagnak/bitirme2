import sqlite3
import random
import os

# Veritabanı yolları
DB_PATHS = ['movielens_100k.db', 'movie_recommendation.db']

def add_imdb_scores():
    for db_path in DB_PATHS:
        if not os.path.exists(db_path):
            continue
            
        print(f"🔄 {db_path} güncelleniyor...")
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 1. Sütun var mı kontrol et, yoksa ekle
            try:
                cursor.execute("ALTER TABLE movies ADD COLUMN imdb_score FLOAT")
                print("   ✅ 'imdb_score' sütunu eklendi.")
            except sqlite3.OperationalError:
                print("   ℹ️ 'imdb_score' sütunu zaten var.")

            # 2. Filmleri çek (id, avg_rating)
            movies = cursor.execute("SELECT id, avg_rating, title FROM movies").fetchall()
            
            updated_count = 0
            for movie in movies:
                movie_id = movie[0]
                avg_rating = movie[1] if movie[1] else 2.5 # Default orta değer
                
                # 3. Mantıklı IMDb Puanı Simülasyonu
                # MovieLens (0-5) -> IMDb (0-10)
                # Biraz varyasyon ekle (-0.5 ile +0.8 arası)
                # İyi filmlerin IMDb puanı genelde ortalamadan bir tık yüksek olur
                base_score = avg_rating * 1.9 
                variance = random.uniform(0.2, 1.2)
                
                imdb_score = base_score + variance
                
                # Sınırları koru (Max 9.9, Min 1.5)
                if imdb_score > 9.9: imdb_score = 9.9
                if imdb_score < 1.5: imdb_score = 1.5
                
                # Tek haneli float yap (örn: 8.4)
                imdb_score = round(imdb_score, 1)
                
                cursor.execute("UPDATE movies SET imdb_score = ? WHERE id = ?", (imdb_score, movie_id))
                updated_count += 1
            
            conn.commit()
            print(f"   ✅ {updated_count} filme IMDb puanı atandı.")
            
            # Örnek göster
            examples = cursor.execute("SELECT title, avg_rating, imdb_score FROM movies ORDER BY imdb_score DESC LIMIT 5").fetchall()
            print("   🏆 En yüksek puanlı örnekler:")
            for ex in examples:
                print(f"      - {ex[0]}: Site({ex[1]}) -> IMDb({ex[2]})")
                
            conn.close()
            
        except Exception as e:
            print(f"   ❌ Hata: {e}")

if __name__ == "__main__":
    add_imdb_scores()
