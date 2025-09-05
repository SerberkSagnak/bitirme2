import pandas as pd
import sqlite3
import os

class MovieLensLoader:
    def __init__(self, data_dir=None, db_path='movielens_100k.db'):
        # Otomatik yol bulma
        if data_dir is None:
            # Mevcut klasör ve alt klasörlerde ml-100k ara
            possible_paths = [
                'ml-100k',
                'bitirme2/ml-100k', 
                '../ml-100k',
                './bitirme2/ml-100k'
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    self.data_dir = path
                    break
            else:
                # Manuel yol belirtmesi gerekiyor
                print("❌ ml-100k klasörü bulunamadı!")
                print("Lütfen ml-100k klasörünün tam yolunu girin:")
                self.data_dir = input("Yol: ").strip()
        else:
            self.data_dir = data_dir
            
        self.db_path = db_path
        print(f"📁 Kullanılan veri klasörü: {self.data_dir}")
        
    def check_main_files(self):
        """Ana dosyaları kontrol et"""
        print("📁 MovieLens 100k Dosya Kontrolü:")
        
        if not os.path.exists(self.data_dir):
            print(f"❌ Klasör bulunamadı: {self.data_dir}")
            return False
        
        main_files = {
            'u.data': 'Ratings (user_id, movie_id, rating, timestamp)',
            'u.item': 'Movies (movie bilgileri)',
            'u.user': 'Users (kullanıcı bilgileri)',
            'u.genre': 'Genres (film türleri)',
            'u.info': 'Dataset info'
        }
        
        all_exist = True
        for file, description in main_files.items():
            file_path = os.path.join(self.data_dir, file)
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                print(f"  ✅ {file:<10} - {size:>8,} bytes - {description}")
            else:
                print(f"  ❌ {file:<10} - Bulunamadı")
                all_exist = False
        
        return all_exist
    
    def preview_ratings_data(self):
        """u.data dosyasını önizle"""
        file_path = os.path.join(self.data_dir, 'u.data')
        
        if not os.path.exists(file_path):
            print(f"❌ {file_path} bulunamadı")
            return
            
        print(f"\n📊 RATINGS DATA (u.data) Önizleme:")
        
        # MovieLens 100k formatı: user_id \t movie_id \t rating \t timestamp
        df = pd.read_csv(file_path, sep='\t', header=None, 
                        names=['user_id', 'movie_id', 'rating', 'timestamp'])
        
        print(f"Shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")
        print("\nİlk 5 satır:")
        print(df.head())
        print(f"\nRating dağılımı:")
        print(df['rating'].value_counts().sort_index())
        print(f"Toplam kullanıcı: {df['user_id'].nunique()}")
        print(f"Toplam film: {df['movie_id'].nunique()}")
        
    def preview_movies_data(self):
        """u.item dosyasını önizle"""
        file_path = os.path.join(self.data_dir, 'u.item')
        
        if not os.path.exists(file_path):
            print(f"❌ {file_path} bulunamadı")
            return
            
        print(f"\n🎬 MOVIES DATA (u.item) Önizleme:")
        
        # MovieLens 100k item formatı
        column_names = [
            'movie_id', 'title', 'release_date', 'video_release_date', 'imdb_url',
            'unknown', 'Action', 'Adventure', 'Animation', 'Children', 'Comedy',
            'Crime', 'Documentary', 'Drama', 'Fantasy', 'Film-Noir', 'Horror',
            'Musical', 'Mystery', 'Romance', 'Sci-Fi', 'Thriller', 'War', 'Western'
        ]
        
        try:
            df = pd.read_csv(file_path, sep='|', header=None, names=column_names, encoding='latin-1')
            print(f"Shape: {df.shape}")
            print("\nİlk 5 film:")
            print(df[['movie_id', 'title', 'release_date']].head())
            
            # Genre bilgileri
            genre_columns = column_names[5:]
            print(f"\nMevcut türler: {len(genre_columns)} tür")
            
        except Exception as e:
            print(f"Hata: {e}")
    
    def preview_users_data(self):
        """u.user dosyasını önizle"""
        file_path = os.path.join(self.data_dir, 'u.user')
        
        if not os.path.exists(file_path):
            print(f"❌ {file_path} bulunamadı")
            return
            
        print(f"\n👥 USERS DATA (u.user) Önizleme:")
        
        df = pd.read_csv(file_path, sep='|', header=None, 
                        names=['user_id', 'age', 'gender', 'occupation', 'zip_code'])
        
        print(f"Shape: {df.shape}")
        print("\nİlk 5 kullanıcı:")
        print(df.head())
        print(f"\nYaş dağılımı:")
        print(f"Min: {df['age'].min()}, Max: {df['age'].max()}, Ortalama: {df['age'].mean():.1f}")
        print(f"\nCinsiyet dağılımı:")
        print(df['gender'].value_counts())

if __name__ == "__main__":
    loader = MovieLensLoader()
    
    # Dosyaları kontrol et
    files_exist = loader.check_main_files()
    
    if files_exist:
        loader.preview_ratings_data()
        loader.preview_movies_data() 
        loader.preview_users_data()
    else:
        print("\n💡 Çözüm önerileri:")
        print("1. Script'i bitirme2 klasörüne taşıyın")
        print("2. Veya ml-100k klasörünün tam yolunu belirtin")
