import sqlite3

conn = sqlite3.connect('movie_recommendation.db')
cursor = conn.cursor()

print("🔍 İlk 5 film:")
cursor.execute("SELECT id, title FROM movies LIMIT 5")
for row in cursor.fetchall():
    print(f"ID: {row[0]}, Title: {row[1]}")

print("\n🔍 'a' harfi içeren filmler:")
cursor.execute("SELECT title FROM movies WHERE title LIKE '%a%' LIMIT 5")
for (title,) in cursor.fetchall():
    print(f"Title: {title}")

print("\n🔍 Toplam film sayısı:")
cursor.execute("SELECT COUNT(*) FROM movies")
count = cursor.fetchone()[0]
print(f"Total movies: {count}")

conn.close()