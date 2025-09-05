import os
import sqlite3
from datetime import datetime

print("🔍 MEVCUT VERİTABANI ARAMA ARACI")
print("="*60)

def search_db_files(directory):
    """Belirtilen dizinde .db dosyalarını ara"""
    db_files = []
    try:
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.db'):
                    full_path = os.path.join(root, file)
                    db_files.append(full_path)
    except PermissionError:
        pass
    return db_files

def analyze_database(db_path):
    """Veritabanını analiz et"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Dosya bilgileri
        size = os.path.getsize(db_path)
        modified = datetime.fromtimestamp(os.path.getmtime(db_path))
        
        print(f"\n📁 {db_path}")
        print(f"   📏 Boyut: {size:,} bytes ({size/1024:.1f} KB)")
        print(f"   📅 Son değişiklik: {modified}")
        
        # Tabloları kontrol et
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if not tables:
            print("   ❌ Tablo yok")
            conn.close()
            return False
        
        print(f"   📋 Tablolar: {[t[0] for t in tables]}")
        
        # Film tablosu var mı kontrol et
        table_names = [t[0] for t in tables]
        movie_tables = [t for t in table_names if 'movie' in t.lower()]
        user_tables = [t for t in table_names if 'user' in t.lower()]
        
        has_data = False
        
        # Her tablodaki kayıt sayısını kontrol et
        for table_name in table_names:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                if count > 0:
                    print(f"   📊 {table_name}: {count} kayıt ✅")
                    has_data = True
                    
                    # Örnek veri göster
                    if count <= 5:
                        cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                        samples = cursor.fetchall()
                        for sample in samples[:2]:  # İlk 2 kayıt
                            print(f"      📄 {sample}")
                else:
                    print(f"   📊 {table_name}: {count} kayıt")
            except Exception as e:
                print(f"   ❌ {table_name}: Hata - {e}")
        
        conn.close()
        
        if has_data:
            print("   🎉 BU VERİTABANINDA VERİ VAR!")
            return True
        else:
            print("   ⚠️  Bu veritabanı boş")
            return False
            
    except Exception as e:
        print(f"   ❌ Analiz hatası: {e}")
        return False

# Ana arama
print("🔍 Arama başlıyor...")

# 1. Mevcut dizin
print("\n1️⃣ MEVCUT DİZİN:")
current_dir_dbs = search_db_files(".")
for db in current_dir_dbs:
    analyze_database(db)

# 2. Üst dizin (bitirme klasörü)
print("\n2️⃣ ÜST DİZİN (bitirme):")
parent_dir = os.path.dirname(os.getcwd())
parent_dbs = search_db_files(parent_dir)
for db in parent_dbs:
    if db not in current_dir_dbs:  # Tekrar gösterme
        analyze_database(db)

# 3. Desktop'ta arama
print("\n3️⃣ DESKTOP ARAMA:")
desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
if os.path.exists(desktop_path):
    desktop_dbs = search_db_files(desktop_path)
    for db in desktop_dbs:
        if 'movie' in db.lower() or 'recommendation' in db.lower():
            analyze_database(db)

# 4. OneDrive'da arama
print("\n4️⃣ ONEDRIVE ARAMA:")
onedrive_path = os.path.join(os.path.expanduser("~"), "OneDrive")
if os.path.exists(onedrive_path):
    onedrive_dbs = search_db_files(onedrive_path)
    movie_related_dbs = [db for db in onedrive_dbs if 'movie' in db.lower() or 'recommendation' in db.lower()]
    for db in movie_related_dbs[:10]:  # İlk 10 tanesi
        analyze_database(db)

print("\n" + "="*60)
print("🎯 ÖZET:")
print("Yukarıda '🎉 BU VERİTABANINDA VERİ VAR!' yazan dosya senin veritabanın!")
print("O dosyanın tam yolunu kopyala ve söyle.")
print("="*60)