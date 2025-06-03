import pandas as pd
import requests
import zipfile
import os
from database_fixed import SessionLocal, User, Movie, Rating
import json
from datetime import datetime

def download_movielens_100k():
    """MovieLens 100K dataset'ini indir ve yükle"""
    
    print("🎬 MovieLens 100K Dataset indiriliyor...")
    
    # Dataset URL
    url = "https://files.grouplens.org/datasets/movielens/ml-100k.zip"
    
    # İndir
    if not os.path.exists("ml-100k.zip"):
        print("📥 Dataset indiriliyor... (5MB)")
        response = requests.get(url)
        with open("ml-100k.zip", "wb") as f:
            f.write(response.content)
        print("✅ İndirme tamamlandı!")
    
    # Zip'i aç
    if not os.path.exists("ml-100k"):
        print("📂 Zip dosyası açılıyor...")
        with zipfile.ZipFile("ml-100k.zip", "r") as zip_ref:
            zip_ref.extractall(".")
        print("✅ Dosyalar çıkarıldı!")
    
    # Verileri oku
    print("📊 Veriler okunuyor...")
    
    # Movies (u.item)
    movies_df = pd.read_csv(
        "ml-100k/u.item", 
        sep="|", 
        encoding="latin-1",
        header=None,
        names=["movie_id", "title", "release_date", "video_release_date", "imdb_url"] + 
              [f"genre_{i}" for i in range(19)]
    )
    
    # Ratings (u.data)
    ratings_df = pd.read_csv(
        "ml-100k/u.data",
        sep="\t",
        header=None,
        names=["user_id", "movie_id", "rating", "timestamp"]
    )
    
    # Users (u.user)
    users_df = pd.read_csv(
        "ml-100k/u.user",
        sep="|",
        header=None,
        names=["user_id", "age", "gender", "occupation", "zip_code"]
    )
    
    print(f"📊 Dataset boyutu:")
    print(f"   👥 {len(users_df)} kullanıcı")
    print(f"   🎬 {len(movies_df)} film")
    print(f"   ⭐ {len(ratings_df)} rating")
    
    # Genre mapping
    genre_cols = [f"genre_{i}" for i in range(19)]
    genre_names = [
        "unknown", "Action", "Adventure", "Animation", "Children's", "Comedy", 
        "Crime", "Documentary", "Drama", "Fantasy", "Film-Noir", "Horror", 
        "Musical", "Mystery", "Romance", "Sci-Fi", "Thriller", "War", "Western"
    ]
    
    return movies_df, ratings_df, users_df, genre_names

def load_to_database(movies_df, ratings_df, users_df, genre_names):
    """Verileri database'e yükle"""
    
    db = SessionLocal()
    
    print("🚀 Database'e yükleniyor...")
    
    # 1. Users ekle
    print("👥 Kullanıcılar ekleniyor...")
    user_mapping = {}  # MovieLens ID -> Database ID
    
    for _, row in users_df.iterrows():
        # MovieLens kullanıcıları için otomatik username oluştur
        username = f"ml_user_{row['user_id']}"
        email = f"ml_user_{row['user_id']}@movielens.test"
        
        existing = db.query(User).filter(User.username == username).first()
        if not existing:
            user = User(
                username=username,
                email=email,
                hashed_password="movielens123_simple_hash",  # ✅ Bu çalışır
                age=int(row['age']) if pd.notna(row['age']) else None,
                gender=row['gender'] if pd.notna(row['gender']) else None
            )
            db.add(user)
            db.flush()
            user_mapping[row['user_id']] = user.id
        else:
            user_mapping[row['user_id']] = existing.id
    
    # 2. Movies ekle
    print("🎬 Filmler ekleniyor...")
    movie_mapping = {}  # MovieLens ID -> Database ID
    
    for _, row in movies_df.iterrows():
        # Genre'ları topla
        genres = []
        for i, genre_name in enumerate(genre_names):
            if row[f"genre_{i}"] == 1:
                genres.append(genre_name)
        
        # Title'dan yılı ayır
        title = row['title']
        year = None
        if title.endswith(")") and "(" in title:
            try:
                year_part = title.split("(")[-1].replace(")", "")
                if year_part.isdigit() and len(year_part) == 4:
                    year = int(year_part)
                    title = title.split("(")[0].strip()
            except:
                pass
        
        existing = db.query(Movie).filter(Movie.movie_id == row['movie_id']).first()
        if not existing:
            movie = Movie(
                movie_id=row['movie_id'],
                title=title,
                genres=json.dumps(genres),
                release_date=f"{year}-01-01" if year else "1995-01-01",
                avg_rating=0,
                rating_count=0,
                imdb_url=row['imdb_url'] if pd.notna(row['imdb_url']) else None
            )
            db.add(movie)
            db.flush()
            movie_mapping[row['movie_id']] = movie.id
        else:
            movie_mapping[row['movie_id']] = existing.id
    
    db.commit()
    
    # 3. Ratings ekle (batch'ler halinde)
    print("⭐ Ratings ekleniyor... (Bu birkaç dakika sürebilir)")
    
    batch_size = 1000
    total_ratings = len(ratings_df)
    
    for i in range(0, total_ratings, batch_size):
        batch = ratings_df.iloc[i:i+batch_size]
        
        for _, row in batch.iterrows():
            if row['user_id'] in user_mapping and row['movie_id'] in movie_mapping:
                # Aynı rating zaten var mı kontrol et
                existing = db.query(Rating).filter(
                    Rating.user_id == user_mapping[row['user_id']],
                    Rating.movie_id == movie_mapping[row['movie_id']]
                ).first()
                
                if not existing:
                    rating = Rating(
                        user_id=user_mapping[row['user_id']],
                        movie_id=movie_mapping[row['movie_id']],
                        rating=float(row['rating']),
                        created_at=datetime.fromtimestamp(row['timestamp'])
                    )
                    db.add(rating)
        
        db.commit()
        print(f"  📊 {min(i+batch_size, total_ratings)}/{total_ratings} rating eklendi...")
    
    db.close()
    
    print("\n🎉 MovieLens 100K Dataset başarıyla yüklendi!")
    print(f"📊 {len(users_df)} kullanıcı")
    print(f"📊 {len(movies_df)} film")
    print(f"📊 {total_ratings} rating")
    print(f"\n🤖 Şimdi ML sistemi gerçek verilerle çalışacak!")
    print(f"🔐 Test kullanıcıları: ml_user_1, ml_user_2... (şifre: movielens123)")

def main():
    try:
        # Dataset'i indir
        movies_df, ratings_df, users_df, genre_names = download_movielens_100k()
        
        # Database'e yükle
        load_to_database(movies_df, ratings_df, users_df, genre_names)
        
        # Temizlik
        print("\n🧹 Geçici dosyalar temizleniyor...")
        if os.path.exists("ml-100k.zip"):
            os.remove("ml-100k.zip")
        
        print("✅ İşlem tamamlandı!")
        
    except Exception as e:
        print(f"❌ Hata: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()