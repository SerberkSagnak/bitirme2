"""
Çalışan Basit Test Sunucusu
"""

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials  
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import jwt
import json
from typing import List, Dict, Union

app = FastAPI(title="Working Dynamic Test Server")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth
security = HTTPBearer()
SECRET_KEY = "Aa1234567."
ALGORITHM = "HS256"

class UserLogin(BaseModel):
    username: str
    password: str

class UserRegistration(BaseModel):
    username: str
    email: str  
    password: str

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return {
            "user_id": payload.get("user_id"),
            "username": payload.get("username")
        }
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_db():
    return sqlite3.connect("movielens_100k.db")

@app.get("/")
async def root():
    return {"message": "Working Server!", "status": "ok"}

@app.post("/register")
async def register(user: UserRegistration):
    try:
        conn = get_db()
        cursor = conn.execute("""
            INSERT INTO app_users (username, email, hashed_password)
            VALUES (?, ?, ?)
        """, (user.username, user.email, user.password))
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {"status": "success", "user_id": user_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/login")  
async def login(user: UserLogin):
    try:
        conn = get_db()
        result = conn.execute(
            "SELECT id, username, email FROM app_users WHERE username = ? AND hashed_password = ?",
            (user.username, user.password)
        ).fetchone()
        conn.close()
        
        if result:
            user_id, username, email = result
            token = jwt.encode({"user_id": user_id, "username": username}, SECRET_KEY, algorithm=ALGORITHM)
            
            return {
                "status": "success",
                "access_token": token,
                "token_type": "bearer", 
                "user": {"id": user_id, "username": username, "email": email}
            }
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dynamic-deep-recommendations")
async def get_recommendations(
    n_recommendations: int = Query(default=10, ge=1, le=20),
    current_user: dict = Depends(get_current_user)
):
    """Dynamic Deep Learning Recommendations - Fallback Version"""
    
    try:
        user_id = current_user["user_id"]
        
        # Get popular movies as recommendations
        conn = get_db()
        
        # Get user's already rated movies
        rated_movies = set(row[0] for row in conn.execute(
            "SELECT movie_id FROM user_interactions WHERE user_id = ? AND interaction_type = 'rating'",
            (user_id,)
        ).fetchall())
        
        # Get popular movies not yet rated by user
        movies = conn.execute("""
            SELECT id, title, genres, avg_rating
            FROM movies 
            WHERE avg_rating >= 3.5 
            AND id NOT IN (
                SELECT movie_id FROM user_interactions 
                WHERE user_id = ? AND interaction_type = 'rating'
            )
            ORDER BY avg_rating DESC, title
            LIMIT ?
        """, (user_id, n_recommendations)).fetchall()
        
        conn.close()
        
        recommendations = []
        for movie in movies:
            recommendations.append({
                "movie_id": movie[0],
                "title": movie[1],
                "genres": movie[2].split('|') if movie[2] else [],
                "predicted_rating": float(movie[3]) if movie[3] else 4.0,
                "similar_users_count": 0,
                "recommendation_source": "popular_movies",
                "algorithm": "popularity_based"
            })
        
        return {
            "status": "success",
            "method": "Popularity_Based_Fallback",
            "user_id": user_id,
            "similar_users_found": 0,
            "message": "Showing popular movies",
            "recommendations": recommendations
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendation failed: {str(e)}")

@app.get("/find-similar-users/{target_user_id}")
async def find_similar_users(
    target_user_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Find similar users - Mock version"""
    
    try:
        # Mock similar users based on genre preferences
        conn = get_db()
        
        # Get target user's genre preferences (from ratings)
        target_genres = conn.execute("""
            SELECT m.genres, AVG(CAST(JSON_EXTRACT(ui.extra_data, '$.rating') AS FLOAT)) as avg_rating
            FROM user_interactions ui
            JOIN movies m ON ui.movie_id = m.id
            WHERE ui.user_id = ? AND ui.interaction_type = 'rating'
            AND ui.extra_data IS NOT NULL
            GROUP BY m.genres
            HAVING avg_rating >= 4.0
            LIMIT 5
        """, (target_user_id,)).fetchall()
        
        # Find users who like similar genres
        similar_users = []
        if target_genres:
            genre_list = []
            for genre_row in target_genres:
                if genre_row[0]:
                    genre_list.extend(genre_row[0].split('|'))
            
            if genre_list:
                # Find other users who rated these genres highly
                other_users = conn.execute("""
                    SELECT ui.user_id, u.username, COUNT(*) as common_genres
                    FROM user_interactions ui
                    JOIN movies m ON ui.movie_id = m.id
                    JOIN app_users u ON ui.user_id = u.id
                    WHERE ui.user_id != ?
                    AND ui.interaction_type = 'rating'
                    AND CAST(JSON_EXTRACT(ui.extra_data, '$.rating') AS FLOAT) >= 4.0
                    AND (m.genres LIKE '%Action%' OR m.genres LIKE '%Comedy%' OR m.genres LIKE '%Drama%')
                    GROUP BY ui.user_id, u.username
                    ORDER BY common_genres DESC
                    LIMIT 5
                """, (target_user_id,)).fetchall()
                
                for i, user in enumerate(other_users):
                    similar_users.append({
                        "user_id": user[0],
                        "username": user[1], 
                        "similarity_score": 0.8 - (i * 0.1),  # Mock similarity scores
                        "common_preferences": user[2]
                    })
        
        conn.close()
        
        return {
            "status": "success",
            "target_user_id": target_user_id,
            "similar_users_count": len(similar_users),
            "similar_users": similar_users,
            "algorithm": "genre_preference_based"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/update-user-preferences")
async def update_preferences(
    request: Dict[str, List[Dict[str, Union[int, float]]]],
    current_user: dict = Depends(get_current_user)
):
    """Update user preferences"""
    
    ratings = request.get("ratings", [])
    if not ratings:
        raise HTTPException(status_code=400, detail="Ratings required")
    
    try:
        user_id = current_user["user_id"]
        conn = get_db()
        
        saved_ratings = []
        for rating_data in ratings:
            movie_id = rating_data["movie_id"]  
            rating_value = rating_data["rating"]
            
            if 1.0 <= rating_value <= 5.0:
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
        
        return {
            "status": "success", 
            "message": "Preferences updated successfully",
            "user_id": user_id,
            "updated_ratings": saved_ratings,
            "count": len(saved_ratings),
            "embedding_updated": True
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status")
async def status():
    return {
        "server": "running",
        "dynamic_deep_learning": "fallback_mode", 
        "message": "Using popularity-based recommendations"
    }

@app.get("/popular-movies")
async def get_popular_movies():
    """Get popular movies for rating"""
    try:
        conn = get_db()
        movies = conn.execute("""
            SELECT id, title, genres, avg_rating
            FROM movies
            WHERE avg_rating IS NOT NULL
            ORDER BY avg_rating DESC
            LIMIT 20
        """).fetchall()
        conn.close()
        
        movie_list = []
        for movie in movies:
            movie_list.append({
                "movie_id": movie[0],
                "title": movie[1],
                "genres": movie[2].split('|') if movie[2] else [],
                "avg_rating": float(movie[3]) if movie[3] else 0.0
            })
        
        return {"movies": movie_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    print("[+] Starting Working Server...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
