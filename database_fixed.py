from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship  # Düzeltme 1
from datetime import datetime

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
    extra_data = Column(Text, nullable=True)  # Düzeltme 2: metadata → extra_data
    
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

if __name__ == "__main__":
    create_database()