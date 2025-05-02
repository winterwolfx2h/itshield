import sqlite3
import os
from cryptography.fernet import Fernet

# Generate or load encryption key
key_path = "/app/encryption_key.key"
if not os.path.exists(key_path):
    key = Fernet.generate_key()
    with open(key_path, "wb") as key_file:
        key_file.write(key)
else:
    with open(key_path, "rb") as key_file:
        key = key_file.read()
cipher = Fernet(key)

def init_db():
    conn = sqlite3.connect("/app/connections.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            db_type TEXT NOT NULL,
            host TEXT NOT NULL,
            port INTEGER NOT NULL,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            database_name TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def add_connection(name, db_type, host, port, username, password, database_name):
    encrypted_password = cipher.encrypt(password.encode()).decode()
    conn = sqlite3.connect("/app/connections.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO connections (name, db_type, host, port, username, password, database_name)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name, db_type, host, port, username, encrypted_password, database_name))
    conn.commit()
    conn.close()

def get_connections():
    conn = sqlite3.connect("/app/connections.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, db_type, host, port, username, password, database_name FROM connections")
    rows = cursor.fetchall()
    connections = []
    for row in rows:
        decrypted_password = cipher.decrypt(row[6].encode()).decode()
        connections.append({
            "id": row[0],
            "name": row[1],
            "db_type": row[2],
            "host": row[3],
            "port": row[4],
            "username": row[5],
            "password": decrypted_password,
            "database_name": row[7]
        })
    conn.close()
    return connections

def get_connection_by_id(conn_id):
    conn = sqlite3.connect("/app/connections.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, db_type, host, port, username, password, database_name FROM connections WHERE id = ?", (conn_id,))
    row = cursor.fetchone()
    if row:
        decrypted_password = cipher.decrypt(row[6].encode()).decode()
        connection = {
            "id": row[0],
            "name": row[1],
            "db_type": row[2],
            "host": row[3],
            "port": row[4],
            "username": row[5],
            "password": decrypted_password,
            "database_name": row[7]
        }
        conn.close()
        return connection
    conn.close()
    return None
