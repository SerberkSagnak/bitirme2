import sqlite3

def check_user_ratings():
    """Kullanıcı rating'lerini kontrol et"""
    
    conn = sqlite3.connect('movielens_100k.db')
    cursor = conn.cursor()
    
    # User 1'in rating'lerini kontrol et
    cursor.execute("""
        SELECT r.movie_id, m.title, r.rating, r.created_at
        FROM ratings r
        JOIN movies m ON r.movie_id = m.id
        WHERE r.user_id = 1
        ORDER BY r.created_at DESC
    """)
    
    ratings = cursor.fetchall()
    
    print("🎯 USER 1'İN RATING'LERİ:")
    print("=" * 50)
    
    if ratings:
        for rating in ratings:
            print(f"  🎬 {rating[1]} → ⭐ {rating[2]} ({rating[3]})")
    else:
        print("  ❌ Hiç rating bulunamadı!")
    
    # Favorites tablosunu kontrol et
    cursor.execute("""
        SELECT f.movie_id, m.title, f.created_at
        FROM favorites f
        JOIN movies m ON f.movie_id = m.id
        WHERE f.user_id = 1
        ORDER BY f.created_at DESC
    """)
    
    favorites = cursor.fetchall()
    
    print(f"\n❤️ USER 1'İN FAVORİLERİ ({len(favorites)} adet):")
    print("=" * 50)
    
    for fav in favorites:
        print(f"  🎬 {fav[1]} ({fav[2]})")
    
    conn.close()

if __name__ == "__main__":
    check_user_ratings()