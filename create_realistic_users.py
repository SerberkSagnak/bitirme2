"""
Gerçekçi Kullanıcı ve Rating Sistemi Oluşturucu
100+ kullanıcı ile sağlam derin öğrenme modeli için
"""

import sqlite3
import random
import json
import numpy as np
from datetime import datetime, timedelta

class RealisticUserGenerator:
    def __init__(self):
        # Gerçekçi isim listeleri
        self.first_names = [
            'Ahmet', 'Mehmet', 'Ali', 'Fatma', 'Ayşe', 'Zeynep', 'Mustafa', 'Emre',
            'Seda', 'Elif', 'Burak', 'Cem', 'Deniz', 'Ege', 'Furkan', 'Gül',
            'Hakan', 'İrem', 'Kemal', 'Leyla', 'Murat', 'Nalan', 'Oğuz', 'Pınar',
            'Rıza', 'Selin', 'Tolga', 'Umut', 'Volkan', 'Yasemin', 'Zafer'
        ]
        
        # Gerçekçi film türü tercihleri (demographics based)
        self.genre_preferences = {
            'young_male': ['Action', 'Sci-Fi', 'Adventure', 'Fantasy', 'Thriller'],
            'young_female': ['Romance', 'Comedy', 'Drama', 'Musical', 'Fantasy'],
            'adult_male': ['Action', 'Crime', 'War', 'Western', 'Thriller'],
            'adult_female': ['Drama', 'Romance', 'Comedy', 'Mystery', 'Documentary'],
            'senior': ['Drama', 'Documentary', 'Musical', 'Comedy', 'Romance'],
            'cinephile': ['Drama', 'Film-Noir', 'Documentary', 'Foreign', 'Art'],
            'casual': ['Comedy', 'Action', 'Adventure', 'Romance', 'Animation']
        }
        
        # Meslek grupları
        self.occupations = [
            'student', 'engineer', 'teacher', 'doctor', 'lawyer', 'artist',
            'manager', 'worker', 'nurse', 'programmer', 'designer', 'analyst',
            'writer', 'musician', 'chef', 'accountant', 'researcher', 'consultant'
        ]

    def determine_user_profile(self, age, gender):
        """Yaş ve cinsiyete göre film tercihi profili belirle"""
        if age < 25:
            if gender == 'M':
                return 'young_male'
            else:
                return 'young_female'
        elif age < 45:
            if gender == 'M':
                return 'adult_male'
            else:
                return 'adult_female'
        else:
            return 'senior'

    def generate_realistic_users(self, n_users=100):
        """Gerçekçi kullanıcı profilleri oluştur"""
        users = []
        
        for i in range(n_users):
            name = random.choice(self.first_names)
            username = f"{name.lower()}_{i+1:03d}"
            
            # Gerçekçi demografik dağılım
            age = int(np.random.normal(35, 12))  # Normal distribution
            age = max(18, min(70, age))  # 18-70 yaş arası
            
            gender = random.choice(['M', 'F'])
            occupation = random.choice(self.occupations)
            
            # Profil belirle
            profile = self.determine_user_profile(age, gender)
            
            # %20 şans ile cinephile veya casual
            if random.random() < 0.1:
                profile = 'cinephile'
            elif random.random() < 0.2:
                profile = 'casual'
            
            preferred_genres = self.genre_preferences[profile]
            favorite_genres = ','.join(random.sample(preferred_genres, min(3, len(preferred_genres))))
            
            users.append({
                'username': username,
                'email': f"{username}@realistic.com",
                'age': age,
                'gender': gender,
                'occupation': occupation,
                'favorite_genres': favorite_genres,
                'profile': profile
            })
        
        return users

    def generate_realistic_ratings(self, user_profile, user_id, movies):
        """Kullanıcı profiline göre gerçekçi rating'ler oluştur"""
        ratings = []
        
        # Profil bazlı film sayısı
        if user_profile['profile'] == 'cinephile':
            n_movies = random.randint(40, 80)  # Film severler çok izler
        elif user_profile['profile'] == 'casual':
            n_movies = random.randint(10, 25)  # Casual izleyiciler az
        else:
            n_movies = random.randint(15, 40)  # Normal dağılım
        
        # Kullanıcının sevdiği türler
        preferred_genres = user_profile['favorite_genres'].split(',')
        
        # Filmler arasından seç
        selected_movies = random.sample(movies, min(n_movies, len(movies)))
        
        for movie in selected_movies:
            movie_id, title, genres = movie
            movie_genres = genres.split('|') if genres else []
            
            # Genre match hesapla
            genre_match = len(set(preferred_genres) & set(movie_genres)) > 0
            
            # Rating probabilistic olarak belirle
            if genre_match:
                # Sevdiği türse yüksek puan verme olasılığı
                if random.random() < 0.7:  # %70 şans ile 4-5 puan
                    rating = random.choice([4.0, 4.5, 5.0])
                else:  # %30 şans ile orta puan
                    rating = random.choice([3.0, 3.5])
            else:
                # Sevmediği türse daha düşük puanlar
                if random.random() < 0.4:  # %40 şans ile düşük puan
                    rating = random.choice([1.5, 2.0, 2.5])
                else:  # %60 şans ile orta puan  
                    rating = random.choice([3.0, 3.5, 4.0])
            
            # Timestamp - son 2 yıl içinde rastgele
            days_ago = random.randint(1, 730)
            timestamp = datetime.now() - timedelta(days=days_ago)
            
            ratings.append({
                'user_id': user_id,
                'movie_id': movie_id,
                'rating': rating,
                'timestamp': timestamp
            })
        
        return ratings

def create_solid_dataset():
    print("SOLID REALISTIC DATASET CREATION")
    print("=" * 50)
    
    conn = sqlite3.connect('movielens_100k.db')
    
    # Mevcut filmler al
    movies = conn.execute("SELECT id, title, genres FROM movies WHERE genres IS NOT NULL LIMIT 500").fetchall()
    print(f"[1] Available movies: {len(movies)}")
    
    # User generator
    generator = RealisticUserGenerator()
    
    # 100 gerçekçi kullanıcı oluştur
    print("[2] Creating 100 realistic users...")
    users = generator.generate_realistic_users(100)
    
    created_users = 0
    total_ratings = 0
    
    for user in users:
        try:
            # Kullanıcı oluştur
            cursor = conn.execute("""
                INSERT INTO app_users (username, email, hashed_password, age, gender, favorite_genres)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user['username'], 
                user['email'], 
                'test123',  # Plaintext şifre (hash önceden düzeltildi)
                user['age'],
                user['gender'],
                user['favorite_genres']
            ))
            
            user_id = cursor.lastrowid
            created_users += 1
            
            # Bu kullanıcı için gerçekçi rating'ler
            ratings = generator.generate_realistic_ratings(user, user_id, movies)
            
            # Rating'leri database'e ekle
            for rating in ratings:
                conn.execute("""
                    INSERT INTO user_interactions (user_id, movie_id, interaction_type, extra_data, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    rating['user_id'],
                    rating['movie_id'],
                    'rating',
                    json.dumps({"rating": rating['rating']}),
                    rating['timestamp']
                ))
                
                total_ratings += 1
            
            if created_users % 20 == 0:
                print(f"    Created {created_users} users, {total_ratings} ratings...")
                
        except sqlite3.IntegrityError:
            # Kullanıcı zaten var, skip
            continue
        except Exception as e:
            print(f"    Error creating user {user['username']}: {e}")
    
    conn.commit()
    
    # Final statistics
    total_users = conn.execute("SELECT COUNT(*) FROM app_users").fetchone()[0]
    total_valid_ratings = conn.execute("""
        SELECT COUNT(*) FROM user_interactions 
        WHERE interaction_type = 'rating'
        AND extra_data IS NOT NULL
        AND JSON_EXTRACT(extra_data, '$.rating') IS NOT NULL
    """).fetchone()[0]
    
    users_with_ratings = conn.execute("""
        SELECT COUNT(DISTINCT user_id) FROM user_interactions
        WHERE interaction_type = 'rating' 
        AND extra_data IS NOT NULL
        AND JSON_EXTRACT(extra_data, '$.rating') IS NOT NULL
    """).fetchone()[0]
    
    conn.close()
    
    print(f"\n[+] Dataset Creation Complete!")
    print(f"    Total users: {total_users}")
    print(f"    Valid ratings: {total_valid_ratings}")
    print(f"    Users with ratings: {users_with_ratings}")
    print(f"    New users created: {created_users}")
    print(f"    New ratings created: {total_ratings}")
    
    return users_with_ratings >= 30  # En az 30 kullanıcı olmalı

if __name__ == "__main__":
    success = create_solid_dataset()
    if success:
        print("\n" + "=" * 50)
        print("REALISTIC DATASET READY FOR DEEP LEARNING!")
        print("=" * 50)
    else:
        print("\nDataset creation failed")
