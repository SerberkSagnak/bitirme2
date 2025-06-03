import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# Matrix'i yükle
user_movie_matrix = pd.read_pickle('user_movie_matrix.pkl')

print("🤖 User-Based Collaborative Filtering Modeli")

# Kullanıcılar arası benzerlik hesapla (cosine similarity)
print("📐 Kullanıcı benzerlik matrisi hesaplanıyor...")
user_similarity = cosine_similarity(user_movie_matrix)
user_similarity_df = pd.DataFrame(user_similarity, 
                                  index=user_movie_matrix.index, 
                                  columns=user_movie_matrix.index)

print(f"✅ Benzerlik matrisi hazır: {user_similarity_df.shape}")

# Test edelim: 1 numaralı kullanıcıya en benzer kullanıcılar kimler?
user_1_similarities = user_similarity_df[1].sort_values(ascending=False)
print(f"\n👤 1 numaralı kullanıcıya en benzer 5 kullanıcı:")
print(user_1_similarities.head(6))  # İlki kendisi olacak

# Basit öneri fonksiyonu
def get_recommendations(user_id, n_recommendations=5):
    # Bu kullanıcının izlemediği filmler
    user_ratings = user_movie_matrix.loc[user_id]
    unwatched_movies = user_ratings[user_ratings == 0].index
    
    # En benzer kullanıcılar (kendisi hariç)
    similar_users = user_similarity_df[user_id].sort_values(ascending=False)[1:11]
    
    # Öneriler için skorlar
    movie_scores = {}
    for movie_id in unwatched_movies:
        score = 0
        for similar_user, similarity in similar_users.items():
            if user_movie_matrix.loc[similar_user, movie_id] > 0:
                score += similarity * user_movie_matrix.loc[similar_user, movie_id]
        movie_scores[movie_id] = score
    
    # En yüksek skorlu filmleri döndür
    top_movies = sorted(movie_scores.items(), key=lambda x: x[1], reverse=True)
    return top_movies[:n_recommendations]

# Test edelim!
print(f"\n🎬 1 numaralı kullanıcı için öneriler:")
recommendations = get_recommendations(1, 5)
for movie_id, score in recommendations:
    print(f"Film ID: {movie_id}, Skor: {score:.3f}")