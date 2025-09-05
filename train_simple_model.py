import pandas as pd
import numpy as np
from sklearn.decomposition import NMF
from sklearn.metrics import mean_squared_error
import pickle

def train_recommendation_model():
    """Basit öneri modelini eğit - DÜZELTME"""
    
    print("🤖 MODEL EĞİTİMİ BAŞLIYOR")
    print("=" * 50)
    
    # 1. Temizlenmiş veriyi yükle
    print("📊 Veri yükleniyor...")
    ratings_df = pd.read_csv('cleaned_ratings.csv')
    
    print(f"✅ {len(ratings_df)} rating yüklendi")
    
    # 2. User-Item matrix oluştur
    print("📊 User-Item matrix oluşturuluyor...")
    
    user_item_matrix = ratings_df.pivot_table(
        index='user_id',
        columns='movie_id', 
        values='rating',
        fill_value=0
    )
    
    print(f"✅ Matrix boyutu: {user_item_matrix.shape}")
    
    # 3. NMF modeli eğit (DÜZELTME)
    print("🤖 NMF modeli eğitiliyor...")
    
    model = NMF(
        n_components=20,  # 20 gizli faktör
        random_state=42,
        max_iter=100
        # alpha parametresi kaldırıldı
    )
    
    # Modeli eğit
    W = model.fit_transform(user_item_matrix)
    H = model.components_
    
    # Tahmin matrisi
    predicted_ratings = np.dot(W, H)
    
    print("✅ Model eğitimi tamamlandı!")
    
    # 4. Basit performans testi
    print("📊 Model performansı test ediliyor...")
    
    # Gerçek vs tahmin
    mask = user_item_matrix > 0
    actual = user_item_matrix.values[mask]
    predicted = predicted_ratings[mask]
    
    rmse = np.sqrt(mean_squared_error(actual, predicted))
    
    print(f"✅ Model RMSE: {rmse:.3f}")
    print(f"✅ Ortalama gerçek rating: {actual.mean():.3f}")
    print(f"✅ Ortalama tahmin: {predicted.mean():.3f}")
    
    # 5. Modeli kaydet
    print("💾 Model kaydediliyor...")
    
    model_data = {
        'nmf_model': model,
        'user_item_matrix': user_item_matrix,
        'predicted_ratings': predicted_ratings,
        'W': W,
        'H': H,
        'rmse': rmse,
        'user_ids': list(user_item_matrix.index),
        'movie_ids': list(user_item_matrix.columns)
    }
    
    with open('trained_model.pkl', 'wb') as f:
        pickle.dump(model_data, f)
    
    print("✅ Model 'trained_model.pkl' dosyasına kaydedildi!")
    print(f"📊 Model özeti:")
    print(f"  - RMSE: {rmse:.3f}")
    print(f"  - Matrix boyutu: {user_item_matrix.shape}")
    print(f"  - Faktör sayısı: 20")
    
    return model_data

if __name__ == "__main__":
    train_recommendation_model()
