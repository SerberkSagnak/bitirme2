import pandas as pd
import numpy as np
import sqlite3
import pickle
import os

def create_proper_matrix():
    """Matrix'i doğru şekilde oluştur"""
    print("🔧 CREATING PROPER MATRIX")
    print("="*50)
    
    # Database connection
    conn = sqlite3.connect('movie_recommendation.db')
    
    # Load ratings data
    print("📊 Loading ratings...")
    ratings_df = pd.read_sql_query("""
        SELECT user_id, movie_id, rating 
        FROM ratings 
        ORDER BY user_id, movie_id
    """, conn)
    
    print(f"✅ Loaded {len(ratings_df):,} ratings")
    print(f"👥 Users: {ratings_df['user_id'].nunique()}")
    print(f"🎬 Movies: {ratings_df['movie_id'].nunique()}")
    
    # Ensure correct data types
    ratings_df['user_id'] = ratings_df['user_id'].astype(int)
    ratings_df['movie_id'] = ratings_df['movie_id'].astype(int)
    ratings_df['rating'] = ratings_df['rating'].astype(float)
    
    print(f"Data types: {ratings_df.dtypes}")
    print(f"Sample data:")
    print(ratings_df.head())
    
    # Create pivot table with proper handling
    print("\n🔄 Creating matrix...")
    
    # Method 1: Using pivot_table
    try:
        user_movie_matrix = ratings_df.pivot(
            index='user_id',
            columns='movie_id', 
            values='rating'
        )
        print("✅ Matrix created using pivot()")
        
    except ValueError as e:
        print(f"⚠️ Pivot failed: {e}")
        print("🔄 Trying pivot_table with aggregation...")
        
        # Method 2: Using pivot_table with mean aggregation
        user_movie_matrix = ratings_df.pivot_table(
            index='user_id',
            columns='movie_id',
            values='rating',
            aggfunc='mean'  # In case of duplicates
        )
        print("✅ Matrix created using pivot_table()")
    
    # Check matrix content
    print(f"\n📊 Matrix Analysis:")
    print(f"Shape: {user_movie_matrix.shape}")
    
    # Count non-null values
    non_null_count = user_movie_matrix.count().sum()
    print(f"Non-null values: {non_null_count:,}")
    
    if non_null_count > 0:
        # Get non-null values
        non_null_values = user_movie_matrix.stack().values
        print(f"✅ Successfully created matrix with {len(non_null_values):,} ratings")
        print(f"Rating range: {non_null_values.min():.1f} - {non_null_values.max():.1f}")
        print(f"Average rating: {non_null_values.mean():.2f}")
        
        # Sparsity
        sparsity = (user_movie_matrix.isnull().sum().sum() / user_movie_matrix.size) * 100
        print(f"Sparsity: {sparsity:.1f}%")
        
        # Save matrix
        print("\n💾 Saving matrix...")
        
        # Backup old matrix
        if os.path.exists('user_movie_matrix.pkl'):
            os.rename('user_movie_matrix.pkl', 'user_movie_matrix_backup.pkl')
            print("📦 Old matrix backed up")
        
        # Save new matrix
        with open('user_movie_matrix.pkl', 'wb') as f:
            pickle.dump(user_movie_matrix, f)
        
        print("✅ Matrix saved successfully!")
        
        # Verification
        print("\n🔍 Verification:")
        with open('user_movie_matrix.pkl', 'rb') as f:
            test_matrix = pickle.load(f)
        
        test_non_null = test_matrix.count().sum()
        print(f"Verified non-null count: {test_non_null:,}")
        
        if test_non_null > 0:
            test_values = test_matrix.stack().values
            print(f"Verified average: {test_values.mean():.2f}")
            print("✅ Matrix verification successful!")
            return True
        else:
            print("❌ Matrix verification failed!")
            return False
        
    else:
        print("❌ Matrix creation failed - no non-null values!")
        return False
    
    conn.close()

if __name__ == "__main__":
    success = create_proper_matrix()
    if success:
        print("\n🎉 SUCCESS! Matrix created properly!")
        print("🚀 Now run: python analyze_system_final_fixed.py")
    else:
        print("\n❌ FAILED! Check debug output above.")