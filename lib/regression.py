import sys
import os
from sklearn import linear_model
try:
    import cPickle as pickle
except:
    import pickle
p = os.path.dirname(os.path.abspath(__file__))
if p not in sys.path:
    sys.path.append(p)
from features import Features

class Regression():

    def __init__(self, filename, **kwargs):
        self.filename = os.path.join(os.path.dirname(
                                     os.path.abspath(__file__)),
                                     '..', 'clf',
                                     filename)

    def new_clf(self, regression_type="Ridge",
                alpha=1):
        if regression_type == "Ridge":
            clf = linear_model.Ridge(alpha=alpha)
        else:
            clf = linear_model.Lasso(alpha=alpha)
        return clf

    def _save_clf(self):
        with open(self.filename, 'wb') as f:
            pickle.dump(self.clf, f)

    def _load_clf(self):
        with open(self.filename, 'rb') as f:
            clf = pickle.load(f)
        return clf

    def train(self, arr, remember=True,
              regression_type="Ridge"):
        f = Features()

        if os.path.exists(self.filename):
            self.clf = self._load_clf()
            train_X, train_y = f.proportion_class(arr)
        else:
            self.clf = self.new_clf(regression_type=regression_type)
            train_X, train_y = f.proportion_class(arr, len(arr))

        self.clf.fit(train_X, train_y)
        if remember:
            self._save_clf()

        return train_X, train_y

    def predict(self, test_X, base):
        return self.clf.predict(test_X.values[-14:].reshape([1, -1])) * base
