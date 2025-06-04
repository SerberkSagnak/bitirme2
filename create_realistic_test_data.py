import pandas as pd
import numpy as np
import sqlite3
import pickle
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_realistic_test_user():
    """🧪 Gerçekçi test kullanıcısı oluştur"""
    
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
    
    # 🎯 REALISTIC RATING PATTERN
    # Test kullanıcısı farklı türlerde farklı tercihler yapacak
    
    # User preferences by genre
    user_preferences = {
        'Action': 4.2,      # Loves action movies
        'Comedy': 3.8,      # Likes comedy
        'Drama': 4.5,       # Loves drama
        'Horror': 2.0,      # Dislikes horror
        'Romance': 3.5,     # Neutral on romance
        'Sci-Fi': 4.0,      # Likes sci-fi
        'Thriller': 3.9,    # Likes thriller
        'Adventure': 4.1,   # Likes adventure
        'Animation': 3.7,   # Likes animation
        'Crime': 4.0        # Likes crime
    }
    
    # Generate realistic ratings
    test_ratings = {}
    rated_movies = []
    
    # Select 60-80 movies to rate (realistic number)
    num_ratings = np.random.randint(60, 81)
    selected_movies = np.random.choice(movie_ids, num_ratings, replace=False)
    
    for movie_id in selected_movies:
        movie_info = movies_df[movies_df['movie_id'] == movie_id].iloc[0]
        movie_genres = str(movie_info['genres']).split('|') if pd.notna(movie_info['genres']) else ['Unknown']
        
        # Calculate base rating from user preferences
        genre_scores = []
        for genre in movie_genres:
            if genre in user_preferences:
                genre_scores.append(user_preferences[genre])
            else:
                genre_scores.append(3.0)  # Neutral for unknown genres
        
        base_rating = np.mean(genre_scores)
        
        # Add some randomness (±0.5)
        final_rating = base_rating + np.random.uniform(-0.5, 0.5)
        
        # Clamp to 1-5 range
        final_rating = max(1.0, min(5.0, final_rating))
        
        # Round to nearest 0.5
        final_rating = round(final_rating * 2) / 2
        
        test_ratings[movie_id] = final_rating
        rated_movies.append({
            'movie_id': movie_id,
            'title': movie_info['title'],
            'genres': movie_info['genres'],
            'rating': final_rating,
            'is_liked': final_rating >= 4.0
        })
    
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
            # Random but realistic rating
            rating = np.random.choice([1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0], 
                                    p=[0.05, 0.05, 0.1, 0.1, 0.2, 0.2, 0.15, 0.1, 0.05])
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
    
    print("\n❤️ LIKED MOVIES (Rating ≥ 4.0):")
    for movie in liked_movies[:10]:
        print(f"   ⭐ {movie['rating']:.1f} - {movie['title']} ({movie['genres']})")
    
    print(f"\n👎 DISLIKED MOVIES (Rating < 4.0):")
    for movie in disliked_movies[:5]:
        print(f"   ⭐ {movie['rating']:.1f} - {movie['title']} ({movie['genres']})")
    
    return {
        'test_user_id': test_user_id,
        'all_ratings': rated_movies,
        'liked_movies': liked_movies,
        'disliked_movies': disliked_movies,
        'matrix_shape': test_matrix.shape
    }

def test_with_realistic_data():
    """🧪 Gerçekçi test verisiyle sistem testi"""
    
    # Create realistic test data
    test_data = create_realistic_test_user()
    if not test_data:
        return
    
    test_user_id = test_data['test_user_id']
    liked_movies = test_data['liked_movies']
    
    print(f"\n🎯 Testing recommendations for user {test_user_id}")
    print("="*60)
    
    # Import and test our recommendation system
    try:
        from enhanced_hybrid_recommender_v6_fixed import EnhancedHybridRecommender
        
        # Initialize system
        recommender = EnhancedHybridRecommender()
        if not recommender.initialize_system():
            logger.error("❌ System initialization failed!")
            return
        
        # Get recommendations
        recommendations = recommender.hybrid_recommendations(test_user_id, 20)
        
        if not recommendations:
            logger.error("❌ No recommendations generated!")
            return
        
        print(f"\n🎯 TOP 10 RECOMMENDATIONS:")
        print("-" * 40)
        
        # Show recommendations with known preferences
        liked_movie_ids = [m['movie_id'] for m in liked_movies]
        
        hit_count = 0
        for i, rec in enumerate(recommendations[:10]):
            movie_id = rec['movie_id']
            is_known_liked = movie_id in liked_movie_ids
            
            if is_known_liked:
                hit_count += 1
                status = "✅ KNOWN LIKED"
            else:
                status = "❓ NEW"
            
            print(f"{i+1:2d}. {rec['title']}")
            print(f"    📊 Score: {rec['hybrid_score']:.3f} | {status}")
            print(f"    🎭 {rec['genres_str']}")
            print()
        
        # Calculate basic metrics
        precision = hit_count / 10 if len(recommendations) >= 10 else 0
        recall = hit_count / len(liked_movies) if len(liked_movies) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        print(f"\n📊 EVALUATION RESULTS:")
        print(f"   Hits in Top-10: {hit_count}/10")
        print(f"   Precision@10: {precision:.3f}")
        print(f"   Recall: {recall:.3f}")
        print(f"   F1-Score: {f1:.3f}")
        
        # Test different algorithms individually
        print(f"\n🔬 ALGORITHM COMPARISON:")
        print("-" * 40)
        
        algorithms = ['collaborative_filtering', 'content_based', 'popularity_based']
        
        for algo in algorithms:
            try:
                if algo == 'collaborative_filtering':
                    algo_recs = recommender.collaborative_filtering_recommendations(test_user_id, 10)
                elif algo == 'content_based':
                    algo_recs = recommender.content_based_recommendations(test_user_id, 10)
                elif algo == 'popularity_based':
                    algo_recs = recommender.popularity_based_recommendations(test_user_id, 10)
                
                # Count hits for this algorithm
                algo_hits = 0
                for movie_id, _ in algo_recs:
                    if movie_id in liked_movie_ids:
                        algo_hits += 1
                
                algo_precision = algo_hits / len(algo_recs) if algo_recs else 0
                
                print(f"   {algo.replace('_', ' ').title()}: {algo_hits}/{len(algo_recs)} hits (P={algo_precision:.3f})")
                
            except Exception as e:
                print(f"   {algo}: Error - {e}")
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.info("Please make sure enhanced_hybrid_recommender_v6_fixed.py exists")

if __name__ == "__main__":
    print("🧪 CREATING REALISTIC TEST DATA")
    print("="*50)
    
    test_with_realistic_data()
    
    print("\n✅ REALISTIC TEST COMPLETED!")