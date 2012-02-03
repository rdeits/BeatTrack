from __future__ import division

import wave
import numpy as np
import scipy.signal
import matplotlib.pyplot as plt
import bisect
from scipy_savitzky import savitzky_golay

def fast_rolling_envelope(data, width):
    """Do a rolling envelope filter on array [data], returning an array of the same length."""
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

def bpm2numsamples(bpm, filtered_framerate):
    return int(filtered_framerate / (bpm / 60))

def trybeat(envelope, bpm, num_teeth, filtered_framerate):
    """Try a 3-sample comb filter on the envelope-filtered data at a given BPM. Based on Ciuffo's implementation at http://ch00ftech.com/2012/02/02/software-beat-tracking-because-a-tap-tempo-button-is-too-lazy/"""
    energy = 0
    gap = bpm2numsamples(bpm, filtered_framerate) #converts BPM to samples per beat
    comb_width = (num_teeth - 1) * gap
    if (len(envelope)<=comb_width): #envelope waveform is too small to fit the comb.
        return 0, 0
    else:
        # comb_positions = gap
        comb_positions = len(envelope) - comb_width

        comb_vals = np.array([np.sum(envelope[[-(i+j*gap) for j in range(num_teeth)]])
                              for i in range(comb_positions)])
        comb_vals = np.power(comb_vals, 2)
    energy = np.sum(comb_vals)/comb_positions #take the average so that the function doesn't favor smaller combs that can calculate more values before they hit the end of the envelope waveform
    phase = np.argmax(comb_vals)
    return energy, phase

def most_likely_bpm(enveloped_data, bpm_list, num_teeth, filtered_framerate):
    max_energy = 0
    max_energy_bpm = 0
    max_energy_phase = 0
    for i, bpm in enumerate(bpm_list):
        energy, phase = trybeat(enveloped_data, bpm, num_teeth, filtered_framerate)
        if energy > max_energy:
            max_energy = energy
            max_energy_bpm = bpm
            max_energy_phase = phase
    return max_energy_bpm, max_energy_phase


if __name__  == "__main__":
    block_size_s = 5
    stream = wave.open('crazy.wav', 'r')
    num_channels = stream.getnchannels()
    framerate = stream.getframerate()
    total_samples = int(framerate * block_size_s) * num_channels
    sample_width = stream.getsampwidth()
    if sample_width == 1: 
            fmt = "%iB" % total_samples # read unsigned chars
    elif sample_width == 2:
        fmt = "%ih" % total_samples # read signed 2 byte shorts
    else:
        raise ValueError("Only supports 8 and 16 bit audio formats.")
    cutoff = 160
    nyq = framerate/2
    q = int(nyq//cutoff)
    filtered_framerate = framerate / q
    bpm_to_test = range(50, 170)
    bpm_to_plot = bpm_to_test
    print block_size_s, bpm_to_test[0]
    num_teeth = int(block_size_s * (bpm_to_test[0] / 60.))
    print "teeth:", num_teeth
    assert num_teeth > 3, "Block size too small"
    calculated_bpms = []
    for time_ndx in range(10):
        channels = [ [] for x in range(num_channels) ]

        # stream.readframes(range_s[0] * framerate)
        data = stream.readframes(int(block_size_s * framerate))
        data = wave.struct.unpack(fmt, data)

        for index, value in enumerate(data):
            bucket = index % num_channels
            channels[bucket].append(value)

        filtered_data = scipy.signal.decimate(channels[0], q, n=3, ftype="iir")
        enveloped_data = fast_rolling_envelope(filtered_data, 10)
        # enveloped_data = np.diff(enveloped_data)
        # enveloped_data = savitzky_golay(enveloped_data, 11, 3, deriv=0)
        # enveloped_data = fast_rolling_envelope(enveloped_data, 10)
        # enveloped_data = np.power(enveloped_data, 2)
        # enveloped_data = savitzky_golay(enveloped_data, 11, 3, deriv=0)
        bpm, phase = most_likely_bpm(enveloped_data, 
                                     bpm_to_test, num_teeth, 
                                     filtered_framerate)
        print "Most likely BPM:", bpm
        calculated_bpms.append(bpm)
        gap = bpm2numsamples(bpm, filtered_framerate)
        if time_ndx == 0:
            plt.plot(filtered_data,'b')
            plt.hold(True)
            plt.plot(enveloped_data,'r')
            plt.plot([len(enveloped_data) - (phase + gap * i) for i in range(num_teeth)], [0 for i in range(num_teeth)], 'ko')
            plt.figure()
            bpm_energies = [trybeat(enveloped_data, 
                                           bpm, num_teeth,
                                           filtered_framerate) for bpm in bpm_to_plot]
            plt.plot(bpm_to_plot, bpm_energies)
            # plt.figure()
            # plt.plot(bpm_to_plot, np.diff(bpm_energies))

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



