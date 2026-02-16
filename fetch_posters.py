import sqlite3
import requests
import time
import re

# Yapılandırma
DB_PATH = 'movielens_100k.db'
TMDB_API_KEY = '44431894b6f2461345b464dd13cd58dc'
TMDB_SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"

def extract_year(title):
    """Başlıktan yılı çıkarır (örn: 'Toy Story (1995)' -> '1995')"""
    match = re.search(r'\((\d{4})\)', title)
    if match:
        return match.group(1)
    return None

def clean_title(title):
    """Başlıktan yılı ve parantezleri temizler"""
    return re.sub(r'\s*\(\d{4}\).*', '', title).strip()

def add_poster_column():
    """Veritabanına poster_url sütunu ekler"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE movies ADD COLUMN poster_url TEXT")
        print("✅ 'poster_url' sütunu eklendi.")
    except sqlite3.OperationalError:
        print("ℹ️ 'poster_url' sütunu zaten var.")
    conn.commit()
    conn.close()

def fetch_posters():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Poster URL'i olmayan filmleri çek
    # (Hepsini yenilemek isterseniz WHERE kısmını kaldırabilirsiniz)
    movies = cursor.execute("SELECT id, title FROM movies WHERE poster_url IS NULL OR poster_url = ''").fetchall()
    
    print(f"🚀 {len(movies)} film için poster aranacak...")
    
    updated_count = 0
    not_found_count = 0
    
    for index, (movie_id, title_raw) in enumerate(movies):
        year = extract_year(title_raw)
        title_clean = clean_title(title_raw)
        
        # TMDB'de ara
        params = {
            'api_key': TMDB_API_KEY,
            'query': title_clean,
            'year': year
        }
        
        try:
            response = requests.get(TMDB_SEARCH_URL, params=params)
            data = response.json()
            
            poster_path = None
            
            if data.get('results'):
                # En iyi eşleşmeyi al
                poster_path = data['results'][0].get('poster_path')
            
            # Eğer yıl ile bulunamadıysa bir de yılsız deneyelim (Bazen yıl 1-2 sene oynayabilir)
            if not poster_path:
                params.pop('year', None)
                response = requests.get(TMDB_SEARCH_URL, params=params)
                data = response.json()
                if data.get('results'):
                    poster_path = data['results'][0].get('poster_path')

            if poster_path:
                full_poster_url = f"{TMDB_IMAGE_BASE_URL}{poster_path}"
                cursor.execute("UPDATE movies SET poster_url = ? WHERE id = ?", (full_poster_url, movie_id))
                updated_count += 1
                # print(f"✅ [{index+1}/{len(movies)}] Bulundu: {title_clean}") # Çok log basmasın diye kapattım
            else:
                not_found_count += 1
                print(f"❌ [{index+1}/{len(movies)}] Bulunamadı: {title_clean}")
                
        except Exception as e:
            print(f"⚠️ Hata ({title_clean}): {e}")
        
        # Her 50 filmde bir commit yap
        if index % 50 == 0:
            conn.commit()
            print(f"💾 Kaydediliyor... ({updated_count} poster bulundu)")
            
        # Hız sınırı için çok kısa bekle
        time.sleep(0.1)
        
    conn.commit()
    conn.close()
    
    print("\n" + "="*40)
    print(f"🎉 İşlem Tamamlandı!")
    print(f"✅ Toplam Bulunan: {updated_count}")
    print(f"❌ Bulunamayan: {not_found_count}")
    print("="*40)

if __name__ == "__main__":
    add_poster_column()
    fetch_posters()
