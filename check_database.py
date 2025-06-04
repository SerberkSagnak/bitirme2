import sqlite3
import pandas as pd

def check_database_structure():
    conn = sqlite3.connect('movie_recommendation.db')
    
    # Movies tablosunun yapısını kontrol et
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(movies)")
    columns = cursor.fetchall()
    
    print("🔍 Movies tablosundaki kolonlar:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")
    
    # Eksik kolonları tespit et
    existing_columns = [col[1] for col in columns]
    required_columns = ['popularity', 'avg_rating']
    
    missing_columns = [col for col in required_columns if col not in existing_columns]
    
    if missing_columns:
        print(f"\n❌ Eksik kolonlar: {missing_columns}")
        return False
    else:
        print("\n✅ Tüm gerekli kolonlar mevcut")
        return True
    
    conn.close()

if __name__ == "__main__":
    check_database_structure()