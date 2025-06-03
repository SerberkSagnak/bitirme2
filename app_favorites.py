from fastapi import FastAPI, HTTPException, Depends, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
import pandas as pd
import numpy as np
import json
from datetime import datetime

# Import modüller
from database_fixed import get_db, User, Movie, Rating, Favorite, UserActivity
from auth import UserService, create_access_token, verify_token, ACCESS_TOKEN_EXPIRE_MINUTES
from advanced_recommender import HybridRecommendationEngine
from datetime import timedelta

# Global recommendation engine
rec_engine = HybridRecommendationEngine()

# FastAPI App
app = FastAPI(title="🎬 Film Öneri Sistemi v5.0 - Favorites & Watchlist", version="5.0.0")

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

class FavoriteRequest(BaseModel):
    movie_id: int

class WatchlistRequest(BaseModel):
    movie_id: int
    status: str = "to_watch"  # "to_watch", "watched", "removed"

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

# 🆕 FAVORITES ENDPOINTS
@app.post("/add-to-favorites")
async def add_to_favorites(
    favorite_request: FavoriteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Film favorilere ekle"""
    try:
        # Film var mı kontrol et
        movie = db.query(Movie).filter(Movie.movie_id == favorite_request.movie_id).first()
        if not movie:
            raise HTTPException(status_code=404, detail="Film bulunamadı")
        
        # Zaten favori mi?
        existing_favorite = db.query(Favorite).filter(
            Favorite.user_id == current_user.id,
            Favorite.movie_id == movie.id
        ).first()
        
        if existing_favorite:
            return {"status": "info", "message": "Film zaten favorilerinizde"}
        
        # Favori ekle
        new_favorite = Favorite(
            user_id=current_user.id,
            movie_id=movie.id
        )
        db.add(new_favorite)
        
        # Activity log
        activity = UserActivity(
            user_id=current_user.id,
            activity_type="favorite",
            movie_id=movie.id,
            extra_data=json.dumps({"action": "add"})
        )
        db.add(activity)
        
        db.commit()
        
        return {
            "status": "success",
            "message": f"'{movie.title}' favorilerinize eklendi! ❤️"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/remove-from-favorites/{movie_id}")
async def remove_from_favorites(
    movie_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Film favorilerden çıkar"""
    try:
        # Film var mı kontrol et
        movie = db.query(Movie).filter(Movie.movie_id == movie_id).first()
        if not movie:
            raise HTTPException(status_code=404, detail="Film bulunamadı")
        
        # Favori var mı?
        favorite = db.query(Favorite).filter(
            Favorite.user_id == current_user.id,
            Favorite.movie_id == movie.id
        ).first()
        
        if not favorite:
            return {"status": "info", "message": "Film zaten favorilerinizde değil"}
        
        # Favoriyi sil
        db.delete(favorite)
        
        # Activity log
        activity = UserActivity(
            user_id=current_user.id,
            activity_type="unfavorite",
            movie_id=movie.id,
            extra_data=json.dumps({"action": "remove"})
        )
        db.add(activity)
        
        db.commit()
        
        return {
            "status": "success",
            "message": f"'{movie.title}' favorilerinizden çıkarıldı! 💔"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/my-favorites")
async def get_my_favorites(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Kullanıcının favori filmlerini listele"""
    try:
        favorites = db.query(Favorite).filter(Favorite.user_id == current_user.id).all()
        
        favorite_movies = []
        for favorite in favorites:
            movie = db.query(Movie).filter(Movie.id == favorite.movie_id).first()
            if movie:
                favorite_movies.append({
                    "movie_id": movie.movie_id,
                    "title": movie.title,
                    "release_date": movie.release_date,
                    "avg_rating": movie.avg_rating,
                    "popularity": movie.rating_count,
                    "genres": json.loads(movie.genres) if movie.genres else [],
                    "imdb_url": movie.imdb_url,
                    "added_to_favorites": favorite.created_at.isoformat()
                })
        
        # En son eklenen önce
        favorite_movies.sort(key=lambda x: x['added_to_favorites'], reverse=True)
        
        return {
            "status": "success",
            "count": len(favorite_movies),
            "favorites": favorite_movies
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/favorites-based-recommendations")
async def get_favorites_based_recommendations(
    n_recommendations: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Favori filmlere dayalı öneriler"""
    try:
        # Kullanıcının favori filmlerini al
        favorites = db.query(Favorite).filter(Favorite.user_id == current_user.id).all()
        
        if not favorites:
            return {
                "status": "info",
                "message": "Önce birkaç film favorinize ekleyin!",
                "recommendations": []
            }
        
        # Favori film ID'lerini topla
        favorite_movie_ids = []
        for favorite in favorites:
            movie = db.query(Movie).filter(Movie.id == favorite.movie_id).first()
            if movie:
                favorite_movie_ids.append(movie.movie_id)
        
        # Kullanıcının puanlamalarını al
        user_ratings_db = db.query(Rating).filter(Rating.user_id == current_user.id).all()
        user_ratings = {}
        
        for rating in user_ratings_db:
            movie = db.query(Movie).filter(Movie.id == rating.movie_id).first()
            if movie:
                user_ratings[movie.movie_id] = rating.rating
        
        # Content-based öneriler (favori filmlere benzer)
        recommendations = rec_engine.get_content_based_recommendations(
            liked_movie_ids=favorite_movie_ids,
            user_ratings=user_ratings,
            n_recommendations=n_recommendations
        )
        
        return {
            "status": "success",
            "favorite_count": len(favorite_movie_ids),
            "method": f"FAVORİ FİLMLERE DAYALI ÖNERİLER ({len(favorite_movie_ids)} favori film)",
            "recommendations": recommendations
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 🆕 WATCHLIST ENDPOINTS
@app.post("/add-to-watchlist")
async def add_to_watchlist(
    watchlist_request: WatchlistRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Film watchlist'e ekle"""
    try:
        # Film var mı kontrol et
        movie = db.query(Movie).filter(Movie.movie_id == watchlist_request.movie_id).first()
        if not movie:
            raise HTTPException(status_code=404, detail="Film bulunamadı")
        
        # Watchlist entry var mı kontrol et (UserActivity tablosunda)
        existing_watchlist = db.query(UserActivity).filter(
            UserActivity.user_id == current_user.id,
            UserActivity.movie_id == movie.id,
            UserActivity.activity_type == "watchlist"
        ).first()
        
        if existing_watchlist:
            # Mevcut watchlist entry'yi güncelle
            existing_watchlist.extra_data = json.dumps({"status": watchlist_request.status})
            existing_watchlist.created_at = datetime.utcnow()
        else:
            # Yeni watchlist entry oluştur
            watchlist_activity = UserActivity(
                user_id=current_user.id,
                activity_type="watchlist",
                movie_id=movie.id,
                extra_data=json.dumps({"status": watchlist_request.status})
            )
            db.add(watchlist_activity)
        
        db.commit()
        
        status_messages = {
            "to_watch": f"'{movie.title}' izleme listenize eklendi! 📋",
            "watched": f"'{movie.title}' izlendi olarak işaretlendi! ✅",
            "removed": f"'{movie.title}' izleme listenizden çıkarıldı! ❌"
        }
        
        return {
            "status": "success",
            "message": status_messages.get(watchlist_request.status, "Watchlist güncellendi!")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/my-watchlist")
async def get_my_watchlist(
    status_filter: str = Query("to_watch", description="to_watch, watched, all"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Kullanıcının watchlist'ini listele"""
    try:
        watchlist_query = db.query(UserActivity).filter(
            UserActivity.user_id == current_user.id,
            UserActivity.activity_type == "watchlist"
        )
        
        watchlist_entries = watchlist_query.all()
        
        watchlist_movies = []
        for entry in watchlist_entries:
            extra_data = json.loads(entry.extra_data) if entry.extra_data else {}
            entry_status = extra_data.get("status", "to_watch")
            
            # Status filtreleme
            if status_filter != "all" and entry_status != status_filter:
                continue
            
            if entry_status == "removed":
                continue
                
            movie = db.query(Movie).filter(Movie.id == entry.movie_id).first()
            if movie:
                watchlist_movies.append({
                    "movie_id": movie.movie_id,
                    "title": movie.title,
                    "release_date": movie.release_date,
                    "avg_rating": movie.avg_rating,
                    "popularity": movie.rating_count,
                    "genres": json.loads(movie.genres) if movie.genres else [],
                    "imdb_url": movie.imdb_url,
                    "watchlist_status": entry_status,
                    "added_to_watchlist": entry.created_at.isoformat()
                })
        
        # En son eklenen önce
        watchlist_movies.sort(key=lambda x: x['added_to_watchlist'], reverse=True)
        
        return {
            "status": "success",
            "filter": status_filter,
            "count": len(watchlist_movies),
            "watchlist": watchlist_movies
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 🆕 USER STATISTICS
@app.get("/user-stats")
async def get_user_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Kullanıcının istatistiklerini getir"""
    try:
        # Ratings sayısı
        ratings_count = db.query(Rating).filter(Rating.user_id == current_user.id).count()
        
        # Favorites sayısı
        favorites_count = db.query(Favorite).filter(Favorite.user_id == current_user.id).count()
        
        # Watchlist sayıları
        watchlist_to_watch = db.query(UserActivity).filter(
            UserActivity.user_id == current_user.id,
            UserActivity.activity_type == "watchlist"
        ).all()
        
        to_watch_count = 0
        watched_count = 0
        
        for entry in watchlist_to_watch:
            extra_data = json.loads(entry.extra_data) if entry.extra_data else {}
            status = extra_data.get("status", "to_watch")
            
            if status == "to_watch":
                to_watch_count += 1
            elif status == "watched":
                watched_count += 1
        
        # Favori türleri
        favorite_genres = json.loads(current_user.favorite_genres) if current_user.favorite_genres else []
        
        return {
            "status": "success",
            "stats": {
                "ratings_count": ratings_count,
                "favorites_count": favorites_count,
                "to_watch_count": to_watch_count,
                "watched_count": watched_count,
                "favorite_genres_count": len(favorite_genres),
                "total_activity": ratings_count + favorites_count + to_watch_count + watched_count
            },
            "user_info": {
                "username": current_user.username,
                "email": current_user.email,
                "age": current_user.age,
                "gender": current_user.gender,
                "favorite_genres": favorite_genres,
                "member_since": current_user.created_at.isoformat()
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mevcut endpoint'leri koru (önceki app_advanced.py'dan kopyala)
# ... (diğer endpoint'ler burada olacak - Register, Login, Rate, Search vs.)

@app.get("/")
async def root():
    return {
        "message": "🎬 Film Öneri Sistemi v5.0 - Favorites & Watchlist Ready!",
        "features": ["favorites", "watchlist", "user_stats", "favorites_recommendations"],
        "new_endpoints": ["/add-to-favorites", "/my-favorites", "/add-to-watchlist", "/my-watchlist", "/user-stats"]
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Favorites & Watchlist API başlatılıyor...")
    uvicorn.run(app, host="0.0.0.0", port=8000)