import sqlite3
import pandas as pd
import struct

def decode_binary_ratings():
    """Binary ratings verilerini çöz"""
    
    conn = sqlite3.connect('movielens_100k.db')
    
    print("🔓 BINARY VERİLERİ ÇÖZME")
    print("=" * 50)
    
    # Ham veriyi al
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, movie_id, rating FROM ratings LIMIT 10")
    raw_data = cursor.fetchall()
    
    decoded_data = []
    
    for row in raw_data:
        user_id_bytes = row[0]
        movie_id_bytes = row[1] 
        rating_bytes = row[2]
        
        try:
            # Little-endian 64-bit integer olarak çöz
            user_id = struct.unpack('<Q', user_id_bytes)[0]
            movie_id = struct.unpack('<Q', movie_id_bytes)[0]
            rating = struct.unpack('<Q', rating_bytes)[0]  # Rating da integer olarak gelmiş
            
            decoded_data.append({
                'user_id': user_id,
                'movie_id': movie_id, 
                'rating': rating
            })
            
        except Exception as e:
            print(f"Çözme hatası: {e}")
    
    # DataFrame'e çevir
    df = pd.DataFrame(decoded_data)
    
    print("✅ Çözülmüş ratings verileri:")
    print(df)
    
    print(f"\n📊 İstatistikler:")
    print(f"User ID aralığı: {df['user_id'].min()} - {df['user_id'].max()}")
    print(f"Movie ID aralığı: {df['movie_id'].min()} - {df['movie_id'].max()}")
    print(f"Rating aralığı: {df['rating'].min()} - {df['rating'].max()}")
    
    conn.close()
    
    return df

if __name__ == "__main__":
    decode_binary_ratings()