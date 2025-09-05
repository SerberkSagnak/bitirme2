"""
Quick MovieLens 100k Import - Unicode Safe
"""

import sqlite3
import pandas as pd
from datetime import datetime

def import_movielens_data():
    print("=== QUICK MOVIELENS IMPORT ===")
    
    conn = sqlite3.connect("movielens_100k.db")
    
    # 1. Import movies (u.item)
    print("[1] Importing movies...")
    try:
        # Read movies file
        movies = []
        with open("ml-100k/u.item", "r", encoding="latin-1") as f:
            for line in f:
                parts = line.strip().split("|")
                if len(parts) >= 5:
                    movie_id = int(parts[0])
                    title = parts[1]
                    
                    # Extract genres (last 19 columns are genre flags)
                    genre_flags = [int(x) for x in parts[5:24]]
                    genre_names = [
                        'unknown', 'Action', 'Adventure', 'Animation', 'Children', 
                        'Comedy', 'Crime', 'Documentary', 'Drama', 'Fantasy',
                        'Film-Noir', 'Horror', 'Musical', 'Mystery', 'Romance',
                        'Sci-Fi', 'Thriller', 'War', 'Western'
                    ]
                    
                    active_genres = [genre_names[i] for i, flag in enumerate(genre_flags) if flag == 1]
                    genres_str = "|".join(active_genres) if active_genres else "unknown"
                    
                    movies.append((movie_id, title, genres_str))
        
        # Insert movies
        conn.executemany("""
            INSERT OR REPLACE INTO movies (id, title, genres, avg_rating, rating_count)
            VALUES (?, ?, ?, 3.5, 10)
        """, movies)
        
        print(f"   Imported {len(movies)} movies")
        
    except Exception as e:
        print(f"   Movie import error: {e}")
    
    # 2. Import ratings (u.data)
    print("[2] Importing ratings...")
    try:
        ratings = []
        with open("ml-100k/u.data", "r") as f:
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) >= 4:
                    user_id = int(parts[0])
                    movie_id = int(parts[1])
                    rating = float(parts[2])
                    timestamp = datetime.fromtimestamp(int(parts[3]))
                    
                    ratings.append((user_id, movie_id, rating, timestamp))
        
        # Import as user interactions
        for rating in ratings:
            conn.execute("""
                INSERT OR REPLACE INTO user_interactions 
                (user_id, movie_id, interaction_type, extra_data, timestamp)
                VALUES (?, ?, 'rating', ?, ?)
            """, (
                rating[0], 
                rating[1], 
                f'{{"rating": {rating[2]}}}',
                rating[3]
            ))
        
        print(f"   Imported {len(ratings)} ratings")
        
    except Exception as e:
        print(f"   Rating import error: {e}")
    
    # 3. Import users (u.user)  
    print("[3] Importing users...")
    try:
        users = []
        with open("ml-100k/u.user", "r") as f:
            for line in f:
                parts = line.strip().split("|")
                if len(parts) >= 5:
                    user_id = int(parts[0])
                    age = int(parts[1])
                    gender = parts[2]
                    occupation = parts[3]
                    
                    username = f"user_{user_id:03d}"
                    email = f"{username}@movielens.com"
                    password = "test123"  # Default password
                    
                    from passlib.context import CryptContext
                    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
                    hashed_password = pwd_context.hash(password)
                    
                    users.append((user_id, username, email, hashed_password, age, gender))
        
        # Insert users
        conn.executemany("""
            INSERT OR REPLACE INTO app_users 
            (id, username, email, hashed_password, age, gender, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [(u[0], u[1], u[2], u[3], u[4], u[5], datetime.now()) for u in users])
        
        print(f"   Imported {len(users)} users")
        
    except Exception as e:
        print(f"   User import error: {e}")
    
    conn.commit()
    
    # Final check
    movie_count = conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
    user_count = conn.execute("SELECT COUNT(*) FROM app_users").fetchone()[0] 
    rating_count = conn.execute("SELECT COUNT(*) FROM user_interactions WHERE interaction_type = 'rating'").fetchone()[0]
    
    conn.close()
    
    print("\n=== IMPORT COMPLETE ===")
    print(f"Movies: {movie_count}")
    print(f"Users: {user_count}")
    print(f"Ratings: {rating_count}")
    
    if rating_count > 50000:
        print("\nSUCCESS! Deep Learning Dataset Ready!")
        print("Login info:")
        print("  Username: user_001 (or any user_XXX)")
        print("  Password: test123")
    else:
        print("\nPartial success - may need more data")
    
    return rating_count > 1000

if __name__ == "__main__":
    import_movielens_data()
