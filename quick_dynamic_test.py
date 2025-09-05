"""
Quick Dynamic Deep Learning Test - Direct Test
"""

import sys
import os
sys.path.append("bitirme2")

def test_dynamic_system():
    print("=" * 50)
    print("DYNAMIC DEEP LEARNING DIRECT TEST")
    print("=" * 50)
    
    try:
        # Test dynamic recommender import
        print("[1] Testing dynamic recommender import...")
        from bitirme2.dynamic_deep_recommender import DynamicDeepRecommender
        print("[+] Import successful")
        
        # Create instance
        print("[2] Creating recommender instance...")
        recommender = DynamicDeepRecommender(
            embedding_dim=128,
            n_similar_users=10,
            model_path="bitirme2/dynamic_deep_model.h5",
            embeddings_path="bitirme2/user_embeddings.pkl"
        )
        print("[+] Instance created")
        
        # Check if model files exist
        print("[3] Checking model files...")
        model_exists = os.path.exists("bitirme2/dynamic_deep_model.h5")
        embeddings_exist = os.path.exists("bitirme2/user_embeddings.pkl")
        
        print(f"   Model file: {'OK' if model_exists else 'MISSING'}")
        print(f"   Embeddings file: {'OK' if embeddings_exist else 'MISSING'}")
        
        if not model_exists:
            print("[!] Model not found - training required")
            print("[*] Starting model training...")
            success = recommender.train_model(retrain=True)
            if success:
                print("[+] Model training completed!")
            else:
                print("[x] Model training failed!")
                return False
        
        # Test database connection
        print("[4] Testing database connection...")
        import sqlite3
        conn = sqlite3.connect("movielens_100k.db")
        user_count = conn.execute("SELECT COUNT(*) FROM app_users").fetchone()[0]
        rating_count = conn.execute("SELECT COUNT(*) FROM user_interactions WHERE interaction_type = 'rating'").fetchone()[0]
        conn.close()
        print(f"[+] Database OK - {user_count} users, {rating_count} ratings")
        
        # Test similarity calculation
        print("[5] Testing similarity calculation...")
        if user_count > 0:
            similar_users = recommender.find_similar_users(1)
            print(f"[+] Found {len(similar_users)} similar users for user 1")
            
            if similar_users:
                for i, user in enumerate(similar_users[:3]):
                    print(f"   {i+1}. User {user['user_id']}: {user['similarity_score']:.3f}")
        
        # Test recommendations
        print("[6] Testing recommendations...")
        if user_count > 0:
            recommendations = recommender.get_recommendations_from_similar_users(1, 5)
            print(f"[+] Generated {len(recommendations)} recommendations")
            
            for i, rec in enumerate(recommendations[:3]):
                print(f"   {i+1}. {rec['title']}: {rec['predicted_rating']:.2f}")
        
        print("\n" + "=" * 50)
        print("DYNAMIC DEEP LEARNING SYSTEM WORKING!")
        print("=" * 50)
        print("\nSystem is ready for API server!")
        return True
        
    except Exception as e:
        print(f"\n[x] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_dynamic_system()
