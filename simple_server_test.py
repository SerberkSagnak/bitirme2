"""
Simple Server Test - Unicode Safe
"""

import requests
import json
import time

def test_system():
    print("=" * 50)
    print("SIMPLE SYSTEM TEST")
    print("=" * 50)
    
    base_url = "http://localhost:8001"
    
    # Test server status
    try:
        response = requests.get(f"{base_url}/status", timeout=3)
        print(f"[+] Server Status: {response.status_code}")
        if response.status_code == 200:
            print(f"    Status Data: {response.json()}")
    except:
        print("[x] Server not running - please start server first")
        print("    Run: python working_server.py")
        return False
    
    # Quick registration test
    print("\n[1] Testing Registration...")
    reg_data = {
        "username": f"testuser_{int(time.time())}",
        "email": "test@example.com",
        "password": "test123"
    }
    
    try:
        response = requests.post(f"{base_url}/register", json=reg_data, timeout=5)
        if response.status_code == 200:
            result = response.json()
            print("[+] Registration OK")
            user_id = result.get("user_id", 0)
        else:
            print(f"[-] Registration failed: {response.status_code}")
            user_id = 1  # Use existing user
    except:
        print("[x] Registration error - using fallback")
        user_id = 1
    
    # Login test
    print("\n[2] Testing Login...")
    try:
        response = requests.post(f"{base_url}/login", json=reg_data, timeout=5)
        if response.status_code == 200:
            result = response.json()
            token = result["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            print("[+] Login OK")
        else:
            print("[-] Login failed")
            return False
    except:
        print("[x] Login error")
        return False
    
    # Recommendations test
    print("\n[3] Testing Recommendations...")
    try:
        response = requests.get(
            f"{base_url}/dynamic-deep-recommendations",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            recommendations = result.get("recommendations", [])
            method = result.get("method", "Unknown")
            print(f"[+] Recommendations: {len(recommendations)} movies")
            print(f"    Method: {method}")
            
            # Show top 3
            for i, rec in enumerate(recommendations[:3], 1):
                title = rec.get("title", "Unknown")[:30]  # Limit length
                rating = rec.get("predicted_rating", 0.0)
                print(f"    {i}. {title} ({rating:.1f}/5.0)")
        else:
            print(f"[-] Recommendations failed: {response.status_code}")
    except:
        print("[x] Recommendations error")
    
    # Similar users test
    print("\n[4] Testing Similar Users...")
    try:
        response = requests.get(
            f"{base_url}/find-similar-users/{user_id}",
            headers=headers,
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            similar_users = result.get("similar_users", [])
            print(f"[+] Similar Users: {len(similar_users)} found")
            
            for i, user in enumerate(similar_users[:3], 1):
                uid = user.get("user_id", 0)
                score = user.get("similarity_score", 0.0)
                print(f"    {i}. User {uid}: {score:.3f}")
        else:
            print(f"[-] Similar users failed: {response.status_code}")
    except:
        print("[x] Similar users error")
    
    # Preference update test
    print("\n[5] Testing Preference Update...")
    try:
        update_data = {
            "ratings": [
                {"movie_id": 1, "rating": 5.0},
                {"movie_id": 2, "rating": 4.5}
            ]
        }
        
        response = requests.post(
            f"{base_url}/update-user-preferences",
            headers=headers,
            json=update_data,
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            count = result.get("count", 0)
            print(f"[+] Preferences Updated: {count} ratings")
        else:
            print(f"[-] Preference update failed: {response.status_code}")
    except:
        print("[x] Preference update error")
    
    print("\n" + "=" * 50)
    print("SYSTEM TEST COMPLETED!")
    print("=" * 50)
    
    return True

if __name__ == "__main__":
    test_system()
