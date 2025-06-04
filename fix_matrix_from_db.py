import pandas as pd
import numpy as np
import sqlite3
import pickle
import os

def fix_matrix_from_existing_db():
    """Mevcut database'den proper matrix oluştur"""
    print("🔧 FIXING MATRIX FROM EXISTING DATABASE")
    print("="*60)
    
    # Database bağlantısı
    conn = sqlite3.connect('movie_recommendation.db')
    
    print("📊 Loading ratings from database...")
    
    # Ratings'leri çek
    ratings_df = pd.read_sql_query("""
        SELECT user_id, movie_id, rating 
        FROM ratings 
        ORDER BY user_id, movie_id
    """, conn)
    
    print(f"✅ Loaded {len(ratings_df):,} ratings")
    print(f"👥 Unique users: {ratings_df['user_id'].nunique()}")
    print(f"🎬 Unique movies: {ratings_df['movie_id'].nunique()}")
    print(f"⭐ Rating range: {ratings_df['rating'].min()} - {ratings_df['rating'].max()}")
    print(f"📈 Average rating: {ratings_df['rating'].mean():.2f}")
    
    # Proper sparse matrix oluştur
    print("\n🔄 Creating proper sparse matrix...")
    user_movie_matrix = ratings_df.pivot_table(
        index='user_id', 
        columns='movie_id', 
        values='rating', 
        fill_value=np.nan  # NaN for missing, NOT 0!
    )
    
    # Matrix stats
    non_null_count = user_movie_matrix.count().sum()
    total_cells = user_movie_matrix.size
    sparsity = (user_movie_matrix.isnull().sum().sum() / total_cells) * 100
    
    print(f"📏 Matrix shape: {user_movie_matrix.shape}")
    print(f"⭐ Non-null ratings: {non_null_count:,}")
    print(f"🕳️ Sparsity: {sparsity:.1f}%")
    print(f"📊 Average rating: {user_movie_matrix.dropna().values.mean():.2f}")
    
    # Backup old matrix
    if os.path.exists('user_movie_matrix.pkl'):
        os.rename('user_movie_matrix.pkl', 'user_movie_matrix_OLD.pkl')
        print("💾 Old matrix backed up as 'user_movie_matrix_OLD.pkl'")
    
    # Save new matrix
    with open('user_movie_matrix.pkl', 'wb') as f:
        pickle.dump(user_movie_matrix, f)
    
    print("✅ New proper matrix saved!")
    
    # Verification
    print("\n🔍 VERIFICATION:")
    with open('user_movie_matrix.pkl', 'rb') as f:
        verify_matrix = pickle.load(f)
    
    verify_non_null = verify_matrix.dropna().values.flatten()
    print(f"📏 Verified shape: {verify_matrix.shape}")
    print(f"⭐ Verified ratings: {len(verify_non_null):,}")
    print(f"📈 Verified average: {verify_non_null.mean():.2f}")
    print(f"🕳️ Verified sparsity: {(verify_matrix.isnull().sum().sum() / verify_matrix.size * 100):.1f}%")
    
    conn.close()
    
    print("\n🎉 MATRIX FIXED! Database and Matrix now synchronized!")
    return user_movie_matrix

if __name__ == "__main__":
    fix_matrix_from_existing_db()
    print("\n🚀 Now run: python analyze_system_final.py")