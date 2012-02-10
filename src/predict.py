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
        self.num_results = 5
        self.results_list = [(0, 0, 0, 0) for i in range(self.num_results)]
        self.result = self.conn.recv()
        self.results_list[-1] = self.result
        self.printed_beat_times = []
        self.last_beat_time = None
        self.output = 1
        print "starting to predict"
        while True:
            i = 0
            while True:
                while self.conn.poll():
                    new_result = self.conn.recv()
                    self.results_list[:-1] = self.results_list[1:]
                    self.results_list[-1] = new_result

                bpm_list = [x[0] for x in self.results_list]
                confidence_list = [x[3] for x in self.results_list]
                bpm = np.average(bpm_list, weights=confidence_list)
                self.result = (bpm,) + self.results_list[-1][1:]
                # if bpm != 0 and np.std(bpm_list) < 2:
                if bpm != 0 and not np.isnan(bpm):
                    if self.last_beat_time is None:
                        self.last_beat_time = time.time()
                    calculated_beat_time = self.calculate_next_beat(self.result)
                    s_per_beat = 60. / bpm
                    predicted_beat_time = self.last_beat_time + s_per_beat
                    calculated_beat_time += round(((predicted_beat_time - calculated_beat_time) % s_per_beat) / s_per_beat) * s_per_beat
                    next_beat_time = np.average((calculated_beat_time, predicted_beat_time), weights = (0.1, 0.9))
                    time.sleep(next_beat_time - time.time())
                    print predicted_beat_time, ",", calculated_beat_time, ",", next_beat_time, bpm
                    # if self.output:
                    #     # print "#########################################"
                    #     # print "Predicted beat at:", predicted_beat_time
                    #     # print "Calculated beat at:", calculated_beat_time
                    #     # print "Next beat at:", next_beat_time
                    #     self.output = 0
                    # else:
                    #     self.output = 1
                    now = time.time()
                    # print 60. / (now - self.last_beat_time)
                    self.last_beat_time = now
                    i += 1
                else:
                    self.last_beat_time = time.time()

if __name__ == "__main__":
    conn1, conn2 = multiprocessing.Pipe()
    listener = Listener(connection=conn1)
    listener.start()
    predictor = Predictor(conn2)
    predictor.run()


