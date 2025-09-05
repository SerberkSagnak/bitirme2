"""
Deep Learning Sistemi Debug Script
"""

import sqlite3
import requests
import json

def debug_user_ratings():
    print("=" * 50)
    print("DEEP LEARNING SYSTEM DEBUG")
    print("=" * 50)
    
    # Database kontrol
    conn = sqlite3.connect('movielens_100k.db')
    
    # Alice user bilgileri
    alice = conn.execute('SELECT id, username FROM app_users WHERE username = "alice"').fetchone()
    if alice:
        alice_id, username = alice
        print(f'[1] User found: {username} (ID: {alice_id})')
        
        # Rating sayısı
        rating_count = conn.execute('''
            SELECT COUNT(*) FROM user_interactions 
            WHERE user_id = ? AND interaction_type = "rating"
        ''', (alice_id,)).fetchone()[0]
        
        print(f'[2] Rating count: {rating_count}')
        
        # Sample ratings
        if rating_count > 0:
            sample_ratings = conn.execute('''
                SELECT movie_id, extra_data FROM user_interactions 
                WHERE user_id = ? AND interaction_type = "rating" 
                LIMIT 5
            ''', (alice_id,)).fetchall()
            
            print('[3] Sample ratings:')
            for i, rating in enumerate(sample_ratings, 1):
                print(f'    {i}. Movie {rating[0]}: {rating[1][:50]}...')
        else:
            print('[3] No ratings found!')
            
        # API test
        print('\n[4] Testing API...')
        try:
            # Login test
            login_response = requests.post('http://localhost:8000/login',
                json={'username': 'alice', 'password': 'test123'}, timeout=5)
            
            if login_response.status_code == 200:
                result = login_response.json()
                token = result['access_token']
                headers = {'Authorization': f'Bearer {token}'}
                print('    Login: SUCCESS')
                
                # Recommendations test
                rec_response = requests.get(f'http://localhost:8000/recommendations/new/{alice_id}',
                    headers=headers, timeout=10)
                
                print(f'    API call: {rec_response.status_code}')
                
                if rec_response.status_code == 200:
                    data = rec_response.json()
                    print(f'    Method: {data.get("method", "Unknown")}')
                    print(f'    Message: {data.get("message", "No message")}')
                    print(f'    Recommendation count: {len(data.get("recommendations", []))}')
                    
                    if 'user_rating_count' in data:
                        print(f'    User ratings: {data["user_rating_count"]}')
                        print(f'    Required minimum: {data.get("minimum_required", "N/A")}')
                    
                    if data.get("recommendations"):
                        print('    Sample recommendations:')
                        for i, rec in enumerate(data["recommendations"][:3], 1):
                            print(f'      {i}. {rec.get("title", "Unknown")}')
                else:
                    print(f'    API Error: {rec_response.text}')
            else:
                print(f'    Login failed: {login_response.status_code}')
        except Exception as e:
            print(f'    API test failed: {e}')
    else:
        print('[1] Alice user not found!')
    
    conn.close()
    
    print("\n" + "=" * 50)
    return alice_id if alice else None

if __name__ == "__main__":
    debug_user_ratings()
