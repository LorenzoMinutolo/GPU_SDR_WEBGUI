import json
import os
import time
import numpy as np
import pyUSRP as u
from flask_socketio import emit
from flask_login import current_user
from app import socketio, check_connection, measure_manager, job_manager

@socketio.on('worker_action')
def handle_worker_action(msg, methods=['GET', 'POST']):
    print('received worker action: ' + str(msg))
    try:
        worker_to_remove = msg['remove_']
        print("removing worker %s ..."%worker_to_remove)
        resp = json.dumps({'response':job_manager.delete_worker(worker_to_remove)})
        socketio.emit('deletion_respone', resp)
    except KeyError:
        pass
    try:
        worker_to_add = int(msg['add_'])
        print("adding %d workers ..."%worker_to_add)
        spawn_success = [job_manager.spawn_worker() for i in range(worker_to_add)]
        resp = json.dumps({'response':(sum(spawn_success) == len(spawn_success))})
        socketio.emit('creation_respone', resp)
    except KeyError:
        pass

@socketio.on('jobs_update')
def handle_job_update(msg, methods=['GET', 'POST']):
    #print('received job update_request: ' + str(msg))
    if msg['update']:
        #print("Fetching jobs...")
        socketio.emit('update_job_resopnse',json.dumps(job_manager.get_jobs()))
    else:
        print("Not requesting an update?")

@socketio.on('measure_update')
def handle_meas_update(msg, methods=['GET', 'POST']):
    #print('received job update_request: ' + str(msg))
    if msg['update']:
        response_ = json.dumps(measure_manager.get_measure_queue())
        socketio.emit('update_measure_resopnse',response_)
    else:
        print("Not requesting an update?")
