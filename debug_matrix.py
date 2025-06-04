import pandas as pd
import numpy as np
import sqlite3
import pickle

def debug_matrix_creation():
    """Matrix oluşturma sürecini debug et"""
    print("🔍 MATRIX DEBUG ANALYSIS")
    print("="*50)
    
    # 1. Database'den veri çek
    conn = sqlite3.connect('movie_recommendation.db')
    print("📊 Step 1: Loading from database...")
    
    ratings_df = pd.read_sql_query("""
        SELECT user_id, movie_id, rating 
        FROM ratings 
        LIMIT 10
    """, conn)
    
    print(f"Sample data from database:")
    print(ratings_df)
    print(f"Data types: {ratings_df.dtypes}")
    
    # 2. Full data çek
    print("\n📊 Step 2: Full data load...")
    ratings_df_full = pd.read_sql_query("""
        SELECT user_id, movie_id, rating 
        FROM ratings 
        ORDER BY user_id, movie_id
    """, conn)
    
    print(f"Full data shape: {ratings_df_full.shape}")
    print(f"User ID range: {ratings_df_full['user_id'].min()} - {ratings_df_full['user_id'].max()}")
    print(f"Movie ID range: {ratings_df_full['movie_id'].min()} - {ratings_df_full['movie_id'].max()}")
    print(f"Rating range: {ratings_df_full['rating'].min()} - {ratings_df_full['rating'].max()}")
    
    # 3. Pivot table oluştur
    print("\n📊 Step 3: Creating pivot table...")
    user_movie_matrix = ratings_df_full.pivot_table(
        index='user_id', 
        columns='movie_id', 
        values='rating', 
        fill_value=np.nan
    )
    
    print(f"Matrix shape: {user_movie_matrix.shape}")
    print(f"Matrix index (users): {user_movie_matrix.index.min()} - {user_movie_matrix.index.max()}")
    print(f"Matrix columns (movies): {user_movie_matrix.columns.min()} - {user_movie_matrix.columns.max()}")
    
    # 4. Matrix content check
    print("\n📊 Step 4: Matrix content analysis...")
    
    # Non-null count
    non_null_count = user_movie_matrix.count().sum()
    print(f"Non-null values: {non_null_count}")
    
    # Sample values
    print("\nSample matrix values (first 5x5):")
    print(user_movie_matrix.iloc[:5, :5])
    
    # Check for actual values
    flat_values = user_movie_matrix.values.flatten()
    non_nan_values = flat_values[~np.isnan(flat_values)]
    print(f"\nFlat non-NaN values count: {len(non_nan_values)}")
    
    if len(non_nan_values) > 0:
        print(f"Sample non-NaN values: {non_nan_values[:10]}")
        print(f"Value range: {non_nan_values.min()} - {non_nan_values.max()}")
    else:
        print("❌ NO NON-NAN VALUES FOUND!")
    
    conn.close()
    return user_movie_matrix

def check_existing_matrix():
    """Mevcut matrix'i kontrol et"""
    print("\n🔍 CHECKING EXISTING MATRIX")
    print("="*40)
    
    try:
        with open('user_movie_matrix.pkl', 'rb') as f:
            matrix = pickle.load(f)
        
        print(f"✅ Matrix loaded: {matrix.shape}")
        
        # Content check
        print("\nMatrix content check:")
        print(f"Total cells: {matrix.size}")
        print(f"Non-null count: {matrix.count().sum()}")
        
        flat_values = matrix.values.flatten()
        non_nan_values = flat_values[~np.isnan(flat_values)]
        print(f"Non-NaN values: {len(non_nan_values)}")
        
        if len(non_nan_values) > 0:
            print(f"Value range: {non_nan_values.min()} - {non_nan_values.max()}")
            print(f"Sample values: {non_nan_values[:5]}")
        else:
            print("❌ All values are NaN!")
        
        # Sample locations
        print("\nSample matrix (first 5x5):")
        print(matrix.iloc[:5, :5])
        
    except Exception as e:
        print(f"❌ Error loading matrix: {e}")

if __name__ == "__main__":
    debug_matrix_creation()
    check_existing_matrix()