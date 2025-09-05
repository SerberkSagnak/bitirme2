import sqlite3
import pandas as pd

def create_movielens_mapping():
    """MoveLens ID'leri ile veritabanı ID'lerini eşleştir"""
    
    print("🔗 MoveLens ID Mapping oluşturuluyor...")
    
    conn = sqlite3.connect('movielens_100k.db')
    
    # Veritabanındaki filmler
    movies_df = pd.read_sql_query("SELECT * FROM movies", conn)
    print(f"📊 Veritabanında {len(movies_df)} film var")
    
    # MoveLens verisi
    ratings_df = pd.read_csv('cleaned_ratings.csv')
    movielens_movie_ids = ratings_df['movie_id'].unique()
    print(f"📊 MoveLens'te {len(movielens_movie_ids)} film var")
    
    # Mapping tablosu oluştur
    cursor = conn.cursor()
    
    # Mapping tablosunu oluştur
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movielens_mapping (
            movielens_id INTEGER PRIMARY KEY,
            database_id INTEGER,
            title TEXT,
            mapped BOOLEAN DEFAULT 0
        )
    ''')
    
    # MoveLens ID'lerini ekle
    for ml_id in movielens_movie_ids:
        cursor.execute('''
            INSERT OR IGNORE INTO movielens_mapping (movielens_id, mapped) 
            VALUES (?, 0)
        ''', (int(ml_id),))
    
    # Basit eşleştirme: MoveLens ID = Database ID olanları bul
    mapped_count = 0
    for ml_id in movielens_movie_ids:
        # Aynı ID'li film var mı?
        db_movie = movies_df[movies_df['id'] == ml_id]
        if not db_movie.empty:
            cursor.execute('''
                UPDATE movielens_mapping 
                SET database_id = ?, title = ?, mapped = 1
                WHERE movielens_id = ?
            ''', (int(ml_id), db_movie.iloc[0]['title'], int(ml_id)))
            mapped_count += 1
    
    conn.commit()
    
    print(f"✅ {mapped_count} film eşleştirildi")
    
    # Eşleşmeyen filmler için rastgele atama
    cursor.execute("SELECT COUNT(*) FROM movielens_mapping WHERE mapped = 0")
    unmapped_count = cursor.fetchone()[0]
    
    if unmapped_count > 0:
        print(f"🔄 {unmapped_count} eşleşmeyen film için rastgele atama yapılıyor...")
        
        # Rastgele database ID'leri al
        available_db_ids = movies_df['id'].tolist()
        
        cursor.execute("SELECT movielens_id FROM movielens_mapping WHERE mapped = 0")
        unmapped_ids = [row[0] for row in cursor.fetchall()]
        
        for i, ml_id in enumerate(unmapped_ids):
            if i < len(available_db_ids):
                db_id = available_db_ids[i]
                db_movie = movies_df[movies_df['id'] == db_id]
                
                cursor.execute('''
                    UPDATE movielens_mapping 
                    SET database_id = ?, title = ?, mapped = 1
                    WHERE movielens_id = ?
                ''', (db_id, db_movie.iloc[0]['title'], ml_id))
    
    conn.commit()
    
    # Sonuçları kontrol et
    cursor.execute("SELECT COUNT(*) FROM movielens_mapping WHERE mapped = 1")
    total_mapped = cursor.fetchone()[0]
    
    print(f"✅ Toplam {total_mapped} film eşleştirildi")
    
    # Örnek eşleştirmeler
    cursor.execute("SELECT * FROM movielens_mapping WHERE mapped = 1 LIMIT 10")
    examples = cursor.fetchall()
    
    print("\n📋 Örnek eşleştirmeler:")
    for ex in examples:
        print(f"  MoveLens {ex[0]} → DB {ex[1]} ({ex[2]})")
    
    conn.close()
    return True

if __name__ == "__main__":
    create_movielens_mapping()