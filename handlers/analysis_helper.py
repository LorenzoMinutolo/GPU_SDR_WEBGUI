import json
import os
import time
import numpy as np
import pyUSRP as u
from flask_socketio import emit
from flask_login import current_user
from app import socketio, check_connection, measure_manager, job_manager, app
from diagnostic_text import *
from models import filename_to_abs_path, check_db_measure
from multiprocessing import Lock
import pprint

def init_dry_run(file, parameters):
    '''
    Dry run for fitting initialization.
    '''

def submit_job_wrapper(job_dict):
    if job_dict['type'] == 'vna_simple':
        args = job_dict['arguments']
        args['filename'] = job_dict['file']
        job_manager.submit_job(u.VNA_analysis, arguments = args, name = job_dict['name'], depends = job_dict['depends'])

    elif job_dict['type'] == 'vna_dynamic':
        args = job_dict['arguments']
        args['filename'] = job_dict['file']
        job_manager.submit_job(u.VNA_timestream_analysis, arguments = args, name = job_dict['name'], depends = job_dict['depends'])

    elif job_dict['type'] == 'fitting':
        pass
    elif job_dict['type'] == 'psd':
        pass
    elif job_dict['type'] == 'psd':
        pass
    elif job_dict['type'] == 'qf':
        pass
    elif job_dict['type'] == 'qf_psd':
        pass
    elif job_dict['type'] == 'calibrated_psd':
        pass
    elif job_dict['type'] == 'pair_subtraction':
        print_error('Analysis %s not implemented' % job_dict['type'])

    elif job_dict['type'] == 'calibration':
        print_error('Analysis %s not implemented' % job_dict['type'])

    elif job_dict['type'] == 'delay':
        pass

    else:
        print_error('Cannot execute job type %s' % job_dict['type'])
