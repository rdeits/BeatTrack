from __future__ import division
import time
import multiprocessing
from listener import Listener
import numpy as np


class Predictor:
    def __init__(self, connection):
        self.conn = connection

    def calculate_next_beat(self, result):
        bpm, phase, timestamp, confidence = result
        s_per_beat = 60./bpm
        now = time.time()
        return now + (s_per_beat - ((now - (timestamp - phase)) % s_per_beat))

    def run(self):
        self.num_results = 3
        self.results_list = [(0, 0, 0, 0) for i in range(self.num_results)]
        self.result = self.conn.recv()
        self.results_list[-1] = self.result
        print "starting to predict"
        while True:
            i = 0
            while True:
                while self.conn.poll():
                    new_result = self.conn.recv()
                    self.results_list[:-1] = self.results_list[1:]
                    self.results_list[-1] = new_result
                    confidence_list = [x[3] for x in self.results_list]
                    avg_confidence = np.average(confidence_list)
                    bpm, phase, timestamp, confidence = new_result
                    print new_result
                    if bpm != 0 and confidence > avg_confidence:
                        lag = abs(self.calculate_next_beat(new_result) 
                                  - self.calculate_next_beat(self.result))
                        if lag > .25 or abs(bpm - self.result[0]) > 1:
                            print "off by", lag
                            self.result = (bpm, phase, confidence, timestamp)
                bpm = self.result[0]
                bpm_list = [x[0] for x in self.results_list]
                if bpm != 0 and np.std(bpm_list) < 2:
                    next_beat_time = self.calculate_next_beat(self.result)
                    time.sleep(next_beat_time - time.time())
                    print "Beat:", i, "at", bpm, "BPM"
                    i += 1

if __name__ == "__main__":
    conn1, conn2 = multiprocessing.Pipe()
    listener = Listener(conn1)
    listener.start()
    predictor = Predictor(conn2)
    predictor.run()
            
    
