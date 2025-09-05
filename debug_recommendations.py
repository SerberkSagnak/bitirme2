import sqlite3

def debug_recommendations():
    conn = sqlite3.connect('movie_recommendation.db')
    cursor = conn.cursor()
    
    print("🔍 RECOMMENDATION DEBUG RAPORU")
    print("=" * 50)
    
    # 1. Film sayısı
    cursor.execute("SELECT COUNT(*) FROM movies")
    movie_count = cursor.fetchone()[0]
    print(f"📊 Toplam film sayısı: {movie_count}")
    
    # 2. Film rating dağılımı
    cursor.execute("SELECT MIN(avg_rating), MAX(avg_rating), AVG(avg_rating) FROM movies")
    rating_stats = cursor.fetchone()
    print(f"⭐ Rating istatistikleri: Min={rating_stats[0]}, Max={rating_stats[1]}, Avg={rating_stats[2]:.2f}")
    
    # 3. Rating count dağılımı
    cursor.execute("SELECT MIN(rating_count), MAX(rating_count), AVG(rating_count) FROM movies")
    count_stats = cursor.fetchone()
    print(f"👥 Rating count istatistikleri: Min={count_stats[0]}, Max={count_stats[1]}, Avg={count_stats[2]:.0f}")
    
    # 4. Kullanıcı etkileşimleri
    cursor.execute("SELECT COUNT(*) FROM user_interactions")
    interaction_count = cursor.fetchone()[0]
    print(f"🔄 Toplam kullanıcı etkileşimi: {interaction_count}")
    
    # 5. Etkileşim türleri
    cursor.execute("SELECT interaction_type, COUNT(*) FROM user_interactions GROUP BY interaction_type")
    interaction_types = cursor.fetchall()
    print("📋 Etkileşim türleri:")
    for itype, count in interaction_types:
        print(f"  - {itype}: {count}")
    
    # 6. Kullanıcı sayısı
    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM user_interactions")
    user_count = cursor.fetchone()[0]
    print(f"👤 Aktif kullanıcı sayısı: {user_count}")
    
    # 7. Türler analizi
    cursor.execute("SELECT genres FROM movies WHERE genres IS NOT NULL LIMIT 10")
    genres_sample = cursor.fetchall()
    print("🎭 Örnek türler:")
    for genre in genres_sample[:5]:
        print(f"  - {genre[0]}")
    
    # 8. Test filtreleri
    print("\n🧪 TEST FİLTRELERİ:")
    
    # Yüksek rating filmleri
    cursor.execute("SELECT COUNT(*) FROM movies WHERE avg_rating >= 8.0")
    high_rating = cursor.fetchone()[0]
    print(f"  - Rating >= 8.0: {high_rating} film")
    
    cursor.execute("SELECT COUNT(*) FROM movies WHERE avg_rating >= 7.0")
    medium_rating = cursor.fetchone()[0]
    print(f"  - Rating >= 7.0: {medium_rating} film")
    
    cursor.execute("SELECT COUNT(*) FROM movies WHERE avg_rating >= 6.0")
    low_rating = cursor.fetchone()[0]
    print(f"  - Rating >= 6.0: {low_rating} film")
    
    # Popüler filmler
    cursor.execute("SELECT COUNT(*) FROM movies WHERE rating_count >= 1000000")
    very_popular = cursor.fetchone()[0]
    print(f"  - Rating count >= 1M: {very_popular} film")
    
    cursor.execute("SELECT COUNT(*) FROM movies WHERE rating_count >= 100000")
    popular = cursor.fetchone()[0]
    print(f"  - Rating count >= 100K: {popular} film")
    
    cursor.execute("SELECT COUNT(*) FROM movies WHERE rating_count >= 10000")
    somewhat_popular = cursor.fetchone()[0]
    print(f"  - Rating count >= 10K: {somewhat_popular} film")
    
    # 9. Örnek filmler
    print("\n🎬 ÖRNEK FİLMLER:")
    cursor.execute("SELECT title, avg_rating, rating_count, genres FROM movies ORDER BY avg_rating DESC LIMIT 5")
    top_movies = cursor.fetchall()
    for movie in top_movies:
        print(f"  - {movie[0]}: ⭐{movie[1]} 👥{movie[2]} 🎭{movie[3]}")
    
    conn.close()

if __name__ == "__main__":
    debug_recommendations()