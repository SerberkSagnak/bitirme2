import pickle
import pandas as pd
import numpy as np

def test_trained_model():
    """Eğitilmiş modeli test et"""
    
    print("🧪 MODEL TEST EDİLİYOR")
    print("=" * 50)
    
    # 1. Modeli yükle
    print("📂 Model yükleniyor...")
    with open('trained_model.pkl', 'rb') as f:
        model_data = pickle.load(f)
    
    print("✅ Model yüklendi!")
    
    # 2. Model bilgileri
    user_item_matrix = model_data['user_item_matrix']
    predicted_ratings = model_data['predicted_ratings']
    user_ids = model_data['user_ids']
    movie_ids = model_data['movie_ids']
    
    print(f"📊 Model bilgileri:")
    print(f"  - RMSE: {model_data['rmse']:.3f}")
    print(f"  - Kullanıcı sayısı: {len(user_ids)}")
    print(f"  - Film sayısı: {len(movie_ids)}")
    
    # 3. Örnek kullanıcı için öneri
    test_user_id = user_ids[0]  # İlk kullanıcı
    user_index = user_ids.index(test_user_id)
    
    print(f"\n🎯 Kullanıcı {test_user_id} için öneriler:")
    
    # Kullanıcının gerçek puanları
    user_ratings = user_item_matrix.iloc[user_index]
    rated_movies = user_ratings[user_ratings > 0]
    
    print(f"📋 Kullanıcının puanladığı filmler: {len(rated_movies)}")
    print("İlk 5 puanlama:")
    for movie_id, rating in rated_movies.head().items():
        print(f"  Film {movie_id}: {rating} puan")
    
    # Tahmin edilen puanlar
    user_predictions = predicted_ratings[user_index]
    
    # Henüz puanlamadığı filmler için öneriler
    unrated_movies = user_ratings[user_ratings == 0]
    recommendations = []
    
    for movie_id in unrated_movies.index:
        movie_index = movie_ids.index(movie_id)
        predicted_rating = user_predictions[movie_index]
        recommendations.append({
            'movie_id': movie_id,
            'predicted_rating': predicted_rating
        })
    
    # En yüksek puanlı önerileri sırala
    recommendations.sort(key=lambda x: x['predicted_rating'], reverse=True)
    
    print(f"\n🎬 Top 10 film önerisi:")
    for i, rec in enumerate(recommendations[:10]):
        print(f"  {i+1}. Film {rec['movie_id']}: {rec['predicted_rating']:.2f} puan")
    
    return recommendations[:10]

if __name__ == "__main__":
    test_trained_model()