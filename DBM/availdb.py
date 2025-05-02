import mysql.connector
import psycopg2
from mysql.connector import Error as MySQLError
from psycopg2 import Error as PostgresError
from collections import defaultdict
from utils import query_history, daily_query_stats
from db_manager import get_connections

def check_database_availability():
    databases = get_connections()
    availability_status = defaultdict(dict)

    for db in databases:
        db_host = db["host"]
        db_name = db["database_name"]
        try:
            if db["db_type"] == "mysql":
                connection = mysql.connector.connect(
                    host=db["host"],
                    port=db["port"],
                    user=db["username"],
                    password=db["password"],
                    database=db["database_name"]
                )
            elif db["db_type"] == "postgres":
                connection = psycopg2.connect(
                    host=db["host"],
                    port=db["port"],
                    user=db["username"],
                    password=db["password"],
                    dbname=db["database_name"]
                )
            if (db["db_type"] == "mysql" and connection.is_connected()) or (db["db_type"] == "postgres"):
                availability_status[db_host][db_name] = "Available"
                connection.close()
            else:
                availability_status[db_host][db_name] = "Unavailable"
        except (MySQLError, PostgresError) as err:
            availability_status[db_host][db_name] = f"Unavailable: {err}"
            print(f"Error connecting to {db_host}/{db_name}: {err}")

    return availability_status

def fetch_database_availability():
    availability_status = check_database_availability()
    return query_history, availability_status, daily_query_stats