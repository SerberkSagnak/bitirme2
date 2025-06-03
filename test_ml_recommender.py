from simple_ml_recommender import simple_ml
import json

def test_simple_ml():
    print("🧪 Simple ML Recommender Test Başlıyor...")
    
    # Test verisi oluştur
    test_ratings = [
        {"user_id": 1, "movie_id": 101, "rating": 5.0},
        {"user_id": 1, "movie_id": 102, "rating": 4.0},
        {"user_id": 1, "movie_id": 103, "rating": 3.0},
        {"user_id": 2, "movie_id": 101, "rating": 4.0},
        {"user_id": 2, "movie_id": 102, "rating": 5.0},
        {"user_id": 2, "movie_id": 104, "rating": 4.5},
        {"user_id": 3, "movie_id": 103, "rating": 2.0},
        {"user_id": 3, "movie_id": 104, "rating": 4.0},
        {"user_id": 3, "movie_id": 105, "rating": 5.0},
    ]
    
    test_movies = [
        {"movie_id": 101, "title": "Star Wars", "genres": '["Action", "Adventure", "Sci-Fi"]'},
        {"movie_id": 102, "title": "The Matrix", "genres": '["Action", "Sci-Fi"]'},
        {"movie_id": 103, "title": "Titanic", "genres": '["Drama", "Romance"]'},
        {"movie_id": 104, "title": "Avatar", "genres": '["Action", "Adventure", "Sci-Fi"]'},
        {"movie_id": 105, "title": "Inception", "genres": '["Action", "Sci-Fi", "Thriller"]'},
    ]
    
    print("📊 Test verisi hazırlandı:")
    print(f"   - {len(test_ratings)} rating")
    print(f"   - {len(test_movies)} film")
    
    # ML modelini train et
    print("\n🤖 Model eğitiliyor...")
    simple_ml.prepare_data(test_ratings, test_movies)
    
    # Test 1: User 1 için öneriler
    print("\n🎯 Test 1: User 1 için öneriler")
    recommendations = simple_ml.get_user_recommendations(user_id=1, n_recommendations=3)
    print(f"   Bulunan öneri sayısı: {len(recommendations)}")
    for rec in recommendations:
        print(f"   - Movie {rec['movie_id']}: {rec['predicted_rating']:.2f} ⭐ (Güven: {rec['ml_confidence']:.2f})")
    
    # Test 2: Yeni kullanıcı için öneriler
    print("\n🎯 Test 2: Yeni kullanıcı (ID: 999) için öneriler")
    new_user_recs = simple_ml.get_user_recommendations(user_id=999, n_recommendations=3)
    print(f"   Bulunan öneri sayısı: {len(new_user_recs)}")
    for rec in new_user_recs:
        print(f"   - Movie {rec['movie_id']}: {rec['predicted_rating']:.2f} ⭐")
    
    # Test 3: Puan tahmini
    print("\n🎯 Test 3: User 1'in Movie 104'e vereceği puan tahmini")
    predicted_rating = simple_ml.predict_rating(user_id=1, movie_id=104)
    print(f"   Tahmin edilen puan: {predicted_rating:.2f} ⭐")
    
    # Test 4: Model durumu
    print("\n📊 Model Durumu:")
    print(f"   - Eğitildi mi: {simple_ml.is_trained}")
    print(f"   - User-Item Matrix boyutu: {simple_ml.user_item_matrix.shape if simple_ml.user_item_matrix is not None else 'None'}")
    
    print("\n✅ Test tamamlandı!")

if __name__ == "__main__":
    test_simple_ml()