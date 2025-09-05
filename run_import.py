#!/usr/bin/env python3

import sys
import os
sys.path.append('.')

from import_existing_movielens import MovieLensImporter

def quick_import():
    """Hızlı import - varsayılan ayarlarla"""
    
    # MovieLens dizinini kontrol et
    possible_paths = [
        'ml-100k',
        '../ml-100k', 
        'data/ml-100k',
        './ml-100k'
    ]
    
    data_path = None
    for path in possible_paths:
        if os.path.exists(path):
            data_path = path
            break
    
    if not data_path:
        print("❌ MovieLens 100k dizini bulunamadı!")
        print("Kontrol edilen dizinler:")
        for path in possible_paths:
            print(f"  - {path}")
        return False
    
    print(f"✅ MovieLens dizini bulundu: {data_path}")
    
    # Import et
    importer = MovieLensImporter(data_path)
    
    if importer.import_all():
        importer.show_summary()
        return True
    else:
        return False

if __name__ == "__main__":
    print("🚀 MovieLens 100k Hızlı Import")
    print("="*40)
    
    if quick_import():
        print("\n🎉 Import tamamlandı!")
        print("📝 Artık sistemde şunlar var:")
        print("   - 943 kullanıcı")
        print("   - 1682 film") 
        print("   - 100,000 puanlama")
        print("\n💡 Sistemi test etmek için:")
        print("   python -m uvicorn app_enhanced_v6:app --reload")
    else:
        print("\n❌ Import başarısız!")