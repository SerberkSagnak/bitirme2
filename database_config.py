import sqlite3
import os
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Database configuration - MovieLens 100k veritabanını kullan
DATABASE_PATH = 'movielens_100k.db'
MOVIELENS_DATA_DIR = 'bitirme2/ml-100k'

# SQLAlchemy setup
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Database session dependency for FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_database_info():
    """Veritabanı bilgilerini döndürür"""
    if os.path.exists(DATABASE_PATH):
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        try:
            # Tablo sayısını kontrol et
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            info = {
                'exists': True,
                'tables': [table[0] for table in tables],
                'path': DATABASE_PATH,
                'size': os.path.getsize(DATABASE_PATH)
            }
            
            # Her tablo için kayıt sayısı
            table_counts = {}
            for table_name in info['tables']:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    table_counts[f'{table_name}_count'] = count
                except Exception:
                    table_counts[f'{table_name}_count'] = 0
            
            info.update(table_counts)
            
        except Exception as e:
            info = {'exists': False, 'error': str(e)}
        finally:
            conn.close()
            
        return info
    else:
        return {'exists': False, 'path': DATABASE_PATH}

def check_database_health():
    """Veritabanı sağlık kontrolü"""
    try:
        db = SessionLocal()
        
        # Ana tabloları kontrol et
        movies_count = db.execute(text("SELECT COUNT(*) FROM movies")).scalar()
        movielens_users_count = db.execute(text("SELECT COUNT(*) FROM movielens_users")).scalar() 
        ratings_count = db.execute(text("SELECT COUNT(*) FROM ratings")).scalar()
        
        # App kullanıcıları (varsa)
        try:
            app_users_count = db.execute(text("SELECT COUNT(*) FROM app_users")).scalar()
        except:
            app_users_count = 0
        
        db.close()
        
        return {
            "status": "healthy",
            "movies": movies_count,
            "movielens_users": movielens_users_count,
            "app_users": app_users_count,
            "ratings": ratings_count,
            "ready": True
        }
    except Exception as e:
        return {
            "status": "error", 
            "error": str(e),
            "ready": False
        }

def create_app_user_tables():
    """App kullanıcıları için ek tablolar oluştur"""
    print("🔧 App kullanıcı tabloları oluşturuluyor...")
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        # App Users tablosu (mevcut app_users tablosunu kontrol et)
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
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # User Interactions tablosu (güncellenmiş)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                movie_id INTEGER,
                interaction_type TEXT NOT NULL,
                metadata TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES app_users (id),
                FOREIGN KEY (movie_id) REFERENCES movies (id)
            )
        ''')
        
        # User Preferences tablosu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                favorite_genres TEXT,
                preferred_year_range TEXT,
                min_rating REAL,
                max_rating REAL,
                preferred_duration TEXT,
                exclude_genres TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES app_users (id),
                UNIQUE(user_id)
            )
        ''')
        
        # Watchlist tablosu  
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                movie_id INTEGER NOT NULL,
                status TEXT DEFAULT 'to_watch',
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                watched_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES app_users (id),
                FOREIGN KEY (movie_id) REFERENCES movies (id),
                UNIQUE(user_id, movie_id)
            )
        ''')
        
        # Analytics tablosu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                user_type TEXT DEFAULT 'app',
                action_type TEXT NOT NULL,
                movie_id INTEGER,
                details TEXT,
                session_id TEXT,
                ip_address TEXT,
                user_agent TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # İndeksler
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_interactions_user ON user_interactions(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_interactions_movie ON user_interactions(movie_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_analytics_user ON user_analytics(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_watchlist_user ON watchlist(user_id)')
        
        conn.commit()
        print("✅ App kullanıcı tabloları başarıyla oluşturuldu!")
        return True
        
    except Exception as e:
        print(f"❌ App tabloları oluşturma hatası: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def initialize_database():
    """Veritabanını başlatır ve kontrol eder"""
    try:
        db_info = get_database_info()
        
        if not db_info['exists']:
            print("❌ MovieLens veritabanı bulunamadı!")
            print("💡 Önce 'python movielens_database_setup.py' çalıştırın")
            return False
        
        print(f"✅ MovieLens veritabanı mevcut: {len(db_info['tables'])} tablo")
        print(f"📊 Movies: {db_info.get('movies_count', 0)} kayıt")
        print(f"👥 MovieLens Users: {db_info.get('movielens_users_count', 0)} kayıt")
        print(f"⭐ Ratings: {db_info.get('ratings_count', 0)} kayıt")
        
        # App kullanıcı tablolarını kontrol et ve oluştur
        if 'app_users' not in db_info['tables']:
            print("🔧 App kullanıcı tabloları eksik, oluşturuluyor...")
            create_app_user_tables()
        else:
            print(f"👤 App Users: {db_info.get('app_users_count', 0)} kayıt")
        
        return True
        
    except Exception as e:
        print(f"❌ Veritabanı başlatma hatası: {e}")
        return False

def get_sample_movies(limit=10):
    """Örnek filmleri getirir"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, title, genres, avg_rating, rating_count 
            FROM movies 
            WHERE rating_count > 50
            ORDER BY avg_rating DESC 
            LIMIT ?
        ''', (limit,))
        
        movies = cursor.fetchall()
        conn.close()
        
        return [
            {
                "id": movie[0],
                "title": movie[1], 
                "genres": movie[2].split(',') if movie[2] else [],
                "avg_rating": round(movie[3], 2),
                "rating_count": movie[4]
            }
            for movie in movies
        ]
        
    except Exception as e:
        print(f"❌ Örnek filmler alınamadı: {e}")
        return []

def get_user_statistics(user_id, user_type='app'):
    """Kullanıcı istatistiklerini getirir"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        if user_type == 'app':
            # App kullanıcısı istatistikleri
            cursor.execute('''
                SELECT COUNT(*) FROM ratings 
                WHERE user_id = ? AND user_type = 'app'
            ''', (user_id,))
            ratings_count = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT COUNT(*) FROM user_interactions 
                WHERE user_id = ? AND interaction_type = 'favorite'
            ''', (user_id,))
            favorites_count = cursor.fetchone()[0]
            
        else:
            # MovieLens kullanıcısı istatistikleri
            cursor.execute('''
                SELECT COUNT(*) FROM ratings 
                WHERE user_id = ? AND user_type = 'movielens'
            ''', (user_id,))
            ratings_count = cursor.fetchone()[0]
            favorites_count = 0
        
        conn.close()
        
        return {
            "ratings_count": ratings_count,
            "favorites_count": favorites_count,
            "user_type": user_type
        }
        
    except Exception as e:
        print(f"❌ Kullanıcı istatistikleri alınamadı: {e}")
        return {"ratings_count": 0, "favorites_count": 0}

def backup_database(backup_path=None):
    """Veritabanını yedekler"""
    if backup_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"backup_movielens_{timestamp}.db"
    
    try:
        import shutil
        shutil.copy2(DATABASE_PATH, backup_path)
        print(f"✅ Veritabanı yedeği oluşturuldu: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"❌ Yedekleme hatası: {e}")
        return None

def get_genre_list():
    """Tüm türleri getirir"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM genres ORDER BY name")
        genres = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return genres
    except Exception as e:
        print(f"❌ Türler alınamadı: {e}")
        return []

def get_recommendation_data(user_id=None, limit=1000):
    """Öneri sistemi için veri hazırlar"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        
        # Movies dataframe
        movies_df = pd.read_sql_query('''
            SELECT id, title, genres, avg_rating, rating_count, 
                   action, adventure, animation, children, comedy,
                   crime, documentary, drama, fantasy, film_noir,
                   horror, musical, mystery, romance, sci_fi,
                   thriller, war, western
            FROM movies
            WHERE rating_count > 0
        ''', conn)
        
        # Ratings dataframe
        if limit:
            ratings_df = pd.read_sql_query('''
                SELECT user_id, movie_id, rating, user_type
                FROM ratings
                ORDER BY RANDOM()
                LIMIT ?
            ''', conn, params=(limit,))
        else:
            ratings_df = pd.read_sql_query('''
                SELECT user_id, movie_id, rating, user_type
                FROM ratings
            ''', conn)
        
        conn.close()
        
        return movies_df, ratings_df
        
    except Exception as e:
        print(f"❌ Öneri verisi hazırlanamadı: {e}")
        return None, None

# Test ve debug fonksiyonları
def test_database_connection():
    """Veritabanı bağlantısını test eder"""
    try:
        health = check_database_health()
        if health["ready"]:
            print("✅ Veritabanı bağlantısı başarılı")
            print(f"📊 Veriler: {health['movies']} film, {health['ratings']} rating")
            return True
        else:
            print(f"❌ Veritabanı sorunu: {health['error']}")
            return False
    except Exception as e:
        print(f"❌ Bağlantı testi hatası: {e}")
        return False

if __name__ == "__main__":
    # Test database operations
    print("🧪 MovieLens Database Config Test...")
    print("-" * 50)
    
    # Veritabanı durumunu kontrol et
    db_info = get_database_info()
    print(f"📁 Veritabanı: {db_info}")
    
    if db_info['exists']:
        print("✅ Veritabanı mevcut")
        
        # Sağlık kontrolü
        health = check_database_health()
        print(f"🏥 Sağlık durumu: {health}")
        
        # Başlatma işlemi
        if initialize_database():
            print("🚀 Veritabanı başarıyla başlatıldı")
            
            # Test verileri
            sample_movies = get_sample_movies(5)
            print(f"🎬 Örnek filmler: {len(sample_movies)}")
            for movie in sample_movies[:3]:
                print(f"  - {movie['title']} ({movie['avg_rating']}⭐)")
            
            # Türler
            genres = get_genre_list()
            print(f"🎭 Mevcut türler: {len(genres)}")
            print(f"  İlk 5: {genres[:5]}")
            
            # Bağlantı testi
            test_database_connection()
            
        else:
            print("❌ Veritabanı başlatılamadı")
    else:
        print("❌ MovieLens veritabanı bulunamadı!")
        print("💡 Çözüm: Önce aşağıdaki komutu çalıştırın:")
        print("   python movielens_database_setup.py")
    
    print("-" * 50)
    print("✅ Test tamamlandı")
