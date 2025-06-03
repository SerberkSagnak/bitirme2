from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
import traceback

# Verileri yükle
user_movie_matrix = pd.read_pickle('user_movie_matrix.pkl')
movies = pd.read_csv('ml-100k/u.item', sep='|', encoding='latin1',
                    names=['movie_id', 'title', 'release_date', 'video_release_date',
                           'imdb_url'] + [f'genre_{i}' for i in range(19)])

def get_popular_movies(n_movies=15):
    movie_stats = []
    for movie_id in user_movie_matrix.columns:
        ratings = user_movie_matrix[movie_id]
        rated_users = ratings[ratings > 0]
        
        if len(rated_users) >= 20:
            avg_rating = rated_users.mean()
            popularity = len(rated_users) 
            score = avg_rating * 0.6 + (popularity/100) * 0.4
            movie_stats.append((movie_id, score, avg_rating, popularity))
    
    top_movies = sorted(movie_stats, key=lambda x: x[1], reverse=True)
    return top_movies[:n_movies]

class AdaptiveRecommendationSystem:
    def __init__(self):
        self.user_movie_matrix = user_movie_matrix
        self.movies = movies
        
    def recommend_for_new_user(self, user_ratings, n_recommendations=10):
        print(f"🔍 DEBUG: Gelen user_ratings: {user_ratings}")
        print(f"🔍 DEBUG: Type: {type(user_ratings)}")
        
        rating_count = len([r for r in user_ratings.values() if r > 0])
        print(f"🔍 DEBUG: Rating count: {rating_count}")
        
        if rating_count < 5:
            method = "AŞAMA 1: Popüler filmler"
            return self._recommend_popular(user_ratings, n_recommendations), method
        else:
            method = "AŞAMA 2+: Gelişmiş öneriler"
            return self._recommend_popular(user_ratings, n_recommendations), method
    
    def _recommend_popular(self, user_ratings, n_recommendations):
        print(f"🔍 DEBUG: _recommend_popular çağrıldı")
        popular_movies = get_popular_movies(50)
        recommendations = []
        
        for movie_id, score, avg_rating, popularity in popular_movies:
            if movie_id not in user_ratings or user_ratings[movie_id] == 0:
                movie_title = self.movies[self.movies['movie_id'] == movie_id]['title'].values[0]
                recommendations.append({
                    'movie_id': movie_id,
                    'title': movie_title,
                    'score': round(score, 2),
                    'avg_rating': round(avg_rating, 1),
                    'popularity': popularity
                })
                if len(recommendations) >= n_recommendations:
                    break
        
        print(f"🔍 DEBUG: {len(recommendations)} öneri hazırlandı")
        return recommendations

# FastAPI App
app = FastAPI(title="🎬 Film Öneri Sistemi API v2 (Debug)", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

recommender = AdaptiveRecommendationSystem()

class UserRatings(BaseModel):
    ratings: Dict[int, float]
    n_recommendations: int = 10

@app.post("/recommend")
async def get_recommendations(user_data: UserRatings):
    print(f"🔍 DEBUG: Recommend endpoint'ine istek geldi")
    print(f"🔍 DEBUG: user_data: {user_data}")
    
    try:
        recommendations, method = recommender.recommend_for_new_user(
            user_data.ratings, 
            user_data.n_recommendations
        )
        
        rating_count = len([r for r in user_data.ratings.values() if r > 0])
        
        result = {
            "status": "success",
            "user_rating_count": rating_count,
            "method": method,
            "recommendations": recommendations
        }
        
        print(f"🔍 DEBUG: Başarılı sonuç döndürülüyor")
        return result
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        print(f"❌ TRACEBACK: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")

# Diğer endpoint'ler aynı...
@app.get("/")
async def root():
    return {"message": "🎬 Debug API", "status": "running"}

@app.get("/onboarding-movies")
async def get_onboarding_movies():
    try:
        popular_movies = get_popular_movies(15)
        movies_list = []
        
        for movie_id, score, avg_rating, popularity in popular_movies:
            movie_title = movies[movies['movie_id'] == movie_id]['title'].values[0]
            movies_list.append({
                "movie_id": movie_id,
                "title": movie_title,
                "avg_rating": round(avg_rating, 1),
                "popularity": popularity,
                "score": round(score, 2)
            })
        
        return {"status": "success", "count": len(movies_list), "movies": movies_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search")
async def search_movies(q: str = Query(..., description="Arama terimi")):
    try:
        search_results = movies[
            movies['title'].str.contains(q, case=False, na=False)
        ].head(20)
        
        results = []
        for _, movie in search_results.iterrows():
            movie_ratings = user_movie_matrix[movie['movie_id']]
            rated_users = movie_ratings[movie_ratings > 0]
            
            avg_rating = rated_users.mean() if len(rated_users) > 0 else 0
            popularity = len(rated_users)
            
            results.append({
                "movie_id": movie['movie_id'],
                "title": movie['title'],
                "release_date": movie['release_date'],
                "avg_rating": round(avg_rating, 1) if avg_rating > 0 else "N/A",
                "popularity": popularity,
                "imdb_url": movie['imdb_url']
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
    print("🚀 Debug API başlatılıyor...")
    uvicorn.run(app, host="0.0.0.0", port=8000)