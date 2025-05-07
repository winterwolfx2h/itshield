import mysql.connector
import psycopg2
from utils import mysql_query_history, postgres_query_history, mysql_query_logs, postgres_query_logs, daily_query_stats
import os

def fetch_database_availability():
    mysql_databases = []
    postgres_databases = []
    availability_status = {'mysql': {}, 'postgres': {}}

    try:
        mysql_host = os.getenv("MYSQL_HOST", "mysql_db")
        mysql_user = os.getenv("MYSQL_USER", "dbuser")
        mysql_password = os.getenv("MYSQL_PASSWORD", "dbpass")
        
        mysql_conn = mysql.connector.connect(
            host=mysql_host,
            user=mysql_user,
            password=mysql_password
        )
        mysql_cursor = mysql_conn.cursor()
        mysql_cursor.execute("SHOW DATABASES")
        mysql_databases = [row[0] for row in mysql_cursor.fetchall()]
        mysql_cursor.close()
        mysql_conn.close()
    except mysql.connector.Error as e:
        print(f"Error connecting to MySQL: {e}")

    try:
        postgres_host = os.getenv("POSTGRES_HOST", "postgres_db")
        postgres_user = os.getenv("POSTGRES_USER", "pguser")
        postgres_password = os.getenv("POSTGRES_PASSWORD", "pgpass")
        
        postgres_conn = psycopg2.connect(
            host=postgres_host,
            user=postgres_user,
            password=postgres_password,
            database="postgres"
        )
        postgres_cursor = postgres_conn.cursor()
        postgres_cursor.execute("SELECT datname FROM pg_database WHERE datistemplate = false")
        postgres_databases = [row[0] for row in postgres_cursor.fetchall()]
        postgres_cursor.close()
        postgres_conn.close()
    except psycopg2.Error as e:
        print(f"Error connecting to PostgreSQL: {e}")

    for db in mysql_databases:
        availability_status['mysql'][db] = {
            'status': 'online' if db in mysql_databases else 'offline',
            'query_history': list(mysql_query_history),
            'query_logs': list(mysql_query_logs),
            'daily_query_stats': daily_query_stats
        }

    for db in postgres_databases:
        availability_status['postgres'][db] = {
            'status': 'online' if db in postgres_databases else 'offline',
            'query_history': list(postgres_query_history),
            'query_logs': list(postgres_query_logs),
            'daily_query_stats': daily_query_stats
        }

    return mysql_databases, availability_status, postgres_databases