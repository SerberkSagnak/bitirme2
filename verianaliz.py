# Database exploration script
db = SessionLocal()

# 1. User tablosu analizi
user_count = db.query(User).count()
print(f"Toplam kullanıcı: {user_count}")

# 2. Movie analizi  
movie_count = db.query(Movie).count()
print(f"Toplam film: {movie_count}")

# İlk 3 filmi göster
sample_movies = db.query(Movie).limit(3).all()
for movie in sample_movies:
    print(f"Film: {movie.title}, Genres: {movie.genres}")

# 3. Rating analizi
rating_count = db.query(Rating).count() 
print(f"Toplam rating: {rating_count}")

# 4. Genre analizi
unique_genres = set()
for movie in db.query(Movie).all():
    if movie.genres:
        unique_genres.update(movie.genres.split('|'))
print(f"Unique genres: {list(unique_genres)}")

db.close()