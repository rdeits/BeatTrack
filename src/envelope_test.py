from listen import rolling_envelope, fast_rolling_envelope
import numpy as np
import timeit

setup_stmt = """
from listen import rolling_envelope, fast_rolling_envelope
import numpy as np
data = [np.random.random() for i in range(100000)]
width = 100
"""

# data = [np.random.random() for i in range(10000)]

t = timeit.Timer("""
                 output = [rolling_envelope(data, i, width) for i in range(len(data))]
                 """, setup_stmt) 

t2 = timeit.Timer("""
                  output2 = fast_rolling_envelope(data, width) #.556 seconds
                  """, setup_stmt)

print "Original:", t.timeit(10)/10.
print "Fast:", t2.timeit(10)/10.

# assert all([abs(output[i] - output2[i]) < .0001 for i in range(len(output))]), [str(i) + "\n" + str(output[i]) + "\n" + str(output2[i]) for i in range(len(output)) if abs(output[i] - output2[i]) >= 1]
# print "passed test"
