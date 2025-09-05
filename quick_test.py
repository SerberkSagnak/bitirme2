"""
Hızlı sunucu test scripti - sunucunun çalışıp çalışmadığını kontrol eder
"""

import requests
import json

def test_server():
    base_url = "http://localhost:8000"
    
    print("="*50)
    print("SUNUCU BAGLANTI TESTI")
    print("="*50)
    
    # 1. Health check
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        print(f"[+] Ana sayfa: {response.status_code}")
    except:
        print("[x] Sunucu çalışmıyor! Lütfen önce sunucuyu başlatın:")
        print("    python run_server.py")
        return False
    
    # 2. API docs
    try:
        response = requests.get(f"{base_url}/docs", timeout=5)
        print(f"[+] API docs: {response.status_code}")
    except:
        print("[-] API docs erişilemez")
    
    # 3. Popüler filmler
    try:
        response = requests.get(f"{base_url}/popular-movies", timeout=5)
        result = response.json()
        movie_count = len(result.get("movies", []))
        print(f"[+] Popüler filmler: {movie_count} film")
    except Exception as e:
        print(f"[-] Film verisi çekilemedi: {e}")
    
    # 4. Test kayıt
    try:
        register_data = {
            "username": "quicktest",
            "email": "quicktest@test.com",
            "password": "test123"
        }
        response = requests.post(f"{base_url}/register", json=register_data, timeout=10)
        print(f"[+] Test kayıt: {response.status_code}")
        
        # Test giriş
        login_data = {
            "username": "quicktest", 
            "password": "test123"
        }
        response = requests.post(f"{base_url}/login", json=login_data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            print(f"[+] Test giriş: başarılı - User ID: {result.get('user_id')}")
        else:
            print(f"[-] Test giriş: {response.status_code}")
            
    except Exception as e:
        print(f"[-] Test kayıt/giriş hatası: {e}")
    
    print("\n[+] Sunucu çalışıyor! Test scriptini çalıştırabilirsiniz:")
    print("    python test_dynamic_deep_system.py")
    print("="*50)
    return True

if __name__ == "__main__":
    test_server()
