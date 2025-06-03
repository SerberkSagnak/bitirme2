from fastapi import FastAPI, HTTPException, Depends, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
import pandas as pd
import numpy as np
import json

# Import ettiğimiz modüller
from database_fixed import get_db, User, Movie, Rating, Favorite, UserActivity
from auth import UserService, create_access_token, verify_token, ACCESS_TOKEN_EXPIRE_MINUTES
from datetime import timedelta

# Mevcut data
user_movie_matrix = pd.read_pickle('user_movie_matrix.pkl')

# FastAPI App
app = FastAPI(title="🎬 Film Öneri Sistemi v3.0 - User System", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
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

class AddToFavorites(BaseModel):
    movie_id: int
    list_type: str = "favorite"  # favorite, watchlist, watched

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

# 🆕 AUTH ENDPOINTS
@app.post("/register")
async def register_user(user_data: UserRegister, db: Session = Depends(get_db)):
    """Kullanıcı kaydı"""
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
    """Kullanıcı girişi"""
    try:
        user_service = UserService()
        user = user_service.authenticate_user(user_data.username, user_data.password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Yanlış kullanıcı adı veya şifre"
            )
        
        # Token oluştur
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

@app.get("/profile")
async def get_user_profile(current_user: User = Depends(get_current_user)):
    """Kullanıcı profili"""
    return {
        "status": "success",
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "age": current_user.age,
            "gender": current_user.gender,
            "favorite_genres": json.loads(current_user.favorite_genres) if current_user.favorite_genres else [],
            "created_at": current_user.created_at,
            "last_active": current_user.last_active
        }
    }

# 🆕 USER-SPECIFIC RATING
@app.post("/rate-movie")
async def rate_movie(
    rating_data: UserRating, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Film puanlama (kullanıcı özel)"""
    try:
        # Movie var mı kontrol et
        movie = db.query(Movie).filter(Movie.movie_id == rating_data.movie_id).first()
        if not movie:
            raise HTTPException(status_code=404, detail="Film bulunamadı")
        
        # Mevcut rating var mı?
        existing_rating = db.query(Rating).filter(
            Rating.user_id == current_user.id,
            Rating.movie_id == movie.id
        ).first()
        
        if existing_rating:
            # Güncelle
            existing_rating.rating = rating_data.rating
            existing_rating.updated_at = datetime.utcnow()
        else:
            # Yeni rating
            new_rating = Rating(
                user_id=current_user.id,
                movie_id=movie.id,
                rating=rating_data.rating
            )
            db.add(new_rating)
        
        # Activity log
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

# 🆕 USER-SPECIFIC RECOMMENDATIONS
@app.get("/my-recommendations")
async def get_user_recommendations(
    n_recommendations: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Kullanıcı özel öneriler"""
    try:
        # Kullanıcının puanladığı filmleri al
        user_ratings = db.query(Rating).filter(Rating.user_id == current_user.id).all()
        
        # Dictionary formatına çevir
        ratings_dict = {}
        for rating in user_ratings:
            movie = db.query(Movie).filter(Movie.id == rating.movie_id).first()
            if movie:
                ratings_dict[movie.movie_id] = rating.rating
        
        # Recommendation engine çalıştır
        if len(ratings_dict) == 0:
            method = "YENİ KULLANICI: Popüler filmler"
            # En popüler filmleri öner
            popular_movies = db.query(Movie).order_by(Movie.popularity_score.desc()).limit(n_recommendations).all()
            recommendations = []
            for movie in popular_movies:
                recommendations.append({
                    "movie_id": movie.movie_id,
                    "title": movie.title,
                    "avg_rating": movie.avg_rating,
                    "popularity": movie.rating_count,
                    "genres": json.loads(movie.genres) if movie.genres else [],
                    "score": movie.popularity_score
                })
        else:
            method = f"KİŞİSELLEŞTİRİLMİŞ: {len(ratings_dict)} puanlamaya dayalı"
            # Burada gelişmiş recommendation algoritması olacak
            # Şimdilik popüler olanları filtreleyelim
            rated_movie_ids = list(ratings_dict.keys())
            popular_movies = db.query(Movie).filter(
                ~Movie.movie_id.in_(rated_movie_ids)
            ).order_by(Movie.popularity_score.desc()).limit(n_recommendations).all()
            
            recommendations = []
            for movie in popular_movies:
                recommendations.append({
                    "movie_id": movie.movie_id,
                    "title": movie.title,
                    "avg_rating": movie.avg_rating,
                    "popularity": movie.rating_count,
                    "genres": json.loads(movie.genres) if movie.genres else [],
                    "score": movie.popularity_score
                })
        
        return {
            "status": "success",
            "user_rating_count": len(ratings_dict),
            "method": method,
            "recommendations": recommendations
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mevcut endpoint'ler (anonim kullanım için)
@app.get("/")
async def root():
    return {
        "message": "🎬 Film Öneri Sistemi v3.0 - User System Ready!",
        "features": ["user_auth", "personalized_recommendations", "rating_system"],
        "endpoints": ["/register", "/login", "/profile", "/rate-movie", "/my-recommendations"]
    }

@app.get("/onboarding-movies")
async def get_onboarding_movies():
    """Anonim kullanıcılar için onboarding filmleri"""
    try:
        popular_movies = db.query(Movie).order_by(Movie.popularity_score.desc()).limit(15).all()
        movies_list = []
        
        for movie in popular_movies:
            movies_list.append({
                "movie_id": movie.movie_id,
                "title": movie.title,
                "avg_rating": movie.avg_rating,
                "popularity": movie.rating_count,
                "genres": json.loads(movie.genres) if movie.genres else [],
                "score": movie.popularity_score
            })
        
        return {"status": "success", "count": len(movies_list), "movies": movies_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search")
async def search_movies(q: str = Query(..., description="Arama terimi"), db: Session = Depends(get_db)):
    """Film arama"""
    try:
        # Database'den arama
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

if __name__ == "__main__":
    import uvicorn
    print("🚀 User System API başlatılıyor...")
    uvicorn.run(app, host="0.0.0.0", port=8000)