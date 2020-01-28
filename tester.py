import numpy as np
import time,os
from scipy.signal import welch
def wait(N=5):
    start = time.time()
    for i in range(N):
        a = np.random.uniform(size=N)
        b = welch(a)
    return time.time() - start

def dummy_job():
    return None
import json

def dump_proxy(proxy_dict):
    tmp = {}
    for key,value in proxy_dict.items():
        if (str(key) == "args") or (str(key) == "target"): # != operator has problems apparently?
            pass
        else:
            tmp[key] = value

    return json.dumps(tmp)


def measure_handler(some_queue):
    while True:
        if not some_queue.empty():
            measure = some_queue.get()
            #print(dump_proxy(measure))
            #print("handling measure %s"%measure['name'])
        time.sleep(0.2)

def counter(N, **kwargs):
    try:
        test_ = kwargs['web_stats']

        flag = True
    except TypeError:
        print("Cannot find shared variables!")
        flag = False

    kwargs['web_stats']['progress'] = 0
    kwargs['web_stats']['error'] = -1
    #os.chdir("static")
    print(os.getcwd())
    time.sleep(1)
    for i in range(N):
        time.sleep(1)
        kwargs['web_stats']['progress']+=1/float(N)
    time.sleep(1)
    if N>1:
        print("failing")
        kwargs['web_stats']['result'] = 3
        return

    kwargs['web_stats']['result'] = "my/beautiful/file"
