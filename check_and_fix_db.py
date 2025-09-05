import os
import sqlite3
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Models'i import et
from models import Base, Movie, User, UserInteraction

print("🔧 VERİTABANI ONARIM ARACI")
print("="*50)

# Veritabanı dosyasını kontrol et
db_file = "movielens_100k.db"
if os.path.exists(db_file):
    print(f"✅ Veritabanı dosyası bulundu: {db_file}")
else:
    print(f"❌ Veritabanı dosyası bulunamadı: {db_file}")

# SQLAlchemy engine oluştur
DATABASE_URL = f"sqlite:///./{db_file}"
engine = create_engine(DATABASE_URL)

print("\n🔨 Tabloları oluşturuyor...")
try:
    # Tüm tabloları oluştur
    Base.metadata.create_all(bind=engine)
    print("✅ Tablolar başarıyla oluşturuldu!")
    
    # Tabloları kontrol et
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    # Movie sayısını kontrol et
    movie_count = db.query(Movie).count()
    user_count = db.query(User).count()
    interaction_count = db.query(UserInteraction).count()
    
    print(f"\n📊 VERİTABANI DURUMU:")
    print(f"  🎬 Movies: {movie_count}")
    print(f"  👥 Users: {user_count}")
    print(f"  🔄 Interactions: {interaction_count}")
    
    if movie_count == 0:
        print("\n⚠️  Movies tablosu boş! CSV'den veri yüklenmesi gerekiyor.")
        print("💡 FastAPI uygulamasını çalıştırın, otomatik yüklenecek.")
    
    db.close()
    
except Exception as e:
    print(f"❌ Hata: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*50)