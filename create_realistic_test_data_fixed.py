import pandas as pd
import numpy as np
import sqlite3
import pickle
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_realistic_test_user():
    """🧪 Gerçekçi test kullanıcısı oluştur - FIXED VERSION"""
    
    # Connect to database to get real movies
    try:
        conn = sqlite3.connect('movie_recommendation.db')
        movies_df = pd.read_sql_query("""
            SELECT movie_id, title, genres, avg_rating, rating_count 
            FROM movies 
            WHERE movie_id IS NOT NULL 
            ORDER BY movie_id 
            LIMIT 200
        """, conn)
        conn.close()
        
        if len(movies_df) == 0:
            logger.error("❌ No movies found in database!")
            return None
            
        logger.info(f"✅ Found {len(movies_df)} movies in database")
        
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        return None
    
    # Create test user profile
    test_user_id = 999  # Special test user ID
    movie_ids = movies_df['movie_id'].tolist()
    
    # 🎯 FIXED RATING PATTERN - More realistic preferences
    user_preferences = {
        'Action': 4.3,      # Really loves action
        'Comedy': 3.2,      # Mild comedy fan  
        'Drama': 4.5,       # Loves drama most
        'Horror': 1.8,      # Really dislikes horror
        'Romance': 2.8,     # Not a romance fan
        'Sci-Fi': 4.4,      # Loves sci-fi
        'Thriller': 4.0,    # Likes thriller
        'Adventure': 4.2,   # Likes adventure
        'Animation': 3.5,   # Neutral on animation
        'Crime': 4.1,       # Likes crime
        'Western': 3.8,     # Likes western
        'War': 3.9,         # Likes war movies
        'Fantasy': 4.0,     # Likes fantasy
        'Mystery': 3.7      # Likes mystery
    }
    
    # Generate realistic ratings with GUARANTEED high ratings
    test_ratings = {}
    rated_movies = []
    
    # Select 70-80 movies to rate
    num_ratings = np.random.randint(70, 81)
    selected_movies = np.random.choice(movie_ids, num_ratings, replace=False)
    
    guaranteed_likes = 0  # Counter for guaranteed likes
    target_likes = 20     # Target number of liked movies
    
    for i, movie_id in enumerate(selected_movies):
        movie_info = movies_df[movies_df['movie_id'] == movie_id].iloc[0]
        movie_genres = str(movie_info['genres']).split('|') if pd.notna(movie_info['genres']) else ['Unknown']
        
        # Clean genres and convert to list if it's a string representation of list
        if len(movie_genres) == 1 and movie_genres[0].startswith('['):
            # Handle string representation of list
            import ast
            try:
                movie_genres = ast.literal_eval(movie_genres[0])
            except:
                movie_genres = ['Unknown']
        
        # Calculate base rating from user preferences
        genre_scores = []
        for genre in movie_genres:
            genre = genre.strip('"').strip("'")  # Clean quotes
            if genre in user_preferences:
                genre_scores.append(user_preferences[genre])
            else:
                genre_scores.append(3.0)  # Neutral for unknown genres
        
        base_rating = np.mean(genre_scores) if genre_scores else 3.0
        
        # 🔧 FIXED: Ensure we get enough liked movies
        if guaranteed_likes < target_likes and i < len(selected_movies) * 0.7:
            # Force some high ratings for popular genres
            if any(g in ['Action', 'Drama', 'Sci-Fi', 'Thriller', 'Adventure'] 
                   for g in movie_genres):
                # Guarantee this will be a liked movie
                final_rating = np.random.uniform(4.0, 5.0)
                guaranteed_likes += 1
            else:
                # Normal rating with less randomness
                randomness = np.random.uniform(-0.3, 0.3)
                final_rating = base_rating + randomness
        else:
            # Normal rating generation
            randomness = np.random.uniform(-0.5, 0.5)
            final_rating = base_rating + randomness
        
        # Clamp to 1-5 range
        final_rating = max(1.0, min(5.0, final_rating))
        
        # Round to nearest 0.5
        final_rating = round(final_rating * 2) / 2
        
        test_ratings[movie_id] = final_rating
        rated_movies.append({
            'movie_id': movie_id,
            'title': movie_info['title'],
            'genres': movie_genres,
            'rating': final_rating,
            'is_liked': final_rating >= 4.0
        })
    
    # 🔧 ADDITIONAL FIX: If still not enough likes, force some
    liked_count = sum(1 for movie in rated_movies if movie['is_liked'])
    if liked_count < 15:  # Minimum 15 liked movies
        # Convert some 3.5 ratings to 4.0
        neutral_movies = [m for m in rated_movies if m['rating'] == 3.5]
        movies_to_boost = min(15 - liked_count, len(neutral_movies))
        
        for i in range(movies_to_boost):
            neutral_movies[i]['rating'] = 4.0
            neutral_movies[i]['is_liked'] = True
            test_ratings[neutral_movies[i]['movie_id']] = 4.0
    
    # Create comprehensive test matrix
    all_movie_ids = movie_ids[:100]  # Use first 100 movies
    test_matrix_data = {}
    
    # Add our test user
    user_ratings_series = pd.Series(index=all_movie_ids, dtype=float)
    for movie_id, rating in test_ratings.items():
        if movie_id in all_movie_ids:
            user_ratings_series[movie_id] = rating
    
    test_matrix_data[test_user_id] = user_ratings_series
    
    # Add some other realistic users for collaborative filtering
    for user_id in range(1000, 1020):  # 20 additional users
        user_ratings = pd.Series(index=all_movie_ids, dtype=float)
        
        # Each user rates 20-40 movies
        n_user_ratings = np.random.randint(20, 41)
        user_movies = np.random.choice(all_movie_ids, n_user_ratings, replace=False)
        
        for movie_id in user_movies:
            # More realistic rating distribution
            rating = np.random.choice([1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0], 
                                    p=[0.03, 0.05, 0.08, 0.12, 0.25, 0.22, 0.15, 0.08, 0.02])
            user_ratings[movie_id] = rating
        
        test_matrix_data[user_id] = user_ratings
    
    # Create DataFrame
    test_matrix = pd.DataFrame(test_matrix_data).T
    
    # Save test matrix
    with open('user_movie_matrix.pkl', 'wb') as f:
        pickle.dump(test_matrix, f)
    
    # Create ground truth for evaluation
    liked_movies = [movie for movie in rated_movies if movie['is_liked']]
    disliked_movies = [movie for movie in rated_movies if not movie['is_liked']]
    
    logger.info(f"✅ Test user {test_user_id} created:")
    logger.info(f"   📊 Total ratings: {len(rated_movies)}")
    logger.info(f"   ❤️ Liked movies (≥4.0): {len(liked_movies)}")
    logger.info(f"   👎 Disliked movies (<4.0): {len(disliked_movies)}")
    
    # Print some examples
    print("\n🎬 TEST USER RATING EXAMPLES:")
    print("="*60)
    
    if liked_movies:
        print(f"\n❤️ LIKED MOVIES (Rating ≥ 4.0): {len(liked_movies)} total")
        for movie in liked_movies[:10]:
            print(f"   ⭐ {movie['rating']:.1f} - {movie['title']} ({movie['genres']})")
    
    if disliked_movies:
        print(f"\n👎 DISLIKED MOVIES (Rating < 4.0): {len(disliked_movies)} total") 
        for movie in disliked_movies[:5]:
            print(f"   ⭐ {movie['rating']:.1f} - {movie['title']} ({movie['genres']})")
    
    return {
        'test_user_id': test_user_id,
        'all_ratings': rated_movies,
        'liked_movies': liked_movies,
        'disliked_movies': disliked_movies,
        'matrix_shape': test_matrix.shape
    }

if __name__ == "__main__":
    print("🧪 CREATING REALISTIC TEST DATA - FIXED VERSION")
    print("="*60)
    
    test_data = create_realistic_test_user()
    if test_data:
        print(f"\n✅ Test data created successfully!")
        print(f"   Matrix shape: {test_data['matrix_shape']}")
        print(f"   Test user: {test_data['test_user_id']}")
        print(f"   Liked movies: {len(test_data['liked_movies'])}")
        
        # Save test data for later use
        with open('test_user_data.pkl', 'wb') as f:
            pickle.dump(test_data, f)
        
        print(f"   💾 Test data saved to 'test_user_data.pkl'")