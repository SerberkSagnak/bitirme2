import pandas as pd
import pickle

def debug_matrix_mismatch():
    """🔍 Matrix mismatch problemini çöz"""
    
    # Load data
    with open('test_user_data.pkl', 'rb') as f:
        test_data = pickle.load(f)
    
    with open('user_movie_matrix.pkl', 'rb') as f:
        user_movie_matrix = pickle.load(f)
    
    test_user_id = test_data['test_user_id']
    liked_movies = test_data['liked_movies']
    
    print("🔍 DEBUGGING MATRIX MISMATCH")
    print("="*50)
    
    # Check matrix structure
    print(f"Matrix shape: {user_movie_matrix.shape}")
    print(f"Matrix columns (first 10): {list(user_movie_matrix.columns[:10])}")
    print(f"Matrix columns (last 10): {list(user_movie_matrix.columns[-10:])}")
    
    # Check liked movies
    liked_movie_ids = [m['movie_id'] for m in liked_movies]
    print(f"\nLiked movie IDs (first 10): {liked_movie_ids[:10]}")
    
    # Check overlap
    matrix_movie_ids = set(user_movie_matrix.columns)
    liked_movie_ids_set = set(liked_movie_ids)
    overlap = matrix_movie_ids.intersection(liked_movie_ids_set)
    
    print(f"\nMatrix movie IDs range: {min(matrix_movie_ids)} - {max(matrix_movie_ids)}")
    print(f"Liked movie IDs range: {min(liked_movie_ids)} - {max(liked_movie_ids)}")
    print(f"Overlap: {len(overlap)} movies")
    print(f"Overlap IDs: {list(overlap)[:10]}")
    
    # Check test user ratings in matrix
    if test_user_id in user_movie_matrix.index:
        user_ratings = user_movie_matrix.loc[test_user_id]
        rated_in_matrix = user_ratings.dropna()
        print(f"\nTest user has {len(rated_in_matrix)} ratings in matrix")
        print(f"Rated movie IDs: {list(rated_in_matrix.index[:10])}")
    else:
        print(f"\n❌ Test user {test_user_id} not found in matrix!")
    
    return overlap

if __name__ == "__main__":
    overlap = debug_matrix_mismatch()