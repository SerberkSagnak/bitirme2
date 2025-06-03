import requests
import json

# Test 1: Onboarding filmlerini al
print("🎬 Onboarding filmlerini alıyorum...")
response = requests.get("http://localhost:8000/onboarding-movies")
onboarding_data = response.json()

print(f"✅ {onboarding_data['count']} film alındı")
print("İlk 3 film:")
for i, movie in enumerate(onboarding_data['movies'][:3]):
    print(f"{i+1}. {movie['title']} (⭐{movie['avg_rating']})")

print("\n" + "="*50)

# Test 2: Yeni kullanıcı için öneri
print("🤖 Yeni kullanıcı için öneri alıyorum...")
user_ratings = {
    "ratings": {
        1: 5.0,    # Toy Story'ye 5 puan
        50: 4.0    # Star Wars'a 4 puan
    },
    "n_recommendations": 5
}

response = requests.post(
    "http://localhost:8000/recommend",
    json=user_ratings
)

recommendation_data = response.json()

print(f"✅ Kullanıcı {recommendation_data['user_rating_count']} film puanlamış")
print(f"📊 Method: {recommendation_data['method']}")
print("\nÖneriler:")
for i, rec in enumerate(recommendation_data['recommendations'], 1):
    print(f"{i}. {rec['title']} (Skor: {rec['score']})")