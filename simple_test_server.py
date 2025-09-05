"""
Basit Test Sunucusu - Dynamic Deep Learning Sistemi için
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import jwt
from typing import List, Dict, Union
import json

# Initialize FastAPI
app = FastAPI(title="Dynamic Deep Learning Test Server", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# JWT Settings
SECRET_KEY = "Aa1234567."
ALGORITHM = "HS256"

# Models
class UserLogin(BaseModel):
    username: str
    password: str

class UserRegistration(BaseModel):
    username: str
    email: str
    password: str
    age: int = 25
    gender: str = "M"

# Auth function
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        if not credentials:
            raise HTTPException(status_code=401, detail="Token required")
        
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_data = {
            "user_id": payload.get("user_id"),
            "username": payload.get("username")
        }
        
        if not user_data["user_id"]:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return user_data
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

# Database helper
def get_db_connection():
    return sqlite3.connect("bitirme2/movielens_100k.db")

# Dynamic Deep Recommender
try:
    import sys
    sys.path.append("bitirme2")
    from bitirme2.dynamic_deep_recommender import DynamicDeepRecommender
    
    dynamic_deep_recommender = DynamicDeepRecommender(
        embedding_dim=128,
        n_similar_users=10,
        model_path="bitirme2/dynamic_deep_model.h5",
        embeddings_path="bitirme2/user_embeddings.pkl"
    )
    print("[+] Dynamic Deep Recommender loaded successfully!")
    
except Exception as e:
    print(f"[x] Dynamic Deep Recommender failed: {e}")
    dynamic_deep_recommender = None

# Endpoints
@app.get("/")
async def root():
    return {"message": "Dynamic Deep Learning Test Server Running!", "status": "ok"}

@app.post("/register")
async def register(user: UserRegistration):
    try:
        conn = get_db_connection()
        cursor = conn.execute("""
            INSERT INTO app_users (username, email, hashed_password, age, gender)
            VALUES (?, ?, ?, ?, ?)
        """, (user.username, user.email, user.password, user.age, user.gender))
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {"status": "success", "message": "User registered", "user_id": user_id}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/login")
async def login(user: UserLogin):
    try:
        conn = get_db_connection()
        result = conn.execute(
            "SELECT id, username, email FROM app_users WHERE username = ? AND hashed_password = ?",
            (user.username, user.password)
        ).fetchone()
        conn.close()
        
        if result:
            user_id, username, email = result
            
            # Create JWT token
            token_data = {"user_id": user_id, "username": username}
            access_token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
            
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
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dynamic-deep-recommendations")
async def get_dynamic_deep_recommendations(
    n_recommendations: int = Query(default=10, ge=1, le=20),
    force_update: bool = Query(default=False),
    current_user: dict = Depends(get_current_user)
):
    """Dynamic Deep Learning Recommendations"""
    
    if dynamic_deep_recommender is None:
        raise HTTPException(status_code=503, detail="Dynamic Deep Learning system not available")
    
    try:
        user_id = current_user["user_id"]
        
        # Find similar users
        similar_users = dynamic_deep_recommender.find_similar_users(user_id, force_update=force_update)
        
        if not similar_users:
            # Fallback to popular movies
            conn = get_db_connection()
            popular_movies = conn.execute("""
                SELECT id, title, genres, avg_rating 
                FROM movies 
                WHERE avg_rating >= 4.0 
                ORDER BY avg_rating DESC 
                LIMIT ?
            """, (n_recommendations,)).fetchall()
            conn.close()
            
            fallback_recommendations = []
            for movie in popular_movies:
                fallback_recommendations.append({
                    "movie_id": movie[0],
                    "title": movie[1],
                    "genres": movie[2].split('|') if movie[2] else [],
                    "predicted_rating": float(movie[3]) if movie[3] else 4.0,
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
        
        # Get recommendations from similar users
        recommendations = dynamic_deep_recommender.get_recommendations_from_similar_users(
            user_id, n_recommendations
        )
        
        return {
            "status": "success",
            "method": "Dynamic_Deep_Learning",
            "user_id": user_id,
            "similar_users_found": len(similar_users),
            "similar_users": similar_users[:3],
            "recommendations": recommendations
        }
        
    except Exception as e:
        print(f"[x] Dynamic deep recommendations error: {e}")
        raise HTTPException(status_code=500, detail=f"Recommendation failed: {str(e)}")

@app.get("/find-similar-users/{target_user_id}")
async def find_similar_users_endpoint(
    target_user_id: int,
    force_update: bool = Query(default=False),
    current_user: dict = Depends(get_current_user)
):
    """Find similar users"""
    
    if dynamic_deep_recommender is None:
        raise HTTPException(status_code=503, detail="Dynamic Deep Learning system not available")
    
    try:
        # Find similar users
        similar_users = dynamic_deep_recommender.find_similar_users(target_user_id, force_update=force_update)
        
        return {
            "status": "success",
            "target_user_id": target_user_id,
            "similar_users_count": len(similar_users),
            "similar_users": similar_users,
            "algorithm": "dynamic_deep_learning_embeddings"
        }
        
    except Exception as e:
        print(f"[x] Find similar users error: {e}")
        raise HTTPException(status_code=500, detail=f"Finding similar users failed: {str(e)}")

@app.post("/update-user-preferences")
async def update_user_preferences_dynamic(
    request: Dict[str, List[Dict[str, Union[int, float]]]],
    current_user: dict = Depends(get_current_user)
):
    """Update user preferences and retrain embeddings"""
    
    if dynamic_deep_recommender is None:
        raise HTTPException(status_code=503, detail="Dynamic Deep Learning system not available")
    
    ratings = request.get("ratings", [])
    if not ratings:
        raise HTTPException(status_code=400, detail="Ratings data required")
    
    try:
        user_id = current_user["user_id"]
        
        # Save ratings to database
        conn = get_db_connection()
        saved_ratings = []
        
        for rating_data in ratings:
            movie_id = rating_data["movie_id"]
            rating_value = rating_data["rating"]
            
            if not (1.0 <= rating_value <= 5.0):
                continue
            
            # Save interaction
            conn.execute("""
                INSERT INTO user_interactions (user_id, movie_id, interaction_type, extra_data)
                VALUES (?, ?, ?, ?)
            """, (user_id, movie_id, 'rating', json.dumps({"rating": rating_value})))
            
            saved_ratings.append({
                "movie_id": movie_id,
                "rating": rating_value
            })
        
        conn.commit()
        conn.close()
        
        # Update embeddings
        if saved_ratings:
            dynamic_deep_recommender.update_user_embedding(user_id, ratings)
        
        return {
            "status": "success",
            "message": "User preferences and embeddings updated successfully",
            "user_id": user_id,
            "updated_ratings": saved_ratings,
            "count": len(saved_ratings),
            "embedding_updated": True
        }
        
    except Exception as e:
        print(f"[x] Update user preferences error: {e}")
        raise HTTPException(status_code=500, detail=f"Updating preferences failed: {str(e)}")

@app.get("/status")
async def get_status():
    """System status"""
    return {
        "server": "running",
        "dynamic_deep_learning": dynamic_deep_recommender is not None,
        "model_files": {
            "model": os.path.exists("bitirme2/dynamic_deep_model.h5"),
            "embeddings": os.path.exists("bitirme2/user_embeddings.pkl")
        }
    }

if __name__ == "__main__":
    import uvicorn
    print("Starting Dynamic Deep Learning Test Server...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
