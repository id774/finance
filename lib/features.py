import sys
import os
import numpy as np
p = os.path.dirname(os.path.abspath(__file__))
if p in sys.path:
    pass
else:
    sys.path.append(p)

class Features():

    def create_features(self, arr):
        train_X = []
        train_y = []
        for i in np.arange(-90, -15):
            s = i + 14
            feature = arr.ix[i:s]
            if feature[-1] < arr[s]:
                train_y.append(1)
            else:
                train_y.append(0)
            train_X.append(feature.values)
        return np.array(train_X), np.array(train_y)
