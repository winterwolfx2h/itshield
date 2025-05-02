import mysql.connector
from mysql.connector import Error
import psycopg2
from collections import defaultdict
from utils import query_history, daily_query_stats
import os

def check_database_availability():
    databases = [
        {
            "type": "mysql",
            "host": os.getenv("MYSQL_HOST", "mysql_db"),
            "user": os.getenv("MYSQL_USER", "dbuser"),
            "password": os.getenv("MYSQL_PASSWORD", "dbpass"),
            "database": "employees"
        },
        {
            "type": "postgres",
            "host": os.getenv("POSTGRES_HOST", "postgres_db"),
            "user": os.getenv("POSTGRES_USER", "pguser"),
            "password": os.getenv("POSTGRES_PASSWORD", "pgpass"),
            "database": "itshield"
        }
    ]

    availability_status = defaultdict(dict)

    for db in databases:
        db_type = db["type"]
        db_host = db["host"]
        db_name = db["database"]

        try:
            if db_type == "mysql":
                connection = mysql.connector.connect(
                    host=db_host,
                    user=db["user"],
                    password=db["password"],
                    database=db_name
                )
            else:
                connection = psycopg2.connect(
                    host=db_host,
                    user=db["user"],
                    password=db["password"],
                    database=db_name,
                    port=5432
                )

            if (db_type == "mysql" and connection.is_connected()) or (db_type == "postgres"):
                availability_status[db_host][db_name] = "Available"
                connection.close()
            else:
                availability_status[db_host][db_name] = "Unavailable"
        except (mysql.connector.Error, psycopg2.Error) as err:
            availability_status[db_host][db_name] = f"Unavailable: {err}"
            print(f"Error connecting to {db_host}/{db_name} ({db_type}): {err}")

    return availability_status

def fetch_database_availability():
    availability_status = check_database_availability()
    return query_history, availability_status, daily_query_stats