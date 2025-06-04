import pickle
import pandas as pd
import numpy as np

def analyze_user_movie_matrix():
    """user_movie_matrix.pkl dosyasını analiz et"""
    
    print("🔍 Model dosyası analiz ediliyor...\n")
    
    try:
        # Dosyayı yükle
        with open('user_movie_matrix.pkl', 'rb') as f:
            user_movie_matrix = pickle.load(f)
        
        print("✅ Dosya başarıyla yüklendi!")
        print(f"📊 Veri tipi: {type(user_movie_matrix)}")
        
        # DataFrame ise
        if isinstance(user_movie_matrix, pd.DataFrame):
            print(f"📏 Boyut: {user_movie_matrix.shape}")
            print(f"👥 Kullanıcı sayısı: {len(user_movie_matrix.index)}")
            print(f"🎬 Film sayısı: {len(user_movie_matrix.columns)}")
            print(f"⭐ Toplam rating: {user_movie_matrix.count().sum()}")
            print(f"🔢 Null oranı: {user_movie_matrix.isnull().sum().sum() / user_movie_matrix.size * 100:.1f}%")
            
            print("\n📈 İstatistikler:")
            print(user_movie_matrix.describe())
            
            print("\n👀 Örnek veri (ilk 5x5):")
            print(user_movie_matrix.iloc[:5, :5])
            
            # Sparsity analizi
            total_cells = user_movie_matrix.size
            filled_cells = user_movie_matrix.count().sum()
            sparsity = (1 - filled_cells/total_cells) * 100
            print(f"\n🕳️ Sparsity: %{sparsity:.1f} (boş hücre oranı)")
            
        # NumPy array ise
        elif isinstance(user_movie_matrix, np.ndarray):
            print(f"📏 Boyut: {user_movie_matrix.shape}")
            print(f"🔢 Veri tipi: {user_movie_matrix.dtype}")
            print(f"📊 Min-Max: {user_movie_matrix.min():.2f} - {user_movie_matrix.max():.2f}")
            print(f"📈 Ortalama: {user_movie_matrix.mean():.2f}")
            
        # Dictionary ise
        elif isinstance(user_movie_matrix, dict):
            print(f"🔑 Anahtarlar: {list(user_movie_matrix.keys())}")
            for key, value in user_movie_matrix.items():
                print(f"  {key}: {type(value)} - {np.array(value).shape if hasattr(value, 'shape') else len(value)}")
        
        return user_movie_matrix
        
    except Exception as e:
        print(f"❌ Hata: {e}")
        return None

def detect_model_algorithm(matrix):
    """Matrix'e bakarak algoritma tipini tahmin et"""
    
    print("\n🧠 Algoritma Analizi:")
    
    if isinstance(matrix, pd.DataFrame):
        # Rating değerleri 1-5 arası mı?
        non_null_values = matrix.dropna().values.flatten()
        min_val, max_val = non_null_values.min(), non_null_values.max()
        
        if 1 <= min_val and max_val <= 5:
            print("🎯 Muhtemelen: Collaborative Filtering (User-Item Rating Matrix)")
            print("  - Kullanıcıların filmlere verdiği puanlar")
            print("  - Matrix Factorization için hazır")
            
        elif 0 <= min_val <= 1:
            print("🎯 Muhtemelen: Binary Preference Matrix")
            print("  - 0: Beğenmedi, 1: Beğendi")
            
        else:
            print("🎯 Muhtemelen: Normalized/Processed Rating Matrix")
            print("  - Önceden işlenmiş veriler")
    
    return "collaborative_filtering_matrix"

if __name__ == "__main__":
    matrix = analyze_user_movie_matrix()
    if matrix is not None:
        algorithm_type = detect_model_algorithm(matrix)