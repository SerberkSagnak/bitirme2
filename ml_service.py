from typing import List, Dict
import pandas as pd
from sqlalchemy.orm import Session
from database_fixed import get_db, User, Movie, Rating
from ml_recommendation_engine import ml_engine
import threading
import time
from datetime import datetime, timedelta

class MLRecommendationService:
    def __init__(self):
        self.last_training = None
        self.training_in_progress = False
        self.auto_retrain_hours = 24  # 24 saatte bir retrain
        
    def prepare_training_data(self, db: Session) -> pd.DataFrame:
        """Database'den training verisi hazırla"""
        ratings = db.query(Rating).all()
        
        data = []
        for rating in ratings:
            data.append({
                'user_id': rating.user_id,
                'movie_id': rating.movie_id, 
                'rating': rating.rating,
                'timestamp': rating.created_at
            })
        
        return pd.DataFrame(data)
    
    def train_models_async(self, db: Session):
        """Background'da model training"""
        if self.training_in_progress:
            return {"status": "training_in_progress"}
        
        def train_thread():
            self.training_in_progress = True
            try:
                print("🚀 ML Model Training başlıyor...")
                
                # Prepare data
                ratings_df = self.prepare_training_data(db)
                
                if len(ratings_df) < 100:
                    print("❌ Yeterli rating verisi yok (min 100)")
                    return
                
                # Train Deep Learning model
                deep_history, deep_metrics = ml_engine.train_deep_model(ratings_df)
                
                # Train Collaborative Filtering
                cf_metrics = ml_engine.train_collaborative_filtering(ratings_df)
                
                # Save models
                ml_engine.save_models()
                
                self.last_training = datetime.now()
                print("✅ ML Model Training tamamlandı!")
                
            except Exception as e:
                print(f"❌ Training hatası: {e}")
            finally:
                self.training_in_progress = False
        
        # Start background thread
        thread = threading.Thread(target=train_thread)
        thread.daemon = True
        thread.start()
        
        return {"status": "training_started"}
    
    def get_ml_recommendations(self, user_id: int, db: Session, n_recommendations: int = 10) -> List[Dict]:
        """ML ile kullanıcı önerileri"""
        if not ml_engine.is_trained and not ml_engine.cf_trained:
            return []
        
        # Get all movies for recommendations
        movies = db.query(Movie).limit(1000).all()  # Limit for performance
        movie_ids = [movie.id for movie in movies]
        
        # Get ML recommendations
        ml_recs = ml_engine.get_user_recommendations(
            user_id=user_id,
            movie_catalog=movie_ids,
            n_recommendations=n_recommendations*2,  # Get more for filtering
            method='hybrid'
        )
        
        # Convert to detailed format
        detailed_recs = []
        for rec in ml_recs:
            movie = db.query(Movie).filter(Movie.id == rec['movie_id']).first()
            if movie:
                detailed_recs.append({
                    'movie_id': movie.movie_id,
                    'title': movie.title,
                    'predicted_rating': rec['predicted_rating'],
                    'ml_confidence': min(rec['predicted_rating'] / 5.0, 1.0),
                    'release_date': movie.release_date,
                    'avg_rating': movie.avg_rating,
                    'genres': movie.genres
                })
        
        return detailed_recs[:n_recommendations]
    
    def update_with_new_rating(self, user_id: int, movie_id: int, rating: float, db: Session):
        """Yeni rating ile model güncelle"""
        if ml_engine.is_trained:
            # Prepare incremental data
            new_data = pd.DataFrame([{
                'user_id': user_id,
                'movie_id': movie_id,
                'rating': rating
            }])
            
            # Incremental update
            ml_engine.update_model_incremental(new_data)
    
    def should_retrain(self) -> bool:
        """Model retrain edilmeli mi?"""
        if self.last_training is None:
            return True
        
        hours_since_training = (datetime.now() - self.last_training).total_seconds() / 3600
        return hours_since_training >= self.auto_retrain_hours
    
    def get_model_status(self) -> Dict:
        """Model durumu"""
        return {
            'deep_model_trained': ml_engine.is_trained,
            'cf_model_trained': ml_engine.cf_trained,
            'last_training': self.last_training.isoformat() if self.last_training else None,
            'training_in_progress': self.training_in_progress,
            'metrics_summary': ml_engine.get_metrics_summary(),
            'should_retrain': self.should_retrain()
        }

# Global ML Service
ml_service = MLRecommendationService()