from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
import json
import asyncio
import logging

from enhanced_hybrid_recommender_v6 import EnhancedRecommendationAPI
from database_fixed import DatabaseManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="🚀 Enhanced Movie Recommendation System v6.0",
    description="Advanced Hybrid Recommendation System with A/B Testing & Analytics",
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

# Initialize components
db_manager = DatabaseManager()
recommendation_api = EnhancedRecommendationAPI()

# Pydantic models
class UserRegistration(BaseModel):
    username: str
    email: str
    password: str
    age: Optional[int] = None
    gender: Optional[str] = None
    favorite_genres: List[str] = []

class UserLogin(BaseModel):
    username: str
    password: str

class MovieRating(BaseModel):
    movie_id: int
    rating: float

class RecommendationRequest(BaseModel):
    algorithm: str = "hybrid"
    n_recommendations: int = 10

class ABTestRequest(BaseModel):
    test_users: List[int]
    algorithms: List[str] = ["hybrid_v6", "collaborative_filtering", "content_based"]

# 🏠 SERVE FRONTEND
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the enhanced frontend"""
    return FileResponse('index_enhanced_v6.html')

# 👤 USER AUTHENTICATION
@app.post("/register")
async def register_user(user_data: UserRegistration):
    """Enhanced user registration with preferences"""
    try:
        result = db_manager.create_user(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            age=user_data.age,
            gender=user_data.gender,
            favorite_genres=user_data.favorite_genres
        )
        
        if result:
            logger.info(f"✅ New user registered: {user_data.username}")
            return {
                "status": "success", 
                "message": "User registered successfully!",
                "user_id": result
            }
        else:
            raise HTTPException(status_code=400, detail="Registration failed")
            
    except Exception as e:
        logger.error(f"❌ Registration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/login")
async def login_user(login_data: UserLogin):
    """Enhanced user login with session management"""
    try:
        user = db_manager.authenticate_user(login_data.username, login_data.password)
        
        if user:
            # Generate session token (simplified)
            token = f"token_{user['user_id']}_{datetime.now().timestamp()}"
            
            logger.info(f"✅ User logged in: {login_data.username}")
            return {
                "status": "success",
                "message": "Login successful!",
                "access_token": token,
                "user": user
            }
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")
            
    except Exception as e:
        logger.error(f"❌ Login error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 🎯 ENHANCED RECOMMENDATIONS
@app.get("/enhanced-recommendations/{user_id}")
async def get_enhanced_recommendations(
    user_id: int, 
    n_recommendations: int = 10,
    algorithm: str = "hybrid"
):
    """
    🚀 Get Enhanced Hybrid Recommendations
    
    Algorithms:
    - hybrid: Advanced multi-algorithm hybrid
    - collaborative_filtering: CF only
    - content_based: Content-based only  
    - matrix_factorization: SVD-based
    - popularity: Popularity-based
    """
    try:
        if algorithm == "hybrid":
            recommendations = await recommendation_api.get_hybrid_recommendations(
                user_id, n_recommendations
            )
        else:
            # Initialize if needed
            await recommendation_api.initialize()
            
            # Get specific algorithm recommendations
            if algorithm == "collaborative_filtering":
                recs = recommendation_api.recommender.collaborative_filtering_recommendations(
                    user_id, n_recommendations
                )
            elif algorithm == "content_based":
                recs = recommendation_api.recommender.content_based_recommendations(
                    user_id, n_recommendations
                )
            elif algorithm == "matrix_factorization":
                recs = recommendation_api.recommender.matrix_factorization_recommendations(
                    user_id, n_recommendations
                )
            elif algorithm == "popularity":
                recs = recommendation_api.recommender.popularity_based_recommendations(
                    user_id, n_recommendations
                )
            else:
                raise HTTPException(status_code=400, detail="Unknown algorithm")
            
            # Convert to standard format
            recommendations = []
            for movie_id, score in recs:
                try:
                    movie_info = recommendation_api.recommender.movies_df[
                        recommendation_api.recommender.movies_df['movie_id'] == movie_id
                    ].iloc[0]
                    
                    recommendations.append({
                        'movie_id': int(movie_id),
                        'title': movie_info['title'],
                        'genres': movie_info['genres'],
                        'release_date': movie_info['release_date'],
                        'avg_rating': float(movie_info['avg_rating']),
                        'popularity': int(movie_info['popularity']),
                        'hybrid_score': float(score),
                        'recommendation_method': f'{algorithm.title()} Algorithm'
                    })
                except (IndexError, KeyError):
                    continue
        
        logger.info(f"✅ Generated {len(recommendations)} {algorithm} recommendations for user {user_id}")
        
        return {
            "status": "success",
            "algorithm": algorithm,
            "user_id": user_id,
            "count": len(recommendations),
            "recommendations": recommendations,
            "system_version": "Enhanced Hybrid v6.0"
        }
        
    except Exception as e:
        logger.error(f"❌ Recommendation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 🧪 A/B TESTING ENDPOINT
@app.post("/ab-test")
async def run_ab_test(request: ABTestRequest):
    """
    🧪 Run A/B Testing Between Algorithms
    """
    try:
        results = await recommendation_api.run_ab_test(request.test_users)
        
        logger.info(f"✅ A/B test completed with {len(request.test_users)} users")
        
        return {
            "status": "success",
            "test_users_count": len(request.test_users),
            "algorithms_tested": len(results),
            "results": results,
            "best_algorithm": max(results.keys(), key=lambda k: results[k]['f1_score']),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ A/B test error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 📊 ANALYTICS DASHBOARD
@app.get("/analytics")
async def get_system_analytics():
    """
    📊 Get Comprehensive System Analytics
    """
    try:
        analytics = await recommendation_api.get_performance_analytics()
        
        # Add real-time statistics
        conn = sqlite3.connect('movie_recommendation.db')
        
        # Recent activity
        recent_ratings = pd.read_sql_query("""
            SELECT COUNT(*) as count 
            FROM ratings 
            WHERE datetime(timestamp) > datetime('now', '-7 days')
        """, conn)
        
        recent_users = pd.read_sql_query("""
            SELECT COUNT(*) as count 
            FROM users 
            WHERE datetime(created_at) > datetime('now', '-7 days')
        """, conn)
        
        # Top genres
        top_genres = pd.read_sql_query("""
            SELECT genres, COUNT(*) as count
            FROM movies m
            JOIN ratings r ON m.movie_id = r.movie_id
            GROUP BY genres
            ORDER BY count DESC
            LIMIT 10
        """, conn)
        
        conn.close()
        
        analytics['real_time_stats'] = {
            'recent_ratings_7days': int(recent_ratings.iloc[0]['count']),
            'new_users_7days': int(recent_users.iloc[0]['count']),
            'top_genres': top_genres.to_dict('records'),
            'last_updated': datetime.now().isoformat()
        }
        
        return {
            "status": "success",
            "analytics": analytics,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Analytics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 🎯 RECOMMENDATION EVALUATION
@app.post("/evaluate-recommendations/{user_id}")
async def evaluate_user_recommendations(user_id: int, n_recommendations: int = 10):
    """
    🔍 Evaluate Recommendation Quality for Specific User
    """
    try:
        await recommendation_api.initialize()
        
        # Get recommendations
        recommendations = await recommendation_api.get_hybrid_recommendations(
            user_id, n_recommendations
        )
        
        # Get user's actual ratings
        user_ratings = recommendation_api.recommender.user_movie_matrix.loc[user_id].dropna().to_dict()
        
        # Evaluate
        metrics = recommendation_api.recommender.evaluate_recommendations(
            user_id, recommendations, user_ratings
        )
        
        return {
            "status": "success",
            "user_id": user_id,
            "recommendations_count": len(recommendations),
            "evaluation_metrics": {
                "precision": metrics.precision,
                "recall": metrics.recall,
                "f1_score": metrics.f1_score,
                "coverage": metrics.coverage,
                "diversity": metrics.diversity,
                "novelty": metrics.novelty,
                "execution_time": metrics.execution_time
            },
            "recommendations": recommendations[:5]  # Sample recommendations
        }
        
    except Exception as e:
        logger.error(f"❌ Evaluation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 🔄 ALGORITHM WEIGHT OPTIMIZATION
@app.post("/optimize-weights")
async def optimize_algorithm_weights(test_users: List[int]):
    """
    🎯 Optimize Algorithm Weights Dynamically
    """
    try:
        await recommendation_api.initialize()
        
        # Run optimization
        recommendation_api.recommender.optimize_algorithm_weights(test_users)
        
        return {
            "status": "success",
            "message": "Algorithm weights optimized successfully",
            "new_weights": recommendation_api.recommender.algorithm_weights,
            "test_users_count": len(test_users),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Weight optimization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 📈 REAL-TIME PERFORMANCE MONITORING
@app.get("/performance-monitor")
async def get_performance_monitor():
    """
    📈 Real-time Performance Monitoring
    """
    try:
        await recommendation_api.initialize()
        
        recent_metrics = recommendation_api.recommender.performance_metrics[-20:]
        
        if not recent_metrics:
            return {
                "status": "info",
                "message": "No recent performance data available"
            }
        
        # Calculate averages
        avg_execution_time = np.mean([m.execution_time for m in recent_metrics])
        algorithm_performance = {}
        
        for metric in recent_metrics:
            if metric.algorithm not in algorithm_performance:
                algorithm_performance[metric.algorithm] = []
            algorithm_performance[metric.algorithm].append(metric.execution_time)
        
        # Average by algorithm
        for alg in algorithm_performance:
            algorithm_performance[alg] = np.mean(algorithm_performance[alg])
        
        return {
            "status": "success",
            "monitoring_data": {
                "average_execution_time": avg_execution_time,
                "algorithm_performance": algorithm_performance,
                "recent_metrics_count": len(recent_metrics),
                "system_health": "healthy" if avg_execution_time < 1.0 else "slow"
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Performance monitoring error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Keep existing endpoints (search, rate-movie, favorites, etc.)
# ... [Previous endpoints from app_complete_v5_fixed.py] ...

# 🚀 SYSTEM HEALTH CHECK
@app.get("/health")
async def health_check():
    """System health check"""
    try:
        # Check database
        conn = sqlite3.connect('movie_recommendation.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        conn.close()
        
        # Check recommendation system
        is_initialized = recommendation_api.is_initialized
        
        return {
            "status": "healthy",
            "database": "connected",
            "users": user_count,
            "recommendation_system": "initialized" if is_initialized else "not initialized",
            "version": "Enhanced Hybrid v6.0",            
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# 🔍 SEARCH WITH ENHANCED RESULTS
@app.get("/enhanced-search")
async def enhanced_search(q: str, limit: int = 20):
    """Enhanced search with recommendation context"""
    try:
        movies = db_manager.search_movies(q, limit)
        
        # Add recommendation context
        for movie in movies:
            # Add genre popularity
            movie['genre_popularity'] = len(movie['genres'].split('|')) if movie['genres'] else 0
            
            # Add recommendation readiness
            movie['recommendation_ready'] = True
        
        return {
            "status": "success",
            "query": q,
            "count": len(movies),
            "results": movies,
            "search_type": "enhanced"
        }
        
    except Exception as e:
        logger.error(f"❌ Enhanced search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Keep all existing endpoints from previous version
# (search, rate-movie, add-to-favorites, etc.)

if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Starting Enhanced Movie Recommendation System v6.0")
    uvicorn.run(app, host="0.0.0.0", port=8000)
