from database_fixed import SessionLocal, User
import hashlib

def fix_movielens_hashes():
    """MovieLens kullanıcılarının hash'lerini MD5'e çevir"""
    
    print("🔧 MovieLens kullanıcı hash'leri düzeltiliyor...")
    
    db = SessionLocal()
    
    try:
        # Tüm MovieLens kullanıcılarını bul
        ml_users = db.query(User).filter(User.username.like("ml_user_%")).all()
        
        print(f"📊 {len(ml_users)} MovieLens kullanıcısı bulundu")
        
        updated_count = 0
        
        for user in ml_users:
            print(f"\n👤 Kontrol ediliyor: {user.username}")
            print(f"   Mevcut hash: {user.hashed_password}")
            
            # Basit string hash'i olan kullanıcıları düzelt
            if user.hashed_password == "movielens123_simple_hash":
                # Doğru MD5 hash hesapla
                correct_hash = hashlib.md5("movielens123".encode()).hexdigest()
                
                # Güncelle
                user.hashed_password = correct_hash
                updated_count += 1
                
                print(f"   ✅ Güncellendi: {correct_hash}")
            
            elif len(user.hashed_password) == 32 and user.hashed_password.isalnum():
                print(f"   ✅ Zaten MD5 hash formatında")
            
            else:
                print(f"   ⚠️ Bilinmeyen hash formatı")
        
        # Database'e kaydet
        db.commit()
        
        print(f"\n🎉 İşlem tamamlandı!")
        print(f"✅ {updated_count} kullanıcı güncellendi")
        print(f"📊 Toplam {len(ml_users)} MovieLens kullanıcısı")
        
        # Test için birkaç kullanıcıyı kontrol et
        print(f"\n🧪 Güncellenmiş kullanıcıları kontrol et:")
        for user in ml_users[:3]:  # İlk 3 kullanıcı
            db.refresh(user)  # Database'den fresh data al
            print(f"   {user.username}: {user.hashed_password[:20]}...")
        
    except Exception as e:
        print(f"❌ Hata: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

def verify_fix():
    """Düzeltmenin başarılı olduğunu doğrula"""
    
    print("\n🔍 Düzeltme doğrulaması yapılıyor...")
    
    db = SessionLocal()
    
    try:
        # Test kullanıcıları
        test_users = ["ml_user_1", "ml_user_2", "ml_user_3"]
        
        for username in test_users:
            user = db.query(User).filter(User.username == username).first()
            
            if user:
                # Hash kontrolü
                expected_hash = hashlib.md5("movielens123".encode()).hexdigest()
                
                print(f"👤 {username}:")
                print(f"   DB Hash: {user.hashed_password}")
                print(f"   Beklenen: {expected_hash}")
                print(f"   Eşleşme: {'✅' if user.hashed_password == expected_hash else '❌'}")
            else:
                print(f"❌ {username} bulunamadı")
    
    except Exception as e:
        print(f"❌ Doğrulama hatası: {e}")
    
    finally:
        db.close()

if __name__ == "__main__":
    fix_movielens_hashes()
    verify_fix()