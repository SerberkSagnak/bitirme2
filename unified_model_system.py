"""
Unified Model Loading System
Tüm modelleri tek yerden yükleyen ve entegre eden sistem
"""

import os
import pickle
import sqlite3
import pandas as pd
import numpy as np
import tensorflow as tf
from sklearn.metrics.pairwise import cosine_similarity
import logging
from typing import Dict, List, Optional, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UnifiedRecommendationSystem:
    """
    Tüm öneri algoritmalarını tek çatı altında birleştiren sistem
    
    Desteklenen Algoritmalar:
    1. Collaborative Filtering (user-movie matrix)
    2. Deep Learning (TensorFlow neural embeddings)
    3. NMF Matrix Factorization
    4. Advanced Hybrid System
    """
    
    def __init__(self, db_path="../movielens_100k.db"):
        self.db_path = db_path
        
        # Model components
        self.user_movie_matrix = None
        self.user_id_map = None
        self.movie_id_map = None
        self.inv_movie_id_map = None
        
        # Deep learning components
        self.dl_model = None
        self.dl_user_to_idx = None
        self.dl_movie_to_idx = None
        self.dl_idx_to_user = None
        self.dl_idx_to_movie = None
        
        # Clean deep learning
        self.clean_deep_recommender = None
        
        # Advanced model
        self.advanced_recommender = None
        
        # NMF model
        self.nmf_model = None
        self.user_features = None
        self.item_features = None
        
        # Status tracking
        self.loaded_models = {
            'collaborative_filtering': False,
            'deep_learning': False,
            'clean_deep_learning': False,
            'advanced_hybrid': False,
            'nmf_model': False
        }
        
        logger.info("[*] Unified Recommendation System initialized")

    def load_all_models(self):
        """Tüm modelleri yükle - priority sırasına göre"""
        logger.info("[*] Loading all models...")
        
        # 1. Collaborative Filtering (en temel)
        self._load_collaborative_filtering()
        
        # 2. Clean Deep Learning (senin ana sistemi)
        self._load_clean_deep_learning()
        
        # 3. TensorFlow Deep Learning
        self._load_tensorflow_deep_learning()
        
        # 4. Advanced Hybrid
        self._load_advanced_hybrid()
        
        # 5. NMF Model
        self._load_nmf_model()
        
        # Summary
        loaded_count = sum(self.loaded_models.values())
        logger.info(f"[+] Model loading complete: {loaded_count}/5 models loaded")
        return loaded_count > 0

    def _load_collaborative_filtering(self):
        """Collaborative Filtering matrix yükle"""
        try:
            self.user_movie_matrix = pd.read_pickle("user_movie_matrix.pkl").to_numpy()
            
            # Create mappings
            user_movie_df = pd.read_pickle("user_movie_matrix.pkl")
            user_ids = user_movie_df.index.tolist()
            movie_ids = user_movie_df.columns.tolist()
            
            self.user_id_map = {int(user_id): i for i, user_id in enumerate(user_ids)}
            self.movie_id_map = {int(movie_id): i for i, movie_id in enumerate(movie_ids)}
            self.inv_movie_id_map = {i: int(movie_id) for i, movie_id in enumerate(movie_ids)}
            
            self.loaded_models['collaborative_filtering'] = True
            logger.info(f"[+] Collaborative Filtering loaded: {self.user_movie_matrix.shape}")
            
        except Exception as e:
            logger.error(f"[x] Collaborative Filtering loading failed: {e}")

    def _load_clean_deep_learning(self):
        """Clean Deep Learning system yükle"""
        try:
            from clean_dynamic_deep_recommender import CleanDynamicDeepRecommender
            
            self.clean_deep_recommender = CleanDynamicDeepRecommender(
                embedding_dim=128,
                n_similar_users=10,
                similarity_threshold=0.1
            )
            
            # Pre-trained model varsa yükle
            if os.path.exists("dynamic_deep_model.h5") and os.path.exists("user_embeddings.pkl"):
                if self.clean_deep_recommender.load_embeddings():
                    self.loaded_models['clean_deep_learning'] = True
                    logger.info("[+] Clean Deep Learning loaded successfully")
                else:
                    # Train if needed
                    if self.clean_deep_recommender.train_model():
                        self.loaded_models['clean_deep_learning'] = True
                        logger.info("[+] Clean Deep Learning trained and loaded")
            else:
                logger.info("[*] Clean Deep Learning model needs training")
                
        except Exception as e:
            logger.error(f"[x] Clean Deep Learning loading failed: {e}")

    def _load_tensorflow_deep_learning(self):
        """TensorFlow deep learning model yükle"""
        try:
            self.dl_model = tf.keras.models.load_model(
                'dl_model.h5',
                custom_objects={'mse': 'mean_squared_error'}
            )
            
            with open('dl_model_mappings.pkl', 'rb') as f:
                mappings = pickle.load(f)
                self.dl_user_to_idx = mappings['user_to_idx']
                self.dl_movie_to_idx = mappings['movie_to_idx']
                self.dl_idx_to_user = {i: user_id for user_id, i in self.dl_user_to_idx.items()}
                self.dl_idx_to_movie = {i: movie_id for movie_id, i in self.dl_movie_to_idx.items()}
            
            self.loaded_models['deep_learning'] = True
            logger.info("[+] TensorFlow Deep Learning loaded")
            
        except Exception as e:
            logger.error(f"[x] TensorFlow Deep Learning loading failed: {e}")

    def _load_advanced_hybrid(self):
        """Advanced hybrid model yükle"""
        try:
            from kullanıcımodel import AdvancedRecommendationSystem
            
            self.advanced_recommender = AdvancedRecommendationSystem()
            self.advanced_recommender.load_model('kullanıcıoneri.pkl')
            
            self.loaded_models['advanced_hybrid'] = True
            logger.info("[+] Advanced Hybrid Model loaded")
            
        except Exception as e:
            logger.error(f"[x] Advanced Hybrid loading failed: {e}")

    def _load_nmf_model(self):
        """NMF model yükle"""
        try:
            with open('trained_model.pkl', 'rb') as f:
                nmf_data = pickle.load(f)
                
            self.nmf_model = nmf_data.get('model')
            self.user_features = nmf_data.get('user_features')
            self.item_features = nmf_data.get('item_features')
            
            self.loaded_models['nmf_model'] = True
            logger.info("[+] NMF Model loaded")
            
        except Exception as e:
            logger.error(f"[x] NMF Model loading failed: {e}")

    def get_recommendations(self, user_id: int, n_recommendations: int = 10, algorithm: str = "auto") -> Dict[str, Any]:
        """
        Unified recommendation interface
        
        Args:
            user_id: Target user ID
            n_recommendations: Number of recommendations
            algorithm: "auto", "collaborative", "deep_learning", "hybrid", "nmf"
        """
        
        # Check user data first
        user_rating_count = self._get_user_rating_count(user_id)
        
        # Algorithm selection based on data availability
        if algorithm == "auto":
            if user_rating_count >= 10 and self.loaded_models['clean_deep_learning']:
                algorithm = "deep_learning"
            elif user_rating_count >= 5 and self.loaded_models['collaborative_filtering']:
                algorithm = "collaborative"
            elif self.loaded_models['advanced_hybrid']:
                algorithm = "hybrid"
            else:
                algorithm = "popular"
        
        logger.info(f"[*] Using {algorithm} algorithm for user {user_id} ({user_rating_count} ratings)")
        
        # Route to appropriate algorithm
        if algorithm == "deep_learning" and self.loaded_models['clean_deep_learning']:
            return self._get_deep_learning_recommendations(user_id, n_recommendations)
        
        elif algorithm == "collaborative" and self.loaded_models['collaborative_filtering']:
            return self._get_collaborative_recommendations(user_id, n_recommendations)
        
        elif algorithm == "hybrid" and self.loaded_models['advanced_hybrid']:
            return self._get_hybrid_recommendations(user_id, n_recommendations)
        
        elif algorithm == "nmf" and self.loaded_models['nmf_model']:
            return self._get_nmf_recommendations(user_id, n_recommendations)
        
        else:
            return self._get_popular_recommendations(user_id, n_recommendations)

    def _get_user_rating_count(self, user_id: int) -> int:
        """Kullanıcının kaç film puanladığını kontrol et"""
        try:
            conn = sqlite3.connect(self.db_path)
            count = conn.execute("""
                SELECT COUNT(*) FROM user_interactions 
                WHERE user_id = ? AND interaction_type = 'rating'
            """, (user_id,)).fetchone()[0]
            conn.close()
            return count
        except:
            return 0

    def _get_deep_learning_recommendations(self, user_id: int, n_recommendations: int) -> Dict[str, Any]:
        """Clean Deep Learning önerileri"""
        try:
            # 10 benzer kullanıcı bul
            similar_users = self.clean_deep_recommender.find_similar_users(user_id)
            
            if similar_users:
                # Bu kullanıcıların filmlerini öner
                recommendations = self.clean_deep_recommender.get_recommendations(user_id, n_recommendations)
                
                return {
                    "status": "success",
                    "message": f"🧠 DERIN ÖĞRENME - {len(similar_users)} benzer kullanıcıdan {len(recommendations)} öneri",
                    "method": "Clean Deep Learning - Neural Embeddings",
                    "algorithm": "neural_collaborative_filtering",
                    "similar_users_found": len(similar_users),
                    "similar_users": similar_users[:3],
                    "recommendations": recommendations,
                    "quality": "personalized_deep_learning"
                }
        except Exception as e:
            logger.error(f"[x] Deep learning recommendations failed: {e}")
        
        # Fallback
        return self._get_collaborative_recommendations(user_id, n_recommendations)

    def _get_collaborative_recommendations(self, user_id: int, n_recommendations: int) -> Dict[str, Any]:
        """Basic collaborative filtering"""
        try:
            if self.user_movie_matrix is not None and user_id in self.user_id_map:
                user_idx = self.user_id_map[user_id]
                user_vector = self.user_movie_matrix[user_idx].reshape(1, -1)
                
                # Similar users
                similarities = cosine_similarity(user_vector, self.user_movie_matrix)[0]
                similar_indices = np.argsort(similarities)[::-1][1:11]
                
                # Recommendations
                similar_ratings = self.user_movie_matrix[similar_indices]
                movie_scores = similar_ratings.mean(axis=0)
                top_movie_indices = np.argsort(movie_scores)[::-1][:n_recommendations]
                
                recommendations = []
                for movie_idx in top_movie_indices:
                    if movie_scores[movie_idx] > 0:
                        movie_id = self.inv_movie_id_map.get(movie_idx)
                        if movie_id:
                            movie_info = self._get_movie_info(movie_id)
                            if movie_info:
                                recommendations.append({
                                    "movie_id": movie_id,
                                    "title": movie_info.get('title'),
                                    "genres": movie_info.get('genres', '').split('|') if movie_info.get('genres') else [],
                                    "predicted_rating": float(movie_scores[movie_idx] * 5.0),
                                    "similarity_score": float(movie_scores[movie_idx]),
                                    "algorithm": "collaborative_filtering"
                                })
                
                return {
                    "status": "success",
                    "message": f"⚡ COLLABORATIVE FILTERING - {len(recommendations)} öneri",
                    "method": "Basic Collaborative Filtering",
                    "algorithm": "collaborative_filtering",
                    "recommendations": recommendations,
                    "quality": "collaborative"
                }
        except Exception as e:
            logger.error(f"[x] Collaborative filtering failed: {e}")
        
        return self._get_popular_recommendations(user_id, n_recommendations)

    def _get_popular_recommendations(self, user_id: int, n_recommendations: int) -> Dict[str, Any]:
        """Popular movies fallback"""
        try:
            conn = sqlite3.connect(self.db_path)
            movies = conn.execute("""
                SELECT id, title, genres, avg_rating
                FROM movies 
                WHERE avg_rating IS NOT NULL
                AND id NOT IN (
                    SELECT DISTINCT movie_id 
                    FROM user_interactions 
                    WHERE user_id = ? 
                    AND interaction_type = 'rating'
                )
                ORDER BY avg_rating DESC 
                LIMIT ?
            """, (user_id, n_recommendations)).fetchall()
            conn.close()
            
            recommendations = []
            for movie in movies:
                recommendations.append({
                    "movie_id": movie[0],
                    "title": movie[1],
                    "genres": movie[2].split('|') if movie[2] else [],
                    "predicted_rating": float(movie[3]) if movie[3] else 4.0,
                    "algorithm": "popularity_based"
                })
            
            return {
                "status": "success",
                "message": f"🔥 POPÜLER FİLMLER - {len(recommendations)} öneri",
                "method": "Popular Movies",
                "algorithm": "popularity_based",
                "recommendations": recommendations,
                "quality": "popular"
            }
            
        except Exception as e:
            logger.error(f"[x] Popular recommendations failed: {e}")
            return {
                "status": "error",
                "message": "Öneri sistemi çalışmıyor",
                "recommendations": []
            }

    def _get_movie_info(self, movie_id: int) -> Optional[Dict[str, str]]:
        """Film bilgilerini getir"""
        try:
            conn = sqlite3.connect(self.db_path)
            movie = conn.execute("SELECT id, title, genres, avg_rating FROM movies WHERE id = ?", (movie_id,)).fetchone()
            conn.close()
            
            if movie:
                return {
                    'id': movie[0],
                    'title': movie[1],
                    'genres': movie[2],
                    'avg_rating': movie[3]
                }
        except:
            pass
        return None

    def get_system_status(self) -> Dict[str, Any]:
        """Sistem durumu raporu"""
        return {
            "loaded_models": self.loaded_models,
            "total_loaded": sum(self.loaded_models.values()),
            "primary_algorithm": "clean_deep_learning" if self.loaded_models['clean_deep_learning'] else "collaborative_filtering",
            "ready": sum(self.loaded_models.values()) > 0
        }

# Global instance
unified_system = UnifiedRecommendationSystem()

def initialize_unified_system():
    """Unified system'i başlat"""
    logger.info("[*] Initializing Unified Recommendation System...")
    
    success = unified_system.load_all_models()
    
    if success:
        logger.info("[+] Unified Recommendation System ready!")
        return unified_system
    else:
        logger.error("[x] Failed to initialize any models")
        return None

# Test function
if __name__ == "__main__":
    system = initialize_unified_system()
    
    if system:
        # Test recommendations for alice (user_id=1)
        print("\n=== TESTING RECOMMENDATIONS ===")
        
        recommendations = system.get_recommendations(1, 5, "auto")
        print(f"Status: {recommendations['status']}")
        print(f"Method: {recommendations['method']}")
        print(f"Count: {len(recommendations.get('recommendations', []))}")
        
        if recommendations.get('recommendations'):
            print("Sample recommendations:")
            for i, rec in enumerate(recommendations['recommendations'][:3], 1):
                print(f"  {i}. {rec['title']}: {rec['predicted_rating']:.2f}/5.0")
        
        print(f"\nSystem Status: {system.get_system_status()}")
    else:
        print("System initialization failed")
