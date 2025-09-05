from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
import json

# SQLite Database
DATABASE_URL = "sqlite:///./movie_recommendation.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 👤 User Model
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    
    # Profile bilgileri
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)  # M, F, Other
    location = Column(String, nullable=True)
    favorite_genres = Column(Text, nullable=True)  # JSON string
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    
    # İlişkiler
    ratings = relationship("Rating", back_populates="user")
    favorites = relationship("Favorite", back_populates="user")

# 🎬 Movie Model (genişletilmiş)
class Movie(Base):
    __tablename__ = "movies"
    
    id = Column(Integer, primary_key=True, index=True)
    movie_id = Column(Integer, unique=True, index=True)  # Original dataset ID
    title = Column(String, index=True)
    release_date = Column(String)
    imdb_url = Column(String)
    
    # Yeni alanlar
    genres = Column(Text)  # JSON string
    description = Column(Text, nullable=True)
    director = Column(String, nullable=True)
    cast = Column(Text, nullable=True)  # JSON string
    
    # İstatistikler (cache için)
    avg_rating = Column(Float, default=0.0)
    rating_count = Column(Integer, default=0)
    popularity_score = Column(Float, default=0.0)
    
    # İlişkiler
    ratings = relationship("Rating", back_populates="movie")
    favorites = relationship("Favorite", back_populates="movie")

# ⭐ Rating Model
class Rating(Base):
    __tablename__ = "ratings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    movie_id = Column(Integer, ForeignKey("movies.id"))
    rating = Column(Float)  # 1.0 - 5.0
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    # İlişkiler
    user = relationship("User", back_populates="ratings")
    movie = relationship("Movie", back_populates="ratings")

# ❤️ Favorites Model
class Favorite(Base):
    __tablename__ = "favorites"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    movie_id = Column(Integer, ForeignKey("movies.id"))
    
    # Favorite türü
    list_type = Column(String, default="favorite")  # favorite, watchlist, watched
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # İlişkiler
    user = relationship("User", back_populates="favorites")
    movie = relationship("Movie", back_populates="favorites")

# 📊 User Activity Model (metrikler için)
class UserActivity(Base):
    __tablename__ = "user_activities"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    activity_type = Column(String)  # "view_movie", "search", "rate", "favorite"
    movie_id = Column(Integer, nullable=True)
    extra_data = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

# Database oluştur
def create_database():
    Base.metadata.create_all(bind=engine)
    print("🗄️ Database tabloları oluşturuldu!")

# Database session dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 🗄️ DatabaseManager Class
class DatabaseManager:
    def __init__(self):
        self.SessionLocal = SessionLocal
    
    def get_session(self):
        """Database session'ı döndürür"""
        return self.SessionLocal()
    
    def authenticate_user(self, username, password):
        """Kullanıcı authentication"""
        try:
            from auth import UserService
            user_service = UserService(self.get_session())
            return user_service.authenticate_user(username, password)
        except Exception as e:
            print(f"❌ DatabaseManager authenticate_user error: {e}")
            return None
    
    def create_access_token_for_user(self, username):
        """Kullanıcı için token oluştur"""
        try:
            from auth import create_access_token
            return create_access_token(data={"sub": username})
        except Exception as e:
            print(f"❌ Token creation error: {e}")
            return None
    
    def get_all_genres(self):
        """Tüm türleri getirir"""
        db = self.get_session()
        try:
            movies = db.query(Movie).filter(Movie.genres.isnot(None)).all()
            genres_set = set()
            
            for movie in movies:
                if movie.genres:
                    try:
                        # JSON string ise parse et
                        genres_list = json.loads(movie.genres)
                        if isinstance(genres_list, list):
                            for genre in genres_list:
                                if isinstance(genre, str):
                                    genres_set.add(genre.strip())
                    except (json.JSONDecodeError, TypeError):
                        # JSON değilse basit split kullan
                        if isinstance(movie.genres, str):
                            genres_list = movie.genres.split('|')
                            for genre in genres_list:
                                genres_set.add(genre.strip())
            
            return sorted(list(genres_set))
        except Exception as e:
            print(f"Get genres error: {e}")
            return []
        finally:
            db.close()
    
    def create_user(self, username, email, hashed_password, **kwargs):
        """Yeni kullanıcı oluşturur"""
        db = self.get_session()
        try:
            user = User(
                username=username,
                email=email,
                hashed_password=hashed_password,
                **kwargs
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            return user
        except Exception as e:
            db.rollback()
            print(f"User creation error: {e}")
            return None
        finally:
            db.close()
    
    def get_user_by_username(self, username):
        """Kullanıcıyı username ile bulur"""
        db = self.get_session()
        try:
            return db.query(User).filter(User.username == username).first()
        finally:
            db.close()
    
    def get_user_by_email(self, email):
        """Kullanıcıyı email ile bulur"""
        db = self.get_session()
        try:
            return db.query(User).filter(User.email == email).first()
        finally:
            db.close()
    
    def get_user_by_id(self, user_id):
        """Kullanıcıyı ID ile bulur"""
        db = self.get_session()
        try:
            return db.query(User).filter(User.id == user_id).first()
        finally:
            db.close()
    
    def get_movie_by_id(self, movie_id):
        """Film ID ile film bulur"""
        db = self.get_session()
        try:
            return db.query(Movie).filter(Movie.id == movie_id).first()
        finally:
            db.close()
    
    def get_movie_by_movie_id(self, movie_id):
        """Original movie ID ile film bulur"""
        db = self.get_session()
        try:
            return db.query(Movie).filter(Movie.movie_id == movie_id).first()
        finally:
            db.close()
    
    def get_movies(self, limit=50, offset=0):
        """Filmleri listeler"""
        db = self.get_session()
        try:
            return db.query(Movie).offset(offset).limit(limit).all()
        finally:
            db.close()
    
    def add_movie(self, movie_data):
        """Yeni film ekler"""
        db = self.get_session()
        try:
            movie = Movie(**movie_data)
            db.add(movie)
            db.commit()
            db.refresh(movie)
            return movie
        except Exception as e:
            db.rollback()
            print(f"Film eklenirken hata: {e}")
            return None
        finally:
            db.close()
    
    def add_rating(self, user_id, movie_id, rating):
        """Film rating'i ekler"""
        db = self.get_session()
        try:
            # Mevcut rating'i kontrol et
            existing_rating = db.query(Rating).filter(
                Rating.user_id == user_id,
                Rating.movie_id == movie_id
            ).first()
            
            if existing_rating:
                existing_rating.rating = rating
                existing_rating.updated_at = datetime.utcnow()
            else:
                new_rating = Rating(
                    user_id=user_id,
                    movie_id=movie_id,
                    rating=rating
                )
                db.add(new_rating)
            
            db.commit()
            # Film istatistiklerini güncelle
            self.update_movie_stats(movie_id)
            return True
        except Exception as e:
            db.rollback()
            print(f"Rating eklenirken hata: {e}")
            return False
        finally:
            db.close()
    
    def add_favorite(self, user_id, movie_id, list_type="favorite"):
        """Favorilere ekler"""
        db = self.get_session()
        try:
            # Mevcut favoriyi kontrol et
            existing_fav = db.query(Favorite).filter(
                Favorite.user_id == user_id,
                Favorite.movie_id == movie_id,
                Favorite.list_type == list_type
            ).first()
            
            if not existing_fav:
                favorite = Favorite(
                    user_id=user_id,
                    movie_id=movie_id,
                    list_type=list_type
                )
                db.add(favorite)
                db.commit()
                return True
            return False
        except Exception as e:
            db.rollback()
            print(f"Favori eklenirken hata: {e}")
            return False
        finally:
            db.close()
    
    def remove_favorite(self, user_id, movie_id, list_type="favorite"):
        """Favorilerden çıkarır"""
        db = self.get_session()
        try:
            favorite = db.query(Favorite).filter(
                Favorite.user_id == user_id,
                Favorite.movie_id == movie_id,
                Favorite.list_type == list_type
            ).first()
            
            if favorite:
                db.delete(favorite)
                db.commit()
                return True
            return False
        except Exception as e:
            db.rollback()
            print(f"Favori silinirken hata: {e}")
            return False
        finally:
            db.close()
    
    def get_user_ratings(self, user_id):
        """Kullanıcının rating'lerini getirir"""
        db = self.get_session()
        try:
            return db.query(Rating).filter(Rating.user_id == user_id).all()
        finally:
            db.close()
    
    def get_user_favorites(self, user_id, list_type="favorite"):
        """Kullanıcının favorilerini getirir"""
        db = self.get_session()
        try:
            return db.query(Favorite).filter(
                Favorite.user_id == user_id,
                Favorite.list_type == list_type
            ).all()
        finally:
            db.close()
    
    def search_movies(self, query, limit=20):
        """Film araması yapar"""
        db = self.get_session()
        try:
            return db.query(Movie).filter(
                Movie.title.contains(query)
            ).limit(limit).all()
        finally:
            db.close()
    
    def get_movies_by_genre(self, genre, limit=20):
        """Türe göre film getirir"""
        db = self.get_session()
        try:
            return db.query(Movie).filter(
                Movie.genres.contains(genre)
            ).limit(limit).all()
        finally:
            db.close()
    
    def get_top_rated_movies(self, limit=20):
        """En yüksek puanlı filmleri getirir"""
        db = self.get_session()
        try:
            return db.query(Movie).filter(
                Movie.rating_count > 0
            ).order_by(Movie.avg_rating.desc()).limit(limit).all()
        finally:
            db.close()
    
    def get_popular_movies(self, limit=20):
        """Popüler filmleri getirir"""
        db = self.get_session()
        try:
            return db.query(Movie).order_by(
                Movie.popularity_score.desc(),
                Movie.rating_count.desc()
            ).limit(limit).all()
        finally:
            db.close()
    
    def update_movie_stats(self, movie_id):
        """Film istatistiklerini günceller"""
        db = self.get_session()
        try:
            movie = db.query(Movie).filter(Movie.id == movie_id).first()
            if movie:
                ratings = db.query(Rating).filter(Rating.movie_id == movie_id).all()
                if ratings:
                    movie.avg_rating = sum(r.rating for r in ratings) / len(ratings)
                    movie.rating_count = len(ratings)
                    # Popularity score hesapla (rating count * avg rating)
                    movie.popularity_score = movie.rating_count * movie.avg_rating
                    db.commit()
                    return True
            return False
        except Exception as e:
            db.rollback()
            print(f"Film istatistikleri güncellenirken hata: {e}")
            return False
        finally:
            db.close()
    
    def add_user_activity(self, user_id, activity_type, movie_id=None, extra_data=None):
        """Kullanıcı aktivitesi ekler"""
        db = self.get_session()
        try:
            activity = UserActivity(
                user_id=user_id,
                activity_type=activity_type,
                movie_id=movie_id,
                extra_data=extra_data
            )
            db.add(activity)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            print(f"Aktivite eklenirken hata: {e}")
            return False
        finally:
            db.close()
    
    def get_user_activities(self, user_id, limit=50):
        """Kullanıcının aktivitelerini getirir"""
        db = self.get_session()
        try:
            return db.query(UserActivity).filter(
                UserActivity.user_id == user_id
            ).order_by(UserActivity.created_at.desc()).limit(limit).all()
        finally:
            db.close()
    
    def get_movie_ratings(self, movie_id):
        """Filmin tüm rating'lerini getirir"""
        db = self.get_session()
        try:
            return db.query(Rating).filter(Rating.movie_id == movie_id).all()
        finally:
            db.close()
    
    def get_user_rating_for_movie(self, user_id, movie_id):
        """Kullanıcının belirli bir film için verdiği rating'i getirir"""
        db = self.get_session()
        try:
            return db.query(Rating).filter(
                Rating.user_id == user_id,
                Rating.movie_id == movie_id
            ).first()
        finally:
            db.close()
    
    def is_movie_favorited(self, user_id, movie_id, list_type="favorite"):
        """Film kullanıcının favorilerinde mi kontrol eder"""
        db = self.get_session()
        try:
            favorite = db.query(Favorite).filter(
                Favorite.user_id == user_id,
                Favorite.movie_id == movie_id,
                Favorite.list_type == list_type
            ).first()
            return favorite is not None
        finally:
            db.close()
    
    def get_recently_added_movies(self, limit=20):
        """Son eklenen filmleri getirir"""
        db = self.get_session()
        try:
            return db.query(Movie).order_by(Movie.id.desc()).limit(limit).all()
        finally:
            db.close()
    
    def get_movies_by_year(self, year, limit=20):
        """Belirli yıla ait filmleri getirir"""
        db = self.get_session()
        try:
            return db.query(Movie).filter(
                Movie.release_date.contains(str(year))
            ).limit(limit).all()
        finally:
            db.close()
    
    def get_movies_by_director(self, director, limit=20):
        """Belirli yönetmene ait filmleri getirir"""
        db = self.get_session()
        try:
            return db.query(Movie).filter(
                Movie.director.contains(director)
            ).limit(limit).all()
        finally:
            db.close()
    
    def update_user_last_active(self, user_id):
        """Kullanıcının son aktiflik zamanını günceller"""
        db = self.get_session()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.last_active = datetime.utcnow()
                db.commit()
                return True
            return False
        except Exception as e:
            db.rollback()
            print(f"Son aktiflik güncellenirken hata: {e}")
            return False
        finally:
            db.close()
    
    def get_active_users(self, days=30, limit=50):
        """Son X gün içinde aktif olan kullanıcıları getirir"""
        db = self.get_session()
        try:
            from datetime import timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            return db.query(User).filter(
                User.last_active >= cutoff_date
            ).order_by(User.last_active.desc()).limit(limit).all()
        finally:
            db.close()
    
    def get_database_stats(self):
        """Database istatistiklerini getirir"""
        db = self.get_session()
        try:
            stats = {
                'total_users': db.query(User).count(),
                'total_movies': db.query(Movie).count(),
                'total_ratings': db.query(Rating).count(),
                'total_favorites': db.query(Favorite).count(),
                'total_activities': db.query(UserActivity).count()
            }
            
            # En aktif kullanıcı
            most_active_user = db.query(User).join(Rating).group_by(User.id).order_by(db.func.count(Rating.id).desc()).first()
            if most_active_user:
                stats['most_active_user'] = most_active_user.username
            
            # En popüler film
            most_popular_movie = db.query(Movie).filter(Movie.rating_count > 0).order_by(Movie.popularity_score.desc()).first()
            if most_popular_movie:
                stats['most_popular_movie'] = most_popular_movie.title
            
            return stats
        except Exception as e:
            print(f"İstatistik hesaplanırken hata: {e}")
            return {}
        finally:
            db.close()
    
    def bulk_update_movie_stats(self):
        """Tüm filmlerin istatistiklerini toplu günceller"""
        db = self.get_session()
        try:
            movies = db.query(Movie).all()
            updated_count = 0
            
            for movie in movies:
                ratings = db.query(Rating).filter(Rating.movie_id == movie.id).all()
                if ratings:
                    movie.avg_rating = sum(r.rating for r in ratings) / len(ratings)
                    movie.rating_count = len(ratings)
                    movie.popularity_score = movie.rating_count * movie.avg_rating
                    updated_count += 1
                else:
                    movie.avg_rating = 0.0
                    movie.rating_count = 0
                    movie.popularity_score = 0.0
            
            db.commit()
            print(f"✅ {updated_count} film istatistiği güncellendi")
            return updated_count
        except Exception as e:
            db.rollback()
            print(f"Toplu güncelleme hatası: {e}")
            return 0
        finally:
            db.close()
    
    def cleanup_old_activities(self, days=90):
        """Eski aktiviteleri temizler"""
        db = self.get_session()
        try:
            from datetime import timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            deleted_count = db.query(UserActivity).filter(
                UserActivity.created_at < cutoff_date
            ).delete()
            
            db.commit()
            print(f"✅ {deleted_count} eski aktivite silindi")
            return deleted_count
        except Exception as e:
            db.rollback()
            print(f"Temizleme hatası: {e}")
            return 0
        finally:
            db.close()

# DatabaseManager instance'ı oluştur
db_manager = DatabaseManager()

# Test fonksiyonu
def test_database():
    """Database bağlantısını test eder"""
    try:
        db = db_manager.get_session()
        # Basit sorgu
        user_count = db.query(User).count()
        movie_count = db.query(Movie).count()
        
        print(f"✅ Database bağlantısı başarılı!")
        print(f"👤 Toplam kullanıcı: {user_count}")
        print(f"🎬 Toplam film: {movie_count}")
        
        db.close()
        return True
    except Exception as e:
        print(f"❌ Database bağlantı hatası: {e}")
        return False

def ensure_database_exists():
    """Database'in var olduğundan emin ol"""
    import os
    if not os.path.exists("movie_recommendation.db"):
        print("⚠️ Database dosyası bulunamadı, oluşturuluyor...")
        create_database()
    else:
        print("✅ Database dosyası mevcut")
if __name__ == "__main__":
    print("🗄️ Database başlatılıyor...")
    create_database()
    
    print("\n🧪 Database testi yapılıyor...")
    test_database()
    
    print("\n📊 Database istatistikleri:")
    stats = db_manager.get_database_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
