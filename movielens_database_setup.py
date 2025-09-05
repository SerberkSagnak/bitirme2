import pandas as pd
import sqlite3
import os
from datetime import datetime

class MovieLensDatabase:
    def __init__(self, data_dir='bitirme2/ml-100k', db_path='movielens_100k.db'):
        self.data_dir = data_dir
        self.db_path = db_path
        
    def create_database_schema(self):
        """Veritabanı şemasını oluştur"""
        print("🔨 Veritabanı şeması oluşturuluyor...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Movies tablosu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS movies (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                release_date TEXT,
                imdb_url TEXT,
                genres TEXT,  -- Virgülle ayrılmış türler
                unknown INTEGER DEFAULT 0,
                action INTEGER DEFAULT 0,
                adventure INTEGER DEFAULT 0,
                animation INTEGER DEFAULT 0,
                children INTEGER DEFAULT 0,
                comedy INTEGER DEFAULT 0,
                crime INTEGER DEFAULT 0,
                documentary INTEGER DEFAULT 0,
                drama INTEGER DEFAULT 0,
                fantasy INTEGER DEFAULT 0,
                film_noir INTEGER DEFAULT 0,
                horror INTEGER DEFAULT 0,
                musical INTEGER DEFAULT 0,
                mystery INTEGER DEFAULT 0,
                romance INTEGER DEFAULT 0,
                sci_fi INTEGER DEFAULT 0,
                thriller INTEGER DEFAULT 0,
                war INTEGER DEFAULT 0,
                western INTEGER DEFAULT 0,
                avg_rating REAL DEFAULT 0.0,
                rating_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Users tablosu - MovieLens kullanıcıları
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS movielens_users (
                id INTEGER PRIMARY KEY,
                age INTEGER,
                gender TEXT,
                occupation TEXT,
                zip_code TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # App kullanıcıları için ayrı tablo
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE,
                hashed_password TEXT NOT NULL,
                age INTEGER,
                gender TEXT,
                favorite_genres TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Ratings tablosu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                movie_id INTEGER NOT NULL,
                rating REAL NOT NULL,
                timestamp INTEGER,
                user_type TEXT DEFAULT 'movielens',  -- 'movielens' veya 'app'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, movie_id, user_type),
                FOREIGN KEY (movie_id) REFERENCES movies (id)
            )
        ''')
        
        # Genres tablosu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS genres (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL
            )
        ''')
        
        # User interactions (app kullanıcıları için)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                movie_id INTEGER,
                interaction_type TEXT NOT NULL,
                extra_data TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES app_users (id),
                FOREIGN KEY (movie_id) REFERENCES movies (id)
            )
        ''')
        
        # İndeksler
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ratings_user ON ratings(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ratings_movie ON ratings(movie_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_movies_genres ON movies(genres)')
        
        conn.commit()
        conn.close()
        print("✅ Veritabanı şeması oluşturuldu")
    
    def load_genres(self):
        """Genre verilerini yükle"""
        print("🎭 Genre verileri yükleniyor...")
        
        file_path = os.path.join(self.data_dir, 'u.genre')
        df = pd.read_csv(file_path, sep='|', header=None, names=['genre', 'genre_id'])
        
        conn = sqlite3.connect(self.db_path)
        
        for _, row in df.iterrows():
            conn.execute('''
                INSERT OR REPLACE INTO genres (id, name)
                VALUES (?, ?)
            ''', (row['genre_id'], row['genre']))
        
        conn.commit()
        conn.close()
        print(f"✅ {len(df)} genre yüklendi")
    
    def load_movies(self):
        """Film verilerini yükle"""
        print("🎬 Film verileri yükleniyor...")
        
        file_path = os.path.join(self.data_dir, 'u.item')
        
        column_names = [
            'movie_id', 'title', 'release_date', 'video_release_date', 'imdb_url',
            'unknown', 'Action', 'Adventure', 'Animation', 'Children', 'Comedy',
            'Crime', 'Documentary', 'Drama', 'Fantasy', 'Film-Noir', 'Horror',
            'Musical', 'Mystery', 'Romance', 'Sci-Fi', 'Thriller', 'War', 'Western'
        ]
        
        df = pd.read_csv(file_path, sep='|', header=None, names=column_names, encoding='latin-1')
        
        conn = sqlite3.connect(self.db_path)
        
        for _, movie in df.iterrows():
            # Genre'ları string olarak birleştir
            genre_cols = column_names[5:]  # Genre sütunları
            genres = []
            for i, genre_col in enumerate(genre_cols):
                if movie[genre_col] == 1:
                    genres.append(genre_col.replace('-', '_').lower())
            
            genres_str = ','.join(genres) if genres else ''
            
            conn.execute('''
                INSERT OR REPLACE INTO movies 
                (id, title, release_date, imdb_url, genres, unknown, action, adventure, 
                 animation, children, comedy, crime, documentary, drama, fantasy, 
                 film_noir, horror, musical, mystery, romance, sci_fi, thriller, war, western)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                movie['movie_id'], movie['title'], movie['release_date'], 
                movie['imdb_url'], genres_str,
                movie['unknown'], movie['Action'], movie['Adventure'],
                movie['Animation'], movie['Children'], movie['Comedy'],
                movie['Crime'], movie['Documentary'], movie['Drama'],
                movie['Fantasy'], movie['Film-Noir'], movie['Horror'],
                movie['Musical'], movie['Mystery'], movie['Romance'],
                movie['Sci-Fi'], movie['Thriller'], movie['War'], movie['Western']
            ))
        
        conn.commit()
        conn.close()
        print(f"✅ {len(df)} film yüklendi")
    
    def load_users(self):
        """MovieLens kullanıcı verilerini yükle"""
        print("👥 Kullanıcı verileri yükleniyor...")
        
        file_path = os.path.join(self.data_dir, 'u.user')
        df = pd.read_csv(file_path, sep='|', header=None, 
                        names=['user_id', 'age', 'gender', 'occupation', 'zip_code'])
        
        conn = sqlite3.connect(self.db_path)
        
        for _, user in df.iterrows():
            conn.execute('''
                INSERT OR REPLACE INTO movielens_users 
                (id, age, gender, occupation, zip_code)
                VALUES (?, ?, ?, ?, ?)
            ''', (user['user_id'], user['age'], user['gender'], 
                  user['occupation'], user['zip_code']))
        
        conn.commit()
        conn.close()
        print(f"✅ {len(df)} kullanıcı yüklendi")
    
    def load_ratings(self):
        """Rating verilerini yükle"""
        print("⭐ Rating verileri yükleniyor...")
        
        file_path = os.path.join(self.data_dir, 'u.data')
        df = pd.read_csv(file_path, sep='\t', header=None, 
                        names=['user_id', 'movie_id', 'rating', 'timestamp'])
        
        conn = sqlite3.connect(self.db_path)
        
        # Batch insert için verileri hazırla
        ratings_data = []
        for _, rating in df.iterrows():
            ratings_data.append((
                rating['user_id'], rating['movie_id'], 
                rating['rating'], rating['timestamp'], 'movielens'
            ))
        
        # Batch insert
        conn.executemany('''
            INSERT OR REPLACE INTO ratings 
            (user_id, movie_id, rating, timestamp, user_type)
            VALUES (?, ?, ?, ?, ?)
        ''', ratings_data)
        
        conn.commit()
        conn.close()
        print(f"✅ {len(df)} rating yüklendi")
    
    def calculate_movie_statistics(self):
        """Film istatistiklerini hesapla"""
        print("📊 Film istatistikleri hesaplanıyor...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE movies 
            SET avg_rating = (
                SELECT AVG(rating) 
                FROM ratings 
                WHERE ratings.movie_id = movies.id
            ),
            rating_count = (
                SELECT COUNT(*) 
                FROM ratings 
                WHERE ratings.movie_id = movies.id
            )
            WHERE id IN (SELECT DISTINCT movie_id FROM ratings)
        ''')
        
        conn.commit()
        conn.close()
        print("✅ Film istatistikleri güncellendi")
    
    def setup_complete_database(self):
        """Tam veritabanı kurulumu"""
        print("🚀 MovieLens 100k Veritabanı Kurulumu Başlıyor...")
        print("-" * 50)
        
        # Adım 1: Şema oluştur
        self.create_database_schema()
        
        # Adım 2: Verileri yükle
        self.load_genres()
        self.load_movies()
        self.load_users() 
        self.load_ratings()
        
        # Adım 3: İstatistikleri hesapla
        self.calculate_movie_statistics()
        
        print("-" * 50)
        print("🎉 Veritabanı kurulumu tamamlandı!")
        
        # Özet bilgi
        self.show_database_summary()
    
    def show_database_summary(self):
        """Veritabanı özetini göster"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        movies_count = cursor.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
        users_count = cursor.execute("SELECT COUNT(*) FROM movielens_users").fetchone()[0]
        ratings_count = cursor.execute("SELECT COUNT(*) FROM ratings").fetchone()[0]
        genres_count = cursor.execute("SELECT COUNT(*) FROM genres").fetchone()[0]
        
        # En popüler filmler
        top_movies = cursor.execute('''
            SELECT title, avg_rating, rating_count 
            FROM movies 
            WHERE rating_count >= 10 
            ORDER BY avg_rating DESC 
            LIMIT 5
        ''').fetchall()
        
        conn.close()
        
        print(f"""
📈 VERİTABANI ÖZETİ:
┌─────────────────────────────────┐
│ 🎬 Filmler:        {movies_count:>8,} │
│ 👥 Kullanıcılar:   {users_count:>8,} │  
│ ⭐ Puanlamalar:    {ratings_count:>8,} │
│ 🎭 Türler:         {genres_count:>8,} │
└─────────────────────────────────┘

🏆 EN POPÜLER FİLMLER:""")
        
        for i, (title, rating, count) in enumerate(top_movies, 1):
            print(f"  {i}. {title[:30]:<30} {rating:.1f}⭐ ({count} oy)")
        
        print(f"\n💾 Veritabanı dosyası: {self.db_path}")
        print(f"📁 Dosya boyutu: {os.path.getsize(self.db_path):,} bytes")

if __name__ == "__main__":
    db_setup = MovieLensDatabase()
    db_setup.setup_complete_database()