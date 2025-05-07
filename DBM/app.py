from flask import Flask, render_template, send_from_directory, redirect, url_for, request, flash
from flask_socketio import SocketIO
from flask_bootstrap import Bootstrap
import psutil
from dashboard import dashboard_bp
from monitor import monitor_bp
from management import management_bp
from utils import fetch_process_list
from availdb import fetch_database_availability
from flask_login import LoginManager, current_user, login_user, login_required, logout_user, UserMixin
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'
Bootstrap(app)

app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
app.register_blueprint(monitor_bp, url_prefix='/monitor')
app.register_blueprint(management_bp, url_prefix='/management')

socketio = SocketIO(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id):
        self.id = id

    def get_id(self):
        return self.id

users = {'admin': {'password': 'admin123'}}

@login_manager.user_loader
def load_user(user_id):
    if user_id in users:
        return User(user_id)
    return None

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username]['password'] == password:
            user = User(username)
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico')

@app.before_request
def before_request():
    if not current_user.is_authenticated and request.endpoint and 'static' not in request.endpoint:
        if request.endpoint.startswith('dashboard') or request.endpoint.startswith('monitor') or request.endpoint.startswith('management'):
            return redirect(url_for('login'))

def background_task():
    while True:
        try:
            mysql_data, mysql_logs, mysql_stats = fetch_process_list(db_type="mysql")
            print(f"Emitting MySQL data: {len(mysql_data)} entries, {len(mysql_logs)} logs")
            socketio.emit('realtime_data_mysql', mysql_data)
            socketio.emit('query_logs_mysql', mysql_logs)
            socketio.emit('daily_query_stats_mysql', mysql_stats)

            postgres_data, postgres_logs, postgres_stats = fetch_process_list(db_type="postgres")
            print(f"Emitting PostgreSQL data: {len(postgres_data)} entries, {len(postgres_logs)} logs")
            socketio.emit('realtime_data_postgres', postgres_data)
            socketio.emit('query_logs_postgres', postgres_logs)
            socketio.emit('daily_query_stats_postgres', postgres_stats)
        except Exception as e:
            print(f"Error during fetch or emit: {e}")
        socketio.sleep(2)

def database_availability_task():
    while True:
        try:
            _, availability_status, _ = fetch_database_availability()
            socketio.emit('db_availability', availability_status)
        except Exception as e:
            print(f"Error during fetch or emit: {e}")
        socketio.sleep(2)

def performance_task():
    while True:
        try:
            performance_stats = {
                'cpu': psutil.cpu_percent(interval=1),
                'memory': psutil.virtual_memory().percent,
                'disk': psutil.disk_usage('/').percent,
                'network': psutil.net_io_counters().bytes_sent + psutil.net_io_counters().bytes_recv
            }
            socketio.emit('realtime_performance', performance_stats)
        except Exception as e:
            print(f"Error during fetch or emit: {e}")
        socketio.sleep(5)

@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")
    mysql_data, mysql_logs, mysql_stats = fetch_process_list(db_type="mysql")
    postgres_data, postgres_logs, postgres_stats = fetch_process_list(db_type="postgres")
    socketio.emit('initial_data', {'dbType': 'mysql', 'data': mysql_data, 'logs': mysql_logs, 'stats': mysql_stats})
    socketio.emit('initial_data', {'dbType': 'postgres', 'data': postgres_data, 'logs': postgres_logs, 'stats': postgres_stats})
    print(f"Sent initial data for mysql: {len(mysql_data)} entries, postgres: {len(postgres_data)} entries")

@socketio.on('request_data')
def handle_request_data(db_type):
    try:
        print(f"Received request_data for {db_type}")
        data, logs, stats = fetch_process_list(db_type=db_type)
        socketio.emit('initial_data', {'dbType': db_type, 'data': data, 'logs': logs, 'stats': stats})
        print(f"Sent initial_data for {db_type}: {len(data)} entries")
    except Exception as e:
        print(f"Error handling request_data for {db_type}: {e}")

socketio.start_background_task(target=background_task)
socketio.start_background_task(target=database_availability_task)
socketio.start_background_task(target=performance_task)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)