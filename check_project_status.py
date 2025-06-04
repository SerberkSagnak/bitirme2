import os
import subprocess
import sys

def check_project_structure():
    """Proje yapısını kontrol et"""
    print("🏗️ PROJE YAPISINI KONTROL EDİYORUZ...\n")
    
    current_dir = os.getcwd()
    print(f"📍 Şu anki dizin: {current_dir}")
    
    # Tüm dosyaları listele
    all_files = []
    for root, dirs, files in os.walk('.'):
        for file in files:
            full_path = os.path.join(root, file)
            all_files.append(full_path)
    
    print(f"\n📄 TÜM DOSYALAR ({len(all_files)} adet):")
    
    # Dosya türlerine göre grupla
    python_files = [f for f in all_files if f.endswith('.py')]
    html_files = [f for f in all_files if f.endswith('.html')]
    pkl_files = [f for f in all_files if f.endswith('.pkl') or f.endswith('.joblib')]
    db_files = [f for f in all_files if f.endswith('.db') or f.endswith('.sqlite')]
    json_files = [f for f in all_files if f.endswith('.json')]
    csv_files = [f for f in all_files if f.endswith('.csv')]
    
    print(f"\n🐍 Python dosyaları ({len(python_files)}):")
    for f in python_files:
        print(f"  {f}")
    
    if html_files:
        print(f"\n🌐 HTML dosyaları ({len(html_files)}):")
        for f in html_files:
            print(f"  {f}")
    
    if pkl_files:
        print(f"\n🗃️ Model dosyaları ({len(pkl_files)}):")
        for f in pkl_files:
            print(f"  {f}")
    else:
        print(f"\n❌ Model dosyaları bulunamadı!")
    
    if db_files:
        print(f"\n🗄️ Database dosyaları ({len(db_files)}):")
        for f in db_files:
            print(f"  {f}")
    else:
        print(f"\n❌ Database dosyaları bulunamadı!")
    
    if csv_files:
        print(f"\n📊 CSV dosyaları ({len(csv_files)}):")
        for f in csv_files:
            print(f"  {f}")
    
    return {
        'python_files': python_files,
        'model_files': pkl_files,
        'database_files': db_files,
        'data_files': csv_files,
        'html_files': html_files
    }

def check_main_project_files():
    """Ana proje dosyalarını kontrol et"""
    print("\n" + "="*50)
    print("🔍 ANA PROJE DOSYALARI KONTROLÜ")
    print("="*50)
    
    expected_files = [
        'main.py',
        'app.py', 
        'database.py',
        'database_fixed.py',
        'advanced_recommender.py',
        'index_favorites_ui.html',
        'movie_recommendation.db',
        'user_movie_matrix.pkl'
    ]
    
    found_files = []
    missing_files = []
    
    for expected in expected_files:
        if os.path.exists(expected):
            found_files.append(expected)
            print(f"✅ {expected}")
        else:
            missing_files.append(expected)
            print(f"❌ {expected}")
    
    print(f"\n📊 DURUM:")
    print(f"  Bulunan: {len(found_files)}/{len(expected_files)}")
    print(f"  Eksik: {len(missing_files)}")
    
    return found_files, missing_files

def check_if_server_running():
    """FastAPI server çalışıyor mu kontrol et"""
    print("\n" + "="*50)
    print("🌐 SERVER DURUMU KONTROLÜ")
    print("="*50)
    
    try:
        import requests
        response = requests.get('http://localhost:8000', timeout=2)
        print("✅ Server çalışıyor!")
        return True
    except:
        print("❌ Server çalışmıyor veya ulaşılamıyor")
        return False

def suggest_next_steps(found_files, missing_files):
    """Sonraki adımları öner"""
    print("\n" + "="*50)
    print("🎯 SONRAKİ ADIMLAR")
    print("="*50)
    
    if 'index_favorites_ui.html' in found_files:
        print("✅ UI dosyası mevcut")
        
    if any('database' in f for f in found_files):
        print("✅ Database modülü mevcut")
    else:
        print("❌ Database modülü eksik")
        
    if any('advanced_recommender' in f or 'recommender' in f for f in found_files):
        print("✅ Recommendation engine mevcut")
    else:
        print("❌ Recommendation engine eksik")
        
    print("\n🚀 ÖNERİLER:")
    
    if len(missing_files) == len(['movie_recommendation.db', 'user_movie_matrix.pkl']):
        print("📋 SENARYO 1: Kod hazır, data eksik")
        print("  1. Database oluştur ve movie/rating verisi yükle")
        print("  2. Model eğit ve .pkl dosyası oluştur")
        print("  3. Option 1 implementation başlat")
        
    elif len(missing_files) > 4:
        print("📋 SENARYO 2: Proje henüz kurulmamış")
        print("  1. Önce temel sistem kurulumu yap")
        print("  2. Database ve model oluştur")
        print("  3. Sonra Option 1'e geç")
        
    else:
        print("📋 SENARYO 3: Kısmi kurulum")
        print("  1. Eksik dosyaları tamamla")
        print("  2. Sistem test et")
        print("  3. Option 1 başlat")

def main():
    """Ana kontrol fonksiyonu"""
    print("🔍 PROJENİN TAM DURUMUNU KONTROL EDİYORUZ...\n")
    
    # 1. Dosya yapısı kontrolü
    file_structure = check_project_structure()
    
    # 2. Ana dosyalar kontrolü
    found_files, missing_files = check_main_project_files()
    
    # 3. Server kontrolü
    server_running = check_if_server_running()
    
    # 4. Öneriler
    suggest_next_steps(found_files, missing_files)
    
    # 5. Sonuç özeti
    print("\n" + "="*50)
    print("📋 ÖZET")
    print("="*50)
    
    if len(found_files) >= 6:
        print("🟢 DURUM: Sistem büyük ölçüde hazır")
        print("🎯 AKSİYON: Option 1 için veri hazırlığı")
    elif len(found_files) >= 3:
        print("🟡 DURUM: Sistem kısmen hazır") 
        print("🎯 AKSİYON: Eksik bileşenleri tamamla")
    else:
        print("🔴 DURUM: Sistem kurulum aşamasında")
        print("🎯 AKSİYON: Temel kurulumdan başla")

if __name__ == "__main__":
    main()