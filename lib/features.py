import sys
import os
import numpy as np
p = os.path.dirname(os.path.abspath(__file__))
if p not in sys.path:
    sys.path.append(p)

class Features():

    def binary_class(self, arr, range=16):
        if range > 135:
            range = 135
        range = range * -1
        train_X = []
        train_y = []
        for i in np.arange(range, -15):
            s = i + 14
            feature = arr.ix[i:s]
            if feature[-1] < arr[s]:
                train_y.append(1)
            else:
                train_y.append(0)
            train_X.append(feature.values)
        return np.array(train_X), np.array(train_y)

    def proportion_class(self, arr, range=16):
        if range > 135:
            range = 135
        range = range * -1
        train_X = []
        train_y = []
        for i in np.arange(range, -14):
            s = i + 14
            feature = arr.ix[i:s]
            x = feature.values
            y = arr[s]
            train_X.append(x)
            train_y.append(y)
        return np.array(train_X), np.array(train_y)
