import pickle
import pandas as pd
from database_fixed import SessionLocal, Rating, User, Movie

def check_matrix_database_compatibility():
    """Matrix ve Database'in uyumluluğunu kontrol et"""
    
    print("🔗 Matrix-Database uyumluluk kontrolü...\n")
    
    # Matrix yükle
    try:
        with open('user_movie_matrix.pkl', 'rb') as f:
            matrix = pickle.load(f)
        print("✅ Matrix yüklendi")
    except:
        print("❌ Matrix yüklenemedi")
        return
    
    # Database bilgileri
    db = SessionLocal()
    try:
        db_users = set(db.query(User.id).all())
        db_movies = set(db.query(Movie.movie_id).all())
        db_ratings_count = db.query(Rating).count()
        
        print(f"🗄️ Database'de {len(db_users)} kullanıcı, {len(db_movies)} film")
        
        if isinstance(matrix, pd.DataFrame):
            matrix_users = set(matrix.index)
            matrix_movies = set(matrix.columns)
            matrix_ratings = matrix.count().sum()
            
            print(f"📊 Matrix'te {len(matrix_users)} kullanıcı, {len(matrix_movies)} film")
            print(f"⭐ Matrix'te {matrix_ratings} rating, Database'de {db_ratings_count} rating")
            
            # Uyumluluk kontrolü
            user_overlap = len(matrix_users.intersection(db_users))
            movie_overlap = len(matrix_movies.intersection(db_movies))
            
            print(f"\n🔗 Uyumluluk:")
            print(f"  Ortak kullanıcı: {user_overlap}/{max(len(matrix_users), len(db_users))}")
            print(f"  Ortak film: {movie_overlap}/{max(len(matrix_movies), len(db_movies))}")
            
            if user_overlap > 0 and movie_overlap > 0:
                print("✅ Matrix ve Database uyumlu!")
                return True
            else:
                print("❌ Matrix ve Database uyumsuz!")
                return False
                
    finally:
        db.close()

if __name__ == "__main__":
    is_compatible = check_matrix_database_compatibility()