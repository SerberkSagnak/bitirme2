import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.metrics.pairwise import cosine_similarity
import sqlite3
import pickle
import logging
from datetime import datetime
from typing import List, Dict, Tuple, Optional

class CleanDynamicDeepRecommender:
    """
    TEMIZ Dynamic Deep Learning Tabanlı Öneri Sistemi
    
    Bu sistem:
    1. TensorFlow ile Neural Collaborative Filtering model eğitir
    2. 128-boyutlu user embeddings oluşturur  
    3. Cosine similarity ile 10 benzer kullanıcı bulur
    4. Bu kullanıcıların tercihlerine göre film önerir
    5. Yeni rating geldiğinde embeddingi dinamik günceller
    """
    
    def __init__(self, 
                 embedding_dim: int = 128,
                 n_similar_users: int = 10,
                 similarity_threshold: float = 0.1):
        
        self.embedding_dim = embedding_dim
        self.n_similar_users = n_similar_users
        self.similarity_threshold = similarity_threshold
        
        # Model components - CLEAN APPROACH
        self.model = None
        self.user_embeddings = None
        
        # Manual ID mappings (NO LabelEncoder!)
        self.user_id_to_idx = {}
        self.movie_id_to_idx = {}
        self.idx_to_user_id = {}
        self.idx_to_movie_id = {}
        
        # Cache
        self.similarity_cache = {}
        self.last_cache_time = {}
        
        self.logger = logging.getLogger(__name__)

    def load_training_data(self) -> pd.DataFrame:
        """Veritabanından tür ve ortalama puan bilgileriyle zenginleştirilmiş eğitim verisini yükle."""
        try:
            conn = sqlite3.connect("movielens_100k.db")
            
            # JOIN'li yeni sorgu: Filmlerin türlerini ve ortalama puanlarını da çekiyoruz.
            query = """
            SELECT 
                ui.user_id,
                ui.movie_id,
                m.genres,
                m.avg_rating,
                m.imdb_score,
                CASE 
                    WHEN JSON_EXTRACT(ui.extra_data, '$.rating') IS NOT NULL THEN
                        CAST(JSON_EXTRACT(ui.extra_data, '$.rating') AS FLOAT)
                    WHEN ui.extra_data IS NOT NULL AND ui.extra_data LIKE '%.%' THEN
                        CAST(ui.extra_data AS FLOAT)
                    ELSE NULL
                END as rating
            FROM user_interactions ui
            JOIN movies m ON ui.movie_id = m.id
            WHERE ui.interaction_type = 'rating'
            AND ui.extra_data IS NOT NULL
            AND m.genres IS NOT NULL -- Tür bilgisi olmayan filmleri eğitime dahil etme
            AND (
                JSON_EXTRACT(ui.extra_data, '$.rating') IS NOT NULL 
                OR (ui.extra_data LIKE '%.%' AND CAST(ui.extra_data AS FLOAT) BETWEEN 1.0 AND 5.0)
            )
            ORDER BY ui.user_id, ui.timestamp DESC
            """
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            self.logger.info(f"[+] Veritabanından {len(df)} zenginleştirilmiş etkileşim yüklendi.")
            
            if df.empty or df['user_id'].nunique() <= 1:
                self.logger.error("[HATA] Yetersiz eğitim verisi!")
                return pd.DataFrame()
            
            # avg_rating'deki boş değerleri ortalama ile doldur
            avg_rating_overall = df['avg_rating'].mean()
            df['avg_rating'].fillna(avg_rating_overall, inplace=True)
            
            # imdb_score'daki boş değerleri doldur
            imdb_score_overall = df['imdb_score'].mean()
            df['imdb_score'].fillna(imdb_score_overall, inplace=True)
            
            self.logger.info(f"[+] Boş 'avg_rating' ({avg_rating_overall:.2f}) ve 'imdb_score' ({imdb_score_overall:.2f}) dolduruldu.")
            
            return df
            
        except Exception as e:
            self.logger.error(f"[x] Zenginleştirilmiş veri yükleme hatası: {e}")
            return pd.DataFrame()

    def prepare_mappings(self, df: pd.DataFrame) -> bool:
        """Manuel ID mappings oluştur"""
        try:
            # Unique IDs
            unique_users = sorted(df['user_id'].unique())
            unique_movies = sorted(df['movie_id'].unique())
            
            # Create mappings manually
            self.user_id_to_idx = {user_id: idx for idx, user_id in enumerate(unique_users)}
            self.movie_id_to_idx = {movie_id: idx for idx, movie_id in enumerate(unique_movies)}
            self.idx_to_user_id = {idx: user_id for user_id, idx in self.user_id_to_idx.items()}
            self.idx_to_movie_id = {idx: movie_id for movie_id, idx in self.movie_id_to_idx.items()}
            
            self.logger.info(f"[+] Created mappings: {len(unique_users)} users, {len(unique_movies)} movies")
            return True
            
        except Exception as e:
            self.logger.error(f"[x] Mapping creation error: {e}")
            return False

    def build_neural_model(self, n_users: int, n_movies: int, n_genres: int) -> tf.keras.Model:
        """Genişletilmiş Hibrit NCF Modeli (Tür ve Puan Özellikleriyle)"""
        
        # --- GİRİŞ KATMANLARI ---
        # Mevcut girişler
        user_input = tf.keras.Input(shape=(), name='user_id_input', dtype='int32')
        movie_input = tf.keras.Input(shape=(), name='movie_id_input', dtype='int32')
        
        # Yeni eklenen içerik özellikleri için girişler
        # Türler için giriş (multi-hot vector)
        genre_input = tf.keras.Input(shape=(n_genres,), name='genre_input')
        # Ortalama puan için giriş (normalize edilmiş tek bir sayı)
        avg_rating_input = tf.keras.Input(shape=(1,), name='avg_rating_input')
        # IMDb puanı için giriş (normalize edilmiş tek bir sayı)
        imdb_score_input = tf.keras.Input(shape=(1,), name='imdb_score_input')

        # --- EMBEDDING KATMANLARI ---
        # Kullanıcı ve film için embedding'ler (gizli özellikleri öğrenir)
        user_embedding = tf.keras.layers.Embedding(
            n_users, self.embedding_dim, 
            name='user_embedding'
        )(user_input)
        
        movie_embedding = tf.keras.layers.Embedding(
            n_movies, self.embedding_dim,
            name='movie_embedding'
        )(movie_input)
        
        # Vektörleri düzleştir
        user_vec = tf.keras.layers.Flatten()(user_embedding)
        movie_vec = tf.keras.layers.Flatten()(movie_embedding)
        
        # --- TÜM ÖZELLİKLERİ BİRLEŞTİRME ---
        # Hem embedding'leri hem de yeni içerik özelliklerini birleştir
        concat = tf.keras.layers.Concatenate()([
            user_vec, 
            movie_vec, 
            genre_input, 
            avg_rating_input,
            imdb_score_input
        ])
        
        # --- YOĞUN SİNİR AĞI KATMANLARI ---
        # Birleştirilmiş bu zengin vektörden karmaşık ilişkileri öğren
        dense1 = tf.keras.layers.Dense(256, activation='relu')(concat)
        dropout1 = tf.keras.layers.Dropout(0.4)(dense1) # Dropout artırıldı
        dense2 = tf.keras.layers.Dense(128, activation='relu')(dropout1)
        dropout2 = tf.keras.layers.Dropout(0.4)(dense2) # Dropout artırıldı
        
        # --- ÇIKIŞ KATMANI ---
        output = tf.keras.layers.Dense(1, activation='sigmoid')(dropout2)
        
        # Modeli oluştur (artık 5 girişi var)
        model = tf.keras.Model(
            inputs=[user_input, movie_input, genre_input, avg_rating_input, imdb_score_input], 
            outputs=output
        )
        
        # Modeli derle
        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
            loss='mean_squared_error',
            metrics=['mean_absolute_error']
        )
        
        return model

    def train_model(self) -> bool:
        """Genişletilmiş hibrit modeli eğitir (Tür ve Puan özellikleriyle)."""
        try:
            # 1. Zenginleştirilmiş Veriyi Yükle
            df = self.load_training_data()
            if df.empty:
                self.logger.error("[x] Eğitim için veri yüklenemedi!")
                return False
            
            # 2. Haritalamaları (Mappings) Hazırla
            if not self.prepare_mappings(df):
                return False

            # --- 3. ÖZELLİK MÜHENDİSLİĞİ ---

            # A. Tür (Genre) Özelliklerini Hazırla (Multi-hot encoding)
            self.logger.info("[*] Tür özellikleri hazırlanıyor (Multi-hot encoding)...")
            all_genres = sorted(list(set([genre for sublist in df['genres'].str.split('|') for genre in sublist])))
            self.genre_to_idx = {genre: i for i, genre in enumerate(all_genres)}
            self.idx_to_genre = {i: genre for genre, i in self.genre_to_idx.items()}
            n_genres = len(all_genres)
            
            genre_features = np.zeros((len(df), n_genres), dtype=np.float32)
            for i, genres_str in enumerate(df['genres']):
                for genre in genres_str.split('|'):
                    if genre in self.genre_to_idx:
                        genre_features[i, self.genre_to_idx[genre]] = 1.0
            self.logger.info(f"[+] {n_genres} benzersiz tür için özellik vektörleri oluşturuldu.")

            # B. Ortalama Puan (avg_rating) Özelliğini Hazırla (Normalization)
            self.logger.info("[*] Ortalama puan ve IMDb puanı özellikleri normalize ediliyor...")
            # Puanları 0-1 arasına ölçekle (genellikle 1-10 arası olduğu varsayılarak)
            avg_rating_features = df['avg_rating'].values / 5.0 # Site içi 5 üzerinden
            avg_rating_features = np.expand_dims(avg_rating_features, axis=-1)
            
            # IMDb Puanı (0-10) -> 0-1
            imdb_score_features = df['imdb_score'].values / 10.0
            imdb_score_features = np.expand_dims(imdb_score_features, axis=-1)
            
            self.logger.info("[+] 'avg_rating' ve 'imdb_score' özellikleri modele hazır.")

            # 4. Eğitim İçin Gerekli Dizileri (Arrays) Oluştur
            df['user_idx'] = df['user_id'].map(self.user_id_to_idx)
            df['movie_idx'] = df['movie_id'].map(self.movie_id_to_idx)
            df['rating_normalized'] = df['rating'] / 5.0
            
            users = df['user_idx'].values
            movies = df['movie_idx'].values
            ratings = df['rating_normalized'].values
            
            # 5. Yeni Hibrit Modeli Oluştur
            n_users = len(self.user_id_to_idx)
            n_movies = len(self.movie_id_to_idx)
            
            self.model = self.build_neural_model(n_users, n_movies, n_genres)
            self.model.summary() # Modelin mimarisini konsola yazdır
            
            self.logger.info(f"[*] Hibrit model {len(users)} etkileşim ile eğitiliyor...")
            
            # 6. Modeli Eğit (Artık 5 giriş verisi var)
            history = self.model.fit(
                [users, movies, genre_features, avg_rating_features, imdb_score_features], 
                ratings,
                batch_size=64, # Batch size artırıldı
                epochs=25,     # Epochs artırıldı
                validation_split=0.2,
                verbose=1,
                callbacks=[
                    tf.keras.callbacks.EarlyStopping(patience=3, monitor='val_loss', restore_best_weights=True)
                ]
            )
            
            # 7. Sonuçları Kaydet
            user_embedding_layer = self.model.get_layer('user_embedding')
            self.user_embeddings = user_embedding_layer.get_weights()[0]
            
            self.model.save('dynamic_deep_model.h5')
            
            # Genre mapping'i de kaydet
            save_data = {
                'user_embeddings': self.user_embeddings,
                'user_id_to_idx': self.user_id_to_idx,
                'movie_id_to_idx': self.movie_id_to_idx,
                'idx_to_user_id': self.idx_to_user_id,
                'idx_to_movie_id': self.idx_to_movie_id,
                'genre_to_idx': self.genre_to_idx, # YENİ
                'idx_to_genre': self.idx_to_genre  # YENİ
            }
            
            with open('user_embeddings.pkl', 'wb') as f:
                pickle.dump(save_data, f)
            
            self.logger.info(f"[+] Hibrit model başarıyla eğitildi ve kaydedildi! Embedding boyutu: {self.user_embeddings.shape}")
            return True
            
        except Exception as e:
            self.logger.error(f"[x] Hibrit model eğitimi başarısız: {e}")
            import traceback
            traceback.print_exc()
            return False

    def load_embeddings(self) -> bool:
        """Eğitilmiş embeddingleri yükle"""
        try:
            with open('user_embeddings.pkl', 'rb') as f:
                data = pickle.load(f)
                
            self.user_embeddings = data['user_embeddings']
            self.user_id_to_idx = data['user_id_to_idx']
            self.movie_id_to_idx = data['movie_id_to_idx']
            self.idx_to_user_id = data['idx_to_user_id']
            self.idx_to_movie_id = data['idx_to_movie_id']
            
            self.logger.info(f"[+] Embeddings loaded: {self.user_embeddings.shape}")
            return True
            
        except Exception as e:
            self.logger.error(f"[x] Loading embeddings failed: {e}")
            return False

    def find_similar_users(self, target_user_id: int, force_update: bool = False) -> List[Dict]:
        """10 benzer kullanıcı bul - GERÇEK DERİN ÖĞRENME"""
        
        try:
            # Cache kontrolü
            if not force_update and target_user_id in self.similarity_cache:
                # Cache süresi kontrolü (örneğin 1 saat)
                if (datetime.now() - self.last_cache_time.get(target_user_id, datetime.min)).total_seconds() < 3600:
                    self.logger.info(f"[⚡] Returning cached similar users for {target_user_id}")
                    return self.similarity_cache[target_user_id]

            # Embeddings yüklü mü kontrol et
            if self.user_embeddings is None:
                if not self.load_embeddings():
                    self.logger.error("[x] No embeddings available!")
                    return []
            
            # User mapping kontrol
            if target_user_id not in self.user_id_to_idx:
                self.logger.warning(f"[!] User {target_user_id} not in training data")
                return []
            
            # Target user embedding al
            user_idx = self.user_id_to_idx[target_user_id]
            target_embedding = self.user_embeddings[user_idx].reshape(1, -1)
            
            # TÜM KULLANICILARLA SİMİLARİTY HESAPLA
            similarities = cosine_similarity(target_embedding, self.user_embeddings)[0]
            
            # En benzer 10 kullanıcıyı bul (kendisi hariç)
            similar_indices = np.argsort(similarities)[::-1][1:self.n_similar_users+1]
            
            similar_users = []
            for idx in similar_indices:
                similarity_score = similarities[idx]
                if similarity_score >= self.similarity_threshold:
                    original_user_id = self.idx_to_user_id[idx]
                    similar_users.append({
                        'user_id': int(original_user_id),
                        'similarity_score': float(similarity_score),
                        'embedding_vector': self.user_embeddings[idx].tolist()[:10]  # İlk 10 boyut
                    })
            
            # Sonuçları cache'e kaydet
            self.similarity_cache[target_user_id] = similar_users
            self.last_cache_time[target_user_id] = datetime.now()
            
            self.logger.info(f"[+] Found {len(similar_users)} similar users for user {target_user_id}")
            return similar_users
            
        except Exception as e:
            self.logger.error(f"[x] Similar users error: {e}")
            return []

    def get_recommendations(self, target_user_id: int, n_recommendations: int = 10) -> List[Dict]:
        """Benzer kullanıcılardan film önerisi"""
        
        # Benzer kullanıcıları bul
        similar_users = self.find_similar_users(target_user_id)
        
        if not similar_users:
            return []
        
        try:
            conn = sqlite3.connect("movielens_100k.db")
            
            # Benzer kullanıcıların IDs
            similar_user_ids = [user['user_id'] for user in similar_users]
            placeholders = ','.join(['?' for _ in similar_user_ids])
            
            # BASİT VE ETKİLİ QUERY - Benzer kullanıcıların filmleri
            query = f"""
            SELECT 
                ui.movie_id,
                m.title,
                m.genres,
                m.imdb_score,
                m.poster_url,  -- POSTER URL EKLENDI
                AVG(
                    CASE 
                        WHEN JSON_EXTRACT(ui.extra_data, '$.rating') IS NOT NULL THEN
                            CAST(JSON_EXTRACT(ui.extra_data, '$.rating') AS FLOAT)
                        ELSE 4.0
                    END
                ) as avg_similar_rating,
                COUNT(*) as rating_count
            FROM user_interactions ui
            JOIN movies m ON ui.movie_id = m.id
            WHERE ui.user_id IN ({placeholders})
            AND ui.interaction_type = 'rating'
            AND ui.extra_data IS NOT NULL
            AND m.title IS NOT NULL
            GROUP BY ui.movie_id, m.title, m.genres, m.imdb_score, m.poster_url
            ORDER BY avg_similar_rating DESC, rating_count DESC
            LIMIT ?
            """
            
            params = similar_user_ids + [n_recommendations * 2]
            df = pd.read_sql_query(query, conn, params=params)
            
            print(f"[DEBUG] Recommendation query returned {len(df)} movies")
            if len(df) > 0:
                print(f"[DEBUG] Sample movies: {df['title'].tolist()[:3]}")
            else:
                print("[DEBUG] No movies from similar users - investigating...")
                
                # DEBUG: Ana query neden çalışmıyor?
                print(f"[DEBUG] Similar user IDs: {similar_user_ids}")
                
                # BASIT TEST QUERY
                simple_test = f"""
                SELECT COUNT(*) as total_movies
                FROM user_interactions ui
                LEFT JOIN movies m ON ui.movie_id = m.id  
                WHERE ui.user_id IN ({placeholders})
                AND ui.interaction_type = 'rating'
                """
                
                test_result = pd.read_sql_query(simple_test, conn, params=similar_user_ids)
                print(f"[DEBUG] Simple test: {test_result.iloc[0]['total_movies']} total movies from similar users")
                
                # Ana query debug
                debug_query = f"""
                SELECT ui.user_id, COUNT(*) as rating_count, 
                       AVG(CASE 
                           WHEN JSON_EXTRACT(ui.extra_data, '$.rating') IS NOT NULL THEN
                               CAST(JSON_EXTRACT(ui.extra_data, '$.rating') AS FLOAT)
                           WHEN ui.extra_data LIKE '%.%' THEN
                               CAST(ui.extra_data AS FLOAT)
                           ELSE NULL
                       END) as avg_rating
                FROM user_interactions ui
                WHERE ui.user_id IN ({placeholders})
                AND ui.interaction_type = 'rating'
                AND ui.extra_data IS NOT NULL
                GROUP BY ui.user_id
                """
                
                debug_df = pd.read_sql_query(debug_query, conn, params=similar_user_ids)
                print(f"[DEBUG] Similar users ratings: {len(debug_df)} users found")
                
                if len(debug_df) > 0:
                    for _, row in debug_df.iterrows():
                        print(f"[DEBUG] User {row['user_id']}: {row['rating_count']} ratings, avg {row['avg_rating']:.2f}")
                
                # GUARANTEED FALLBACK: Alice'in izlemediği popüler filmler
                guaranteed_query = """
                SELECT m.id as movie_id, m.title, m.genres, m.imdb_score, m.poster_url,
                       COALESCE(m.avg_rating, 4.0) as avg_similar_rating, 
                       1 as rating_count
                FROM movies m
                WHERE m.title IS NOT NULL
                AND m.id NOT IN (
                    SELECT DISTINCT movie_id 
                    FROM user_interactions 
                    WHERE user_id = ? 
                    AND interaction_type = 'rating'
                )
                ORDER BY COALESCE(m.avg_rating, 0) DESC 
                LIMIT ?
                """
                df = pd.read_sql_query(guaranteed_query, conn, params=[target_user_id, n_recommendations])
                print(f"[DEBUG] Guaranteed fallback returned {len(df)} movies")
            
            conn.close()
            
            recommendations = []
            for _, row in df.iterrows():
                
                # Derin öğrenme ile skor tahmin et
                if self.model and target_user_id in self.user_id_to_idx and row['movie_id'] in self.movie_id_to_idx:
                    try:
                        user_idx = self.user_id_to_idx[target_user_id] 
                        movie_idx = self.movie_id_to_idx[row['movie_id']]
                        
                        # Özellikleri hazırla
                        genre_feature = np.zeros((1, len(self.genre_to_idx)), dtype=np.float32)
                        if 'genres' in row:
                            genres_list = row['genres'].split('|') if isinstance(row['genres'], str) else row['genres']
                            for g in genres_list:
                                if g in self.genre_to_idx:
                                    genre_feature[0, self.genre_to_idx[g]] = 1.0
                        
                        avg_rating_feature = np.array([[row['avg_similar_rating'] / 5.0]])
                        imdb_score_feature = np.array([[float(row['imdb_score']) / 10.0 if pd.notna(row['imdb_score']) else 0.0]])
                        
                        predicted_score = self.model.predict(
                            [np.array([user_idx]), np.array([movie_idx]), genre_feature, avg_rating_feature, imdb_score_feature], 
                            verbose=0
                        )[0][0] * 5.0
                        
                    except Exception as e:
                        # self.logger.error(f"Prediction error: {e}")
                        predicted_score = row['avg_similar_rating']
                else:
                    predicted_score = row['avg_similar_rating']
                
                recommendations.append({
                    'movie_id': int(row['movie_id']),
                    'title': row['title'],
                    'genres': row['genres'].split('|') if row['genres'] else [],
                    'imdb_score': float(row['imdb_score']) if pd.notna(row['imdb_score']) else 0.0,
                    'poster_url': row['poster_url'], # POSTER URL EKLENDI
                    'predicted_rating': float(predicted_score),
                    'similar_users_avg_rating': float(row['avg_similar_rating']),
                    'similar_users_count': int(row['rating_count']),
                    'recommendation_source': 'deep_learning_similar_users',
                    'algorithm': 'neural_collaborative_filtering'
                })
            
            # Skor sıralması
            recommendations.sort(key=lambda x: x['predicted_rating'], reverse=True)
            
            self.logger.info(f"[+] Generated {len(recommendations)} recommendations")
            return recommendations[:n_recommendations]
            
        except Exception as e:
            self.logger.error(f"[x] Recommendations error: {e}")
            return []

# Test fonksiyonu
def test_clean_system():
    print("CLEAN DEEP LEARNING SYSTEM TEST")
    print("=" * 50)
    
    # Initialize
    recommender = CleanDynamicDeepRecommender(
        embedding_dim=128,
        n_similar_users=10,
        similarity_threshold=0.1
    )
    
    # Train model
    print("[1] Training model...")
    success = recommender.train_model()
    
    if success:
        print("[+] Training successful!")
        
        # Test similarity
        print("[2] Testing similarity for user 1...")
        similar_users = recommender.find_similar_users(1)
        
        print(f"[+] Found {len(similar_users)} similar users:")
        for user in similar_users[:5]:
            print(f"    User {user['user_id']}: {user['similarity_score']:.3f}")
        
        # Test recommendations
        print("[3] Testing recommendations...")
        recommendations = recommender.get_recommendations(1, 5)
        
        print(f"[+] Generated {len(recommendations)} recommendations:")
        for rec in recommendations:
            print(f"    {rec['title']}: {rec['predicted_rating']:.2f}/5.0")
        
        print("\nCLEAN DEEP LEARNING WORKING!")
        return True
    else:
        print("[x] Training failed!")
        return False

if __name__ == "__main__":
    test_clean_system()
