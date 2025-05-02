import mysql.connector
import psycopg2
from mysql.connector import Error as MySQLError
from psycopg2 import Error as PostgresError
import tailer
import re
from collections import deque, defaultdict
from datetime import datetime
import os

# Use deque to maintain the last 100 queries
query_history = deque(maxlen=100)
daily_query_stats = defaultdict(lambda: defaultdict(int))
processed_queries = set()
last_emitted_query = None

EXCLUDED_QUERIES = [
    "SELECT @@hostname AS device_hostname",
    "SELECT ID, USER, HOST, DB, COMMAND, TIME, STATE",
    "SHOW INDEX",
    "SET GLOBAL general_log = 'OFF'",
    "SET GLOBAL general_log_file",
    "SET GLOBAL general_log = 'ON'",
    "SET @@session.autocommit = OFF",
    "SET autocommit=0",
    "SELECT st.* FROM performance_schema.events_waits_history_long st",
    "SET NAMES utf8mb4",
    "SHOW GLOBAL STATUS",
    "SHOW FULL COLUMNS",
    "SHOW"
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

def is_excluded_query(query):
    query_lower = query.lower()
    if any(query_lower == excluded_query.lower() for excluded_query in EXCLUDED_QUERIES):
        return True
    if any(query_lower.startswith(prefix.lower()) for prefix in EXCLUDED_PREFIXES):
        return True
    return False

def fetch_process_list(connection):
    try:
        db_type = connection['db_type']
        if db_type == 'mysql':
            db = mysql.connector.connect(
                host=connection['host'],
                port=connection['port'],
                user=connection['username'],
                password=connection['password'],
                database=connection['database_name']
            )
            cursor = db.cursor()
            cursor.execute("SELECT @@hostname AS device_hostname;")
            hostname = cursor.fetchone()[0]
            process_query = """
                SELECT ID, USER, HOST, DB, COMMAND, TIME, STATE
                FROM INFORMATION_SCHEMA.PROCESSLIST;
            """
            log_path = "/var/log/mysql/mysql.log"
        elif db_type == 'postgres':
            db = psycopg2.connect(
                host=connection['host'],
                port=connection['port'],
                user=connection['username'],
                password=connection['password'],
                dbname=connection['database_name']
            )
            cursor = db.cursor()
            cursor.execute("SELECT inet_server_addr() AS device_hostname;")
            hostname = cursor.fetchone()[0]
            process_query = """
                SELECT pid, usename, client_addr, datname, state, EXTRACT(EPOCH FROM (NOW() - query_start)) AS time, query
                FROM pg_stat_activity WHERE state != 'idle';
            """
            log_path = "/var/log/postgres/postgres.log"
        else:
            raise ValueError("Unsupported database type")

        print(f"Retrieved hostname: {hostname}")
        cursor.execute(process_query)
        processes = cursor.fetchall()
        print(f"Retrieved {len(processes)} processes")

        try:
            log_entries = tailer.tail(open(log_path, 'r'), 100)
            print(f"Read {len(log_entries)} log entries")
            print("Raw log entries:", log_entries)
        except FileNotFoundError:
            print(f"Log file not found: {log_path}")
            log_entries = []

        query_logs = []
        log_entry_pattern = re.compile(r'(?P<time>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{0,6}Z)\s+(?P<id>\d+)\s+Query\s+(?P<query>.*)')
        non_query_pattern = re.compile(r'(?P<time>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{0,6}Z)\s+(?P<id>\d+)\s+(?P<command>Connect|Quit)\s+(?P<details>.*)')

        global last_emitted_query
        new_entries = []

        combined_query = ""
        combined_time = ""
        combined_pid = ""

        for entry in log_entries:
            if entry in processed_queries:
                continue
            if "Query" in entry:
                if combined_query:
                    combined_query = combined_query.strip()
                    query_logs.append((hostname, combined_pid, combined_time, combined_query))
                    new_entries.append((hostname, combined_pid, combined_time, combined_query))
                    combined_query = ""
                    combined_time = ""
                    combined_pid = ""

                match = log_entry_pattern.search(entry)
                if match:
                    time, pid, query = match.groups()
                    print(f"Matched query: {query}")
                    formatted_time = datetime.strptime(time, '%Y-%m-%dT%H:%M:%S.%fZ').strftime('%Y-%m-%d %H:%M:%S')
                    if is_excluded_query(query):
                        print(f"Excluded query: {query}")
                        continue
                    processed_queries.add(entry)
                    combined_query = query
                    combined_time = formatted_time
                    combined_pid = pid

                    query_date = datetime.strptime(time, '%Y-%m-%dT%H:%M:%S.%fZ').strftime('%Y-%m-%d')
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
                if log[1] == pid:
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

        print(f"Returning {len(query_history)} history items, {len(query_logs)} logs, {len(daily_query_stats)} stats")
        return list(query_history), query_logs, daily_query_stats

    except (MySQLError, PostgresError, ValueError) as e:
        print(f"Error during fetch or emit: {e}")
        return list(query_history), [], daily_query_stats