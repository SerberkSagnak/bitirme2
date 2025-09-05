"""
Password Hash Düzeltme Script'i
Mevcut kullanıcıların şifrelerini düzgün hash formatına çevirir
"""

import sqlite3
from passlib.context import CryptContext

# Password context (app_enhanced_v6.py ile aynı)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def fix_user_passwords():
    print("=" * 50)
    print("PASSWORD HASH DUZELTME")
    print("=" * 50)
    
    conn = sqlite3.connect('movielens_100k.db')
    
    # Tüm kullanıcıları al
    users = conn.execute('SELECT id, username, hashed_password FROM app_users').fetchall()
    print(f"Toplam kullanici sayisi: {len(users)}")
    
    fixed_count = 0
    
    for user in users:
        user_id, username, current_password = user
        
        try:
            # Eğer şifre zaten bcrypt hash ise kontrol et
            if current_password and current_password.startswith('$2b$'):
                print(f"  User {username}: Zaten hashli OK")
                continue
            
            # Eğer şifre plaintext ise hash'le
            if current_password:
                # Test şifrelerini bilinen şifreler ile değiştir
                if current_password in ['test123', 'password', '123456']:
                    new_password = current_password
                else:
                    # Bilinmeyen şifreler için default
                    new_password = 'test123'
                
                # Hash'le
                hashed_password = pwd_context.hash(new_password)
                
                # Update database
                conn.execute(
                    'UPDATE app_users SET hashed_password = ? WHERE id = ?',
                    (hashed_password, user_id)
                )
                
                print(f"  User {username}: Sifre hashlendi ({new_password} -> hash)")
                fixed_count += 1
            else:
                # Şifre yoksa default ekle
                default_password = 'test123'
                hashed_password = pwd_context.hash(default_password)
                
                conn.execute(
                    'UPDATE app_users SET hashed_password = ? WHERE id = ?',
                    (hashed_password, user_id)
                )
                
                print(f"  User {username}: Default sifre eklendi (test123)")
                fixed_count += 1
                
        except Exception as e:
            print(f"  User {username}: Hata - {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\n{fixed_count} kullanicinin sifresi duzeltildi!")
    print("\nTest icin kullanici bilgileri:")
    print("  Username: alice")
    print("  Password: test123")
    print("  (Diger tum kullanicilar icin de sifre: test123)")
    
    return fixed_count > 0

if __name__ == "__main__":
    success = fix_user_passwords()
    if success:
        print("\nPassword hash duzeltme tamamlandi!")
        print("Simdi sistemi yeniden baslatabilirsin.")
    else:
        print("\nHic sifre duzeltilmedi.")
