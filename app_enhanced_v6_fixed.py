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

# REST OF THE ENDPOINTS AND CODE CONTINUES HERE...
