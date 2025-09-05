#!/usr/bin/env python3
"""
Model'i bir kez eğit ve kaydet - sonra API sadece yükleyip kullanacak
"""

import logging
logging.basicConfig(level=logging.INFO)

print("🧠 PRE-TRAINING NEURAL MODEL")
print("="*50)

try:
    from clean_dynamic_deep_recommender import CleanDynamicDeepRecommender
    
    # Model oluştur
    recommender = CleanDynamicDeepRecommender(
        embedding_dim=128,
        n_similar_users=10,
        similarity_threshold=0.1
    )
    
    print("[*] Training model once...")
    success = recommender.train_model()
    
    if success:
        print("[+] Model training completed!")
        print("[+] Model saved to: clean_neural_model.h5")
        print("[+] Embeddings saved to: user_embeddings.pkl") 
        print("[+] Mappings saved internally")
        print("")
        print("✅ NOW API CALLS WILL BE FAST!")
        print("Model will be loaded instead of trained each time.")
    else:
        print("[x] Model training failed!")
        
except Exception as e:
    print(f"[x] Error: {e}")
    import traceback
    traceback.print_exc()
