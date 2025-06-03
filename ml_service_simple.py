from simple_ml_recommender import simple_ml
from sqlalchemy.orm import Session
from database_fixed import Rating, Movie, User
import json
from typing import List, Dict

class MLService:
    def __init__(self):
        self.is_ready = False
        
    def train_from_database(self, db: Session):
        """Database'den veri alıp ML modelini train et"""
        try:
            print("🤖 Database'den ML training başlıyor...")
            
            # Ratings verisi al
            ratings_query = db.query(Rating).all()
            ratings_data = []
            for rating in ratings_query:
                ratings_data.append({
                    "user_id": rating.user_id,
                    "movie_id": rating.movie_id,
                    "rating": rating.rating
                })
            
            # Movies verisi al  
            movies_query = db.query(Movie).all()
            movies_data = []
            for movie in movies_query:
                movies_data.append({
                    "movie_id": movie.id,  # Database internal ID
                    "title": movie.title,
                    "genres": movie.genres or '[]'
                })
            
            if len(ratings_data) < 5:
                print(f"❌ Yetersiz rating verisi: {len(ratings_data)} (minimum 5 gerekli)")
                return False
                
            # ML modelini train et
            simple_ml.prepare_data(ratings_data, movies_data)
            self.is_ready = True
            
            print(f"✅ ML Training tamamlandı!")
            print(f"📊 {len(ratings_data)} rating, {len(movies_data)} film")
            return True
            
        except Exception as e:
            print(f"❌ ML Training hatası: {e}")
            return False
    
    def get_recommendations(self, user_id: int, db: Session, n_recommendations: int = 10) -> List[Dict]:
        """Kullanıcı için ML önerileri"""
        if not self.is_ready:
            return []
            
        try:
            # ML önerilerini al
            ml_recs = simple_ml.get_user_recommendations(user_id, n_recommendations)
            
            # Movie detaylarını ekle
            detailed_recs = []
            for rec in ml_recs:
                movie = db.query(Movie).filter(Movie.id == rec['movie_id']).first()
                if movie:
                    detailed_recs.append({
                        "movie_id": movie.movie_id,  # External movie ID
                        "title": movie.title,
                        "predicted_rating": round(rec['predicted_rating'], 2),
                        "ml_confidence": round(rec['ml_confidence'], 2),
                        "release_date": movie.release_date,
                        "avg_rating": movie.avg_rating,
                        "genres": json.loads(movie.genres) if movie.genres else []
                    })
            
            return detailed_recs
            
        except Exception as e:
            print(f"❌ ML Recommendations hatası: {e}")
            return []
    
    def predict_rating(self, user_id: int, movie_internal_id: int) -> float:
        """Tek film için puan tahmini"""
        if not self.is_ready:
            return 3.5
            
        try:
            prediction = simple_ml.predict_rating(user_id, movie_internal_id)
            return round(prediction, 2)
        except:
            return 3.5
    
    def get_status(self) -> Dict:
        """ML servis durumu"""
        return {
            "ml_ready": self.is_ready,
            "model_trained": simple_ml.is_trained,
            "matrix_shape": simple_ml.user_item_matrix.shape if simple_ml.user_item_matrix is not None else None
        }

# Global ML Service
ml_service = MLService()