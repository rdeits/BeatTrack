from __future__ import division

import wave
import numpy as np
import time
import pyaudio
import matplotlib.pyplot as plt
import multiprocessing
import scipy.signal
import bisect
# from pylab import *

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

# from listen import most_likely_bpm, filter_and_envelope, trybeat, calc_num_teeth

def fast_rolling_envelope(data, width):
    """Do a rolling envelope filter on array [data], returning an array of the same
    length."""
    envelope_points = list(data[:int(width//2 - 1)])
    envelope_points.sort()
    points_to_average = int(width//10)
    output = np.zeros(len(data))
    for i, x in enumerate(data):
        index_to_insert = i+int(width//2 - 1)
        if index_to_insert < len(data):
            bisect.insort(envelope_points, data[index_to_insert])
        if len(envelope_points) > width:
            index_to_pop = i-int(width//2 + 1)
            envelope_points.pop(bisect.bisect_left(envelope_points,
                                                   data[index_to_pop]))
        output[i] = np.average(envelope_points[-points_to_average:])
    return output

class Listener(multiprocessing.Process):
    def __init__(self, live = True, connection=None, debug_connection=None):
        super(Listener, self).__init__()
        self.result = (0, 0, 0, 0)
        self.conn = connection
        self.debug_conn = debug_connection
        self.live = live


    def open_stream(self):
        self.block_size_s = 2.5
        if self.live:
            ######################## PyAudio Block #############################
            p = pyaudio.PyAudio()
            self.stream = p.open(input_device_index = 3,
                                 format = FORMAT,
                                 channels = CHANNELS,
                                 rate = RATE,
                                 input = True,
                                 frames_per_buffer = int(self.block_size_s * RATE))
            self.num_channels = CHANNELS
            self.sample_width = p.get_sample_size(FORMAT)
            self.framerate = RATE
            self.read_function = self.stream.read
        else:
            ######################## WAVE Block #############################
            self.stream = wave.open('120-b.wav', 'r')
            self.num_channels = self.stream.getnchannels()
            self.framerate = self.stream.getframerate()
            self.sample_width = self.stream.getsampwidth()
            self.read_function = self.stream.readframes

        self.data_buffer_factor = 2
        self.data_buffer = np.zeros(self.data_buffer_factor
                                    * self.framerate
                                    * self.block_size_s)
        cutoff = 160
        nyq = self.framerate/2
        self.decimate_ratio = int(nyq//cutoff)
        # self.filtered_framerate = self.framerate / self.decimate_ratio
        self.read_timestamp = time.time()

    def bpm_to_numsamples(self, bpm):
        return int(self.filtered_framerate / (bpm / 60))

    def calc_num_teeth(self, bpm):
        return int(self.block_size_s * self.data_buffer_factor * bpm / 60.)

    def filter_and_envelope(self, raw_data):
        """
        Run all of our filters on the data, returning the result.
        """
        # Downsample and low-pass filter
        filtered_data = scipy.signal.decimate(raw_data,
                                              self.decimate_ratio,
                                              n=3,
                                              ftype="iir")
        self.filtered_framerate = len(filtered_data) / len(raw_data) * self.framerate
        # plt.figure(3)
        # plt.plot(filtered_data)
        # plt.show()
        # Envelope filter
        enveloped_data = fast_rolling_envelope(filtered_data, 10)
        # Derivative filter
        # enveloped_data = np.diff(enveloped_data)
        # # Half-wave rectify
        # enveloped_data = np.max(np.vstack((enveloped_data,
        #                                    np.zeros_like(enveloped_data))), 0)
        # # Envelope filter
        # enveloped_data = fast_rolling_envelope(enveloped_data, 5)
        return enveloped_data

    def most_likely_bpm(self, enveloped_data, bpm_list):
        max_energy = 0
        max_energy_bpm = 0
        max_energy_phase = 0
        all_energies = []
        for bpm in bpm_list:
            energy, phase = self.trybeat(enveloped_data, bpm)
            all_energies.append(energy)
            if energy > max_energy:
                max_energy = energy
                max_energy_bpm = bpm
                max_energy_phase = phase
        self.bpm_energies = np.array(all_energies)
        confidence = ((max(self.bpm_energies) - np.average(self.bpm_energies))
                      / np.std(self.bpm_energies))
        # if not self.live:
        #     plt.figure(1)
        #     plt.plot(bpm_list, self.bpm_energies)
        #     plt.figure(2)
        #     plt.plot(enveloped_data)
        #     plt.show()
        # bpm_range = bpm_list[-1] - bpm_list[0]
        # if bpm_range > 10:
        #     max_energy_bpm = self.most_likely_bpm(enveloped_data,
        #                                 np.linspace(max(max_energy_bpm - 2, 0),
        #                                             max_energy_bpm + 2,
        #                                             17))[0]
        return (max_energy_bpm, max_energy, max_energy_phase, confidence)

    def trybeat(self, envelope, bpm):
        """
        Try an n-sample comb filter on the envelope-filtered data at a given BPM.
        Based on Ciuffo's implementation at
        http://ch00ftech.com/2012/02/02/software-beat-tracking-because-a-tap-tempo-button-is-too-lazy/
        """
        gap = self.bpm_to_numsamples(bpm) #converts BPM to samples per beat
        num_teeth = self.calc_num_teeth(bpm)
        assert num_teeth > 3, "Block size too small: %3d" % num_teeth
        comb_width = (num_teeth - 1) * gap
        if (len(envelope)<=comb_width): #envelope waveform is too small to fit comb
            return (0, 0)
        else:
            comb_positions = gap
            comb_vals = np.array([np.sum(envelope[[-(i+j*gap)
                                                   for j in range(num_teeth)]])
                                  for i in range(comb_positions)])
            comb_vals = np.power(comb_vals, 4)
        energy = np.sum(comb_vals)/(comb_positions * num_teeth**4) # normalize
        phase = np.argmax(comb_vals)/self.filtered_framerate # Phase in seconds
        return (energy, phase)

    def unpack_audio_data(self, data):
        """
        Decode the bytearray into one channel of numerical values
        """
        data = wave.struct.unpack(self.fmt, data)
        channels = [ [] for x in range(self.num_channels) ]

        for index, value in enumerate(data):
            bucket = index % self.num_channels
            channels[bucket].append(value)
        #TODO: Try combining the two channels instead of stripping out one
        return channels[0]

    def read_audio_block(self):
        elapsed_time = time.time() - self.read_timestamp
        if self.live:
            time.sleep(self.block_size_s - elapsed_time - 0.5)
        available_samples = int(self.block_size_s * self.framerate)
        if self.sample_width == 1:
            # read unsigned chars
            self.fmt = "%iB" % available_samples * self.num_channels
        elif self.sample_width == 2:
            # read signed 2 byte shorts
            self.fmt = "%ih" % available_samples * self.num_channels
        else:
            raise ValueError("Only supports 8 and 16 bit audio formats.")

        data = self.read_function(available_samples)
        self.read_timestamp = time.time()
        return data

    def run(self):
        self.open_stream()
        # self.bpm_to_test = range(90, 180)
        self.bpm_to_test = np.linspace(90, 180, 91)
        while True:
            data = self.read_audio_block()
            new_data = self.unpack_audio_data(data)
            self.data_buffer[:-len(new_data)] = self.data_buffer[len(new_data):]
            self.data_buffer[-len(new_data):] = new_data
            # self.data_buffer = self.unpack_audio_data(data)
            enveloped_data = self.filter_and_envelope(self.data_buffer)

            bpm, energy, phase, confidence = self.most_likely_bpm(enveloped_data,
                                                     self.bpm_to_test)
            self.result = (bpm, phase, self.read_timestamp, confidence)
            if self.conn is not None:
                self.conn.send(self.result)
            else:
                print "Most likely BPM:", bpm, "phase:", phase, "confidence:", confidence, "read_timestamp:", self.read_timestamp
            if self.debug_conn is not None:
                self.debug_conn.send((self.bpm_to_test, self.bpm_energies))

if __name__ == "__main__":
    listener = Listener(live = True)
    listener.start()
    listener.join()

