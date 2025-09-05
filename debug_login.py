import sqlite3

conn = sqlite3.connect('movielens_100k.db')

print('=== LOGIN DEBUG ===')

# Alice kontrol
alice = conn.execute('SELECT id, username, email FROM app_users WHERE username = "alice"').fetchone()
if alice:
    print(f'Alice DB: ID={alice[0]}, Username={alice[1]}, Email={alice[2]}')
    
    alice_ratings = conn.execute('SELECT COUNT(*) FROM user_interactions WHERE user_id = ? AND interaction_type = "rating"', (alice[0],)).fetchone()[0]
    print(f'Alice Ratings: {alice_ratings}')
else:
    print('Alice NOT FOUND!')

# user8 kontrol
user8 = conn.execute('SELECT id, username, email FROM app_users WHERE username = "user8"').fetchone() 
if user8:
    print(f'User8 DB: ID={user8[0]}, Username={user8[1]}, Email={user8[2]}')
    
    user8_ratings = conn.execute('SELECT COUNT(*) FROM user_interactions WHERE user_id = ? AND interaction_type = "rating"', (user8[0],)).fetchone()[0]
    print(f'User8 Ratings: {user8_ratings}')
else:
    print('User8 NOT FOUND!')

# Tüm kullanıcılar
all_users = conn.execute('SELECT id, username FROM app_users ORDER BY id LIMIT 10').fetchall()
print('\nFirst 10 users:')
for user in all_users:
    print(f'  ID {user[0]}: {user[1]}')

conn.close()
