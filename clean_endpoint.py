# Temiz Deep Learning Endpoint

@app.get("/recommendations/new/{user_id}")
async def get_pure_deep_learning_recommendations(
    user_id: int,
    n_recommendations: int = 10,
    current_user: dict = Depends(get_current_user)):
    """🧠 PURE DEEP LEARNING RECOMMENDATION SYSTEM"""
    
    if not main_deep_learning_system:
        raise HTTPException(status_code=503, detail="Deep Learning System not available")
    
    try:
        logger.info(f"[🧠] Pure Deep Learning - User {user_id}")
        
        # QUALITY CHECK
        conn = get_simple_db()
        user_ratings = conn.execute("""
            SELECT ui.movie_id, 
                   JSON_EXTRACT(ui.extra_data, '$.rating') as rating,
                   m.genres
            FROM user_interactions ui
            JOIN movies m ON ui.movie_id = m.id  
            WHERE ui.user_id = ? 
            AND ui.interaction_type = 'rating'
            AND JSON_EXTRACT(ui.extra_data, '$.rating') IS NOT NULL
        """, (user_id,)).fetchall()
        conn.close()
        
        rating_count = len(user_ratings)
        
        # Genre diversity
        all_genres = set()
        for rating in user_ratings:
            if rating[2]:
                all_genres.update(rating[2].split('|'))
        
        genre_count = len(all_genres)
        logger.info(f"[📊] Quality: {rating_count} ratings, {genre_count} genres")
        
        # QUALITY GATES
        if rating_count < 10:
            return {
                "status": "insufficient_data",
                "message": f"🎬 {10-rating_count} DAHA FİLM PUANLAYIN!",
                "user_rating_count": rating_count,
                "minimum_required": 10,
                "recommendations": []
            }
        
        if genre_count < 3:
            return {
                "status": "insufficient_diversity",
                "message": f"🎭 {3-genre_count} FARKLI TÜR PUANLAYIN!",
                "current_genres": genre_count,
                "rated_genres": list(all_genres),
                "recommendations": []
            }
        
        # REAL-TIME NEURAL TRAINING
        logger.info("[⚡] Real-time neural training...")
        training_success = main_deep_learning_system.train_model()
        
        if not training_success:
            raise HTTPException(status_code=500, detail="Neural training failed")
        
        # FIND SIMILAR USERS
        similar_users = main_deep_learning_system.find_similar_users(user_id)
        logger.info(f"[👥] Found {len(similar_users)} similar users")
        
        if not similar_users:
            raise HTTPException(status_code=404, detail="No similar users found")
        
        # GENERATE RECOMMENDATIONS
        recommendations = main_deep_learning_system.get_recommendations(user_id, n_recommendations)
        logger.info(f"[🎬] Generated {len(recommendations)} recommendations")
        
        if not recommendations:
            raise HTTPException(status_code=404, detail="No recommendations generated")
        
        # SUCCESS
        return {
            "status": "success",
            "message": f"🧠 NEURAL CF - {rating_count} rating, {genre_count} tür → {len(similar_users)} benzer → {len(recommendations)} film",
            "method": "Pure Deep Learning - Real-Time Neural CF",
            "algorithm": "neural_collaborative_filtering_128d",
            "user_rating_count": rating_count,
            "user_genre_count": genre_count,
            "rated_genres": list(all_genres)[:5],
            "similar_users_found": len(similar_users),
            "similar_users": [
                {"user_id": u["user_id"], "similarity": u["similarity_score"]} 
                for u in similar_users[:5]
            ],
            "embedding_dimension": 128,
            "recommendations": recommendations,
            "quality": "pure_deep_learning"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[🚨] Deep Learning error: {e}")
        raise HTTPException(status_code=500, detail=f"Deep Learning failed: {str(e)}")
