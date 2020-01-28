from redis import Redis
import redis
import rq
import re
from rq import Queue, Worker, Connection, cancel_job
from rq.job import Job
from multiprocessing import Process, Lock, Manager
import multiprocessing as mp
from multiprocessing.managers import SyncManager
import signal as Signal
import time
import os,sys,signal
from contextlib import contextmanager
from threading import Thread
from datetime import datetime
from queue import Empty
@contextmanager
def silence_stdout():
    new_target = open(os.devnull, "w")
    old_target = sys.stdout
    sys.stdout = new_target
    try:
        yield new_target
    finally:
        sys.stdout = old_target

def find_between( s, first, last ):
    '''
    Utility function to deal with naming
    '''
    try:
        start = s.index( first ) + len( first )
        end = s.index( last, start )
        return s[start:end]
    except ValueError:
        return "No jobs"

def mgr_init():
    '''
    Initialization for the thread synchronization manager. This is basically propagaring the Ctrl+C command to kill the
    threads (processes). This is ment to be used in:
    >>> manager.start(mgr_init)

    :return: None
    '''
    Signal.signal(Signal.SIGINT, Signal.SIG_IGN)

def proxy2dict(proxy_dict):
    '''
    Utility function to dump the items of the measure_queue of to normal dictionaries.
    '''
    tmp = {}
    for key,value in proxy_dict.items():
        if (str(key) == "args") or (str(key) == "target"): # != operator has problems apparently?
            pass
        else:
            tmp[key] = value

    return tmp

class Job_Processor(object):
    '''
    Manage workers and redis processes.
    '''

    def __init__(self):

        self.redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')
        # Initialize process manager interface
        self.manager = Manager()
        self.connected = False
        # explicitly starting the manager, and telling it to ignore the interrupt signal and propagate it.
        #self.manager.start(mgr_init)
        self.INFO = self.manager.dict()
        self.lock = Lock()
        self.job_table = []
        self.worker_table = []
        self.job_queue = self.manager.Queue() #mp.Queue()
        self.job_manager = Process(target=self.job_updater, name="job_manager", args = [self.job_queue,self.lock])
        self.job_manager.daemon = True

    def connect(self):

        listen = ['default']
        self.conn = redis.from_url(self.redis_url)
        self.q = Queue(connection=self.conn)
        self.job_manager.start()
        self.connected = self.test_connection(self.q, self.conn)
        return self.connected

    def test_connection(self, redis_queue_, connection_):
        res = True
        dummy_job_ = Job.create(time.sleep, [0.1], id = "this-is-a-test", connection = connection_)
        try:
            try:
                redis_queue_.enqueue_job(dummy_job_)
            except ConnectionRefusedError:
                res = False
        except redis.exceptions.ConnectionError:
            res = False
        self.connected = res
        return res

    def spawn_worker(self, name = None):
        try:
            if name is None:
                name = "Worker_%d"%len(self.worker_table)
            print("Spawning redis worker %s..."%name)
            listen = ['high', 'default', 'low']
            with Connection(self.conn):
                with silence_stdout():
                    worker = Worker(map(Queue, listen))
                    just_a_process = Process(target=self.worker_wrapper, name=name,args=(worker,), kwargs={})
                    just_a_process.daemon = True
                    self.worker_table.append({
                        'thread':just_a_process,
                        'worker':worker
                    })
                    just_a_process.start()
            print("Worker %s Initialized."%name)
            return True
        except:
            return False

    def worker_wrapper(self, worker):
        with silence_stdout():
            with Connection(self.conn):
                worker.work()

    def delete_worker(self, name):
        print("Deleting worker %s ..."%name)
        name_list = [worker['thread'].name for worker in self.worker_table]
        try:
            current_item = self.worker_table[name_list.index(name)]
        except ValueError:
            print("Cannot find worker %s, cannot terminate"%name)
            return False
        worker = Worker.find_by_key(worker_key = 'rq:worker:'+current_item['worker'].name, connection = self.conn)
        thread = current_item['thread']
        worker_status = worker.state
        if worker_status != 'busy':
            thread.terminate()
            thread.join()
            self.worker_table.remove(current_item)
            print("Worker %s deleted"%name)
            return True
        else:
            print("cannot delete worker %s, it's %s"%(thread.name, worker.state))
            return False

    def workers_status(self):
        name_list = [worker['thread'].name for worker in self.worker_table]

        workers = [Worker.find_by_key(worker_key = 'rq:worker:'+worker['worker'].name, connection = self.conn) for worker in self.worker_table ]
        #status_list = [worker['worker'].state for worker in self.worker_table]
        status_list = [worker.state for worker in workers]

        job_list = []
        for worker in workers:
            try:
                sub_job_name = str(worker.get_current_job())
                sub_job_name = find_between( sub_job_name, '<Job ', ': ' )
                job_list.append(sub_job_name)
            except AttributeError:
                job_list.append("no jobs")

        return {'name':name_list, 'status':status_list, 'job':job_list}

    def job_updater(self, job_queue, lock):
        '''
        Process for updateing jobs status.
        '''
        while True:
            tmp_list = []
            lock.acquire()

            while not job_queue.empty():
                current_job = job_queue.get()
                try:
                    job = Job.fetch(id = current_job['name'], connection=self.conn)
                    if current_job['status'] != 'canceled':
                        current_job = {
                            'name':current_job['name'],
                            'status': job.get_status(),
                            'started':str(job.started_at)[:-7],
                            'enqueued':str(job.enqueued_at)[:-7],
                            'result':job.result
                        }
                except rq.exceptions.NoSuchJobError:
                    current_job['status'] = '?'

                tmp_list.append(current_job)
            for x in tmp_list:
                job_queue.put(x)
            lock.release()
            time.sleep(0.3)

    def get_jobs(self):
        '''
        Return a list of dictionaries. An element represent a job and has name, status, started, enqueued and result attribute.
        '''
        self.lock.acquire()
        tmp_list = []
        while not self.job_queue.empty():
            current_job = self.job_queue.get()
            tmp_list.append(current_job)
        # a double check necessary to avoid some bug of mp module
        if len(tmp_list) == 0:
            while not self.job_queue.empty():
                current_job = self.job_queue.get()
                tmp_list.append(current_job)
        for x in tmp_list:
            self.job_queue.put(x)

        self.lock.release()
        return sorted(tmp_list, key = lambda i: i['enqueued'], reverse=True)
        #return tmp_list

    def pprint_jobs(self, jobs = None):
        if jobs is None:
            jobs = self.get_jobs()
        print("-----------PRINTING JOBS STATUS----------------")
        for current_job in jobs:
            print("Job: %s"%current_job['name'])
            print("\tStatus: %s"%current_job['status'])
            print("\tEnqueued: %s"%current_job['enqueued'])
            print("\tStarted: %s"%current_job['started'])
            print("\tResult: %s"%current_job['result'])
            print("\n")

    def wait_for_all_(self):
        not_done = True
        while not_done:
            jobs = self.get_jobs()
            #print(len(jobs))
            counter = 0
            for job in jobs:
                not_done = False
                if (job['status'] != 'finished'):
                    not_done = True
                else:
                    counter+=1
            self.pprint_jobs(jobs)
            print("jobs done : %d / %d"%(counter,len(jobs)))
            time.sleep(0.5)


    def submit_job(self, function, arguments, name, depends = None):
        #job = Job.create(function, kwargs = arguments, id = name, connection = self.conn, timeout = -1)

        if depends is not None:
            try:
                depends = Job.fetch(id = str(depends), connection=self.conn)
            except rq.exceptions.NoSuchJobError:
                print("Submitting %s job : Dependant job %s not found in job database, have you submitted?"%(name,depends))
                return

        job = self.q.enqueue_call(function, args=None, kwargs=arguments, timeout=-1,
                 result_ttl=None, ttl=None, failure_ttl=None,
                 description=None, depends_on=depends, job_id=name,
                 at_front=False, meta=None)

        self.lock.acquire()
        self.job_queue.put(
            {
                'name':name,
                'status':job.get_status(),
                'enqueued':str(job.enqueued_at)[:-7],
                'started':str(job.started_at)[:-7],
                'result':job.result
            }
        )
        self.lock.release()
        print("Job %s added"%name)

    def chk_job(self, job_name):
        jobs = self.get_jobs()
        name_list = [x['name'] for x in jobs]
        try:
            return jobs[name_list.index(str(job_name))]['status']
        except ValueError:
            print("There is no job named %s"% job_name)
            return None

    def get_job_res(self, job_name):
        jobs = self.get_jobs()
        name_list = [x['name'] for x in jobs]
        try:
            if jobs[name_list.index(str(job_name))]['status']!='finished':
                print("Getting resulst from a bad job!")
            return jobs[name_list.index(str(job_name))]['result']
        except ValueError:
            print("There is no job named %s"% job_name)
            return None

    def get_many_job_res(self, job_names):
        '''
        get a list of results from a list of names.
        Including canceled and failed jobs.
        '''
        jobs = self.get_jobs()
        name_list = [x['name'] for x in jobs]
        res = []
        for name in job_names:
            try:
                r = jobs[name_list.index(str(name))]['result']
            except ValueError:
                print("There is no job named %s"% name)
                r = None
            res.append(r)
        return res

    def change_status(self, name, status):
        '''
        Dangerous function. Only used for canceled jobs as rq does not have the canceled status.
        '''
        flag = False
        tmp_list = []
        self.lock.acquire()
        while not self.job_queue.empty():
            current_job = self.job_queue.get()
            tmp_list.append(current_job)
        for x in tmp_list:
            if x['name'] == name:
                flag = True
                x['status'] = status
            self.job_queue.put(x)
        self.lock.release()
        if flag:
            return True
        else:
            print("Cannot change the status of %s job"% flag)
            return False

    def cancel_job(self, name):
        print("Cancelling job %s ..."%name)
        jobs = self.get_jobs()
        name_list = [x['name'] for x in jobs]
        try:
            status = jobs[name_list.index(str(name))]['status']
        except ValueError:
            print("There is no job named %s"% name)
            return False
        job = Job.fetch(id = name, connection=self.conn)
        status = job.get_status()
        if status == "finished" or status == "failed":
            print("Cannot cancel a finished/failde job")
            return False
        else:
            cancel_job(name, connection = self.conn)
            self.change_status(name, 'canceled')
            print("Job %s canceled..."%name)
            return True

class Contextual_Job_processor(object):
    '''
    An other job processor, similar to the other one but not based on the rq module
    and that works only locally, importing the multiprocess manager context of the executing function's module.
    '''

    def __init__(self):
        self.manager = Manager()
        self.INFO = self.manager.dict()
        self.INFO['TYPE_IN_PROGRESS'] = ""

        self.stats = self.manager.dict() #shared object to monitor the GPU sdr client performance
        self.stats['result'] = None
        self.stats['error'] = 0
        self.stats['progress'] = 0

        self._thread_control = self.manager.dict()
        self._thread_control['running'] = True

        # Measure complete event handling. This is very home-brew but works.
        # It's expected to be SCSP so no lock is required.
        self.result_queue = self.manager.Queue()

        self._current_lock = Lock()
        self._queue_lock = Lock()

        # This is an internal queue. do not use it outside
        self._measure_queue = self.manager.Queue()
        #self._handler = Process(target = self.execution_handler_thread, args = [self._thread_control,])
        self._handler = Thread(target = self.execution_handler_thread, args = [self._thread_control,], daemon =True)
        #self._handler.daemon=True
        self._handler.start()

    def set_measure(self, measure_type):
        '''
        Set the managed variable INFO['MEASURE_IN_PROGRESS'] in a thread-safe way
        '''
        self._current_lock.acquire()
        self.INFO['TYPE_IN_PROGRESS'] = str(measure_type)
        self._current_lock.release()

    def unset_measure(self):
        self._current_lock.acquire()
        self.INFO['TYPE_IN_PROGRESS'] = ""
        self._current_lock.release()

    def chk_measure_in_progress(self):
        self._current_lock.acquire()
        res = self.INFO['TYPE_IN_PROGRESS']
        self._current_lock.release()

        if len(res) == 0:
            ret = False
        else:
            ret = res

        return ret

    def enqueue_measure(self, target, args, kind, name, author):
        '''
        Enqueue a measure.
        '''
        # Add special arguments used to monitor status and result of the measure
        args['web_stats'] = self.stats

        measure = {
            'name':name,
            'enqueued':(datetime.now()).strftime("%m/%d/%Y, %H:%M:%S"),
            'start': None,
            'end':None,
            'errors':0,
            'kind':str(kind),
            'author':str(author),
            'progress':0,
            'status':'queued',
            'args':args,
            'target':target,
            'result':None
        }
        self._queue_lock.acquire()
        self._measure_queue.put(measure)
        self._queue_lock.release()

    def queue_to_list_(self):
        '''
        NEVER USE THIS FUNCTION IF NOT UNDER QUEUE LOCK. FOR INTERNAL USE ONLY.
        Remember to follow this example:
        >>> lock()
        >>> requeue_jobs = self.queue_to_list_()
        >>> for each_job in requeue_jobs:
        >>>     self._measure_queue.put(each_job)
        >>> unlock()
        '''
        tmp_list = []
        while not self._measure_queue.empty():
            tmp_list.append(
                self._measure_queue.get()
            )

        #add a retry
        if len(tmp_list) == 0:
            while not self._measure_queue.empty():
                tmp_list.append(
                    self._measure_queue.get()
                )
        return sorted(tmp_list, key = lambda i: i['enqueued'], reverse=True)


    def remove_enqueued_measure(self, name):
        '''
        Remove an enqueued measure.
        Return bolean representing the success of the operation.
        '''

        self._queue_lock.acquire()

        tmp_list = self.queue_to_list_()

        selected = next((item for item in tmp_list if item["name"] == name), None)
        if selected is not None:
            if selected['status'] != "in progress":
                print("Deleting measure %s from job queue"%str(name))
                for i in range(len(tmp_list)):
                    if tmp_list[i]['name'] == str(name):
                        del tmp_list[i]
            else:
                print("Cannot delete measure %s, is in progress!"%str(name))
                ret = False
        else:
            print("Cannot delete measure %s, not found."%str(name))
            ret = False

        for meas in tmp_list:
            self._measure_queue.put(meas)

        self._queue_lock.release()
        return ret

    def stop_current_measure(self, name):
        '''
        Kill the current measure.
        '''

    def clear_measure_queue(self):
        '''
        Clear the measure queue except the one in progress.
        Return the number of removed items.
        '''
        counter = 0
        self._queue_lock.acquire()
        while not self._measure_queue.empty():
            self._measure_queue.get()
            counter += 1

        #add a retry
        if counter == 0 or not self._measure_queue.empty():
            while not self._measure_queue.empty():
                self._measure_queue.get()
                counter += 1

        self._queue_lock.release()

        return counter

    def clean_measure_queue(self):
        '''
        Remove all failed, finished and canceled measure from the queue.
        '''
        self._queue_lock.acquire()

        tmp_list = self.queue_to_list_()
        for i in range(len(tmp_list)):
            if (tmp_list[i]['status'] != 'failed') and (tmp_list[i]['status'] != 'canceled') and (tmp_list[i]['status'] != 'finished'):
                self._measure_queue.put(tmp_list[i])

        self._queue_lock.release()

    def get_measure_queue(self):
        '''
        Ususal list of dicts representing measure queue for jinja2 representation.
        '''
        self._queue_lock.acquire()

        tmp_list = self.queue_to_list_()

        for meas in tmp_list:
            self._measure_queue.put(meas)

        self._queue_lock.release()

        static_list = []
        for meas in tmp_list:
            static_list.append(
                proxy2dict(meas)
            )
        return static_list

    def handle_measure_result(self, name):
        '''
        Store the measure restult in the database.
        '''

    def execution_handler_thread(self, thread_control):
        '''
        Thread for executing the measure in the queue
        '''
        #while thread_control['running']:
        while thread_control['running']:
            # Main loop: search for a queued job and start it
            self._queue_lock.acquire()
            requeue_jobs = self.queue_to_list_()
            current_job_index = None
            for i in range(len(requeue_jobs)):
                if requeue_jobs[i]['status'] == "queued":
                    current_job_index = i
                    current_job_name = requeue_jobs[i]['name'] # index may variate
                    break
            if current_job_index is not None:
                requeue_jobs[current_job_index]['status']= 'in progress'
                requeue_jobs[current_job_index]['started'] = (datetime.now()).strftime("%m/%d/%Y, %H:%M:%S")
                #current_process = Process(target = requeue_jobs[current_job_index]['target'] , kwargs = requeue_jobs[current_job_index]['args'])
                #current_process.daemon=True
                current_process = Thread(target = requeue_jobs[current_job_index]['target'] , kwargs = requeue_jobs[current_job_index]['args'], daemon = True)
                current_process.start()
                self.set_measure(requeue_jobs[current_job_index]['kind'])
            for each_job in requeue_jobs:
                self._measure_queue.put(each_job)
            self._queue_lock.release()

            # Internal loop: monitor the job progress and join when done
            if current_job_index is not None:
                current_job_done = False
                while not current_job_done:
                    self._queue_lock.acquire()
                    requeue_jobs = self.queue_to_list_()
                    current_job_index = next((index for (index, d) in enumerate(requeue_jobs) if d["name"] == current_job_name), None)
                    if current_job_index is None:
                        #print("Measure job handler cannot find %s measure process."%current_job_name)
                        #current_job_done = True
                        self._queue_lock.release()
                        print("Waiting for measure %s to appear..."%current_job_name)
                        continue
                    requeue_jobs[current_job_index]['progress'] = round(self.stats['progress'],2)
                    requeue_jobs[current_job_index]['errors'] = self.stats['error']

                    if not current_process.is_alive():
                        current_process.join()
                        requeue_jobs[current_job_index]['end'] = (datetime.now()).strftime("%m/%d/%Y, %H:%M:%S")
                        requeue_jobs[current_job_index]['status'] = "finished"
                        requeue_jobs[current_job_index]['result'] = self.stats['result']
                        current_job_done = True

                        # The result is expected to be a string
                        try:
                            chk_res = len(self.stats['result'])
                        except TypeError:
                            chk_res = 0
                        if chk_res == 0:
                            requeue_jobs[current_job_index]['status'] = "failed"

                        print("Measure complete, pushing the result")
                        self.result_queue.put(requeue_jobs[current_job_index])
                        self.stats['result'] = None
                        self.stats['error'] = 0
                        self.stats['progress'] = 0

                    for each_job in requeue_jobs:
                        self._measure_queue.put(each_job)
                    self._queue_lock.release()
                    time.sleep(0.2)
            else:
                self.unset_measure()
                #handle the result

            time.sleep(0.3) # timeout between jobs
