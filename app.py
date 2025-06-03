from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List
import pandas as pd
import numpy as np

# Model classını import et
exec(open('adaptive_recommendation_fixed.py').read())

app = FastAPI(title="🎬 Film Öneri Sistemi API", version="1.0.0")

# Global model instance
recommender = AdaptiveRecommendationSystem()

class UserRatings(BaseModel):
    ratings: Dict[int, float]  # {movie_id: rating}
    n_recommendations: int = 10

class OnboardingResponse(BaseModel):
    movies: List[dict]

@app.get("/")
async def root():
    return {"message": "🎬 Film Öneri Sistemi API Çalışıyor!"}

@app.get("/onboarding-movies")
async def get_onboarding_movies():
    """Yeni kullanıcılar için onboarding filmlerini döndür"""
    try:
        popular_movies = get_popular_movies(15)
        movies_list = []
        
        for movie_id, score, avg_rating, popularity in popular_movies:
            movie_title = movies[movies['movie_id'] == movie_id]['title'].values[0]
            movies_list.append({
                "movie_id": movie_id,
                "title": movie_title,
                "avg_rating": round(avg_rating, 1),
                "popularity": popularity
            })
        
        return {"movies": movies_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/recommend")
async def get_recommendations(user_data: UserRatings):
    """Kullanıcı puanlarına göre film önerisi yap"""
    try:
        recommendations = recommender.recommend_for_new_user(
            user_data.ratings, 
            user_data.n_recommendations
        )
        
        return {
            "user_rating_count": len([r for r in user_data.ratings.values() if r > 0]),
            "recommendations": recommendations
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)