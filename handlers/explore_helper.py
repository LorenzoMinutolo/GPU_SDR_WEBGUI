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

class Analysis_Config(object):
    '''
    Class for managing analysis configurations.
    Act as a bridge between pyUSRP checks and websockets.
    '''
    def __init__(self, file_list):
        self.config = {
            'multi':{
                'diagnostic':{
                    'available':0,
                    'requested':0,
                    'reason':'Diagnostic is implemented only as a plotting mode.',
                    'files_noise':[],
                    'files_vna':[],
                    'paths_noise':[],
                    'paths_vna':[],
                    'override':[],
                    'parameters':{}
                }
            },
            'single':{
                'vna_simple':{
                    'available':0,
                    'requested':0,
                    'reason':'no files matching criteria',
                    'files':[],
                    'paths':[],
                    'override':[],
                    'parameters':{}
                },
                'vna_dynamic':{
                    'available':0,
                    'requested':0,
                    'reason':'no files matching criteria',
                    'files':[],
                    'paths':[],
                    'override':[],
                    'parameters':{}
                },
                'fitting':{
                    'available':0,
                    'requested':0,
                    'reason':'no files matching criteria',
                    'files':[],
                    'paths':[],
                    'override':[],
                    'parameters':{}
                },
                'psd':{
                    'available':0,
                    'requested':0,
                    'reason':'no files matching criteria',
                    'files':[],
                    'paths':[],
                    'override':[],
                    'parameters':{}
                },
                'qf':{
                    'available':0,
                    'requested':0,
                    'reason':'Implemented only as a plotting mode',
                    'files':[],
                    'paths':[],
                    'override':[],
                    'parameters':{}
                },
                'qf_psd':{
                    'available':0,
                    'requested':0,
                    'reason':'no files matching criteria',
                    'files':[],
                    'paths':[],
                    'override':[],
                    'parameters':{}
                },
                'calibrated_psd':{
                    'available':0,
                    'requested':0,
                    'reason':'Calibration is in development',
                    'files':[],
                    'paths':[],
                    'override':[],
                    'parameters':{}
                },
                'pair_subtraction':{
                    'available':0,
                    'requested':0,
                    'reason':'Pair subtraction is in development',
                    'files':[],
                    'paths':[],
                    'override':[],
                    'parameters':{}
                },
                'calibration':{
                    'available':0,
                    'requested':0,
                    'reason':'Calibration is in development',
                    'files':[],
                    'paths':[],
                    'override':[],
                    'parameters':{}
                },
                'delay':{
                    'available':0,
                    'requested':0,
                    'reason':'no files matching criteria',
                    'files':[],
                    'paths':[],
                    'override':[],
                    'parameters':{}
                }
            },
            'excluded_files':[],
            'excluded_paths':[],
            'exclusion_reason':[]
        }

        self.file_list = file_list
        self.path_list = []
        self.err_list = [] # errors relative to a file
        self.convert_filenames()
        self.invalid_meas_type = "Invalid measure type defined inside the raw data group: "
        self.invalid_meas_db = "Cannot find the measure in the database"
        # Alolows thread-safe operations on self.config
        # may be usefull when operating in with large amount of files as the checks can be parallelized
        self.lock = Lock()

    def convert_filenames(self):
        '''
        Take a list of finelames and correlate it with absolute paths.
        '''
        for f in self.file_list:
            err, path = filename_to_abs_path(f)
            self.path_list.append(path)
            self.err_list.append(err)

    def check_if_previously_excluded(self, filename):
        '''
        If a file has been previously excluded but now it's included, remove from exclusion list.
        '''
        if filename in self.config['excluded_files']:
            index = self.config['excluded_files'].index(filename)
            self.config['excluded_files'].remove(filename)
            self.config['exclusion_reason'].remove(self.config['exclusion_reason'][index])
            self.config['excluded_paths'].remove(self.config['exclusion_reason'][index])
            return True
        else:
            return False

    def check_if_already_included(self, filename):
        '''
        Check if the file is included in any other analysis config.
        '''
        ret = False
        ret = ret or (filename in self.config['multi']['diagnostic']['files_noise'])
        ret = ret or (filename in self.config['multi']['diagnostic']['files_vna'])
        ret = ret or (filename in self.config['single']['vna_simple']['files'])
        ret = ret or (filename in self.config['single']['vna_dynamic']['files'])
        ret = ret or (filename in self.config['single']['psd']['files'])
        ret = ret or (filename in self.config['single']['qf']['files'])
        ret = ret or (filename in self.config['single']['qf_psd']['files'])
        ret = ret or (filename in self.config['single']['calibrated_psd']['files'])
        ret = ret or (filename in self.config['single']['pair_subtraction']['files'])
        ret = ret or (filename in self.config['single']['calibration']['files'])
        return ret

    def analysis_check_single_file(self, path, err):
        '''
        Check the analysis one can do on a single file
        '''
        f_type = u.get_meas_type(path)[0] #assuming one USRP devices!!!
        filename = os.path.basename(path)
        dir_name = os.path.dirname(os.path.relpath(path, os.path.commonprefix([app.config["GLOBAL_MEASURES_PATH"],path])))

        self.lock.acquire()
        if check_db_measure(os.path.join(dir_name,filename)) and not err:

            try:
                f_type.decode('utf-8')=='VNA'
                VNA_old_version_flag = True
            except AttributeError:
                VNA_old_version_flag = False

            try:
                f_type.decode('utf-8')=='Noise'
                Noise_old_version_flag = True
            except AttributeError:
                Noise_old_version_flag = False

            try:
                f_type.decode('utf-8')=='delay'
                delay_old_version_flag = True
            except AttributeError:
                delay_old_version_flag = False

            # VNA type
            if (f_type=='VNA') or VNA_old_version_flag:

                self.check_if_previously_excluded(filename)
                self.config['single']['vna_simple']['available'] = 1
                self.config['single']['vna_simple']['reason'] = ''
                self.config['single']['vna_simple']['files'].append(filename)
                self.config['single']['vna_simple']['paths'].append(dir_name)
                self.config['single']['vna_simple']['override'].append(int(u.is_VNA_analyzed(path)))

                self.config['single']['fitting']['available'] = 1
                self.config['single']['fitting']['reason'] = ''
                self.config['single']['fitting']['files'].append(filename)
                self.config['single']['fitting']['paths'].append(dir_name)
                self.config['single']['fitting']['override'].append(int(u.has_fit_data(path)))


                if u.get_VNA_iterations(path, usrp_number = 0)>1:
                    # sub-analysis: depend on the VNA group
                    self.config['single']['vna_dynamic']['available'] = 1
                    self.config['single']['vna_dynamic']['reason'] = ''
                    self.config['single']['vna_dynamic']['files'].append(filename)
                    self.config['single']['vna_dynamic']['paths'].append(dir_name)
                    self.config['single']['vna_dynamic']['override'].append(int(u.is_VNA_dynamic_analyzed(path)))

            # Noise type
            elif (f_type=='Noise') or Noise_old_version_flag:

                self.check_if_previously_excluded(filename)
                self.config['single']['psd']['available'] = 1
                self.config['single']['psd']['reason'] = ''
                self.config['single']['psd']['files'].append(filename)
                self.config['single']['psd']['paths'].append(dir_name)
                self.config['single']['psd']['override'].append(int(u.has_noise_group(path)))

                if u.has_fit_data(path):
                    self.check_if_previously_excluded(filename)
                    #self.config['single']['qf']['available'] = 1
                    #self.config['single']['qf']['reason'] = ''
                    #self.config['single']['qf']['files'].append(filename)
                    #self.config['single']['qf']['override'].append(?)


                    self.config['single']['qf_psd']['available'] = 1
                    self.config['single']['qf_psd']['reason'] = ''
                    self.config['single']['qf_psd']['files'].append(filename)
                    self.config['single']['qf_psd']['paths'].append(dir_name)
                    self.config['single']['vna_dynamic']['override'].append(int(u.has_NEF_group(path)))


            elif (f_type=='delay') or delay_old_version_flag:

                self.config['single']['delay']['available'] = 1
                self.config['single']['delay']['reason'] = ''
                self.config['single']['delay']['files'].append(filename)
                self.config['single']['delay']['paths'].append(dir_name)
                self.config['single']['delay']['override'].append(int(u.has_delay_goup(path)))

            # TODO add spectrum files
            # TODO add raw files
            else:
                if not self.check_if_already_included(filename):
                    self.config['excluded_files'].append(filename)
                    self.config['exclusion_reason'].append(self.invalid_meas_type + f_type)
                    self.config['excluded_paths'].append(dir_name)
        else:
            self.config['excluded_files'].append(filename)
            self.config['exclusion_reason'].append(self.invalid_meas_db )
            self.config['excluded_paths'].append('db query null')


        self.lock.release()

    def check_diagnostic_association(self, noise_file, vna_file):
        '''
        check if two files are compatible for diagnotic plots. will be updated when the noise H5 files carry the VNA name.
        '''
        try:
            procede_flag = False
            if (u.get_meas_type(noise_file)[0] == "Noise") and (u.get_meas_type(vna_file)[0] == "VNA"): procede_flag = True
            try:
                if (u.get_meas_type(noise_file)[0].decode('utf-8') == "Noise") and (u.get_meas_type(vna_file)[0].decode('utf-8') == "VNA"):procede_flag = True
            except AttributeError:
                pass

            if procede_flag:
                # Quite stochastic...
                reso_n = list(u.bound_open(noise_file)['Resonators']['reso_0']['fitted_S21'][:20:3])
                reso_v = list(u.bound_open(vna_file)['Resonators']['reso_0']['fitted_S21'][:20:3])
                ret = (reso_n == reso_v)
            else:
                ret = False
        except KeyError:
            ret =  False
        except OSError:
            print_warning("file not found in check_diagnostic_association")
            ret =  False
        except ValueError:
            ret = False

        return ret

    def check_file_list(self):
        '''
        wrapper function for analysis check file.
        '''
        for i in range(len(self.path_list)):
            self.analysis_check_single_file(self.path_list[i], self.err_list[i])
            '''# Dianostic is implemented only as a plotting mode
            self.lock.acquire()
            for j in range(len(self.path_list)):
                if self.check_diagnostic_association(self.path_list[i], self.path_list[j]):
                    self.check_if_previously_excluded(self.path_list[i])
                    self.check_if_previously_excluded(self.path_list[j])
                    self.config['multi']['diagnostic']['available'] = 1
                    self.config['multi']['diagnostic']['reason'] = ''
                    self.config['multi']['diagnostic']['files_noise'].append(self.file_list[i])
                    self.config['multi']['diagnostic']['files_vna'].append(self.file_list[j])
                    self.config['multi']['diagnostic']['noise_paths'].append(dir_name)!!!
            self.lock.release()
            '''

        # at this point the config is done
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(self.config)

    def build_job_queue(self, web_request):
        '''
        Build the measure list of dict.
        '''

    def sort_job_queue(self):
        '''
        Define the order of the measure queue.
        '''

    def enqueue_job(self):
        '''
        Enqueue each analysis job
        '''
