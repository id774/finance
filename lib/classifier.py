import sys
import os
from sklearn import tree
try:
    import cPickle as pickle
except:
    import pickle
p = os.path.dirname(os.path.abspath(__file__))
if p in sys.path:
    pass
else:
    sys.path.append(p)
from features import Features

class Classifier():

    def __init__(self, filename, **kwargs):
        self.filename = os.path.join(os.path.dirname(
                                     os.path.abspath(__file__)),
                                     '..', 'clf',
                                     filename)

    def _new_clf(self):
        return tree.DecisionTreeClassifier()

    def _save_clf(self):
        with open(self.filename, 'wb') as f:
            pickle.dump(self.clf, f)

    def _load_clf(self):
        with open(self.filename, 'rb') as f:
            clf = pickle.load(f)
        return clf

    def train(self, arr):
        f = Features()

        if os.path.exists(self.filename):
            self.clf = self._load_clf()
            train_X, train_y = f.create_features(arr)
        else:
            self.clf = self._new_clf()
            train_X, train_y = f.create_features(arr, 90)

        self.clf.fit(train_X, train_y)
        self._save_clf()

        return train_X, train_y

    def classify(self, test_X):
        return self.clf.predict(test_X)
