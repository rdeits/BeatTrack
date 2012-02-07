from __future__ import division
import time
import multiprocessing
from listener import Listener
import numpy as np


class Predictor:
    def __init__(self, connection):
        self.conn = connection

    def calculate_next_beat(self, result):
        # bpms, phases, timestamps, confidences = [[x[i] for x in self.results_list]\
        #                                          for i in range(4)]
        # now = time.time()
        # adjusted_phases = [0 for x in self.results_list]
        # for i in range(len(self.results_list)):
        #     if bpms[i] == 0:
        #         adjusted_phases[i] = 0
        #     else:
        #         last_beat_time = timestamps[i] - phases[i]
        #         s_per_beat = 60. / bpms[i]
        #         time_since_beat = now - last_beat_time
        #         time_since_predicted_beat = time_since_beat % s_per_beat
        #         adjusted_phases[i] = time_since_predicted_beat
        # print "Adjusted phases:", adjusted_phases
        # # bpm, phase, timestamp, confidence = self.most_likely_result
        # bpm = np.average(bpms, weights = confidences)
        # timestamp = now
        # phase = np.average(adjusted_phases, weights = confidences)
        # s_per_beat = 60. / bpm
        # print "Averaged BPM:", bpm
        # next_beat_times = []
        # confidences = []
        # for x in self.results_list:
        #     bpm, phase, timestamp, confidence = x
        #     if bpm == 0:
        #         continue
        #     now = time.time()
        #     s_per_beat = 60./bpm
        #     next_beat_times.append(now + (s_per_beat - ((now - (timestamp - phase)) % s_per_beat)))
        #     confidences.append(confidence)
        # next_beat_time = np.average(next_beat_times, weights=confidences)
        # return now + (s_per_beat - ((now - (timestamp - phase)) % s_per_beat))
        # return next_beat_time
        bpm, phase, timestamp, confidence = result
        s_per_beat = 60./bpm
        now = time.time()
        return now + (s_per_beat - ((now - (timestamp - phase)) % s_per_beat))

    def run(self):
        self.num_results = 3
        self.results_list = [(0, 0, 0, 0) for i in range(self.num_results)]
        # self.most_likely_result = self.conn.recv()
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

                # confidence_list = [x[3] for x in self.results_list]
                # most_likely_index = np.argmax(confidence_list)
                # self.most_likely_result = self.results_list[most_likely_index]
                # if np.std(x[2] for x in self.results_list) < 1
                # bpm = self.most_likely_result[0]
                bpm = self.result[0]
                bpm_list = [x[0] for x in self.results_list]
                if bpm != 0 and np.std(bpm_list) < 2:
                    # print "confidences:", confidence_list
                    # print "BPMs:", [x[0] for x in self.results_list]
                    # print "Most likely:", self.most_likely_result[0]
                    # print "std:", np.std([x[0] for x in self.results_list])
                    next_beat_time = self.calculate_next_beat(self.result)
                    # print "Next beat:", next_beat_time, "in", next_beat_time - time.time(), "seconds"
                    time.sleep(next_beat_time - time.time())
                    print "Beat:", i, "at", bpm, "BPM"
                    i += 1

if __name__ == "__main__":
    conn1, conn2 = multiprocessing.Pipe()
    listener = Listener(conn1)
    listener.start()
    predictor = Predictor(conn2)
    predictor.run()
            
    
