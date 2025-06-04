import pandas as pd
import numpy as np
import pickle
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def simple_collaborative_filtering(user_id, user_movie_matrix, n_recommendations=10):
    """Simple collaborative filtering for testing"""
    try:
        if user_id not in user_movie_matrix.index:
            return []
        
        user_ratings = user_movie_matrix.loc[user_id]
        user_mean = user_ratings.mean()
        
        # Find similar users
        correlations = {}
        for other_user in user_movie_matrix.index:
            if other_user != user_id:
                other_ratings = user_movie_matrix.loc[other_user]
                common_movies = user_ratings.dropna().index.intersection(other_ratings.dropna().index)
                
                if len(common_movies) >= 3:
                    corr = user_ratings[common_movies].corr(other_ratings[common_movies])
                    if not pd.isna(corr) and corr > 0.1:
                        correlations[other_user] = corr
        
        # Generate recommendations
        recommendations = {}
        for movie_id in user_movie_matrix.columns:
            if pd.isna(user_ratings[movie_id]):  # Unrated movie
                weighted_sum = 0
                correlation_sum = 0
                
                for similar_user, correlation in correlations.items():
                    similar_rating = user_movie_matrix.loc[similar_user, movie_id]
                    if not pd.isna(similar_rating):
                        weighted_sum += correlation * similar_rating
                        correlation_sum += abs(correlation)
                
                if correlation_sum > 0:
                    predicted_rating = weighted_sum / correlation_sum
                    recommendations[movie_id] = predicted_rating
        
        # Sort and return
        sorted_recs = sorted(recommendations.items(), key=lambda x: x[1], reverse=True)
        return sorted_recs[:n_recommendations]
        
    except Exception as e:
        logger.error(f"CF error: {e}")
        return []

def popularity_based_recommendations(user_id, user_movie_matrix, n_recommendations=10):
    """Simple popularity-based recommendations"""
    try:
        # Calculate movie popularity (average rating * rating count)
        movie_stats = {}
        
        for movie_id in user_movie_matrix.columns:
            ratings = user_movie_matrix[movie_id].dropna()
            if len(ratings) >= 3:  # Minimum 3 ratings
                avg_rating = ratings.mean()
                rating_count = len(ratings)
                popularity_score = avg_rating * (rating_count / 10)  # Normalized
                movie_stats[movie_id] = popularity_score
        
        # Filter out already rated movies
        user_ratings = user_movie_matrix.loc[user_id]
        unrated_movies = {mid: score for mid, score in movie_stats.items() 
                         if pd.isna(user_ratings[mid])}
        
        # Sort and return
        sorted_recs = sorted(unrated_movies.items(), key=lambda x: x[1], reverse=True)
        return sorted_recs[:n_recommendations]
        
    except Exception as e:
        logger.error(f"Popularity error: {e}")
        return []

def test_recommendations():
    """Test recommendations with our realistic data"""
    try:
        # Load test data
        with open('test_user_data.pkl', 'rb') as f:
            test_data = pickle.load(f)
        
        with open('user_movie_matrix.pkl', 'rb') as f:
            user_movie_matrix = pickle.load(f)
        
        test_user_id = test_data['test_user_id']
        liked_movies = test_data['liked_movies']
        liked_movie_ids = [m['movie_id'] for m in liked_movies]
        
        print(f"🎯 Testing recommendations for user {test_user_id}")
        print("="*60)
        print(f"Known liked movies: {len(liked_movies)}")
        print(f"Matrix shape: {user_movie_matrix.shape}")
        
        # Test different algorithms
        algorithms = {
            'Collaborative Filtering': simple_collaborative_filtering,
            'Popularity Based': popularity_based_recommendations
        }
        
        results = {}
        
        for algo_name, algo_func in algorithms.items():
            print(f"\n🔬 {algo_name.upper()}")
            print("-" * 40)
            
            recs = algo_func(test_user_id, user_movie_matrix, 15)
            
            if not recs:
                print("❌ No recommendations generated!")
                results[algo_name] = {'precision': 0, 'recall': 0, 'f1': 0, 'hits': 0}
                continue
            
            # Show top 10
            hits = 0
            print("Top 10 Recommendations:")
            for i, (movie_id, score) in enumerate(recs[:10]):
                is_hit = movie_id in liked_movie_ids
                if is_hit:
                    hits += 1
                    status = "✅ HIT!"
                else:
                    status = "❓ NEW"
                
                print(f"{i+1:2d}. Movie {movie_id} | Score: {score:.3f} | {status}")
            
            # Calculate metrics
            precision = hits / min(10, len(recs))
            recall = hits / len(liked_movies) if len(liked_movies) > 0 else 0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            
            results[algo_name] = {
                'precision': precision,
                'recall': recall, 
                'f1': f1,
                'hits': hits,
                'total_recs': len(recs)
            }
            
            print(f"\n📊 Metrics:")
            print(f"   Hits: {hits}/10")
            print(f"   Precision@10: {precision:.3f}")
            print(f"   Recall: {recall:.3f}")
            print(f"   F1-Score: {f1:.3f}")
        
        # Summary
        print(f"\n📊 ALGORITHM COMPARISON SUMMARY")
        print("="*50)
        for algo_name, metrics in results.items():
            print(f"{algo_name:20} | P: {metrics['precision']:.3f} | R: {metrics['recall']:.3f} | F1: {metrics['f1']:.3f}")
        
        # Show some liked movies for reference
        print(f"\n❤️ REFERENCE: User's Known Liked Movies (sample)")
        print("-" * 50)
        for movie in liked_movies[:10]:
            print(f"⭐ {movie['rating']:.1f} - ID: {movie['movie_id']} - {movie['title']}")
            
    except FileNotFoundError as e:
        print(f"❌ File not found: {e}")
        print("Please run create_realistic_test_data_fixed.py first!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🧪 SIMPLE RECOMMENDATION SYSTEM TEST")
    print("="*50)
    test_recommendations()