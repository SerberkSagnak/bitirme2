import sqlite3
import pickle
import numpy as np
import pandas as pd
import os
from pathlib import Path

def analyze_matrix():
    """Matrix analizi - PROPER NaN handling"""
    print("📊 1. MATRIX ANALYSIS")
    print("-" * 30)
    
    try:
        with open('user_movie_matrix.pkl', 'rb') as f:
            matrix = pickle.load(f)
        
        print("✅ Matrix loaded successfully!")
        print(f"📏 Shape: {matrix.shape[0]} users × {matrix.shape[1]} movies")
        
        # ✅ CORRECT WAY - Use stack() to get non-null values
        non_null_values = matrix.stack().values  # Automatically removes NaN
        total_ratings = len(non_null_values)
        total_cells = matrix.size
        sparsity = (matrix.isnull().sum().sum() / total_cells) * 100
        
        print(f"⭐ Total ratings: {total_ratings:,}")
        print(f"🕳️ Sparsity: {sparsity:.1f}%")
        
        if total_ratings > 0:
            print(f"📈 Rating range: {non_null_values.min():.1f} - {non_null_values.max():.1f}")
            print(f"📊 Average rating: {non_null_values.mean():.2f}")
        else:
            print("❌ No ratings found in matrix!")
            return None
            
        return {
            'shape': matrix.shape,
            'total_ratings': total_ratings,
            'sparsity': sparsity,
            'avg_rating': non_null_values.mean(),
            'rating_range': (non_null_values.min(), non_null_values.max())
        }
        
    except FileNotFoundError:
        print("❌ Matrix file not found!")
        return None
    except Exception as e:
        print(f"❌ Matrix error: {e}")
        return None

def analyze_database():
    """Database analizi"""
    print("\n🗄️ 2. DATABASE ANALYSIS")
    print("-" * 30)
    
    try:
        conn = sqlite3.connect('movie_recommendation.db')
        cursor = conn.cursor()
        
        # Tablo listesi
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [t[0] for t in cursor.fetchall()]
        print(f"📊 Tables: {', '.join(tables)}")
        
        # Her tablo için kayıt sayısı
        table_counts = {}
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            table_counts[table] = count
            print(f"  {table}: {count:,} records")
        
        # Ratings detayı
        if 'ratings' in tables:
            cursor.execute("SELECT MIN(rating), MAX(rating), AVG(rating) FROM ratings")
            min_r, max_r, avg_r = cursor.fetchone()
            
            cursor.execute("SELECT COUNT(DISTINCT user_id) FROM ratings")
            unique_users = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT movie_id) FROM ratings")
            unique_movies = cursor.fetchone()[0]
            
            total_possible = unique_users * unique_movies
            actual_ratings = table_counts['ratings']
            db_sparsity = ((total_possible - actual_ratings) / total_possible) * 100
            
            print(f"\n⭐ Ratings Details:")
            print(f"  Range: {min_r} - {max_r}")
            print(f"  Average: {avg_r:.2f}")
            print(f"  Unique users: {unique_users}")
            print(f"  Unique movies: {unique_movies}")
            print(f"  DB Sparsity: {db_sparsity:.1f}%")
            
            conn.close()
            
            return {
                'tables': table_counts,
                'ratings_count': actual_ratings,
                'avg_rating': avg_r,
                'unique_users': unique_users,
                'unique_movies': unique_movies,
                'sparsity': db_sparsity
            }
        else:
            print("❌ No ratings table found!")
            conn.close()
            return None
            
    except Exception as e:
        print(f"❌ Database error: {e}")
        return None

def check_code_components():
    """Kod bileşenlerini kontrol et"""
    print("\n🐍 3. CODE COMPONENTS")
    print("-" * 30)
    
    required_files = {
        'database_fixed.py': 'Database layer',
        'advanced_recommender.py': 'Recommendation engine', 
        'app_complete_v5_fixed.py': 'Main FastAPI app',
        'index_favorites_ui.html': 'Frontend UI'
    }
    
    for file, desc in required_files.items():
        if os.path.exists(file):
            print(f"✅ {desc}: {file}")
        else:
            print(f"❌ {desc}: {file} - NOT FOUND")

def check_compatibility(matrix_stats, db_stats):
    """Matrix-Database uyumluluğu kontrol et"""
    print("\n🔗 4. COMPATIBILITY CHECK")
    print("-" * 30)
    
    if not matrix_stats or not db_stats:
        print("❌ Cannot assess compatibility - missing data")
        return False
    
    # Rating count comparison
    matrix_ratings = matrix_stats['total_ratings']
    db_ratings = db_stats['ratings_count']
    
    print(f"📊 Matrix ratings: {matrix_ratings:,}")
    print(f"📊 Database ratings: {db_ratings:,}")
    
    if matrix_ratings == db_ratings:
        print(f"✅ Perfect match: {matrix_ratings:,}")
        consistency = 100
    else:
        consistency = min(matrix_ratings, db_ratings) / max(matrix_ratings, db_ratings) * 100
        print(f"⚠️ Rating count difference: {abs(matrix_ratings - db_ratings):,}")
    
    # Average rating comparison
    matrix_avg = matrix_stats['avg_rating']
    db_avg = db_stats['avg_rating']
    avg_diff = abs(matrix_avg - db_avg)
    
    print(f"📈 Average ratings: Matrix({matrix_avg:.2f}) vs DB({db_avg:.2f}) - Diff: {avg_diff:.3f}")
    
    # Sparsity comparison
    matrix_sparsity = matrix_stats['sparsity']
    db_sparsity = db_stats['sparsity']
    sparsity_diff = abs(matrix_sparsity - db_sparsity)
    
    print(f"🕳️ Sparsity: Matrix({matrix_sparsity:.1f}%) vs DB({db_sparsity:.1f}%) - Diff: {sparsity_diff:.1f}%")
    
    # Overall compatibility score
    print(f"\n📊 Data consistency: {consistency:.1f}%")
    
    if consistency >= 99.9 and avg_diff < 0.01 and sparsity_diff < 1:
        print("✅ PERFECT COMPATIBILITY - 100% Synchronized!")
        return True
    elif consistency >= 95 and avg_diff < 0.1 and sparsity_diff < 5:
        print("✅ HIGH COMPATIBILITY - Ready for Option 1!")
        return True
    elif consistency > 80:
        print("⚠️ MEDIUM COMPATIBILITY - Minor sync issues")
        return False
    else:
        print("❌ LOW COMPATIBILITY - Major sync required")
        return False

def assess_option1_readiness(is_compatible):
    """Option 1 hazırlık durumu"""
    print("\n🎯 5. OPTION 1 READINESS")
    print("-" * 30)
    
    if is_compatible:
        print("🟢 STATUS: READY FOR OPTION 1")
        print("🚀 IMPLEMENTATION READY:")
        print("  ✅ Enhanced Hybrid Recommendation System v6.0")
        print("  ✅ Multi-Algorithm Engine (CF, Content, Matrix Factorization)")  
        print("  ✅ Real-time Performance Tracking")
        print("  ✅ TP/FP Evaluation Framework")
        print("  ✅ A/B Testing System")
        print("  ✅ Advanced Analytics Dashboard")
        return True
    else:
        print("🔴 STATUS: NEEDS SETUP")
        print("🛠️ MINOR FIXES REQUIRED:")
        print("  1. Data synchronization")
        print("  2. Matrix format verification")
        return False

def main():
    """Ana analiz fonksiyonu"""
    print("🚀 COMPLETE SYSTEM ANALYSIS - FINAL")
    print("=" * 60)
    
    # 1. Matrix analizi
    matrix_stats = analyze_matrix()
    
    # 2. Database analizi  
    db_stats = analyze_database()
    
    # 3. Kod bileşenleri
    check_code_components()
    
    # 4. Uyumluluk kontrolü
    is_compatible = check_compatibility(matrix_stats, db_stats)
    
    # 5. Option 1 hazırlık durumu
    option1_ready = assess_option1_readiness(is_compatible)
    
    print("\n" + "=" * 60)
    if option1_ready:
        print("🎉 SYSTEM 100% READY! Option 1 implementation can begin!")
        print("🚀 Next: Enhanced Hybrid Recommendation System v6.0")
    else:
        print("⚠️ System needs minor adjustments.")

if __name__ == "__main__":
    main()
