import sqlite3
import random
from datetime import datetime, timedelta
import json
import hashlib

# Veritabanı yolu
DB_PATH = 'movielens_100k.db'

# Kullanıcı Profilleri (Personas)
PROFILES = [
    {"name": "Aksiyon Sever", "genres": ["Action", "Adventure", "Thriller"], "min_imdb": 6.0},
    {"name": "Romantik Dramcı", "genres": ["Drama", "Romance"], "min_imdb": 7.0},
    {"name": "Kalite Avcısı (Snob)", "genres": [], "min_imdb": 8.5}, # Sadece yüksek puanlı izler
    {"name": "Bilim Kurgu Kurdu", "genres": ["Sci-Fi", "Fantasy"], "min_imdb": 5.5},
    {"name": "Korku Fanatiği", "genres": ["Horror", "Thriller", "Mystery"], "min_imdb": 5.0},
    {"name": "Her Şeyi İzleyen", "genres": [], "min_imdb": 4.0}, # Rastgele
    {"name": "Eski Toprak", "genres": ["Western", "War", "Film-Noir"], "min_imdb": 7.5}
]

def get_password_hash(password):
    return hashlib.sha256(password.encode()).hexdigest()

def populate_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("🚀 Akıllı Veri Doldurma Başlıyor...")
    
    # 1. Filmleri Çek
    movies = cursor.execute("SELECT id, title, genres, imdb_score FROM movies").fetchall()
    if not movies:
        print("❌ Film bulunamadı! Önce veritabanını oluşturun.")
        return

    # 2. 50 Yeni Kullanıcı Oluştur
    new_users = []
    for i in range(1, 51):
        profile = random.choice(PROFILES)
        username = f"user_{profile['name'].lower().replace(' ', '_')}_{i}"
        email = f"user{i}@example.com"
        password = get_password_hash("123456")
        
        # Favori türleri string olarak hazırla
        fav_genres = ",".join(profile['genres']) if profile['genres'] else "General"
        
        try:
            cursor.execute("""
                INSERT INTO app_users (username, email, hashed_password, age, gender, favorite_genres, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (username, email, password, random.randint(18, 60), random.choice(['M', 'F']), fav_genres, datetime.now()))
            
            user_id = cursor.lastrowid
            new_users.append({"id": user_id, "profile": profile})
        except sqlite3.IntegrityError:
            continue # Zaten varsa geç

    print(f"✅ {len(new_users)} yeni kullanıcı profili oluşturuldu.")

    # 3. Her Kullanıcı İçin Etkileşim Üret
    interaction_count = 0
    
    for user in new_users:
        profile = user["profile"]
        user_id = user["id"]
        
        # Bu kullanıcının puanlayacağı film sayısı (10 ile 50 arası)
        num_ratings = random.randint(10, 50)
        
        # Filmleri karıştır
        random.shuffle(movies)
        
        rated_count = 0
        for movie in movies:
            if rated_count >= num_ratings:
                break
                
            m_id, m_title, m_genres, m_imdb = movie
            m_imdb = m_imdb if m_imdb else 5.0
            m_genres_list = m_genres.split('|') if m_genres else []
            
            # Profil Uyumu Kontrolü
            is_genre_match = any(g in profile["genres"] for g in m_genres_list) if profile["genres"] else True
            is_quality_match = m_imdb >= profile["min_imdb"]
            
            rating = 0
            
            # Mantıklı Puanlama Algoritması
            if is_genre_match and is_quality_match:
                # Hem türü seviyor hem film kaliteli -> Yüksek Puan (4-5)
                rating = random.choice([4.0, 4.5, 5.0])
            elif is_genre_match and not is_quality_match:
                # Türü seviyor ama film kötü -> Orta Puan (2.5 - 3.5)
                rating = random.choice([2.5, 3.0, 3.5])
            elif not is_genre_match and is_quality_match:
                # Türü sevmiyor ama film çok kaliteli -> Orta/İyi Puan (3.0 - 4.0)
                rating = random.choice([3.0, 3.5, 4.0])
            else:
                # Ne türü seviyor ne film kaliteli -> Düşük Puan (0.5 - 2.0)
                rating = random.choice([0.5, 1.0, 1.5, 2.0])
            
            # Puanı Kaydet (Hem ratings hem user_interactions tablosuna)
            
            # A. Ratings Tablosu
            cursor.execute("""
                INSERT INTO ratings (user_id, movie_id, rating, timestamp, user_type)
                VALUES (?, ?, ?, ?, 'app')
            """, (user_id, m_id, rating, int(datetime.now().timestamp())))
            
            # B. User Interactions Tablosu
            extra_data = json.dumps({"rating": rating})
            cursor.execute("""
                INSERT INTO user_interactions (user_id, movie_id, interaction_type, extra_data, timestamp)
                VALUES (?, ?, 'rating', ?, ?)
            """, (user_id, m_id, extra_data, datetime.now()))
            
            # C. Favorilere Ekle (Eğer 4.5 üzeriyse %50 şansla)
            if rating >= 4.5 and random.random() > 0.5:
                cursor.execute("""
                    INSERT INTO user_interactions (user_id, movie_id, interaction_type, extra_data, timestamp)
                    VALUES (?, ?, 'favorite', '{}', ?)
                """, (user_id, m_id, datetime.now()))
            
            rated_count += 1
            interaction_count += 1
            
    conn.commit()
    conn.close()
    print(f"✅ Toplam {interaction_count} adet gerçekçi etkileşim (puan/favori) eklendi.")
    print("🎯 Model artık bu verilerle 'Tür + IMDb Puanı' ilişkilerini öğrenebilir.")

if __name__ == "__main__":
    populate_data()
