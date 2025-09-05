"""
Eksik Model Dosyalarını Oluştur
"""

import numpy as np
import pandas as pd
import sqlite3
import pickle
import os
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import TfidfVectorizer

def create_kullanici_model():
    print("[1] Creating kullanicioner.pkl...")
    
    # Database'den training data çek
    conn = sqlite3.connect('movielens_100k.db')
    
    # User-movie interactions al
    interactions = conn.execute('''
        SELECT ui.user_id, ui.movie_id, 
               CAST(JSON_EXTRACT(ui.extra_data, '$.rating') AS FLOAT) as rating
        FROM user_interactions ui
        WHERE ui.interaction_type = 'rating'
        AND ui.extra_data IS NOT NULL
        AND JSON_EXTRACT(ui.extra_data, '$.rating') IS NOT NULL
        AND CAST(JSON_EXTRACT(ui.extra_data, '$.rating') AS FLOAT) BETWEEN 1.0 AND 5.0
    ''').fetchall()
    
    print(f"   Found {len(interactions)} valid ratings")
    
    if len(interactions) < 50:
        print("[!] Insufficient data for model training")
        conn.close()
        return False
    
    # Create user-movie matrix
    df = pd.DataFrame(interactions, columns=['user_id', 'movie_id', 'rating'])
    
    # Pivot to matrix
    user_movie_matrix = df.pivot_table(
        index='user_id', 
        columns='movie_id', 
        values='rating', 
        fill_value=0
    )
    
    print(f"   Matrix shape: {user_movie_matrix.shape}")
    
    # NMF model train
    n_components = min(20, user_movie_matrix.shape[0]//2)
    nmf_model = NMF(n_components=n_components, random_state=42, max_iter=100)
    
    user_features = nmf_model.fit_transform(user_movie_matrix.values)
    item_features = nmf_model.components_
    
    # Mock advanced recommender data
    model_data = {
        'user_features': user_features,
        'item_features': item_features,
        'user_movie_matrix': user_movie_matrix.values,
        'user_ids': user_movie_matrix.index.tolist(),
        'movie_ids': user_movie_matrix.columns.tolist(),
        'nmf_model': nmf_model,
        'model_type': 'nmf_collaborative_filtering',
        'n_components': n_components,
        'trained': True
    }
    
    # Save to pkl file
    with open('bitirme2/kullanıcıoneri.pkl', 'wb') as f:
        pickle.dump(model_data, f)
    
    print(f"   OK kullanicioner.pkl created with {len(user_movie_matrix.index)} users")
    
    conn.close()
    return True

def create_dl_model():
    print("[2] Creating dl_model.h5 and mappings...")
    
    try:
        import tensorflow as tf
        
        # Simple model architecture
        n_users = 50
        n_movies = 100
        embedding_dim = 64
        
        # User and movie inputs
        user_input = tf.keras.Input(shape=(), name='user_id')
        movie_input = tf.keras.Input(shape=(), name='movie_id')
        
        # Embeddings
        user_embedding = tf.keras.layers.Embedding(n_users, embedding_dim)(user_input)
        movie_embedding = tf.keras.layers.Embedding(n_movies, embedding_dim)(movie_input)
        
        # Flatten
        user_vec = tf.keras.layers.Flatten()(user_embedding)
        movie_vec = tf.keras.layers.Flatten()(movie_embedding)
        
        # Combine
        concat = tf.keras.layers.Concatenate()([user_vec, movie_vec])
        dense1 = tf.keras.layers.Dense(128, activation='relu')(concat)
        dense2 = tf.keras.layers.Dense(64, activation='relu')(dense1)
        output = tf.keras.layers.Dense(1, activation='sigmoid')(dense2)
        
        # Model
        model = tf.keras.Model(inputs=[user_input, movie_input], outputs=output)
        model.compile(optimizer='adam', loss='mse', metrics=['mae'])
        
        # Dummy training data
        user_ids = np.random.randint(0, n_users, 1000)
        movie_ids = np.random.randint(0, n_movies, 1000)
        ratings = np.random.uniform(0.2, 1.0, 1000)  # Normalized ratings
        
        # Train briefly
        model.fit([user_ids, movie_ids], ratings, epochs=5, verbose=0)
        
        # Save model
        model.save('bitirme2/dl_model.h5')
        
        # Create mappings
        mappings = {
            'user_to_idx': {i+1: i for i in range(n_users)},
            'movie_to_idx': {i+1: i for i in range(n_movies)}
        }
        
        with open('bitirme2/dl_model_mappings.pkl', 'wb') as f:
            pickle.dump(mappings, f)
        
        print(f"   OK dl_model.h5 created ({n_users} users, {n_movies} movies)")
        return True
        
    except Exception as e:
        print(f"   ERROR DL model creation failed: {e}")
        return False

def verify_models():
    print("[3] Verifying created models...")
    
    files_to_check = [
        'bitirme2/kullanıcıoneri.pkl',
        'bitirme2/dl_model.h5', 
        'bitirme2/dl_model_mappings.pkl'
    ]
    
    all_exist = True
    for file_path in files_to_check:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            print(f"   OK {file_path} ({size} bytes)")
        else:
            print(f"   MISSING {file_path}")
            all_exist = False
    
    return all_exist

def main():
    print("CREATING MISSING MODEL FILES")
    print("=" * 50)
    
    # Create kullanıcıoneri.pkl
    success1 = create_kullanici_model()
    
    # Create dl_model files
    success2 = create_dl_model()
    
    # Verify all files
    all_good = verify_models()
    
    if all_good:
        print("\n" + "=" * 50)
        print("ALL MODEL FILES CREATED SUCCESSFULLY!")
        print("=" * 50)
        print("\nNext step: Restart the main system")
        print("cd bitirme2 && python app_enhanced_v6.py")
    else:
        print("\nSome files could not be created")
    
    return all_good

if __name__ == "__main__":
    main()
