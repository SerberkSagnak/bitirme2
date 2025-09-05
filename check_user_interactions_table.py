import sqlite3

print("🔍 USER_INTERACTIONS TABLOSU YAPISI KONTROLÜ")
print("="*50)

conn = sqlite3.connect('movielens_100k.db')
cursor = conn.cursor()

# Tablo yapısını kontrol et
cursor.execute("PRAGMA table_info(user_interactions)")
columns = cursor.fetchall()

print("📋 Sütunlar:")
for col in columns:
    print(f"   {col[1]} ({col[2]})")

# Örnek veri
cursor.execute("SELECT * FROM user_interactions LIMIT 5")
samples = cursor.fetchall()

print("\n📄 Örnek veriler:")
for sample in samples:
    print(f"   {sample}")

conn.close()
print("="*50)