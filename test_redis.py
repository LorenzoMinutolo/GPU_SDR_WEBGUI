import time,os
from tester import counter, measure_handler
from jobs import Contextual_Job_processor
from multiprocessing import Process

manager = Contextual_Job_processor()
handler = Process(target = measure_handler, args = [manager.result_queue])
handler.daemon = True
handler.start()
for i in range(4):
    manager.enqueue_measure(counter, {'N':i}, 'test', 'tester_%d'%i, 'some author')
while True:
    print(os.getcwd())
    job_list = manager.get_measure_queue()
    for x in job_list:
        pass
        #print("%s\tstatus: %s\tprogress: %.2f\tResult: %s"%(x['name'],x['status'],x['progress'],str(x['result'])))
    #print("\n")
    time.sleep(0.5)
