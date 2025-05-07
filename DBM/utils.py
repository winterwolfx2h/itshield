import mysql.connector
from mysql.connector import Error
import psycopg2
import tailer
import re
from collections import deque, defaultdict
from datetime import datetime
import os

# Use deque to maintain the last 100 queries
query_history = deque(maxlen=100)
daily_query_stats = defaultdict(lambda: defaultdict(int))
processed_queries = set()  # Keep track of processed queries
last_emitted_query = None  # Track the last emitted query

EXCLUDED_QUERIES = [
    "SELECT @@hostname AS device_hostname",
    "SELECT ID, USER, HOST, DB, COMMAND, TIME, STATE",
    "SHOW INDEX",
    "SET GLOBAL general_log = 'OFF'",
    "SET GLOBAL general_log_file",
    "SET GLOBAL general_log = 'ON'",
    "SET autocommit=0",
    "SELECT st.* FROM performance_schema.events_waits_history_long st",
    "SET NAMES utf8mb4",
    "SHOW GLOBAL STATUS",
    "SHOW FULL COLUMNS",
    "SHOW",
    "SELECT pid, usename, application_name, client_addr, state, query FROM pg_stat_activity"
]
EXCLUDED_PREFIXES = [
    "SET GLOBAL general_log_file",
    "SET autocommit",
    "SELECT st.* FROM performance_schema.events_waits_history_long",
    "SET NAMES",
    "SHOW INDEX",
    "SELECT st.*",
    "SHOW FULL COLUMNS",
    "SHOW"
]

def get_db_connection(db_type, host, user, password, database):
    try:
        if db_type == "mysql":
            print(f"Connecting to MySQL: {host}/{database}")
            return mysql.connector.connect(
                host=host,
                user=user,
                password=password,
                database=database
            )
        elif db_type == "postgres":
            print(f"Connecting to PostgreSQL: {host}/{database}")
            return psycopg2.connect(
                host=host,
                user=user,
                password=password,
                database=database,
                port=5432
            )
    except (mysql.connector.Error, psycopg2.Error) as e:
        print(f"Error connecting to {db_type} database {host}/{database}: {e}")
        return None
    return None

def fetch_database_performance(database, db_type="mysql"):
    performance_stats = defaultdict(int)
    host = os.getenv("MYSQL_HOST", "mysql_db") if db_type == "mysql" else os.getenv("POSTGRES_HOST", "postgres_db")
    user = os.getenv("MYSQL_USER", "dbuser") if db_type == "mysql" else os.getenv("POSTGRES_USER", "pguser")
    password = os.getenv("MYSQL_PASSWORD", "dbpass") if db_type == "mysql" else os.getenv("POSTGRES_PASSWORD", "pgpass")
    db_name = database

    try:
        db = get_db_connection(db_type, host, user, password, db_name)
        if not db:
            print(f"No connection for {db_type} performance stats: {db_name}")
            return performance_stats

        cursor = db.cursor() if db_type == "mysql" else db.cursor()

        if db_type == "mysql":
            cursor.execute("SHOW GLOBAL STATUS LIKE 'Queries'")
            result = cursor.fetchone()
            performance_stats['queries'] = int(result[1]) if result else 0

            cursor.execute("SHOW GLOBAL STATUS LIKE 'Connections'")
            result = cursor.fetchone()
            performance_stats['connections'] = int(result[1]) if result else 0

            cursor.execute("SHOW GLOBAL STATUS LIKE 'Uptime'")
            result = cursor.fetchone()
            performance_stats['uptime'] = int(result[1]) if result else 0
        else:
            cursor.execute("SELECT COUNT(*) FROM pg_stat_activity")
            performance_stats['connections'] = cursor.fetchone()[0]

            cursor.execute("SELECT EXTRACT(EPOCH FROM (NOW() - pg_postmaster_start_time()))")
            performance_stats['uptime'] = int(cursor.fetchone()[0])

        cursor.close()
        db.close()
    except (mysql.connector.Error, psycopg2.Error) as e:
        print(f"Error fetching performance data for {database} ({db_type}): {e}")

    return performance_stats

def fetch_database_status(database, db_type="mysql"):
    status_stats = defaultdict(int)
    host = os.getenv("MYSQL_HOST", "mysql_db") if db_type == "mysql" else os.getenv("POSTGRES_HOST", "postgres_db")
    user = os.getenv("MYSQL_USER", "dbuser") if db_type == "mysql" else os.getenv("POSTGRES_USER", "pguser")
    password = os.getenv("MYSQL_PASSWORD", "dbpass") if db_type == "mysql" else os.getenv("POSTGRES_PASSWORD", "pgpass")
    db_name = database

    try:
        db = get_db_connection(db_type, host, user, password, db_name)
        if not db:
            print(f"No connection for {db_type} status stats: {db_name}")
            return status_stats

        cursor = db.cursor() if db_type == "mysql" else db.cursor()

        if db_type == "mysql":
            cursor.execute("SHOW STATUS LIKE 'Threads_connected'")
            result = cursor.fetchone()
            status_stats['threads_connected'] = int(result[1]) if result else 0

            cursor.execute("SHOW STATUS LIKE 'Threads_running'")
            result = cursor.fetchone()
            status_stats['threads_running'] = int(result[1]) if result else 0

            cursor.execute("SHOW STATUS LIKE 'Uptime'")
            result = cursor.fetchone()
            status_stats['uptime'] = int(result[1]) if result else 0
        else:
            cursor.execute("SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active'")
            status_stats['threads_running'] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM pg_stat_activity")
            status_stats['threads_connected'] = cursor.fetchone()[0]

            cursor.execute("SELECT EXTRACT(EPOCH FROM (NOW() - pg_postmaster_start_time()))")
            status_stats['uptime'] = int(cursor.fetchone()[0])

        cursor.close()
        db.close()
    except (mysql.connector.Error, psycopg2.Error) as e:
        print(f"Error fetching status data for {database} ({db_type}): {e}")

    return status_stats

def is_excluded_query(query):
    query_lower = query.lower()
    if any(query_lower == excluded_query.lower() for excluded_query in EXCLUDED_QUERIES):
        return True
    if any(query_lower.startswith(prefix.lower()) for prefix in EXCLUDED_PREFIXES):
        return True
    return False

def fetch_process_list(db_type="mysql"):
    try:
        host = os.getenv("MYSQL_HOST", "mysql_db") if db_type == "mysql" else os.getenv("POSTGRES_HOST", "postgres_db")
        user = os.getenv("MYSQL_USER", "dbuser") if db_type == "mysql" else os.getenv("POSTGRES_USER", "pguser")
        password = os.getenv("MYSQL_PASSWORD", "dbpass") if db_type == "mysql" else os.getenv("POSTGRES_PASSWORD", "pgpass")
        database = "employees" if db_type == "mysql" else "itshield"
        log_path = "/var/log/mysql/mysql.log" if db_type == "mysql" else "/var/log/postgres/postgres.log"

        print(f"Fetching process list for {db_type} at {log_path}")
        if not os.path.exists(log_path):
            print(f"Log file {log_path} does not exist")
            return list(query_history), [], daily_query_stats

        db = get_db_connection(db_type, host, user, password, database)
        if not db:
            print(f"Failed to connect to {db_type} database {host}/{database}")
            return list(query_history), [], daily_query_stats

        cursor = db.cursor() if db_type == "mysql" else db.cursor()

        if db_type == "mysql":
            cursor.execute("SET GLOBAL general_log = 'OFF';")
            cursor.execute("SET GLOBAL general_log_file = '/var/log/mysql/mysql.log';")
            cursor.execute("SET GLOBAL general_log = 'ON';")

            cursor.execute("SELECT @@hostname AS device_hostname;")
            hostname = cursor.fetchone()[0]

            cursor.execute("""
                SELECT ID, USER, HOST, DB, COMMAND, TIME, STATE
                FROM INFORMATION_SCHEMA.PROCESSLIST;
            """)
            processes = cursor.fetchall()
        else:
            cursor.execute("SELECT inet_server_addr() AS device_hostname")
            hostname = cursor.fetchone()[0] or "postgres_db"

            cursor.execute("""
                SELECT pid, usename, application_name, client_addr, state, query
                FROM pg_stat_activity
                WHERE pid != pg_backend_pid();
            """)
            processes = [(row[0], row[1], row[3] or '', row[2], row[4], 0, row[5]) for row in cursor.fetchall()]

        log_entries = tailer.tail(open(log_path, 'r'), 100)
        print(f"Read {len(log_entries)} log entries from {log_path}")

        query_logs = []
        log_entry_pattern = re.compile(
            r'(?P<time>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z)\s+(?P<id>\d+)\s+Query\s+(?P<query>.*)' if db_type == "mysql"
            else r'(?P<time>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3}\s+UTC)\s+\[\d+\]\s+LOG:\s+statement:\s+(?P<query>.*)'
        )
        non_query_pattern = re.compile(
            r'(?P<time>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z)\s+(?P<id>\d+)\s+(?P<command>Connect|Quit)\s+(?P<details>.*)' if db_type == "mysql"
            else r'(?P<time>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3}\s+UTC)\s+\[\d+\]\s+LOG:\s+(?P<command>connection\s+received|disconnection):.*'
        )

        global last_emitted_query
        new_entries = []

        combined_query = ""
        combined_time = ""
        combined_pid = ""

        for entry in log_entries:
            if entry in processed_queries:
                continue
            if "Query" in entry or (db_type == "postgres" and "LOG:  statement:" in entry):
                if combined_query:
                    combined_query = combined_query.strip()
                    query_logs.append((hostname, combined_pid, combined_time, combined_query))
                    new_entries.append((hostname, combined_pid, combined_time, combined_query))
                    combined_query = ""
                    combined_time = ""
                    combined_pid = ""

                match = log_entry_pattern.search(entry)
                if match:
                    time, query = match.group('time'), match.group('query')
                    pid = match.group('id') if db_type == "mysql" else ""
                    formatted_time = datetime.strptime(time, '%Y-%m-%dT%H:%M:%S.%fZ' if db_type == "mysql" else '%Y-%m-%d %H:%M:%S.%f UTC').strftime('%Y-%m-%d %H:%M:%S')
                    if is_excluded_query(query):
                        continue
                    processed_queries.add(entry)
                    combined_query = query
                    combined_time = formatted_time
                    combined_pid = pid

                    query_date = datetime.strptime(time, '%Y-%m-%dT%H:%M:%S.%fZ' if db_type == "mysql" else '%Y-%m-%d %H:%M:%S.%f UTC').strftime('%Y-%m-%d')
                    query_upper = query.upper()
                    if query_upper.startswith("SELECT"):
                        daily_query_stats[query_date]["SELECT"] += 1
                    elif query_upper.startswith("INSERT"):
                        daily_query_stats[query_date]["INSERT"] += 1
                    elif query_upper.startswith("UPDATE"):
                        daily_query_stats[query_date]["UPDATE"] += 1
                    elif query_upper.startswith("DELETE"):
                        daily_query_stats[query_date]["DELETE"] += 1
                    elif query_upper.startswith("CREATE"):
                        daily_query_stats[query_date]["CREATE"] += 1
                    elif query_upper.startswith("ALTER"):
                        daily_query_stats[query_date]["ALTER"] += 1
                    elif query_upper.startswith("DROP"):
                        daily_query_stats[query_date]["DROP"] += 1
            else:
                match = non_query_pattern.search(entry)
                if not match:
                    combined_query += " " + entry.strip()

        if combined_query:
            combined_query = combined_query.strip()
            query_logs.append((hostname, combined_pid, combined_time, combined_query))
            new_entries.append((hostname, combined_pid, combined_time, combined_query))

        enhanced_data = []
        for process in processes:
            pid = str(process[0])
            for log in new_entries:
                if (db_type == "mysql" and log[1] == pid) or (db_type == "postgres"):
                    enhanced_data.append((hostname, *process, log[2], log[3]))
                    query_history.append((hostname, *process, log[2], log[3]))

        cursor.close()
        db.close()

        if last_emitted_query is None:
            last_emitted_query = query_logs[-1] if query_logs else None
        else:
            new_queries = [log for log in query_logs if log > last_emitted_query]
            if new_queries:
                last_emitted_query = new_queries[-1]

        print(f"Returning {db_type} data: {len(enhanced_data)} enhanced, {len(query_logs)} logs")
        return list(query_history), query_logs, daily_query_stats

    except (mysql.connector.Error, psycopg2.Error, OSError) as e:
        print(f"Error during fetch or emit for {db_type}: {e}")
        return list(query_history), [], daily_query_stats