import pandas as pd
import numpy as np
import sqlite3
from deep_learning_recommender import DeepLearningRecommender

def main():
    print("Deep Learning Model Training Started...")

    # 1. Load Data from Database
    try:
        conn = sqlite3.connect('movielens_100k.db')
        # Ensure we only get valid ratings
        ratings_df = pd.read_sql_query("SELECT user_id, movie_id, rating FROM ratings WHERE rating IS NOT NULL", conn)
        conn.close()
        print(f"Successfully loaded {len(ratings_df)} ratings from the database.")
    except Exception as e:
        print(f"Error loading data from database: {e}")
        return

    # 2. Prepare Data
    # Convert columns to appropriate types and handle potential errors
    ratings_df['rating'] = pd.to_numeric(ratings_df['rating'], errors='coerce')
    ratings_df.dropna(subset=['rating', 'user_id', 'movie_id'], inplace=True)

    # Map user and movie IDs to continuous integer indices
    user_ids = ratings_df["user_id"].unique().tolist()
    movie_ids = ratings_df["movie_id"].unique().tolist()

    user_to_idx = {original_id: i for i, original_id in enumerate(user_ids)}
    movie_to_idx = {original_id: i for i, original_id in enumerate(movie_ids)}

    ratings_df['user_id'] = ratings_df['user_id'].map(user_to_idx)
    ratings_df['movie_id'] = ratings_df['movie_id'].map(movie_to_idx)
    
    # Ensure dtypes are correct before passing to model
    ratings_df['user_id'] = ratings_df['user_id'].astype(np.int32)
    ratings_df['movie_id'] = ratings_df['movie_id'].astype(np.int32)
    ratings_df['rating'] = ratings_df['rating'].astype(np.float32)

    num_users = len(user_to_idx)
    num_movies = len(movie_to_idx)

    print(f"Number of unique users: {num_users}")
    print(f"Number of unique movies: {num_movies}")
    print("\nData types after cleaning:")
    print(ratings_df.dtypes)
    print("\n")

    # 3. Initialize and Train the Model
    dl_recommender = DeepLearningRecommender(num_users, num_movies, embedding_size=50)
    
    print("Starting model training...")
    dl_recommender.train(ratings_df, epochs=10, batch_size=128)
    print("Model training completed.")

    # 4. Save the Trained Model
    model_path = 'dl_model.h5'
    dl_recommender.model.save(model_path)
    print(f"Trained model saved to {model_path}")
    
    # Also save the mappings
    import pickle
    with open('dl_model_mappings.pkl', 'wb') as f:
        pickle.dump({'user_to_idx': user_to_idx, 'movie_to_idx': movie_to_idx}, f)
    print("User and movie ID mappings saved to dl_model_mappings.pkl")

if __name__ == "__main__":
    main()