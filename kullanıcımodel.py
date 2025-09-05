import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD, NMF
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.cluster import KMeans
import sqlite3
import pickle
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


class AdvancedRecommendationSystem:
    def __init__(self):
        """Initialize the recommendation system"""
        # Model bilesenleri
        self.user_similarity = None
        self.item_similarity = None
        self.content_similarity = None
        self.svd_model = None
        self.nmf_model = None
        self.user_clusters = None
        self.item_clusters = None
        # Veri
        self.user_item_matrix = None
        self.movies_df = None
        self.users_df = None
        self.ratings_df = None

        # Feature matrices
        self.user_features = None
        self.item_features = None

        # Scalers
        self.user_scaler = StandardScaler()
        self.item_scaler = StandardScaler()

        # Hyperparameters
        self.alpha_collaborative = 0.4  # Collaborative filtering agirligi
        self.alpha_content = 0.3        # Content-based agirligi
        self.alpha_demographic = 0.2    # Demographic agirligi
        self.alpha_popularity = 0.1     # Popularity agirligi

        # Temporal decay factor
        self.temporal_decay = 0.95

    def load_and_prepare_data(self):
        """Gelistirilmis veri hazirlama"""
        print("[*] ADVANCED VERI HAZIRLAMA BASLADI...")

        conn = sqlite3.connect('movielens_100k.db')

        # Ratings with temporal info
        ratings_query = """
SELECT r.user_id, r.movie_id, r.rating, r.timestamp, r.created_at,
       u.age, u.gender, u.favorite_genres,
       m.title, m.genres, m.avg_rating, m.release_date
FROM ratings r
JOIN app_users u ON r.user_id = u.id
JOIN movies m ON r.movie_id = m.id
WHERE r.user_type = 'app'
ORDER BY r.timestamp DESC
"""

        self.ratings_df = pd.read_sql_query(ratings_query, conn)

        # Movies with detailed features
        movies_query = """
SELECT id, title, genres, avg_rating, release_date,
       rating_count, imdb_url
FROM movies
"""


        self.movies_df = pd.read_sql_query(movies_query, conn)

        # Users with preferences
        users_query = """
        SELECT id, username, age, gender, favorite_genres, created_at, last_active
        FROM app_users
        """
        self.users_df = pd.read_sql_query(users_query, conn)

        conn.close()

        # Temporal weighting (son rating'ler daha onemli)
        self.ratings_df['days_ago'] = (datetime.now() - pd.to_datetime(self.ratings_df['created_at'])).dt.days
        self.ratings_df['temporal_weight'] = self.temporal_decay ** (self.ratings_df['days_ago'] / 30)
        self.ratings_df['weighted_rating'] = self.ratings_df['rating'] * self.ratings_df['temporal_weight']

        # User-Item Matrix (weighted)
        self.user_item_matrix = self.ratings_df.pivot_table(
            index='user_id',
            columns='movie_id',
            values='weighted_rating',
            fill_value=0
        )

        print(f"[*] Veri Istatistikleri:")
        print(f"   [+] Kullanici: {len(self.users_df)}")
        print(f"   [+] Film: {len(self.movies_df)}")
        print(f"   [+] Rating: {len(self.ratings_df)}")
        print(f"   [*] Matrix: {self.user_item_matrix.shape}")
        print(f"   [+] Temporal Weighting: Aktif")

        # Feature engineering
        self._create_user_features()
        self._create_item_features()

        print("[+] Gelistirilmis veri hazirlama tamamlandi!")

    def _create_user_features(self):
        """Kullanici ozellik matrisi olustur"""
        print("[+] Kullanici ozellikleri olusturuluyor...")

        user_features = []

        for user_id in self.user_item_matrix.index:
            user_info = self.users_df[self.users_df['id'] == user_id].iloc[0]
            user_ratings = self.user_item_matrix.loc[user_id]

            # Demografik ozellikler
            age = user_info['age'] if pd.notna(user_info['age']) else 30
            gender_m = 1 if user_info['gender'] == 'M' else 0
            gender_f = 1 if user_info['gender'] == 'F' else 0

            # Rating davranislari
            avg_rating = user_ratings[user_ratings > 0].mean() if (user_ratings > 0).any() else 3.0
            rating_count = (user_ratings > 0).sum()
            rating_std = user_ratings[user_ratings > 0].std() if (user_ratings > 0).sum() > 1 else 1.0

            # Tur tercihleri (one-hot encoding)
            fav_genres = user_info['favorite_genres'].split(',') if pd.notna(user_info['favorite_genres']) else []
            genre_features = self._encode_genres(fav_genres)

            # Aktivite ozellikleri
            account_age = (datetime.now() - pd.to_datetime(user_info['created_at'])).days

            features = [
                age, gender_m, gender_f, avg_rating, rating_count, rating_std, account_age
            ] + genre_features

            user_features.append(features)

        self.user_features = np.array(user_features)
        self.user_features = self.user_scaler.fit_transform(self.user_features)

        print(f"[+] Kullanici features: {self.user_features.shape}")
        
    def _encode_genres(self, genres):
        """Tur encoding (one-hot)"""
        all_genres = [
            'Action', 'Adventure', 'Animation', 'Children', 'Comedy', 'Crime',
            'Documentary', 'Drama', 'Fantasy', 'Film-Noir', 'Horror', 'Musical',
            'Mystery', 'Romance', 'Sci-Fi', 'Thriller', 'War', 'Western'
        ]
        return [1 if genre.strip() in genres else 0 for genre in all_genres]



    def _create_item_features(self):
        """Film ozellik matrisi olustur"""
        print("[+] Film ozellikleri olusturuluyor...")

        # TF-IDF for genres
        tfidf = TfidfVectorizer(max_features=50)
        genre_matrix = tfidf.fit_transform(self.movies_df['genres'].fillna(''))

        # Numerical features
        numerical_features = []
        for _, movie in self.movies_df.iterrows():
            avg_rating = movie['avg_rating'] if pd.notna(movie['avg_rating']) else 3.0

            # Release year
            try:
                release_year = int(movie['release_date'].split('-')[0]) if pd.notna(movie['release_date']) else 1990
            except:
                release_year = 1990

            age_of_movie = 2024 - release_year

            numerical_features.append([avg_rating, age_of_movie])

        numerical_features = np.array(numerical_features)
        numerical_features = self.item_scaler.fit_transform(numerical_features)

        # Combine features
        self.item_features = np.hstack([genre_matrix.toarray(), numerical_features])

        print(f"[+] Film features: {self.item_features.shape}")



    def _encode_genres(self, genres):
        """Tur encoding (one-hot)"""
        all_genres = ['Action', 'Adventure', 'Animation', 'Children', 'Comedy', 'Crime',
                      'Documentary', 'Drama', 'Fantasy', 'Film-Noir', 'Horror', 'Musical',
                      'Mystery', 'Romance', 'Sci-Fi', 'Thriller', 'War', 'Western']

        return [1 if genre.strip() in genres else 0 for genre in all_genres]

    def train_all_models(self):
        """Tum modelleri egit"""
        print("[*] TUM MODELLERI EGITIYOR...")

        # 1. Collaborative Filtering
        self._train_collaborative()

        # 2. Content-Based
        self._train_content_based()

        # 3. Matrix Factorization
        self._train_matrix_factorization()

        # 4. Clustering
        self._train_clustering()

        print("[+] Tum modeller egitildi!")

    def _train_collaborative(self):
        """Gelistirilmis Collaborative Filtering"""
        print("[*] Collaborative Filtering egitiliyor...")

        # User similarity (cosine +pearson hybrid)
        user_matrix = self.user_item_matrix.values

        # Cosine similarity
        cosine_sim = cosine_similarity(user_matrix)

        # Pearson correlation
        user_df = pd.DataFrame(user_matrix)
        pearson_sim = user_df.T.corr().fillna(0).values

        # Hybrid similarity
        self.user_similarity = 0.7 * cosine_sim + 0.3 * pearson_sim

        # Item similarity
        item_matrix = self.user_item_matrix.T.values
        self.item_similarity = cosine_similarity(item_matrix)

        print("[+] Collaborative Filtering egitildi!")

    def _train_content_based(self):
        """Content-Based Filtering"""
        print("[*] Content-Based Filtering egitiliyor...")

        # Film icerik benzerligi
        self.content_similarity = cosine_similarity(self.item_features)

        print("[+] Content-Based Filtering egitildi!")

    def _train_matrix_factorization(self):
        """Matrix Factorization (SVD + NMF)"""
        print("[*] Matrix Factorization egitiliyor...")

        # SVD
        self.svd_model = TruncatedSVD(n_components=50, random_state=42)
        self.svd_model.fit(self.user_item_matrix)

        # NMF (Non-negative Matrix Factorization)
        self.nmf_model = NMF(n_components=30, random_state=42, max_iter=200)
        self.nmf_model.fit(self.user_item_matrix)

        print("[+] Matrix Factorization egitildi!")

    def _train_clustering(self):
        """Kullanici ve Film Clustering"""
        print("[*] Clustering egitiliyor...")

        # User clustering
        user_kmeans = KMeans(n_clusters=10, random_state=42)
        self.user_clusters = user_kmeans.fit_predict(self.user_features)

        # Item clustering  
        item_kmeans = KMeans(n_clusters=15, random_state=42)
        self.item_clusters = item_kmeans.fit_predict(self.item_features)

        print("[+] Clustering egitildi!")

    def get_hybrid_recommendations(self, user_id, n_recommendations=20,
                                   diversity_factor=0.3, novelty_factor=0.2):
        """Gelistirilmis Hybrid Oneriler"""
        print(f"[*] {user_id} icin hybrid oneriler hesaplaniyor...")

        if self.user_item_matrix is None:
            print("[!] HATA: user_item_matrix yuklenmemis. Cold start onerileri kullaniliyor.")
            return self._cold_start_recommendations(user_id, n_recommendations)

        if user_id not in self.user_item_matrix.index:
            return self._cold_start_recommendations(user_id, n_recommendations)

        # 1. Collaborative Filtering Scores
        collab_scores = self._get_collaborative_scores(user_id)

        # 2. Content-Based Scores
        content_scores = self._get_content_scores(user_id)

        # 3. Demographic Scores
        demo_scores = self._get_demographic_scores(user_id)

        # 4. Popularity Scores
        pop_scores = self._get_popularity_scores()

        # 5. Matrix Factorization Scores
        mf_scores = self._get_matrix_factorization_scores(user_id)

        # Hybrid combination
        final_scores = {}
        all_movies = set(collab_scores.keys()) | set(content_scores.keys()) | \
                     set(demo_scores.keys()) | set(pop_scores.keys()) | set(mf_scores.keys())

        for movie_id in all_movies:
            score = (
                self.alpha_collaborative * collab_scores.get(movie_id, 0) +
                self.alpha_content * content_scores.get(movie_id, 0) +
                self.alpha_demographic * demo_scores.get(movie_id, 0) +
                self.alpha_popularity * pop_scores.get(movie_id, 0) +
                0.1 * mf_scores.get(movie_id, 0)  # Matrix factorization bonus
            )

            # Diversity boost
            if diversity_factor > 0:
                score += diversity_factor * self._get_diversity_score(user_id, movie_id)

            # Novelty boost  
            if novelty_factor > 0:
                score += novelty_factor * self._get_novelty_score(movie_id)

            final_scores[movie_id] = score

        # Confidence scoring
        recommendations_with_confidence = []
        for movie_id, score in sorted(final_scores.items(), key=lambda x: x[1], reverse=True):
            confidence = self._calculate_confidence(user_id, movie_id, score)

            movie_info = self.movies_df[self.movies_df['id'] == movie_id].iloc[0]

            recommendations_with_confidence.append({
                'movie_id': movie_id,
                'title': movie_info['title'],
                'genres': movie_info['genres'],
                'predicted_rating': min(5.0, max(1.0, score)),
                'confidence': confidence,
                'hybrid_score': score,
                'avg_rating': movie_info['avg_rating'],
            })

        return recommendations_with_confidence[:n_recommendations]

    def _get_collaborative_scores(self, user_id):
        """Collaborative Filtering skorlari"""
        user_idx = list(self.user_item_matrix.index).index(user_id)
        user_similarities = self.user_similarity[user_idx]
        user_ratings = self.user_item_matrix.iloc[user_idx]

        # En benzer 20 kullanici
        similar_users = np.argsort(user_similarities)[::-1][1:21]

        scores = {}
        for movie_id in self.user_item_matrix.columns:
            if user_ratings[movie_id] == 0:  # Izlemedigi filmler
                movie_idx = list(self.user_item_matrix.columns).index(movie_id)

                weighted_score = 0
                similarity_sum = 0

                for similar_user_idx in similar_users:
                    similarity = user_similarities[similar_user_idx]
                    rating = self.user_item_matrix.iloc[similar_user_idx, movie_idx]

                    if rating > 0 and similarity > 0.1:  # Minimum similarity threshold
                        weighted_score += similarity * rating
                        similarity_sum += similarity

                if similarity_sum > 0:
                    scores[movie_id] = weighted_score / similarity_sum

        return scores

    def _get_content_scores(self, user_id):
        """Content-Based skorlari"""
        user_ratings = self.user_item_matrix.loc[user_id]
        liked_movies = user_ratings[user_ratings >= 4].index  # Begendigi filmler

        scores = {}

        for liked_movie_id in liked_movies:
            if liked_movie_id in self.movies_df['id'].values:
                movie_idx = self.movies_df[self.movies_df['id'] == liked_movie_id].index[0]
                movie_similarities = self.content_similarity[movie_idx]

                for i, similarity in enumerate(movie_similarities):
                    candidate_movie_id = self.movies_df.iloc[i]['id']

                    if (
                        candidate_movie_id != liked_movie_id and
                        user_ratings.get(candidate_movie_id, 0) == 0 and
                        similarity > 0.2):  # Minimum content similarity

                        user_rating = user_ratings[liked_movie_id]
                        content_score = similarity * (user_rating / 5.0)

                        if candidate_movie_id in scores:
                            scores[candidate_movie_id] += content_score
                        else:
                            scores[candidate_movie_id] = content_score

        return scores

    def _get_demographic_scores(self, user_id):
        """Demografik benzerlik skorlari"""
        user_info = self.users_df[self.users_df['id'] == user_id].iloc[0]
        user_idx = list(self.user_item_matrix.index).index(user_id)
        user_cluster = self.user_clusters[user_idx]

        # Ayni cluster'daki kullanicilar
        similar_cluster_users = []
        for i, cluster in enumerate(self.user_clusters):
            if cluster == user_cluster and list(self.user_item_matrix.index)[i] != user_id:
                similar_cluster_users.append(list(self.user_item_matrix.index)[i])

        scores = {}
        user_ratings = self.user_item_matrix.loc[user_id]

        for similar_user_id in similar_cluster_users[:10]:  # Top 10 cluster mate
            similar_user_ratings = self.user_item_matrix.loc[similar_user_id]

            for movie_id in similar_user_ratings.index:
                if (
                    user_ratings[movie_id] == 0 and
                    similar_user_ratings[movie_id] >= 4):  # Cluster mate begenmis

                    if movie_id in scores:
                        scores[movie_id] += similar_user_ratings[movie_id] / 5.0
                    else:
                        scores[movie_id] = similar_user_ratings[movie_id] / 5.0

        return scores

   

    def _get_matrix_factorization_scores(self, user_id):
        """Matrix Factorization skorlari"""
        user_idx = list(self.user_item_matrix.index).index(user_id)
        user_vector = self.svd_model.transform(self.user_item_matrix.iloc[[user_idx]])

        # Tum filmler icin tahmin
        all_predictions = self.svd_model.inverse_transform(user_vector)[0]

        scores = {}
        user_ratings = self.user_item_matrix.loc[user_id]

        for i, movie_id in enumerate(self.user_item_matrix.columns):
            if user_ratings[movie_id] == 0:  # Izlemedigi filmler
                predicted_rating = all_predictions[i]
                scores[movie_id] = max(0,
                predicted_rating / 5.0)  # Normalize

        return scores

    def _get_diversity_score(self, user_id, movie_id):
        """Cesitlilik skoru"""
        user_ratings = self.user_item_matrix.loc[user_id]
        watched_movies = user_ratings[user_ratings > 0].index

        if len(watched_movies) == 0:
            return 0.5  # Neutral diversity for new users

        # Bu filmin kullanicinin izledigi filmlerden ne kadar farkli oldugu
        movie_idx = self.movies_df[self.movies_df['id'] == movie_id].index[0]

        diversity_scores = []
        for watched_movie_id in watched_movies:
            if watched_movie_id in self.movies_df['id'].values:
                watched_idx = self.movies_df[self.movies_df['id'] == watched_movie_id].index[0]
                similarity = self.content_similarity[movie_idx][watched_idx]
                diversity_scores.append(1 - similarity)  # Dusuk benzerlik = yuksek cesitlilik

        return np.mean(diversity_scores) if diversity_scores else 0.5

    def _get_novelty_score(self, movie_id):
        """Yenilik skoru (az bilinen filmler icin bonus)"""
        movie_info = self.movies_df[self.movies_df['id'] == movie_id].iloc[0]

        # Populerlik tersine cevir (az populer = daha novel)
        
        novelty = 0.5

        # Yeni filmler icin bonus
        try:
            release_year = int(movie_info['release_date'].split('-')[0])
            if release_year >= 2020:
                novelty += 0.2
        except:
            pass

        return min(1.0, novelty)

    def _calculate_confidence(self, user_id, movie_id, score):
        """Oneri guven skoru"""
        user_ratings = self.user_item_matrix.loc[user_id]
        user_rating_count = (user_ratings > 0).sum()

        # Kullanici aktivitesi
        activity_confidence = min(1.0, user_rating_count / 20)

        # Skor buyuklugu
        score_confidence = min(1.0, score / 4.0)

        # Genel guven
        confidence = (
            0.6 * activity_confidence +
    
            0.4 * score_confidence
        )

        return round(confidence, 3)
    

    def _get_popularity_scores(self):
        """Populerlik skorlari (sadece avg_rating'e gore)"""
        scores = {}
        for _, movie in self.movies_df.iterrows():
            avg_rating_score = movie['avg_rating'] / 5.0 if pd.notna(movie['avg_rating']) else 0.6
            scores[movie['id']] = avg_rating_score
        return scores
    def _cold_start_recommendations(self, user_id, n_recommendations):
        """Yeni kullanicilar icin cold start cozumu"""
        print(f"[*] Cold start recommendations for user {user_id}")

        # Populer + kaliteli filmler
        popular_movies = self.movies_df.nlargest(50, 'avg_rating')
        quality_movies = self.movies_df[self.movies_df['avg_rating'] >= 4.0].nlargest(50, 'avg_rating')

        # Kullanici demografik bilgisi varsa
        user_info = self.users_df[self.users_df['id'] == user_id]

        recommendations = []

        if not user_info.empty:
            user_data = user_info.iloc[0]

            # Yas bazli oneriler
            if pd.notna(user_data['age']):
                if user_data['age'] < 25:
                    # Genc kullanicilar icin
                    genre_filter = ['Action', 'Comedy', 'Adventure', 'Sci-Fi']
                elif user_data['age'] < 45:
                    # Orta yas icin
                    genre_filter = ['Drama', 'Thriller', 'Crime', 'Romance']
                else:
                    # Yasli kullanicilar icin
                    genre_filter = ['Drama', 'Documentary', 'War', 'Film-Noir']

                # Tur bazli filtreleme
                for _, movie in popular_movies.iterrows():
                    if any(genre in movie['genres'] for genre in genre_filter):
                        recommendations.append({
                            'movie_id': movie['id'],
                            'title': movie['title'],
                            'genres': movie['genres'],
                            'predicted_rating': movie['avg_rating'],
                            'confidence': 0.6,  # Orta guven
                            'hybrid_score': movie['avg_rating'],
                            'avg_rating': movie['avg_rating'],
                            'recommendation_reason': 'Cold Start - Demographic'
                        })

        # Yeterli oneri yoksa populer filmlerle tamamla
        if len(recommendations) < n_recommendations:
            for _, movie in popular_movies.iterrows():
                if len(recommendations) >= n_recommendations:
                    break

                if not any(r['movie_id'] == movie['id'] for r in recommendations):
                    recommendations.append({
                        'movie_id': movie['id'],
                        'title': movie['title'],
                        'genres': movie['genres'],
                        'predicted_rating': movie['avg_rating'],
                        'confidence': 0.4,  # Dusuk guven
                        'hybrid_score': movie['avg_rating'],
                        'avg_rating': movie['avg_rating'],
                        'recommendation_reason': 'Cold Start - Popular'
                    })

        return recommendations[:n_recommendations]

    def save_model(self, filename='kullanicioneri.pkl'):
        """Modeli kaydet"""
        model_data = {
            'user_similarity': self.user_similarity,
            'item_similarity': self.item_similarity,
            'content_similarity': self.content_similarity,
            'svd_model': self.svd_model,
            'nmf_model': self.nmf_model,
            'user_clusters': self.user_clusters,
            'item_clusters': self.item_clusters,
            'user_item_matrix': self.user_item_matrix,
            'movies_df': self.movies_df,
            'users_df': self.users_df,
            'ratings_df': self.ratings_df,
            'user_features': self.user_features,
            'item_features': self.item_features,
            'user_scaler': self.user_scaler,
            'item_scaler': self.item_scaler,
            'hyperparameters': {
                'alpha_collaborative': self.alpha_collaborative,
                'alpha_content': self.alpha_content,
                'alpha_demographic': self.alpha_demographic,
                'alpha_popularity': self.alpha_popularity,
                'temporal_decay': self.temporal_decay
            }
        }

        with open(filename, 'wb') as f:
            pickle.dump(model_data, f)

        print(f"[+] Advanced model saved to {filename}")

    def load_model(self, filename='kullanicioneri.pkl'):
        """Modeli yukle - Guvenli surum"""
        with open(filename, 'rb') as f:
            model_data = pickle.load(f)

        # Guvenli field loading
        self.user_similarity = model_data.get('user_similarity', None)
        self.item_similarity = model_data.get('item_similarity', None) 
        self.content_similarity = model_data.get('content_similarity', None)
        self.svd_model = model_data.get('svd_model', None)
        self.nmf_model = model_data.get('nmf_model', None)
        self.user_clusters = model_data.get('user_clusters', None)
        self.item_clusters = model_data.get('item_clusters', None)
        self.user_item_matrix = model_data.get('user_item_matrix', None)
        self.movies_df = model_data.get('movies_df', None)
        self.users_df = model_data.get('users_df', None)
        self.ratings_df = model_data.get('ratings_df', None)
        
        # NMF model varsa kullan
        if 'user_features' in model_data and 'item_features' in model_data:
            self.user_features = model_data['user_features']
            self.item_features = model_data['item_features']
            self.user_ids = model_data.get('user_ids', [])
            self.movie_ids = model_data.get('movie_ids', [])
        else:
            self.user_features = None
            self.item_features = None
            
        # Optional fields guvenli yukleme
        self.user_scaler = model_data.get('user_scaler', None)
        self.item_scaler = model_data.get('item_scaler', None)

        # Hyperparameters guvenli yukleme
        if 'hyperparameters' in model_data:
            hyperparams = model_data['hyperparameters']
            self.alpha_collaborative = hyperparams.get('alpha_collaborative', 0.5)
            self.alpha_content = hyperparams.get('alpha_content', 0.3)
            self.alpha_demographic = hyperparams.get('alpha_demographic', 0.1)
            self.alpha_popularity = hyperparams.get('alpha_popularity', 0.1)
            self.temporal_decay = hyperparams.get('temporal_decay', 0.95)
        else:
            # Default values
            self.alpha_collaborative = 0.5
            self.alpha_content = 0.3
            self.alpha_demographic = 0.1
            self.alpha_popularity = 0.1
            self.temporal_decay = 0.95

        print("[+] Advanced model loaded successfully")

    def update_model_with_new_rating(self, user_id, movie_id, rating):
        """Yeni rating ile modeli guncelle (Real-time Learning)"""
        print(f"[*] Model updating with new rating: User {user_id}, Movie {movie_id}, Rating {rating}")

        # User-Item matrix'i guncelle
        if user_id in self.user_item_matrix.index and movie_id in self.user_item_matrix.columns:
            # Temporal weight hesapla (yeni rating'ler daha onemli)
            temporal_weight = 1.0  # En yeni rating
            weighted_rating = rating * temporal_weight

            # Matrix'i guncelle
            self.user_item_matrix.loc[user_id, movie_id] = weighted_rating

            # Sadece etkilenen kullanicinin similarity'sini yeniden hesapla
            self._update_user_similarity(user_id)

            print("[+] Model updated successfully!")
        else:
            print("[!] User or movie not found in matrix")

    def _update_user_similarity(self, user_id):
        """Belirli bir kullanicinin similarity'sini guncelle"""
        user_idx = list(self.user_item_matrix.index).index(user_id)
        user_vector = self.user_item_matrix.iloc[user_idx].values.reshape(1, -1)

        # Bu kullanicinin tum diger kullanicilarla similarity'sini hesapla
        all_similarities = cosine_similarity(user_vector, self.user_item_matrix.values)[0]

        # Similarity matrix'ini guncelle
        self.user_similarity[user_idx] = all_similarities
        self.user_similarity[:, user_idx] = all_similarities

    def get_explanation(self, user_id, movie_id):
        """Oneri aciklamasi"""
        explanations = []

        # Collaborative explanation
        user_idx = list(self.user_item_matrix.index).index(user_id)
        user_similarities = self.user_similarity[user_idx]
        top_similar_users = np.argsort(user_similarities)[::-1][1:4]  # Top 3

        similar_user_ratings = []
        for similar_user_idx in top_similar_users:
            similar_user_id = list(self.user_item_matrix.index)[similar_user_idx]
            if movie_id in self.user_item_matrix.columns:
                rating = self.user_item_matrix.loc[similar_user_id, movie_id]
                if rating > 0:
                    similarity = user_similarities[similar_user_idx]
                    similar_user_ratings.append((similar_user_id, rating, similarity))

        if similar_user_ratings:
            explanations.append(f"Sizinle benzer zevklere sahip kullanicilar bu filmi begendi")

        # Content-based explanation
        user_ratings = self.user_item_matrix.loc[user_id]
        liked_movies = user_ratings[user_ratings >= 4].index

        if len(liked_movies) > 0:
            # En begendigi film turlerini bul
            liked_genres = []
            for liked_movie_id in liked_movies[:3]:
                if liked_movie_id in self.movies_df['id'].values:
                    movie_genres = self.movies_df[self.movies_df['id'] == liked_movie_id]['genres'].iloc[0]
                    liked_genres.extend(movie_genres.split('|'))

            # Onerilen filmin turleri
            recommended_movie = self.movies_df[self.movies_df['id'] == movie_id]
            if not recommended_movie.empty:
                rec_genres = recommended_movie['genres'].iloc[0].split('|')
                common_genres = set(liked_genres) & set(rec_genres)

                if common_genres:
                    explanations.append(f"Sevdiginiz {', '.join(list(common_genres)[:2])} turundeki filmlerle benzer")

        # Popularity explanation
        # Popularity explanation (sadece avg_rating ile)
        movie_info = self.movies_df[self.movies_df['id'] == movie_id]
        if not movie_info.empty:
            if movie_info['avg_rating'].iloc[0] >= 4.0:
                explanations.append("Yuksek puan almis kaliteli bir film")


        return explanations if explanations else ["Genel tercihlerinize uygun"]

    def get_model_performance_metrics(self):
        """Model performans metrikleri"""
        metrics = {
            'total_users': len(self.user_item_matrix.index),
            'total_movies': len(self.user_item_matrix.columns),
            'total_ratings': (self.user_item_matrix > 0).sum().sum(),
            'sparsity': 1 - ((self.user_item_matrix > 0).sum().sum() /
                             (len(self.user_item_matrix.index) * len(self.user_item_matrix.columns))),
            'avg_ratings_per_user': (self.user_item_matrix > 0).sum(axis=1).mean(),
            'avg_ratings_per_movie': (self.user_item_matrix > 0).sum(axis=0).mean(),
            'user_clusters': len(np.unique(self.user_clusters)),
            'item_clusters': len(np.unique(self.item_clusters))
        }

        return metrics


# Model egitimi ve test
if __name__ == "__main__":
    print("[*] ADVANCED RECOMMENDATION SYSTEM BASLATILIYOR...")

    # Model olustur
    recommender = AdvancedRecommendationSystem()

    # Veriyi yukle ve hazirla
    recommender.load_and_prepare_data()

    # Tum modelleri egit
    recommender.train_all_models()

    # Modeli kaydet
    recommender.save_model()

    # Test onerileri
    print("\n[*] TEST ONERILERI:")
    test_user_id = list(recommender.user_item_matrix.index)[0]


    recommendations = recommender.get_hybrid_recommendations(
        user_id=test_user_id,
        n_recommendations=10,
        diversity_factor=0.3,
        novelty_factor=0.2
    )

    print(f"\n[+] User {test_user_id} icin oneriler:")
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec['title']}")
        print(f"   Genres: {rec['genres']}")
        print(f"   Predicted Rating: {rec['predicted_rating']:.2f}")
        print(f"   Confidence: {rec['confidence']:.3f}")
        print(f"   Hybrid Score: {rec['hybrid_score']:.3f}")

        # Aciklama
        explanations = recommender.get_explanation(test_user_id, rec['movie_id'])
        print(f"   Why: {'; '.join(explanations)}")
        print()

    # Model metrikleri
    metrics = recommender.get_model_performance_metrics()
    print("[*] MODEL METRIKLERI:")
    for key, value in metrics.items():
        print(f"   {key}: {value}")

    print("\n[+] ADVANCED RECOMMENDATION SYSTEM HAZIR!")