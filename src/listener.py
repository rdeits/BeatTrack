from __future__ import division

import wave
import numpy as np
import threading
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
    def open_stream(self):
        self.block_size_s = 5
        ######################## PyAudio Block #############################
        p = pyaudio.PyAudio()
        self.stream = p.open(input_device_index = 3, 
                             format = FORMAT, 
                             channels = CHANNELS,
                             rate = RATE, 
                             input = True, 
                             frames_per_buffer = self.block_size_s * RATE)
        self.num_channels = CHANNELS
        self.sample_width = p.get_sample_size(FORMAT)
        self.framerate = RATE
        ######################## WAVE Block #############################
        # self.stream = wave.open('crazy.wav', 'r')
        # self.num_channels = self.stream.getnchannels()
        # self.framerate = self.stream.getframerate()
        # self.sample_width = self.stream.getsampwidth()
        ######################## end ####################################
        
        data_buffer_size = int(self.framerate * self.block_size_s)
        self.data_buffer = np.zeros(data_buffer_size)
        cutoff = 160
        nyq = self.framerate/2
        self.decimate_ratio = int(nyq//cutoff)
        self.filtered_framerate = self.framerate / self.decimate_ratio
        self.read_timestamp = time.time()

    def bpm_to_numsamples(self, bpm):
        return int(self.filtered_framerate / (bpm / 60))

    def calc_num_teeth(self, bpm):
        return int(self.block_size_s * bpm / 60.)

    def filter_and_envelope(self, raw_data):
        filtered_data = scipy.signal.decimate(raw_data,
                                              self.decimate_ratio, 
                                              n=3, 
                                              ftype="iir")
        enveloped_data = fast_rolling_envelope(filtered_data, 10)
        return enveloped_data

    def most_likely_bpm(self, enveloped_data, bpm_list):
        max_energy = 0
        max_energy_bpm = 0
        max_energy_phase = 0
        all_energies = []
        for i, bpm in enumerate(bpm_list):
            num_teeth = self.calc_num_teeth(bpm)
            energy, phase = self.trybeat(enveloped_data, bpm)
            all_energies.append(energy)
            if energy > max_energy:
                max_energy = energy
                max_energy_bpm = bpm
                max_energy_phase = phase
        self.bpm_energies = np.array(all_energies)
        confidence = (max_energy - np.average(all_energies)) / np.std(all_energies)
        return (max_energy_bpm, max_energy_phase, confidence)

    def trybeat(self, envelope, bpm):
        """Try a 3-sample comb filter on the envelope-filtered data at a given BPM. 
        Based on Ciuffo's implementation at 
        http://ch00ftech.com/2012/02/02/software-beat-tracking-because-a-tap-tempo-button-is-too-lazy/"""
        num_teeth = self.calc_num_teeth(bpm)
        assert num_teeth > 3, "Block size too small"
        gap = self.bpm_to_numsamples(bpm) #converts BPM to samples per beat
        comb_width = (num_teeth - 1) * gap
        if (len(envelope)<=comb_width): #envelope waveform is too small to fit the comb.
            return (0, 0)
        else:
            comb_positions = gap
            # comb_positions = len(envelope) - comb_width

            comb_vals = np.array([np.sum(envelope[[-(i+j*gap) for j in range(num_teeth)]])
                                  for i in range(comb_positions)])
            comb_vals = np.power(comb_vals, 4)
        energy = np.sum(comb_vals)/(comb_positions * num_teeth**4) # normalize
        phase = np.argmax(comb_vals)/self.filtered_framerate # Phase in seconds
        return (energy, phase)

    def unpack_audio_data(self, data):
        """
        Decode the bytearray into one channel of numerical values
        """
        # if len(data) < block_size_s * framerate * num_channels * sample_width:
        #     print "not enough samples"
        #     break
        data = wave.struct.unpack(self.fmt, data)
        channels = [ [] for x in range(self.num_channels) ]

        for index, value in enumerate(data):
            bucket = index % self.num_channels
            channels[bucket].append(value)
        #TODO: Try combining the two channels instead of stripping out one
        return channels[0]


    def run(self):
        self.open_stream()
        self.bpm_to_test = np.linspace(50, 99)
        while True:
            # data = self.stream.read(int(self.block_size_s * self.framerate))
            # available_samples = self.stream.get_read_available()
            # print "in loop"

            # elapsed_time = time.time() - self.read_timestamp
            # time.sleep(2 - elapsed_time)
            available_samples = int(self.block_size_s * self.framerate)
            # available_samples = max(
            #     int((time.time() - self.read_timestamp) * self.framerate * 1.5),
            #     1024)
            if self.sample_width == 1: 
                # read unsigned chars
                self.fmt = "%iB" % available_samples * self.num_channels
            elif self.sample_width == 2:
                # read signed 2 byte shorts
                self.fmt = "%ih" % available_samples * self.num_channels
            else:
                raise ValueError("Only supports 8 and 16 bit audio formats.")
            data = self.stream.read(available_samples)
            # data = self.stream.readframes(available_samples)
            self.read_timestamp = time.time()
            raw_data = self.unpack_audio_data(data)

            # self.data_buffer[:-len(raw_data)] = self.data_buffer[len(raw_data):]
            # self.data_buffer[-len(raw_data):] = raw_data
            self.data_buffer = raw_data

            enveloped_data = self.filter_and_envelope(self.data_buffer)

            fft_data = np.fft.rfft(enveloped_data - np.average(enveloped_data))
            max_fft_index = np.argmax(fft_data)
            max_fft_freq = max_fft_index * self.filtered_framerate / len(enveloped_data)
            max_fft_bpm = max_fft_freq * 60
            print max_fft_bpm

            bpm, phase, confidence = self.most_likely_bpm(enveloped_data, 
                                                     self.bpm_to_test)
            self.result = (bpm, phase, confidence)
            print "Most likely BPM:", bpm, "phase:", phase, "confidence:", confidence
            if bpm != 0:
                print "Next beat in", (60./bpm - phase), "seconds"

if __name__ == "__main__":
    listener = Listener()
    listener.start()
    listener.join()
            
