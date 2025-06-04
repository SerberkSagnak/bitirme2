import numpy as np
import pandas as pd
import pickle
import sqlite3
from datetime import datetime
import logging

def create_dense_test_data():
    """Create more dense test data for better evaluation"""
    logging.info("🔧 Creating DENSE test data for better evaluation...")
    
    try:
        # Get real movie IDs from database
        conn = sqlite3.connect('movie_recommendation.db')
        movies_df = pd.read_sql_query("SELECT movie_id FROM movies LIMIT 200", conn)
        users_df = pd.read_sql_query("SELECT id FROM users LIMIT 100", conn)
        conn.close()
        
        movie_ids = movies_df['movie_id'].head(200).tolist()
        user_ids = users_df['id'].head(100).tolist()
        
        # Create MUCH MORE DENSE rating patterns
        np.random.seed(42)
        matrix_data = {}
        
        for user_id in user_ids:
            user_ratings = {}
            # Each user rates 40-80 movies (much more dense!)
            n_ratings = np.random.randint(40, 81)
            rated_movies = np.random.choice(movie_ids, n_ratings, replace=False)
            
            for movie_id in rated_movies:
                # More realistic rating distribution with clear preferences
                rating = np.random.choice([1, 2, 3, 4, 5], p=[0.05, 0.10, 0.20, 0.35, 0.30])
                user_ratings[movie_id] = rating
                
            matrix_data[user_id] = user_ratings
        
        # Convert to DataFrame
        rating_matrix = pd.DataFrame(matrix_data).T
        rating_matrix = rating_matrix.reindex(columns=movie_ids)
        
        # Calculate new sparsity
        total_cells = rating_matrix.size
        filled_cells = rating_matrix.count().sum()
        sparsity = ((total_cells - filled_cells) / total_cells) * 100
        
        print(f"📊 New Matrix Stats:")
        print(f"   Users: {len(user_ids)}")
        print(f"   Movies: {len(movie_ids)}")
        print(f"   Total Ratings: {filled_cells}")
        print(f"   Sparsity: {sparsity:.1f}% (was 79.6%)")
        
        # Save enhanced matrix
        with open('user_movie_matrix.pkl', 'wb') as f:
            pickle.dump(rating_matrix, f)
        
        logging.info(f"✅ DENSE test data created: {len(user_ids)} users, {len(movie_ids)} movies, {filled_cells} ratings")
        return True
        
    except Exception as e:
        logging.error(f"❌ Dense data creation failed: {e}")
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    create_dense_test_data()