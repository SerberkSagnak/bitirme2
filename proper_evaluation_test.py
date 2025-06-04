import pandas as pd
import numpy as np
import pickle
import logging
from sklearn.model_selection import train_test_split

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_train_test_split():
    """🎯 Proper train/test split for evaluation"""
    
    # Load aligned test data
    with open('test_user_data.pkl', 'rb') as f:
        test_data = pickle.load(f)
    
    with open('user_movie_matrix.pkl', 'rb') as f:
        full_matrix = pickle.load(f)
    
    test_user_id = test_data['test_user_id']
    liked_movies = test_data['liked_movies']
    
    print("🎯 CREATING PROPER TRAIN/TEST SPLIT")
    print("="*50)
    
    # Get user's ratings
    user_ratings = full_matrix.loc[test_user_id].dropna()
    liked_movie_ids = [m['movie_id'] for m in liked_movies]
    
    print(f"User {test_user_id} total ratings: {len(user_ratings)}")
    print(f"User liked movies: {len(liked_movies)}")
    
    # 🎯 SPLIT: Hide 50% of liked movies for testing
    train_liked, test_liked = train_test_split(
        liked_movie_ids, 
        test_size=0.5, 
        random_state=42
    )
    
    print(f"Train liked movies: {len(train_liked)}")
    print(f"Test liked movies (hidden): {len(test_liked)}")
    
    # Create train matrix (hide test liked movies)
    train_matrix = full_matrix.copy()
    
    # Hide test movies from user's ratings
    for movie_id in test_liked:
        train_matrix.loc[test_user_id, movie_id] = np.nan
    
    # Show what we're doing
    print(f"\n🎬 EXAMPLES:")
    print("Train Set (visible to system):")
    for movie_id in train_liked[:5]:
        movie_info = next(m for m in liked_movies if m['movie_id'] == movie_id)
        print(f"   ⭐ {movie_info['rating']:.1f} - ID:{movie_id} - {movie_info['title']}")
    
    print("\nTest Set (hidden from system):")
    for movie_id in test_liked[:5]:
        movie_info = next(m for m in liked_movies if m['movie_id'] == movie_id)
        print(f"   🎯 {movie_info['rating']:.1f} - ID:{movie_id} - {movie_info['title']}")
    
    # Save splits
    evaluation_data = {
        'train_matrix': train_matrix,
        'test_user_id': test_user_id,
        'train_liked': train_liked,
        'test_liked': test_liked,
        'all_liked_movies': liked_movies
    }
    
    with open('evaluation_data.pkl', 'wb') as f:
        pickle.dump(evaluation_data, f)
    
    return evaluation_data

def evaluate_recommendations_properly():
    """🧪 Proper recommendation evaluation"""
    
    # Load evaluation data
    with open('evaluation_data.pkl', 'rb') as f:
        eval_data = pickle.load(f)
    
    train_matrix = eval_data['train_matrix']
    test_user_id = eval_data['test_user_id']
    test_liked = eval_data['test_liked']
    
    print(f"\n🧪 PROPER EVALUATION")
    print("="*50)
    print(f"Hidden movies to find: {len(test_liked)}")
    
    # Collaborative Filtering on TRAIN data
    def collaborative_filtering_train(user_id, matrix, n_recs=20):
        """CF using only training data"""
        try:
            if user_id not in matrix.index:
                return []
            
            user_ratings = matrix.loc[user_id]
            
            # Find similar users based on train data
            correlations = {}
            for other_user in matrix.index:
                if other_user != user_id:
                    other_ratings = matrix.loc[other_user]
                    common_movies = user_ratings.dropna().index.intersection(other_ratings.dropna().index)
                    
                    if len(common_movies) >= 3:
                        corr = user_ratings[common_movies].corr(other_ratings[common_movies])
                        if not pd.isna(corr) and corr > 0.1:
                            correlations[other_user] = corr
            
            # Generate recommendations for unrated movies
            recommendations = {}
            for movie_id in matrix.columns:
                if pd.isna(user_ratings[movie_id]):  # Unrated in TRAIN
                    weighted_sum = 0
                    correlation_sum = 0
                    
                    for similar_user, correlation in correlations.items():
                        similar_rating = matrix.loc[similar_user, movie_id]
                        if not pd.isna(similar_rating):
                            weighted_sum += correlation * similar_rating
                            correlation_sum += abs(correlation)
                    
                    if correlation_sum > 0:
                        predicted_rating = weighted_sum / correlation_sum
                        recommendations[movie_id] = predicted_rating
            
            # Sort recommendations
            sorted_recs = sorted(recommendations.items(), key=lambda x: x[1], reverse=True)
            return sorted_recs[:n_recs]
            
        except Exception as e:
            logger.error(f"CF error: {e}")
            return []
    
    # Get recommendations
    cf_recs = collaborative_filtering_train(test_user_id, train_matrix, 30)
    
    if not cf_recs:
        print("❌ No recommendations generated!")
        return
    
    # Evaluate: How many hidden liked movies are in recommendations?
    recommended_movie_ids = [movie_id for movie_id, _ in cf_recs]
    
    hits = []
    for movie_id in test_liked:
        if movie_id in recommended_movie_ids:
            rank = recommended_movie_ids.index(movie_id) + 1
            hits.append((movie_id, rank))
    
    print(f"\n🎯 EVALUATION RESULTS:")
    print("-" * 30)
    
    # Show top recommendations
    print("Top 15 Recommendations:")
    for i, (movie_id, score) in enumerate(cf_recs[:15]):
        is_hit = movie_id in test_liked
        status = "🎯 HIT!" if is_hit else "❓ NEW"
        print(f"{i+1:2d}. Movie {movie_id} | Score: {score:.3f} | {status}")
    
    # Calculate metrics
    total_hits = len(hits)
    precision_at_10 = len([h for h in hits if h[1] <= 10]) / 10
    precision_at_15 = len([h for h in hits if h[1] <= 15]) / 15
    recall = total_hits / len(test_liked)
    
    print(f"\n📊 METRICS:")
    print(f"   Total hits: {total_hits}/{len(test_liked)}")
    print(f"   Precision@10: {precision_at_10:.3f}")
    print(f"   Precision@15: {precision_at_15:.3f}")
    print(f"   Recall: {recall:.3f}")
    
    if precision_at_10 > 0 and recall > 0:
        f1_10 = 2 * (precision_at_10 * recall) / (precision_at_10 + recall)
        print(f"   F1@10: {f1_10:.3f}")
    
    # Show hit details
    if hits:
        print(f"\n🎯 SUCCESSFUL PREDICTIONS:")
        for movie_id, rank in hits:
            movie_info = next(m for m in eval_data['all_liked_movies'] if m['movie_id'] == movie_id)
            print(f"   Rank {rank:2d}: ⭐{movie_info['rating']:.1f} - {movie_info['title']}")
    else:
        print(f"\n❌ No hidden liked movies found in recommendations")
        print(f"This could mean:")
        print(f"   1. Not enough similar users")
        print(f"   2. Collaborative filtering needs tuning")
        print(f"   3. Test data is too sparse")

def run_proper_evaluation():
    """🚀 Complete proper evaluation pipeline"""
    print("🚀 RUNNING PROPER RECOMMENDATION EVALUATION")
    print("="*60)
    
    # Step 1: Create train/test split
    eval_data = create_train_test_split()
    
    # Step 2: Run evaluation
    evaluate_recommendations_properly()
    
    print(f"\n✅ PROPER EVALUATION COMPLETED!")
    print(f"This is how recommendation systems should be evaluated! 🎯")

if __name__ == "__main__":
    run_proper_evaluation()