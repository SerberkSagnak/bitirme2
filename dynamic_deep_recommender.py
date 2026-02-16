import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler, LabelEncoder
import sqlite3
import pickle
import logging
from datetime import datetime
from typing import List, Dict, Tuple, Optional

class DynamicDeepRecommender:
    """
    Dinamik Derin Öğrenme Tabanlı Öneri Sistemi
    
    Bu sistem şu şekilde çalışır:
    1. Kullanıcıları 128-boyutlu vektörlerde temsil eder
    2. Hedef kullanıcıya en benzer 10 kullanıcıyı bulur
    3. Bu 10 kullanıcının tercihlerine göre film önerileri üretir
    4. Yeni rating geldiğinde embeddingleri dinamik olarak günceller
    """
    
    def __init__(self, 
                 embedding_dim: int = 128,
                 similarity_threshold: float = 0.3,
                 n_similar_users: int = 10,
                 model_path: str = "dynamic_deep_model.h5",
                 embeddings_path: str = "user_embeddings.pkl"):
        
        self.embedding_dim = embedding_dim
        self.similarity_threshold = similarity_threshold
        self.n_similar_users = n_similar_users
        self.model_path = model_path
        self.embeddings_path = embeddings_path
        
        # Model bileşenleri
        self.model = None
        self.user_embeddings = None
        self.movie_embeddings = None
        self.user_encoder = LabelEncoder()
        self.movie_encoder = LabelEncoder()
        self.scaler = StandardScaler()
        
        # Cache için
        self.user_similarity_cache = {}
        self.last_update_time = {}
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def build_neural_model(self, n_users: int, n_movies: int) -> tf.keras.Model:
        """
        Neural Collaborative Filtering modeli oluşturur
        User ve Movie embeddingleri + Similarity hesaplama katmanları
        """
        # Input layers
        user_input = tf.keras.Input(shape=(), name='user_id')
        movie_input = tf.keras.Input(shape=(), name='movie_id')
        
        # Embedding layers
        user_embedding = tf.keras.layers.Embedding(
            n_users, self.embedding_dim, 
            name='user_embedding'
        )(user_input)
        
        movie_embedding = tf.keras.layers.Embedding(
            n_movies, self.embedding_dim,
            name='movie_embedding'
        )(movie_input)
        
        # Flatten embeddings
        user_vec = tf.keras.layers.Flatten()(user_embedding)
        movie_vec = tf.keras.layers.Flatten()(movie_embedding)
        
        # Interaction layers - Deep Learning magic happens here!
        concat = tf.keras.layers.Concatenate()([user_vec, movie_vec])
        
        # Dense layers for complex interactions
        dense1 = tf.keras.layers.Dense(256, activation='relu')(concat)
        dropout1 = tf.keras.layers.Dropout(0.3)(dense1)
        
        dense2 = tf.keras.layers.Dense(128, activation='relu')(dropout1)
        dropout2 = tf.keras.layers.Dropout(0.3)(dense2)
        
        dense3 = tf.keras.layers.Dense(64, activation='relu')(dropout2)
        
        # Output layer - Rating prediction
        output = tf.keras.layers.Dense(1, activation='sigmoid', name='rating')(dense3)
        
        # Model compile
        model = tf.keras.Model(
            inputs=[user_input, movie_input], 
            outputs=output,
            name='DynamicDeepRecommender'
        )
        
        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
            loss='mse',
            metrics=['mae']
        )
        
        return model

    def load_data_from_db(self, db_path: str = "movielens_100k.db") -> pd.DataFrame:
        """Veritabanından kullanıcı-film etkileşim verisini yükler"""
        try:
            conn = sqlite3.connect(db_path)
            
            # Ana etkileşim verisini çek  
            query = """
            SELECT 
                ui.user_id,
                ui.movie_id,
                CAST(JSON_EXTRACT(ui.extra_data, '$.rating') AS FLOAT) as rating,
                ui.timestamp,
                u.age,
                u.gender,
                u.favorite_genres,
                m.genres,
                m.title
            FROM user_interactions ui
            LEFT JOIN app_users u ON ui.user_id = u.id
            LEFT JOIN movies m ON ui.movie_id = m.id
            WHERE ui.interaction_type = 'rating'
            AND ui.extra_data IS NOT NULL
            AND JSON_EXTRACT(ui.extra_data, '$.rating') IS NOT NULL
            AND CAST(JSON_EXTRACT(ui.extra_data, '$.rating') AS FLOAT) BETWEEN 1.0 AND 5.0
            ORDER BY ui.timestamp DESC
            """
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            self.logger.info(f"[+] Loaded {len(df)} interactions from database")
            return df
            
        except Exception as e:
            self.logger.error(f"[x] Database loading error: {e}")
            return pd.DataFrame()

    def prepare_training_data(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Eğitim verisi hazırlığı"""
        # User ve Movie ID'lerini encode et
        df['user_encoded'] = self.user_encoder.fit_transform(df['user_id'])
        df['movie_encoded'] = self.movie_encoder.fit_transform(df['movie_id'])
        
        # Rating normalizasyonu (0-1 arası)
        df['rating_normalized'] = df['rating'] / 5.0
        
        # Feature arrays
        users = df['user_encoded'].values
        movies = df['movie_encoded'].values
        ratings = df['rating_normalized'].values
        
        self.logger.info(f"[+] Prepared training data: {len(users)} interactions")
        self.logger.info(f"[+] Unique users: {df['user_id'].nunique()}")
        self.logger.info(f"[+] Unique movies: {df['movie_id'].nunique()}")
        
        return users, movies, ratings

    def train_model(self, retrain: bool = False):
        """Modeli eğit veya var olanı yükle"""
        
        # Veri yükleme
        df = self.load_data_from_db()
        if df.empty:
            self.logger.error("[x] No training data available!")
            return False
        
        # Training data preparation
        users, movies, ratings = self.prepare_training_data(df)
        
        n_users = len(self.user_encoder.classes_)
        n_movies = len(self.movie_encoder.classes_)
        
        # Model yükleme veya oluşturma
        if not retrain and tf.io.gfile.exists(self.model_path):
            try:
                self.model = tf.keras.models.load_model(self.model_path)
                self.logger.info(f"[+] Loaded existing model from {self.model_path}")
            except:
                retrain = True
        
        if retrain or self.model is None:
            self.logger.info("[*] Training new model...")
            self.model = self.build_neural_model(n_users, n_movies)
            
            # Model eğitimi
            history = self.model.fit(
                [users, movies], ratings,
                batch_size=1024,
                epochs=50,
                validation_split=0.2,
                verbose=1,
                callbacks=[
                    tf.keras.callbacks.EarlyStopping(patience=5, restore_best_weights=True),
                    tf.keras.callbacks.ReduceLROnPlateau(patience=3, factor=0.5)
                ]
            )
            
            # Model kaydetme
            self.model.save(self.model_path)
            self.logger.info(f"[+] Model saved to {self.model_path}")
        
        # User embeddingleri çıkar ve kaydet
        self._extract_user_embeddings()
        return True

    def _extract_user_embeddings(self):
        """Eğitilmiş modelden user embeddingleri çıkarır"""
        if self.model is None:
            self.logger.error("[x] Model not trained!")
            return
        
        # User embedding layer'ını al
        user_embedding_layer = None
        for layer in self.model.layers:
            if layer.name == 'user_embedding':
                user_embedding_layer = layer
                break
        
        if user_embedding_layer is None:
            self.logger.error("[x] User embedding layer not found!")
            return
        
        # Tüm user embeddingleri
        self.user_embeddings = user_embedding_layer.get_weights()[0]
        
        # Embeddingleri kaydet
        embedding_data = {
            'user_embeddings': self.user_embeddings,
            'user_encoder': self.user_encoder,
            'movie_encoder': self.movie_encoder
        }
        
        with open(self.embeddings_path, 'wb') as f:
            pickle.dump(embedding_data, f)
            
        self.logger.info(f"[+] User embeddings extracted: shape {self.user_embeddings.shape}")

    def find_similar_users(self, target_user_id: int, force_update: bool = False) -> List[Dict]:
        """
        Hedef kullanıcıya en benzer N kullanıcıyı bulur
        Cache kullanarak performansı artırır
        """
        
        # Cache kontrolü
        cache_key = f"user_{target_user_id}"
        if not force_update and cache_key in self.user_similarity_cache:
            cache_time = self.last_update_time.get(cache_key, datetime.min)
            if (datetime.now() - cache_time).seconds < 300:  # 5 dakika cache
                return self.user_similarity_cache[cache_key]
        
        try:
            # Target user encoding
            if target_user_id not in self.user_encoder.classes_:
                self.logger.warning(f"[!] User {target_user_id} not in training data")
                return []
            
            target_user_encoded = self.user_encoder.transform([target_user_id])[0]
            target_embedding = self.user_embeddings[target_user_encoded].reshape(1, -1)
            
            # Tüm kullanıcılarla benzerlik hesapla
            similarities = cosine_similarity(target_embedding, self.user_embeddings)[0]
            
            # En benzer kullanıcıları bul (kendisi hariç)
            similar_indices = np.argsort(similarities)[::-1][1:self.n_similar_users+1]
            
            similar_users = []
            for idx in similar_indices:
                similarity_score = similarities[idx]
                if similarity_score >= self.similarity_threshold:
                    original_user_id = self.user_encoder.inverse_transform([idx])[0]
                    similar_users.append({
                        'user_id': int(original_user_id),
                        'similarity_score': float(similarity_score),
                        'embedding_vector': self.user_embeddings[idx].tolist()
                    })
            
            # Cache güncelle
            self.user_similarity_cache[cache_key] = similar_users
            self.last_update_time[cache_key] = datetime.now()
            
            self.logger.info(f"[+] Found {len(similar_users)} similar users for user {target_user_id}")
            return similar_users
            
        except Exception as e:
            self.logger.error(f"[x] Error finding similar users: {e}")
            return []

    def get_recommendations_from_similar_users(self, 
                                             target_user_id: int, 
                                             n_recommendations: int = 10) -> List[Dict]:
        """
        Benzer kullanıcıların tercihlerine göre film önerisi üretir
        """
        
        # Benzer kullanıcıları bul
        similar_users = self.find_similar_users(target_user_id)
        
        if not similar_users:
            self.logger.warning(f"[!] No similar users found for user {target_user_id}")
            return []
        
        # Benzer kullanıcıların puanladığı filmleri topla
        conn = sqlite3.connect("movielens_100k.db")
        
        similar_user_ids = [user['user_id'] for user in similar_users]
        placeholders = ','.join(['?' for _ in similar_user_ids])
        
        # Benzer kullanıcıların yüksek puanladığı filmler
        query = f"""
        SELECT 
            ui.movie_id,
            m.title,
            m.genres,
            m.imdb_score,
            AVG(CAST(ui.interaction_data AS FLOAT)) as avg_similar_rating,
            COUNT(*) as rating_count,
            SUM(CASE WHEN CAST(ui.interaction_data AS FLOAT) >= 4.0 THEN 1 ELSE 0 END) as high_ratings
        FROM user_interactions ui
        LEFT JOIN movies m ON ui.movie_id = m.id
        WHERE ui.user_id IN ({placeholders})
        AND ui.interaction_type = 'rating'
        AND CAST(ui.interaction_data AS FLOAT) >= 3.5
        AND ui.movie_id NOT IN (
            SELECT DISTINCT movie_id 
            FROM user_interactions 
            WHERE user_id = ? 
            AND interaction_type = 'rating'
        )
        GROUP BY ui.movie_id, m.title, m.genres, m.imdb_score
        HAVING rating_count >= 2
        ORDER BY avg_similar_rating DESC, high_ratings DESC
        LIMIT ?
        """
        
        params = similar_user_ids + [target_user_id, n_recommendations * 2]
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        recommendations = []
        for _, row in df.iterrows():
            
            # Derin öğrenme modeli ile skor hesapla
            if self.model:
                try:
                    user_encoded = self.user_encoder.transform([target_user_id])[0]
                    movie_encoded = self.movie_encoder.transform([row['movie_id']])[0]
                    
                    predicted_rating = self.model.predict(
                        [np.array([user_encoded]), np.array([movie_encoded])], 
                        verbose=0
                    )[0][0] * 5.0
                    
                except:
                    predicted_rating = row['avg_similar_rating']
            else:
                predicted_rating = row['avg_similar_rating']
            
            recommendations.append({
                'movie_id': int(row['movie_id']),
                'title': row['title'],
                'genres': row['genres'].split('|') if row['genres'] else [],
                'imdb_score': float(row['imdb_score']) if pd.notna(row['imdb_score']) else 0.0,
                'predicted_rating': float(predicted_rating),
                'similar_users_avg_rating': float(row['avg_similar_rating']),
                'similar_users_count': int(row['rating_count']),
                'recommendation_source': 'similar_users_deep_learning',
                'algorithm': 'dynamic_deep_recommender'
            })
        
        # Skor sıralaması
        recommendations.sort(key=lambda x: x['predicted_rating'], reverse=True)
        
        self.logger.info(f"[+] Generated {len(recommendations)} recommendations for user {target_user_id}")
        return recommendations[:n_recommendations]

    def update_user_embedding(self, user_id: int, new_ratings: List[Dict]):
        """
        Yeni rating verildiğinde user embeddingini dinamik günceller
        new_ratings: [{'movie_id': 123, 'rating': 4.5}, ...]
        """
        
        if not new_ratings:
            return
        
        try:
            # Cache temizle
            cache_key = f"user_{user_id}"
            if cache_key in self.user_similarity_cache:
                del self.user_similarity_cache[cache_key]
            
            self.logger.info(f"[*] Updating embeddings for user {user_id} with {len(new_ratings)} new ratings")
            
            # Küçük bir re-training with new data
            # Bu gerçek zamanlı güncelleme için incremental learning yapılabilir
            # Şimdilik basit: yeni verilerle kısa eğitim
            
            users_array = []
            movies_array = []
            ratings_array = []
            
            for rating_data in new_ratings:
                if user_id in self.user_encoder.classes_ and rating_data['movie_id'] in self.movie_encoder.classes_:
                    user_encoded = self.user_encoder.transform([user_id])[0]
                    movie_encoded = self.movie_encoder.transform([rating_data['movie_id']])[0]
                    rating_normalized = rating_data['rating'] / 5.0
                    
                    users_array.append(user_encoded)
                    movies_array.append(movie_encoded)
                    ratings_array.append(rating_normalized)
            
            if users_array:
                # Mini batch update
                self.model.fit(
                    [np.array(users_array), np.array(movies_array)], 
                    np.array(ratings_array),
                    batch_size=len(users_array),
                    epochs=5,
                    verbose=0
                )
                
                # Embeddingleri tekrar çıkar
                self._extract_user_embeddings()
                
                self.logger.info(f"[+] User {user_id} embeddings updated successfully")
            
        except Exception as e:
            self.logger.error(f"[x] Error updating user embedding: {e}")

# Test ve kullanım örneği
if __name__ == "__main__":
    recommender = DynamicDeepRecommender()
    
    # Model eğitimi
    print("[*] Training model...")
    recommender.train_model(retrain=False)
    
    # Test kullanıcısı için benzer kullanıcıları bul
    test_user_id = 1
    print(f"\n[*] Finding similar users for user {test_user_id}...")
    similar_users = recommender.find_similar_users(test_user_id)
    
    for user in similar_users[:5]:
        print(f"   User {user['user_id']}: {user['similarity_score']:.3f}")
    
    # Film önerileri al
    print(f"\n[*] Getting recommendations for user {test_user_id}...")
    recommendations = recommender.get_recommendations_from_similar_users(test_user_id, 5)
    
    for rec in recommendations:
        print(f"   {rec['title']} - Predicted: {rec['predicted_rating']:.2f}")
    
    # Dinamik güncelleme testi
    print(f"\n[*] Testing dynamic update...")
    new_ratings = [{'movie_id': 50, 'rating': 5.0}]
    recommender.update_user_embedding(test_user_id, new_ratings)
    
    print("[+] Dynamic Deep Recommender system ready!")
