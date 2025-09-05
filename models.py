from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime

# SQLAlchemy 2.0 uyumlu
Base = declarative_base()

# Database Configuration
DATABASE_PATH = 'movielens_100k.db'
DATABASE_URL = f'sqlite:///{DATABASE_PATH}'



# Engine ve SessionLocal oluştur
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False},
    echo=False  # SQL logları için True yapabilirsin
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Database dependency function
def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class Movie(Base):
    """MovieLens filmler tablosu"""
    __tablename__ = "movies"
    
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    release_date = Column(String)
    imdb_url = Column(String)
    genres = Column(String)  # Virgülle ayrılmış türler
    
    # Genre flags (MovieLens binary indicators)
    unknown = Column(Integer, default=0)
    action = Column(Integer, default=0)
    adventure = Column(Integer, default=0)
    animation = Column(Integer, default=0)
    children = Column(Integer, default=0)
    comedy = Column(Integer, default=0)
    crime = Column(Integer, default=0)
    documentary = Column(Integer, default=0)
    drama = Column(Integer, default=0)
    fantasy = Column(Integer, default=0)
    film_noir = Column(Integer, default=0)
    horror = Column(Integer, default=0)
    musical = Column(Integer, default=0)
    mystery = Column(Integer, default=0)
    romance = Column(Integer, default=0)
    sci_fi = Column(Integer, default=0)
    thriller = Column(Integer, default=0)
    war = Column(Integer, default=0)
    western = Column(Integer, default=0)
    
    # Hesaplanmış istatistikler
    avg_rating = Column(Float, default=0.0)
    rating_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    ratings = relationship("Rating", back_populates="movie")
    interactions = relationship("UserInteraction", back_populates="movie")
    watchlist_items = relationship("Watchlist", back_populates="movie")
    analytics = relationship("UserAnalytics", back_populates="movie")
    
    def __repr__(self):
        return f"<Movie(id={self.id}, title='{self.title}')>"
    
    @property
    def genre_list(self):
        """Türleri liste olarak döndür"""
        return self.genres.split(',') if self.genres else []
    
    @property
    def is_popular(self):
        """Popüler film mi kontrol et"""
        return self.rating_count >= 50 and self.avg_rating >= 3.5

class MovieLensUser(Base):
    """MovieLens orijinal kullanıcıları"""
    __tablename__ = "movielens_users"
    
    id = Column(Integer, primary_key=True)
    age = Column(Integer)
    gender = Column(String)
    occupation = Column(String)
    zip_code = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<MovieLensUser(id={self.id}, age={self.age}, gender='{self.gender}')>"

class AppUser(Base):
    """Uygulama kullanıcıları"""
    __tablename__ = "app_users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True)
    hashed_password = Column(String, nullable=False)
    age = Column(Integer)
    gender = Column(String)
    favorite_genres = Column(String)  # Virgülle ayrılmış
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    interactions = relationship("UserInteraction", back_populates="user")
    preferences = relationship("UserPreference", back_populates="user", uselist=False)
    watchlist_items = relationship("Watchlist", back_populates="user")
    
    def __repr__(self):
        return f"<AppUser(id={self.id}, username='{self.username}')>"
    
    @property
    def favorite_genre_list(self):
        """Favori türleri liste olarak döndür"""
        return self.favorite_genres.split(',') if self.favorite_genres else []

class Rating(Base):
    """Film puanlamaları - hem MovieLens hem App kullanıcıları"""
    __tablename__ = "ratings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    movie_id = Column(Integer, ForeignKey('movies.id'), nullable=False)
    rating = Column(Float, nullable=False)
    timestamp = Column(Integer)  # Unix timestamp (MovieLens format)
    user_type = Column(String, default='movielens')  # 'movielens' or 'app'
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    movie = relationship("Movie", back_populates="ratings")
    
    def __repr__(self):
        return f"<Rating(user_id={self.user_id}, movie_id={self.movie_id}, rating={self.rating})>"
    
    @property
    def is_positive(self):
        """Pozitif puan mı (4+ yıldız)"""
        return self.rating >= 4.0

class Genre(Base):
    """Film türleri"""
    __tablename__ = "genres"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    
    def __repr__(self):
        return f"<Genre(id={self.id}, name='{self.name}')>"

class UserInteraction(Base):
    """Kullanıcı etkileşimleri (favoriler, görüntülemeler, vb.)"""
    __tablename__ = "user_interactions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('app_users.id'), nullable=False)
    movie_id = Column(Integer, ForeignKey('movies.id'))
    interaction_type = Column(String, nullable=False)  # 'favorite', 'view', 'search', 'click'
    extra_data = Column(Text)  # JSON string for extra data
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("AppUser", back_populates="interactions")
    movie = relationship("Movie", back_populates="interactions")
    
    def __repr__(self):
        return f"<UserInteraction(user_id={self.user_id}, type='{self.interaction_type}')>"

class UserPreference(Base):
    """Kullanıcı tercihleri"""
    __tablename__ = "user_preferences"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('app_users.id'), nullable=False, unique=True)
    favorite_genres = Column(String)  # Virgülle ayrılmış
    preferred_year_range = Column(String)  # "1990-2020"
    min_rating = Column(Float)
    max_rating = Column(Float)
    preferred_duration = Column(String)  # "short", "medium", "long"
    exclude_genres = Column(String)  # Virgülle ayrılmış
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("AppUser", back_populates="preferences")
    
    def __repr__(self):
        return f"<UserPreference(user_id={self.user_id}, genres='{self.favorite_genres}')>"

class Watchlist(Base):
    """Kullanıcı izleme listesi"""
    __tablename__ = "watchlist"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('app_users.id'), nullable=False)
    movie_id = Column(Integer, ForeignKey('movies.id'), nullable=False)
    status = Column(String, default='to_watch')  # 'to_watch', 'watching', 'watched'
    added_at = Column(DateTime, default=datetime.utcnow)
    watched_at = Column(DateTime)
    
    # Relationships
    user = relationship("AppUser", back_populates="watchlist_items")
    movie = relationship("Movie", back_populates="watchlist_items")
    
    def __repr__(self):
        return f"<Watchlist(user_id={self.user_id}, movie_id={self.movie_id}, status='{self.status}')>"

class UserAnalytics(Base):
    """Kullanıcı aktivite analitiği"""
    __tablename__ = "user_analytics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    user_type = Column(String, default='app')  # 'app' or 'movielens'
    action_type = Column(String, nullable=False)  # 'view', 'rate', 'search', 'recommend'
    movie_id = Column(Integer, ForeignKey('movies.id'))
    details = Column(Text)  # JSON string
    session_id = Column(String)
    ip_address = Column(String)
    user_agent = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    movie = relationship("Movie", back_populates="analytics")
    
    def __repr__(self):
        return f"<UserAnalytics(user_id={self.user_id}, action='{self.action_type}')>"

# Backward compatibility - API için User alias
User = AppUser

# Database creation and initialization functions
def create_database():
    """Database ve tabloları oluştur"""
    from sqlalchemy import create_engine
    import os
    
    DATABASE_PATH = 'movie_recommendation.db'
    DATABASE_URL = f'sqlite:///{DATABASE_PATH}'
    
    try:
        # SQLAlchemy engine oluştur
        engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
        
        # Tüm tabloları oluştur
        Base.metadata.create_all(bind=engine)
        
        print("✅ Database tables created successfully!")
        print(f"📁 Database path: {DATABASE_PATH}")
        
        # Mevcut tabloları listele
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"📋 Created tables: {', '.join(tables)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        return False

def create_test_data():
    """Test verilerini oluştur"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import os
    
    DATABASE_PATH = 'movie_recommendation.db'
    DATABASE_URL = f'sqlite:///{DATABASE_PATH}'
    
    if not os.path.exists(DATABASE_PATH):
        print("❌ Database not found! Creating database first...")
        if not create_database():
            return False
    
    try:
        # Password hash function import
        try:
            from auth import get_password_hash
        except ImportError:
            import hashlib
            def get_password_hash(password):
                return hashlib.sha256(password.encode()).hexdigest()
        
        # Database session oluştur
        engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        # Mevcut veri kontrolü
        existing_users = db.query(AppUser).count()
        existing_movies = db.query(Movie).count()
        
        if existing_users > 0:
            print(f"ℹ️ Database already has {existing_users} users and {existing_movies} movies")
            db.close()
            return True
        
        # Test kullanıcıları oluştur
        test_users = [
            AppUser(
                username="admin",
                email="admin@test.com",
                hashed_password=get_password_hash("admin123"),
                age=30,
                gender="M",
                favorite_genres="Action,Sci-Fi,Thriller"
            ),
            AppUser(
                username="testuser",
                email="user@test.com",
                hashed_password=get_password_hash("test123"),
                age=25,
                gender="F",
                favorite_genres="Drama,Romance,Comedy"
            ),
            AppUser(
                username="moviefan",
                email="fan@test.com",
                hashed_password=get_password_hash("fan123"),
                age=35,
                gender="M",
                favorite_genres="Crime,Mystery,Drama"
            )
        ]
        
        for user in test_users:
            db.add(user)
        
        # Test filmleri oluştur
        test_movies = [
            Movie(
                id=1,
                title="The Matrix (1999)",
                release_date="1999",
                genres="Action,Sci-Fi",
                action=1,
                sci_fi=1,
                avg_rating=8.7,
                rating_count=1500,
                imdb_url="http://us.imdb.com/M/title-exact?Matrix%2C%20The%20(1999)"
            ),
            Movie(
                id=2,
                title="Titanic (1997)",
                release_date="1997",
                genres="Drama,Romance",
                drama=1,
                romance=1,
                avg_rating=7.8,
                rating_count=2000,
                imdb_url="http://us.imdb.com/Title?Titanic+(1997)"
            ),
            Movie(
                id=3,
                title="The Godfather (1972)",
                release_date="1972",
                genres="Crime,Drama",
                crime=1,
                drama=1,
                                avg_rating=9.2,
                rating_count=3000,
                imdb_url="http://us.imdb.com/Title?Godfather+(1972)"
            ),
            Movie(
                id=4,
                title="Pulp Fiction (1994)",
                release_date="1994",
                genres="Crime,Drama,Thriller",
                crime=1,
                drama=1,
                thriller=1,
                avg_rating=8.9,
                rating_count=2500,
                imdb_url="http://us.imdb.com/Title?Pulp+Fiction+(1994)"
            ),
            Movie(
                id=5,
                title="The Dark Knight (2008)",
                release_date="2008",
                genres="Action,Crime,Drama",
                action=1,
                crime=1,
                drama=1,
                avg_rating=9.0,
                rating_count=2800,
                imdb_url="http://us.imdb.com/title/tt0468569/"
            ),
            Movie(
                id=6,
                title="Forrest Gump (1994)",
                release_date="1994",
                genres="Comedy,Drama,Romance",
                comedy=1,
                drama=1,
                romance=1,
                avg_rating=8.8,
                rating_count=2200,
                imdb_url="http://us.imdb.com/Title?Forrest+Gump+(1994)"
            ),
            Movie(
                id=7,
                title="The Shawshank Redemption (1994)",
                release_date="1994",
                genres="Crime,Drama",
                crime=1,
                drama=1,
                avg_rating=9.3,
                rating_count=2600,
                imdb_url="http://us.imdb.com/Title?Shawshank+Redemption%2C+The+(1994)"
            ),
            Movie(
                id=8,
                title="Star Wars (1977)",
                release_date="1977",
                genres="Action,Adventure,Fantasy,Sci-Fi",
                action=1,
                adventure=1,
                fantasy=1,
                sci_fi=1,
                avg_rating=8.7,
                rating_count=2400,
                imdb_url="http://us.imdb.com/Title?Star+Wars+(1977)"
            ),
            Movie(
                id=9,
                title="Goodfellas (1990)",
                release_date="1990",
                genres="Crime,Drama",
                crime=1,
                drama=1,
                avg_rating=8.7,
                rating_count=1800,
                imdb_url="http://us.imdb.com/Title?Goodfellas+(1990)"
            ),
            Movie(
                id=10,
                title="Casablanca (1942)",
                release_date="1942",
                genres="Drama,Romance,War",
                drama=1,
                romance=1,
                war=1,
                avg_rating=8.5,
                rating_count=1600,
                imdb_url="http://us.imdb.com/Title?Casablanca+(1942)"
            )
        ]
        
        for movie in test_movies:
            db.add(movie)
        
        # Test türleri oluştur
        test_genres = [
            Genre(name="Action"),
            Genre(name="Adventure"),
            Genre(name="Animation"),
            Genre(name="Children"),
            Genre(name="Comedy"),
            Genre(name="Crime"),
            Genre(name="Documentary"),
            Genre(name="Drama"),
            Genre(name="Fantasy"),
            Genre(name="Film-Noir"),
            Genre(name="Horror"),
            Genre(name="Musical"),
            Genre(name="Mystery"),
            Genre(name="Romance"),
            Genre(name="Sci-Fi"),
            Genre(name="Thriller"),
            Genre(name="War"),
            Genre(name="Western")
        ]
        
        for genre in test_genres:
            db.add(genre)
        
        # Test puanlamaları oluştur
        test_ratings = [
            Rating(user_id=1, movie_id=1, rating=5.0, user_type='app'),
            Rating(user_id=1, movie_id=3, rating=5.0, user_type='app'),
            Rating(user_id=1, movie_id=4, rating=4.5, user_type='app'),
            Rating(user_id=2, movie_id=2, rating=4.0, user_type='app'),
            Rating(user_id=2, movie_id=6, rating=4.5, user_type='app'),
            Rating(user_id=2, movie_id=10, rating=4.0, user_type='app'),
            Rating(user_id=3, movie_id=3, rating=5.0, user_type='app'),
            Rating(user_id=3, movie_id=7, rating=5.0, user_type='app'),
            Rating(user_id=3, movie_id=9, rating=4.5, user_type='app'),
        ]
        
        for rating in test_ratings:
            db.add(rating)
        
        # Test etkileşimleri oluştur
        test_interactions = [
            UserInteraction(user_id=1, movie_id=1, interaction_type='favorite'),
            UserInteraction(user_id=1, movie_id=3, interaction_type='favorite'),
            UserInteraction(user_id=2, movie_id=2, interaction_type='favorite'),
            UserInteraction(user_id=2, movie_id=6, interaction_type='favorite'),
            UserInteraction(user_id=3, movie_id=7, interaction_type='favorite'),
        ]
        
        for interaction in test_interactions:
            db.add(interaction)
        
        # Commit all changes
        db.commit()
        
        # Sonuçları yazdır
        user_count = db.query(AppUser).count()
        movie_count = db.query(Movie).count()
        rating_count = db.query(Rating).count()
        genre_count = db.query(Genre).count()
        interaction_count = db.query(UserInteraction).count()
        
        print("✅ Test data created successfully!")
        print(f"👥 Users: {user_count}")
        print(f"🎬 Movies: {movie_count}")
        print(f"⭐ Ratings: {rating_count}")
        print(f"🎭 Genres: {genre_count}")
        print(f"💝 Interactions: {interaction_count}")
        
        db.close()
        return True
        
    except Exception as e:
        if 'db' in locals():
            db.rollback()
            db.close()
        print(f"❌ Error creating test data: {e}")
        return False

def initialize_database():
    """Database'i tamamen hazırla"""
    print("🔄 Initializing database...")
    
    # 1. Database oluştur
    if not create_database():
        return False
    
    # 2. Test verilerini ekle
    if not create_test_data():
        return False
    
    print("🎉 Database initialization completed!")
    return True

# Helper functions for models
def get_movie_by_id(db, movie_id: int):
    """ID ile film getir"""
    return db.query(Movie).filter(Movie.id == movie_id).first()

def get_app_user_by_username(db, username: str):
    """Username ile app kullanıcısı getir"""
    return db.query(AppUser).filter(AppUser.username == username).first()

def get_user_by_username(db, username: str):
    """Username ile kullanıcı getir (alias)"""
    return get_app_user_by_username(db, username)

def get_user_ratings(db, user_id: int, user_type: str = 'app'):
    """Kullanıcının puanlamalarını getir"""
    return db.query(Rating).filter(
        Rating.user_id == user_id,
        Rating.user_type == user_type
    ).all()

def get_movie_ratings(db, movie_id: int):
    """Filmin tüm puanlamalarını getir"""
    return db.query(Rating).filter(Rating.movie_id == movie_id).all()

def get_popular_movies(db, limit: int = 20, min_ratings: int = 50):
    """Popüler filmleri getir"""
    return db.query(Movie).filter(
        Movie.rating_count >= min_ratings
    ).order_by(
        Movie.avg_rating.desc(),
        Movie.rating_count.desc()
    ).limit(limit).all()

def get_movies_by_genre(db, genre: str, limit: int = 20):
    """Türe göre film getir"""
    return db.query(Movie).filter(
        Movie.genres.ilike(f"%{genre}%")
    ).order_by(Movie.avg_rating.desc()).limit(limit).all()

def get_user_favorites(db, user_id: int):
    """Kullanıcının favori filmlerini getir"""
    return db.query(UserInteraction, Movie).join(
        Movie, UserInteraction.movie_id == Movie.id
    ).filter(
        UserInteraction.user_id == user_id,
        UserInteraction.interaction_type == 'favorite'
    ).all()

def get_all_genres(db):
    """Tüm türleri getir"""
    genres = db.query(Genre).all()
    return [genre.name for genre in genres]

def search_movies(db, query: str, limit: int = 20):
    """Film ara"""
    search_term = f"%{query}%"
    return db.query(Movie).filter(
        Movie.title.ilike(search_term)
    ).order_by(Movie.avg_rating.desc()).limit(limit).all()

def get_user_by_email(db, email: str):
    """Email ile kullanıcı getir"""
    return db.query(AppUser).filter(AppUser.email == email).first()

def create_user(db, username: str, email: str, hashed_password: str, **kwargs):
    """Yeni kullanıcı oluştur"""
    try:
        user = AppUser(
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
        raise e

# Model validation functions
def validate_rating(rating: float) -> bool:
    """Rating değerini doğrula"""
    return 0.5 <= rating <= 5.0

def validate_genre(genre: str, db) -> bool:
    """Tür var mı kontrol et"""
    return db.query(Genre).filter(Genre.name == genre).first() is not None

def validate_user_data(username: str, email: str, password: str) -> tuple:
    """Kullanıcı verilerini doğrula"""
    errors = []
    
    if not username or len(username) < 3:
        errors.append("Username en az 3 karakter olmalı")
    
    if not email or '@' not in email:
        errors.append("Geçerli bir email adresi giriniz")
    
    if not password or len(password) < 6:
        errors.append("Şifre en az 6 karakter olmalı")
    
    return len(errors) == 0, errors

# Database info functions
def get_database_info():
    """Database bilgilerini getir"""
    import os
    DATABASE_PATH = 'movie_recommendation.db'
    
    if os.path.exists(DATABASE_PATH):
        size = os.path.getsize(DATABASE_PATH)
        return {
            "exists": True,
            "path": DATABASE_PATH,
            "size": size,
            "size_mb": round(size / (1024 * 1024), 2)
        }
    else:
        return {
            "exists": False,
            "path": DATABASE_PATH,
            "size": 0,
            "size_mb": 0
        }

# Export all models
__all__ = [
    'Base',
    'Movie',
    'MovieLensUser',
    'AppUser',
    'User',  # Alias ekledik
    'Rating',
    'Genre',
    'UserInteraction',
    'UserPreference',
    'Watchlist',
    'UserAnalytics',
    # Database functions
    'create_database',
    'create_test_data',
    'initialize_database',
    # Helper functions
    'get_movie_by_id',
    'get_app_user_by_username',
    'get_user_by_username',
    'get_user_ratings',
    'get_movie_ratings',
    'get_popular_movies',
    'get_movies_by_genre',
    'get_user_favorites',
    'get_all_genres',
    'search_movies',
    'get_user_by_email',
    'create_user',
    'get_database_info',
    # Validation functions
    'validate_rating',
    'validate_genre',
    'validate_user_data'
]

# En sona ekle:
if __name__ == "__main__":
    print("🔄 Testing models.py...")
    
    # Database oluştur
    create_database()
    create_test_data()
    
    # Test et
    db = SessionLocal()
    movies = db.query(Movie).count()
    users = db.query(AppUser).count()
    db.close()
    
    print(f"✅ Database test: {movies} movies, {users} users")
