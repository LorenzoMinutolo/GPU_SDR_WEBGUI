import json
import os
import time
import numpy as np
import pyUSRP as u
from flask_socketio import emit
from flask_login import current_user
from app import socketio, check_connection, measure_manager

@socketio.on('vna_param')
def handle_vna_param(msg, methods=['GET', 'POST']):
        f_min = 1e6*float(msg['start_F'])
        f_max = 1e6*float(msg['end_F'])
        f_lo = 1e6*float(msg['central_F'])
        N_points = int(msg['N_points'])
        scan_time = msg['scan_time']
        tx_gain = int(msg['tx_gain'])

        try:
            iterations = int(msg['pass'])
        except ValueError:
            iterations = None
        except TypeError:
            iterations = None

        try:
            rate = int(msg['rate'])
        except ValueError:
            rate = None
        except TypeError:
            rate = None

        try:
            decim = int(msg['decim'])
        except ValueError:
            decim = None
        except TypeError:
            decim = None

        try:
            tone_comp = int(msg['amp'])
        except ValueError:
            tone_comp = 1
        except TypeError:
            tone_comp = None

        if check_connection():
            socketio.emit('vna_response',json.dumps({'connected':int(1)}))
            args = {
                'start_f' : f_min,
                'last_f' : f_max,
                'measure_t' : scan_time,
                'n_points' : N_points,
                'tx_gain' : tx_gain,
                'Rate':rate,
                'decimation':True,
                'RF':f_lo,
                'Front_end':None,
                'Device':None,
                'output_filename':None,
                'Multitone_compensation':tone_comp,
                'Iterations':iterations,
                'verbose':False
            }
            # job_manager.submit_job(u.Single_VNA, arguments = args, name = 'vna', depends = None)
            # sadly does not work because of the context independant nature of Redis. Bonus: theoretically
            # Redis can be programmed to execute function on a remote server and return the result locally
            measure_manager.enqueue_measure(
                target = u.Single_VNA,
                args = args,
                kind = "vna",
                name = "VNA_"+str(time.time()),
                author = str(current_user)[6:-1]
            )
        else:
            socketio.emit('vna_response',json.dumps({'connected':int(0)}))
