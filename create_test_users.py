"""
🎮 100 TEST KULLANICISI OLUŞTURUCU
Kolay test edilebilir kullanıcılar oluşturur
"""

import sqlite3
import random
import hashlib
from datetime import datetime, timedelta
import numpy as np

# Veritabanı bağlantısı
DB_FILE = 'movielens_100k.db'

def create_test_users():
    print("🎮 100 TEST KULLANICISI OLUŞTURULUYOR...")
    print("=" * 50)
    print("📋 Format: user1-user100, hepsi şifre: 123456")
    print("=" * 50)
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # Mevcut film ID'lerini al
        cursor.execute("SELECT id FROM movies")
        movie_ids = [row[0] for row in cursor.fetchall()]
        print(f"📊 {len(movie_ids)} film mevcut")
        
        # Şifre hash'i (hepsi için aynı)
        password_hash = hashlib.sha256("123456".encode()).hexdigest()
        
        # Kullanıcı grupları
        user_groups = [
            {"name": "Genç Erkek", "range": (1, 20), "age": (18, 25), "gender": "M", "genres": ["Action", "Comedy", "Adventure", "Sci-Fi"]},
            {"name": "Genç Kadın", "range": (21, 40), "age": (18, 25), "gender": "F", "genres": ["Romance", "Comedy", "Drama", "Musical"]},
            {"name": "Orta Yaş Erkek", "range": (41, 60), "age": (26, 45), "gender": "M", "genres": ["Thriller", "Crime", "Action", "War"]},
            {"name": "Orta Yaş Kadın", "range": (61, 80), "age": (26, 45), "gender": "F", "genres": ["Drama", "Romance", "Musical", "Mystery"]},
            {"name": "Yaşlı Karışık", "range": (81, 100), "age": (46, 65), "gender": None, "genres": ["Drama", "Documentary", "Film-Noir", "War"]}
        ]
        
        total_stats = {
            'users': 0, 'ratings': 0, 'favorites': 0, 'watchlist': 0
        }
        
        # Her grup için kullanıcı oluştur
        for group in user_groups:
            print(f"\n🎭 {group['name']} grubu oluşturuluyor...")
            
            start_id, end_id = group['range']
            
            for user_num in range(start_id, end_id + 1):
                # Kullanıcı profili
                username = f"user{user_num}"
                email = f"user{user_num}@test.com"
                age = random.randint(*group['age'])
                
                if group['gender']:
                    gender = group['gender']
                else:
                    gender = random.choice(['M', 'F'])
                
                # Favori türler (grup + random)
                base_genres = group['genres'].copy()
                extra_genres = random.sample(['Animation', 'Fantasy', 'Horror', 'Western'], 
                                           random.randint(0, 2))
                favorite_genres = ','.join(base_genres + extra_genres)
                
                # Tarihler
                days_ago = random.randint(30, 365)
                created_at = datetime.now() - timedelta(days=days_ago)
                last_active = created_at + timedelta(days=random.randint(0, days_ago))
                
                # Kullanıcıyı ekle
                cursor.execute("""
                    INSERT INTO app_users (username, email, hashed_password, age, gender, favorite_genres, created_at, last_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (username, email, password_hash, age, gender, favorite_genres,
                     created_at.isoformat(), last_active.isoformat()))
                
                user_id = cursor.lastrowid
                total_stats['users'] += 1
                
                # Bu kullanıcı için etkileşimler oluştur
                interactions = generate_user_interactions(age, gender, movie_ids, created_at)
                
                # Rating'leri ekle
                for rating_data in interactions['ratings']:
                    cursor.execute("""
                        INSERT INTO ratings (user_id, movie_id, rating, timestamp, user_type, created_at)
                        VALUES (?, ?, ?, ?, 'app', ?)
                    """, (user_id, rating_data['movie_id'], rating_data['rating'],
                         rating_data['timestamp'], rating_data['created_at']))
                    total_stats['ratings'] += 1
                
                # Favorileri ekle
                for fav_data in interactions['favorites']:
                    cursor.execute("""
                        INSERT INTO user_interactions (user_id, movie_id, interaction_type, timestamp)
                        VALUES (?, ?, 'favorite', ?)
                    """, (user_id, fav_data['movie_id'], fav_data['timestamp']))
                    total_stats['favorites'] += 1
                
                # Watchlist'i ekle
                for watch_data in interactions['watchlist']:
                    cursor.execute("""
                        INSERT INTO watchlist (user_id, movie_id, status, added_at, watched_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (user_id, watch_data['movie_id'], watch_data['status'],
                         watch_data['added_at'], watch_data['watched_at']))
                    total_stats['watchlist'] += 1
            
            print(f"✅ {group['name']}: user{start_id}-user{end_id} oluşturuldu")
        
        conn.commit()
        
        print(f"\n🎉 BAŞARIYLA TAMAMLANDI!")
        print(f"👥 Toplam Kullanıcı: {total_stats['users']}")
        print(f"⭐ Toplam Rating: {total_stats['ratings']}")
        print(f"❤️ Toplam Favori: {total_stats['favorites']}")
        print(f"📋 Toplam Watchlist: {total_stats['watchlist']}")
        
        print(f"\n🎮 TEST İÇİN:")
        print(f"   Username: user1, user2, ..., user100")
        print(f"   Password: 123456 (hepsi için aynı)")
        print(f"   Email: user1@test.com, user2@test.com, ...")
        
        print(f"\n🎯 ÖRNEK TEST KULLANICILARI:")
        print(f"   user5  → Genç erkek (aksiyon sever)")
        print(f"   user25 → Genç kadın (romantik sever)")
        print(f"   user45 → Orta yaş erkek (gerilim sever)")
        print(f"   user65 → Orta yaş kadın (drama sever)")
        print(f"   user85 → Yaşlı (klasik sever)")
        
    except Exception as e:
        print(f"❌ Hata: {e}")
        conn.rollback()
    
    finally:
        conn.close()

def generate_user_interactions(age, gender, movie_ids, created_at):
    """Kullanıcı etkileşimleri oluştur"""
    
    # Aktivite seviyesi
    if age < 30:
        rating_count = random.randint(15, 40)
    elif age < 50:
        rating_count = random.randint(10, 30)
    else:
        rating_count = random.randint(8, 20)
    
    # Random filmler seç
    selected_movies = random.sample(movie_ids, min(rating_count, len(movie_ids)))
    
    interactions = {'ratings': [], 'favorites': [], 'watchlist': []}
    
    for movie_id in selected_movies:
        # Rating (1-5, normal distribution)
        rating = max(1, min(5, round(np.random.normal(3.5, 0.8))))
        
        # Tarih
        days_after = random.randint(1, 300)
        rating_date = created_at + timedelta(days=days_after)
        
        interactions['ratings'].append({
            'movie_id': movie_id,
            'rating': rating,
            'timestamp': int(rating_date.timestamp()),
            'created_at': rating_date.isoformat()
        })
        
        # Favori (%20 ihtimal, yüksek puanlı filmler için daha fazla)
        fav_chance = 0.1 + (rating - 1) * 0.05
        if random.random() < fav_chance:
            interactions['favorites'].append({
                'movie_id': movie_id,
                'timestamp': rating_date.isoformat()
            })
        
        # Watchlist (%25 ihtimal)
        if random.random() < 0.25:
            status = random.choice(['watched', 'to_watch'])
            watched_at = rating_date.isoformat() if status == 'watched' else None
            
            interactions['watchlist'].append({
                'movie_id': movie_id,
                'status': status,
                'added_at': rating_date.isoformat(),
                'watched_at': watched_at
            })
    
    return interactions

if __name__ == "__main__":
    create_test_users()