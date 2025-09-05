import sqlite3
import pandas as pd
import struct
import numpy as np

def prepare_movielens_data():
    """Model eğitimi için verileri hazırla"""
    
    conn = sqlite3.connect('movielens_100k.db')
    
    print("📊 MODEL EĞİTİMİ İÇİN VERİ HAZIRLAMA")
    print("=" * 50)
    
    # 1. Tüm ratings verilerini çöz
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, movie_id, rating FROM ratings")
    raw_data = cursor.fetchall()
    
    print(f"📋 Toplam {len(raw_data)} rating verisi işleniyor...")
    
    decoded_ratings = []
    
    for i, row in enumerate(raw_data):
        if i % 10000 == 0:
            print(f"  İşlenen: {i}/{len(raw_data)}")
        
        try:
            user_id = struct.unpack('<Q', row[0])[0]
            movie_id = struct.unpack('<Q', row[1])[0] 
            rating = struct.unpack('<Q', row[2])[0]
            
            decoded_ratings.append({
                'user_id': user_id,
                'movie_id': movie_id,
                'rating': rating
            })
            
        except Exception as e:
            continue
    
    # DataFrame'e çevir
    ratings_df = pd.DataFrame(decoded_ratings)
    
    print(f"\n✅ {len(ratings_df)} rating başarıyla çözüldü!")
    
    # 2. Temel istatistikler
    print(f"\n📊 VERİ İSTATİSTİKLERİ:")
    print(f"Benzersiz kullanıcı: {ratings_df['user_id'].nunique()}")
    print(f"Benzersiz film: {ratings_df['movie_id'].nunique()}")
    print(f"Rating dağılımı:")
    print(ratings_df['rating'].value_counts().sort_index())
    
    # 3. Sparsity hesapla
    n_users = ratings_df['user_id'].nunique()
    n_movies = ratings_df['movie_id'].nunique()
    n_ratings = len(ratings_df)
    sparsity = (1 - n_ratings / (n_users * n_movies)) * 100
    
    print(f"\n📊 Matrix Sparsity: {sparsity:.2f}%")
    
    # 4. Veriyi kaydet
    ratings_df.to_csv('cleaned_ratings.csv', index=False)
    print(f"\n💾 Temizlenmiş veriler 'cleaned_ratings.csv' dosyasına kaydedildi!")
    
    conn.close()
    
    return ratings_df

if __name__ == "__main__":
    prepare_movielens_data()