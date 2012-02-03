from listen import rolling_envelope, fast_rolling_envelope
import numpy as np

data = [np.random.random() for i in range(10000)]

output = [rolling_envelope(data, i, 10) for i in range(len(data))]

output2 = fast_rolling_envelope(data, 10)

assert all([abs(output[i] - output2[i]) < .0001 for i in range(len(output))]), [str(i) + "\n" + str(output[i]) + "\n" + str(output2[i]) for i in range(len(output)) if abs(output[i] - output2[i]) >= 1]
print "passed test"
