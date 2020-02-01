import json
import os
import time
import numpy as np
import pyUSRP as u
from flask_socketio import emit
from flask_login import current_user
from app import socketio, check_connection, measure_manager, job_manager, app
from diagnostic_text import *
from models import add_file_selected, user_files_selected, remove_file_selected, clear_user_file_selected

from .explore_helper import *

@socketio.on('explore_clear_selection')
def clear_all_selected_files(msg):
    '''
    Clear the selectef file list.
    '''
    msg_clear_warning = "Clearing all temporary files of user %s"%current_user
    clear_user_file_selected()
    print_warning(msg_clear_warning)

@socketio.on('remove_from_selection')
def remove_from_selection(msg):
    '''
    Remove file from selected list
    '''
    old_list = user_files_selected()
    if msg['file'] in old_list:
        ret = remove_file_selected(msg['file'])
        old_list = user_files_selected()
        socketio.emit('update_selection',json.dumps({'files':old_list,'err':int(ret)}))
    else:
        print_warning('cannot remove %s from selected list, not found')

@socketio.on('add_to_selection')
def add_to_selection(msg):
    '''
    Add file from selected list
    '''
    ret = add_file_selected(msg['file'])
    old_list = user_files_selected()
    socketio.emit('update_selection',json.dumps({'files':old_list,'err':int(ret)}))

@socketio.on('request_selection')
def send_selection_update(msg):
    socketio.emit('update_selection',json.dumps({'files':user_files_selected(),'err':int(1)}))

@socketio.on('add_to_selection_from_folder')
def select_from_folder(msg):
    '''
    Select all the files in a folder.
    '''
    relative_path = os.path.join(msg['path'], msg['folder'])
    ret = True
    print(app.config["GLOBAL_MEASURES_PATH"],relative_path)
    for root, dirs, files in os.walk(os.path.join(app.config["GLOBAL_MEASURES_PATH"],relative_path), topdown=False):
        for name in files:
            if name.endswith('.h5'):
                ret = ret and add_file_selected(name)
    socketio.emit('update_selection',json.dumps({'files':user_files_selected(),'err':int(ret)}))

@socketio.on('analysis_modal_config')
def define_possible_analysis(msg):
    file_list = user_files_selected()
    config = Analysis_Config(file_list)
    config.check_file_list() # Determine which analysis on which file
    socketio.emit('analyze_config_modal',json.dumps(config.config))
