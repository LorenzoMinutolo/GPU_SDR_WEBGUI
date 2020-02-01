import json
import os
import time
import numpy as np
import pyUSRP as u
from flask_socketio import emit
from flask_login import current_user
from app import socketio, check_connection, measure_manager, connection_lock, INFO

@socketio.on('server_connect')
def handle_job_update(msg, methods=['GET', 'POST']):
    if msg['action'] == "connect":
        addr = msg['addr']
        res = u.Connect(timeout = 5, addrss = addr)
        connection_lock.acquire()
        INFO['SERVER_CONNECTED'] = res
        connection_lock.release()
        socketio.emit('connect_resopnse',json.dumps({'response':int(res)}))
    elif msg['action'] == "disconnect":
        u.Disconnect()
        connection_lock.acquire()
        INFO['SERVER_CONNECTED'] = False
        connection_lock.release()
        socketio.emit('connect_resopnse',json.dumps({'response':int(False)}))
    elif msg['action'] == "ping":
        pass # requires server dev
    elif msg['action'] == "restart":
        pass # requires server dev
