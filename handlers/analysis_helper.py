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
