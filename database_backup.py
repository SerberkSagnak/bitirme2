import os
import subprocess
import datetime
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseBackup:
    def __init__(self):
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
        
        # Database config
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'movielens_recommendation_db'),
            'username': os.getenv('DB_USER', 'movie_admin'),
            'password': os.getenv('DB_PASSWORD', 'secure_movie_pass_2024')
        }
    
    def create_backup(self):
        """Veritabanı yedeği oluştur"""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"movielens_backup_{timestamp}.sql"
            
            logger.info(f"💾 Backup oluşturuluyor: {backup_file}")
            
            # pg_dump komutu
            cmd = [
                'pg_dump',
                '-h', self.db_config['host'],
                '-p', self.db_config['port'],
                '-U', self.db_config['username'],
                '-d', self.db_config['database'],
                '-f', str(backup_file),
                '--verbose',
                '--no-password'
            ]
            
            # Environment variable for password
            env = os.environ.copy()
            env['PGPASSWORD'] = self.db_config['password']
            
            # Execute backup
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Get file size
                size_mb = backup_file.stat().st_size / (1024 * 1024)
                logger.info(f"✅ Backup başarılı: {backup_file} ({size_mb:.2f} MB)")
                return str(backup_file)
            else:
                logger.error(f"❌ Backup hatası: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Backup exception: {e}")
            return None
    
    def restore_backup(self, backup_file):
        """Backup'tan veritabanını geri yükle"""
        try:
            if not os.path.exists(backup_file):
                logger.error(f"❌ Backup dosyası bulunamadı: {backup_file}")
                return False
            
            logger.info(f"🔄 Backup geri yükleniyor: {backup_file}")
            
            # Drop existing database (dikkatli!)
            logger.info("⚠️ Mevcut veritabanı siliniyor...")
            
            # psql komutu
            cmd = [
                'psql',
                '-h', self.db_config['host'],
                '-p', self.db_config['port'],
                '-U', self.db_config['username'],
                '-d', 'postgres',  # Connect to postgres db to drop target db
                '-c', f"DROP DATABASE IF EXISTS {self.db_config['database']};"
            ]
            
            env = os.environ.copy()
            env['PGPASSWORD'] = self.db_config['password']
            
            subprocess.run(cmd, env=env, check=True)
            
            # Create new database
            cmd[5] = f"CREATE DATABASE {self.db_config['database']};"
            subprocess.run(cmd, env=env, check=True)
            
            # Restore from backup
            cmd = [
                'psql',
                '-h', self.db_config['host'], 
                '-p', self.db_config['port'],
                '-U', self.db_config['username'],
                '-d', self.db_config['database'],
                '-f', backup_file
            ]
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("✅ Backup geri yükleme başarılı!")
                return True
            else:
                logger.error(f"❌ Restore hatası: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Restore exception: {e}")
            return False