import pandas as pd
import numpy as np

# Önceki verileri kullan (ratings ve movies)
ratings = pd.read_csv('ml-100k/u.data', sep='\t', 
                     names=['user_id', 'movie_id', 'rating', 'timestamp'])

# User-Item Rating Matrix oluştur
print("🔄 User-Item Matrix oluşturuluyor...")
user_movie_matrix = ratings.pivot_table(
    index='user_id',
    columns='movie_id', 
    values='rating',
    fill_value=0
)

print(f"📏 Matrix boyutu: {user_movie_matrix.shape}")
print(f"📊 Sparsity (boşluk oranı): {(user_movie_matrix == 0).sum().sum() / (user_movie_matrix.shape[0] * user_movie_matrix.shape[1]) * 100:.2f}%")

# İlk 5 kullanıcı, ilk 10 filmin rating'lerini göster
print("\n🎯 Matrix örneği (ilk 5 kullanıcı, ilk 10 film):")
print(user_movie_matrix.iloc[:5, :10])

# Hangi kullanıcı en çok film izlemiş?
user_rating_counts = (user_movie_matrix > 0).sum(axis=1)
print(f"\n👤 En aktif kullanıcı: {user_rating_counts.idxmax()} ({user_rating_counts.max()} film)")
print(f"👤 En az aktif kullanıcı: {user_rating_counts.idxmin()} ({user_rating_counts.min()} film)")

# Matrix'i kaydet
user_movie_matrix.to_pickle('user_movie_matrix.pkl')
print("\n💾 Matrix kaydedildi: user_movie_matrix.pkl")