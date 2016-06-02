import sys
import os
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, AdaBoostClassifier
from sklearn.naive_bayes import GaussianNB, MultinomialNB, BernoulliNB
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as LDA
try:
    import cPickle as pickle
except:
    import pickle
p = os.path.dirname(os.path.abspath(__file__))
if p not in sys.path:
    sys.path.append(p)
from features import Features

class Classifier():

    def __init__(self, filename, **kwargs):
        self.filename = os.path.join(os.path.dirname(
                                     os.path.abspath(__file__)),
                                     '..', 'clf',
                                     filename)

    def new_clf(self, classifier="Decision Tree"):
        names = ["Decision Tree",
                 "Random Forest", "AdaBoost",
                 "Gaussian Naive Bayes",
                 "Multinomial Naive Bayes",
                 "Bernoulli Naive Bayes",
                 "LDA"]
        classifiers = [
            DecisionTreeClassifier(max_depth=5),
            RandomForestClassifier(
                max_depth=5, n_estimators=10, max_features=1),
            AdaBoostClassifier(),
            GaussianNB(), MultinomialNB(), BernoulliNB(),
            LDA()]
        dic = dict(zip(names, classifiers))
        return dic[classifier]

    def _save_clf(self):
        with open(self.filename, 'wb') as f:
            pickle.dump(self.clf, f)

    def _load_clf(self):
        with open(self.filename, 'rb') as f:
            clf = pickle.load(f)
        return clf

    def train(self, arr, remember=True,
              classifier="Decision Tree"):
        f = Features()

        if os.path.exists(self.filename):
            self.clf = self._load_clf()
            train_X, train_y = f.binary_class(arr)
        else:
            self.clf = self.new_clf(classifier=classifier)
            train_X, train_y = f.binary_class(arr, len(arr))

        self.clf.fit(train_X, train_y)
        if remember:
            self._save_clf()

        return train_X, train_y

    def classify(self, test_X):
        return self.clf.predict(test_X.values[-14:].reshape([1, -1]))
