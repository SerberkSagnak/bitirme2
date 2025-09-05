"""
Deep Learning Dataset Generator
100+ kullanıcı + 2000+ rating ile solid training data
"""

import sqlite3
import random
import json
import hashlib
from datetime import datetime, timedelta
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class DeepLearningDatasetGenerator:
    def __init__(self):
        self.db_path = "movielens_100k.db"
        
        # Gerçekçi kullanıcı isimleri
        self.first_names = [
            'Alice', 'Bob', 'Charlie', 'Diana', 'Emma', 'Frank', 'Grace', 'Henry',
            'Iris', 'Jack', 'Kate', 'Liam', 'Mia', 'Noah', 'Olivia', 'Paul',
            'Quinn', 'Ruby', 'Sam', 'Tina', 'Uma', 'Victor', 'Wendy', 'Xander',
            'Yara', 'Zoe', 'Alex', 'Ben', 'Chloe', 'David', 'Eva', 'Felix',
            'Gina', 'Hugo', 'Ivy', 'Jake', 'Luna', 'Max', 'Nina', 'Oscar'
        ]
        
        # Film türü profilleri
        self.genre_profiles = {
            'action_lover': {
                'genres': ['Action', 'Adventure', 'Sci-Fi', 'Thriller', 'War'],
                'high_rating_chance': 0.8,
                'avg_rating': 4.2
            },
            'romance_fan': {
                'genres': ['Romance', 'Comedy', 'Drama', 'Musical'],
                'high_rating_chance': 0.7,
                'avg_rating': 4.0
            },
            'horror_enthusiast': {
                'genres': ['Horror', 'Thriller', 'Mystery', 'Crime'],
                'high_rating_chance': 0.6,
                'avg_rating': 3.8
            },
            'comedy_lover': {
                'genres': ['Comedy', 'Animation', 'Family', 'Romance'],
                'high_rating_chance': 0.9,
                'avg_rating': 4.3
            },
            'drama_critic': {
                'genres': ['Drama', 'Documentary', 'Biography', 'History'],
                'high_rating_chance': 0.5,
                'avg_rating': 3.9
            },
            'sci_fi_geek': {
                'genres': ['Sci-Fi', 'Fantasy', 'Adventure', 'Action'],
                'high_rating_chance': 0.7,
                'avg_rating': 4.1
            },
            'cinephile': {
                'genres': ['Drama', 'Foreign', 'Art', 'Documentary', 'Film-Noir'],
                'high_rating_chance': 0.4,
                'avg_rating': 3.7
            },
            'casual_viewer': {
                'genres': ['Comedy', 'Action', 'Adventure', 'Animation'],
                'high_rating_chance': 0.8,
                'avg_rating': 4.0
            }
        }
        
        self.occupations = [
            'student', 'engineer', 'teacher', 'doctor', 'artist', 'manager',
            'programmer', 'designer', 'writer', 'researcher', 'analyst', 'nurse',
            'lawyer', 'chef', 'musician', 'accountant', 'consultant', 'architect'
        ]

    def create_realistic_user(self, index):
        """Gerçekçi kullanıcı profili oluştur"""
        name = random.choice(self.first_names)
        username = f"{name.lower()}_{index:03d}"
        
        # Realistic demographics
        age = max(18, min(70, int(random.gauss(32, 12))))
        gender = random.choice(['M', 'F'])
        occupation = random.choice(self.occupations)
        
        # Genre profili belirle
        profile_type = random.choice(list(self.genre_profiles.keys()))
        profile = self.genre_profiles[profile_type]
        
        return {
            'username': username,
            'email': f"{username}@dataset.com",
            'password': 'test123',  # Tüm kullanıcılar için aynı şifre
            'age': age,
            'gender': gender,
            'occupation': occupation,
            'profile_type': profile_type,
            'preferred_genres': profile['genres'],
            'high_rating_chance': profile['high_rating_chance'],
            'avg_rating_tendency': profile['avg_rating']
        }

    def generate_realistic_ratings(self, user_profile, user_id, available_movies):
        """Kullanıcı profiline göre gerçekçi rating'ler"""
        ratings = []
        
        # Film sayısı profil bazlı
        if user_profile['profile_type'] == 'cinephile':
            n_movies = random.randint(40, 80)  # Film severler çok izler
        elif user_profile['profile_type'] == 'casual_viewer':
            n_movies = random.randint(10, 25)  # Casual izleyiciler az
        else:
            n_movies = random.randint(20, 50)  # Normal dağılım
        
        # Random film seçimi
        selected_movies = random.sample(available_movies, min(n_movies, len(available_movies)))
        
        for movie in selected_movies:
            movie_id, title, genres = movie
            movie_genres = set(genres.split('|')) if genres else set()
            
            # Genre match kontrolü
            preferred = set(user_profile['preferred_genres'])
            genre_match_score = len(movie_genres & preferred) / max(len(preferred), 1)
            
            # Rating hesaplama (realistic)
            if genre_match_score > 0.5:  # Sevdiği tür
                if random.random() < user_profile['high_rating_chance']:
                    rating = random.uniform(4.0, 5.0)
                else:
                    rating = random.uniform(3.0, 4.0)
            elif genre_match_score > 0.2:  # Orta seviye
                rating = random.uniform(2.5, 4.0)
            else:  # Sevmediği tür
                if random.random() < 0.3:  # %30 şans ile izler
                    rating = random.uniform(1.5, 3.5)
                else:
                    continue  # İzlemez
            
            # Realistic rating distribution
            rating = round(rating * 2) / 2  # 0.5'lik adımlar
            rating = max(1.0, min(5.0, rating))
            
            # Random timestamp (son 2 yıl)
            days_ago = random.randint(1, 730)
            timestamp = datetime.now() - timedelta(days=days_ago)
            
            ratings.append({
                'user_id': user_id,
                'movie_id': movie_id,
                'rating': rating,
                'timestamp': timestamp,
                'genre_match': genre_match_score
            })
        
        return ratings

    def populate_database(self):
        """Database'i solid data ile doldur"""
        print("=== DEEP LEARNING DATASET GENERATION ===")
        
        conn = sqlite3.connect(self.db_path)
        
        # Mevcut filmler al
        movies = conn.execute("SELECT id, title, genres FROM movies WHERE genres IS NOT NULL").fetchall()
        print(f"[1] Available movies: {len(movies)}")
        
        if len(movies) < 100:
            print("[!] Not enough movies for deep learning!")
            return False
        
        # Alice kullanıcısını ekle (senin test kullanıcın)
        print("[2] Creating Alice user...")
        try:
            alice_password = pwd_context.hash('test123')
            conn.execute("""
                INSERT OR REPLACE INTO app_users 
                (id, username, email, hashed_password, age, gender, favorite_genres, created_at)
                VALUES (1, 'alice', 'alice@deeplearning.com', ?, 28, 'F', 'Action,Sci-Fi,Drama', ?)
            """, (alice_password, datetime.now()))
            print("   ✅ Alice user created")
        except Exception as e:
            print(f"   Alice creation error: {e}")
        
        # 100 realistic kullanıcı oluştur
        print("[3] Creating 100 realistic users...")
        created_users = []
        
        for i in range(100):
            user_profile = self.create_realistic_user(i + 2)  # Start from ID 2
            
            try:
                hashed_password = pwd_context.hash(user_profile['password'])
                
                cursor = conn.execute("""
                    INSERT INTO app_users 
                    (username, email, hashed_password, age, gender, favorite_genres, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_profile['username'],
                    user_profile['email'], 
                    hashed_password,
                    user_profile['age'],
                    user_profile['gender'],
                    ','.join(user_profile['preferred_genres']),
                    datetime.now()
                ))
                
                user_id = cursor.lastrowid
                created_users.append((user_id, user_profile))
                
                if (i + 1) % 20 == 0:
                    print(f"   Created {i + 1} users...")
                    
            except Exception as e:
                print(f"   Error creating user {i}: {e}")
        
        conn.commit()
        print(f"[4] Created {len(created_users)} users")
        
        # Rating'ler oluştur
        print("[5] Generating realistic ratings...")
        total_ratings = 0
        
        # Alice için özel rating'ler (test için)
        alice_movies = random.sample(movies, 30)
        for movie in alice_movies:
            rating = random.uniform(3.5, 5.0)  # Alice pozitif kullanıcı
            conn.execute("""
                INSERT INTO user_interactions 
                (user_id, movie_id, interaction_type, extra_data, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (1, movie[0], 'rating', json.dumps({"rating": rating}), datetime.now()))
            total_ratings += 1
        
        # Diğer kullanıcılar için rating'ler
        for user_id, user_profile in created_users:
            ratings = self.generate_realistic_ratings(user_profile, user_id, movies)
            
            for rating in ratings:
                conn.execute("""
                    INSERT INTO user_interactions 
                    (user_id, movie_id, interaction_type, extra_data, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    rating['user_id'],
                    rating['movie_id'],
                    'rating',
                    json.dumps({"rating": rating['rating']}),
                    rating['timestamp']
                ))
                total_ratings += 1
            
            if len(created_users) > 20 and (user_id - 1) % 20 == 0:
                print(f"   Generated ratings for {user_id - 1} users...")
        
        conn.commit()
        
        # Final statistics
        final_users = conn.execute("SELECT COUNT(*) FROM app_users").fetchone()[0]
        final_movies = conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
        final_ratings = conn.execute("SELECT COUNT(*) FROM user_interactions WHERE interaction_type = 'rating'").fetchone()[0]
        
        conn.close()
        
        print("\n=== DATASET GENERATION COMPLETE ===")
        print(f"Total Users: {final_users}")
        print(f"Total Movies: {final_movies}")
        print(f"Total Ratings: {final_ratings}")
        print(f"New Ratings Added: {total_ratings}")
        print("")
        print("Alice login info:")
        print("  Username: alice")
        print("  Password: test123")
        print("  Ratings: ~30 films")
        print("")
        print("✅ DEEP LEARNING DATASET READY!")
        
        return final_ratings > 1000  # En az 1000 rating olmalı

if __name__ == "__main__":
    generator = DeepLearningDatasetGenerator()
    success = generator.populate_database()
    
    if success:
        print("\n🧠 Ready for Neural Collaborative Filtering!")
        print("Next: Restart app_enhanced_v6.py")
    else:
        print("\n❌ Dataset generation failed")
