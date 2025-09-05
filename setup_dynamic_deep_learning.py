"""
Dinamik Derin Öğrenme Sistemini Kurulum ve Aktifleştirme

Bu script:
1. Veritabanından training data hazırlar  
2. TensorFlow modelini eğitir
3. User embeddings oluşturur
4. Sistemi aktifleştirir
"""

import sys
import os
import sqlite3
import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

def create_training_data():
    """Veritabanından training data oluştur"""
    print("[*] Creating training data from database...")
    
    db_path = "movielens_100k.db"
    if not os.path.exists(db_path):
        print("[x] Database not found!")
        return False
    
    conn = sqlite3.connect(db_path)
    
    # Mevcut user ve movie sayısını kontrol et
    user_count = conn.execute("SELECT COUNT(*) FROM app_users").fetchone()[0]
    movie_count = conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
    rating_count = conn.execute("SELECT COUNT(*) FROM user_interactions WHERE interaction_type = 'rating'").fetchone()[0]
    
    print(f"[*] Current data: {user_count} users, {movie_count} movies, {rating_count} ratings")
    
    # Eğer yeterli veri yoksa synthetic data oluştur
    if rating_count < 100:
        print("[*] Insufficient data. Creating synthetic training data...")
        create_synthetic_training_data(conn)
    
    conn.close()
    return True

def create_synthetic_training_data(conn):
    """Synthetic training data oluştur"""
    
    # Mevcut filmler al
    movies_df = pd.read_sql_query("SELECT id, title, genres FROM movies", conn)
    movie_ids = movies_df['id'].tolist()
    
    if len(movie_ids) < 20:
        print("[x] Not enough movies for training!")
        return
    
    # Yeni test kullanıcıları oluştur
    test_users = []
    for i in range(20):  # 20 test kullanıcısı
        username = f"synth_user_{i+1}"
        
        # Kullanıcı var mı kontrol et
        existing = conn.execute("SELECT id FROM app_users WHERE username = ?", (username,)).fetchone()
        if existing:
            test_users.append(existing[0])
            continue
        
        # Yeni kullanıcı oluştur
        age = random.randint(18, 65)
        gender = random.choice(['M', 'F'])
        occupation = random.choice(['student', 'teacher', 'engineer', 'other'])
        
        cursor = conn.execute("""
            INSERT INTO app_users (username, email, hashed_password, age, gender, favorite_genres)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (username, f"{username}@synthetic.com", "test123", age, gender, "Action,Comedy"))
        
        user_id = cursor.lastrowid
        test_users.append(user_id)
        conn.commit()
    
    print(f"[+] Created {len(test_users)} synthetic users")
    
    # Her kullanıcı için rastgele film puanları oluştur
    total_ratings = 0
    for user_id in test_users:
        # Her kullanıcı 10-30 film puanlasın
        n_ratings = random.randint(10, 30)
        rated_movies = random.sample(movie_ids, min(n_ratings, len(movie_ids)))
        
        for movie_id in rated_movies:
            # Realistic rating distribution
            if random.random() < 0.6:  # %60 pozitif rating
                rating = random.choice([4.0, 4.5, 5.0])
            else:  # %40 orta/düşük rating
                rating = random.choice([2.0, 2.5, 3.0, 3.5])
            
            timestamp = datetime.now() - timedelta(days=random.randint(1, 365))
            
            # Rating kaydet
            conn.execute("""
                INSERT INTO user_interactions 
                (user_id, movie_id, interaction_type, extra_data, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, movie_id, 'rating', str(rating), timestamp))
            
            total_ratings += 1
    
    conn.commit()
    print(f"[+] Created {total_ratings} synthetic ratings")

def train_dynamic_model():
    """Dynamic Deep Learning modelini eğit"""
    print("[*] Training Dynamic Deep Learning Model...")
    
    try:
        # bitirme2 klasörüne geç
        os.chdir("bitirme2")
        
        # Dynamic recommender import et
        from bitirme2.dynamic_deep_recommender import DynamicDeepRecommender
        
        # Model instance oluştur
        recommender = DynamicDeepRecommender(
            embedding_dim=128,
            n_similar_users=10,
            model_path="dynamic_deep_model.h5",
            embeddings_path="user_embeddings.pkl"
        )
        
        # Model eğitimi
        print("[*] Starting model training...")
        success = recommender.train_model(retrain=True)
        
        if success:
            print("[+] Model training completed successfully!")
            
            # Test user için similarity test
            print("[*] Testing similarity calculation...")
            similar_users = recommender.find_similar_users(1)
            print(f"[+] Found {len(similar_users)} similar users for user 1")
            
            # Test recommendation
            recommendations = recommender.get_recommendations_from_similar_users(1, 5)
            print(f"[+] Generated {len(recommendations)} test recommendations")
            
            return True
        else:
            print("[x] Model training failed!")
            return False
            
    except Exception as e:
        print(f"[x] Training error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        os.chdir("..")  # Ana klasöre geri dön

def verify_system():
    """Sistemin çalışır durumda olduğunu doğrula"""
    print("[*] Verifying Dynamic Deep Learning System...")
    
    # Model dosyaları var mı kontrol et
    model_files = [
        "bitirme2/dynamic_deep_model.h5",
        "bitirme2/user_embeddings.pkl"
    ]
    
    all_exist = True
    for file_path in model_files:
        if os.path.exists(file_path):
            print(f"[+] {file_path} ✓")
        else:
            print(f"[x] {file_path} ✗")
            all_exist = False
    
    if all_exist:
        print("[+] All model files exist!")
        
        # API test
        try:
            import requests
            response = requests.get("http://localhost:8000/", timeout=5)
            if response.status_code == 200:
                print("[+] Server is running ✓")
                return True
            else:
                print("[x] Server not responding")
                return False
        except:
            print("[!] Server not running - please restart server")
            return False
    else:
        print("[x] Some model files missing")
        return False

def main():
    print("="*60)
    print("DINAMIK DERIN OGRENME SISTEMI KURULUMU")
    print("="*60)
    
    # 1. Training data oluştur
    if not create_training_data():
        print("[x] Training data creation failed!")
        return
    
    print("\n" + "="*40)
    print("MODEL EGITIMI BASLATIYOR...")
    print("="*40)
    
    # 2. Model eğit
    if not train_dynamic_model():
        print("[x] Model training failed!")
        return
    
    print("\n" + "="*40)
    print("SISTEM DOGRULAMA...")
    print("="*40)
    
    # 3. Sistem doğrula
    if verify_system():
        print("\n" + "="*60)
        print("DINAMIK DERIN OGRENME SISTEMI AKTIF!")
        print("="*60)
        print("\n[*] Artık şu endpoint'ler kullanılabilir:")
        print("- GET /dynamic-deep-recommendations")
        print("- GET /find-similar-users/{user_id}")
        print("- POST /update-user-preferences")
        print("- POST /retrain-dynamic-model")
        print("\n[*] Test için:")
        print("python test_dynamic_deep_system.py")
        print("="*60)
    else:
        print("\n[x] System verification failed!")

if __name__ == "__main__":
    main()
