"""
🔍 BASİT VERİTABANI ANALİZ SCRİPTİ
Mevcut veritabanı yapısını hızlıca analiz eder
"""

import sys
import os
from datetime import datetime

# Mevcut database modellerini import et
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app_enhanced_v6 import SessionLocal, User, Movie, Rating, Favorite, Watchlist
    print("✅ Database models imported successfully!")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def simple_db_analysis():
    """Basit veritabanı analizi"""
    
    print("🔍 VERİTABANI YAPISINI ANALİZ EDİYORUM...")
    print("=" * 40)
    
    db = SessionLocal()
    
    try:
        # 1. TABLO SAYILARI
        print("📊 MEVCUT VERİ:")
        user_count = db.query(User).count()
        movie_count = db.query(Movie).count()
        rating_count = db.query(Rating).count()
        favorite_count = db.query(Favorite).count()
        watchlist_count = db.query(Watchlist).count()
        
        print(f"👥 Kullanıcı: {user_count}")
        print(f"🎬 Film: {movie_count}")
        print(f"⭐ Rating: {rating_count}")
        print(f"❤️ Favorite: {favorite_count}")
        print(f"📋 Watchlist: {watchlist_count}")
        
        # 2. ÖRNEK VERİLER
        print("\n📋 ÖRNEK VERİLER:")
        
        # Örnek kullanıcı
        if user_count > 0:
            sample_user = db.query(User).first()
            print(f"\n👤 Örnek Kullanıcı:")
            print(f"   ID: {sample_user.id}")
            print(f"   Username: {sample_user.username}")
            print(f"   Email: {sample_user.email}")
            print(f"   Age: {sample_user.age}")
            print(f"   Gender: {sample_user.gender}")
            print(f"   Favorite Genres: {sample_user.favorite_genres}")
            print(f"   Created At: {sample_user.created_at}")
        
        # Örnek film
        if movie_count > 0:
            sample_movie = db.query(Movie).first()
            print(f"\n🎬 Örnek Film:")
            print(f"   ID: {sample_movie.id}")
            print(f"   Title: {sample_movie.title}")
            print(f"   Genres: {sample_movie.genres}")
            print(f"   Avg Rating: {sample_movie.avg_rating}")
            print(f"   Rating Count: {sample_movie.rating_count}")
            print(f"   Release Date: {sample_movie.release_date}")
            print(f"   Popularity: {sample_movie.popularity}")
        
        # Örnek rating
        if rating_count > 0:
            sample_rating = db.query(Rating).first()
            print(f"\n⭐ Örnek Rating:")
            print(f"   ID: {sample_rating.id}")
            print(f"   User ID: {sample_rating.user_id}")
            print(f"   Movie ID: {sample_rating.movie_id}")
            print(f"   Rating: {sample_rating.rating}")
            print(f"   Created At: {sample_rating.created_at}")
        
        # 3. GENRE LİSTESİ
        print(f"\n🎭 MEVCUT TÜRLER:")
        all_genres = set()
        for movie in db.query(Movie).all():
            if movie.genres:
                genres = movie.genres.split('|')
                all_genres.update([g.strip() for g in genres])
        
        genre_list = sorted(list(all_genres))
        print(f"Toplam {len(genre_list)} tür:")
        for i, genre in enumerate(genre_list, 1):
            print(f"   {i:2d}. {genre}")
        
        # 4. MOVIE ID ARALIĞI
        if movie_count > 0:
            movie_ids = [movie.id for movie in db.query(Movie).all()]
            print(f"\n🔢 FİLM ID ARALIĞI:")
            print(f"   Min ID: {min(movie_ids)}")
            print(f"   Max ID: {max(movie_ids)}")
            print(f"   Toplam Film: {len(movie_ids)}")
            print(f"   ID Gap Var mı: {'Evet' if max(movie_ids) - min(movie_ids) + 1 != len(movie_ids) else 'Hayır'}")
        
        # 5. SENTETİK VERİ İÇİN BİLGİLER
        print(f"\n💡 SENTETİK VERİ İÇİN:")
        print(f"   ✅ Kullanılabilir Film ID'ler: {min(movie_ids) if movie_ids else 'N/A'} - {max(movie_ids) if movie_ids else 'N/A'}")
        print(f"   ✅ Kullanılabilir Türler: {len(genre_list)} adet")
        print(f"   ✅ Mevcut Kullanıcı Sayısı: {user_count}")
        
        # 6. VERİTABANI YAPISI
        print(f"\n🏗️ VERİTABANI YAPISI:")
        print(f"   📋 Users tablosu: id, username, email, password_hash, age, gender, favorite_genres, created_at, updated_at")
        print(f"   📋 Movies tablosu: id, title, genres, avg_rating, rating_count, release_date, imdb_url, popularity")
        print(f"   📋 Ratings tablosu: id, user_id, movie_id, rating, created_at")
        print(f"   📋 Favorites tablosu: id, user_id, movie_id, created_at")
        print(f"   📋 Watchlist tablosu: id, user_id, movie_id, status, created_at, updated_at")
        
        print("\n" + "="*40)
        print("✅ ANALİZ TAMAMLANDI!")
        
        # Return data for synthetic data generation
        return {
            'movie_ids': movie_ids if movie_count > 0 else [],
            'genres': genre_list,
            'current_users': user_count,
            'total_movies': movie_count
        }
        
    except Exception as e:
        print(f"❌ Hata: {e}")
        return None
        
    finally:
        db.close()

if __name__ == "__main__":
    result = simple_db_analysis()
    if result:
        print(f"\n🎯 SONUÇ: {len(result['movie_ids'])} film, {len(result['genres'])} tür mevcut")