import pandas as pd

# Film verilerini yükle
movies = pd.read_csv('ml-100k/u.item', sep='|', encoding='latin1',
                    names=['movie_id', 'title', 'release_date', 'video_release_date',
                           'imdb_url'] + [f'genre_{i}' for i in range(19)])

# Matrix'i yükle
user_movie_matrix = pd.read_pickle('user_movie_matrix.pkl')

print("🎭 ÖNERİLEN FİLMLER:")
print("Film ID: 318 ->", movies[movies['movie_id'] == 318]['title'].values[0])
print("Film ID: 474 ->", movies[movies['movie_id'] == 474]['title'].values[0])
print("Film ID: 655 ->", movies[movies['movie_id'] == 655]['title'].values[0])
print("Film ID: 423 ->", movies[movies['movie_id'] == 423]['title'].values[0])
print("Film ID: 403 ->", movies[movies['movie_id'] == 403]['title'].values[0])

# 1 numaralı kullanıcının daha önce izlediği ve beğendiği filmler (4-5 puan)
print(f"\n👤 1 numaralı kullanıcının sevdiği filmler (4-5 puan):")
user_1_ratings = user_movie_matrix.loc[1]
high_rated = user_1_ratings[user_1_ratings >= 4]
for movie_id, rating in high_rated.head(10).items():
    movie_title = movies[movies['movie_id'] == movie_id]['title'].values[0]
    print(f"⭐ {rating} - {movie_title}")

print(f"\nToplam {len(high_rated)} film 4+ puan almış")