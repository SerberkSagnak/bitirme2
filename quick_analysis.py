def quick_system_analysis():
    """Tüm sistem analizini tek seferde yap"""
    
    print("🚀 Hızlı Sistem Analizi\n" + "="*50)
    
    # 1. Model analizi
    print("\n1️⃣ MODEL ANALİZİ:")
    try:
        matrix = analyze_user_movie_matrix()
        if matrix is not None:
            algorithm_type = detect_model_algorithm(matrix)
    except:
        print("❌ Model analizi başarısız")
    
    # 2. Database analizi  
    print("\n2️⃣ DATABASE ANALİZİ:")
    try:
        db_stats = analyze_database()
    except:
        print("❌ Database analizi başarısız")
    
    # 3. Uyumluluk kontrolü
    print("\n3️⃣ UYUMLULUK KONTROLÜ:")
    try:
        compatibility = check_matrix_database_compatibility()
    except:
        print("❌ Uyumluluk kontrolı başarısız")
    
    # 4. Öneri
    print("\n🎯 SONUÇ VE ÖNERİ:")
    print("Bu analizlere göre Option 1 implementation stratejisi belirlenecek!")

if __name__ == "__main__":
    quick_system_analysis()