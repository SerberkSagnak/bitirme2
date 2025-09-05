import sqlite3

conn = sqlite3.connect('movielens_100k.db')
users = conn.execute('SELECT id, username, hashed_password FROM app_users LIMIT 5').fetchall()
print('Mevcut kullanicilar:')
for user in users:
    pwd_preview = user[2][:30] if user[2] else 'None'
    print(f'  User {user[0]}: {user[1]} -> Password: {pwd_preview}')
conn.close()
