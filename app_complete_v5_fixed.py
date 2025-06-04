from fastapi import FastAPI, HTTPException, Depends, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
import json
from datetime import datetime
from ml_service_simple import ml_service



# Import modüller
from database_fixed import get_db, User, Movie, Rating, Favorite, UserActivity# app_complete_v5_fixed.py dosyasının EN BAŞINA şunu ekle:
from ml_service_simple import ml_service

from auth import UserService, create_access_token, verify_token, ACCESS_TOKEN_EXPIRE_MINUTES
from advanced_recommender import HybridRecommendationEngine
from datetime import timedelta

# Global recommendation engine
rec_engine = HybridRecommendationEngine()

# FastAPI App
app = FastAPI(title="🎬 Film Öneri Sistemi v5.0 - Fixed Edition", version="5.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# Pydantic Models
# Bu satırları 31. satırdan sonra ekleyin:
class AdvancedRecommendationRequest(BaseModel):
    n_recommendations: int = 20
    hybrid_method: str = "weighted"

class GenreBasedRequest(BaseModel):
    genres: List[str]
    n_recommendations: int = 15

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
    status: str = "to_watch"

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

# 🔑 AUTH ENDPOINTS
@app.post("/register")
async def register_user(user_data: UserRegister, db: Session = Depends(get_db)):
    """Kullanıcı kaydı"""
    try:
        user_service = UserService(db)
        
        # Kullanıcı zaten var mı?
        if user_service.get_user_by_username(user_data.username):
            raise HTTPException(status_code=400, detail="Bu kullanıcı adı zaten kullanılıyor")
        
        if user_service.get_user_by_email(user_data.email):
            raise HTTPException(status_code=400, detail="Bu email adresi zaten kullanılıyor")
        
        # Kullanıcı oluştur
        new_user = user_service.create_user(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            age=user_data.age,
            gender=user_data.gender,
            favorite_genres=user_data.favorite_genres or []
        )
        
        return {
            "status": "success",
            "message": "Kullanıcı başarıyla kaydedildi!",
            "user_id": new_user.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/login")
async def login_user(login_data: UserLogin, db: Session = Depends(get_db)):
    """Kullanıcı girişi"""
    try:
        user_service = UserService(db)
        user = user_service.authenticate_user(login_data.username, login_data.password)
        
        if not user:
            raise HTTPException(status_code=401, detail="Kullanıcı adı veya şifre hatalı")
        
        # JWT token oluştur
        access_token = create_access_token(data={"sub": user.username})
        
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
                "favorite_genres": json.loads(user.favorite_genres) if user.favorite_genres else [],
                "created_at": user.created_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 🎬 MOVIE ENDPOINTS
@app.get("/search")
async def search_movies(q: str, limit: int = 20, db: Session = Depends(get_db)):
    """Film arama - Database'den"""
    try:
        # Database'den arama yap
        movies = db.query(Movie).filter(
            Movie.title.ilike(f"%{q}%")
        ).limit(limit).all()
        
        results = []
        for movie in movies:
            results.append({
                "movie_id": movie.movie_id,
                "title": movie.title,
                "release_date": movie.release_date,
                "avg_rating": round(movie.avg_rating, 2) if movie.avg_rating else 0,
                "popularity": movie.rating_count if movie.rating_count else 0,
                "genres": json.loads(movie.genres) if movie.genres else [],
                "imdb_url": movie.imdb_url if movie.imdb_url else None
            })
        
        return {
            "status": "success",
            "query": q,
            "count": len(results),
            "results": results
        }
        
    except Exception as e:
        print(f"Search error: {e}")  # Debug için
        raise HTTPException(status_code=500, detail=f"Arama hatası: {str(e)}")

@app.get("/genres")
async def get_all_genres(db: Session = Depends(get_db)):
    """Tüm film türlerini getir - Database'den"""
    try:
        # Database'den tüm film türlerini topla
        movies = db.query(Movie).filter(Movie.genres.isnot(None)).all()
        all_genres = set()
        
        for movie in movies:
            if movie.genres:
                try:
                    genres = json.loads(movie.genres)
                    if isinstance(genres, list):
                        all_genres.update(genres)
                except:
                    continue
        
        # Eğer database'de türler yoksa default türler ekle
        if not all_genres:
            all_genres = {
                "Action", "Adventure", "Animation", "Comedy", "Crime", 
                "Documentary", "Drama", "Family", "Fantasy", "Horror",
                "Music", "Mystery", "Romance", "Science Fiction", 
                "Thriller", "War", "Western"
            }
        
        return {
            "status": "success",
            "genres": sorted(list(all_genres))
        }
        
    except Exception as e:
        print(f"Genres error: {e}")  # Debug için
        # Fallback olarak default türleri döndür
        default_genres = [
            "Action", "Adventure", "Animation", "Comedy", "Crime", 
            "Documentary", "Drama", "Family", "Fantasy", "Horror",
            "Music", "Mystery", "Romance", "Science Fiction", 
            "Thriller", "War", "Western"
        ]
        return {
            "status": "success",
            "genres": default_genres
        }

@app.post("/rate-movie")
async def rate_movie(
    rating_data: UserRating,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Film puanlama"""
    try:
        # Film var mı kontrol et
        movie = db.query(Movie).filter(Movie.movie_id == rating_data.movie_id).first()
        if not movie:
            raise HTTPException(status_code=404, detail="Film bulunamadı")
        
        # Daha önce puanlamış mı?
        existing_rating = db.query(Rating).filter(
            Rating.user_id == current_user.id,
            Rating.movie_id == movie.id
        ).first()
        
        if existing_rating:
            existing_rating.rating = rating_data.rating
            existing_rating.created_at = datetime.utcnow()
        else:
            new_rating = Rating(
                user_id=current_user.id,
                movie_id=movie.id,
                rating=rating_data.rating
            )
            db.add(new_rating)
        
        # Activity log
        activity = UserActivity(
            user_id=current_user.id,
            activity_type="rating",
            movie_id=movie.id,
            extra_data=json.dumps({"rating": rating_data.rating})
        )
        db.add(activity)
        
        db.commit()
        
        return {
            "status": "success",
            "message": f"'{movie.title}' filmi {rating_data.rating} ⭐ ile puanlandı!"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ❤️ FAVORITES ENDPOINTS
@app.post("/add-to-favorites")
async def add_to_favorites(
    favorite_request: FavoriteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Film favorilere ekle"""
    try:
        movie = db.query(Movie).filter(Movie.movie_id == favorite_request.movie_id).first()
        if not movie:
            raise HTTPException(status_code=404, detail="Film bulunamadı")
        
        existing_favorite = db.query(Favorite).filter(
            Favorite.user_id == current_user.id,
            Favorite.movie_id == movie.id
        ).first()
        
        if existing_favorite:
            return {"status": "info", "message": "Film zaten favorilerinizde"}
        
        new_favorite = Favorite(
            user_id=current_user.id,
            movie_id=movie.id
        )
        db.add(new_favorite)
        
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
        movie = db.query(Movie).filter(Movie.movie_id == movie_id).first()
        if not movie:
            raise HTTPException(status_code=404, detail="Film bulunamadı")
        
        favorite = db.query(Favorite).filter(
            Favorite.user_id == current_user.id,
            Favorite.movie_id == movie.id
        ).first()
        
        if not favorite:
            return {"status": "info", "message": "Film zaten favorilerinizde değil"}
        
        db.delete(favorite)
        
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
        
        favorite_movies.sort(key=lambda x: x['added_to_favorites'], reverse=True)
        
        return {
            "status": "success",
            "count": len(favorite_movies),
            "favorites": favorite_movies
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 📋 WATCHLIST ENDPOINTS
@app.post("/add-to-watchlist")
async def add_to_watchlist(
    watchlist_request: WatchlistRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Film watchlist'e ekle"""
    try:
        movie = db.query(Movie).filter(Movie.movie_id == watchlist_request.movie_id).first()
        if not movie:
            raise HTTPException(status_code=404, detail="Film bulunamadı")
        
        existing_watchlist = db.query(UserActivity).filter(
            UserActivity.user_id == current_user.id,
            UserActivity.movie_id == movie.id,
            UserActivity.activity_type == "watchlist"
        ).first()
        
        if existing_watchlist:
            existing_watchlist.extra_data = json.dumps({"status": watchlist_request.status})
            existing_watchlist.created_at = datetime.utcnow()
        else:
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
        watchlist_entries = db.query(UserActivity).filter(
            UserActivity.user_id == current_user.id,
            UserActivity.activity_type == "watchlist"
        ).all()
        
        watchlist_movies = []
        for entry in watchlist_entries:
            extra_data = json.loads(entry.extra_data) if entry.extra_data else {}
            entry_status = extra_data.get("status", "to_watch")
            
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
        
        watchlist_movies.sort(key=lambda x: x['added_to_watchlist'], reverse=True)
        
        return {
            "status": "success",
            "filter": status_filter,
            "count": len(watchlist_movies),
            "watchlist": watchlist_movies
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 📊 USER STATS
@app.get("/user-stats")
async def get_user_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Kullanıcının istatistiklerini getir"""
    try:
        ratings_count = db.query(Rating).filter(Rating.user_id == current_user.id).count()
        favorites_count = db.query(Favorite).filter(Favorite.user_id == current_user.id).count()
        
        watchlist_entries = db.query(UserActivity).filter(
            UserActivity.user_id == current_user.id,
            UserActivity.activity_type == "watchlist"
        ).all()
        
        to_watch_count = 0
        watched_count = 0
        
        for entry in watchlist_entries:
            extra_data = json.loads(entry.extra_data) if entry.extra_data else {}
            status = extra_data.get("status", "to_watch")
            
            if status == "to_watch":
                to_watch_count += 1
            elif status == "watched":
                watched_count += 1
        
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

# 🤖 BASIC RECOMMENDATION ENDPOINTS
@app.get("/favorites-based-recommendations")
async def get_favorites_based_recommendations(
    n_recommendations: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Favori filmlere dayalı basit öneriler"""
    try:
        favorites = db.query(Favorite).filter(Favorite.user_id == current_user.id).all()
        
        if not favorites:
            return {
                "status": "info",
                "message": "Önce birkaç film favorinize ekleyin!",
                "recommendations": []
            }
        
        # Basit öneri: Favori filmlerin türlerini al ve o türlerden öneriler yap
        favorite_genres = set()
        for favorite in favorites:
            movie = db.query(Movie).filter(Movie.id == favorite.movie_id).first()
            if movie and movie.genres:
                try:
                    genres = json.loads(movie.genres)
                    favorite_genres.update(genres)
                except:
                    continue
        
        # O türlerden başka filmler öner
        recommended_movies = []
        if favorite_genres:
            all_movies = db.query(Movie).filter(
                Movie.genres.isnot(None)
            ).limit(100).all()
            
            for movie in all_movies:
                if movie.genres:
                    try:
                        movie_genres = set(json.loads(movie.genres))
                        if favorite_genres.intersection(movie_genres):
                            recommended_movies.append({
                                "movie_id": movie.movie_id,
                                "title": movie.title,
                                "release_date": movie.release_date,
                                "avg_rating": movie.avg_rating or 0,
                                "popularity": movie.rating_count or 0,
                                "genres": list(movie_genres),
                                "imdb_url": movie.imdb_url,
                                "similarity_score": len(favorite_genres.intersection(movie_genres)) / len(favorite_genres)
                            })
                    except:
                        continue
        
        # Benzerlik skoruna göre sırala
        recommended_movies.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        return {
            "status": "success",
            "favorite_count": len(favorites),
            "method": f"BASIT FAVORİ BAZLI ÖNERİLER ({len(favorite_genres)} tür)",
            "recommendations": recommended_movies[:n_recommendations]
        }
        
    except Exception as e:
        print(f"Favorites recommendations error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/similar-movies/{movie_id}")
async def get_similar_movies(
    movie_id: int,
    n_recommendations: int = 8,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Belirli bir filme benzer filmler - Basit versiyon"""
    try:
        # Ana filmi bul
        base_movie = db.query(Movie).filter(Movie.movie_id == movie_id).first()
        if not base_movie:
            raise HTTPException(status_code=404, detail="Film bulunamadı")
        
        base_genres = set()
        if base_movie.genres:
            try:
                base_genres = set(json.loads(base_movie.genres))
            except:
                pass
        
        # Benzer filmler bul
        similar_movies = []
        if base_genres:
            all_movies = db.query(Movie).filter(
                Movie.movie_id != movie_id,
                Movie.genres.isnot(None)
            ).limit(100).all()
            
            for movie in all_movies:
                if movie.genres:
                    try:
                        movie_genres = set(json.loads(movie.genres))
                        common_genres = base_genres.intersection(movie_genres)
                        if common_genres:
                            similarity = len(common_genres) / len(base_genres)
                            similar_movies.append({
                                "movie_id": movie.movie_id,
                                "title": movie.title,
                                "release_date": movie.release_date,
                                "avg_rating": movie.avg_rating or 0,
                                "popularity": movie.rating_count or 0,
                                "genres": list(movie_genres),
                                "imdb_url": movie.imdb_url,
                                "similarity_score": similarity
                            })
                    except:
                        continue
        
        # Benzerlik skoruna göre sırala
        similar_movies.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        return {
            "status": "success",
            "base_movie_id": movie_id,
            "method": "BASIT TÜR BAZLI BENZERLİK",
            "recommendations": similar_movies[:n_recommendations]
        }
        
    except Exception as e:
        print(f"Similar movies error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/update-genre-preferences")
async def update_genre_preferences(
    genre_request: GenreRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Kullanıcının tür tercihlerini güncelle"""
    try:
        current_user.favorite_genres = json.dumps(genre_request.genres)
        db.commit()
        
        return {
            "status": "success",
            "message": "Tür tercihleri güncellendi!",
            "genres": genre_request.genres
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mevcut advanced-recommendations endpoint'ini değiştir:
@app.post("/advanced-recommendations")
async def get_advanced_recommendations(
    request: AdvancedRecommendationRequest,  # dict yerine Pydantic model
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)):
    """Gelişmiş hibrit öneriler"""
    try:
        # request.n_recommendations kullanın (request['n_recommendations'] yerine)
        n_recommendations = request.n_recommendations
        
        # Kullanıcının puanladığı filmler
        user_ratings = db.query(Rating).filter(Rating.user_id == current_user.id).all()
        
        if len(user_ratings) < 3:
            return {
                "status": "info",
                "message": "Daha iyi öneriler için en az 3 film puanlayın!",
                "recommendations": []
            }
        
        # Yüksek puan verdiği filmlerden türleri topla
        liked_genres = set()
        for rating in user_ratings:
            if rating.rating >= 4.0:  # Beğendiği filmler
                movie = db.query(Movie).filter(Movie.id == rating.movie_id).first()
                if movie and movie.genres:
                    try:
                        genres = json.loads(movie.genres)
                        liked_genres.update(genres)
                    except:
                        continue
        
        # O türlerden öneriler
        recommendations = []
        if liked_genres:
            all_movies = db.query(Movie).filter(Movie.genres.isnot(None)).limit(200).all()
            
            for movie in all_movies:
                # Zaten puanladığı filmleri atla
                if any(r.movie_id == movie.id for r in user_ratings):
                    continue
                    
                if movie.genres:
                    try:
                        movie_genres = set(json.loads(movie.genres))
                        common = liked_genres.intersection(movie_genres)
                        if common:
                            score = len(common) / len(liked_genres)
                            # Popülerlik bonusu ekle
                            if movie.rating_count and movie.rating_count > 50:
                                score += 0.1
                            if movie.avg_rating and movie.avg_rating > 7.0:
                                score += 0.2
                                
                            recommendations.append({
                                "movie_id": movie.movie_id,
                                "title": movie.title,
                                "release_date": movie.release_date,
                                "avg_rating": movie.avg_rating or 0,
                                "popularity": movie.rating_count or 0,
                                "genres": list(movie_genres),
                                "imdb_url": movie.imdb_url,
                                "hybrid_score": round(score, 3)
                            })
                    except:
                        continue
        
        # Skora göre sırala
        recommendations.sort(key=lambda x: x['hybrid_score'], reverse=True)
        
        return {
            "status": "success",
            "method": "BASİT HİBRİT ÖNERİLER (Rating + Genre)",
            "user_rating_count": len(user_ratings),
            "recommendations": recommendations[:n_recommendations]
        }
        
    except Exception as e:
        print(f"Advanced recommendations error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {
        "message": "🎬 Film Öneri Sistemi v5.0 - Fixed Edition Ready!",
        "features": ["auth", "search", "rating", "favorites", "watchlist", "recommendations", "user_stats"],
        "version": "5.0.0-fixed",
        "note": "Database-based implementation"
    }


# 🤖 MACHINE LEARNING ENDPOINTS

@app.post("/ml/train")
async def train_ml_model(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ML modelini database verisiyle train et"""
    try:
        # Basit auth check (admin olması gerekiyor)
        if current_user.username != "admin":
            # Eğer admin yoksa, herhangi bir kullanıcı train edebilir (geliştirme için)
            pass
            
        success = ml_service.train_from_database(db)
        
        if success:
            return {
                "status": "success",
                "message": "🤖 ML Model başarıyla eğitildi!",
                "ml_status": ml_service.get_status()
            }
        else:
            return {
                "status": "error",
                "message": "❌ ML Model eğitimi başarısız! (Yetersiz veri olabilir)",
                "ml_status": ml_service.get_status()
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ML Training hatası: {str(e)}")

@app.get("/ml/recommendations")
async def get_ml_recommendations(
    n_recommendations: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ML bazlı kişiselleştirilmiş öneriler"""
    try:
        if not ml_service.is_ready:
            return {
                "status": "info",
                "message": "❌ ML modeli henüz hazır değil. Önce /ml/train endpoint'ini çağırın!",
                "recommendations": [],
                "ml_status": ml_service.get_status()
            }
        
        recommendations = ml_service.get_recommendations(
            user_id=current_user.id,
            db=db,
            n_recommendations=n_recommendations
        )
        
        return {
            "status": "success",
            "method": "🤖 MACHINE LEARNING COLLABORATIVE FILTERING",
            "user_id": current_user.id,
            "count": len(recommendations),
            "recommendations": recommendations,
            "ml_status": ml_service.get_status()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ML Recommendations hatası: {str(e)}")

@app.post("/ml/predict-rating")
async def predict_movie_rating(
    movie_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Kullanıcının bir filme vereceği puanı ML ile tahmin et"""
    try:
        if not ml_service.is_ready:
            raise HTTPException(status_code=400, detail="ML modeli henüz hazır değil!")
        
        # Movie'yi bul (external movie_id ile)
        movie = db.query(Movie).filter(Movie.movie_id == movie_id).first()
        if not movie:
            raise HTTPException(status_code=404, detail="Film bulunamadı")
        
        # ML ile tahmin yap (internal ID kullan)
        predicted_rating = ml_service.predict_rating(current_user.id, movie.id)
        
        return {
            "status": "success",
            "user_id": current_user.id,
            "movie_id": movie_id,
            "movie_title": movie.title,
            "predicted_rating": predicted_rating,
            "confidence": min(predicted_rating / 5.0, 1.0),
            "method": "🤖 ML Collaborative Filtering"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Puan tahmini hatası: {str(e)}")
    
    
@app.post("/genre-based-recommendations")
async def get_genre_based_recommendations(
    request: GenreBasedRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)):
    """Tür bazlı öneriler"""
    try:
        genres = request.genres
        n_recommendations = request.n_recommendations
        
        if not genres:
            return {
                "status": "error",
                "message": "Lütfen önce tür tercihlerinizi belirleyin!",
                "recommendations": []
            }
        
        # Tür bazlı filmler bul
        recommended_movies = []
        all_movies = db.query(Movie).filter(Movie.genres.isnot(None)).limit(200).all()
        
        for movie in all_movies:
            if movie.genres:
                try:
                    movie_genres = set(json.loads(movie.genres))
                    selected_genres = set(genres)
                    
                    # Ortak türler var mı?
                    common_genres = selected_genres.intersection(movie_genres)
                    if common_genres:
                        score = len(common_genres) / len(selected_genres)
                        
                        # Popülerlik bonusu
                        if movie.rating_count and movie.rating_count > 20:
                            score += 0.1
                        if movie.avg_rating and movie.avg_rating > 7.0:
                            score += 0.2
                        
                        recommended_movies.append({
                            "movie_id": movie.movie_id,
                            "title": movie.title,
                            "release_date": movie.release_date,
                            "avg_rating": movie.avg_rating or 0,
                            "popularity": movie.rating_count or 0,
                            "genres": list(movie_genres),
                            "imdb_url": movie.imdb_url,
                            "genre_match_score": round(score, 3)
                        })
                except:
                    continue
        
        # Skora göre sırala
        recommended_movies.sort(key=lambda x: x['genre_match_score'], reverse=True)
        
        return {
            "status": "success",
            "selected_genres": genres,
            "method": f"TÜR BAZLI ÖNERİLER ({len(genres)} tür seçili)",
            "recommendations": recommended_movies[:n_recommendations]
        }
        
    except Exception as e:
        print(f"Genre-based recommendations error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ml/status")
async def get_ml_status():
    """ML sistem durumu"""
    try:
        status = ml_service.get_status()
        
        return {
            "status": "success",
            "ml_system": status,
            "endpoints": {
                "train": "/ml/train (POST) - Modeli eğit",
                "recommendations": "/ml/recommendations (GET) - Öneriler al", 
                "predict": "/ml/predict-rating (POST) - Puan tahmini",
                "status": "/ml/status (GET) - Bu sayfa"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    print("🚀 Fixed Film Recommendation System v5.0 başlatılıyor...")
    uvicorn.run(app, host="0.0.0.0", port=8000)