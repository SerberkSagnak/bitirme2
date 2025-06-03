from database_fixed import SessionLocal, User, Movie, Rating
from auth import get_password_hash
import json
from datetime import datetime

def load_test_data():
    db = SessionLocal()
    
    print("🚀 Test verisi yükleniyor...")
    
    # Test kullanıcıları
    test_users = [
        {"username": "alice", "email": "alice@test.com", "password": "123456"},
        {"username": "bob", "email": "bob@test.com", "password": "123456"},
        {"username": "charlie", "email": "charlie@test.com", "password": "123456"},
        {"username": "diana", "email": "diana@test.com", "password": "123456"},
        {"username": "eve", "email": "eve@test.com", "password": "123456"},
    ]
    
    # Test filmleri (popüler filmler)
    test_movies = [
        {"movie_id": 1001, "title": "The Matrix", "genres": '["Action", "Sci-Fi"]', "release_date": "1999-03-31", "avg_rating": 4.5},
        {"movie_id": 1002, "title": "Star Wars", "genres": '["Action", "Adventure", "Sci-Fi"]', "release_date": "1977-05-25", "avg_rating": 4.6},
        {"movie_id": 1003, "title": "Titanic", "genres": '["Drama", "Romance"]', "release_date": "1997-12-19", "avg_rating": 4.2},
        {"movie_id": 1004, "title": "Avatar", "genres": '["Action", "Adventure", "Sci-Fi"]', "release_date": "2009-12-18", "avg_rating": 4.3},
        {"movie_id": 1005, "title": "Inception", "genres": '["Action", "Sci-Fi", "Thriller"]', "release_date": "2010-07-16", "avg_rating": 4.7},
        {"movie_id": 1006, "title": "The Godfather", "genres": '["Crime", "Drama"]', "release_date": "1972-03-24", "avg_rating": 4.9},
        {"movie_id": 1007, "title": "Pulp Fiction", "genres": '["Crime", "Drama"]', "release_date": "1994-10-14", "avg_rating": 4.8},
        {"movie_id": 1008, "title": "Forrest Gump", "genres": '["Drama", "Romance"]', "release_date": "1994-07-06", "avg_rating": 4.4},
        {"movie_id": 1009, "title": "The Dark Knight", "genres": '["Action", "Crime", "Drama"]', "release_date": "2008-07-18", "avg_rating": 4.8},
        {"movie_id": 1010, "title": "Interstellar", "genres": '["Drama", "Sci-Fi"]', "release_date": "2014-11-07", "avg_rating": 4.6},
    ]
    
    # Kullanıcıları ekle
    user_ids = {}
    for user_data in test_users:
        existing = db.query(User).filter(User.username == user_data["username"]).first()
        if not existing:
            user = User(
                username=user_data["username"],
                email=user_data["email"],
                hashed_password=get_password_hash(user_data["password"])
            )
            db.add(user)
            db.flush()  # ID almak için
            user_ids[user_data["username"]] = user.id
            print(f"✅ Kullanıcı eklendi: {user_data['username']} (ID: {user.id})")
        else:
            user_ids[user_data["username"]] = existing.id
            print(f"♻️ Kullanıcı zaten var: {user_data['username']} (ID: {existing.id})")
    
    # Filmleri ekle
    movie_ids = {}
    for movie_data in test_movies:
        existing = db.query(Movie).filter(Movie.movie_id == movie_data["movie_id"]).first()
        if not existing:
            movie = Movie(
                movie_id=movie_data["movie_id"],
                title=movie_data["title"],
                genres=movie_data["genres"],
                release_date=movie_data["release_date"],
                avg_rating=movie_data["avg_rating"],
                rating_count=0
            )
            db.add(movie)
            db.flush()  # ID almak için
            movie_ids[movie_data["movie_id"]] = movie.id
            print(f"✅ Film eklendi: {movie_data['title']} (ID: {movie.id})")
        else:
            movie_ids[movie_data["movie_id"]] = existing.id
            print(f"♻️ Film zaten var: {movie_data['title']} (ID: {existing.id})")
    
    db.commit()
    
    # Test ratings (gerçekçi veriler)
    test_ratings = [
        # Alice - Sci-Fi sever
        {"username": "alice", "movie_id": 1001, "rating": 5.0},  # Matrix
        {"username": "alice", "movie_id": 1002, "rating": 4.5},  # Star Wars
        {"username": "alice", "movie_id": 1004, "rating": 4.0},  # Avatar
        {"username": "alice", "movie_id": 1005, "rating": 5.0},  # Inception
        {"username": "alice", "movie_id": 1010, "rating": 4.5},  # Interstellar
        {"username": "alice", "movie_id": 1003, "rating": 2.5},  # Titanic (sevmez)
        
        # Bob - Aksiyon sever
        {"username": "bob", "movie_id": 1001, "rating": 4.0},   # Matrix
        {"username": "bob", "movie_id": 1002, "rating": 5.0},   # Star Wars
        {"username": "bob", "movie_id": 1009, "rating": 5.0},   # Dark Knight
        {"username": "bob", "movie_id": 1004, "rating": 4.5},   # Avatar
        {"username": "bob", "movie_id": 1006, "rating": 3.0},   # Godfather (ok)
        {"username": "bob", "movie_id": 1008, "rating": 2.0},   # Forrest Gump (sevmez)
        
        # Charlie - Drama sever
        {"username": "charlie", "movie_id": 1006, "rating": 5.0},  # Godfather
        {"username": "charlie", "movie_id": 1007, "rating": 4.5},  # Pulp Fiction
        {"username": "charlie", "movie_id": 1008, "rating": 5.0},  # Forrest Gump
        {"username": "charlie", "movie_id": 1003, "rating": 4.0},  # Titanic
        {"username": "charlie", "movie_id": 1009, "rating": 4.0},  # Dark Knight
        {"username": "charlie", "movie_id": 1001, "rating": 3.0},  # Matrix (ok)
        
        # Diana - Romance sever
        {"username": "diana", "movie_id": 1003, "rating": 5.0},   # Titanic
        {"username": "diana", "movie_id": 1008, "rating": 4.5},   # Forrest Gump
        {"username": "diana", "movie_id": 1006, "rating": 4.0},   # Godfather
        {"username": "diana", "movie_id": 1010, "rating": 3.5},   # Interstellar
        {"username": "diana", "movie_id": 1001, "rating": 3.0},   # Matrix
        {"username": "diana", "movie_id": 1009, "rating": 2.5},   # Dark Knight
        
        # Eve - Çeşitli beğeniler
        {"username": "eve", "movie_id": 1005, "rating": 5.0},     # Inception
        {"username": "eve", "movie_id": 1007, "rating": 4.5},     # Pulp Fiction
        {"username": "eve", "movie_id": 1009, "rating": 4.0},     # Dark Knight
        {"username": "eve", "movie_id": 1002, "rating": 4.0},     # Star Wars
        {"username": "eve", "movie_id": 1010, "rating": 4.5},     # Interstellar
        {"username": "eve", "movie_id": 1003, "rating": 3.0},     # Titanic
    ]
    
    # Ratings ekle
    rating_count = 0
    for rating_data in test_ratings:
        user_internal_id = user_ids[rating_data["username"]]
        movie_internal_id = movie_ids[rating_data["movie_id"]]
        
        existing = db.query(Rating).filter(
            Rating.user_id == user_internal_id,
            Rating.movie_id == movie_internal_id
        ).first()
        
        if not existing:
            rating = Rating(
                user_id=user_internal_id,
                movie_id=movie_internal_id,
                rating=rating_data["rating"]
            )
            db.add(rating)
            rating_count += 1
    
    db.commit()
    db.close()
    
    print("\n🎉 Test verisi başarıyla yüklendi!")
    print(f"📊 {len(test_users)} kullanıcı")
    print(f"📊 {len(test_movies)} film") 
    print(f"📊 {rating_count} yeni rating")
    print("\n🚀 Şimdi ML modelini train edebilirsin!")

if __name__ == "__main__":
    load_test_data()