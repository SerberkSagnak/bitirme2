import sqlite3

conn = sqlite3.connect('movielens_100k.db')

print('DATABASE STATUS:')

try:
    users = conn.execute('SELECT COUNT(*) FROM app_users').fetchone()[0]
    print(f'Users: {users}')
except:
    print('Users: ERROR')

try:
    movies = conn.execute('SELECT COUNT(*) FROM movies').fetchone()[0] 
    print(f'Movies: {movies}')
except:
    print('Movies: ERROR')

try:
    ratings = conn.execute('SELECT COUNT(*) FROM user_interactions').fetchone()[0]
    print(f'Ratings: {ratings}')
except:
    print('Ratings: ERROR')

# Sample user check
try:
    sample_user = conn.execute('SELECT username FROM app_users LIMIT 1').fetchone()
    if sample_user:
        print(f'Sample user: {sample_user[0]}')
    else:
        print('No users found')
except:
    print('User query error')

conn.close()
