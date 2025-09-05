"""
🔍 VERİTABANI KEŞİF ARACI
Hiçbir şey bilmeden veritabanını keşfeder
"""

import sqlite3
import os

def explore_database():
    # Veritabanı dosyasını bul
    db_files = []
    for file in os.listdir('.'):
        if file.endswith('.db') or file.endswith('.sqlite'):
            db_files.append(file)
    
    if not db_files:
        print("❌ .db veya .sqlite dosyası bulunamadı!")
        return
    
    print(f"📁 Bulunan veritabanı dosyaları: {db_files}")
    
    # İlk veritabanını aç
    db_file = db_files[0]
    print(f"🔍 {db_file} dosyasını inceliyorum...")
    
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # 1. Tüm tabloları listele
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print(f"\n📊 BULUNAN TABLOLAR ({len(tables)} adet):")
        for i, (table_name,) in enumerate(tables, 1):
            print(f"  {i}. {table_name}")
        
        # 2. Her tablo için detay
        for (table_name,) in tables:
            print(f"\n🔍 '{table_name}' TABLOSU:")
            
            # Tablo yapısını göster
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            
            print(f"  📋 Sütunlar ({len(columns)} adet):")
            for col in columns:
                col_id, name, data_type, not_null, default, pk = col
                pk_text = " (PRIMARY KEY)" if pk else ""
                null_text = " NOT NULL" if not_null else ""
                default_text = f" DEFAULT {default}" if default else ""
                print(f"    - {name}: {data_type}{pk_text}{null_text}{default_text}")
            
            # Kayıt sayısını göster
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            count = cursor.fetchone()[0]
            print(f"  📊 Toplam kayıt: {count:,}")
            
            # Eğer kayıt varsa ilk 2 kaydı göster
            if count > 0:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 2;")
                sample_rows = cursor.fetchall()
                
                print(f"  📋 Örnek kayıtlar:")
                column_names = [desc[0] for desc in cursor.description]
                
                for i, row in enumerate(sample_rows, 1):
                    print(f"    Kayıt {i}:")
                    for col_name, value in zip(column_names, row):
                        # Uzun değerleri kısalt
                        if isinstance(value, str) and len(value) > 50:
                            value = value[:47] + "..."
                        print(f"      {col_name}: {value}")
        
        print(f"\n✅ Veritabanı keşfi tamamlandı!")
        
    except Exception as e:
        print(f"❌ Hata: {e}")
    
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    explore_database()