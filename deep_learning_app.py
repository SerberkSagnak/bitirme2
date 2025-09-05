"""
PURE DEEP LEARNING MOVIE RECOMMENDATION SYSTEM
Academic Project - Neural Collaborative Filtering Focus

Features:
- TensorFlow Neural Networks  
- 128-dimensional User Embeddings
- 10 Similar Users Detection
- Dynamic Learning System
- Clean Architecture
"""

import sys
import os
import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# FastAPI imports
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# Auth imports
import jwt
from passlib.context import CryptContext

# Core libraries
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === AUTHENTICATION SETUP ===
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()
SECRET_KEY = "Aa1234567."
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_data = {
            "user_id": payload.get("user_id"),
            "username": payload.get("username")
        }
        
        if not user_data["user_id"]:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return user_data
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# === DATABASE CONNECTION ===
DATABASE_PATH = "../movielens_100k.db"

def get_db_connection():
    return sqlite3.connect(DATABASE_PATH)

def execute_query(query: str, params: tuple = None):
    """Safe database query execution"""
    try:
        conn = get_db_connection()
        if params:
            result = conn.execute(query, params).fetchall()
        else:
            result = conn.execute(query).fetchall()
        conn.close()
        return result
    except Exception as e:
        logger.error(f"[x] Database query error: {e}")
        return []

# === DEEP LEARNING SYSTEM ===
try:
    from clean_dynamic_deep_recommender import CleanDynamicDeepRecommender
    
    # Initialize Deep Learning System
    deep_learning_system = CleanDynamicDeepRecommender(
        embedding_dim=128,
        n_similar_users=10,
        similarity_threshold=0.1
    )
    
    logger.info("[+] Deep Learning System initialized")
    
except Exception as e:
    logger.error(f"[x] Deep Learning System initialization failed: {e}")
    deep_learning_system = None

# === FASTAPI APP ===
app = FastAPI(
    title="🧠 Pure Deep Learning Movie Recommendation System",
    description="Academic Project - Neural Collaborative Filtering",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === MODELS ===
class UserLogin(BaseModel):
    username: str
    password: str

class UserRegistration(BaseModel):
    username: str
    email: str
    password: str
    age: Optional[int] = None
    gender: Optional[str] = None

# === ROUTES ===

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve frontend"""
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except:
        return HTMLResponse(content="""
            <h1>🧠 Pure Deep Learning System</h1>
            <p>Frontend file not found</p>
            <a href="/docs">API Documentation</a>
        """)

@app.get("/health")
async def health_check():
    """System health check"""
    try:
        # Check database
        users = execute_query("SELECT COUNT(*) FROM app_users")
        movies = execute_query("SELECT COUNT(*) FROM movies")
        
        user_count = users[0][0] if users else 0
        movie_count = movies[0][0] if movies else 0
        
        # Check deep learning system
        dl_status = deep_learning_system is not None
        
        return {
            "status": "healthy",
            "database": {
                "users": user_count,
                "movies": movie_count
            },
            "deep_learning": {
                "available": dl_status,
                "embedding_dim": 128 if dl_status else 0,
                "similar_users": 10 if dl_status else 0
            },
            "project_type": "pure_deep_learning"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.post("/login")
async def login(user: UserLogin):
    """User login"""
    try:
        # Database query
        result = execute_query(
            "SELECT id, username, email, hashed_password FROM app_users WHERE username = ?",
            (user.username,)
        )
        
        if not result:
            raise HTTPException(status_code=401, detail="User not found")
        
        user_data = result[0]
        user_id, username, email, hashed_password = user_data
        
        # Password verification  
        if not verify_password(user.password, hashed_password):
            raise HTTPException(status_code=401, detail="Invalid password")
        
        # Create token
        access_token = create_access_token({"user_id": user_id, "username": username})
        
        return {
            "status": "success",
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user_id,
                "username": username,
                "email": email
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

@app.get("/recommendations/new/{user_id}")
async def get_deep_learning_recommendations(
    user_id: int,
    n_recommendations: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """
    🧠 PURE DEEP LEARNING RECOMMENDATIONS
    
    Algorithm:
    1. Neural Collaborative Filtering ile user embeddings (128-dim)
    2. Cosine similarity ile 10 benzer kullanıcı bulma
    3. Bu kullanıcıların film tercihlerini analiz etme
    4. TensorFlow model ile rating prediction
    5. Personalized recommendation list
    """
    
    if not deep_learning_system:
        raise HTTPException(status_code=503, detail="Deep Learning System not available")
    
    try:
        logger.info(f"[🧠] Deep Learning recommendation request for user {user_id}")
        
        # Check user has enough data
        user_rating_count = len(execute_query(
            "SELECT id FROM user_interactions WHERE user_id = ? AND interaction_type = 'rating'",
            (user_id,)
        ))
        
        logger.info(f"[📊] User {user_id} has {user_rating_count} ratings")
        
        # Minimum rating requirement for deep learning
        MIN_RATINGS = 3
        
        if user_rating_count < MIN_RATINGS:
            # Cold start - popular movies with explanation
            popular_movies = execute_query("""
                SELECT id, title, genres, avg_rating
                FROM movies 
                WHERE avg_rating >= 4.0
                ORDER BY avg_rating DESC 
                LIMIT ?
            """, (n_recommendations,))
            
            recommendations = []
            for movie in popular_movies:
                recommendations.append({
                    "movie_id": movie[0],
                    "title": movie[1],
                    "genres": movie[2].split('|') if movie[2] else [],
                    "predicted_rating": float(movie[3]) if movie[3] else 4.0,
                    "reason": f"Popüler film - {MIN_RATINGS} film puanlayın!",
                    "algorithm": "cold_start_popular"
                })
            
            return {
                "status": "success",
                "message": f"🔥 COLD START - Derin öğrenme için {MIN_RATINGS} film puanlayın! ({user_rating_count}/{MIN_RATINGS})",
                "method": "Cold Start - Popular Movies",
                "user_rating_count": user_rating_count,
                "minimum_required": MIN_RATINGS,
                "algorithm": "cold_start",
                "recommendations": recommendations
            }
        
        # PURE DEEP LEARNING PROCESS
        logger.info("[🧠] Starting Neural Collaborative Filtering...")
        
        # Train model if needed
        if not os.path.exists("dynamic_deep_model.h5"):
            logger.info("[🧠] Training Deep Learning model...")
            training_success = deep_learning_system.train_model()
            if not training_success:
                raise HTTPException(status_code=500, detail="Deep Learning model training failed")
        
        # Find 10 similar users using neural embeddings
        similar_users = deep_learning_system.find_similar_users(user_id)
        logger.info(f"[👥] Found {len(similar_users)} similar users")
        
        if not similar_users:
            raise HTTPException(status_code=404, detail="No similar users found")
        
        # Get recommendations from similar users
        recommendations = deep_learning_system.get_recommendations(user_id, n_recommendations)
        logger.info(f"[🎬] Generated {len(recommendations)} recommendations")
        
        return {
            "status": "success",
            "message": f"🧠 NEURAL COLLABORATIVE FILTERING - {len(similar_users)} benzer kullanıcıdan {len(recommendations)} film",
            "method": "Pure Deep Learning - Neural Embeddings",
            "algorithm": "neural_collaborative_filtering",
            "user_rating_count": user_rating_count,
            "similar_users_found": len(similar_users),
            "similar_users": [
                {
                    "user_id": user["user_id"],
                    "similarity_score": user["similarity_score"]
                } for user in similar_users[:3]
            ],
            "embedding_dimension": 128,
            "model_type": "tensorflow_neural_network",
            "recommendations": recommendations,
            "quality": "personalized_deep_learning"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[🚨] Deep Learning error: {e}")
        raise HTTPException(status_code=500, detail=f"Deep Learning recommendation failed: {str(e)}")

@app.get("/user-stats")
async def get_user_stats(current_user: dict = Depends(get_current_user)):
    """User statistics for frontend"""
    try:
        user_id = current_user["user_id"]
        
        # Count ratings
        ratings = execute_query(
            "SELECT COUNT(*) FROM user_interactions WHERE user_id = ? AND interaction_type = 'rating'",
            (user_id,)
        )
        
        # Count favorites
        favorites = execute_query(
            "SELECT COUNT(*) FROM user_interactions WHERE user_id = ? AND interaction_type = 'favorite'",
            (user_id,)
        )
        
        ratings_count = ratings[0][0] if ratings else 0
        favorites_count = favorites[0][0] if favorites else 0
        
        return {
            "status": "success",
            "user_id": user_id,
            "ratings_count": ratings_count,
            "favorites_count": favorites_count,
            "total_activity": ratings_count + favorites_count,
            "deep_learning_eligible": ratings_count >= 3
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail="Stats failed")

@app.get("/genres")
async def get_genres():
    """Get all movie genres"""
    try:
        genres_raw = execute_query("SELECT DISTINCT genres FROM movies WHERE genres IS NOT NULL")
        
        all_genres = set()
        for genre_row in genres_raw:
            if genre_row[0]:
                genres = genre_row[0].split('|')
                all_genres.update(genres)
        
        return {
            "status": "success",
            "genres": sorted(list(all_genres)),
            "count": len(all_genres)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Could not fetch genres")

@app.post("/register")
async def register(user: UserRegistration):
    """User registration"""
    try:
        # Check if user exists
        existing = execute_query("SELECT id FROM app_users WHERE username = ?", (user.username,))
        if existing:
            raise HTTPException(status_code=400, detail="Username already exists")
        
        # Create user
        conn = get_db_connection()
        cursor = conn.execute("""
            INSERT INTO app_users (username, email, hashed_password, age, gender)
            VALUES (?, ?, ?, ?, ?)
        """, (
            user.username, 
            user.email, 
            pwd_context.hash(user.password),
            user.age,
            user.gender
        ))
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {
            "status": "success",
            "message": "User registered successfully",
            "user_id": user_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Registration failed")

@app.post("/rate-movie")
async def rate_movie(
    rating_data: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """Rate a movie - triggers dynamic deep learning update"""
    try:
        user_id = current_user["user_id"]
        movie_id = int(rating_data["movie_id"])
        rating = float(rating_data["rating"])
        
        if not (1.0 <= rating <= 5.0):
            raise HTTPException(status_code=400, detail="Rating must be between 1.0 and 5.0")
        
        # Save rating
        conn = get_db_connection()
        
        # Check if movie exists
        movie = conn.execute("SELECT title FROM movies WHERE id = ?", (movie_id,)).fetchone()
        if not movie:
            raise HTTPException(status_code=404, detail="Movie not found")
        
        # Insert rating
        conn.execute("""
            INSERT INTO user_interactions (user_id, movie_id, interaction_type, extra_data, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (
            user_id, 
            movie_id, 
            'rating', 
            json.dumps({"rating": rating}),
            datetime.now()
        ))
        
        conn.commit()
        conn.close()
        
        # DYNAMIC DEEP LEARNING UPDATE
        if deep_learning_system:
            try:
                deep_learning_system.update_user_embedding(user_id, [{"movie_id": movie_id, "rating": rating}])
                logger.info(f"[🧠] Dynamic embedding updated for user {user_id}")
            except Exception as e:
                logger.warning(f"[!] Dynamic update failed: {e}")
        
        return {
            "status": "success",
            "message": f"Rating saved: {movie[0]}",
            "user_id": user_id,
            "movie_id": movie_id,
            "movie_title": movie[0],
            "rating": rating,
            "dynamic_update": deep_learning_system is not None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Rating failed")

@app.get("/deep-learning-status")
async def get_deep_learning_status():
    """Deep Learning system status"""
    try:
        if not deep_learning_system:
            return {"status": "not_available"}
        
        # Check if model is trained
        model_trained = os.path.exists("dynamic_deep_model.h5")
        embeddings_available = os.path.exists("user_embeddings.pkl")
        
        # Get training data stats
        training_interactions = len(execute_query("""
            SELECT ui.user_id FROM user_interactions ui
            WHERE ui.interaction_type = 'rating'
            AND ui.extra_data IS NOT NULL
            AND JSON_EXTRACT(ui.extra_data, '$.rating') IS NOT NULL
        """))
        
        training_users = len(execute_query("""
            SELECT DISTINCT ui.user_id FROM user_interactions ui
            WHERE ui.interaction_type = 'rating'
            AND ui.extra_data IS NOT NULL
            AND JSON_EXTRACT(ui.extra_data, '$.rating') IS NOT NULL
        """))
        
        return {
            "status": "available",
            "model_trained": model_trained,
            "embeddings_available": embeddings_available,
            "training_data": {
                "interactions": training_interactions,
                "users": training_users
            },
            "architecture": {
                "embedding_dimension": 128,
                "similar_users_count": 10,
                "model_type": "neural_collaborative_filtering"
            },
            "ready": model_trained and embeddings_available
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

# === MAIN EXECUTION ===
if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("PURE DEEP LEARNING MOVIE RECOMMENDATION SYSTEM")
    print("=" * 60)
    print("Academic Project - Neural Collaborative Filtering Focus")
    print("")
    print("Features:")
    print("- TensorFlow Neural Networks")
    print("- 128-dimensional User Embeddings") 
    print("- 10 Similar Users Detection")
    print("- Dynamic Learning System")
    print("=" * 60)
    
    # Check deep learning system
    if deep_learning_system:
        print("[+] Deep Learning System: READY")
    else:
        print("[!] Deep Learning System: NOT AVAILABLE")
    
    print("")
    print("Starting server...")
    print("Frontend: http://localhost:8000")
    print("API Docs: http://localhost:8000/docs")
    print("Health: http://localhost:8000/health")
    print("=" * 60)
    
    uvicorn.run(
        "deep_learning_app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
