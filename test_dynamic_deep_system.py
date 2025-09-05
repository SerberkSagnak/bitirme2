"""
Dinamik Derin Öğrenme Öneri Sistemi Test Scripti

Bu script sisteminizi test etmek için kullanılır:
1. API'ye kayıt olup giriş yapar
2. Film puanlar
3. Benzer kullanıcıları bulur
4. Dinamik öneriler alır
5. Yeni puanlarla sistemi günceller
"""

import requests
import json
import time
import random
from datetime import datetime

class DynamicDeepSystemTester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.token = None
        self.user_id = None
        self.headers = {}
    
    def register_and_login(self, username="test_user_dynamic"):
        """Test kullanıcısı kayıt ol ve giriş yap"""
        print(f"[*] Registering user: {username}")
        
        # Kayıt ol
        register_data = {
            "username": username,
            "email": f"{username}@test.com", 
            "password": "test123",
            "age": 25,
            "gender": "M",
            "occupation": "student",
            "favorite_genres": ["Action", "Sci-Fi", "Comedy"]
        }
        
        try:
            response = requests.post(f"{self.base_url}/register", json=register_data)
            if response.status_code == 200:
                print(f"[+] Registration successful")
            else:
                print(f"[!] Registration response: {response.status_code}")
        except:
            pass
        
        # Giriş yap
        login_data = {
            "username": username,
            "password": "test123"
        }
        
        response = requests.post(f"{self.base_url}/login", json=login_data)
        if response.status_code == 200:
            result = response.json()
            self.token = result["access_token"]
            self.user_id = result["user"]["id"]  # Response format farklı
            self.headers = {"Authorization": f"Bearer {self.token}"}
            print(f"[+] Login successful - User ID: {self.user_id}")
            return True
        else:
            print(f"[x] Login failed: {response.status_code}")
            return False
    
    def rate_some_movies(self, n_ratings=10):
        """Rastgele filmler puanla"""
        print(f"[*] Rating {n_ratings} movies...")
        
        # Popüler filmleri al
        response = requests.get(f"{self.base_url}/popular-movies", headers=self.headers)
        if response.status_code != 200:
            print("[x] Could not get movies to rate")
            return []
        
        movies = response.json().get("movies", [])[:n_ratings * 2]
        
        rated_movies = []
        for i in range(min(n_ratings, len(movies))):
            movie = movies[i]
            rating = round(random.uniform(3.0, 5.0), 1)  # 3.0-5.0 arası rating
            
            rating_data = {
                "movie_id": movie["movie_id"],
                "rating": rating
            }
            
            response = requests.post(
                f"{self.base_url}/rate-movie", 
                json=rating_data,
                headers=self.headers
            )
            
            if response.status_code == 200:
                rated_movies.append({
                    "movie_id": movie["movie_id"],
                    "title": movie["title"],
                    "rating": rating
                })
                print(f"   [+] Rated '{movie['title']}': {rating}/5.0")
            else:
                print(f"   [x] Failed to rate movie {movie['movie_id']}")
            
            time.sleep(0.5)  # API rate limiting
        
        return rated_movies
    
    def test_similar_users(self):
        """Benzer kullanıcıları bul"""
        print(f"[*] Finding similar users for user {self.user_id}")
        
        response = requests.get(
            f"{self.base_url}/find-similar-users/{self.user_id}",
            headers=self.headers
        )
        
        if response.status_code == 200:
            result = response.json()
            similar_users = result.get("similar_users", [])
            
            print(f"[+] Found {len(similar_users)} similar users:")
            for user in similar_users[:5]:  # İlk 5'ini göster
                print(f"   User {user['user_id']}: {user['username']} " +
                      f"(similarity: {user['similarity_score']:.3f})")
            
            return similar_users
        else:
            print(f"[x] Similar users request failed: {response.status_code}")
            return []
    
    def test_dynamic_recommendations(self):
        """Dinamik derin öğrenme önerilerini test et"""
        print("[*] Getting dynamic deep learning recommendations...")
        
        response = requests.get(
            f"{self.base_url}/dynamic-deep-recommendations",
            params={"n_recommendations": 8, "force_update": True},
            headers=self.headers
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"[+] Algorithm: {result.get('method', 'Unknown')}")
            print(f"[+] Similar users found: {result.get('similar_users_found', 0)}")
            
            if result.get('similar_users'):
                print("[*] Top similar users:")
                for user in result['similar_users']:
                    print(f"   User {user['user_id']}: {user['similarity_score']:.3f}")
            
            recommendations = result.get("recommendations", [])
            print(f"[+] Got {len(recommendations)} recommendations:")
            
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec['title']} - Predicted: {rec['predicted_rating']:.2f}/5.0")
                if rec.get('similar_users_count'):
                    print(f"      Based on {rec['similar_users_count']} similar users")
            
            return recommendations
        else:
            print(f"[x] Dynamic recommendations failed: {response.status_code}")
            if response.status_code == 503:
                print("[!] Dynamic Deep Learning system may not be available")
            return []
    
    def test_preference_update(self):
        """Kullanıcı tercihlerini güncelle"""
        print("[*] Testing preference update with new ratings...")
        
        # Yeni rastgele puanlar
        new_ratings = [
            {"movie_id": random.randint(1, 100), "rating": 5.0},
            {"movie_id": random.randint(101, 200), "rating": 4.5},
            {"movie_id": random.randint(201, 300), "rating": 1.0}  # Kötü puan
        ]
        
        response = requests.post(
            f"{self.base_url}/update-user-preferences",
            json={"ratings": new_ratings},
            headers=self.headers
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"[+] Updated {result.get('count', 0)} ratings")
            print(f"[+] Embedding updated: {result.get('embedding_updated', False)}")
            
            return True
        else:
            print(f"[x] Preference update failed: {response.status_code}")
            return False
    
    def full_test_cycle(self):
        """Tam test döngüsü çalıştır"""
        print("=" * 60)
        print("DYNAMIC DEEP LEARNING RECOMMENDATION SYSTEM TEST")
        print("=" * 60)
        
        # 1. Kayıt ve Giriş
        if not self.register_and_login():
            print("[x] Test failed - Could not login")
            return
        
        time.sleep(1)
        
        # 2. Film puanlama
        rated_movies = self.rate_some_movies(8)
        print(f"[+] Successfully rated {len(rated_movies)} movies")
        
        time.sleep(2)  # Model güncellemesi için bekle
        
        # 3. Benzer kullanıcıları bul
        similar_users = self.test_similar_users()
        
        time.sleep(1)
        
        # 4. İlk öneriler
        print("\n" + "="*30 + " FIRST RECOMMENDATIONS " + "="*30)
        recommendations1 = self.test_dynamic_recommendations()
        
        time.sleep(2)
        
        # 5. Tercih güncelleme
        print("\n" + "="*30 + " UPDATING PREFERENCES " + "="*30)
        self.test_preference_update()
        
        time.sleep(3)  # Embedding güncellenmesi için bekle
        
        # 6. Güncellenmiş öneriler
        print("\n" + "="*30 + " UPDATED RECOMMENDATIONS " + "="*30)
        recommendations2 = self.test_dynamic_recommendations()
        
        # 7. Karşılaştırma
        print("\n" + "="*30 + " COMPARISON " + "="*30)
        print(f"Before update: {len(recommendations1)} recommendations")
        print(f"After update:  {len(recommendations2)} recommendations")
        
        if recommendations1 and recommendations2:
            print("\nRecommendation changes:")
            titles1 = {rec['title'] for rec in recommendations1}
            titles2 = {rec['title'] for rec in recommendations2}
            
            new_movies = titles2 - titles1
            removed_movies = titles1 - titles2
            
            print(f"New movies in recommendations: {len(new_movies)}")
            for title in list(new_movies)[:3]:
                print(f"   + {title}")
                
            print(f"Removed from recommendations: {len(removed_movies)}")
            for title in list(removed_movies)[:3]:
                print(f"   - {title}")
        
        print("\n" + "="*60)
        print("DYNAMIC DEEP LEARNING TEST COMPLETED!")
        print("="*60)

if __name__ == "__main__":
    tester = DynamicDeepSystemTester()
    tester.full_test_cycle()
