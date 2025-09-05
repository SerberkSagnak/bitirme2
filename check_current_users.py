import sqlite3

conn = sqlite3.connect('movielens_100k.db')

print('=== CURRENT USERS ===')
users = conn.execute('SELECT id, username, email FROM app_users LIMIT 10').fetchall()

for user in users:
    print(f'ID {user[0]}: {user[1]} - {user[2]}')

print(f'\nTotal users: {len(users)}')

# Check if we need to create test user
if len(users) == 0:
    print('No users found - need to create!')
elif len(users) < 10:
    print('Very few users - MovieLens import may have failed')
    
    # Create Alice for testing
    print('\nCreating Alice test user...')
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    try:
        alice_password = pwd_context.hash('test123')
        conn.execute("""
            INSERT INTO app_users (username, email, hashed_password, age, gender)
            VALUES ('alice', 'alice@test.com', ?, 25, 'F')
        """, (alice_password,))
        conn.commit()
        print('✅ Alice created successfully')
        print('Login: alice / test123')
    except Exception as e:
        print(f'Alice creation error: {e}')

conn.close()
