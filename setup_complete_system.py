import sqlite3
import pandas as pd
import numpy as np
import pickle
import requests
import zipfile
import os
from datetime import datetime

def download_movielens_100k():
    """MovieLens 100K dataset indir"""
    print("📥 DOWNLOADING MOVIELENS 100K DATASET")
    print("="*50)
    
    url = "https://files.grouplens.org/datasets/movielens/ml-100k.zip"
    zip_file = "ml-100k.zip"
    
    if not os.path.exists("ml-100k"):
        print("⬇️ Downloading MovieLens 100K...")
        response = requests.get(url)
        with open(zip_file, 'wb') as f:
            f.write(response.content)
        
        print("📦 Extracting...")
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall()
        
        os.remove(zip_file)
        print("✅ Dataset downloaded and extracted!")
    else:
        print("✅ Dataset already exists!")

def setup_database():
    """Complete database setup"""
    print("\n🗄️ DATABASE SETUP")
    print("="*30)
    
    conn = sqlite3.connect('movie_recommendation.db')
    cursor = conn.cursor()
    
    # 1. Create tables
    print("📊 Creating tables...")
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            email TEXT,
            password_hash TEXT,
            age INTEGER,
            gender TEXT,
            occupation TEXT,
            zip_code TEXT,
            favorite_genres TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Movies table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movies (
            movie_id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            release_date TEXT,
            video_release_date TEXT,
            imdb_url TEXT,
            genres TEXT,
            avg_rating REAL DEFAULT 0,
            popularity INTEGER DEFAULT 0
        )
    ''')
    
    # Ratings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            movie_id INTEGER,
            rating REAL,
            timestamp INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (movie_id) REFERENCES movies (movie_id)
        )
    ''')
    
    # Favorites table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            movie_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (movie_id) REFERENCES movies (movie_id)
        )
    ''')
    
    # User activities table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_activities (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            movie_id INTEGER,
            activity_type TEXT,
            status TEXT,
            rating REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (movie_id) REFERENCES movies (movie_id)
        )
    ''')
    
    conn.commit()
    print("✅ Tables created!")
    
    return conn

def import_movielens_data(conn):
    """MovieLens verilerini import et"""
    print("\n📥 IMPORTING MOVIELENS DATA")
    print("="*40)
    
    cursor = conn.cursor()
    
    # 1. Import users
    print("👥 Importing users...")
    users_file = "ml-100k/u.user"
    if os.path.exists(users_file):
        users_data = []
        with open(users_file, 'r', encoding='latin-1') as f:
            for line in f:
                parts = line.strip().split('|')
                if len(parts) >= 5:
                    user_id, age, gender, occupation, zip_code = parts[:5]
                    users_data.append((int(user_id), f"user_{user_id}", f"user{user_id}@example.com", 
                                     "dummy_hash", int(age), gender, occupation, zip_code, ""))
        
        cursor.executemany('''
            INSERT OR REPLACE INTO users (id, username, email, password_hash, age, gender, occupation, zip_code, favorite_genres)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', users_data)
        print(f"✅ Imported {len(users_data)} users")
    
    # 2. Import movies
    print("🎬 Importing movies...")
    movies_file = "ml-100k/u.item"
    if os.path.exists(movies_file):
        movies_data = []
        with open(movies_file, 'r', encoding='latin-1', errors='ignore') as f:
            for line in f:
                parts = line.strip().split('|')
                if len(parts) >= 5:
                    movie_id = int(parts[0])
                    title = parts[1]
                    release_date = parts[2] if parts[2] else None
                    video_release_date = parts[3] if parts[3] else None
                    imdb_url = parts[4] if parts[4] else None
                    
                    # Genres (son 19 kolon)
                    genre_cols = parts[5:] if len(parts) > 5 else []
                    genre_names = ['unknown', 'Action', 'Adventure', 'Animation', 'Children', 'Comedy', 
                                 'Crime', 'Documentary', 'Drama', 'Fantasy', 'Film-Noir', 'Horror', 
                                 'Musical', 'Mystery', 'Romance', 'Sci-Fi', 'Thriller', 'War', 'Western']
                    
                    genres = []
                    for i, col in enumerate(genre_cols[:19]):
                        if col == '1' and i < len(genre_names):
                            genres.append(genre_names[i])
                    
                    movies_data.append((movie_id, title, release_date, video_release_date, 
                                     imdb_url, '|'.join(genres), 0, 0))
        
        cursor.executemany('''
            INSERT OR REPLACE INTO movies (movie_id, title, release_date, video_release_date, imdb_url, genres, avg_rating, popularity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', movies_data)
        print(f"✅ Imported {len(movies_data)} movies")
    
    # 3. Import ratings
    print("⭐ Importing ratings...")
    ratings_file = "ml-100k/u.data"
    if os.path.exists(ratings_file):
        ratings_data = []
        with open(ratings_file, 'r') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) >= 4:
                    user_id, movie_id, rating, timestamp = parts[:4]
                    ratings_data.append((int(user_id), int(movie_id), float(rating), int(timestamp)))
        
        cursor.executemany('''
            INSERT OR REPLACE INTO ratings (user_id, movie_id, rating, timestamp)
            VALUES (?, ?, ?, ?)
        ''', ratings_data)
        print(f"✅ Imported {len(ratings_data)} ratings")
    
    # Update movie statistics
    print("📊 Updating movie statistics...")
    cursor.execute('''
        UPDATE movies SET 
            avg_rating = (SELECT AVG(rating) FROM ratings WHERE ratings.movie_id = movies.movie_id),
            popularity = (SELECT COUNT(*) FROM ratings WHERE ratings.movie_id = movies.movie_id)
        WHERE movie_id IN (SELECT DISTINCT movie_id FROM ratings)
    ''')
    
    conn.commit()
    print("✅ Data import completed!")

def create_user_movie_matrix(conn):
    """Proper user-movie matrix oluştur"""
    print("\n📊 CREATING USER-MOVIE MATRIX")
    print("="*40)
    
    # Ratings'leri al
    print("📥 Loading ratings from database...")
    ratings_df = pd.read_sql_query("""
        SELECT user_id, movie_id, rating 
        FROM ratings 
        ORDER BY user_id, movie_id
    """, conn)
    
    print(f"✅ Loaded {len(ratings_df):,} ratings")
    print(f"👥 Users: {ratings_df['user_id'].nunique()}")
    print(f"🎬 Movies: {ratings_df['movie_id'].nunique()}")
    
    # Matrix oluştur
    print("🔄 Creating matrix...")
    user_movie_matrix = ratings_df.pivot_table(
        index='user_id', 
        columns='movie_id', 
        values='rating', 
        fill_value=np.nan
    )
    
    print(f"📏 Matrix shape: {user_movie_matrix.shape}")
    non_null_count = user_movie_matrix.count().sum()
    sparsity = (user_movie_matrix.isnull().sum().sum() / user_movie_matrix.size) * 100
    
    print(f"⭐ Non-null ratings: {non_null_count:,}")
    print(f"🕳️ Sparsity: {sparsity:.1f}%")
    
    # Save matrix
    with open('user_movie_matrix.pkl', 'wb') as f:
        pickle.dump(user_movie_matrix, f)
    
    print("✅ Matrix saved as 'user_movie_matrix.pkl'")
    
    return user_movie_matrix

def verify_system():
    """Sistem kurulumunu doğrula"""
    print("\n✅ SYSTEM VERIFICATION")
    print("="*30)
    
    # Database check
    conn = sqlite3.connect('movie_recommendation.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cursor.fetchall()]
    print(f"📊 Tables: {tables}")
    
    for table in ['users', 'movies', 'ratings']:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table}: {count:,} records")
    
    # Matrix check
    if os.path.exists('user_movie_matrix.pkl'):
        with open('user_movie_matrix.pkl', 'rb') as f:
            matrix = pickle.load(f)
        print(f"📏 Matrix: {matrix.shape}")
        print(f"⭐ Ratings: {matrix.count().sum():,}")
    
    conn.close()
    print("\n🎉 SYSTEM SETUP COMPLETED!")
    print("🚀 Ready for Option 1 Implementation!")

def main():
    """Ana setup fonksiyonu"""
    print("🚀 COMPLETE SYSTEM SETUP")
    print("="*60)
    
    try:
        # 1. Download dataset
        download_movielens_100k()
        
        # 2. Setup database
        conn = setup_database()
        
        # 3. Import data
        import_movielens_data(conn)
        
        # 4. Create matrix
        create_user_movie_matrix(conn)
        
        # 5. Verify
        verify_system()
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Setup error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()