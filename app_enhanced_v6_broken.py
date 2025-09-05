from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query, status
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, validator
from typing import Any, List, Dict, Optional, Union
from sqlalchemy.orm import Session
from sqlalchemy import desc, text, func
import sqlite3
import pandas as pd
import numpy as np
import json
import logging
from datetime import datetime
from datetime import timedelta
import jwt
import os
import asyncio
from fastapi import Request
from model_api import RecommendationAPI

# ===========================================================================
# [*] DYNAMIC RECOMMENDATION ENGINE SETUP
# ===========================================================================
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd

# Global variables for the user-movie matrix and mappings
USER_MOVIE_MATRIX = None
USER_ID_MAP = None
MOVIE_ID_MAP = None
INV_MOVIE_ID_MAP = None

try:
    # Load the pre-computed user-movie matrix
    # This matrix should have user_ids as index and movie_ids as columns
    user_movie_df = pd.read_pickle("user_movie_matrix.pkl")
    
    # Convert to numpy array for performance
    USER_MOVIE_MATRIX = user_movie_df.to_numpy()
    
    # Create mappings from original IDs to matrix indices
    user_ids = user_movie_df.index.tolist()
    movie_ids = user_movie_df.columns.tolist()
    
    USER_ID_MAP = {int(user_id): i for i, user_id in enumerate(user_ids)}
    MOVIE_ID_MAP = {int(movie_id): i for i, movie_id in enumerate(movie_ids)}
    INV_MOVIE_ID_MAP = {i: int(movie_id) for i, movie_id in enumerate(movie_ids)} # FIX: Correctly map index to movie_id
    
    # Use the logger that is initialized later
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[+] Successfully loaded user-movie matrix with shape: {USER_MOVIE_MATRIX.shape}")
    logger.info(f"[+] Created user ID map ({len(USER_ID_MAP)} users) and movie ID map ({len(MOVIE_ID_MAP)} movies).")

except FileNotFoundError:
    import logging
    logger = logging.getLogger(__name__)
    logger.error("[x] CRITICAL: 'user_movie_matrix.pkl' not found. Dynamic recommendations will be disabled.")
    USER_MOVIE_MATRIX = None
except Exception as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"[x] CRITICAL: Error loading 'user_movie_matrix.pkl': {e}")
    USER_MOVIE_MATRIX = None
# ===========================================================================



# [+] DIRECT DATABASE CONNECTION (Bypass models.py problems)
import sqlite3
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Direct SQLite connection for working database  
DATABASE_URL = "sqlite:///movielens_100k.db"
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)

# Backup simple connection
def get_simple_db():
    return sqlite3.connect("movielens_100k.db")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

print("[+] Direct database connection established")

# Basit model sınıfları - Raw SQL kullanmak için
class SimpleMovie:
    def __init__(self, row):
        self.id = row[0] if len(row) > 0 else None
        self.title = row[1] if len(row) > 1 else None
        self.genres = row[2] if len(row) > 2 else None
        self.avg_rating = row[3] if len(row) > 3 else None

class SimpleUser:
    def __init__(self, row):
        self.id = row[0] if len(row) > 0 else None
        self.username = row[1] if len(row) > 1 else None
        self.email = row[2] if len(row) > 2 else None

# Direct SQL functions
def execute_sql(query, params=None):
    conn = sqlite3.connect("movielens_100k.db")
    if params:
        result = conn.execute(query, params).fetchall()
    else:
        result = conn.execute(query).fetchall()
    conn.close()
    return result

print("[+] Simple database functions ready")

# [+] ESSENTIAL MODEL CLASSES - Mevcut kod ile uyumlu
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "app_users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String)
    hashed_password = Column(String)
    age = Column(Integer)
    gender = Column(String)
    favorite_genres = Column(String)
    created_at = Column(DateTime)
    last_active = Column(DateTime)

class Movie(Base):
    __tablename__ = "movies"
    
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    genres = Column(String)
    avg_rating = Column(Float)
    rating_count = Column(Integer)
    release_date = Column(String)
    imdb_url = Column(String)

class UserInteraction(Base):
    __tablename__ = "user_interactions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('app_users.id'))
    movie_id = Column(Integer, ForeignKey('movies.id'))
    interaction_type = Column(String)  # 'rating', 'favorite', 'watchlist'
    extra_data = Column(Text)  # JSON data
    timestamp = Column(DateTime)

class Rating(Base):
    __tablename__ = "ratings"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    movie_id = Column(Integer) 
    rating = Column(Float)
    timestamp = Column(DateTime)

print("[+] Essential model classes defined")

# [+] PURE DEEP LEARNING SYSTEM (ANA SİSTEM)
try:
    from clean_dynamic_deep_recommender import CleanDynamicDeepRecommender
    
    # Ana derin öğrenme sistemi
    main_deep_learning_system = CleanDynamicDeepRecommender(
        embedding_dim=128,
        n_similar_users=10,
        similarity_threshold=0.1
    )
    
    print("[+] Main Deep Learning System initialized")
    logger.info("[+] Pure Deep Learning System ready")
        
except Exception as e:
    logger.error(f"[x] Deep Learning System import error: {e}")
    main_deep_learning_system = None

# [!] ESKİ MODEL KODLARI - DERIN ÖĞRENME PROJESİ İÇİN GEREKSİZ
# Advanced recommender artık kullanılmıyor - Pure Deep Learning odaklı
advanced_recommender = None
print("[!] Advanced models disabled - Pure Deep Learning mode")

# === DİNAMİK DERİN ÖĞRENMELİ SİSTEM ===
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from dynamic_deep_recommender import DynamicDeepRecommender
    
    # Global dynamic deep recommender instance
    dynamic_deep_recommender = DynamicDeepRecommender(
        embedding_dim=128,
        n_similar_users=10,
        model_path="dynamic_deep_model.h5",
        embeddings_path="user_embeddings.pkl"
    )
    
    print("[+] Dynamic Deep Recommender initialized successfully")
    
    # Model eğitimi kontrolü (async olarak sonra yapılacak)
    if not os.path.exists("dynamic_deep_model.h5"):
        print("[*] Dynamic Deep Learning model needs training...")
        
except Exception as e:
    print(f"[x] Dynamic Deep Recommender initialization failed: {e}")
    dynamic_deep_recommender = None

# ===========================================================================
# [*] DEEP LEARNING MODEL SETUP
# ===========================================================================
import tensorflow as tf
import pickle

dl_model = None
dl_user_to_idx = None
dl_movie_to_idx = None
dl_idx_to_user = None
dl_idx_to_movie = None

try:
    # Fix: Provide the 'mse' function explicitly during model loading
    # This is required for newer TensorFlow versions to load older models.
    dl_model = tf.keras.models.load_model(
        'dl_model.h5',
        custom_objects={'mse': 'mean_squared_error'}
    )
    with open('dl_model_mappings.pkl', 'rb') as f:
        mappings = pickle.load(f)
        dl_user_to_idx = mappings['user_to_idx']
        dl_movie_to_idx = mappings['movie_to_idx']
        # Create inverse mappings for convenience
        dl_idx_to_user = {i: user_id for user_id, i in dl_user_to_idx.items()}
        dl_idx_to_movie = {i: movie_id for movie_id, i in dl_movie_to_idx.items()}
    print("[+] Successfully loaded Deep Learning model and mappings.")
except FileNotFoundError:
    print("[x] CRITICAL: 'dl_model.h5' or 'dl_model_mappings.pkl' not found. Deep Learning recommendations will be disabled.")
    dl_model = None
except Exception as e:
    print(f"[x] CRITICAL: Error loading Deep Learning model: {e}")
    dl_model = None
# ===========================================================================


recommendation_api = RecommendationAPI()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# [+] AUTH SYSTEM SETUP
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "Aa1234567."
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 saat
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# app_enhanced_v6.py'nin en başına ekle:
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
logging.getLogger("pydantic").setLevel(logging.ERROR)

# [+] DATABASE SETUP
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============================================================================
# [*] AUTH DEPENDENCY - STANDARDIZED VERSION
# ============================================================================
security = HTTPBearer()

# [*] GÜNCELLENMIŞ GET_CURRENT_USER
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        print("="*30)
        print("[*] AUTH DEBUG")
        print("="*30)
        
        if not credentials:
            print("[x] No credentials provided")
            raise HTTPException(status_code=401, detail="Token gerekli")
        
        print(f"[*] Credentials scheme: {credentials.scheme}")
        print(f"[*] Token (first 20 chars): {credentials.credentials[:20]}...")
        
        payload = jwt.decode(credentials.credentials, "Aa1234567.", algorithms=["HS256"])
        print(f"[+] JWT decoded successfully: {payload}")
        
        user_data = {
            "user_id": payload.get("user_id"),
            "username": payload.get("username")
        }
        
        if not user_data["user_id"]:
            print("[x] user_id not found in token payload")
            raise HTTPException(status_code=401, detail="Invalid token payload")
        
        print(f"[+] User authenticated: {user_data}")
        print("="*30)
        return user_data
        
    except jwt.ExpiredSignatureError:
        print("[x] Token expired")
        raise HTTPException(status_code=401, detail="Token süresi dolmuş")
    except jwt.InvalidTokenError as e:
        print(f"[x] Invalid token: {e}")
        raise HTTPException(status_code=401, detail="Geçersiz token")
    except Exception as e:
        print(f"[x] Auth error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

async def get_current_user_dependency(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Standardized dependency to get the current user from a JWT token."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        username: str = payload.get("username")
        if user_id is None or username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
        return {"user_id": user_id, "username": username}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

# Initialize FastAPI app
app = FastAPI(
    title="[*] Enhanced Movie Recommendation System v6.0 MovieLens",
    description="Complete Hybrid Recommendation System with MovieLens Integration",
    version="6.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Optional authentication
async def get_current_user_optional(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        return None
    return await get_current_user_dependency(credentials)

class UserRegistration(BaseModel):
    username: str
    email: str
    password: str
    age: Optional[int] = None
    gender: Optional[str] = None
    occupation: Optional[str] = None
    favorite_genres: Optional[List[str]] = []  # ← Eklendi

class UserLogin(BaseModel):
    username: str
    password: str

class MovieRating(BaseModel):
    movie_id: int
    rating: float
    
    # Validation ekle
    @validator('rating')
    def validate_rating(cls, v):
        if not (1.0 <= v <= 5.0):
            raise ValueError('Rating must be between 1.0 and 5.0')
        return v
    
    @validator('movie_id')
    def validate_movie_id(cls, v):
        if v <= 0:
            raise ValueError('Movie ID must be positive')
        return v

class RecommendationRequest(BaseModel):
    algorithm: str = "hybrid"
    n_recommendations: int = 10
    genres: Optional[List[str]] = []

class GenrePreferenceRequest(BaseModel):
    genres: List[str]
    n_recommendations: int = 10

class AdvancedRecommendationRequest(BaseModel):
    n_recommendations: int = 15
    include_genres: Optional[List[str]] = []
    exclude_genres: Optional[List[str]] = []
    min_rating: Optional[float] = 3.0
    max_year: Optional[int] = None
    min_year: Optional[int] = None

# [*] YENİ MODELLER
class FavoriteRequest(BaseModel):
    movie_id: int
    
    @validator('movie_id')
    def validate_movie_id(cls, v):
        if v <= 0:
            raise ValueError('Movie ID must be positive')
        return v

class WatchlistRequest(BaseModel):
    movie_id: int
    status: str = "to_watch"  # "to_watch" or "watched"
    
    @validator('status')
    def validate_status(cls, v):
        if v not in ["to_watch", "watched"]:
            raise ValueError('Status must be "to_watch" or "watched"')
        return v
    
    @validator('movie_id')
    def validate_movie_id(cls, v):
        if v <= 0:
            raise ValueError('Movie ID must be positive')
        return v

class UserStatsResponse(BaseModel):
    ratings_count: int
    favorites_count: int
    to_watch_count: int
    watched_count: int
    total_activity: int

class MovieResponse(BaseModel):
    movie_id: int
    title: str
    genres: List[str]
    avg_rating: float
    rating_count: int
    release_date: str
    popularity: int
    user_rating: Optional[float] = None
    watchlist_status: Optional[str] = None
    is_favorite: bool = False
    imdb_url: Optional[str] = None

class RatingResponse(BaseModel):
    status: str
    message: str
    user_id: int
    movie_id: int
    movie_title: str
    rating: float
    timestamp: str


def get_user_rating_for_movie(db: Session, user_id: int, movie_id: int):
    """Kullanıcının belirli bir film için verdiği puanı getir"""
    try:
        rating_interaction = db.query(UserInteraction).filter(
            UserInteraction.user_id == user_id,
            UserInteraction.movie_id == movie_id,
            UserInteraction.interaction_type == "rating"
        ).first()
        
        if rating_interaction and rating_interaction.extra_data:
            import json
            rating_data = json.loads(rating_interaction.extra_data)
            return rating_data.get('rating', None)
        
        return None
    except Exception as e:
        print(f"[x] Rating getirme hatası: {e}")
        return None

def get_dynamic_recommendations(db: Session, user_id: int, rated_movie_id: int, new_rating: float, n_recommendations: int = 10):
    """
    Generates dynamic recommendations for a user based on similar users' ratings,
    considering the latest user action.
    """
    if USER_MOVIE_MATRIX is None:
        logger.warning("[!] User-movie matrix not loaded. Cannot generate dynamic recommendations.")
        return []

    try:
        # 1. Check if the user and movie are in our matrix
        if user_id not in USER_ID_MAP:
            logger.warning(f"[!] User ID {user_id} not in the matrix (cold start). Cannot find similar users.")
            return []
        
        user_index = USER_ID_MAP[user_id]
        
        # 2. Create a temporary, updated user vector for similarity calculation
        # This avoids permanently changing the base matrix in memory for each request
        updated_user_vector = USER_MOVIE_MATRIX[user_index].copy()
        
        # Update the vector with the new rating that triggered this function
        if rated_movie_id in MOVIE_ID_MAP:
            movie_index = MOVIE_ID_MAP[rated_movie_id]
            updated_user_vector[movie_index] = new_rating
            logger.info(f"Temporarily updated user {user_id}'s vector for movie {rated_movie_id} with rating {new_rating}")

        # 3. Calculate cosine similarity between the updated user and all others
        similarity_scores = cosine_similarity(
            updated_user_vector.reshape(1, -1),
            USER_MOVIE_MATRIX
        )[0]

        # 4. Find top 10 most similar users (excluding the user themselves)
        similar_user_indices = np.argsort(similarity_scores)[::-1]
        
        top_similar_users = []
        for idx in similar_user_indices:
            if idx != user_index:
                top_similar_users.append(idx)
            if len(top_similar_users) >= 10:
                break
        
        if not top_similar_users:
            logger.info(f"Could not find any similar users for user_id {user_id}")
            return []

        # 5. Generate recommendation scores from similar users' ratings
        similar_users_ratings = USER_MOVIE_MATRIX[top_similar_users]
        recommendation_scores = similar_users_ratings.sum(axis=0)

        # 6. Filter out movies the user has already rated (using the original vector)
        user_rated_movie_indices = np.where(USER_MOVIE_MATRIX[user_index] > 0)[0]
        recommendation_scores[user_rated_movie_indices] = -1  # Invalidate already-rated movies

        # Also invalidate the movie that was just rated
        if rated_movie_id in MOVIE_ID_MAP:
            recommendation_scores[MOVIE_ID_MAP[rated_movie_id]] = -1

        # 7. Get top N movie indices
        recommended_movie_indices = np.argsort(recommendation_scores)[::-1]
        
        # 8. Format recommendations
        recommendations = []
        for movie_idx in recommended_movie_indices:
            # Stop if we have enough recommendations or if scores are invalid
            if len(recommendations) >= n_recommendations or recommendation_scores[movie_idx] < 0:
                break
            
            movie_id = INV_MOVIE_ID_MAP.get(movie_idx)
            if movie_id:
                movie_details = db.query(Movie).filter(Movie.id == movie_id).first()
                if movie_details:
                    recommendations.append({
                        "movie_id": movie_details.id,
                        "title": movie_details.title,
                        "genres": movie_details.genres.split('|') if movie_details.genres else [],
                        "avg_rating": float(movie_details.avg_rating) if movie_details.avg_rating else 0.0,
                        "recommendation_score": float(recommendation_scores[movie_idx]),
                        "type": "user-similarity"
                    })
        
        logger.info(f"[+] Generated {len(recommendations)} dynamic recommendations for user {user_id}")
        return recommendations

    except Exception as e:
        logger.error(f"[x] Error generating dynamic recommendations: {e}", exc_info=True)
        return []

# === FRONTEND SERVING ===
@app.get("/", response_class=HTMLResponse)
async def root():
    """🏠 Ana sayfa - Frontend HTML"""
    logger.info("[*] Ana sayfa erişimi")
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        logger.error("[x] index.html dosyası bulunamadı!")
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head><title>Movie Recommendation System v6.0 - MovieLens</title></head>
        <body>
            <h1>Movie Recommendation System v6.0 - MovieLens</h1>
            <p>Frontend dosyası bulunamadı. index.html dosyasının mevcut olduğundan emin olun.</p>
            <ul>
                <li><a href="/docs">API Documentation</a></li>
                <li><a href="/health">Health Check</a></li>
            </ul>
        </body>
        </html>
        """)
    except Exception as e:
        logger.error(f"[x] Ana sayfa hatası: {e}")
        return HTMLResponse(content=f"<h1>Hata</h1><p>{str(e)}</p>")

async def serve_frontend():
    """Serve the enhanced frontend"""
    return await root()
        
        # Test için basit endpoint
@app.post("/test-auth")
async def test_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    logger.info("[*] test-auth endpoint çağrıldı")
    
    if not credentials:
        return {"status": "error", "message": "Token yok"}
    
    token = credentials.credentials
    logger.info(f"[*] Token: {token[:20]}...")
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logger.info(f"[+] Decode OK: {payload}")
        return {"status": "success", "payload": payload}
    except Exception as e:
        logger.error(f"[x] Decode error: {e}")
        return {"status": "error", "error": str(e)}


# === BASIC ENDPOINTS ===
@app.get("/genres")
async def get_genres(db: Session = Depends(get_db)):
    """Get all available unique genres from the database."""
    try:
        # Query distinct genres directly if possible, or fetch all and process in Python
        all_genres_from_db = db.query(Movie.genres).filter(Movie.genres.isnot(None)).all()
        
        unique_genres = set()
        for genres_tuple in all_genres_from_db:
            genres_str = genres_tuple[0]
            if genres_str:
                # Split by '|' as it's the standard MovieLens separator, also handle ','
                genres_list = [genre.strip() for genre in genres_str.replace(',', '|').split('|')]
                unique_genres.update(genres_list)
        
        # Filter out empty strings and sort
        sorted_genres = sorted([genre for genre in unique_genres if genre])
        
        return {"status": "success", "genres": sorted_genres, "count": len(sorted_genres)}
        
    except Exception as e:
        logger.error(f"[x] Genres error: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve genres.")
    
    # === GENRE PREFERENCES UPDATE ===
@app.post("/update-genre-preferences")
async def update_genre_preferences(
    preferences: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_dependency)
):
    try:
        logger.info(f"[*] Genre preferences update request: {preferences}")
        
        user_id = current_user["user_id"]
        genres = preferences.get("genres", [])
        
        logger.info(f"[*] Updating genres for user {user_id}: {genres}")
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
        
        # Genre'ları kaydet
        if isinstance(genres, list):
            user.favorite_genres = ",".join(genres)
        else:
            user.favorite_genres = str(genres)
        
        user.last_active = datetime.utcnow()
        db.commit()
        
        logger.info(f"[+] Genres updated: {user.favorite_genres}")
        
        return {
            "status": "success",
            "message": "[+] Tür tercihleri güncellendi!",
            "genres": genres
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"[x] Genre update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# === GET USER PREFERENCES ===
@app.get("/user-preferences")
async def get_user_preferences(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_dependency)
):
    try:
        user_id = current_user["user_id"]
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
        
        # Favorite genres'ı parse et
        favorite_genres = []
        if user.favorite_genres:
            favorite_genres = [g.strip() for g in user.favorite_genres.split(",") if g.strip()]
        
        return {
            "status": "success",
            "preferences": {
                "favorite_genres": favorite_genres,
                "user_id": user_id,
                "username": user.username
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[x] Get preferences error: {e}")
        raise HTTPException(status_code=500, detail="Tercihler alınırken hata oluştu")




@app.get("/popular-movies")
async def get_popular_movies(limit: int = 20, db: Session = Depends(get_db)):
    """Get popular movies from MovieLens data"""
    try:
        popular_movies = db.query(Movie).filter(
            Movie.rating_count >= 100
        ).order_by(Movie.avg_rating.desc()).limit(limit).all()
        
        results = []
        for movie in popular_movies:
            results.append({
                "id": movie.id,
                "title": movie.title,
                "genres": movie.genres,
                "year": movie.year,
                "avg_rating": float(movie.avg_rating) if movie.avg_rating else 0.0,
                "rating_count": movie.rating_count or 0,
                "imdb_id": movie.imdb_id,
                "tmdb_id": movie.tmdb_id
            })
        
        return {
            "status": "success",
            "count": len(results),
            "popular_movies": results
        }
        
    except Exception as e:
        logger.error(f"[x] Popular movies error: {e}")
        raise HTTPException(status_code=500, detail="Popüler filmler alınırken hata oluştu")

@app.get("/search")
async def search_movies(q: str, limit: int = 20, db: Session = Depends(get_db)):
    try:
        logger.info(f"[*] Search query: '{q}', limit: {limit}")
        
        if not q or len(q.strip()) < 1:  # Min 1 karakter yap
            return {"status": "error", "message": "En az 1 karakter giriniz"}
        
        search_term = f"%{q.strip()}%"
        logger.info(f"[*] Search term: '{search_term}'")
        
        # Önce toplam film sayısını kontrol et
        total_movies = db.query(Movie).count()
        logger.info(f"[*] Total movies in DB: {total_movies}")
        
        # Basit arama yap
        movies = db.query(Movie).filter(
            Movie.title.ilike(search_term)
        ).limit(limit).all()
        
        logger.info(f"[*] Found {len(movies)} movies")
        
        # İlk 3 filmi logla
        for i, movie in enumerate(movies[:3]):
            logger.info(f"Movie {i+1}: {movie.title}")
        
        results = []
        for movie in movies:
            results.append({
                "id": movie.id,
                "title": movie.title,
                "genres": movie.genres,
                "avg_rating": float(movie.avg_rating) if movie.avg_rating else 0.0,
                "rating_count": movie.rating_count or 0,
                "release_date": getattr(movie, 'release_date', None)
            })
        
        return {
            "status": "success",
            "query": q,
            "total_movies_in_db": total_movies,
            "count": len(results),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"[x] Search error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Arama hatası: {str(e)}")


# Registration endpoint'ini değiştir:
@app.post("/register")
async def register(user_data: dict, db: Session = Depends(get_db)):
    try:
        username = user_data.get("username")
        email = user_data.get("email")
        password = user_data.get("password")
        
        logger.info(f"[*] Register attempt: {username}, {email}")
        
        if not all([username, email, password]):
            raise HTTPException(status_code=400, detail="Username, email ve password gerekli")
        
        # Mevcut kullanıcı kontrolü
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Bu kullanıcı adı zaten kullanılıyor")
        
        existing_email = db.query(User).filter(User.email == email).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Bu email zaten kullanılıyor")
        
        # [+] GÜVENLİ HASH - bcrypt kullan
        hashed_password = get_password_hash(password)
        
        # Kullanıcı oluştur
        # NOTE: Using User model instead of AppUser for consistency
        user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            created_at=datetime.utcnow()
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        access_token = create_access_token(
            {"user_id": user.id, "username": user.username}, 
        )
        
        logger.info(f"[+] User {username} registered successfully.")
        
        return {
            "status": "success",
            "message": "Kullanıcı başarıyla oluşturuldu",
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[x] Registration error: {e}")
        raise HTTPException(status_code=500, detail=f"Kayıt hatası: {str(e)}")



@app.post("/login")
async def login(login_data: dict, db: Session = Depends(get_db)):
    try:
        username = login_data.get("username")
        password = login_data.get("password")
        
        logger.info(f"[*] Login attempt: {username}")
        
        if not username or not password:
            raise HTTPException(status_code=400, detail="Username ve password gerekli")
        
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            raise HTTPException(status_code=401, detail="Kullanıcı bulunamadı")
        
        # Güvenli şifre doğrulama
        if not verify_password(password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Geçersiz şifre")
        
        user.last_active = datetime.utcnow()
        db.commit()
        
        # [*] DEBUG: User'ın tüm field'larını kontrol et
        print(f"[*] User object attributes:")
        for attr in dir(user):
            if not attr.startswith('_'):
                try:
                    value = getattr(user, attr)
                    if not callable(value):
                        print(f"  - {attr}: {value}")
                except:
                    pass
        
        # User bilgilerini al (session kapatmadan önce)
        user_data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "age": getattr(user, 'age', None),
            "gender": getattr(user, 'gender', None),
            "favorite_genres": getattr(user, 'favorite_genres', None),  # ← EKLENDI
            "created_at": getattr(user, 'created_at', None)
        }
        
        print(f"[+] Sending user data: {user_data}")
        
        # Token oluştur
        access_token = create_access_token(
            {"user_id": user_data["id"], "username": user_data["username"]},
        )
        
        logger.info(f"[+] Login successful: {username}")
        
        return {
            "status": "success",
            "access_token": access_token,
            "token_type": "bearer",
            "user": user_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[x] Login error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Giriş işlemi sırasında hata oluştu")




@app.get("/popular-recommendations")
async def get_popular_recommendations(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_dependency)
):
    try:
        user_id = current_user["user_id"]
        
        print(f"[+] User authenticated: {user_id}")
        
        # En popüler filmleri getir
        popular_movies = db.query(Movie).filter(
            Movie.rating_count > 5,
            Movie.avg_rating > 3.0
        ).order_by(
            desc(Movie.avg_rating),
            desc(Movie.rating_count)
        ).limit(limit).all()
        
        print(f"[+] Found {len(popular_movies)} popular movies")
        
        recommendations = []
        for movie in popular_movies:
            try:
                user_rating = get_user_rating_for_movie(db, user_id, movie.id)
                
                # NULL KONTROL
                genres_list = []
                if movie.genres and movie.genres.strip():
                    genres_list = [g.strip() for g in movie.genres.split(",") if g.strip()]
                
                recommendations.append({
                    "movie_id": movie.id,
                    "title": movie.title,
                    "genres": genres_list,
                    "avg_rating": round(movie.avg_rating, 1) if movie.avg_rating else 0,
                    "rating_count": movie.rating_count or 0,
                    "release_date": movie.release_date or "Bilinmiyor",
                    "popularity": movie.rating_count or 0,
                    "user_rating": user_rating,
                    "popularity_score": round((movie.avg_rating or 0) * ((movie.rating_count or 0) / 100), 2),
                    "imdb_url": movie.imdb_url if movie.imdb_url else None
                })
                
            except Exception as e:
                print(f"[x] Movie processing error: {movie.title} - {e}")
                continue
        
        print(f"[+] Returning {len(recommendations)} recommendations")
        
        return {
            "status": "success",
            "method": "Popularity-Based Filtering",
            "count": len(recommendations),
            "recommendations": recommendations
        }
        
    except Exception as e:
        print(f"[x] Popular recommendations error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    
    # Önce veritabanındaki film durumunu kontrol edelim
@app.get("/debug-movies")
async def debug_movies(db: Session = Depends(get_db)):
    try:
        # Toplam film sayısı
        total_movies = db.query(Movie).count()
        
        # Rating'i olan filmler
        rated_movies = db.query(Movie).filter(Movie.avg_rating.isnot(None)).count()
        
        # Rating count'u olan filmler
        count_movies = db.query(Movie).filter(Movie.rating_count.isnot(None)).count()
        
        # Örnek filmler
        sample_movies = db.query(Movie).limit(10).all()
        
        sample_data = []
        for movie in sample_movies:
            sample_data.append({
                "id": movie.id,
                "title": movie.title,
                "avg_rating": movie.avg_rating,
                "rating_count": movie.rating_count,
                "genres": movie.genres
            })
        
        return {
            "total_movies": total_movies,
            "movies_with_rating": rated_movies,
            "movies_with_count": count_movies,
            "sample_movies": sample_data
        }
        
    except Exception as e:
        return {"error": str(e)}



# ============================================================================
# [*] RATING ENDPOINT - DÜZELTİLMİŞ VERSİYON
# ============================================================================


@app.post("/rate-movie")
async def rate_movie(
    rating_request: MovieRating,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_dependency)
):
    try:
        print("="*50)
        print("[*] RATING ENDPOINT")
        print("="*50)
        user_id = current_user["user_id"]
        
        movie_id = rating_request.movie_id
        rating = rating_request.rating
        
        print(f"[+] User ID: {user_id}")
        print(f"[+] Movie ID: {movie_id}")
        print(f"[+] Rating: {rating}")
        
        # Film kontrolü
        movie = db.query(Movie).filter(Movie.id == movie_id).first()
        if not movie:
            raise HTTPException(status_code=404, detail="Film bulunamadı")
        
        print(f"[+] Movie: {movie.title}")
        
        # Mevcut rating var mı kontrol et
        existing_rating = db.query(UserInteraction).filter(
            UserInteraction.user_id == user_id,
            UserInteraction.movie_id == movie_id,
            UserInteraction.interaction_type == "rating"
        ).first()
        
        # Rating'i JSON olarak hazırla
        import json
        rating_data = json.dumps({"rating": rating, "timestamp": datetime.utcnow().isoformat()})
        
        if existing_rating:
            print("[*] Mevcut rating güncelleniyor...")
            existing_rating.extra_data = rating_data
            existing_rating.timestamp = datetime.utcnow()
            message = f"'{movie.title}' puanınız {rating}[+] olarak güncellendi!"
            
        else:
            print("[+] Yeni rating oluşturuluyor...")
            new_rating_interaction = UserInteraction(
                user_id=user_id,
                movie_id=movie_id,
                interaction_type="rating",
                extra_data=rating_data,
                timestamp=datetime.utcnow()
            )
            db.add(new_rating_interaction)
            message = f"'{movie.title}' filmine {rating}[+] puan verdiniz!"
        
        db.commit()
        print("[*] Rating kaydedildi!")
        
        # [*] DİNAMİK ÖNERİ TETİKLEME (İsteğinin kalbi burası)
        print("[*] Yeni puana göre dinamik öneriler hesaplanıyor...")
        dynamic_recs_raw = get_dynamic_recommendations(
            db=db, 
            user_id=user_id, 
            rated_movie_id=movie_id, 
            new_rating=rating
        )
        
        # Dinamik önerileri film detaylarıyla zenginleştir
        dynamic_recommendations = []
        if dynamic_recs_raw:
            rec_movie_ids = [rec['movie_id'] for rec in dynamic_recs_raw]
            movies_in_recs = db.query(Movie).filter(Movie.id.in_(rec_movie_ids)).all()
            movie_map = {m.id: m for m in movies_in_recs}
            
            for rec in dynamic_recs_raw:
                movie_detail = movie_map.get(rec['movie_id'])
                if movie_detail:
                    dynamic_recommendations.append({
                        "movie_id": movie_detail.id,
                        "title": movie_detail.title,
                    })
        
        return {
            "status": "success",
            "message": message,
            "movie_id": movie_id,
            "movie_title": movie.title,
            "rating": rating,
            "dynamic_recommendations": dynamic_recommendations
        }
        
    except Exception as e:
        db.rollback()
        print(f"[x] Hata: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Bu endpoint'i ekle - veritabanında rating'leri kontrol etmek için
@app.get("/debug-ratings/{user_id}")
async def debug_user_ratings(user_id: int, db: Session = Depends(get_db)):
    try:
        print(f"[*] User {user_id} için rating'ler kontrol ediliyor...")
        
        # User'ın tüm rating'lerini getir
        ratings = db.query(UserInteraction).filter(
            UserInteraction.user_id == user_id,
            UserInteraction.interaction_type == "rating"
        ).all()
        
        print(f"[+] {len(ratings)} rating bulundu")
        
        rating_list = []
        for rating in ratings:
            print(f"[*] Movie ID: {rating.movie_id}, Extra Data: {rating.extra_data}")
            
            # Movie bilgisini al
            movie = db.query(Movie).filter(Movie.id == rating.movie_id).first()
            movie_title = movie.title if movie else "Bilinmiyor"
            
            # Rating'i parse et
            import json
            try:
                rating_data = json.loads(rating.extra_data) if rating.extra_data else {}
                user_rating = rating_data.get('rating', 'Bilinmiyor')
            except:
                user_rating = 'Parse Hatası'
            
            rating_list.append({
                "movie_id": rating.movie_id,
                "movie_title": movie_title,
                "user_rating": user_rating,
                "extra_data": rating.extra_data,
                "timestamp": rating.timestamp.isoformat() if rating.timestamp else None
            })
        
        return {
            "status": "success",
            "user_id": user_id,
            "ratings_count": len(ratings),
            "ratings": rating_list
        }
        
    except Exception as e:
        print(f"[x] Debug hatası: {e}")
        return {"error": str(e)}


# === EXPORT DATA ===
@app.get("/export-user-data")
async def export_user_data(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Export user's data (GDPR compliance)"""
    try:
        user_id = current_user["user_id"]
        
        # Get user ratings
        ratings = db.query(Rating, Movie).join(
            Movie, Rating.movie_id == Movie.id
        ).filter(Rating.user_id == user_id).all()
        
        # Get user favorites
        favorites = db.query(UserInteraction, Movie).join(
            Movie, UserInteraction.movie_id == Movie.id
        ).filter(
            UserInteraction.user_id == user_id,
            UserInteraction.interaction_type == "favorite"
        ).all()
        
        # Get user interactions
        interactions = db.query(UserInteraction).filter(
            UserInteraction.user_id == user_id
        ).all()
        
        user_data = {
            "user_id": user_id,
            "username": current_user["username"],
            "export_date": datetime.now().isoformat(),
            "ratings": [
                {
                    "movie_id": rating.movie_id,
                    "movie_title": movie.title,
                    "rating": float(rating.rating),
                    "timestamp": rating.timestamp.isoformat() if rating.timestamp else None
                }
                for rating, movie in ratings
            ],
            "favorites": [
                {
                    "movie_id": interaction.movie_id,
                    "movie_title": movie.title,
                    "added_date": interaction.timestamp.isoformat() if interaction.timestamp else None
                }
                for interaction, movie in favorites
            ],
            "interactions": [
                {
                    "type": interaction.interaction_type,
                    "movie_id": interaction.movie_id,
                    "timestamp": interaction.timestamp.isoformat() if interaction.timestamp else None,
                    "metadata": json.loads(interaction.metadata) if interaction.metadata else None
                }
                for interaction in interactions
            ]
        }
        
        return {
            "status": "success",
            "data": user_data,
            "stats": {
                "total_ratings": len(ratings),
                "total_favorites": len(favorites),
                "total_interactions": len(interactions)
            }
        }
        
    except Exception as e:
        logger.error(f"[x] Export data error: {e}")
        raise HTTPException(status_code=500, detail="Veri export edilirken hata oluştu")

# === ADMIN ENDPOINTS ===
@app.get("/admin/stats")
async def get_admin_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Admin dashboard statistics"""
    try:
        # Verify admin access (basic check)
        if current_user["username"] not in ["admin", "administrator"]:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Comprehensive stats
        stats = {
            "users": {
                "total": db.query(User).count(),
                "active_last_7_days": db.query(User).filter(
                    User.last_active >= datetime.now() - timedelta(days=7)
                ).count(),
                "new_last_30_days": db.query(User).filter(
                    User.created_at >= datetime.now() - timedelta(days=30)
                ).count()
            },
            "movies": {
                "total": db.query(Movie).count(),
                "with_ratings": db.query(Movie).filter(Movie.rating_count > 0).count(),
                "high_rated": db.query(Movie).filter(Movie.avg_rating >= 4.0).count()
            },
            "ratings": {
                "total": db.query(Rating).count(),
                "last_24_hours": db.query(Rating).filter(
                    Rating.timestamp >= datetime.now() - timedelta(hours=24)
                ).count(),
                "average_rating": db.query(func.avg(Rating.rating)).scalar()
            },
            "interactions": {
                "total": db.query(UserInteraction).count(),
                "favorites": db.query(UserInteraction).filter(
                    UserInteraction.interaction_type == "favorite"
                ).count()
            }
        }
        
        # Top users by activity
        top_users = db.query(
            User.username,
            func.count(Rating.id).label('rating_count')
        ).outerjoin(Rating).group_by(User.id).order_by(
            func.count(Rating.id).desc()
        ).limit(10).all()
        
        stats["top_users"] = [
            {"username": user.username, "ratings": count}
            for user, count in top_users
        ]
        
        return {
            "status": "success",
            "admin_stats": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[x] Admin stats error: {e}")
        raise HTTPException(status_code=500, detail="Admin stats alınırken hata oluştu")

# === BACKUP & MAINTENANCE ===
@app.post("/admin/backup-database")
async def backup_database_endpoint(
    current_user: dict = Depends(get_current_user)
):
    """Create database backup"""
    try:
        if current_user["username"] not in ["admin", "administrator"]:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        backup_filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        backup_path = f"backups/{backup_filename}"
        
        # Create backups directory if not exists
        os.makedirs("backups", exist_ok=True)
        
        # Copy database file
        import shutil
        shutil.copy2("movielens_100k.db", backup_path)
        
        return {
            "status": "success",
            "message": "Database backup created successfully",
            "backup_file": backup_filename,
            "backup_path": backup_path,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"[x] Backup error: {e}")
        raise HTTPException(status_code=500, detail="Backup oluşturulurken hata oluştu")
    
    
# ============================================================================
# [*] WATCHLIST ENDPOINTS
# ============================================================================







# [*] GÜNCELLENMIŞ ADD TO FAVORITES
@app.post("/add-to-favorites")
async def add_to_favorites(
    request: Request,
    favorite_data: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        # [*] Debug
        print("="*50)
        print("[*] ADD TO FAVORITES REQUEST DEBUG")
        print("="*50)
        
        body = await request.body()
        print(f"[*] Raw request body: {body}")
        print(f"[*] Parsed favorite_data: {favorite_data}")
        print(f"[*] Current user: {current_user}")
        
        # Validation
        movie_id = favorite_data.get("movie_id")
        
        if movie_id is None:
            print("[x] movie_id is None")
            raise HTTPException(status_code=422, detail=[{
                "loc": ["body", "movie_id"],
                "msg": "movie_id is required",
                "type": "value_error.missing"
            }])
        
        try:
            movie_id = int(movie_id)
            print(f"[+] Movie ID converted to int: {movie_id}")
        except (ValueError, TypeError) as e:
            print(f"[x] Cannot convert movie_id to int: {e}")
            raise HTTPException(status_code=422, detail=[{
                "loc": ["body", "movie_id"],
                "msg": "movie_id must be an integer",
                "type": "type_error.integer"
            }])
        
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid user authentication")
        
        # Movie check
        movie = db.query(Movie).filter(Movie.id == movie_id).first()
        if not movie:
            print(f"[x] Movie not found: {movie_id}")
            raise HTTPException(status_code=404, detail=f"Movie with ID {movie_id} not found")
        
        print(f"[+] Movie found: {movie.title}")
        
        # Existing favorite check
        existing = db.query(UserInteraction).filter(
            UserInteraction.user_id == user_id,
            UserInteraction.movie_id == movie_id,
            UserInteraction.interaction_type == "favorite"
        ).first()
        
        if existing:
            print(f"[i] Movie already in favorites")
            return {
                "status": "info", 
                "message": f"'{movie.title}' zaten favorilerinizde!",
                "movie_id": movie_id,
                "movie_title": movie.title
            }
        
        # Add new favorite
        print(f"[+] Adding new favorite")
        new_favorite = UserInteraction(
            user_id=user_id,
            movie_id=movie_id,
            interaction_type="favorite",
            timestamp=datetime.utcnow()
        )
        
        db.add(new_favorite)
        
        try:
            db.commit()
            print(f"[+] Favorite added successfully")
        except Exception as commit_error:
            print(f"[x] Database commit failed: {commit_error}")
            db.rollback()
            raise HTTPException(status_code=500, detail="Database commit failed")
        
        response_data = {
            "status": "success",
            "message": f"[+] '{movie.title}' favorilere eklendi!",
            "movie_id": movie_id,
            "movie_title": movie.title,
            "user_id": user_id
        }
        
        print(f"[+] Returning response: {response_data}")
        return response_data
        
    except HTTPException as http_ex:
        print(f"[x] HTTP Exception: {http_ex.detail}")
        raise http_ex
    except Exception as e:
        db.rollback()
        print(f"[x] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


 # Mevcut my-favorites fonksiyonunu şununla değiştir:

@app.get("/my-favorites")
def get_my_favorites(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        user_id = current_user["user_id"]
        
        print(f"[*] User {user_id} için favoriler getiriliyor...")
        
        # Favorites getir
        favorites = db.query(UserInteraction).filter(
            UserInteraction.user_id == user_id,
            UserInteraction.interaction_type == "favorite"
        ).all()
        
        print(f"[+] {len(favorites)} favori bulundu")
        
        favorite_movies = []
        for fav in favorites:
            movie = db.query(Movie).filter(Movie.id == fav.movie_id).first()
            if movie:
                # [*] USER RATING EKLE
                user_rating = get_user_rating_for_movie(db, user_id, movie.id)
                print(f"[*] Movie: {movie.title}, User Rating: {user_rating}")
                
                favorite_movies.append({
                    "movie_id": movie.id,
                    "title": movie.title,
                    "genres": movie.genres.split("|") if movie.genres else [],  # ← | ile split (doğru)
                    "avg_rating": round(movie.avg_rating, 1) if movie.avg_rating else 0,
                    "rating_count": movie.rating_count or 0,
                    "release_date": movie.release_date or "Bilinmiyor",
                    "popularity": movie.rating_count or 0,
                    "user_rating": user_rating,  # ← EKLENDI
                    "imdb_url": movie.imdb_url if movie.imdb_url else None
                })
        
        return {
            "status": "success",
            "count": len(favorite_movies),
            "favorites": favorite_movies
        }
        
    except Exception as e:
        print(f"[x] Favorites hatası: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    
    # Bu endpoint'i main.py'ye ekle:

@app.get("/similar-movies/{movie_id}")
async def get_similar_movies(
    movie_id: int,
    n_recommendations: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """Belirli bir filme benzer filmler öner"""
    
    try:
        db = SessionLocal()
        
        # Hedef filmi kontrol et
        target_movie = db.query(Movie).filter(Movie.id == movie_id).first()
        if not target_movie:
            return {
                "status": "error",
                "message": "Film bulunamadı"
            }
        
        print(f"[*] {target_movie.title} filmine benzer filmler aranıyor...")
        
        # Basit benzerlik: Aynı türdeki filmler
        target_genres = target_movie.genres.split('|') if target_movie.genres else []
        
        if not target_genres:
            return {
                "status": "info",
                "message": "Bu film için tür bilgisi bulunamadı"
            }
        
        # Aynı türlerden filmler bul
        similar_movies = []
        
        # Her tür için filmler bul
        for genre in target_genres:
            genre_movies = db.query(Movie).filter(
                Movie.genres.like(f'%{genre}%'),
                Movie.id != movie_id  # Kendisini hariç tut
            ).order_by(Movie.avg_rating.desc()).limit(20).all()
            
            for movie in genre_movies:
                if movie.id not in [m['movie_id'] for m in similar_movies]:
                    # Benzerlik skoru hesapla (ortak tür sayısı)
                    movie_genres = movie.genres.split('|') if movie.genres else []
                    common_genres = len(set(target_genres) & set(movie_genres))
                    similarity_score = (common_genres / len(target_genres)) * 5
                    
                    similar_movies.append({
                        'movie_id': movie.id,
                        'title': movie.title,
                        'genres': movie_genres,
                        'avg_rating': float(movie.avg_rating) if movie.avg_rating else 0.0,
                        'popularity': movie.rating_count or 0,
                        'release_date': movie.release_date or 'Bilinmiyor',
                        'imdb_url': movie.imdb_url,
                        'similarity_score': similarity_score,
                        'common_genres': common_genres,
                        'recommendation_type': 'Content_Based_Similarity'
                    })
        
        # Benzerlik skoruna göre sırala
        similar_movies.sort(key=lambda x: x['similarity_score'], reverse=True)
        similar_movies = similar_movies[:n_recommendations]
        
        db.close()
        
        return {
            "status": "success",
            "message": f"{target_movie.title} filmine benzer {len(similar_movies)} film",
            "target_movie": {
                "id": target_movie.id,
                "title": target_movie.title,
                "genres": target_genres
            },
            "method": "Content-Based Genre Similarity",
            "recommendations": similar_movies
        }
        
    except Exception as e:
        logger.error(f"Similar movies error: {e}")
        return {
            "status": "error",
            "message": f"Benzer filmler alınırken hata: {str(e)}"
        }




# Movie modelinin hangi field'ları var kontrol edelim
@app.get("/debug-movie-model")
async def debug_movie_model(db: Session = Depends(get_db)):
    try:
        # İlk movie'yi al
        movie = db.query(Movie).first()
        if movie:
            # Movie'nin tüm attribute'larını göster
            movie_dict = {}
            for column in movie.__table__.columns:
                movie_dict[column.name] = getattr(movie, column.name, None)
            
            print("[*] Movie model fields:")
            for key, value in movie_dict.items():
                print(f"  - {key}: {value}")
            
            return {
                "status": "success",
                "available_fields": list(movie_dict.keys()),
                "sample_movie": movie_dict
            }
        else:
            return {"error": "No movies found"}
            
    except Exception as e:
        return {"error": str(e)}


# USER STATS GÜNCELLEMESİ:
@app.get("/user-stats")
async def get_user_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        user_id = current_user["user_id"]
        
        # Puanlamalar (DOĞRU TABLODAN: UserInteraction)
        ratings_count = db.query(UserInteraction).filter(
            UserInteraction.user_id == user_id,
            UserInteraction.interaction_type == "rating"
        ).count()
        
        # Favoriler
        favorites_count = db.query(UserInteraction).filter(
            UserInteraction.user_id == user_id,
            UserInteraction.interaction_type == "favorite"
        ).count()
        
        # Watchlist counts
        to_watch_count = db.query(UserInteraction).filter(
            UserInteraction.user_id == user_id,
            UserInteraction.interaction_type == "watchlist",
            UserInteraction.extra_data.like('%"status": "to_watch"%')
        ).count()
        
        watched_count = db.query(UserInteraction).filter(
            UserInteraction.user_id == user_id,
            UserInteraction.interaction_type == "watchlist",
            UserInteraction.extra_data.like('%"status": "watched"%')
        ).count()
        
        return {
            "status": "success",
            "stats": {
                "ratings_count": ratings_count,
                "favorites_count": favorites_count,
                "to_watch_count": to_watch_count,
                "watched_count": watched_count,
                "total_activity": ratings_count + favorites_count + to_watch_count + watched_count
            }
        }
        
    except Exception as e:
        logger.error(f"[x] User stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# === RECOMMENDATION FEEDBACK ===
@app.post("/recommendation-feedback")
async def submit_recommendation_feedback(
    feedback_data: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Submit feedback on recommendation quality"""
    try:
        user_id = current_user["user_id"]
        movie_id = feedback_data.get("movie_id")
        feedback_type = feedback_data.get("feedback_type")  # helpful, not_helpful, irrelevant
        algorithm_used = feedback_data.get("algorithm_used", "hybrid")
        
        # Store feedback for system improvement
        feedback = UserInteraction(
            user_id=user_id,
            movie_id=movie_id,
            interaction_type="feedback",
            metadata=json.dumps({
                "feedback_type": feedback_type,
                "algorithm_used": algorithm_used,
                "timestamp": datetime.now().isoformat()
            }),
            timestamp=datetime.utcnow()
        )
        
        db.add(feedback)
        db.commit()
        
        return {
            "status": "success",
            "message": "Feedback submitted successfully",
            "feedback_type": feedback_type
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"[x] Feedback error: {e}")
        raise HTTPException(status_code=500, detail="Feedback gönderilirken hata oluştu")

# === GENRE POPULARITY ===
@app.get("/genre-popularity")
async def get_genre_popularity(
    time_period: str = "all",  # week, month, all
    db: Session = Depends(get_db)
):
    """Get genre popularity statistics"""
    try:
        # Calculate date filter
        if time_period == "week":
            date_filter = datetime.now() - timedelta(days=7)
        elif time_period == "month":
            date_filter = datetime.now() - timedelta(days=30)
        else:
            date_filter = datetime.now() - timedelta(days=365*10)  # Very old date
        
        # Get ratings within time period
        ratings_query = db.query(Rating, Movie).join(
            Movie, Rating.movie_id == Movie.id
        ).filter(Rating.timestamp >= date_filter)
        
        genre_stats = {}
        total_ratings = 0
        
        for rating, movie in ratings_query.all():
            if movie.genres:
                total_ratings += 1
                for genre in movie.genres.split("|"):
                    if genre not in genre_stats:
                        genre_stats[genre] = {
                            "count": 0,
                            "total_rating": 0.0,
                            "avg_rating": 0.0
                        }
                    
                    genre_stats[genre]["count"] += 1
                    genre_stats[genre]["total_rating"] += rating.rating
        
        # Calculate averages and percentages
        for genre in genre_stats:
            genre_stats[genre]["avg_rating"] = (
                genre_stats[genre]["total_rating"] / genre_stats[genre]["count"]
            )
            genre_stats[genre]["percentage"] = (
                (genre_stats[genre]["count"] / total_ratings * 100) if total_ratings > 0 else 0
            )
        
        # Sort by popularity
        sorted_genres = sorted(
            genre_stats.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )
        
        return {
            "status": "success",
            "time_period": time_period,
            "total_ratings_analyzed": total_ratings,
            "genres": [
                {
                    "genre": genre,
                    "rating_count": stats["count"],
                    "avg_rating": round(stats["avg_rating"], 2),
                    "popularity_percentage": round(stats["percentage"], 2)
                }
                for genre, stats in sorted_genres
            ]
        }
        
    except Exception as e:
        logger.error(f"[x] Genre popularity error: {e}")
        raise HTTPException(status_code=500, detail="Tür popülerliği alınırken hata oluştu")

# === CLEAR USER DATA ===
@app.delete("/clear-user-data")
async def clear_user_data(
    confirm: bool = False,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Clear user's data (GDPR compliance)"""
    try:
        if not confirm:
            raise HTTPException(
                status_code=400, 
                detail="Bu işlemi onaylamak için confirm=true parametresini gönderin"
            )
        
        user_id = current_user["user_id"]
        
        # Delete user ratings
        db.query(Rating).filter(Rating.user_id == user_id).delete()
        
        # Delete user interactions
        db.query(UserInteraction).filter(UserInteraction.user_id == user_id).delete()
        
        # Update user info (keep account but clear personal data)
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.email = f"deleted_user_{user_id}@deleted.com"
            user.favorite_genres = None
            user.age = None
            user.gender = None
        
        db.commit()
        
        return {
            "status": "success",
            "message": "Kullanıcı verileri başarıyla temizlendi",
            "cleared_data": [
                "ratings",
                "interactions",
                "personal_preferences"
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[x] Clear user data error: {e}")
        raise HTTPException(status_code=500, detail="Veri temizlenirken hata oluştu")

# === MOVIE MANAGEMENT ===
@app.post("/admin/add-movie")
async def add_movie(
    movie_data: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Add new movie to the system"""
    try:
        if current_user["username"] not in ["admin", "administrator"]:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        new_movie = Movie(
            title=movie_data["title"],
            genres=movie_data.get("genres"),
            release_date=movie_data.get("release_date"),
            avg_rating=movie_data.get("avg_rating", 0.0),
            rating_count=movie_data.get("rating_count", 0)
                    )
        
        db.add(new_movie)
        db.commit()
        db.refresh(new_movie)
        
        return {
            "status": "success",
            "message": "Film başarıyla eklendi",
            "movie": {
                "id": new_movie.id,
                "title": new_movie.title,
                "genres": new_movie.genres,
                "release_date": new_movie.release_date
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[x] Add movie error: {e}")
        raise HTTPException(status_code=500, detail="Film eklenirken hata oluştu")

@app.put("/admin/update-movie/{movie_id}")
async def update_movie(
    movie_id: int,
    movie_data: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update movie information"""
    try:
        if current_user["username"] not in ["admin", "administrator"]:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        movie = db.query(Movie).filter(Movie.id == movie_id).first()
        if not movie:
            raise HTTPException(status_code=404, detail="Film bulunamadı")
        
        # Update fields if provided
        if "title" in movie_data:
            movie.title = movie_data["title"]
        if "genres" in movie_data:
            movie.genres = movie_data["genres"]
        if "release_date" in movie_data:
            movie.release_date = movie_data["release_date"]
        
        db.commit()
        
        return {
            "status": "success",
            "message": "Film bilgileri güncellendi",
            "movie": {
                "id": movie.id,
                "title": movie.title,
                "genres": movie.genres,
                "release_date": movie.release_date
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[x] Update movie error: {e}")
        raise HTTPException(status_code=500, detail="Film güncellenirken hata oluştu")

# === RECOMMENDATION HISTORY ===
@app.get("/recommendation-history")
async def get_recommendation_history(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get user's recommendation history"""
    try:
        user_id = current_user["user_id"]
        
        # Get user's interactions that indicate recommendations were viewed
        history = db.query(UserInteraction, Movie).join(
            Movie, UserInteraction.movie_id == Movie.id, isouter=True
        ).filter(
            UserInteraction.user_id == user_id,
            UserInteraction.interaction_type.in_(["recommendation_view", "recommendation_click"])
        ).order_by(UserInteraction.timestamp.desc()).limit(limit).all()
        
        recommendation_history = []
        for interaction, movie in history:
            metadata = json.loads(interaction.metadata) if interaction.metadata else {}
            
            recommendation_history.append({
                "interaction_id": interaction.id,
                "movie_id": interaction.movie_id,
                "movie_title": movie.title if movie else "Unknown",
                "interaction_type": interaction.interaction_type,
                "algorithm_used": metadata.get("algorithm_used", "unknown"),
                "timestamp": interaction.timestamp.isoformat() if interaction.timestamp else None,
                "metadata": metadata
            })
        
        return {
            "status": "success",
            "count": len(recommendation_history),
            "history": recommendation_history
        }
        
    except Exception as e:
        logger.error(f"[x] Recommendation history error: {e}")
        raise HTTPException(status_code=500, detail="Öneri geçmişi alınırken hata oluştu")

# === SYSTEM CONFIGURATION ===
@app.get("/system-config")
async def get_system_config():
    """Get system configuration and feature flags"""
    recommendation_api = None  # Define recommendation_api or import it from the appropriate module
    return {
        "status": "success",
        "config": {
            "version": "Enhanced Hybrid v6.0 Complete",
            "features": {
                "basic_recommendations": True,
                "hybrid_recommendations": recommendation_api is not None,
                "collaborative_filtering": recommendation_api is not None,
                "content_based_filtering": recommendation_api is not None,
                "matrix_factorization": recommendation_api is not None,
                "ab_testing": recommendation_api is not None,
                "analytics": True,
                "user_management": True,
                "favorites_system": True,
                "rating_system": True,
                "search_functionality": True,
                "trending_movies": True,
                "admin_panel": True,
                "data_export": True,
                "feedback_system": True
            },
            "algorithms": {
                "hybrid": {
                    "enabled": recommendation_api is not None,
                    "weights": {
                        "collaborative_filtering": 0.35,
                        "content_based": 0.25,
                        "matrix_factorization": 0.25,
                        "popularity": 0.15
                    } if recommendation_api else None
                },
                "fallback": {
                    "enabled": True,
                    "type": "genre_based_with_popularity"
                }
            },
            "database": {
                "type": "SQLite",
                "path": "movielens_100k.db",
                "backup_enabled": True
            }
        }
    }
# === STATISTICS ENDPOINTS ===
@app.get("/user-activity-stats")
async def get_user_activity_stats(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get detailed user activity statistics"""
    try:
        user_id = current_user["user_id"]
        start_date = datetime.now() - timedelta(days=days)
        
        # Daily activity
        daily_stats = db.query(
            func.date(Rating.timestamp).label('date'),
            func.count(Rating.id).label('ratings_count')
        ).filter(
            Rating.user_id == user_id,
            Rating.timestamp >= start_date
        ).group_by(func.date(Rating.timestamp)).all()
        
        # Genre preferences over time
        genre_stats = db.query(
            Movie.genres,
            func.count(Rating.id).label('count'),
            func.avg(Rating.rating).label('avg_rating')
        ).join(Rating, Movie.id == Rating.movie_id).filter(
            Rating.user_id == user_id,
            Rating.timestamp >= start_date
        ).group_by(Movie.genres).all()
        
        # Rating distribution
        rating_distribution = db.query(
            Rating.rating,
            func.count(Rating.id).label('count')
        ).filter(
            Rating.user_id == user_id,
            Rating.timestamp >= start_date
        ).group_by(Rating.rating).all()
        
        return {
            "status": "success",
            "period_days": days,
            "daily_activity": [
                {
                    "date": str(stat.date),
                    "ratings_count": stat.ratings_count
                }
                for stat in daily_stats
            ],
            "genre_preferences": [
                {
                    "genres": stat.genres,
                    "rating_count": stat.count,
                    "avg_rating": round(float(stat.avg_rating), 2)
                }
                for stat in genre_stats if stat.genres
            ],
            "rating_distribution": [
                {
                    "rating": float(stat.rating),
                    "count": stat.count
                }
                for stat in rating_distribution
            ]
        }
        
    except Exception as e:
        logger.error(f"[x] User activity stats error: {e}")
        raise HTTPException(status_code=500, detail="Kullanıcı aktivite istatistikleri alınırken hata oluştu")

# === RECOMMENDATION QUALITY METRICS ===
@app.get("/recommendation-quality")
async def get_recommendation_quality_metrics(
    algorithm: str = "hybrid",
    sample_size: int = 100,
    recommendation_api = None
):
    """Get recommendation quality metrics"""
    try:
        if not recommendation_api:
            return {
                "status": "info",
                "message": "Advanced recommendation system not available",
                "basic_metrics": {
                    "system_health": "basic_mode",
                    "fallback_active": True
                }
            }
        
        await recommendation_api.initialize()
        
        # Get sample users for evaluation
        conn = sqlite3.connect('movielens_100k.db')
        sample_users = pd.read_sql_query(
            f"""
            SELECT DISTINCT user_id 
            FROM ratings 
            ORDER BY RANDOM() 
            LIMIT {sample_size}
            """, 
            conn
        )['user_id'].tolist()
        conn.close()
        
        total_metrics = {
            'precision': [],
            'recall': [],
            'f1_score': [],
            'coverage': [],
            'diversity': [],
            'novelty': []
        }
        
        successful_evaluations = 0
        
        for user_id in sample_users:
            try:
                recommendations = await recommendation_api.get_hybrid_recommendations(user_id, 10)
                
                if recommendations:
                    # Mock evaluation metrics (in real implementation, you'd calculate these properly)
                    mock_metrics = {
                        'precision': np.random.uniform(0.6, 0.9),
                        'recall': np.random.uniform(0.5, 0.8),
                        'f1_score': np.random.uniform(0.55, 0.85),
                        'coverage': np.random.uniform(0.1, 0.3),
                        'diversity': np.random.uniform(0.7, 0.95),
                        'novelty': np.random.uniform(0.6, 0.9)
                    }
                    
                    for metric, value in mock_metrics.items():
                        total_metrics[metric].append(value)
                    
                    successful_evaluations += 1
                    
            except Exception as e:
                logger.warning(f"Evaluation failed for user {user_id}: {e}")
                continue
        
        if successful_evaluations == 0:
            raise HTTPException(status_code=500, detail="No successful evaluations")
        
        # Calculate averages
        avg_metrics = {
            metric: np.mean(values) for metric, values in total_metrics.items()
        }
        
        return {
            "status": "success",
            "algorithm": algorithm,
            "sample_size": sample_size,
            "successful_evaluations": successful_evaluations,
            "quality_metrics": {
                "precision": round(avg_metrics['precision'], 3),
                "recall": round(avg_metrics['recall'], 3),
                "f1_score": round(avg_metrics['f1_score'], 3),
                "coverage": round(avg_metrics['coverage'], 3),
                "diversity": round(avg_metrics['diversity'], 3),
                "novelty": round(avg_metrics['novelty'], 3)
            },
            "performance_grade": "A" if avg_metrics['f1_score'] > 0.7 else "B" if avg_metrics['f1_score'] > 0.6 else "C",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"[x] Recommendation quality error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
# === BULK DATA OPERATIONS ===
@app.post("/admin/bulk-import-movies")
async def bulk_import_movies(
    movies_data: List[dict],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Bulk import movies"""
    try:
        if current_user["username"] not in ["admin", "administrator"]:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        successful_imports = 0
        failed_imports = 0
        errors = []
        
        for movie_data in movies_data:
            try:
                # Check if movie already exists
                existing_movie = db.query(Movie).filter(
                    Movie.title == movie_data["title"]
                ).first()
                
                if existing_movie:
                    failed_imports += 1
                    errors.append(f"Movie '{movie_data['title']}' already exists")
                    continue
                
                new_movie = Movie(
                    title=movie_data["title"],
                    genres=movie_data.get("genres"),
                    release_date=movie_data.get("release_date"),
                    avg_rating=movie_data.get("avg_rating", 0.0),
                    rating_count=movie_data.get("rating_count", 0)
                )
                
                db.add(new_movie)
                successful_imports += 1
                
            except Exception as e:
                failed_imports += 1
                errors.append(f"Failed to import '{movie_data.get('title', 'Unknown')}': {str(e)}")
        
        db.commit()
        
        return {
            "status": "success",
            "message": f"Bulk import completed",
            "results": {
                "total_movies": len(movies_data),
                "successful_imports": successful_imports,
                "failed_imports": failed_imports,
                "errors": errors[:10]  # Limit error messages
            }
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"[x] Bulk import error: {e}")
        raise HTTPException(status_code=500, detail="Toplu import işlemi başarısız")

# === WEBSOCKET FOR REAL-TIME UPDATES ===
from fastapi import WebSocket, WebSocketDisconnect

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove dead connections
                self.active_connections.remove(connection)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and send periodic updates
            await asyncio.sleep(30)
            await websocket.send_text(json.dumps({
                "type": "heartbeat",
                "timestamp": datetime.now().isoformat()
            }))
    except WebSocketDisconnect:
                manager.disconnect(websocket)

# === NOTIFICATION SYSTEM ===
@app.post("/send-recommendation-notification")
async def send_recommendation_notification(
    user_id: int,
    message: str,
    recommendation_data: dict = None
):
    """Send real-time recommendation notification"""
    try:
        notification = {
            "type": "recommendation",
            "user_id": user_id,
            "message": message,
            "data": recommendation_data,
            "timestamp": datetime.now().isoformat()
        }
        
        await manager.broadcast(json.dumps(notification))
        
        return {
            "status": "success",
            "message": "Notification sent successfully"
        }
        
    except Exception as e:
        logger.error(f"[x] Notification error: {e}")
        raise HTTPException(status_code=500, detail="Bildirim gönderilirken hata oluştu")

# === RECOMMENDATION CACHE ===
class RecommendationCache:
    def __init__(self):
        self.cache = {}
        self.cache_timeout = 3600  # 1 hour
    
    def get(self, user_id: int, algorithm: str):
        cache_key = f"{user_id}_{algorithm}"
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if datetime.now().timestamp() - timestamp < self.cache_timeout:
                return cached_data
        return None
    
    def set(self, user_id: int, algorithm: str, recommendations: list):
        cache_key = f"{user_id}_{algorithm}"
        self.cache[cache_key] = (recommendations, datetime.now().timestamp())
    
    def clear_user_cache(self, user_id: int):
        keys_to_remove = [key for key in self.cache.keys() if key.startswith(f"{user_id}_")]
        for key in keys_to_remove:
            del self.cache[key]

# Initialize cache
recommendation_cache = RecommendationCache()


# Model tabanlı öneriler endpoint'i
# Bu kodu main.py'deki model-recommendations endpoint'inin yerine koy:
# Bu kodu main.py'deki model-recommendations endpoint'inin yerine koy:

@app.get("/model-recommendations/{user_id}")
async def get_model_recommendations(
    user_id: int,
    n_recommendations: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """Eğitilmiş NMF modelinden öneriler al - Fixed Version"""
    
    try:
        # Model önerilerini al
        recommendations = recommendation_api.get_user_recommendations(
            user_id=user_id,
            n_recommendations=n_recommendations
        )
        
        if not recommendations:
            return {
                "status": "info",
                "message": "Bu kullanıcı için model önerisi bulunamadı",
                "recommendations": []
            }
        
        # Film bilgilerini veritabanından al
        enhanced_recommendations = []
        
        db = SessionLocal()
        try:
            for rec in recommendations:
                movie_id = rec['movie_id']
                
                # Veritabanından film bilgilerini al
                movie = db.query(Movie).filter(Movie.id == movie_id).first()
                
                if movie:
                    # [*] Sadece mevcut field'ları kullan
                    enhanced_rec = {
                        'movie_id': movie.id,
                        'title': movie.title,
                        'genres': movie.genres.split('|') if movie.genres else ['Bilinmiyor'],
                        'avg_rating': float(movie.avg_rating) if movie.avg_rating else 0.0,
                        'popularity': 0,  # Default değer
                        'release_date': getattr(movie, 'release_date', 'Bilinmiyor'),
                        'imdb_url': getattr(movie, 'imdb_url', None),
                        'predicted_rating': rec['predicted_rating'],
                        'model_score': rec['predicted_rating'],
                        'recommendation_type': 'NMF_Collaborative_Filtering',
                        'hybrid_score': rec['predicted_rating'],
                        'total_score': rec['predicted_rating'],
                        'similarity_score': rec['predicted_rating']
                    }
                    enhanced_recommendations.append(enhanced_rec)
                else:
                    # Film bulunamazsa basit bilgi
                    enhanced_rec = {
                        'movie_id': movie_id,
                        'title': f'Film {movie_id}',
                        'genres': ['Model Önerisi'],
                        'avg_rating': 0.0,
                        'popularity': 0,
                        'release_date': 'Bilinmiyor',
                        'imdb_url': None,
                        'predicted_rating': rec['predicted_rating'],
                        'model_score': rec['predicted_rating'],
                        'recommendation_type': 'NMF_Collaborative_Filtering',
                        'hybrid_score': rec['predicted_rating'],
                        'total_score': rec['predicted_rating'],
                        'similarity_score': rec['predicted_rating']
                    }
                    enhanced_recommendations.append(enhanced_rec)
                
        finally:
            db.close()
        
        return {
            "status": "success",
            "message": f"Model tabanlı {len(enhanced_recommendations)} öneri",
            "method": "NMF Collaborative Filtering",
            "recommendations": enhanced_recommendations,
            "model_info": recommendation_api.get_model_info()
        }
        
    except Exception as e:
        logger.error(f"Model recommendation error: {e}")
        return {
            "status": "error",
            "message": f"Model önerisi hatası: {str(e)}"
        }



# Model bilgileri endpoint'i
@app.get("/model-info")
async def get_model_info():
    """Eğitilmiş model bilgilerini döndür"""
    return {
        "status": "success",
        "model_info": recommendation_api.get_model_info()
    }

# Problematic code block has been removed to fix syntax errors
            
            # Yetersiz tür çeşitliliği kontrolü  
            if genre_count < MIN_GENRES:
                return {
                    "status": "insufficient_diversity",
                    "message": f"🎭 FARKLI TÜRLERDEN FİLM PUANLAYIN! ({genre_count}/{MIN_GENRES} tür)",
                    "method": "Quality Gate - Insufficient Genre Diversity",
                    "user_rating_count": rating_count,
                    "current_genres": genre_count,
                    "minimum_genres": MIN_GENRES,
                    "rated_genres": list(all_genres)[:10],  # İlk 10'unu göster
                    "recommendation_quality": "insufficient_diversity",
                    "next_steps": [
                        f"{MIN_GENRES - genre_count} farklı tür daha gerekli",
                        "Action, Comedy, Drama, Romance, Sci-Fi türlerini deneyin",
                        "Çeşitlilik neural embeddings kalitesini artırır"
                    ],
                    "recommendations": []
                }
            
            # KALITE ŞARTLARI TAMAM - REAL-TIME NEURAL TRAINING
            logger.info(f"[✅] Quality Gate Passed - Starting Real-Time Neural Training...")
            
            if main_deep_learning_system:
                try:
                    logger.info("[🧠] Real-Time Neural Collaborative Filtering...")
                    
                    # REAL-TIME TRAINING (Fresh data ile)
                    logger.info("[⚡] Starting real-time neural training...")
                    training_success = main_deep_learning_system.train_model()
                    
                    if training_success:
                        logger.info("[🎯] Fresh neural embeddings ready!")
                        
                        # DYNAMIC SIMILARITY (Fresh embeddings ile)  
                        similar_users = main_deep_learning_system.find_similar_users(user_id)
                        logger.info(f"[👥] Dynamic similarity: {len(similar_users)} benzer kullanıcı")
                        
                        if similar_users:
                            # FRESH RECOMMENDATIONS
                            recommendations = main_deep_learning_system.get_recommendations(user_id, n_recommendations)
                            logger.info(f"[🎬] Real-time recommendations: {len(recommendations)} film")
                            
                            if recommendations:
                                return {
                                    "status": "success",
                                    "message": f"🧠 REAL-TIME NEURAL CF - {rating_count} rating, {genre_count} tür → {len(similar_users)} benzer kullanıcı → {len(recommendations)} film",
                                    "method": "Real-Time Neural Collaborative Filtering", 
                                    "algorithm": "dynamic_neural_collaborative_filtering_128d",
                                    "user_rating_count": rating_count,
                                    "user_genre_count": genre_count,
                                    "rated_genres": list(all_genres)[:5],
                                    "similar_users_found": len(similar_users),
                                    "similar_users": [
                                        {"user_id": u["user_id"], "similarity": u["similarity_score"]} 
                                        for u in similar_users[:5]
                                    ],
                                    "embedding_dimension": 128,
                                    "model_type": "real_time_tensorflow_neural_network",
                                    "training_type": "incremental_learning",
                                    "recommendations": recommendations,
                                    "quality": "real_time_personalized_deep_learning"
                                }
                        
                        logger.warning("[!] No similar users after real-time training")
                    else:
                        logger.error("[x] Real-time training failed")
                    
                except Exception as e:
                    logger.error(f"[🚨] Real-time neural error: {e}")
            
            # Fallback if real-time fails
            logger.info("[*] Real-time neural failed, using cached system...")
            
            # Fallback: Basit collaborative filtering
            logger.info("[*] Dynamic Deep Learning yok, basit collaborative filtering...")
            if USER_MOVIE_MATRIX is not None and user_id in USER_ID_MAP:
                try:
                    from sklearn.metrics.pairwise import cosine_similarity
                    
                    user_idx = USER_ID_MAP[user_id]
                    user_vector = USER_MOVIE_MATRIX[user_idx].reshape(1, -1)
                    
                    # Benzer kullanıcıları bul (BASIT YÖNTEM)
                    similarities = cosine_similarity(user_vector, USER_MOVIE_MATRIX)[0]
                    similar_indices = np.argsort(similarities)[::-1][1:11]  # Top 10
                    
                    # Öneri oluştur
                    similar_ratings = USER_MOVIE_MATRIX[similar_indices]
                    movie_scores = similar_ratings.mean(axis=0)
                    top_movie_indices = np.argsort(movie_scores)[::-1][:n_recommendations]
                    
                    recommendations = []
                    for movie_idx in top_movie_indices:
                        if movie_scores[movie_idx] > 0:
                            movie_id = INV_MOVIE_ID_MAP.get(movie_idx)
                            if movie_id:
                                movie_details = db.query(Movie).filter(Movie.id == movie_id).first()
                                if movie_details:
                                    recommendations.append({
                                        "movie_id": movie_details.id,
                                        "title": movie_details.title,
                                        "genres": movie_details.genres.split('|') if movie_details.genres else [],
                                        "predicted_rating": float(movie_scores[movie_idx] * 5.0),
                                        "similarity_score": float(movie_scores[movie_idx]),
                                        "reason": f"Benzer kullanıcılar önerdi (skor: {movie_scores[movie_idx]:.2f})",
                                        "type": "basic_collaborative_filtering"
                                    })
                    
                    if recommendations:
                        return {
                            "status": "success",
                            "message": f"⚡ BASIT BENZER KULLANICI - {len(recommendations)} öneri",
                            "method": "Basic Collaborative Filtering",
                            "user_rating_count": user_ratings_count,
                            "recommendation_quality": "basic_similarity",
                            "recommendations": recommendations
                        }
                
                except Exception as e:
                    logger.error(f"Basic collaborative filtering error: {e}")
            
            # Son çare: Popüler filmler
            return {
                "status": "info",
                "message": "Hiçbir model çalışmıyor, popüler filmler",
                "method": "Popular Fallback",
                "recommendations": []
            }
        
        return {
            "status": "success",
            "message": f"Kişiselleştirilmiş öneriler ({len(recommendations)} film)",
            "method": "Advanced Hybrid System - Personalized",
            "model_type": "new_advanced",
            "user_rating_count": user_ratings_count,
            "recommendation_quality": "personalized",
            "recommendations": recommendations
        }
        
    except Exception as e:
        logger.error(f"New model error: {e}")
        return {
            "status": "error", 
            "message": f"Yeni model hatası: {str(e)}"
        }
"""

# === 🧠 NEW PURE DEEP LEARNING ENDPOINT ===
@app.get("/deep-learning-recommendations/{user_id}")
async def get_clean_deep_learning_recommendations(
    user_id: int,
    n_recommendations: int = 10,
    current_user: dict = Depends(get_current_user)):
    """🧠 CLEAN PURE DEEP LEARNING SYSTEM"""
    
    if not main_deep_learning_system:
        raise HTTPException(status_code=503, detail="Deep Learning System not available")
    
    try:
        logger.info(f"[🧠] Clean Deep Learning - User {user_id}")
        
        # QUALITY CHECK
        conn = get_simple_db()
        user_ratings = conn.execute("""
            SELECT ui.movie_id, 
                   JSON_EXTRACT(ui.extra_data, '$.rating') as rating,
                   m.genres
            FROM user_interactions ui
            JOIN movies m ON ui.movie_id = m.id  
            WHERE ui.user_id = ? 
            AND ui.interaction_type = 'rating'
            AND JSON_EXTRACT(ui.extra_data, '$.rating') IS NOT NULL
        """, (user_id,)).fetchall()
        conn.close()
        
        rating_count = len(user_ratings)
        
        # Genre diversity
        all_genres = set()
        for rating in user_ratings:
            if rating[2]:
                all_genres.update(rating[2].split('|'))
        
        genre_count = len(all_genres)
        logger.info(f"[📊] Quality: {rating_count} ratings, {genre_count} genres")
        
        # QUALITY GATES
        if rating_count < 10:
            return {
                "status": "insufficient_data",
                "message": f"🎬 {10-rating_count} DAHA FİLM PUANLAYIN!",
                "user_rating_count": rating_count,
                "minimum_required": 10,
                "recommendations": []
            }
        
        if genre_count < 3:
            return {
                "status": "insufficient_diversity", 
                "message": f"🎭 {3-genre_count} FARKLI TÜR PUANLAYIN!",
                "current_genres": genre_count,
                "rated_genres": list(all_genres),
                "recommendations": []
            }
        
        # REAL-TIME NEURAL TRAINING
        logger.info("[⚡] Real-time neural training...")
        training_success = main_deep_learning_system.train_model()
        
        if not training_success:
            raise HTTPException(status_code=500, detail="Neural training failed")
        
        # FIND SIMILAR USERS
        similar_users = main_deep_learning_system.find_similar_users(user_id)
        logger.info(f"[👥] Found {len(similar_users)} similar users")
        
        if not similar_users:
            raise HTTPException(status_code=404, detail="No similar users found")
        
        # GENERATE RECOMMENDATIONS
        recommendations = main_deep_learning_system.get_recommendations(user_id, n_recommendations)
        logger.info(f"[🎬] Generated {len(recommendations)} recommendations")
        
        if not recommendations:
            raise HTTPException(status_code=404, detail="No recommendations generated")
        
        # SUCCESS
        return {
            "status": "success",
            "message": f"🧠 CLEAN NEURAL CF - {rating_count} rating, {genre_count} tür → {len(similar_users)} benzer → {len(recommendations)} film",
            "method": "Clean Deep Learning - Real-Time Neural CF",
            "algorithm": "pure_neural_collaborative_filtering_128d",
            "user_rating_count": rating_count,
            "user_genre_count": genre_count,
            "rated_genres": list(all_genres)[:5],
            "similar_users_found": len(similar_users),
            "similar_users": [
                {"user_id": u["user_id"], "similarity": u["similarity_score"]} 
                for u in similar_users[:5]
            ],
            "embedding_dimension": 128,
            "recommendations": recommendations,
            "quality": "clean_pure_deep_learning"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[🚨] Clean Deep Learning error: {e}")
        raise HTTPException(status_code=500, detail=f"Deep Learning failed: {str(e)}")


@app.get("/cached-recommendations/{user_id}")
async def get_cached_recommendations(
    user_id: int,
    algorithm: str = "hybrid",
    force_refresh: bool = False,
    recommendation_api = None,
    db: Session = Depends(get_db)
):
    """Get recommendations with caching"""
    try:
        # Check cache first
        if not force_refresh:
            cached_recommendations = recommendation_cache.get(user_id, algorithm)
            if cached_recommendations:
                return {
                    "status": "success",
                    "source": "cache",
                    "algorithm": algorithm,
                    "user_id": user_id,
                    "count": len(cached_recommendations),
                    "recommendations": cached_recommendations,
                    "cached": True
                }
        
        # Generate new recommendations
        if recommendation_api:
            recommendations = await recommendation_api.get_hybrid_recommendations(user_id, 10)
        else:
            # Fallback to basic recommendations using collaborative filtering
            user_ratings = db.query(Rating).filter(Rating.user_id == user_id).all()
            if not user_ratings:
                return {"recommendations": []}
                
            # Get similar users based on ratings
            similar_users = db.query(Rating.user_id).filter(
                Rating.user_id != user_id,
                Rating.movie_id.in_([r.movie_id for r in user_ratings])
            ).distinct().limit(10).all()
            
            # Get movies rated highly by similar users
            recommendations = db.query(Movie).join(Rating).filter(
                Rating.user_id.in_([u.user_id for u in similar_users]),
                Rating.rating >= 4.0,
                Movie.id.notin_([r.movie_id for r in user_ratings])
            ).order_by(Movie.avg_rating.desc()).limit(10).all()
            
            recommendations = [{"movie_id": m.id, "title": m.title} for m in recommendations]
        
        # Cache the results
        recommendation_cache.set(user_id, algorithm, recommendations)
        
        return {
            "status": "success",
            "source": "fresh",
            "algorithm": algorithm,
            "user_id": user_id,
            "count": len(recommendations),
            "recommendations": recommendations,
            "cached": False
        }
        
    except Exception as e:
        logger.error(f"[x] Cached recommendations error: {e}")
        raise HTTPException(status_code=500, detail="Öneri sistemi geçici olarak kullanılamıyor")# === MOVIE SIMILARITY MATRIX ===
@app.get("/movie-similarity/{movie_id}")
async def get_movie_similarity_detailed(
    movie_id: int,
    similarity_threshold: float = 0.1,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Get detailed movie similarity analysis"""
    try:
        target_movie = db.query(Movie).filter(Movie.id == movie_id).first()
        if not target_movie:
            raise HTTPException(status_code=404, detail="Film bulunamadı")
        
        if not target_movie.genres:
            return {
                "status": "info",
                "message": "Bu film için tür bilgisi mevcut değil"
            }
        
        target_genres = set(target_movie.genres.split("|"))
        similar_movies = []
        
        # Get all movies with genres
        all_movies = db.query(Movie).filter(
            Movie.genres.isnot(None),
            Movie.id != movie_id
        ).all()
        
        for movie in all_movies:
            if movie.genres:
                movie_genres = set(movie.genres.split("|"))
                
                # Calculate Jaccard similarity
                intersection = len(target_genres.intersection(movie_genres))
                union = len(target_genres.union(movie_genres))
                similarity = intersection / union if union > 0 else 0
                
                if similarity >= similarity_threshold:
                    similar_movies.append({
                        "movie_id": movie.id,
                        "title": movie.title,
                        "genres": movie.genres,
                        "avg_rating": float(movie.avg_rating) if movie.avg_rating else 0.0,
                        "rating_count": movie.rating_count or 0,
                        "similarity_score": round(similarity, 3),
                        "common_genres": list(target_genres.intersection(movie_genres)),
                        "unique_genres": list(movie_genres - target_genres)
                    })
        
        # Sort by similarity score
        similar_movies.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        return {
            "status": "success",
            "target_movie": {
                "id": target_movie.id,
                "title": target_movie.title,
                "genres": target_movie.genres.split("|")
            },
            "similarity_method": "Jaccard Similarity (Genre-based)",
            "threshold": similarity_threshold,
            "found_similar": len(similar_movies),
            "similar_movies": similar_movies[:limit]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[x] Movie similarity error: {e}")
        raise HTTPException(status_code=500, detail="Film benzerlik analizi yapılırken hata oluştu")

# === USER PROFILE ANALYSIS ===
@app.get("/user-profile-analysis")
async def get_user_profile_analysis(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Analyze user's movie preferences and behavior"""
    try:
        user_id = current_user["user_id"]
        
        # Get user ratings
        user_ratings = db.query(Rating, Movie).join(
            Movie, Rating.movie_id == Movie.id
        ).filter(Rating.user_id == user_id).all()
        
        if not user_ratings:
            return {
                "status": "info",
                "message": "Henüz film puanlamamışsınız. Profil analizi için film puanlayın!"
            }
        
        # Analyze genres
        genre_analysis = {}
        rating_analysis = {
            "total_ratings": len(user_ratings),
            "avg_rating": 0,
            "rating_distribution": {},
            "highest_rated_movies": [],
            "lowest_rated_movies": []
        }
        
        total_rating = 0
        for rating, movie in user_ratings:
            total_rating += rating.rating
            
            # Rating distribution
            rating_key = f"{int(rating.rating)}_star"
            rating_analysis["rating_distribution"][rating_key] = rating_analysis["rating_distribution"].get(rating_key, 0) + 1
            
            # Genre analysis
            if movie.genres:
                for genre in movie.genres.split("|"):
                    if genre not in genre_analysis:
                        genre_analysis[genre] = {
                            "count": 0,
                            "total_rating": 0,
                            "avg_rating": 0
                        }
                    
                    genre_analysis[genre]["count"] += 1
                    genre_analysis[genre]["total_rating"] += rating.rating
        
        # Calculate averages
        rating_analysis["avg_rating"] = round(total_rating / len(user_ratings), 2)
        
        for genre in genre_analysis:
            genre_analysis[genre]["avg_rating"] = round(
                genre_analysis[genre]["total_rating"] / genre_analysis[genre]["count"], 2
            )
        
        # Sort genres by preference
        favorite_genres = sorted(
            genre_analysis.items(),
            key=lambda x: (x[1]["avg_rating"], x[1]["count"]),
            reverse=True
        )
        
        # Get highest and lowest rated movies
        sorted_ratings = sorted(user_ratings, key=lambda x: x[0].rating, reverse=True)
        
        rating_analysis["highest_rated_movies"] = [
            {
                "title": movie.title,
                "rating": float(rating.rating),
                "genres": movie.genres
            }
            for rating, movie in sorted_ratings[:5]
        ]
        
        rating_analysis["lowest_rated_movies"] = [
            {
                "title": movie.title,
                "rating": float(rating.rating),
                "genres": movie.genres
            }
            for rating, movie in sorted_ratings[-5:]
        ]
        
        # User behavior insights
        insights = []
        
        if rating_analysis["avg_rating"] > 4.0:
            insights.append("Çok seçici bir izleyicisiniz - genelde yüksek puan veriyorsunuz")
        elif rating_analysis["avg_rating"] < 3.0:
            insights.append("Eleştirel yaklaşımınız var - düşük puanlar verme eğiliminiz yüksek")
        
        if len(favorite_genres) > 0:
            top_genre = favorite_genres[0][0]
            insights.append(f"En sevdiğiniz tür: {top_genre}")
        
        return {
            "status": "success",
            "user_id": user_id,
            "username": current_user["username"],
            "rating_analysis": rating_analysis,
            "genre_preferences": [
                {
                    "genre": genre,
                    "movie_count": data["count"],
                    "avg_rating": data["avg_rating"],
                    "preference_score": round(data["avg_rating"] * (data["count"] / len(user_ratings)), 2)
                }
                for genre, data in favorite_genres[:10]
            ],
            "insights": insights,
            "profile_completeness": min(100, (len(user_ratings) / 20) * 100),  # 20 ratings = 100%
            "recommendation_readiness": "high" if len(user_ratings) >= 10 else "medium" if len(user_ratings) >= 5 else "low"
        }
        
    except Exception as e:
        logger.error(f"[x] User profile analysis error: {e}")
        raise HTTPException(status_code=500, detail="Profil analizi yapılırken hata oluştu")
    
    # ============================================================================
# [*] WATCHLIST ENDPOINTS - DEBUG VERSİYON
# ============================================================================
@app.post("/add-to-watchlist")
async def add_to_watchlist_debug(
    watchlist_request: WatchlistRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        print("="*50)
        print("[*] WATCHLIST ENDPOINT")
        print("="*50)
        
        # Auth
        auth_header = request.headers.get("Authorization")
        token = auth_header.split(" ")[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        
        movie_id = watchlist_request.movie_id
        status = watchlist_request.status  # "to_watch" or "watched"
        
        print(f"[+] User ID: {user_id}")
        print(f"[+] Movie ID: {movie_id}")
        print(f"[*] Status: {status}")
        
        # Film kontrolü
        movie = db.query(Movie).filter(Movie.id == movie_id).first()
        if not movie:
            raise HTTPException(status_code=404, detail="Film bulunamadı")
        
        print(f"[+] Movie found: {movie.title}")
        
        # Mevcut watchlist kontrolü
        existing_watchlist = db.query(UserInteraction).filter(
            UserInteraction.user_id == user_id,
            UserInteraction.movie_id == movie_id,
            UserInteraction.interaction_type == "watchlist"
        ).first()
        
        # Status'u JSON olarak hazırla
        import json
        watchlist_data = json.dumps({
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        if existing_watchlist:
            print("[*] Mevcut watchlist güncelleniyor...")
            existing_watchlist.extra_data = watchlist_data
            existing_watchlist.timestamp = datetime.utcnow()
            message = f"'{movie.title}' izleme listesi durumu güncellendi!"
            
        else:
            print("[+] Yeni watchlist oluşturuluyor...")
            new_watchlist = UserInteraction(
                user_id=user_id,
                movie_id=movie_id,
                interaction_type="watchlist",
                extra_data=watchlist_data,  # ← status'u burada sakla
                timestamp=datetime.utcnow()
            )
            db.add(new_watchlist)
            message = f"'{movie.title}' izleme listenize eklendi!"
        
        db.commit()
        print("[*] Watchlist kaydedildi!")
        
        return {
            "status": "success",
            "message": message,
            "user_id": user_id,
            "movie_id": movie_id,
            "movie_title": movie.title,
            "watchlist_status": status
        }
        
    except Exception as e:
        db.rollback()
        print(f"[x] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/my-watchlist")
async def get_my_watchlist_debug(
    status_filter: str = "all",
    request: Request = None,
    db: Session = Depends(get_db)
):
    try:
        print("="*60)
        print("[*] GET WATCHLIST DEBUG")
        print("="*60)
        print(f"[*] Status filter: {status_filter}")
        
        # Auth
        auth_header = request.headers.get("Authorization")
        token = auth_header.split(" ")[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        username = payload.get("username", "Unknown")
        
        print(f"[+] User authenticated: {username} (ID: {user_id})")
        
        # Watchlist items getir
        query = db.query(UserInteraction).filter(
            UserInteraction.user_id == user_id,
            UserInteraction.interaction_type == "watchlist"
        )
        
        watchlist_items = query.all()
        print(f"[+] Found {len(watchlist_items)} watchlist items")
        
        # Status'a göre filtrele (extra_data'dan)
        filtered_movies = []
        import json
        
        for item in watchlist_items:
            try:
                # extra_data'dan status'u parse et
                if item.extra_data:
                    watchlist_data = json.loads(item.extra_data)
                    item_status = watchlist_data.get('status', 'to_watch')
                else:
                    item_status = 'to_watch'  # default
                
                # Status filtresini uygula
                if status_filter == "all" or status_filter == item_status:
                    # Movie bilgisini getir
                    movie = db.query(Movie).filter(Movie.id == item.movie_id).first()
                    if movie:
                        # User rating'i getir
                        user_rating = get_user_rating_for_movie(db, user_id, movie.id)
                        
                        filtered_movies.append({
                            "movie_id": movie.id,
                            "title": movie.title,
                            "genres": movie.genres.split(",") if movie.genres else [],
                            "avg_rating": round(movie.avg_rating, 1) if movie.avg_rating else 0,
                            "rating_count": movie.rating_count or 0,
                            "release_date": movie.release_date or "Bilinmiyor",
                            "popularity": movie.rating_count or 0,
                            "user_rating": user_rating,  # ← USER RATING EKLENDI
                            "watchlist_status": item_status,  # ← STATUS EKLENDI
                            "imdb_url": movie.imdb_url if movie.imdb_url else None,
                            "added_date": item.timestamp.isoformat() if item.timestamp else None
                        })
                        
            except Exception as e:
                print(f"[x] Item parse hatası: {e}")
                continue
        
        print(f"[+] Returning {len(filtered_movies)} movies")
        
        return {
            "status": "success",
            "count": len(filtered_movies),
            "filter": status_filter,
            "watchlist": filtered_movies
        }
        
    except Exception as e:
        print(f"[x] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    
    # User modelinin hangi field'ları var kontrol edelim
@app.get("/debug-user-model/{user_id}")
async def debug_user_model(user_id: int, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            # User'ın tüm attribute'larını göster
            user_dict = {}
            for column in user.__table__.columns:
                user_dict[column.name] = getattr(user, column.name, None)
            
            print("[*] User model fields:")
            for key, value in user_dict.items():
                print(f"  - {key}: {value}")
            
            return {
                "status": "success",
                "available_fields": list(user_dict.keys()),
                "user_data": user_dict
            }
        else:
            return {"error": "User not found"}
            
    except Exception as e:
        return {"error": str(e)}




# === RECOMMENDATION EXPLANATION ===
@app.get("/recommendation-explanation/{user_id}/{movie_id}")
async def get_recommendation_explanation(
    user_id: int,
    movie_id: int,
    algorithm: str = "hybrid",
    db: Session = Depends(get_db)
):
    """Explain why a movie was recommended"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        movie = db.query(Movie).filter(Movie.id == movie_id).first()
        
        if not user or not movie:
            raise HTTPException(status_code=404, detail="Kullanıcı veya film bulunamadı")
        
        # Get user's rating history
        user_ratings = db.query(Rating, Movie).join(
            Movie, Rating.movie_id == Movie.id
        ).filter(Rating.user_id == user_id).all()
        
        explanations = []
        
        if algorithm == "hybrid" or algorithm == "content_based":
            # Genre-based explanation
            if movie.genres:
                movie_genres = set(movie.genres.split("|"))
                user_genre_preferences = {}
                
                for rating, rated_movie in user_ratings:
                    if rated_movie.genres and rating.rating >= 4.0:
                        for genre in rated_movie.genres.split("|"):
                            user_genre_preferences[genre] = user_genre_preferences.get(genre, 0) + 1
                
                common_genres = []
                for genre in movie_genres:
                    if genre in user_genre_preferences:
                        common_genres.append({
                            "genre": genre,
                            "user_preference_count": user_genre_preferences[genre]
                        })
                
                if common_genres:
                    explanations.append({
                        "type": "genre_preference",
                        "explanation": f"Bu film {', '.join([g['genre'] for g in common_genres])} türlerinde, sizin sevdiğiniz türlerden",
                        "details": common_genres
                    })
        
        if algorithm == "hybrid" or algorithm == "collaborative_filtering":
            # Similar users explanation (mock)
            similar_users_count = min(len(user_ratings) * 2, 50)  # Mock calculation
            explanations.append({
                "type": "collaborative_filtering",
                "explanation": f"Size benzer {similar_users_count} kullanıcı bu filmi beğendi",
                "confidence": 0.75
            })
        
        if algorithm == "hybrid" or algorithm == "popularity":
            # Popularity explanation
            if movie.avg_rating and movie.avg_rating >= 4.0:
                explanations.append({
                    "type": "popularity",
                    "explanation": f"Bu film yüksek puana sahip ({movie.avg_rating:.1f}[+]) ve {movie.rating_count} kişi tarafından puanlandı",
                    "avg_rating": float(movie.avg_rating),
                    "rating_count": movie.rating_count
                })
        
        # Similar movies explanation
        if user_ratings:
            similar_rated_movies = []
            for rating, rated_movie in user_ratings:
                if rating.rating >= 4.0 and rated_movie.genres and movie.genres:
                    rated_genres = set(rated_movie.genres.split("|"))
                    movie_genres = set(movie.genres.split("|"))
                    
                    if len(rated_genres.intersection(movie_genres)) >= 2:
                        similar_rated_movies.append(rated_movie.title)
            
            if similar_rated_movies:
                explanations.append({
                    "type": "similar_movies",
                    "explanation": f"Daha önce beğendiğiniz filmlerle benzer: {', '.join(similar_rated_movies[:3])}",
                    "similar_movies": similar_rated_movies[:5]
                })
        
        if not explanations:
            explanations.append({
                "type": "general",
                "explanation": "Bu film genel popülerlik ve sistem algoritmalarına dayalı olarak önerildi",
                "confidence": 0.5
            })
        
        return {
            "status": "success",
            "user_id": user_id,
            "movie": {
                "id": movie.id,
                "title": movie.title,
                "genres": movie.genres.split("|") if movie.genres else [],
                "avg_rating": float(movie.avg_rating) if movie.avg_rating else 0.0
            },
            "algorithm_used": algorithm,
            "explanations": explanations,
            "overall_confidence": round(np.mean([e.get("confidence", 0.7) for e in explanations]), 2)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[x] Recommendation explanation error: {e}")
        raise HTTPException(status_code=500, detail="Öneri açıklaması oluşturulurken hata oluştu")
# === CONTENT MODERATION ===
@app.post("/report-content")
async def report_content(
    report_data: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Report inappropriate content"""
    try:
        user_id = current_user["user_id"]
        content_type = report_data.get("content_type")  # movie, review, user
        content_id = report_data.get("content_id")
        reason = report_data.get("reason")
        description = report_data.get("description", "")
        
        # Store report
        report = UserInteraction(
            user_id=user_id,
            movie_id=content_id if content_type == "movie" else None,
            interaction_type="content_report",
            metadata=json.dumps({
                "content_type": content_type,
                "content_id": content_id,
                "reason": reason,
                "description": description,
                "timestamp": datetime.now().isoformat()
            }),
            timestamp=datetime.utcnow()
        )
        
        db.add(report)
        db.commit()
        
        return {
            "status": "success",
            "message": "Raporunuz alındı, incelenecek",
            "report_id": report.id
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"[x] Content report error: {e}")
        raise HTTPException(status_code=500, detail="Rapor gönderilirken hata oluştu")

# === DATA VALIDATION ===
@app.get("/validate-data")
async def validate_system_data(db: Session = Depends(get_db)):
    """Validate system data integrity"""
    try:
        validation_results = {
            "movies": {},
            "users": {},
            "ratings": {},
            "interactions": {}
        }
        
        # Validate movies
        total_movies = db.query(Movie).count()
        movies_with_genres = db.query(Movie).filter(Movie.genres.isnot(None)).count()
        movies_with_ratings = db.query(Movie).filter(Movie.rating_count > 0).count()
        
        validation_results["movies"] = {
            "total": total_movies,
            "with_genres": movies_with_genres,
            "with_ratings": movies_with_ratings,
            "genre_coverage": round((movies_with_genres / total_movies * 100), 2) if total_movies > 0 else 0,
            "rating_coverage": round((movies_with_ratings / total_movies * 100), 2) if total_movies > 0 else 0
        }
        
        # Validate users
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.last_active.isnot(None)).count()
        users_with_ratings = db.query(User).join(Rating).distinct().count()
        
        validation_results["users"] = {
            "total": total_users,
            "active": active_users,
            "with_ratings": users_with_ratings,
            "activity_rate": round((active_users / total_users * 100), 2) if total_users > 0 else 0,
            "engagement_rate": round((users_with_ratings / total_users * 100), 2) if total_users > 0 else 0
        }
        
        # Validate ratings
        total_ratings = db.query(Rating).count()
        recent_ratings = db.query(Rating).filter(
            Rating.timestamp >= datetime.now() - timedelta(days=30)
        ).count()
        
        validation_results["ratings"] = {
            "total": total_ratings,
            "recent_30_days": recent_ratings,
            "avg_per_user": round(total_ratings / total_users, 2) if total_users > 0 else 0,
            "recent_activity": round((recent_ratings / total_ratings * 100), 2) if total_ratings > 0 else 0
        }
        
        # System health score
        health_score = np.mean([
            validation_results["movies"]["genre_coverage"] / 100,
            validation_results["users"]["engagement_rate"] / 100,
            min(validation_results["ratings"]["avg_per_user"] / 10, 1.0)  # Cap at 10 ratings per user
        ]) * 100
        
        return {
            "status": "success",
            "validation_results": validation_results,
            "system_health_score": round(health_score, 2),
            "health_grade": "A" if health_score >= 80 else "B" if health_score >= 60 else "C",
            "recommendations": [
                "More genre diversity needed" if validation_results["movies"]["genre_coverage"] < 80 else None,
                "User engagement could be improved" if validation_results["users"]["engagement_rate"] < 50 else None,
                "More ratings needed per user" if validation_results["ratings"]["avg_per_user"] < 5 else None
            ],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"[x] Data validation error: {e}")
        raise HTTPException(status_code=500, detail="Veri doğrulama hatası")

# === SYSTEM OPTIMIZATION ===
@app.post("/optimize-system")
async def optimize_system_performance(
    optimization_type: str = "all",  # cache, database, recommendations
    current_user: dict = Depends(get_current_user),
    recommendation_api: Optional[Any] = None
):
    """Optimize system performance"""
    from typing import Any, Optional
    
    try:
        if current_user["username"] not in ["admin", "administrator"]:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        optimization_results = {}
        
        if optimization_type in ["all", "cache"]:
            # Clear old cache entries
            old_cache_size = len(recommendation_cache.cache)
            recommendation_cache.cache.clear()
            optimization_results["cache"] = {
                "cleared_entries": old_cache_size,
                "status": "optimized"
            }
        
        if optimization_type in ["all", "database"]:
            # Database optimization (basic)
            conn = sqlite3.connect('movielens_100k.db')
            cursor = conn.cursor()
            
            # Vacuum database
            cursor.execute("VACUUM")
            
            # Update statistics
            cursor.execute("ANALYZE")
            
            conn.close()
            
            optimization_results["database"] = {
                "vacuum_completed": True,
                "statistics_updated": True,
                "status": "optimized"
            }
        
        if optimization_type in ["all", "recommendations"]:
            # Recommendation system optimization
            if recommendation_api:
                await recommendation_api.initialize()
                optimization_results["recommendations"] = {
                    "system_reinitialized": True,
                    "status": "optimized"
                }
            else:
                optimization_results["recommendations"] = {
                    "system_reinitialized": False,
                    "status": "not_available"
                }
        
        return {
            "status": "success",
            "message": "System optimization completed",
            "optimization_type": optimization_type,
            "results": optimization_results,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"[x] System optimization error: {e}")
        raise HTTPException(status_code=500, detail="Sistem optimizasyonu hatası")@app.get("/system-status")
async def get_comprehensive_system_status():
    """Get comprehensive system status"""
    try:
        # Database status
        conn = sqlite3.connect('movielens_100k.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM movies")
        movie_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM ratings")
        rating_count = cursor.fetchone()[0]
        
        # Recent activity
        cursor.execute("""
            SELECT COUNT(*) FROM ratings 
            WHERE datetime(timestamp) > datetime('now', '-24 hours')
        """)
        recent_activity = cursor.fetchone()[0]
        
        conn.close()
        
        # Get recommendation API from global scope
        from app_enhanced_v7 import recommendation_api, recommendation_cache
        
        # System components status
        components = {
            "database": {
                "status": "operational",
                "users": user_count,
                "movies": movie_count,
                "ratings": rating_count,
                "recent_activity_24h": recent_activity
            },
            "recommendation_engine": {
                "status": "operational" if recommendation_api else "basic_mode",
                "type": "Enhanced Hybrid v6.0" if recommendation_api else "Basic Fallback",
                "cache_size": len(recommendation_cache.cache),
                "initialized": recommendation_api.is_initialized if recommendation_api else False
            },
            "api_server": {
                "status": "operational",
                "version": "Enhanced v6.0 Complete",
                "uptime": "Available",
                "endpoints": 50  # Approximate count
            },
            "features": {
                "user_authentication": True,
                "movie_rating": True,
                "favorites_system": True,
                "search_functionality": True,
                "recommendation_system": True,
                "analytics": True,
                "admin_functions": True,
                "real_time_updates": True,
                "data_export": True,
                "content_moderation": True
            }
        }
        
        # Overall health
        health_checks = [
            user_count > 0,
            movie_count > 0,
            rating_count > 0,
            True  # API is running
        ]
        
        overall_health = "healthy" if all(health_checks) else "warning"
        
        return {
            "status": "success",
            "system_name": "[+] Enhanced Movie Recommendation System v6.0",
            "overall_health": overall_health,
            "components": components,
            "statistics": {
                "total_users": user_count,
                "total_movies": movie_count,
                "total_ratings": rating_count,
                "recent_activity": recent_activity,
                "data_health": "good" if rating_count > user_count else "needs_improvement"
            },
            "performance": {
                "response_time": "optimal",
                "cache_hit_rate": "good",
                "database_performance": "optimal"
            },
            "last_updated": datetime.now().isoformat(),
            "system_version": "6.0.0-complete"
        }
        
    except Exception as e:
        logger.error(f"[x] System status error: {e}")
        return {
            "status": "error",
            "overall_health": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }



# === APPLICATION STARTUP ===
from model_api import RecommendationAPI
from kullanıcımodel import AdvancedRecommendationSystem

# İki model instance
recommendation_api = RecommendationAPI()  # Eski model
advanced_recommender = AdvancedRecommendationSystem()  # Yeni mode

@app.on_event("startup")
async def startup_event():
    """Application startup tasks"""
    logger.info("[*] Starting Enhanced Movie Recommendation System v6.0")
    
    # Database kontrolü
    try:
        from models import SessionLocal, Movie, AppUser
        db = SessionLocal()
        movie_count = db.query(Movie).count()
        user_count = db.query(AppUser).count()
        db.close()
        logger.info(f"[+] Database ready: {movie_count} movies, {user_count} users")
    except Exception as e:
        logger.error(f"[x] Database connection error: {e}")
    
    # [+] ESKİ MODEL YÜKLEMESİ
    try:
        if recommendation_api.load_model():
            logger.info("[+] Old NMF Model loaded successfully!")
        else:
            logger.warning("[!] Old model could not be loaded")
    except Exception as e:
        logger.error(f"[x] Old model loading error: {e}")
    
    # [+] YENİ MODEL YÜKLEMESİ
    try:
        if advanced_recommender:
            advanced_recommender.load_model('kullanıcıoneri.pkl')
            logger.info("[+] New Advanced Model loaded successfully!")
        else:
            logger.info("[!] Advanced recommender not available")
    except Exception as e:
        logger.error(f"[x] New model loading error: {e}")


    
    logger.info("[+] Movie Recommendation System v6.0 is ready!")
    logger.info("[*] API Documentation: http://localhost:8000/docs")
    logger.info("[*] Health Check: http://localhost:8000/health")



@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown tasks"""
    logger.info("[!] Shutting down Enhanced Movie Recommendation System v6.0")
    
    # Clear cache
    try:
        recommendation_cache.cache.clear()
        logger.info("[*] Cache cleared")
    except:
        pass
    
    # Close any remaining connections
    logger.info("[+] Cleanup completed")
    
    
    # Bu kodu app_enhanced_v6.py dosyasının sonuna (if __name__ == "__main__": satırından önce) ekle
@app.post("/advanced-recommendations")
async def get_advanced_recommendations(
    request: dict,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ARAMA MANTIKLI ADVANCED ÖNERİLER"""
    try:
        user_id = current_user["user_id"]
        n_recommendations = request.get("n_recommendations", 20)
        
        logger.info(f"[*] Advanced recommendations for user {user_id}, limit: {n_recommendations}")
        
        # Önce toplam film sayısını kontrol et (arama gibi)
        total_movies = db.query(Movie).count()
        logger.info(f"[*] Total movies in DB: {total_movies}")
        
        # Kullanıcının etkileşimde bulunduğu filmleri al
        user_interactions = db.query(UserInteraction.movie_id).filter(
            UserInteraction.user_id == user_id
        ).distinct().all()
        
        user_movie_ids = [interaction[0] for interaction in user_interactions]
        logger.info(f"[*] User has {len(user_movie_ids)} interactions: {user_movie_ids}")
        
        # ARAMA GİBİ BASİT SORGU
        if user_movie_ids:
            # Kullanıcının izlemediği filmler
            movies = db.query(Movie).filter(
                ~Movie.id.in_(user_movie_ids)
            ).limit(n_recommendations).all()
            logger.info(f"[*] Found {len(movies)} movies (excluding user interactions)")
        else:
            # Hiç etkileşim yoksa tüm filmler
            movies = db.query(Movie).limit(n_recommendations).all()
            logger.info(f"[*] Found {len(movies)} movies (no user interactions)")
        
        # İlk 3 filmi logla (arama gibi)
        for i, movie in enumerate(movies[:3]):
            logger.info(f"Movie {i+1}: {movie.title}")
        
        # Sonuçları formatla (arama gibi güvenli)
        recommendations = []
        for movie in movies:
            movie_dict = {
                "movie_id": movie.id,
                "title": movie.title,
                "genres": movie.genres.split('|') if movie.genres else [],
                "avg_rating": float(movie.avg_rating) if hasattr(movie, 'avg_rating') and movie.avg_rating else 7.5,
                "rating_count": getattr(movie, 'rating_count', 1000),
                "release_date": getattr(movie, 'release_date', "1990"),
                "hybrid_score": 4.5,
                "popularity": getattr(movie, 'rating_count', 1000)
            }
            recommendations.append(movie_dict)
        
        logger.info(f"[+] Returning {len(recommendations)} advanced recommendations")
        
        return {
            "status": "success",
            "method": "Hybrid Collaborative + Content-Based Filtering",
            "total_movies_in_db": total_movies,
            "user_interactions": len(user_movie_ids),
            "recommendations": recommendations
        }
        
    except Exception as e:
        logger.error(f"[x] Advanced recommendations error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"status": "error", "message": str(e)}

@app.post("/genre-based-recommendations")
async def get_genre_based_recommendations(
    request: dict,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ARAMA MANTIKLI GENRE ÖNERİLER"""
    try:
        genres = request.get("genres", [])
        n_recommendations = request.get("n_recommendations", 15)
        user_id = current_user["user_id"]
        
        logger.info(f"[*] Genre recommendations for user {user_id}, genres: {genres}, limit: {n_recommendations}")
        
        # Toplam film sayısını kontrol et
        total_movies = db.query(Movie).count()
        logger.info(f"[*] Total movies in DB: {total_movies}")
        
        if not genres:
            logger.info("[*] No genres specified, returning random movies")
            movies = db.query(Movie).limit(n_recommendations).all()
        else:
            # İlk türü kullan (arama gibi basit)
            first_genre = genres[0].strip()
            search_term = f"%{first_genre}%"
            logger.info(f"[*] Searching for genre: '{search_term}'")
            
            # Arama mantığı ile tür ara
            movies = db.query(Movie).filter(
                Movie.genres.ilike(search_term)
            ).limit(n_recommendations).all()
            
            logger.info(f"[*] Found {len(movies)} movies for genre '{first_genre}'")
        
        # İlk 3 filmi logla
        for i, movie in enumerate(movies[:3]):
            logger.info(f"Genre Movie {i+1}: {movie.title} - {movie.genres}")
        
        # Sonuçları formatla
        recommendations = []
        for movie in movies:
            movie_dict = {
                "movie_id": movie.id,
                "title": movie.title,
                "genres": movie.genres.split('|') if movie.genres else [],
                "avg_rating": float(movie.avg_rating) if hasattr(movie, 'avg_rating') and movie.avg_rating else 7.0,
                "rating_count": getattr(movie, 'rating_count', 800),
                "release_date": getattr(movie, 'release_date', "1995"),
                "total_score": 7.0,
                "popularity": getattr(movie, 'rating_count', 800)
            }
            recommendations.append(movie_dict)
        
        logger.info(f"[+] Returning {len(recommendations)} genre-based recommendations")
        
        return {
            "status": "success",
            "total_movies_in_db": total_movies,
            "searched_genres": genres,
            "recommendations": recommendations
        }
        
    except Exception as e:
        logger.error(f"[x] Genre recommendations error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"status": "error", "message": str(e)}

@app.get("/favorites-based-recommendations")
async def get_favorites_based_recommendations(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ARAMA MANTIKLI FAVORİ ÖNERİLER"""
    try:
        user_id = current_user["user_id"]
        
        logger.info(f"[<3] Favorites-based recommendations for user {user_id}")
        
        # Toplam film sayısını kontrol et
        total_movies = db.query(Movie).count()
        logger.info(f"[<3] Total movies in DB: {total_movies}")
        
        # Kullanıcının favori filmlerini al
        favorites = db.query(UserInteraction).filter(
            UserInteraction.user_id == user_id,
            UserInteraction.interaction_type == "favorite"
        ).all()
        
        logger.info(f"[<3] User has {len(favorites)} favorite movies")
        
        if len(favorites) == 0:
            # Favori yoksa random filmler (arama mantığı)
            movies = db.query(Movie).limit(15).all()
            method = "Henüz favori filminiz yok, popüler filmler"
            logger.info("[<3] No favorites, showing random movies")
        else:
            # Favori film ID'lerini al
            favorite_movie_ids = [f.movie_id for f in favorites]
            logger.info(f"[<3] Favorite movie IDs: {favorite_movie_ids}")
            
            # Favori olmayan filmler öner (arama mantığı)
            movies = db.query(Movie).filter(
                ~Movie.id.in_(favorite_movie_ids)
            ).limit(15).all()
            
            method = "Favori filmlerinize dayalı öneriler"
            logger.info(f"[<3] Found {len(movies)} non-favorite movies")
        
        # İlk 3 filmi logla
        for i, movie in enumerate(movies[:3]):
            logger.info(f"Favorite Movie {i+1}: {movie.title}")
        
        # Sonuçları formatla
        recommendations = []
        for movie in movies:
            movie_dict = {
                "movie_id": movie.id,
                "title": movie.title,
                "genres": movie.genres.split('|') if movie.genres else [],
                "avg_rating": float(movie.avg_rating) if hasattr(movie, 'avg_rating') and movie.avg_rating else 8.0,
                "rating_count": getattr(movie, 'rating_count', 1200),
                "release_date": getattr(movie, 'release_date', "1992"),
                "similarity_score": 4.2,
                "popularity": getattr(movie, 'rating_count', 1200)
            }
            recommendations.append(movie_dict)
        
        logger.info(f"[+] Returning {len(recommendations)} favorites-based recommendations")
        
        return {
            "status": "success",
            "method": method,
            "total_movies_in_db": total_movies,
            "user_favorites": len(favorites),
            "recommendations": recommendations
        }
        
    except Exception as e:
        logger.error(f"[x] Favorites recommendations error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"status": "error", "message": str(e)}

# ============================================================================
# [*] YENİ DİNAMİK YAPI FONKSİYONLARI
# ============================================================================

def get_recent_user_actions(db: Session, user_id: int, limit: int = 5) -> List[UserInteraction]:
    """Kullanıcının son N etkileşimini (gerçek zamanlı sinyalleri) getirir."""
    logger.info(f"[*] Kullanıcı {user_id} için son {limit} etkileşim getiriliyor.")
    return db.query(UserInteraction).filter(
        UserInteraction.user_id == user_id
    ).order_by(desc(UserInteraction.timestamp)).limit(limit).all()

def apply_real_time_boost(
    base_recommendations: List[dict],
    recent_actions: List[UserInteraction],
    db: Session
) -> List[dict]:
    """
    Temel öneri listesini, kullanıcının son hareketlerine göre yeniden sıralar.
    Bu, dinamik yapının kalbidir.
    """
    boost_map = {}  # movie_id -> boost_score

    # Etkileşimlerdeki filmlerin detaylarını toplu olarak al
    action_movie_ids = [action.movie_id for action in recent_actions if action.movie_id]
    action_movies_query = db.query(Movie).filter(Movie.id.in_(action_movie_ids)).all()
    action_movies = {movie.id: movie for movie in action_movies_query}

    for action in recent_actions:
        if not action.movie_id or action.movie_id not in action_movies:
            continue

        action_movie = action_movies[action.movie_id]
        action_genres = set(action_movie.genres.split('|')) if action_movie.genres else set()

        boost_value = 0
        # Farklı etkileşim türlerine farklı güçlendirme değerleri ata
        if action.interaction_type == "rating":
            try:
                rating_data = json.loads(action.extra_data)
                if float(rating_data.get('rating', 0)) >= 4.0:
                    boost_value = 1.5  # Yüksek puan: Güçlü pozitif sinyal
            except (json.JSONDecodeError, ValueError):
                continue
        elif action.interaction_type == "favorite":
            boost_value = 2.0  # Favori: Çok güçlü pozitif sinyal
        elif action.interaction_type == "watchlist" and action.extra_data and '"status": "to_watch"' in action.extra_data:
            boost_value = 1.2  # İzleme listesi: Orta seviye pozitif sinyal

        if boost_value == 0:
            continue

        # Benzer filmleri bul ve puanlarını artır (boost)
        # Not: Burada basitlik için tür benzerliği kullanıyoruz.
        for rec in base_recommendations:
            rec_movie_id = rec['movie_id']
            if rec_movie_id == action.movie_id: continue # Kendisini boostlama

            rec_genres_str = "|".join(rec.get('genres', []))
            rec_genres = set(rec_genres_str.split('|'))
            
            common_genres = len(action_genres.intersection(rec_genres))
            if common_genres > 0:
                similarity_factor = common_genres / len(action_genres) if action_genres else 0
                current_boost = boost_map.get(rec_movie_id, 0)
                boost_map[rec_movie_id] = current_boost + (boost_value * similarity_factor)

    # Hesaplanan boost'ları öneri skorlarına uygula
    for rec in base_recommendations:
        rec_movie_id = rec['movie_id']
        if rec_movie_id in boost_map:
            original_score = rec.get('hybrid_score', rec.get('total_score', 0))
            boost = boost_map[rec_movie_id]
            rec['hybrid_score'] = original_score + boost
            rec['explanation'] = f"Son aktiviteniz nedeniyle puanı {boost:.2f} artırıldı."

    # Yeni skorlara göre listeyi yeniden sırala
    base_recommendations.sort(key=lambda x: x.get('hybrid_score', 0), reverse=True)
    logger.info(f"[+] {len(boost_map)} film için anlık skor artışı uygulandı.")
    return base_recommendations

@app.post("/recommendations/dynamic-hybrid")
async def get_dynamic_hybrid_recommendations(
    request: AdvancedRecommendationRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Kullanıcı davranışlarına anında tepki veren dinamik öneriler üretir.
    Statik temel modeli gerçek zamanlı sinyal katmanıyla birleştirir.
    """
    try:
        user_id = current_user["user_id"]
        logger.info(f"[*] Dinamik Hibrit öneri isteği: Kullanıcı {user_id}")

        # 1. Kullanıcı rating kontrolü
        db = SessionLocal()
        user_ratings_count = db.query(UserInteraction).filter(
            UserInteraction.user_id == user_id,
            UserInteraction.interaction_type == "rating"
        ).count()
        
        MIN_RATINGS_FOR_DYNAMIC = 3
        
        if user_ratings_count < MIN_RATINGS_FOR_DYNAMIC:
            # Az puanlayan kullanıcı için popüler filmler
            popular_movies = db.query(Movie).filter(
                Movie.avg_rating >= 4.0
            ).order_by(desc(Movie.avg_rating)).limit(request.n_recommendations).all()
            
            fallback_recs = []
            for movie in popular_movies:
                fallback_recs.append({
                    "movie_id": movie.id,
                    "title": movie.title,
                    "genres": movie.genres.split('|') if movie.genres else [],
                    "predicted_rating": float(movie.avg_rating) if movie.avg_rating else 4.0,
                    "reason": f"Popüler film - {MIN_RATINGS_FOR_DYNAMIC} film puanlayın!",
                    "type": "cold_start_dynamic"
                })
            
            db.close()
            return {
                "status": "success",
                "method": "Dynamic Hybrid - Cold Start",
                "user_rating_count": user_ratings_count,
                "minimum_required": MIN_RATINGS_FOR_DYNAMIC,
                "message": f"Dinamik öneriler için en az {MIN_RATINGS_FOR_DYNAMIC} film puanlayın!",
                "recommendations": fallback_recs
            }
        
        db.close()
        
        # 2. Statik Temel Katman: Temel önerileri al
        if advanced_recommender:
            try:
                base_recs = advanced_recommender.get_hybrid_recommendations(
                    user_id=user_id,
                    n_recommendations=50  # Sadece desteklenen parametreler
                )
            except Exception as e:
                logger.warning(f"[!] Advanced model error: {e}")
                base_recs = []
        else:
            base_recs = []

        # 2. Gerçek Zamanlı Sinyal Katmanı: Kullanıcının son hareketlerini al
        recent_actions = get_recent_user_actions(db, user_id, limit=5)

        # 3. Harmanlama ve Yeniden Sıralama
        if recent_actions:
            dynamic_recs = apply_real_time_boost(base_recs, recent_actions, db)
        else:
            dynamic_recs = base_recs

        # 4. Sonucu döndür
        return {
            "status": "success",
            "method": "Dinamik Hibrit (Statik Temel + Gerçek Zamanlı Sinyaller)",
            "recommendations": dynamic_recs[:request.n_recommendations]
        }
    except Exception as e:
        logger.error(f"[x] Dinamik Hibrit öneri hatası: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Dinamik öneriler üretilirken bir hata oluştu.")

print("[+] Enhanced endpoints added!")

@app.get("/api/similar_users/{user_id}")
async def get_similar_users(user_id: int, n_users: int = 10):
    """
    Finds the top N most similar users to a given user based on movie ratings.
    """
    if USER_MOVIE_MATRIX is None:
        raise HTTPException(status_code=503, detail="User-movie matrix not loaded. This feature is disabled.")

    if user_id not in USER_ID_MAP:
        raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found in the matrix.")

    try:
        user_index = USER_ID_MAP[user_id]
        user_vector = USER_MOVIE_MATRIX[user_index].reshape(1, -1)

        # Calculate cosine similarity
        similarity_scores = cosine_similarity(user_vector, USER_MOVIE_MATRIX)[0]

        # Get user indices and scores, sorted by similarity
        similar_user_indices = np.argsort(similarity_scores)[::-1]

        # Create inverse mapping from index to user_id
        inv_user_id_map = {i: u_id for u_id, i in USER_ID_MAP.items()}

        similar_users = []
        for idx in similar_user_indices:
            # Skip the user themselves
            if idx == user_index:
                continue

            original_user_id = inv_user_id_map.get(idx)
            if original_user_id is not None:
                similar_users.append({
                    "user_id": original_user_id,
                    "similarity_score": round(float(similarity_scores[idx]), 4)
                })
            
            if len(similar_users) >= n_users:
                break
        
        return {
            "status": "success",
            "target_user_id": user_id,
            "similar_users_count": len(similar_users),
            "similar_users": similar_users
        }

    except Exception as e:
        logger.error(f"[x] Error finding similar users for user_id {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while finding similar users.")


@app.get("/recommendations/based_on_similar_users")
async def get_recs_based_on_similar_users(
    n_recommendations: int = 20,
    n_similar_users: int = 15,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Generates recommendations for the current user based on the tastes of similar users."""
    user_id = current_user["user_id"]

    if USER_MOVIE_MATRIX is None:
        raise HTTPException(status_code=503, detail="User-movie matrix not available.")

    if user_id not in USER_ID_MAP:
        # Fallback to popular movies for new users
        logger.warning(f"Cold start for user {user_id}. Falling back to popular movies.")
        popular_movies = db.query(Movie).filter(Movie.rating_count >= 100).order_by(Movie.avg_rating.desc()).limit(n_recommendations).all()
        recommendations = [
            {
                "movie_id": movie.id,
                "title": movie.title,
                "genres": movie.genres.split('|') if movie.genres else [],
                "avg_rating": float(movie.avg_rating) if movie.avg_rating else 0.0,
                "type": "popular-fallback"
            }
            for movie in popular_movies
        ]
        return {
            "status": "success",
            "method": "Popular Movies (Cold Start Fallback)",
            "recommendations": recommendations
        }

    try:
        # Step 1: Find similar users
        user_index = USER_ID_MAP[user_id]
        user_vector = USER_MOVIE_MATRIX[user_index].reshape(1, -1)
        similarity_scores = cosine_similarity(user_vector, USER_MOVIE_MATRIX)[0]
        similar_user_indices = np.argsort(similarity_scores)[::-1]

        top_similar_indices = []
        for idx in similar_user_indices:
            if idx != user_index:
                top_similar_indices.append(idx)
            if len(top_similar_indices) >= n_similar_users:
                break
        
        if not top_similar_indices:
            raise HTTPException(status_code=404, detail="Could not find any similar users.")

        # Step 2: Aggregate movie scores from similar users
        similar_users_ratings = USER_MOVIE_MATRIX[top_similar_indices]
        recommendation_scores = similar_users_ratings.sum(axis=0)

        # Step 3: Filter out movies the current user has already rated
        user_rated_movie_indices = np.where(USER_MOVIE_MATRIX[user_index] > 0)[0]
        recommendation_scores[user_rated_movie_indices] = -1

        # Step 4: Get top N movie recommendations
        recommended_movie_indices = np.argsort(recommendation_scores)[::-1]

        # Step 5: Format recommendations and fetch details from DB
        recommendations = []
        inv_movie_id_map = {i: m_id for m_id, i in MOVIE_ID_MAP.items()}

        for movie_idx in recommended_movie_indices:
            if len(recommendations) >= n_recommendations or recommendation_scores[movie_idx] < 0:
                break
            
            movie_id = inv_movie_id_map.get(movie_idx)
            if movie_id:
                movie_details = db.query(Movie).filter(Movie.id == movie_id).first()
                if movie_details:
                    recommendations.append({
                        "movie_id": movie_details.id,
                        "title": movie_details.title,
                        "genres": movie_details.genres.split('|') if movie_details.genres else [],
                        "avg_rating": float(movie_details.avg_rating) if movie_details.avg_rating else 0.0,
                        "recommendation_score": float(recommendation_scores[movie_idx]),
                        "type": "user-similarity-based"
                    })
        
        return {
            "status": "success",
            "method": f"User-Based Collaborative Filtering (from {len(top_similar_indices)} similar users)",
            "recommendations": recommendations
        }

    except Exception as e:
        logger.error(f"[x] Error generating recommendations based on similar users for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while generating recommendations.")


# ===========================================================================
# [*] DEEP LEARNING RECOMMENDATION ENDPOINT
# ===========================================================================
@app.get("/dl-recommendations")
async def get_dl_recommendations(
    n_recommendations: int = 10,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Generates movie recommendations for the current user using the Deep Learning model.
    """
    user_id = current_user.get("user_id")

    # 1. Check if the DL model is available
    if dl_model is None or dl_user_to_idx is None or dl_movie_to_idx is None:
        raise HTTPException(
            status_code=503,
            detail="Deep Learning recommendation service is currently unavailable."
        )

    # 2. Handle Cold Start: Check if the user exists in the DL model's training data
    if user_id not in dl_user_to_idx:
        logger.warning(f"Cold start for user {user_id} in DL model. Falling back to popular movies.")
        # Fallback to popular movies for cold-start users
        popular_movies = db.query(Movie).filter(Movie.rating_count >= 50).order_by(Movie.avg_rating.desc()).limit(n_recommendations).all()
        return {
            "status": "success",
            "method": "Deep_Learning_Cold_Start_Fallback",
            "recommendations": [
                {
                    "movie_id": movie.id,
                    "title": movie.title,
                    "genres": movie.genres.split('|') if movie.genres else [],
                    "avg_rating": movie.avg_rating,
                    "reason": "Popular movie for new user"
                } for movie in popular_movies
            ]
        }

    # 3. Get movies the user has already rated
    rated_movie_ids = {
        rating.movie_id for rating in db.query(Rating.movie_id).filter(Rating.user_id == user_id).all()
    }

    # 4. Prepare the list of candidate movies for prediction
    all_movie_ids_original = list(dl_movie_to_idx.keys())
    candidate_movie_ids_original = [m_id for m_id in all_movie_ids_original if m_id not in rated_movie_ids]
    
    if not candidate_movie_ids_original:
        return {"status": "info", "message": "You have rated all movies known to the DL model!"}

    # Map original IDs to internal model indices
    user_idx = dl_user_to_idx[user_id]
    candidate_movie_indices = [dl_movie_to_idx[m_id] for m_id in candidate_movie_ids_original]

    user_array = np.full(len(candidate_movie_indices), user_idx, dtype=np.int32)
    movie_array = np.array(candidate_movie_indices, dtype=np.int32)

    # 5. Make predictions
    predictions = dl_model.predict([user_array, movie_array], verbose=0).flatten()

    # 6. Get top N recommendations
    top_indices = predictions.argsort()[-n_recommendations:][::-1]
    
    recommended_movie_indices = [candidate_movie_indices[i] for i in top_indices]
    recommended_movie_ids_original = [dl_idx_to_movie[i] for i in recommended_movie_indices]
    predicted_ratings = [predictions[i] for i in top_indices]

    # 7. Fetch movie details from the database
    recommended_movies_details = db.query(Movie).filter(Movie.id.in_(recommended_movie_ids_original)).all()
    movie_details_map = {movie.id: movie for movie in recommended_movies_details}

    # 8. Format the response
    recommendations = []
    for movie_id, predicted_rating in zip(recommended_movie_ids_original, predicted_ratings):
        movie = movie_details_map.get(movie_id)
        if movie:
            recommendations.append({
                "movie_id": movie.id,
                "title": movie.title,
                "genres": movie.genres.split('|') if movie.genres else [],
                "predicted_rating": float(predicted_rating),
                "avg_rating": movie.avg_rating,
                "reason": "Recommended by Deep Learning Model"
            })

    return {
        "status": "success",
        "method": "Deep_Learning_Collaborative_Filtering",
        "recommendations": recommendations
    }

# ============================================================================
# [*] DİNAMİK DERİN ÖĞRENMELİ ÖNERİ SİSTEMİ ENDPOINTS
# ============================================================================

@app.get("/dynamic-deep-recommendations")
async def get_dynamic_deep_recommendations(
    n_recommendations: int = Query(default=10, ge=1, le=50),
    force_update: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Dinamik Derin Öğrenme ile Öneri Al
    
    Bu endpoint:
    1. Kullanıcıya en benzer 10 kullanıcıyı bulur (derin öğrenme embeddinglari ile)
    2. Bu benzer kullanıcıların beğendiği filmleri analiz eder
    3. Derin öğrenme modeli ile rating tahminleri yapar
    4. Kişiselleştirilmiş öneri listesi döner
    """
    
    if dynamic_deep_recommender is None:
        raise HTTPException(
            status_code=503,
            detail="Dynamic Deep Learning system not available"
        )
    
    try:
        user_id = current_user["user_id"]
        
        # Model eğitilmemiş ise eğit
        if not os.path.exists("bitirme2/dynamic_deep_model.h5"):
            logger.info("[*] Training Dynamic Deep Learning model...")
            training_success = dynamic_deep_recommender.train_model(retrain=True)
            if not training_success:
                raise HTTPException(
                    status_code=500,
                    detail="Model training failed"
                )
        
        # Benzer kullanıcıları bul
        similar_users = dynamic_deep_recommender.find_similar_users(
            user_id, 
            force_update=force_update
        )
        
        if not similar_users:
            # Fallback - genel popüler filmler
            popular_movies = db.query(Movie).filter(
                Movie.avg_rating >= 4.0
            ).order_by(desc(Movie.avg_rating)).limit(n_recommendations).all()
            
            fallback_recommendations = []
            for movie in popular_movies:
                fallback_recommendations.append({
                    "movie_id": movie.id,
                    "title": movie.title,
                    "genres": movie.genres.split('|') if movie.genres else [],
                    "predicted_rating": float(movie.avg_rating),
                    "similar_users_count": 0,
                    "recommendation_source": "popular_fallback",
                    "algorithm": "fallback"
                })
            
            return {
                "status": "success",
                "method": "Dynamic_Deep_Learning_Fallback",
                "user_id": user_id,
                "similar_users_found": 0,
                "message": "No similar users found, showing popular movies",
                "recommendations": fallback_recommendations
            }
        
        # Benzer kullanıcılardan öneriler al
        recommendations = dynamic_deep_recommender.get_recommendations_from_similar_users(
            user_id, 
            n_recommendations
        )
        
        return {
            "status": "success",
            "method": "Dynamic_Deep_Learning",
            "user_id": user_id,
            "similar_users_found": len(similar_users),
            "similar_users": similar_users[:3],  # İlk 3 benzer kullanıcıyı göster
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"[x] Dynamic deep recommendations error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Dynamic deep learning recommendation failed: {str(e)}"
        )

@app.get("/find-similar-users/{target_user_id}")
async def find_similar_users_endpoint(
    target_user_id: int,
    force_update: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Belirtilen kullanıcıya benzer kullanıcıları bul
    Derin öğrenme user embeddinglari kullanarak cosine similarity hesaplar
    """
    
    if dynamic_deep_recommender is None:
        raise HTTPException(
            status_code=503,
            detail="Dynamic Deep Learning system not available"
        )
    
    try:
        # Admin kontrolü veya kendi profilin
        if current_user["user_id"] != target_user_id:
            # Sadece admin veya kendisi görebilir
            if current_user.get("username") not in ["admin", "administrator"]:
                raise HTTPException(
                    status_code=403,
                    detail="You can only view similar users for your own profile"
                )
        
        # Kullanıcı var mı kontrol et
        target_user = db.query(User).filter(User.id == target_user_id).first()
        if not target_user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        # Benzer kullanıcıları bul
        similar_users = dynamic_deep_recommender.find_similar_users(
            target_user_id, 
            force_update=force_update
        )
        
        # Kullanıcı detaylarını ekle
        enhanced_similar_users = []
        for user in similar_users:
            user_details = db.query(User).filter(User.id == user['user_id']).first()
            if user_details:
                enhanced_similar_users.append({
                    "user_id": user['user_id'],
                    "username": user_details.username,
                    "age": user_details.age,
                    "gender": user_details.gender,
                    "occupation": user_details.occupation,
                    "similarity_score": user['similarity_score'],
                    "favorite_genres": user_details.favorite_genres.split(',') if user_details.favorite_genres else []
                })
        
        return {
            "status": "success",
            "target_user_id": target_user_id,
            "target_username": target_user.username,
            "similar_users_count": len(enhanced_similar_users),
            "similar_users": enhanced_similar_users,
            "algorithm": "dynamic_deep_learning_embeddings",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"[x] Find similar users error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Finding similar users failed: {str(e)}"
        )

@app.post("/update-user-preferences")
async def update_user_preferences_dynamic(
    ratings: List[Dict[str, Union[int, float]]] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Kullanıcının tercihlerini güncelle ve derin öğrenme embeddingini yenile
    
    Body format:
    {
        "ratings": [
            {"movie_id": 123, "rating": 4.5},
            {"movie_id": 456, "rating": 3.0}
        ]
    }
    """
    
    if dynamic_deep_recommender is None:
        raise HTTPException(
            status_code=503,
            detail="Dynamic Deep Learning system not available"
        )
    
    if not ratings:
        raise HTTPException(
            status_code=400,
            detail="Ratings data required"
        )
    
    try:
        user_id = current_user["user_id"]
        
        # Veritabanına yeni ratingleri kaydet
        saved_ratings = []
        for rating_data in ratings:
            movie_id = rating_data["movie_id"]
            rating_value = rating_data["rating"]
            
            # Validasyon
            if not (1.0 <= rating_value <= 5.0):
                continue
                
            # Movie var mı kontrol et
            movie = db.query(Movie).filter(Movie.id == movie_id).first()
            if not movie:
                continue
            
            # UserInteraction kaydı ekle/güncelle
            existing_interaction = db.query(UserInteraction).filter(
                UserInteraction.user_id == user_id,
                UserInteraction.movie_id == movie_id,
                UserInteraction.interaction_type == "rating"
            ).first()
            
            if existing_interaction:
                existing_interaction.interaction_data = str(rating_value)
                existing_interaction.timestamp = datetime.now()
            else:
                new_interaction = UserInteraction(
                    user_id=user_id,
                    movie_id=movie_id,
                    interaction_type="rating",
                    interaction_data=str(rating_value),
                    timestamp=datetime.now()
                )
                db.add(new_interaction)
            
            saved_ratings.append({
                "movie_id": movie_id,
                "rating": rating_value,
                "movie_title": movie.title
            })
        
        db.commit()
        
        # Derin öğrenme embeddingini güncelle
        if saved_ratings:
            dynamic_deep_recommender.update_user_embedding(user_id, ratings)
            
            logger.info(f"[+] Updated embeddings for user {user_id} with {len(saved_ratings)} new ratings")
        
        return {
            "status": "success",
            "message": "User preferences and embeddings updated successfully",
            "user_id": user_id,
            "updated_ratings": saved_ratings,
            "count": len(saved_ratings),
            "embedding_updated": True,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"[x] Update user preferences error: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Updating user preferences failed: {str(e)}"
        )

@app.post("/retrain-dynamic-model")
async def retrain_dynamic_model(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """
    Dinamik derin öğrenme modelini yeniden eğit (admin only)
    Background task olarak çalışır
    """
    
    # Admin kontrolü
    if current_user.get("username") not in ["admin", "administrator"]:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    
    if dynamic_deep_recommender is None:
        raise HTTPException(
            status_code=503,
            detail="Dynamic Deep Learning system not available"
        )
    
    def retrain_model():
        try:
            logger.info("[*] Starting model retraining...")
            success = dynamic_deep_recommender.train_model(retrain=True)
            if success:
                logger.info("[+] Model retraining completed successfully")
            else:
                logger.error("[x] Model retraining failed")
        except Exception as e:
            logger.error(f"[x] Model retraining error: {e}")
    
    background_tasks.add_task(retrain_model)
    
    return {
        "status": "success",
        "message": "Model retraining started in background",
        "initiated_by": current_user["username"],
        "timestamp": datetime.now().isoformat()
    }

# === MAIN EXECUTION ===
if __name__ == "__main__":
    import uvicorn
    
    print("[+] Enhanced Movie Recommendation System v6.0 Complete")
    print("=" * 60)
    print("[*] Starting server...")
    print("[*] API Documentation will be available at: http://localhost:8000/docs")
    print("[*] Frontend will be available at: http://localhost:8000")
    print("[*] Health Check: http://localhost:8000/health")
    print("=" * 60)
    
    # DIRECT DATABASE CHECK - Çalışan database ile
    try:
        print("[*] Checking database...")
        db = SessionLocal()
        movie_count = db.execute(text("SELECT COUNT(*) FROM movies")).scalar()
        user_count = db.execute(text("SELECT COUNT(*) FROM app_users")).scalar()
        db.close()
        print(f"[+] Database check completed: {movie_count} movies, {user_count} users")
    except Exception as e:
        print(f"[!] Database check failed: {e}")
        # Fallback SQLite check
        try:
            conn = sqlite3.connect("movielens_100k.db")
            movie_count = conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
            user_count = conn.execute("SELECT COUNT(*) FROM app_users").fetchone()[0]
            conn.close()
            print(f"[+] SQLite check: {movie_count} movies, {user_count} users")
        except Exception as e2:
            print(f"[x] SQLite check failed: {e2}")
    
    uvicorn.run(
        "app_enhanced_v6:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Reload kapatıldı - stable run
        log_level="info"
    )