import shutil
import os

print("🔧 VERİTABANI YOLU DÜZELTİLİYOR...")
print("="*50)

# Kaynak (asıl veritabanı)
source_db = r"C:\Users\serbe\OneDrive\Desktop\bitirme\movielens_100k.db"

# Hedef (mevcut dizin)
target_db = "movielens_100k.db"

# Mevcut boş veritabanını yedekle
if os.path.exists(target_db):
    backup_name = "movielens_100k_empty_backup.db"
    shutil.copy2(target_db, backup_name)
    print(f"📦 Boş veritabanı yedeklendi: {backup_name}")

# Asıl veritabanını kopyala
try:
    shutil.copy2(source_db, target_db)
    
    
    
    
    print(f"✅ Asıl veritabanı kopyalandı!")
    print(f"   Kaynak: {source_db}")
    print(f"   Hedef: {target_db}")
    
    # Boyut kontrolü
    source_size = os.path.getsize(source_db)
    target_size = os.path.getsize(target_db)
    
    print(f"📏 Kaynak boyut: {source_size:,} bytes")
    print(f"📏 Hedef boyut: {target_size:,} bytes")
    
    if source_size == target_size:
        print("🎉 Kopyalama başarılı!")
    else:
        print("⚠️ Boyutlar farklı, kontrol edin!")
        
except Exception as e:
    print(f"❌ Kopyalama hatası: {e}")

print("="*50)