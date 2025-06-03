import pandas as pd
import numpy as np

# Veriyi yükle
ratings = pd.read_csv('ml-100k/u.data', sep='\t', 
                     names=['user_id', 'movie_id', 'rating', 'timestamp'])
movies = pd.read_csv('ml-100k/u.item', sep='|', encoding='latin1',
                    names=['movie_id', 'title', 'release_date', 'video_release_date',
                           'imdb_url'] + [f'genre_{i}' for i in range(19)])

print("📊 VERİ BOYUTLARI:")
print(f"Ratings: {ratings.shape}")
print(f"Movies: {movies.shape}")

print("\n📈 İLK 5 RATING:")
print(ratings.head())

print("\n🎬 İLK 5 FİLM:")
print(movies[['movie_id', 'title']].head())

print("\n📊 TEMEL İSTATİSTİKLER:")
print(f"Toplam kullanıcı: {ratings['user_id'].nunique()}")
print(f"Toplam film: {ratings['movie_id'].nunique()}")
print(f"Toplam rating: {len(ratings)}")
print(f"Rating dağılımı:\n{ratings['rating'].value_counts().sort_index()}")