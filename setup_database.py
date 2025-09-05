#!/usr/bin/env python3
"""
MovieLens Veritabanı Kurulum Script'i
Adım adım tüm işlemleri yapar
"""

import os
import sys
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def step_1_check_environment():
    """Adım 1: Ortam kontrolü"""
    print("\n" + "="*60)
    print("📋 ADIM 1: ORTAM KONTROLÜ")
    print("="*60)
    
    # PostgreSQL kontrolü
    try:
        import psycopg2
        print("✅ psycopg2 kurulu")
    except ImportError:
        print("❌ psycopg2 kurulu değil!")
        print("Kurulum: pip install psycopg2-binary")
        return False
    
    # SQLAlchemy kontrolü
    try:
        import sqlalchemy
        print("✅ SQLAlchemy kurulu")
    except ImportError:
        print("❌ SQLAlchemy kurulu değil!")
        print("Kurulum: pip install sqlalchemy")
        return False
    
    # Pandas kontrolü
    try:
        import pandas
        print("✅ Pandas kurulu")
    except ImportError:
        print("❌ Pandas kurulu değil!")
        print("Kurulum: pip install pandas")
        return False
    
    # MovieLens dizini kontrolü
    ml_paths = ['ml-100k', '../ml-100k', 'data/ml-100k']
    ml_found = False
    
    for path in ml_paths:
        if os.path.exists(path):
            print(f"✅ MovieLens dizini bulundu: {path}")
            ml_found = True
            break
    
    if not ml_found:
        print("❌ MovieLens 100k dizini bulunamadı!")
        print("Kontrol edilen yerler:", ml_paths)
        return False
    
    return True

def step_2_create_tables():
    """Adım 2: Tabloları oluştur"""
    print("\n" + "="*60)
    print("🔨 ADIM 2: VERİTABANI TABLOLARI OLUŞTURMA")
    print("="*60)
    
    try:
        from bitirme2.database_config import create_all_tables, get_database_info
        
        # Database bağlantısı test et
        db_info = get_database_info()
        if not db_info['exists']:
            print(f"❌ Veritabanı bağlantısı başarısız: {db_info.get('error', 'Unknown')}")
            return False
        
        print(f"✅ Veritabanı bağlantısı başarılı: {db_info['version']}")
        
        # Tabloları oluştur
        if create_all_tables():
            print("✅ Tablolar başarıyla oluşturuldu!")
            return True
        else:
            print("❌ Tablo oluşturma başarısız!")
            return False
            
    except Exception as e:
        print(f"❌ Hata: {e}")
        return False

def step_3_import_data():
    """Adım 3: MovieLens verilerini import et"""
    print("\n" + "="*60)
    print("📥 ADIM 3: MOVIELENS VERİLERİNİ İMPORT ETME")
    print("="*60)
    
    try:
        from import_existing_movielens import MovieLensImporter
        
        # MovieLens dizinini bul
        ml_paths = ['ml-100k', '../ml-100k', 'data/ml-100k']
        data_path = None
        
        for path in ml_paths:
            if os.path.exists(path):
                data_path = path
                break
        
        if not data_path:
            print("❌ MovieLens dizini bulunamadı!")
            return False
        
        print(f"📂 MovieLens dizini: {data_path}")
        
        # Import et
        importer = MovieLensImporter(data_path)
        
        if importer.import_all():
            print("✅ Veri import'u başarılı!")
            importer.show_summary()
            return True
        else:
            print("❌ Veri import'u başarısız!")
            return False
            
    except Exception as e:
        print(f"❌ Hata: {e}")
        return False

def step_4_create_backup():
    """Adım 4: İlk backup oluştur"""
    print("\n" + "="*60)
    print("💾 ADIM 4: İLK BACKUP OLUŞTURMA")
    print("="*60)
    
    try:
        from database_backup import DatabaseBackup
        
        backup_manager = DatabaseBackup()
        backup_file = backup_manager.create_backup()
        
        if backup_file:
            print(f"✅ Backup oluşturuldu: {backup_file}")
            print("💡 Bu backup'ı güvenli bir yerde saklayın!")
            return True
        else:
            print("❌ Backup oluşturulamadı!")
            return False
            
    except Exception as e:
        print(f"❌ Backup hatası: {e}")
        print("⚠️ Backup opsiyonel, devam edebilirsiniz")
        return True

def step_5_test_system():
    """Adım 5: Sistemi test et"""
    print("\n" + "="*60)
    print("🧪 ADIM 5: SİSTEM TESTİ")
    print("="*60)
    
    try:
        from bitirme2.database_config import SessionLocal, User, Movie, Rating
        from sqlalchemy import func
        
        db = SessionLocal()
        
        # Test sorguları
        user_count = db.query(User).count()
        movie_count = db.query(Movie).count()
        rating_count = db.query(Rating).count()
        avg_rating = db.query(func.avg(Rating.rating)).scalar()
        
        print(f"👥 Kullanıcılar: {user_count:,}")
        print(f"🎬 Filmler: {movie_count:,}")
        print(f"⭐ Puanlamalar: {rating_count:,}")
        print(f"📊 Ortalama Puan: {avg_rating:.2f}")
        
        # Örnek sorgular
        print("\n🔍 Örnek Sorgular:")
        
        # En yüksek puanlı film
        top_movie = db.query(Movie).filter(
            Movie.rating_count >= 50
        ).order_by(Movie.avg_rating.desc()).first()
        
        if top_movie:
            print(f"🏆 En iyi film: {top_movie.title} ({top_movie.avg_rating:.2f}⭐)")
        
        # En aktif kullanıcı
        active_user = db.query(User.id, func.count(Rating.id).label('rating_count')).join(
            Rating
        ).group_by(User.id).order_by(func.count(Rating.id).desc()).first()
        
        if active_user:
            print(f"👑 En aktif kullanıcı: User {active_user[0]} ({active_user[1]} puan)")
        
        db.close()
        
        print("\n✅ Sistem testi başarılı!")
        return True
        
    except Exception as e:
        print(f"❌ Test hatası: {e}")
        return False

def main():
    """Ana kurulum fonksiyonu"""
    print("🎬 MOVIELENS VERİTABANI KURULUM SIHIRBAZI")
    print("="*60)
    print("Bu script MovieLens 100k verisini PostgreSQL'e aktarır")
    print("Devam etmek için Enter'a basın...")
    input()
    
    steps = [
        ("Ortam Kontrolü", step_1_check_environment),
        ("Tablolar Oluştur", step_2_create_tables),
        ("Veri Import", step_3_import_data),
        ("Backup Oluştur", step_4_create_backup),
        ("Sistem Testi", step_5_test_system)
    ]
    
    for i, (step_name, step_func) in enumerate(steps, 1):
        print(f"\n▶️ {step_name} başlıyor...")
        
        if not step_func():
            print(f"\n❌ {step_name} başarısız!")
            print("Kurulum durduruluyor.")
            return False
        
        print(f"✅ {step_name} tamamlandı!")
        
        if i < len(steps):
            input(f"\nSıradaki adıma geçmek için Enter'a basın... ({i+1}/{len(steps)})")
    
    print("\n" + "="*60)
    print("🎉 KURULUM TAMAMLANDI!")
    print("="*60)
    print("✅ PostgreSQL veritabanınız hazır!")
    print("✅ MovieLens 100k verileri import edildi!")
    print("✅ Backup oluşturuldu!")
    print("\n🚀 Sistemi başlatmak için:")
    print("   python -m uvicorn app_enhanced_v6:app --reload")
    print("\n📊 Web interface:")
    print("   http://localhost:8000")
    print("   http://localhost:8000/docs (API Dokümantasyonu)")
    
    return True

if __name__ == "__main__":
    main()