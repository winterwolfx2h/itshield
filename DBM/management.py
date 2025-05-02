from flask import Blueprint, render_template, request, jsonify
import mysql.connector
import psycopg2
import subprocess
import platform

management_bp = Blueprint('management', __name__)

databases = []

@management_bp.route('/')
def management():
    return render_template('management.html', databases=databases)

@management_bp.route('/add_database', methods=['POST'])
def add_database():
    db_type = request.form['type']
    host = request.form['host']
    port = request.form['port']
    user = request.form['user']
    password = request.form['password']
    database = request.form['database']
    
    try:
        if db_type == "mysql":
            connection = mysql.connector.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database
            )
        else:
            connection = psycopg2.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database
            )

        if (db_type == "mysql" and connection.is_connected()) or (db_type == "postgres"):
            connection.close()
            databases.append({
                'type': db_type,
                'host': host,
                'port': port,
                'user': user,
                'password': password,
                'database': database
            })
            return jsonify({"status": "success"})
    except (mysql.connector.Error, psycopg2.Error) as err:
        return jsonify({"status": "error", "message": str(err)}), 400

@management_bp.route('/remove_database', methods=['POST'])
def remove_database():
    index = int(request.form['index'])
    if 0 <= index < len(databases):
        databases.pop(index)
    return jsonify({"status": "success"})

def manage_database(command, db_type, host, port):
    try:
        service_name = 'mysqld' if db_type == "mysql" else 'postgresql'

        if platform.system() == "Windows":
            if command == 'start':
                subprocess.run(['net', 'start', service_name], check=True)
            elif command == 'stop':
                subprocess.run(['net', 'stop', service_name], check=True)
            elif command == 'restart':
                subprocess.run(['net', 'stop', service_name], check=True)
                subprocess.run(['net', 'start', service_name], check=True)
        else:
            if command == 'start':
                subprocess.run(['systemctl', 'start', service_name], check=True)
            elif command == 'stop':
                subprocess.run(['systemctl', 'stop', service_name], check=True)
            elif command == 'restart':
                subprocess.run(['systemctl', 'restart', service_name], check=True)
        return jsonify({"status": "success", "message": f"{db_type.capitalize()} database {command}ed successfully on {host}:{port}"})
    except subprocess.CalledProcessError as e:
        return jsonify({"status": "error", "message": f"Failed to {command} {db_type} database on {host}:{port}: {str(e)}"}), 500

@management_bp.route('/start_database', methods=['POST'])
def start_database():
    db_type = request.form['type']
    host = request.form['host']
    port = request.form['port']
    return manage_database('start', db_type, host, port)

@management_bp.route('/stop_database', methods=['POST'])
def stop_database():
    db_type = request.form['type']
    host = request.form['host']
    port = request.form['port']
    return manage_database('stop', db_type, host, port)

@management_bp.route('/restart_database', methods=['POST'])
def restart_database():
    db_type = request.form['type']
    host = request.form['host']
    port = request.form['port']
    return manage_database('restart', db_type, host, port)