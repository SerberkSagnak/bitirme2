import pickle
import pandas as pd
import numpy as np
from typing import List, Dict

class RecommendationAPI:
    """Eğitilmiş modeli kullanan API servisi"""
    
    def __init__(self):
        self.model_data = None
        self.is_loaded = False
        
    def load_model(self):
        """Eğitilmiş modeli yükle"""
        try:
            with open('trained_model.pkl', 'rb') as f:
                self.model_data = pickle.load(f)
            self.is_loaded = True
            print("✅ Model API'ye yüklendi!")
            return True
        except Exception as e:
            print(f"❌ Model yükleme hatası: {e}")
            return False
    
    def get_user_recommendations(self, user_id: int, n_recommendations: int = 10) -> List[Dict]:
        """Kullanıcı için film önerileri"""
        if not self.is_loaded:
            return []
        
        user_ids = self.model_data['user_ids']
        movie_ids = self.model_data['movie_ids']
        user_item_matrix = self.model_data['user_item_matrix']
        predicted_ratings = self.model_data['predicted_ratings']
        
        # Kullanıcı var mı kontrol et
        if user_id not in user_ids:
            return []
        
        user_index = user_ids.index(user_id)
        user_ratings = user_item_matrix.iloc[user_index]
        user_predictions = predicted_ratings[user_index]
        
        # Henüz puanlamadığı filmler
        unrated_movies = user_ratings[user_ratings == 0]
        recommendations = []
        
        for movie_id in unrated_movies.index:
            movie_index = movie_ids.index(movie_id)
            predicted_rating = user_predictions[movie_index]
            
            recommendations.append({
                'movie_id': int(movie_id),
                'predicted_rating': float(predicted_rating),
                'recommendation_type': 'collaborative_filtering'
            })
        
        # Skorlara göre sırala
        recommendations.sort(key=lambda x: x['predicted_rating'], reverse=True)
        
        return recommendations[:n_recommendations]
    
    def get_model_info(self) -> Dict:
        """Model bilgilerini döndür"""
        if not self.is_loaded:
            return {}
        
        return {
            'model_type': 'NMF Collaborative Filtering',
            'rmse': float(self.model_data['rmse']),
            'n_users': len(self.model_data['user_ids']),
            'n_movies': len(self.model_data['movie_ids']),
            'n_factors': 20,
            'status': 'ready'
        }

# Test fonksiyonu
def test_api():
    """API'yi test et"""
    print("🧪 MODEL API TEST")
    print("=" * 40)
    
    # API'yi başlat
    api = RecommendationAPI()
    
    if not api.load_model():
        print("❌ Model yüklenemedi!")
        return
    
    # Model bilgileri
    info = api.get_model_info()
    print("📊 Model Bilgileri:")
    for key, value in info.items():
        print(f"  {key}: {value}")
    
    # Örnek öneriler
    test_user = 1
    recommendations = api.get_user_recommendations(test_user, 5)
    
    print(f"\n🎬 Kullanıcı {test_user} için öneriler:")
    for i, rec in enumerate(recommendations, 1):
        print(f"  {i}. Film {rec['movie_id']}: {rec['predicted_rating']:.2f}")
    
    print("\n✅ API test başarılı!")

if __name__ == "__main__":
    test_api()