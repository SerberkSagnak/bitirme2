from database_fixed import SessionLocal, Rating, User, Movie
from sqlalchemy import func

def analyze_database():
    """Database'deki rating durumunu analiz et"""
    
    print("🗄️ Database analiz ediliyor...\n")
    
    db = SessionLocal()
    try:
        # Rating sayıları
        total_ratings = db.query(Rating).count()
        total_users = db.query(User).count()
        total_movies = db.query(Movie).count()
        
        print(f"⭐ Toplam rating: {total_ratings:,}")
        print(f"👥 Toplam kullanıcı: {total_users:,}")
        print(f"🎬 Toplam film: {total_movies:,}")
        
        if total_ratings > 0:
            # Rating istatistikleri
            rating_stats = db.query(
                func.min(Rating.rating).label('min_rating'),
                func.max(Rating.rating).label('max_rating'),
                func.avg(Rating.rating).label('avg_rating'),
                func.count(Rating.rating).label('count')
            ).first()
            
            print(f"\n📊 Rating İstatistikleri:")
            print(f"  Min: {rating_stats.min_rating}")
            print(f"  Max: {rating_stats.max_rating}")
            print(f"  Ortalama: {rating_stats.avg_rating:.2f}")
            
            # En aktif kullanıcılar
            active_users = db.query(
                Rating.user_id,
                func.count(Rating.id).label('rating_count')
            ).group_by(Rating.user_id).order_by(
                func.count(Rating.id).desc()
            ).limit(5).all()
            
            print(f"\n🏆 En aktif kullanıcılar:")
            for user_id, count in active_users:
                print(f"  Kullanıcı {user_id}: {count} rating")
            
            # En popüler filmler
            popular_movies = db.query(
                Movie.title,
                func.count(Rating.id).label('rating_count')
            ).join(Rating, Movie.movie_id == Rating.movie_id).group_by(
                Movie.movie_id, Movie.title
            ).order_by(
                func.count(Rating.id).desc()
            ).limit(5).all()
            
            print(f"\n🎬 En popüler filmler:")
            for title, count in popular_movies:
                print(f"  {title}: {count} rating")
            
            # Sparsity hesaplama
            if total_users > 0 and total_movies > 0:
                possible_ratings = total_users * total_movies
                sparsity = (1 - total_ratings / possible_ratings) * 100
                print(f"\n🕳️ Database Sparsity: %{sparsity:.2f}")
                
                # Yeterli veri var mı?
                if total_ratings >= 1000:
                    print("✅ ML için yeterli veri var!")
                elif total_ratings >= 100:
                    print("⚠️ ML için minimum veri var, daha fazla rating gerekebilir")
                else:
                    print("❌ ML için yetersiz veri")
        
        else:
            print("⚠️ Database'de hiç rating yok!")
            
        return {
            'total_ratings': total_ratings,
            'total_users': total_users,
            'total_movies': total_movies,
            'has_sufficient_data': total_ratings >= 100
        }
        
    finally:
        db.close()

if __name__ == "__main__":
    db_stats = analyze_database()