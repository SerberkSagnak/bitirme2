import sqlite3

conn = sqlite3.connect('movielens_100k.db')

print('=== MEVCUT KULLANICILAR ===')
users = conn.execute('SELECT id, username, email FROM app_users').fetchall()

for user in users:
    print(f'ID {user[0]}: {user[1]} ({user[2]})')

print('')
print('Sifre test:')
test_passwords = ['test123', 'admin', '123456', 'password']

for user in users:
    username = user[1]
    for pwd in test_passwords:
        try:
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            
            # Get hashed password
            hashed = conn.execute('SELECT hashed_password FROM app_users WHERE username = ?', (username,)).fetchone()[0]
            
            if pwd_context.verify(pwd, hashed):
                print(f'✅ {username}: {pwd}')
                break
        except:
            continue

conn.close()
