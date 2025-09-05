import sqlite3
import os
from datetime import datetime

print("🕵️ GERÇEK VERİTABANI DURUMU KONTROLÜ")
print("="*60)

# Tüm .db dosyalarını kontrol et
db_files = [f for f in os.listdir('.') if f.endswith('.db')]
print(f"📁 Bulunan .db dosyaları: {db_files}")

for db_file in db_files:
    print(f"\n🔍 {db_file} analiz ediliyor...")
    print("-" * 40)
    
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Dosya boyutu
        size = os.path.getsize(db_file)
        print(f"📏 Boyut: {size:,} bytes ({size/1024:.1f} KB)")
        
        # Tabloları listele
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        table_names = [t[0] for t in tables]
        print(f"📋 Tablolar: {table_names}")
        
        # Her tablodaki kayıt sayısı
        for table_name in table_names:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"  📊 {table_name}: {count} kayıt")
                
                # Eğer kayıt varsa örnek göster
                if count > 0:
                    cursor.execute(f"SELECT * FROM {table_name} LIMIT 2")
                    samples = cursor.fetchall()
                    
                    # Kolon isimlerini al
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = [col[1] for col in cursor.fetchall()]
                    
                    print(f"    📝 Örnek kayıtlar:")
                    for sample in samples:
                        sample_dict = dict(zip(columns, sample))
                        # Sadece önemli alanları göster
                        if table_name == 'users':
                            print(f"      👤 {sample_dict.get('username', 'N/A')} - {sample_dict.get('email', 'N/A')}")
                        elif table_name == 'movies':
                            print(f"      🎬 {sample_dict.get('title', 'N/A')} - Rating: {sample_dict.get('avg_rating', 'N/A')}")
                        elif table_name == 'user_interactions':
                            print(f"      🔄 User:{sample_dict.get('user_id', 'N/A')} Movie:{sample_dict.get('movie_id', 'N/A')} Type:{sample_dict.get('type', 'N/A')}")
                        else:
                            print(f"      📄 {sample}")
                            
            except Exception as e:
                print(f"    ❌ {table_name} okuma hatası: {e}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ {db_file} açma hatası: {e}")

print(f"\n" + "="*60)

# FastAPI'nin hangi veritabanını kullandığını kontrol et
print("🔧 FASTAPI KONFIGURASYON KONTROLÜ:")
try:
    with open('app_enhanced_v6.py', 'r', encoding='utf-8') as f:
        content = f.read()
        
    # DATABASE_URL'i bul
    import re
    db_url_match = re.search(r'DATABASE_URL\s*=\s*["\']([^"\']+)["\']', content)
    if db_url_match:
        db_url = db_url_match.group(1)
        print(f"📍 FastAPI kullandığı DB: {db_url}")
    else:
        print("❓ DATABASE_URL bulunamadı")
        
except Exception as e:
    print(f"❌ app_enhanced_v6.py okuma hatası: {e}")

print("="*60)