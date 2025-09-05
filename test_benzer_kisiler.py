"""
Benzer Kişiler Sistemi Test - Unicode Safe
"""

import requests
import json

def test_benzer_kisiler():
    print("BENZER KISILER SISTEMI TEST")
    print("=" * 40)
    
    # Login
    login_response = requests.post('http://localhost:8000/login',
        json={'username': 'alice', 'password': 'test123'})
    
    if login_response.status_code != 200:
        print("Login failed!")
        return
    
    result = login_response.json()
    token = result['access_token']
    user_id = result['user']['id']
    headers = {'Authorization': f'Bearer {token}'}
    
    print(f"Login OK - User ID: {user_id}")
    
    # Test recommendations/new endpoint
    print("\nTesting recommendations/new endpoint...")
    
    rec_response = requests.get(f'http://localhost:8000/recommendations/new/{user_id}',
        headers=headers)
    
    print(f"Status code: {rec_response.status_code}")
    
    if rec_response.status_code == 200:
        try:
            data = rec_response.json()
            
            print("Response data:")
            print(f"  Status: {data.get('status', 'unknown')}")
            print(f"  Method: {data.get('method', 'unknown')}")
            
            # Message safely
            message = data.get('message', 'No message')
            if isinstance(message, str):
                # Remove problematic characters
                safe_message = message.encode('ascii', 'ignore').decode('ascii')
                print(f"  Message: {safe_message}")
            
            recommendations = data.get('recommendations', [])
            print(f"  Recommendation count: {len(recommendations)}")
            
            if 'user_rating_count' in data:
                print(f"  User ratings: {data['user_rating_count']}")
                print(f"  Required minimum: {data.get('minimum_required', 'N/A')}")
                print(f"  Quality: {data.get('recommendation_quality', 'unknown')}")
            
            # Show sample recommendations
            if recommendations:
                print("  Sample recommendations:")
                for i, rec in enumerate(recommendations[:3], 1):
                    title = rec.get('title', 'Unknown')[:40]
                    rating = rec.get('predicted_rating', 0.0)
                    rec_type = rec.get('type', 'unknown')
                    print(f"    {i}. {title} ({rating:.1f}) [{rec_type}]")
            else:
                print("  No recommendations returned")
                
        except Exception as e:
            print(f"JSON parse error: {e}")
            print(f"Raw response: {rec_response.text[:200]}")
    else:
        print(f"API Error: {rec_response.status_code}")
        print(f"Response: {rec_response.text}")
    
    print("\n" + "=" * 40)

if __name__ == "__main__":
    test_benzer_kisiler()
