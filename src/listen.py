from __future__ import division

import pyaudio
import wave
import numpy as np
import scipy.signal
import matplotlib.pyplot as plt

CHUNK = 512
FORMAT = pyaudio.paInt8
CHANNELS = 1
RATE = 44100

# p = pyaudio.PyAudio()
# stream = p.open(input_device_index=3,
#                 format=FORMAT,
#                 channels=CHANNELS,
#                 rate=RATE,
#                 input=True,
#                 frames_per_buffer=chunk)

block_size_s = 5
stream = wave.open('crazy.wav', 'r')
framerate = stream.getframerate()
sample_width = stream.getsampwidth()
num_channels = stream.getnchannels()
cutoff = 160
nyq = framerate/2
q = int(nyq//cutoff)
filtered_framerate = framerate / q
total_samples = int(framerate * block_size_s) * num_channels

def rolling_envelope(data, position, width):
    """Do a rolling envelope filter on array [data]. Based on Ciuffo's implementation at http://ch00ftech.com/2012/02/02/software-beat-tracking-because-a-tap-tempo-button-is-too-lazy/"""
    if position < len(data):
        start = max((position - width//2), 0)
        end = min((position + width//2), len(data))
        # print start, end, -width//10
        return np.average(np.sort(data[start:end])[-width//10:])

def bpm2numsamples(bpm):
    return filtered_framerate / (bpm / 60)

def trybeat(envelope, bpm, num_teeth):
    """Try a 3-sample comb filter on the envelope-filtered data at a given BPM. Based on Ciuffo's implementation at http://ch00ftech.com/2012/02/02/software-beat-tracking-because-a-tap-tempo-button-is-too-lazy/"""
    energy = 0
    gap = int(bpm2numsamples(bpm)) #converts BPM to samples per beat
    if (len(envelope)<=2*gap): #envelope waveform is too small to fit the comb.
        return 0, 0
    else:
        # comb_vals = [(envelope[-i]+envelope[-(i+gap)]+envelope[-(i+2*gap)])**2\
        comb_vals = [sum([envelope[-(i+j*gap)] for j in range(num_teeth)])**2\
                     for i in range(0,len(envelope)-(2*gap))]
    energy = sum(comb_vals)/(len(envelope)-(2*gap)) #take the average so that the function doesn't favor smaller combs that can calculate more values before they hit the end of the envelope waveform
    phase = comb_vals.index(max(comb_vals))
    return energy, phase

def most_likely_bpm(enveloped_data, bpm_list, num_teeth):
    max_energy = 0
    max_energy_bpm = 0
    max_energy_phase = 0
    for i, bpm in enumerate(bpm_list):
        energy, phase = trybeat(enveloped_data, bpm, num_teeth)
        if energy>max_energy:
            max_energy = energy
            max_energy_bpm = bpm
            max_energy_phase = phase
    return max_energy_bpm, max_energy_phase

if sample_width == 1: 
        fmt = "%iB" % total_samples # read unsigned chars
elif sample_width == 2:
    fmt = "%ih" % total_samples # read signed 2 byte shorts
else:
    raise ValueError("Only supports 8 and 16 bit audio formats.")

bpm_to_test = range(40, 200)
bpm_to_plot = bpm_to_test
num_teeth = int(block_size_s * (bpm_to_test[0] / 60))
# num_teeth = 3
print "teeth:", num_teeth
calculated_bpms = []
for time_ndx in range(5,6):
    channels = [ [] for x in range(num_channels) ]

    # stream.readframes(range_s[0] * framerate)
    data = stream.readframes(int(block_size_s * framerate))
    data = wave.struct.unpack(fmt, data) 

    for index, value in enumerate(data):
        bucket = index % num_channels
        channels[bucket].append(value)

    filtered_data = scipy.signal.decimate(channels[0], q, n = 30, ftype="fir")
    enveloped_data = [rolling_envelope(filtered_data, i, 10)\
                      for i in range(len(filtered_data))]
    bpm, phase = most_likely_bpm(enveloped_data, bpm_to_test, num_teeth)
    print bpm
    calculated_bpms.append(bpm)
    gap = int(bpm2numsamples(bpm))
    plt.plot(filtered_data,'b')
    plt.hold(True)
    plt.plot(enveloped_data,'r')
    plt.plot([len(enveloped_data) - phase, len(enveloped_data) - (phase + gap), len(enveloped_data) - (phase + gap*2)], [0, 0, 0], 'ko')
    plt.figure()
    plt.plot(bpm_to_plot, [trybeat(enveloped_data, 
                                   bpm, num_teeth) for bpm in bpm_to_plot])

plt.figure()
plt.plot(calculated_bpms, 'b')
plt.show()

# max_energy_gap = int(bpm2numsamples(max_energy_bpm))
# plt.plot(filtered_data,'b')
# plt.hold(True)
# plt.plot(enveloped_data,'r')
# plt.plot([len(enveloped_data) - max_energy_phase, len(enveloped_data) - (max_energy_phase + max_energy_gap), len(enveloped_data) - (max_energy_phase + max_energy_gap*2)], [0, 0, 0], 'ko')
# # plt.plot([median_rolling_envelope(channels[0], i, 1000) for i in range(len(channels[0]))],'g')
# plt.figure()
# plt.plot(bpm_to_plot, [trybeat(enveloped_data, bpm) for bpm in bpm_to_plot])
# plt.show()



