from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from database_fixed import User, SessionLocal
import json
import hashlib
import warnings
warnings.filterwarnings("ignore", message=".*trapped.*error reading bcrypt version")


# Security Ayarları
SECRET_KEY = "Aa1234567."
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Bcrypt context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    """Bcrypt şifre doğrulama"""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        print(f"❌ Bcrypt verify hatası: {e}")
        return False

def get_password_hash(password):
    """Bcrypt şifre hashleme"""
    try:
        return pwd_context.hash(password)
    except Exception as e:
        print(f"❌ Bcrypt hash hatası: {e}")
        # Fallback olarak MD5 kullan
        return hashlib.md5(password.encode()).hexdigest()

def verify_md5_password(plain_password, hashed_password):
    """MD5 şifre doğrulama (MovieLens kullanıcıları için)"""
    try:
        md5_hash = hashlib.md5(plain_password.encode()).hexdigest()
        return md5_hash == hashed_password
    except Exception as e:
        print(f"❌ MD5 verify hatası: {e}")
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """JWT token oluştur"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    """JWT token doğrula"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except JWTError as e:
        print(f"❌ JWT Error: {e}")
        return None

class UserService:
    def __init__(self, db: Session = None):
        if db:
            self.db = db
        else:
            self.db = SessionLocal()
    
    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()
    
    def create_user(self, username: str, email: str, password: str,
                   age: Optional[int] = None, gender: Optional[str] = None,
                   favorite_genres: Optional[list] = None):
        """Yeni kullanıcı oluştur"""
        
        print(f"🆕 Yeni kullanıcı oluşturuluyor: {username}")
        
        # Kullanıcı zaten var mı?
        if self.get_user_by_username(username):
            raise ValueError("Bu kullanıcı adı zaten kullanılıyor")
        
        if self.get_user_by_email(email):
            raise ValueError("Bu email zaten kullanılıyor")
        
        # Şifreyi hashle
        hashed_password = get_password_hash(password)
        print(f"✅ Şifre hashli: {hashed_password[:20]}...")
        
        # Favorite genres JSON'a çevir
        genres_json = json.dumps(favorite_genres) if favorite_genres else None
        
        # User oluştur
        user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            age=age,
            gender=gender,
            favorite_genres=genres_json
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        print(f"✅ Kullanıcı oluşturuldu: ID={user.id}, Username={user.username}")
        return user
    
    def authenticate_user(self, username: str, password: str):
        """Kullanıcı authentication - Hibrit sistem"""
        
        print(f"\n🔐 === LOGIN DENEMESİ ===")
        print(f"👤 Username: {username}")
        print(f"🔑 Password uzunluğu: {len(password)}")
        
        # Kullanıcıyı bul
        user = self.get_user_by_username(username)
        if not user:
            print(f"❌ Kullanıcı bulunamadı: {username}")
            return None  # ✅ DÜZELTME: False değil None return et
        
        print(f"✅ Kullanıcı bulundu: ID={user.id}")
        print(f"📧 Email: {user.email}")
        print(f"🔐 DB Hash (ilk 20 kar): {user.hashed_password[:20]}...")
        print(f"🔐 DB Hash uzunluğu: {len(user.hashed_password)}")
        
        # MovieLens kullanıcıları için MD5 kontrolü
        if username.startswith("ml_user_"):
            print(f"🎬 MovieLens kullanıcısı tespit edildi")
            
            md5_hash = hashlib.md5(password.encode()).hexdigest()
            print(f"🔐 Hesaplanan MD5: {md5_hash[:20]}...")
            print(f"🔐 DB'deki hash: {user.hashed_password[:20]}...")
            
            if user.hashed_password == md5_hash:
                print(f"✅ MovieLens MD5 hash eşleşti!")
                return user
            else:
                print(f"❌ MovieLens MD5 hash eşleşmedi")
                return None  # ✅ DÜZELTME: False değil None
        
        # Normal kullanıcılar için bcrypt kontrolü
        else:
            print(f"👤 Normal kullanıcı - Bcrypt kontrolü")
            
            try:
                if verify_password(password, user.hashed_password):
                    print(f"✅ Bcrypt hash eşleşti!")
                    return user
                else:
                    print(f"❌ Bcrypt hash eşleşmedi")
                    return None  # ✅ DÜZELTME: False değil None
            except Exception as e:
                print(f"❌ Bcrypt kontrolü hatası: {e}")
                # Bcrypt başarısız olursa MD5 dene
                print(f"🔄 Fallback MD5 kontrolü deneniyor...")
                if verify_md5_password(password, user.hashed_password):
                    print(f"✅ Fallback MD5 başarılı!")
                    return user
                else:
                    print(f"❌ Fallback MD5 de başarısız")
                    return None  # ✅ DÜZELTME: False değil None
    
    def get_user_by_username(self, username: str):
        """Username ile kullanıcı bul"""
        try:
            return self.db.query(User).filter(User.username == username).first()
        except Exception as e:
            print(f"❌ get_user_by_username hatası: {e}")
            return None
    
    def get_user_by_email(self, email: str):
        """Email ile kullanıcı bul"""
        try:
            return self.db.query(User).filter(User.email == email).first()
        except Exception as e:
            print(f"❌ get_user_by_email hatası: {e}")
            return None
    
    def get_user_by_id(self, user_id: int):
        """ID ile kullanıcı bul"""
        try:
            return self.db.query(User).filter(User.id == user_id).first()
        except Exception as e:
            print(f"❌ get_user_by_id hatası: {e}")
            return None
    
    def update_user_profile(self, user_id: int, **kwargs):
        """Kullanıcı profilini güncelle"""
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return None
            
            for key, value in kwargs.items():
                if key == "favorite_genres" and value:
                    value = json.dumps(value)
                if hasattr(user, key):
                    setattr(user, key, value)
            
            user.last_active = datetime.utcnow()
            self.db.commit()
            self.db.refresh(user)
            
            return user
        except Exception as e:
            self.db.rollback()
            print(f"❌ update_user_profile hatası: {e}")
            return None
    
    def create_test_users(self):
        """Test kullanıcıları oluştur"""
        test_users = [
            {
                "username": "alice",
                "email": "alice@test.com",
                "password": "123456",
                "age": 25,
                "gender": "F"
            },
            {
                "username": "bob", 
                "email": "bob@test.com",
                "password": "password123",
                "age": 30,
                "gender": "M"
            },
            {
                "username": "ml_user_1",
                "email": "ml1@movielens.com", 
                "password": "movielens123",
                "age": 28,
                "gender": "M"
            }
        ]
        
        created_users = []
        for user_data in test_users:
            try:
                # Kullanıcı zaten var mı kontrol et
                existing = self.get_user_by_username(user_data["username"])
                if existing:
                    print(f"⚠️ Kullanıcı zaten mevcut: {user_data['username']}")
                    created_users.append(existing)
                    continue
                
                # MovieLens kullanıcısı için MD5 hash kullan
                if user_data["username"].startswith("ml_user_"):
                    hashed_password = hashlib.md5(user_data["password"].encode()).hexdigest()
                else:
                    hashed_password = get_password_hash(user_data["password"])
                
                user = User(
                    username=user_data["username"],
                    email=user_data["email"],
                    hashed_password=hashed_password,
                    age=user_data.get("age"),
                    gender=user_data.get("gender")
                )
                
                self.db.add(user)
                self.db.commit()
                self.db.refresh(user)
                
                print(f"✅ Test kullanıcısı oluşturuldu: {user.username}")
                created_users.append(user)
                
            except Exception as e:
                self.db.rollback()
                print(f"❌ Test kullanıcısı oluşturma hatası: {e}")
        
        return created_users

# ... (önceki kodlar aynı) ...

def test_user_system():
    """Kullanıcı sistemini test et"""
    print("🧪 === USER SİSTEMİ TEST ===\n")
    
    user_service = UserService()
    
    try:
        # Test kullanıcıları oluştur
        print("0️⃣ Test kullanıcıları oluşturuluyor...")
        user_service.create_test_users()
        print("\n" + "="*50 + "\n")
        
        # 1. Normal kullanıcı testi
        print("1️⃣ Normal kullanıcı authentication testi:")
        auth_result = user_service.authenticate_user("alice", "123456")
        if auth_result:
            print("✅ Alice authentication başarılı!")
            print(f"   User ID: {auth_result.id}, Email: {auth_result.email}")
        else:
            print("❌ Alice authentication başarısız!")
        
        print("\n" + "="*50 + "\n")
        
        # 2. MovieLens kullanıcı testi
        print("2️⃣ MovieLens kullanıcısı authentication testi:")
        auth_result = user_service.authenticate_user("ml_user_1", "movielens123")
        if auth_result:
            print("✅ ml_user_1 authentication başarılı!")
            print(f"   User ID: {auth_result.id}, Email: {auth_result.email}")
        else:
            print("❌ ml_user_1 authentication başarısız!")
        
        print("\n" + "="*50 + "\n")
        
        # 3. Token testi
        print("3️⃣ Token oluşturma testi:")
        token = create_access_token(data={"sub": "alice"})
        print(f"🔑 Token oluşturuldu: {token[:50]}...")
        
        # Token doğrulama
        verified_username = verify_token(token)
        if verified_username:
            print(f"✅ Token doğrulandı: {verified_username}")
        else:
            print("❌ Token doğrulanamadı!")
        
        print("\n" + "="*50 + "\n")
        
        # 4. Yanlış şifre testi
        print("4️⃣ Yanlış şifre testi:")
        auth_result = user_service.authenticate_user("alice", "wrongpassword")
        if not auth_result:
            print("✅ Yanlış şifre doğru şekilde reddedildi!")
        else:
            print("❌ Yanlış şifre kabul edildi!")
    
    except Exception as e:
        print(f"❌ Test hatası: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Session'ı temizle
        if hasattr(user_service, 'db'):
            user_service.db.close()
            print("🔒 Database session kapatıldı")

if __name__ == "__main__":
    test_user_system()
