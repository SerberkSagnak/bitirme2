"""
Add More Training Data for Dynamic Deep Learning
"""

import sqlite3
import json
import random
from datetime import datetime, timedelta

def add_synthetic_ratings():
    print("Adding synthetic training data...")
    
    conn = sqlite3.connect("movielens_100k.db")
    
    # Get existing users and movies
    users = conn.execute("SELECT id FROM app_users LIMIT 50").fetchall()
    movies = conn.execute("SELECT id FROM movies WHERE avg_rating IS NOT NULL LIMIT 200").fetchall()
    
    user_ids = [u[0] for u in users]
    movie_ids = [m[0] for m in movies]
    
    print(f"Found {len(user_ids)} users and {len(movie_ids)} movies")
    
    # Generate realistic ratings
    ratings_added = 0
    
    for user_id in user_ids[:30]:  # Use first 30 users
        # Each user rates 10-25 movies
        n_ratings = random.randint(10, 25)
        user_movies = random.sample(movie_ids, min(n_ratings, len(movie_ids)))
        
        for movie_id in user_movies:
            # Check if rating already exists
            existing = conn.execute("""
                SELECT id FROM user_interactions 
                WHERE user_id = ? AND movie_id = ? AND interaction_type = 'rating'
            """, (user_id, movie_id)).fetchone()
            
            if not existing:
                # Generate realistic rating (bias towards higher ratings)
                if random.random() < 0.6:  # 60% chance of good rating
                    rating = random.choice([4.0, 4.5, 5.0])
                else:  # 40% chance of moderate rating
                    rating = random.choice([2.5, 3.0, 3.5])
                
                # Random timestamp (last 6 months)
                days_ago = random.randint(1, 180)
                timestamp = datetime.now() - timedelta(days=days_ago)
                
                # Insert rating
                conn.execute("""
                    INSERT INTO user_interactions 
                    (user_id, movie_id, interaction_type, extra_data, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    user_id, 
                    movie_id, 
                    'rating', 
                    json.dumps({"rating": rating}),
                    timestamp
                ))
                
                ratings_added += 1
    
    conn.commit()
    
    # Verify data
    total_ratings = conn.execute("""
        SELECT COUNT(*) FROM user_interactions 
        WHERE interaction_type = 'rating'
    """).fetchone()[0]
    
    valid_json_ratings = conn.execute("""
        SELECT COUNT(*) FROM user_interactions 
        WHERE interaction_type = 'rating' 
        AND JSON_EXTRACT(extra_data, '$.rating') IS NOT NULL
    """).fetchone()[0]
    
    conn.close()
    
    print(f"Added {ratings_added} new ratings")
    print(f"Total ratings in database: {total_ratings}")
    print(f"Valid JSON ratings: {valid_json_ratings}")
    
    return ratings_added > 0

if __name__ == "__main__":
    add_synthetic_ratings()
