import pandas as pd
import os
from sqlalchemy.orm import Session
from sqlalchemy import func
from bitirme2.database_config import SessionLocal, User, Movie, Rating, get_password_hash
import logging
from datetime import datetime
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MovieLensImporter:
    def __init__(self, data_path="ml-100k"):
        self.data_path = data_path
        self.db = SessionLocal()
    
    def check_files(self):
        """Gerekli dosyaların varlığını kontrol et"""
        required_files = ['u.item', 'u.data', 'u.user']
        
        for file in required_files:
            file_path = os.path.join(self.data_path, file)
            if not os.path.exists(file_path):
                logger.error(f"❌ Dosya bulunamadı: {file_path}")
                return False
            else:
                logger.info(f"✅ Dosya mevcut: {file_path}")
        
        return True
    
    def import_all(self):
        """Tüm verileri import et"""
        try:
            if not self.check_files():
                return False
            
            logger.info("🚀 MovieLens 100k import başlıyor...")
            
            # Mevcut verileri temizle
            self.clear_existing_data()
            
            # Verileri import et
            self.import_users()
            self.import_movies()
            self.import_ratings()
            
            # İstatistikleri güncelle
            self.update_movie_stats()
            
            logger.info("✅ Import tamamlandı!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Import hatası: {e}")
            self.db.rollback()
            return False
        finally:
            self.db.close()
    
    def clear_existing_data(self):
        """Mevcut verileri temizle"""
        try:
            logger.info("🗑️ Mevcut veriler temizleniyor...")
            
            self.db.query(Rating).delete()
            self.db.query(Movie).delete()  
            self.db.query(User).delete()
            
            self.db.commit()
            logger.info("✅ Mevcut veriler temizlendi")
            
        except Exception as e:
            logger.error(f"❌ Veri temizleme hatası: {e}")
            self.db.rollback()
            raise
    
    def import_users(self):
        """Kullanıcıları import et"""
        try:
            logger.info("👥 Kullanıcılar import ediliyor...")
            
            # u.user dosyasını oku
            users_file = os.path.join(self.data_path, 'u.user')
            
            users_df = pd.read_csv(
                users_file,
                sep='|',
                names=['user_id', 'age', 'gender', 'occupation', 'zip_code'],
                encoding='latin1'
            )
            
            users_list = []
            for _, row in users_df.iterrows():
                user = User(
                    id=int(row['user_id']),
                    username=f"user_{row['user_id']}",
                    email=f"user_{row['user_id']}@movielens.com",
                    hashed_password=get_password_hash("movielens123"),  # Varsayılan şifre
                    age=int(row['age']) if pd.notna(row['age']) else None,
                    gender=str(row['gender']) if pd.notna(row['gender']) else None,
                    created_at=datetime(1998, 1, 1),  # MovieLens 100k dataset tarihi
                    is_active=True
                )
                users_list.append(user)
            
            # Toplu olarak ekle
            self.db.bulk_save_objects(users_list)
            self.db.commit()
            
            logger.info(f"✅ {len(users_list)} kullanıcı eklendi")
            
        except Exception as e:
            logger.error(f"❌ Kullanıcı import hatası: {e}")
            raise
    
    def import_movies(self):
        """Filmleri import et"""
        try:
            logger.info("🎬 Filmler import ediliyor...")
            
            # u.item dosyasını oku
            movies_file = os.path.join(self.data_path, 'u.item')
            
            # Genre kolonları
            genre_cols = [
                'unknown', 
                , 'Animation', 'Children', 'Comedy',
                'Crime', 'Documentary', 'Drama', 'Fantasy', 'Film-Noir', 'Horror',
                'Musical', 'Mystery', 'Romance', 'Sci-Fi', 'Thriller', 'War', 'Western'
            ]
            
            # Tüm kolonlar
            all_cols = ['movie_id', 'title', 'release_date', 'video_release_date', 'imdb_url'] + genre_cols
            
            movies_df = pd.read_csv(
                movies_file,
                sep='|',
                names=all_cols,
                encoding='latin1'
            )
            
            movies_list = []
            for _, row in movies_df.iterrows():
                # Türleri belirle
                genres = []
                for genre in genre_cols:
                    if row[genre] == 1:
                        genres.append(genre)
                
                # Başlıktan yılı çıkar
                title = str(row['title'])
                year = None
                if '(' in title and title.endswith(')'):
                    try:
                        year_part = title.split('(')[-1].replace(')', '')
                        if year_part.isdigit() and len(year_part) == 4:
                            year = int(year_part)
                            title = title.rsplit('(', 1)[0].strip()
                    except:
                        pass
                
                # Release date ayarla
                release_date = None
                if pd.notna(row['release_date']):
                    try:
                        release_date = pd.to_datetime(row['release_date']).strftime('%Y-%m-%d')
                    except:
                        if year:
                            release_date = f"{year}-01-01"
                elif year:
                    release_date = f"{year}-01-01"
                
                movie = Movie(
                    id=int(row['movie_id']),
                    title=title,
                    original_title=title,
                    genres=json.dumps(genres),
                    release_date=release_date,
                    avg_rating=0.0,
                    rating_count=0,
                    popularity=0.0,
                    vote_average=0.0,
                    vote_count=0,
                    created_at=datetime.now()
                )
                movies_list.append(movie)
            
            # Toplu olarak ekle
            self.db.bulk_save_objects(movies_list)
            self.db.commit()
            
            logger.info(f"✅ {len(movies_list)} film eklendi")
            
        except Exception as e:
            logger.error(f"❌ Film import hatası: {e}")
            raise
    
    def import_ratings(self):
        """Puanlamaları import et"""
        try:
            logger.info("⭐ Puanlamalar import ediliyor...")
            
            # u.data dosyasını oku
            ratings_file = os.path.join(self.data_path, 'u.data')
            
            ratings_df = pd.read_csv(
                ratings_file,
                sep='\t',
                names=['user_id', 'movie_id', 'rating', 'timestamp']
            )
            
            logger.info(f"📊 {len(ratings_df)} puanlama bulundu")
            
            # Batch olarak ekle (bellek tasarrufu için)
            batch_size = 5000
            total_added = 0
            
            for i in range(0, len(ratings_df), batch_size):
                batch = ratings_df.iloc[i:i+batch_size]
                ratings_list = []
                
                for _, row in batch.iterrows():
                    rating = Rating(
                        user_id=int(row['user_id']),
                        movie_id=int(row['movie_id']),
                        rating=float(row['rating']),
                        created_at=datetime.fromtimestamp(int(row['timestamp']))
                    )
                    ratings_list.append(rating)
                
                self.db.bulk_save_objects(ratings_list)
                self.db.commit()
                
                total_added += len(ratings_list)
                logger.info(f"   {total_added}/{len(ratings_df)} puanlama eklendi...")
            
            logger.info(f"✅ {total_added} puanlama eklendi")
            
        except Exception as e:
            logger.error(f"❌ Puanlama import hatası: {e}")
            raise
    
    def update_movie_stats(self):
        """Film istatistiklerini güncelle"""
        try:
            logger.info("📊 Film istatistikleri hesaplanıyor...")
            
            # Her film için ortalama puan ve puan sayısını hesapla
            stats_query = """
                UPDATE movies 
                SET avg_rating = subquery.avg_rating,
                    rating_count = subquery.rating_count
                FROM (
                    SELECT 
                        movie_id,
                        AVG(rating) as avg_rating,
                        COUNT(*) as rating_count
                    FROM ratings 
                    GROUP BY movie_id
                ) AS subquery
                WHERE movies.id = subquery.movie_id
            """
            
            self.db.execute(stats_query)
            self.db.commit()
            
            logger.info("✅ Film istatistikleri güncellendi")
            
        except Exception as e:
            logger.error(f"❌ İstatistik güncelleme hatası: {e}")
            raise
    
    def show_summary(self):
        """Import özeti göster"""
        try:
            db = SessionLocal()
            
            user_count = db.query(User).count()
            movie_count = db.query(Movie).count()
            rating_count = db.query(Rating).count()
            
            avg_rating = db.query(func.avg(Rating.rating)).scalar()
            min_rating = db.query(func.min(Rating.rating)).scalar()
            max_rating = db.query(func.max(Rating.rating)).scalar()
            
            print("\n" + "="*50)
            print("📊 MOVIELENS 100K IMPORT ÖZETİ")
            print("="*50)
            print(f"👥 Toplam Kullanıcı: {user_count:,}")
            print(f"🎬 Toplam Film: {movie_count:,}")
            print(f"⭐ Toplam Puanlama: {rating_count:,}")
            print(f"📈 Ortalama Puan: {avg_rating:.2f}")
            print(f"📉 Puan Aralığı: {min_rating} - {max_rating}")
            print("="*50)
            
            # En çok puanlanan filmler
            top_movies = db.query(Movie).filter(
                Movie.rating_count > 100
            ).order_by(Movie.avg_rating.desc()).limit(10).all()
            
            print("\n🏆 EN YÜKSEK PUANLI FİLMLER (100+ puan):")
            for i, movie in enumerate(top_movies, 1):
                print(f"{i:2d}. {movie.title} - {movie.avg_rating:.2f} ⭐ ({movie.rating_count} puan)")
            
            db.close()
            
        except Exception as e:
            logger.error(f"❌ Özet gösterme hatası: {e}")

def main():
    """Ana fonksiyon"""
    print("🎬 MovieLens 100k Veritabanı Import Aracı")
    print("="*50)
    
    # Veri dizini sor
    data_path = input("📂 MovieLens 100k dizini (varsayılan: ml-100k): ").strip()
    if not data_path:
        data_path = "ml-100k"
    
    if not os.path.exists(data_path):
        print(f"❌ Dizin bulunamadı: {data_path}")
        return
    
    # Import işlemini başlat
    importer = MovieLensImporter(data_path)
    
    if importer.import_all():
        importer.show_summary()
        print("\n✅ Import başarıyla tamamlandı!")
    else:
        print("\n❌ Import başarısız!")

if __name__ == "__main__":
    main()