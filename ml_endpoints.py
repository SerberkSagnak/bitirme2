# app_complete_v5_fixed.py dosyasına ekle:

from ml_service import ml_service

# 🤖 MACHINE LEARNING ENDPOINTS

@app.post("/ml/train-models")
async def train_ml_models(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ML modellerini train et (Admin only)"""
    try:
        # Admin check (basit versiyon)
        if current_user.username != "admin":  # Gerçek projede role-based auth
            raise HTTPException(status_code=403, detail="Admin yetkisi gerekli")
        
        result = ml_service.train_models_async(db)
        
        return {
            "status": "success",
            "message": "ML model training başlatıldı!",
            "details": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ml/recommendations")
async def get_ml_recommendations(
    n_recommendations: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ML bazlı kişiselleştirilmiş öneriler"""
    try:
        recommendations = ml_service.get_ml_recommendations(
            user_id=current_user.id,
            db=db,
            n_recommendations=n_recommendations
        )
        
        if not recommendations:
            return {
                "status": "info",
                "message": "ML modeli henüz hazır değil. Geleneksel öneriler kullanılıyor.",
                "recommendations": []
            }
        
        return {
            "status": "success",
            "method": "MACHINE LEARNING (Deep + Collaborative)",
            "count": len(recommendations),
            "recommendations": recommendations
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ml/model-status")
async def get_ml_model_status(
    current_user: User = Depends(get_current_user)
):
    """ML model durumu"""
    try:
        status = ml_service.get_model_status()
        
        return {
            "status": "success",
            "model_status": status
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ml/predict-rating")
async def predict_movie_rating(
    movie_id: int,
    method: str = "hybrid",  # hybrid, deep, collaborative
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Kullanıcının bir filme vereceği puanı tahmin et"""
    try:
        from ml_recommendation_engine import ml_engine
        
        movie = db.query(Movie).filter(Movie.movie_id == movie_id).first()
        if not movie:
            raise HTTPException(status_code=404, detail="Film bulunamadı")
        
        predicted_rating = ml_engine.predict_rating(
            user_id=current_user.id,
            movie_id=movie.id,
            method=method
        )
        
        return {
            "status": "success",
            "movie_id": movie_id,
            "movie_title": movie.title,
            "predicted_rating": round(predicted_rating, 2),
            "method": method,
            "confidence": min(predicted_rating / 5.0, 1.0)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Rating endpoint'ini güncelle
@app.post("/rate-movie")
async def rate_movie_with_ml_update(
    rating_data: UserRating,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Film puanlama + ML model güncelleme"""
    try:
        # Önceki rating kodu...
        movie = db.query(Movie).filter(Movie.movie_id == rating_data.movie_id).first()
        if not movie:
            raise HTTPException(status_code=404, detail="Film bulunamadı")
        
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
        
        activity = UserActivity(
            user_id=current_user.id,
            activity_type="rating",
            movie_id=movie.id,
            extra_data=json.dumps({"rating": rating_data.rating})
        )
        db.add(activity)
        
        db.commit()
        
        # 🤖 ML Model güncelleme
        ml_service.update_with_new_rating(
            user_id=current_user.id,
            movie_id=movie.id,
            rating=rating_data.rating,
            db=db
        )
        
        return {
            "status": "success",
            "message": f"'{movie.title}' filmi {rating_data.rating} ⭐ ile puanlandı!",
            "ml_updated": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))