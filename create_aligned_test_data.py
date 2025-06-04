import pandas as pd
import numpy as np
import sqlite3
import pickle
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_aligned_test_user():
    """🧪 Matrix'e aligned test kullanıcısı oluştur"""
    
    # Connect to database
    try:
        conn = sqlite3.connect('movie_recommendation.db')
        movies_df = pd.read_sql_query("""
            SELECT movie_id, title, genres, avg_rating, rating_count 
            FROM movies 
            WHERE movie_id IS NOT NULL 
            ORDER BY movie_id 
            LIMIT 100
        """, conn)
        conn.close()
        
        logger.info(f"✅ Found {len(movies_df)} movies in database")
        
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        return None
    
    # 🎯 Use FIRST 100 movies to ensure alignment
    movie_ids = movies_df['movie_id'].tolist()
    test_user_id = 999
    
    # User preferences
    user_preferences = {
        'Action': 4.3, 'Drama': 4.5, 'Sci-Fi': 4.4, 'Thriller': 4.0,
        'Adventure': 4.2, 'Crime': 4.1, 'Comedy': 3.2, 'Horror': 1.8,
        'Romance': 2.8, 'Animation': 3.5, 'Western': 3.8, 'War': 3.9,
        'Fantasy': 4.0, 'Mystery': 3.7
    }
    
    # 🔧 FORCE ratings on the SAME movies that will be in matrix
    test_ratings = {}
    rated_movies = []
    
    # Rate 70 movies from our 100-movie list
    selected_indices = np.random.choice(len(movie_ids), 70, replace=False)
    
    target_likes = 20
    guaranteed_likes = 0
    
    for i, idx in enumerate(selected_indices):
        movie_id = movie_ids[idx]
        movie_info = movies_df.iloc[idx]
        
        # Parse genres
        genres_str = str(movie_info['genres'])
        if genres_str.startswith('['):
            import ast
            try:
                movie_genres = ast.literal_eval(genres_str)
            except:
                movie_genres = genres_str.split('|')
        else:
            movie_genres = genres_str.split('|')
        
        # Clean genres
        movie_genres = [g.strip('"').strip("'").strip() for g in movie_genres]
        
        # Calculate rating
        genre_scores = [user_preferences.get(g, 3.0) for g in movie_genres]
        base_rating = np.mean(genre_scores)
        
        # 🔧 GUARANTEE we get liked movies in matrix
        if guaranteed_likes < target_likes and i < 50:
            if any(g in ['Action', 'Drama', 'Sci-Fi', 'Thriller', 'Adventure', 'Crime'] 
                   for g in movie_genres):
                final_rating = np.random.uniform(4.0, 5.0)
                guaranteed_likes += 1
            else:
                final_rating = base_rating + np.random.uniform(-0.3, 0.3)
        else:
            final_rating = base_rating + np.random.uniform(-0.5, 0.5)
        
        # Clamp and round
        final_rating = max(1.0, min(5.0, final_rating))
        final_rating = round(final_rating * 2) / 2
        
        test_ratings[movie_id] = final_rating
        rated_movies.append({
            'movie_id': movie_id,
            'title': movie_info['title'],
            'genres': movie_genres,
            'rating': final_rating,
            'is_liked': final_rating >= 4.0
        })
    
    # Create matrix with EXACT same movie IDs
    test_matrix_data = {}
    
    # Test user ratings
    user_ratings_series = pd.Series(index=movie_ids, dtype=float)
    for movie_id, rating in test_ratings.items():
        user_ratings_series[movie_id] = rating
    test_matrix_data[test_user_id] = user_ratings_series
    
    # Add 20 other users
    for user_id in range(1000, 1020):
        user_ratings = pd.Series(index=movie_ids, dtype=float)
        
        # Each user rates 25-40 movies
        n_ratings = np.random.randint(25, 41)
        user_movie_ids = np.random.choice(movie_ids, n_ratings, replace=False)
        
        for movie_id in user_movie_ids:
            rating = np.random.choice([1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0], 
                                    p=[0.03, 0.05, 0.08, 0.12, 0.25, 0.22, 0.15, 0.08, 0.02])
            user_ratings[movie_id] = rating
        
        test_matrix_data[user_id] = user_ratings
    
    # Create aligned DataFrame
    test_matrix = pd.DataFrame(test_matrix_data).T
    
    # Save matrix
    with open('user_movie_matrix.pkl', 'wb') as f:
        pickle.dump(test_matrix, f)
    
    # Process results
    liked_movies = [movie for movie in rated_movies if movie['is_liked']]
    disliked_movies = [movie for movie in rated_movies if not movie['is_liked']]
    
    logger.info(f"✅ ALIGNED Test user {test_user_id} created:")
    logger.info(f"   📊 Total ratings: {len(rated_movies)}")
    logger.info(f"   ❤️ Liked movies (≥4.0): {len(liked_movies)}")
    logger.info(f"   👎 Disliked movies (<4.0): {len(disliked_movies)}")
    logger.info(f"   🎯 Matrix shape: {test_matrix.shape}")
    
    # Verify alignment
    liked_movie_ids = [m['movie_id'] for m in liked_movies]
    matrix_movie_ids = set(test_matrix.columns)
    overlap = set(liked_movie_ids).intersection(matrix_movie_ids)
    
    print(f"\n🔍 ALIGNMENT CHECK:")
    print(f"Matrix movie IDs: {min(matrix_movie_ids)} - {max(matrix_movie_ids)}")
    print(f"Liked movie IDs: {min(liked_movie_ids)} - {max(liked_movie_ids)}")
    print(f"✅ ALL {len(overlap)} liked movies are in matrix!")
    
    # Show examples
    print(f"\n❤️ LIKED MOVIES IN MATRIX: {len(liked_movies)} total")
    for movie in liked_movies[:8]:
        print(f"   ⭐ {movie['rating']:.1f} - ID:{movie['movie_id']} - {movie['title']}")
    
    # Save test data
    test_data = {
        'test_user_id': test_user_id,
        'all_ratings': rated_movies,
        'liked_movies': liked_movies,
        'disliked_movies': disliked_movies,
        'matrix_shape': test_matrix.shape
    }
    
    with open('test_user_data.pkl', 'wb') as f:
        pickle.dump(test_data, f)
    
    return test_data

if __name__ == "__main__":
    print("🎯 CREATING ALIGNED TEST DATA")
    print("="*50)
    
    test_data = create_aligned_test_user()
    if test_data:
        print(f"\n✅ ALIGNED test data created!")
        print(f"💾 Files saved: 'user_movie_matrix.pkl', 'test_user_data.pkl'")