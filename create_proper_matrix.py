import pandas as pd
import numpy as np
import sqlite3
import pickle
from scipy.sparse import csr_matrix

def create_proper_matrix():
    """Database'den doğru user-movie matrix oluştur"""
    print("🔧 PROPER MATRIX CREATION")
    print("="*50)
    
    # Database'den veri çek
    conn = sqlite3.connect('movie_recommendation.db')
    
    print("📊 Loading ratings from database...")
    ratings_df = pd.read_sql_query("""
        SELECT user_id, movie_id, rating 
        FROM ratings 
        ORDER BY user_id, movie_id
    """, conn)
    
    print(f"✅ Loaded {len(ratings_df):,} ratings")
    print(f"👥 Users: {ratings_df['user_id'].nunique()}")
    print(f"🎬 Movies: {ratings_df['movie_id'].nunique()}")
    print(f"⭐ Rating range: {ratings_df['rating'].min()} - {ratings_df['rating'].max()}")
    print(f"📈 Average: {ratings_df['rating'].mean():.2f}")
    
    # Pivot table oluştur (proper sparse matrix)
    print("\n🔄 Creating user-movie matrix...")
    user_movie_matrix = ratings_df.pivot_table(
        index='user_id', 
        columns='movie_id', 
        values='rating', 
        fill_value=np.nan  # NaN for missing ratings (not 0!)
    )
    
    print(f"📏 Matrix shape: {user_movie_matrix.shape}")
    print(f"⭐ Non-null ratings: {user_movie_matrix.count().sum():,}")
    print(f"🕳️ Sparsity: {(user_movie_matrix.isnull().sum().sum() / user_movie_matrix.size * 100):.1f}%")
    
    # Save new matrix
    with open('user_movie_matrix_fixed.pkl', 'wb') as f:
        pickle.dump(user_movie_matrix, f)
    
    print("✅ New matrix saved as 'user_movie_matrix_fixed.pkl'")
    
    # Backup old matrix
    import os
    if os.path.exists('user_movie_matrix.pkl'):
        os.rename('user_movie_matrix.pkl', 'user_movie_matrix_old.pkl')
        print("🔄 Old matrix backed up as 'user_movie_matrix_old.pkl'")
    
    # Replace with new matrix
    os.rename('user_movie_matrix_fixed.pkl', 'user_movie_matrix.pkl')
    print("✅ New matrix is now active!")
    
    conn.close()
    
    return user_movie_matrix

def verify_new_matrix():
    """Yeni matrix'i doğrula"""
    print("\n🔍 VERIFICATION")
    print("="*30)
    
    with open('user_movie_matrix.pkl', 'rb') as f:
        matrix = pickle.load(f)
    
    non_null_values = matrix.dropna().values.flatten()
    
    print(f"✅ Matrix verified!")
    print(f"📏 Shape: {matrix.shape}")
    print(f"⭐ Ratings: {len(non_null_values):,}")
    print(f"📈 Average: {non_null_values.mean():.2f}")
    print(f"🕳️ Sparsity: {(matrix.isnull().sum().sum() / matrix.size * 100):.1f}%")
    
    # Sample data
    print(f"\n👀 Sample (first 5x5):")
    print(matrix.iloc[:5, :5])

if __name__ == "__main__":
    matrix = create_proper_matrix()
    verify_new_matrix()
    print("\n🎉 Matrix sync completed! Ready for Option 1!")