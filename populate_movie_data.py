import random
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Proje dizinini Python path'ine ekle
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Veritabanı bağlantısını manuel oluştur
DATABASE_URL = "sqlite:///./movie_recommendation.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Models'i import et
try:
    from models import Movie, Base
    print("✅ Models başarıyla import edildi")
except Exception as e:
    print(f"❌ Models import hatası: {e}")
    sys.exit(1)

def populate_realistic_movie_data():
    """Filmlere gerçekçi rating ve popularity değerleri ver"""
    
    print("🎬 MOVIE DATA POPULATION STARTING...")
    print("="*50)
    
    # Veritabanı dosyasının varlığını kontrol et
    db_file = "movie_recommendation.db"
    if not os.path.exists(db_file):
        print(f"❌ Veritabanı dosyası bulunamadı: {db_file}")
        print("🔍 Mevcut dosyalar:")
        for file in os.listdir("."):
            if file.endswith(".db"):
                print(f"  - {file}")
        return False
    
    print(f"✅ Veritabanı dosyası bulundu: {db_file}")
    
    db = SessionLocal()
    
    try:
        # Tabloların varlığını kontrol et
        movies = db.query(Movie).limit(5).all()
        print(f"✅ Movies tablosu erişilebilir, örnek: {len(movies)} film")
        
        # Tüm filmleri al
        all_movies = db.query(Movie).all()
        print(f"📊 Toplam {len(all_movies)} film bulundu")
        
        updated_count = 0
        
        for i, movie in enumerate(all_movies, 1):
            # Film türüne göre popülerlik belirle
            genres = movie.genres.lower() if movie.genres else ""
            
            # Popüler türler daha yüksek rating alsın
            if any(genre in genres for genre in ['action', 'adventure', 'thriller']):
                base_rating = random.uniform(3.5, 4.8)
                base_count = random.randint(100, 800)
            elif any(genre in genres for genre in ['comedy', 'romance']):
                base_rating = random.uniform(3.2, 4.6)
                base_count = random.randint(80, 600)
            elif any(genre in genres for genre in ['animation', 'children']):
                base_rating = random.uniform(3.8, 4.9)
                base_count = random.randint(150, 1200)
            elif any(genre in genres for genre in ['drama']):
                base_rating = random.uniform(3.0, 4.5)
                base_count = random.randint(60, 500)
            elif any(genre in genres for genre in ['horror', 'mystery']):
                base_rating = random.uniform(2.8, 4.2)
                base_count = random.randint(40, 300)
            else:
                base_rating = random.uniform(2.5, 4.0)
                base_count = random.randint(20, 200)
            
            # Özel filmler için bonus
            title_lower = movie.title.lower()
            if any(word in title_lower for word in ['star', 'batman', 'toy story', 'titanic', 'matrix']):
                base_count = int(base_count * 1.5)
                base_rating = min(base_rating + 0.3, 5.0)
            
            # Veritabanını güncelle
            movie.avg_rating = round(base_rating, 1)
            movie.rating_count = base_count
            
            updated_count += 1
            
            # Progress göster
            if i % 200 == 0:
                print(f"📈 İşlenen: {i}/{len(all_movies)} ({(i/len(all_movies)*100):.1f}%)")
            
            # İlk 5 filmi göster
            if i <= 5:
                print(f"✅ {movie.title}: {movie.avg_rating} ⭐ ({movie.rating_count} oy)")
        
        # Değişiklikleri kaydet
        print("\n💾 Veritabanı kaydediliyor...")
        db.commit()
        
        print("\n" + "="*50)
        print(f"🎉 BAŞARILI!")
        print(f"📊 Toplam {len(all_movies)} film")
        print(f"✅ {updated_count} film güncellendi")
        print(f"💾 Veritabanı kaydedildi")
        print("="*50)
        
        # Örnek veriler göster
        print("\n📋 ÖRNEK GÜNCELLENMIŞ FİLMLER:")
        sample_movies = db.query(Movie).limit(10).all()
        for movie in sample_movies:
            print(f"  🎬 {movie.title}: {movie.avg_rating} ⭐ ({movie.rating_count} oy)")
        
        return True
        
    except Exception as e:
        print(f"❌ HATA: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Film verisi güncelleme başlatılıyor...")
    success = populate_realistic_movie_data()
    
    if success:
        print("\n✅ Script başarıyla tamamlandı!")
        print("🗑️  Bu dosyayı artık silebilirsiniz.")
    else:
        print("\n❌ Script hata ile sonlandı!")
        print("🔍 Lütfen veritabanı dosyasını kontrol edin.")
