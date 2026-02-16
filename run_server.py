#!/usr/bin/env python3
"""
FastAPI Sunucu Başlatıcı
Eksik dosyaları kontrol edip düzeltir, sonra sunucuyu başlatır
"""

import os
import sys
import subprocess
import pickle
import pandas as pd
import numpy as np
from pathlib import Path

def ensure_directory_structure():
    """Gerekli dizinleri oluştur"""
    bitirme2_dir = Path("bitirme2")
    if not bitirme2_dir.exists():
        bitirme2_dir.mkdir()
        print("[+] Created bitirme2/ directory")

def create_dummy_user_movie_matrix():
    """Dummy user-movie matrix oluştur"""
    matrix_path = "bitirme2/user_movie_matrix.pkl"
    
    if not os.path.exists(matrix_path):
        print("[*] Creating dummy user-movie matrix...")
        
        # Dummy data - gerçek veri yerine geçici
        n_users = 50
        n_movies = 100
        
        user_ids = list(range(1, n_users + 1))
        movie_ids = list(range(1, n_movies + 1))
        
        # Sparse matrix oluştur (0-5 arası)
        matrix_data = np.random.choice([0, 0, 0, 0, 3, 4, 5], size=(n_users, n_movies))
        
        df = pd.DataFrame(matrix_data, index=user_ids, columns=movie_ids)
        df.to_pickle(matrix_path)
        
        print(f"[+] Created dummy user-movie matrix: {matrix_data.shape}")
    else:
        print("[+] User-movie matrix already exists")

def create_dummy_advanced_model():
    """Dummy advanced model oluştur"""
    model_path = "bitirme2/kullanıcıoneri.pkl"
    
    if not os.path.exists(model_path):
        print("[*] Creating dummy advanced model...")
        
        # Basit dummy model data
        dummy_model = {
            'model_type': 'dummy',
            'version': '1.0',
            'trained': True,
            'features': ['user_id', 'movie_id'],
            'dummy': True
        }
        
        with open(model_path, 'wb') as f:
            pickle.dump(dummy_model, f)
        
        print("[+] Created dummy advanced model")
    else:
        print("[+] Advanced model already exists")

def create_dummy_trained_model():
    """Dummy trained model oluştur"""
    model_path = "trained_model.pkl"
    
    if not os.path.exists(model_path):
        print("[*] Creating dummy trained model...")
        
        # Basit dummy NMF-style model
        dummy_model = {
            'model_type': 'nmf',
            'n_components': 20,
            'user_factors': np.random.rand(50, 20),
            'item_factors': np.random.rand(100, 20),
            'trained': True
        }
        
        with open(model_path, 'wb') as f:
            pickle.dump(dummy_model, f)
        
        print("[+] Created dummy NMF model")
    else:
        print("[+] Trained model already exists")

def check_database():
    """Veritabanı kontrolü"""
    db_path = "movielens_100k.db"
    
    if not os.path.exists(db_path):
        print("[!] Main database not found. Creating basic structure...")
        # Bu durumda models.py çalıştırılmalı
        try:
            subprocess.run([sys.executable, "bitirme2/models.py"], check=True)
            print("[+] Database created successfully")
        except:
            print("[!] Could not create database automatically")
            return False
    else:
        print("[+] Database exists")
    
    return True

def start_server():
    """FastAPI sunucusunu başlat"""
    print("\n" + "="*60)
    print("STARTING ENHANCED MOVIE RECOMMENDATION SYSTEM")
    print("="*60)
    
    try:
        # Önce bitirme2 dizinine geç
        os.chdir("bitirme2")
        
        # FastAPI uygulamasını başlat
        cmd = [
            sys.executable, 
            "-m", "uvicorn", 
            "app_enhanced_v6:app",
            "--host", "0.0.0.0",
            "--port", "8000", 
            "--reload"  # Auto-reload enabled
        ]
        
        print("[*] Starting server with command:")
        print(f"    {' '.join(cmd)}")
        print("\n[*] Server will be available at:")
        print("    - API: http://localhost:8000")
        print("    - Docs: http://localhost:8000/docs")
        print("    - Frontend: http://localhost:8000/")
        print("\n[*] Press Ctrl+C to stop the server")
        print("="*60)
        
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        print("\n[*] Server stopped by user")
    except Exception as e:
        print(f"[x] Server start failed: {e}")

def main():
    print("FASTAPI SERVER SETUP")
    print("="*40)
    
    # 1. Dizin yapısı
    ensure_directory_structure()
    
    # 2. Eksik dosyaları oluştur
    create_dummy_user_movie_matrix()
    create_dummy_advanced_model()
    create_dummy_trained_model()
    
    # 3. Veritabanı kontrolü
    if not check_database():
        print("[!] Database setup required. Please run: python bitirme2/models.py")
        return
    
    # 4. Sunucu başlat
    start_server()

if __name__ == "__main__":
    main()
