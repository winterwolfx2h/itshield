from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, emit
from availdb import fetch_database_availability
from utils import fetch_process_list
from db_manager import init_db, add_connection, get_connections, get_connection_by_id
import threading
import time

app = Flask(__name__)
app.secret_key = 'your-secret-key'
socketio = SocketIO(app)

# Initialize SQLite database
init_db()

# Simulated user database (replace with proper authentication)
users = {'admin': 'admin123'}

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    connections = get_connections()
    return render_template('index.html', connections=connections)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username] == password:
            session['username'] = username
            return redirect(url_for('index'))
        return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/dashboard/')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/dashboard/query_history')
def query_history():
    query_history, _, _ = fetch_process_list()
    return {'query_history': query_history}

@app.route('/dashboard/query_stats')
def query_stats():
    _, _, daily_query_stats = fetch_process_list()
    return {'daily_query_stats': daily_query_stats}

@app.route('/manage_connections', methods=['GET', 'POST'])
def manage_connections():
    if 'username' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        name = request.form['name']
        db_type = request.form['db_type']
        host = request.form['host']
        port = int(request.form['port'])
        username = request.form['username']
        password = request.form['password']
        database_name = request.form['database_name']
        add_connection(name, db_type, host, port, username, password, database_name)
        return redirect(url_for('manage_connections'))
    connections = get_connections()
    return render_template('manage_connections.html', connections=connections)

def background_task():
    while True:
        if 'selected_db' in session:
            conn = get_connection_by_id(session['selected_db'])
            if conn:
                query_history, query_logs, daily_query_stats = fetch_process_list(conn)
                socketio.emit('realtime_data', query_history)
        time.sleep(1)

@socketio.on('connect')
def handle_connect():
    print("Client connected")

@socketio.on('select_db')
def handle_select_db(data):
    session['selected_db'] = data['conn_id']
    print(f"Selected database: {data['conn_id']}")

if __name__ == '__main__':
    threading.Thread(target=background_task, daemon=True).start()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)