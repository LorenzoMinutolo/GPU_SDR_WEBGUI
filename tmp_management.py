'''
Module handle the temporary folder and files and try to keep things in check.
THIS IS A VERY DRASTIC MODULE. CHANGE STUFF AT YOUR OWN RISK.
'''
import os, shutil
from app import app
from diagnostic_text import *
from flask_login import current_user

tmp_path = os.path.join(app.config["GLOBAL_MEASURES_PATH"],".tmp_webgui/")

def check_tmp_folder():
    '''
    check the existence of the temporary folder. if it does not exist, create it
    '''
    global tmp_path
    if not os.path.isdir(tmp_path):
        try:
            os.mkdir(tmp_path)
        except OSError:
            err = "Cannot create or access the temporary directory! (%s) Many functions will result in dangerous errors."%tmp_path
            print_error(err)
            raise OSError(err)

def check_user_tmp_folder():
    '''
    Check temporary folder for a particular user
    '''
    global tmp_path
    if str(current_user) == "None":
        author = "test_env"
    else:
        author = current_user.username
    user_tmp_path = os.path.join(tmp_path,author)
    if not os.path.isdir(user_tmp_path):
        try:
            os.mkdir(user_tmp_path)
        except OSError:
            err = "Cannot create or access the USER temporary directory! (%s) Many functions will result in dangerous errors."%user_tmp_path
            print_error(err)
            raise OSError(err)

def get_tmp_folder():
    '''
    Return the absolute path to the temporary folder.
    '''
    global tmp_path
    check_user_tmp_folder()
    if str(current_user) == "None":
        author = "test_env"
    else:
        author = current_user.username
    user_tmp_path = os.path.join(tmp_path,author)
    return user_tmp_path

def clean_tmp_folder():
    '''
    Clean the current user temporary folder.
    '''
    global tmp_path
    if str(current_user) == "None":
        author = "test_env"
    else:
        author = current_user.username
    user_tmp_path = os.path.join(tmp_path,author)
    check_user_tmp_folder()
    for filename in os.listdir(user_tmp_path):
        file_path = os.path.join(user_tmp_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete temporary file %s. Reason: %s' % (file_path, e))

def clean_full_temporary_folder():
    '''
    self explanatory
    '''
    global tmp_path
    check_tmp_folder()
    for filename in os.listdir(tmp_path):
        file_path = os.path.join(tmp_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete temporary file %s. Reason: %s' % (file_path, e))
