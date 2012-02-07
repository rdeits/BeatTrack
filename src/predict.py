from __future__ import division
import time
import multiprocessing
from listener import Listener

def calculate_next_beat(bpm, phase, timestamp):
    s_per_beat = 60. / bpm
    # print "s_per_beat:", s_per_beat
    now = time.time()
    # print "now:", now
    # print "starting from:", timestamp
    # print "last known beat:", timestamp - phase
    # print "time since last beat:", now - (timestamp - phase)
    # print "time until next beat:", s_per_beat - ((now - (timestamp - phase)) % s_per_beat)
    return now + (s_per_beat - ((now - (timestamp - phase)) % s_per_beat))

class Predictor:
    def __init__(self, connection):
        self.conn = connection

    def run(self):
        bpm, phase, confidence, timestamp = self.conn.recv()
        print "starting to predict"
        while True:
            i = 0
            while True:
                while self.conn.poll():
                    bpm, phase, confidence, timestamp = self.conn.recv()
                if bpm != 0:
                    next_beat_time = calculate_next_beat(bpm, phase, timestamp)
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
            
    
