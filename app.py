from flask_table import Table, Col, LinkCol
from flask import Flask, Markup, request, url_for
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bootstrap import Bootstrap
from flask_login import current_user

import json
import os
import time
import numpy as np
import pyUSRP as u
from multiprocessing import Process, Lock, Manager, Process

shared_var_manager = Manager()
INFO = shared_var_manager.dict()

# bookeeping of the usrpgpu sevrer connection
INFO['SERVER_CONNECTED'] = False
INFO['MEASURE_IN_PROGRESS'] = ""
connection_lock = Lock()
measure_lock = Lock()

def check_connection(block = True):
    '''
    Check the connection with the GPU server in a thread-safe way.
    May block if block arg is True and someone is trying to connect the server
    '''
    connection_lock.acquire(block = block)
    res = INFO['SERVER_CONNECTED']
    connection_lock.release()
    return res


APP_ADDR = "0.0.0.0"
FLASK_APP = "GPU_SDR"

basedir = os.path.abspath(os.path.dirname(__file__))
GLOBAL_MEASURES_PATH = "/home/lorenzo/Desktop/GPU_SDR/scripts/data/"
GLOBAL_PLOTS_PATH = "/home/lorenzo/Desktop/GPU_SDR/scripts/plots/"
# general settings, TOOD will be replaced by file reading
SECRET_KEY = 'A0Zr348j/3yX R~XHH!1mN]LWX/,?RT'
REDIS_WORKERS = 4
class Config(object):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'reference_database.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSIONS_PER_PAGE = 20
    MAX_SEARCH_RESULTS = 20
    SECRET_KEY = SECRET_KEY
    DEBUG = False
    FLASK_APP = "GPU_SDR"
    GLOBAL_MEASURES_PATH = GLOBAL_MEASURES_PATH
    GLOBAL_PLOTS_PATH = GLOBAL_PLOTS_PATH
    REDIS_WORKERS = REDIS_WORKERS
    APP_ADDR = APP_ADDR

app = Flask(__name__)
app.secret_key =SECRET_KEY
app.config.from_object(Config)
app.config['SESSION_TYPE'] = 'filesystem'
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login = LoginManager(app)
login.login_view = 'login'
bootstrap = Bootstrap(app)
socketio = SocketIO(app)

import jobs
# Analysis job stack
job_manager = jobs.Job_Processor()

# Measures job stack
measure_manager = jobs.Contextual_Job_processor()

# Proces that handles the finished measures
def finished_measures_handler(result_queue):
    print("Measure handler thread online!")
    while True:

        if not result_queue.empty():
            measure = result_queue.get()
            if measure['status'] == 'finished':
                if measure['errors'] == 0:
                    notification_text = "Measure %s completed."%measure['name']
                else:
                    notification_text = "Measure %s completed with %d errors."%(measure['name'],measure['error'])
            elif measure['status'] == 'failed':
                notification_text = "Measure %s failed."%measure['name']
            else:
                notification_text = "Measure %s ended with %s status."%(measure['name'],measure['status'])

            print(notification_text)
            socketio.emit('measure_notification', json.dumps(jobs.proxy2dict(measure))) #TODO: private methods are not guaranteed to work across all version

        time.sleep(0.2)

# MUST be after app init
from routes import *

# This has to be imported last
from handlers import *

from models import clear_all_files_selected

if __name__ == '__main__':
    #app.run(debug=True)

    # Clear the session

    job_connected = job_manager.connect()
    if not job_connected:
        print("Cannot connect to the redis analisis server, make sure redis is runnin on your machine!")
    else:
        print("Redis server connected.")
        for i in range(REDIS_WORKERS):
            job_manager.spawn_worker("Default_%d"%i)

    measures_handler = Process(target = finished_measures_handler, args = [measure_manager.result_queue,])
    measures_handler.deamon = True
    measures_handler.start()

    # Check the existance of the paths
    if not os.path.isdir(GLOBAL_MEASURES_PATH):
        print("cannot find measurement path: %s"%GLOBAL_MEASURES_PATH)
        try:
            print("creating path...")
            os.mkdir(GLOBAL_MEASURES_PATH)
        except OsError:
            print("Cannot create path.")
            exit()

    if not os.path.isdir(GLOBAL_PLOTS_PATH):
        print("cannot find measurement path: %s"%GLOBAL_PLOTS_PATH)
        try:
            print("creating path...")
            os.mkdir(GLOBAL_PLOTS_PATH)
        except OsError:
            print("Cannot create path.")
            exit()
    clear_all_files_selected()
    print("Running application on addr: %s"%APP_ADDR)
    socketio.run(app,host= APP_ADDR, port = "5000") #port 33 and sudo for running on local network?
