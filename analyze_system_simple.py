import pickle
import pandas as pd
import numpy as np
import os
import sqlite3

def find_database_files():
    """Database ve model dosyalarını bul"""
    print("🔍 Mevcut dosyalar:")
    
    python_files = [f for f in os.listdir('.') if f.endswith('.py')]
    pkl_files = [f for f in os.listdir('.') if f.endswith('.pkl')]
    db_files = [f for f in os.listdir('.') if f.endswith('.db')]
    
    print("📄 Python dosyaları:")
    for f in python_files:
        print(f"  {f}")
    
    print("\n🗃️ Pickle dosyaları:")
    for f in pkl_files:
        print(f"  {f}")
        
    print("\n🗄️ Database dosyaları:")
    for f in db_files:
        print(f"  {f}")
    
    return python_files, pkl_files, db_files

def analyze_pickle_file():
    """user_movie_matrix.pkl analizi"""
    print("\n" + "="*50)
    print("📊 user_movie_matrix.pkl ANALIZI")
    print("="*50)
    
    try:
        with open('user_movie_matrix.pkl', 'rb') as f:
            matrix = pickle.load(f)
        
        print("✅ Dosya başarıyla yüklendi!")
        print(f"📊 Veri tipi: {type(matrix)}")
        
        if isinstance(matrix, pd.DataFrame):
            print(f"\n📏 BOYUTLAR:")
            print(f"  Shape: {matrix.shape}")
            print(f"  Kullanıcı sayısı: {len(matrix.index)}")
            print(f"  Film sayısı: {len(matrix.columns)}")
            
            print(f"\n⭐ VERİ İSTATİSTİKLERİ:")
            print(f"  Toplam hücre: {matrix.size:,}")
            print(f"  Dolu hücre: {matrix.count().sum():,}")
            print(f"  Boş hücre: {matrix.isnull().sum().sum():,}")
            print(f"  Sparsity: %{(matrix.isnull().sum().sum() / matrix.size * 100):.1f}")
            
            # Değer aralığı
            non_null_values = matrix.dropna().values.flatten()
            if len(non_null_values) > 0:
                print(f"\n📈 DEĞER ARALIKLARI:")
                print(f"  Min: {non_null_values.min():.2f}")
                print(f"  Max: {non_null_values.max():.2f}")
                print(f"  Ortalama: {non_null_values.mean():.2f}")
                print(f"  Medyan: {np.median(non_null_values):.2f}")
            
            print(f"\n👀 ÖRNEK VERİ (İlk 5x5):")
            print(matrix.iloc[:5, :5])
            
            # Algoritma tahmini
            if 1 <= non_null_values.min() and non_null_values.max() <= 5:
                algorithm_guess = "Collaborative Filtering (User-Item Rating Matrix)"
                print(f"\n🧠 TAHMİN EDİLEN ALGORİTMA:")
                print(f"  {algorithm_guess}")
                print(f"  - Kullanıcıların filmlere verdiği 1-5 puanları")
                print(f"  - Matrix Factorization için ideal")
                
        elif isinstance(matrix, np.ndarray):
            print(f"📏 NumPy Array - Shape: {matrix.shape}")
            print(f"🔢 Data type: {matrix.dtype}")
            
        elif isinstance(matrix, dict):
            print(f"🔑 Dictionary - Keys: {list(matrix.keys())}")
            
        return matrix
        
    except FileNotFoundError:
        print("❌ user_movie_matrix.pkl dosyası bulunamadı!")
        return None
    except Exception as e:
        print(f"❌ Hata: {e}")
        return None

def analyze_sqlite_database():
    """SQLite database'i direkt bağlantı ile analiz et"""
    print("\n" + "="*50)
    print("🗄️ DATABASE ANALİZİ")
    print("="*50)
    
    # Database dosyasını bul
    db_files = [f for f in os.listdir('.') if f.endswith('.db')]
    
    if not db_files:
        print("❌ .db dosyası bulunamadı!")
        return None
    
    db_file = db_files[0]  # İlk .db dosyasını kullan
    print(f"📁 Database dosyası: {db_file}")
    
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Tabloları listele
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"\n📊 TABLOLAR:")
        for table in tables:
            print(f"  {table[0]}")
        
        # Her tablo için kayıt sayısı
        table_stats = {}
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            table_stats[table_name] = count
            print(f"  {table_name}: {count:,} kayıt")
        
        # Ratings tablosu varsa detaylı analiz
        if 'ratings' in [t[0] for t in tables]:
            cursor.execute("SELECT MIN(rating), MAX(rating), AVG(rating), COUNT(*) FROM ratings")
            stats = cursor.fetchone()
            print(f"\n⭐ RATINGS İSTATİSTİKLERİ:")
            print(f"  Min rating: {stats[0]}")
            print(f"  Max rating: {stats[1]}")
            print(f"  Ortalama: {stats[2]:.2f}")
            print(f"  Toplam: {stats[3]:,}")
            
            # Sparsity hesaplama
            cursor.execute("SELECT COUNT(DISTINCT user_id) FROM ratings")
            unique_users = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(DISTINCT movie_id) FROM ratings")  
            unique_movies = cursor.fetchone()[0]
            
            if unique_users > 0 and unique_movies > 0:
                possible_ratings = unique_users * unique_movies
                actual_ratings = stats[3]
                sparsity = (1 - actual_ratings / possible_ratings) * 100
                print(f"  Sparsity: %{sparsity:.2f}")
                print(f"  Kullanıcı sayısı: {unique_users:,}")
                print(f"  Film sayısı: {unique_movies:,}")
        
        conn.close()
        return table_stats
        
    except Exception as e:
        print(f"❌ Database analiz hatası: {e}")
        return None

def compatibility_check(matrix, db_stats):
    """Matrix ve Database uyumluluğunu kontrol et"""
    print("\n" + "="*50)
    print("🔗 UYUMLULUK KONTROLÜ")
    print("="*50)
    
    if matrix is None or db_stats is None:
        print("❌ Matrix veya Database analizi başarısız - uyumluluk kontrol edilemiyor")
        return False
    
    if isinstance(matrix, pd.DataFrame):
        matrix_users = len(matrix.index)
        matrix_movies = len(matrix.columns)
        matrix_ratings = matrix.count().sum()
        
        print(f"📊 MATRIX:")
        print(f"  Kullanıcı: {matrix_users:,}")
        print(f"  Film: {matrix_movies:,}")
        print(f"  Rating: {matrix_ratings:,}")
        
        if 'ratings' in db_stats:
            db_ratings = db_stats['ratings']
            print(f"\n🗄️ DATABASE:")
            print(f"  Rating: {db_ratings:,}")
            
            print(f"\n🔗 UYUMLULUK:")
            if matrix_ratings > 0 and db_ratings > 0:
                ratio = min(matrix_ratings, db_ratings) / max(matrix_ratings, db_ratings)
                print(f"  Veri benzerlik oranı: %{ratio*100:.1f}")
                
                if ratio > 0.8:
                    print("  ✅ Yüksek uyumluluk - direkt kullanılabilir")
                    return True
                elif ratio > 0.5:
                    print("  ⚠️ Orta uyumluluk - preprocessing gerekebilir")
                    return True
                else:
                    print("  ❌ Düşük uyumluluk - veri senkronizasyonu gerekli")
                    return False
    
    return False

def main():
    """Ana analiz fonksiyonu"""
    print("🚀 SİSTEM ANALİZİ BAŞLIYOR...\n")
    
    # 1. Dosya taraması
    py_files, pkl_files, db_files = find_database_files()
    
    # 2. Matrix analizi
    matrix = analyze_pickle_file()
    
    # 3. Database analizi
    db_stats = analyze_sqlite_database()
    
    # 4. Uyumluluk kontrolü
    is_compatible = compatibility_check(matrix, db_stats)
    
    # 5. Sonuç ve öneri
    print("\n" + "="*50)
    print("🎯 SONUÇ VE ÖNERİLER")
    print("="*50)
    
    if matrix is not None:
        print("✅ Matrix dosyası: Kullanılabilir")
    else:
        print("❌ Matrix dosyası: Sorun var")
    
    if db_stats is not None:
        print("✅ Database: Erişilebilir")
    else:
        print("❌ Database: Sorun var")
    
    if is_compatible:
        print("✅ Uyumluluk: İyi")
        print("\n🚀 ÖNERİ: Option 1 implementation'a başlayabilirsiniz!")
        print("   1. Enhanced Hybrid Engine")
        print("   2. Recommendation Tracking")
        print("   3. TP/FP Evaluation")
    else:
        print("⚠️ Uyumluluk: Düzeltme gerekli")
        print("\n🔧 ÖNERİ: Önce veri senkronizasyonu yapın!")

if __name__ == "__main__":
    main()