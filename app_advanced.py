from fastapi import FastAPI, HTTPException, Depends, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
import pandas as pd
import numpy as np
import json

# Import modüller
from database_fixed import get_db, User, Movie, Rating, Favorite, UserActivity
from auth import UserService, create_access_token, verify_token, ACCESS_TOKEN_EXPIRE_MINUTES
from advanced_recommender import HybridRecommendationEngine
from datetime import timedelta

# Global recommendation engine
rec_engine = HybridRecommendationEngine()

# FastAPI App
app = FastAPI(title="🎬 Film Öneri Sistemi v4.0 - Advanced", version="4.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# Pydantic Models
class UserRegister(BaseModel):
    username: str
    email: str
    password: str
    age: Optional[int] = None
    gender: Optional[str] = None
    favorite_genres: Optional[List[str]] = None

class UserLogin(BaseModel):
    username: str
    password: str

class UserRating(BaseModel):
    movie_id: int
    rating: float

class GenreRequest(BaseModel):
    genres: List[str]
    n_recommendations: int = 10

# Dependency: Current User
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials
    username = verify_token(token)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# 🆕 GENRE ENDPOINTS
@app.get("/genres")
async def get_all_genres(db: Session = Depends(get_db)):
    """Sistemdeki tüm film türlerini listele"""
    try:
        movies = db.query(Movie).all()
        all_genres = set()
        
        for movie in movies:
            if movie.genres:
                genres = json.loads(movie.genres)
                all_genres.update(genres)
        
        # 'unknown' türünü çıkar ve sırala
        all_genres.discard('unknown')
        sorted_genres = sorted(list(all_genres))
        
        return {
            "status": "success",
            "count": len(sorted_genres),
            "genres": sorted_genres
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/genre-recommendations")
async def get_genre_recommendations(
    genre_request: GenreRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Belirtilen türlere göre öneriler"""
    try:
        # Kullanıcının puanladığı filmleri al
        user_ratings_db = db.query(Rating).filter(Rating.user_id == current_user.id).all()
        user_ratings = {}
        
        for rating in user_ratings_db:
            movie = db.query(Movie).filter(Movie.id == rating.movie_id).first()
            if movie:
                user_ratings[movie.movie_id] = rating.rating
        
        # Genre-based öneriler al
        recommendations = rec_engine.get_genre_based_recommendations(
            preferred_genres=genre_request.genres,
            user_ratings=user_ratings,
            n_recommendations=genre_request.n_recommendations
        )
        
        return {
            "status": "success",
            "requested_genres": genre_request.genres,
            "user_rated_count": len(user_ratings),
            "method": f"TÜR BAZLI ÖNERİLER: {', '.join(genre_request.genres)}",
            "recommendations": recommendations
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/similar-movies/{movie_id}")
async def get_similar_movies(
    movie_id: int,
    n_recommendations: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Belirtilen filme benzer filmler"""
    try:
        # Film var mı kontrol et
        movie = db.query(Movie).filter(Movie.movie_id == movie_id).first()
        if not movie:
            raise HTTPException(status_code=404, detail="Film bulunamadı")
        
        # Kullanıcının puanladığı filmleri al
        user_ratings_db = db.query(Rating).filter(Rating.user_id == current_user.id).all()
        user_ratings = {}
        
        for rating in user_ratings_db:
            rated_movie = db.query(Movie).filter(Movie.id == rating.movie_id).first()
            if rated_movie:
                user_ratings[rated_movie.movie_id] = rating.rating
        
        # Content-based öneriler
        recommendations = rec_engine.get_content_based_recommendations(
            liked_movie_ids=[movie_id],
            user_ratings=user_ratings,
            n_recommendations=n_recommendations
        )
        
        return {
            "status": "success",
            "base_movie": {
                "movie_id": movie.movie_id,
                "title": movie.title,
                "genres": json.loads(movie.genres) if movie.genres else []
            },
            "method": f"BENZER FİLMLER: {movie.title}",
            "recommendations": recommendations
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/advanced-recommendations")
async def get_advanced_recommendations(
    n_recommendations: int = 12,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Gelişmiş hybrid öneriler"""
    try:
        # Kullanıcının profil bilgilerini al
        user_genres = []
        if current_user.favorite_genres:
            user_genres = json.loads(current_user.favorite_genres)
        
        # Hybrid öneriler al
        recommendations = rec_engine.get_hybrid_recommendations(
            user_id=current_user.id,
            preferred_genres=user_genres,
            n_recommendations=n_recommendations
        )
        
        return {
            "status": "success",
            "user_id": current_user.id,
            "user_favorite_genres": user_genres,
            "method": "GELİŞMİŞ HYBRİD ÖNERİLER (Genre + Content + Collaborative)",
            "breakdown": {
                "genre_based_count": len(recommendations['genre_based']),
                "content_based_count": len(recommendations['content_based']),
                "collaborative_count": len(recommendations['collaborative'])
            },
            "recommendations": recommendations['final_hybrid'],
            "detailed_breakdown": {
                "genre_based": recommendations['genre_based'][:3],
                "content_based": recommendations['content_based'][:3],
                "collaborative": recommendations['collaborative'][:3]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/update-genre-preferences")
async def update_user_genre_preferences(
    genre_request: GenreRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Kullanıcının tür tercihlerini güncelle"""
    try:
        # User'ın favorite_genres'ini güncelle
        current_user.favorite_genres = json.dumps(genre_request.genres)
        db.commit()
        
        return {
            "status": "success",
            "message": "Tür tercihleri güncellendi",
            "updated_genres": genre_request.genres
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mevcut endpoint'leri koru (auth, rating, search vs.)
@app.post("/register")
async def register_user(user_data: UserRegister, db: Session = Depends(get_db)):
    try:
        user_service = UserService()
        user = user_service.create_user(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            age=user_data.age,
            gender=user_data.gender,
            favorite_genres=user_data.favorite_genres
        )
        
        return {
            "status": "success",
            "message": "Kullanıcı başarıyla oluşturuldu",
            "user_id": user.id,
            "username": user.username
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/login")
async def login_user(user_data: UserLogin, db: Session = Depends(get_db)):
    try:
        user_service = UserService()
        user = user_service.authenticate_user(user_data.username, user_data.password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Yanlış kullanıcı adı veya şifre"
            )
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        
        return {
            "status": "success",
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "age": user.age,
                "gender": user.gender,
                "favorite_genres": json.loads(user.favorite_genres) if user.favorite_genres else []
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/rate-movie")
async def rate_movie(
    rating_data: UserRating, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        movie = db.query(Movie).filter(Movie.movie_id == rating_data.movie_id).first()
        if not movie:
            raise HTTPException(status_code=404, detail="Film bulunamadı")
        
        existing_rating = db.query(Rating).filter(
            Rating.user_id == current_user.id,
            Rating.movie_id == movie.id
        ).first()
        
        if existing_rating:
            existing_rating.rating = rating_data.rating
            existing_rating.updated_at = datetime.utcnow()
        else:
            new_rating = Rating(
                user_id=current_user.id,
                movie_id=movie.id,
                rating=rating_data.rating
            )
            db.add(new_rating)
        
        activity = UserActivity(
            user_id=current_user.id,
            activity_type="rate",
            movie_id=movie.id,
            extra_data=json.dumps({"rating": rating_data.rating})
        )
        db.add(activity)
        
        db.commit()
        
        return {
            "status": "success",
            "message": f"{movie.title} filmi {rating_data.rating} puan ile değerlendirildi"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search")
async def search_movies(q: str = Query(..., description="Arama terimi"), db: Session = Depends(get_db)):
    try:
        search_results = db.query(Movie).filter(
            Movie.title.contains(q)
        ).order_by(Movie.popularity_score.desc()).limit(20).all()
        
        results = []
        for movie in search_results:
            results.append({
                "movie_id": movie.movie_id,
                "title": movie.title,
                "release_date": movie.release_date,
                "avg_rating": movie.avg_rating,
                "popularity": movie.rating_count,
                "genres": json.loads(movie.genres) if movie.genres else [],
                "imdb_url": movie.imdb_url
            })
        
        return {
            "status": "success",
            "query": q,
            "count": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {
        "message": "🎬 Film Öneri Sistemi v4.0 - Advanced Ready!",
        "features": ["hybrid_recommendations", "genre_filtering", "content_based", "collaborative"],
        "new_endpoints": ["/genres", "/genre-recommendations", "/similar-movies", "/advanced-recommendations"]
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Advanced API başlatılıyor...")
    uvicorn.run(app, host="0.0.0.0", port=8000)