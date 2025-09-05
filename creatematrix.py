# create_matrix.py
import pandas as pd
import sqlite3
import pickle
import os

# --- GÜVENİLİR YOL TANIMLAMALARI ---
# Bu script'in bulunduğu dizini al
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Veritabanı dosyasının tam yolunu oluştur (script ile aynı dizinde olduğunu varsayıyoruz)
DB_PATH = os.path.join(BASE_DIR, 'movielens_100k.db')
# Çıktı olarak oluşturulacak .pkl dosyasının tam yolunu oluştur
OUTPUT_PATH = os.path.join(BASE_DIR, 'user_movie_matrix.pkl')

def create_and_save_matrix():
    """
    SQLite veritabanından rating'leri okur, bir kullanıcı-film matrisi oluşturur
    ve bu matrisi 'user_movie_matrix.pkl' olarak kaydeder.
    """
    print("🚀 Matris oluşturma işlemi başlıyor...")
    
    # 1. Veritabanı var mı diye kontrol et
    if not os.path.exists(DB_PATH):
        print(f"❌ HATA: Veritabanı dosyası bulunamadı: {DB_PATH}")
        print("   Lütfen veritabanı dosyasının bu script ile aynı dizinde olduğundan emin olun.")
        return # Fonksiyondan çık

    try:
        # 2. Veritabanından rating verilerini oku
        print(f"Veritabanına bağlanılıyor: {DB_PATH}")
        conn = sqlite3.connect(DB_PATH)
        
        # Diğer script'leriniz basit rating kullandığı için, biz de onu kullanalım.
        # Not: Veritabanınızda 'ratings' tablosu ve ilgili sütunlar olmalı.
        query = "SELECT user_id, movie_id, rating FROM ratings"
        ratings_df = pd.read_sql_query(query, conn)
        conn.close()
        
        print(f"✅ {len(ratings_df)} adet puanlama (rating) verisi okundu.")

        if ratings_df.empty:
            print("[!] Rating verisi bulunamadı. Veritabanındaki 'ratings' tablosu boş olabilir.")
            return

        # 3. Kullanıcı-Film matrisini oluştur (pivot table)
        print("Kullanıcı-Film matrisi (pivot table) oluşturuluyor...")
        user_movie_matrix = ratings_df.pivot_table(
            index='user_id',
            columns='movie_id',
            values='rating'
        ).fillna(0) # Puanlanmamış filmlere 0 değerini ata

        print(f"✅ Matris başarıyla oluşturuldu. Boyutu: {user_movie_matrix.shape}")

        # 4. Matrisi .pkl dosyası olarak kaydet
        print(f"Matris '{OUTPUT_PATH}' konumuna kaydediliyor...")
        with open(OUTPUT_PATH, 'wb') as f:
            pickle.dump(user_movie_matrix, f)

        print("\n🎉 Tamamlandı! 'user_movie_matrix.pkl' dosyası başarıyla oluşturuldu.")

    except sqlite3.OperationalError as e:
        print(f"❌ VERİTABANI HATASI: {e}")
        print("   'ratings' tablosu veya 'user_id', 'movie_id', 'rating' sütunları bulunamadı.")
    except Exception as e:
        print(f"❌ BEKLENMEDİK BİR HATA OLUŞTU: {e}")

if __name__ == "__main__":
    create_and_save_matrix()