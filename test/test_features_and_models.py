#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# test_features_and_models.py: Training sets and the two models
#
#  Description:
#  Assert the training windows and the model outputs against the values
#  the legacy suite asserted, on the same fixture window.
#
#  These expectations came from scikit-learn 0.17 and are asserted here
#  on 1.9. That the ridge prediction still lands on 19177.97 to the cent
#  is the evidence that the estimator upgrade did not move the numbers
#  the charts report.
#
#  Test Cases:
#  - binary_class reproduces its 75 labels, window size and boundary
#    values at range 90, and its single window at the default.
#  - binary_class over the whole series reproduces the 120 labels the
#    classifier test asserted.
#  - proportion_class produces windows of the right width.
#  - A series too short for a window is refused.
#  - The decision tree reproduces its class, and the random forest
#    returns a valid one.
#  - Ridge reproduces its predicted price.
#  - Predicting before training raises ModelNotTrainedError rather than
#    AttributeError, which is what the legacy code did.
#  - An unknown estimator name is refused.
#
#  Author: id774 (More info: https://id774.net)
#  Source Code: https://github.com/id774/finance
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
#  Requirements:
#  - Python Version: 3.11 or later
#  - pandas, pytest
#
#  Version History:
#  v1.0 2026-08-14
#       Initial release.
#
########################################################################

from __future__ import annotations

import pytest

from finance import features
from finance.errors import DataFormatError, ModelError, ModelNotTrainedError
from finance.indicators import TechnicalIndicators
from finance.models import PricePredictor, TrendClassifier, new_classifier, new_regression

EXPECTED_LABELS_RANGE_90 = [
    1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 0, 1, 1, 1, 1, 1, 0, 1,
    0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 1, 0, 1, 1, 0, 1, 1,
    0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1,
    1, 1, 1, 1, 0, 1, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 1, 0,
    1, 1, 0,
]

EXPECTED_LABELS_FULL = [
    1, 0, 0, 0, 1, 1, 0, 0, 0, 0,
    0, 0, 1, 0, 0, 1, 0, 1, 0, 1,
    1, 0, 1, 1, 1, 1, 1, 0, 1, 0,
    1, 1, 1, 1, 0, 1, 0, 1, 1, 0,
    1, 0, 0, 1, 1, 1, 1, 1, 1, 1,
    0, 0, 0, 1, 0, 0, 1, 1, 1, 1,
    1, 0, 1, 0, 0, 0, 0, 0, 0, 1,
    1, 1, 0, 0, 1, 0, 1, 1, 0, 1,
    1, 0, 1, 1, 0, 1, 0, 0, 1, 0,
    1, 1, 0, 0, 1, 0, 1, 0, 1, 1,
    1, 1, 1, 0, 1, 1, 1, 0, 0, 1,
    1, 0, 0, 1, 1, 1, 0, 1, 1, 0,
]


@pytest.fixture()
def ret_index(long_prices):
    """ Return the return index the models are trained on. """
    indicators = TechnicalIndicators(long_prices)
    return indicators.calc_ret_index()["ret_index"]


def test_binary_class_reproduces_its_labels(ret_index):
    train_x, train_y = features.binary_class(ret_index, 90)

    assert list(train_y) == EXPECTED_LABELS_RANGE_90
    assert len(train_x) == 75
    assert len(train_x[0]) == 14
    assert round(train_x[-1][-1], 5) == 1.35486
    assert round(train_x[0][0], 5) == 1.19213


def test_binary_class_default_window_yields_one_sample(ret_index):
    train_x, train_y = features.binary_class(ret_index)

    assert len(train_x) == 1
    assert len(train_y) == 1
    assert train_y[0] == 0
    assert len(train_x[0]) == 14
    assert round(train_x[0][0], 5) == 1.30311


def test_binary_class_over_the_whole_series(ret_index):
    train_x, train_y = features.binary_class(ret_index, len(ret_index))

    assert list(train_y) == EXPECTED_LABELS_FULL
    assert len(train_x) == 120
    assert len(train_x[0]) == 14
    assert round(train_x[-1][-1], 5) == 1.35486
    assert round(train_x[0][0], 5) == 1.08871


def test_training_window_is_capped(ret_index):
    # 135 rows back, minus the 14 the last window occupies and the label
    # it needs, is 120 samples however much history is supplied.
    train_x, _ = features.binary_class(ret_index, 10_000)
    assert len(train_x) == 120


def test_proportion_class_windows(ret_index):
    train_x, train_y = features.proportion_class(ret_index, len(ret_index))

    assert len(train_x[0]) == 14
    assert len(train_x) == len(train_y)


def test_short_series_is_refused(ret_index):
    with pytest.raises(DataFormatError, match="at least"):
        features.binary_class(ret_index.iloc[:5], 90)


def test_latest_window_shape(ret_index):
    window = features.latest_window(ret_index)
    assert window.shape == (1, 14)


def test_latest_window_refuses_a_short_series(ret_index):
    with pytest.raises(DataFormatError, match="at least"):
        features.latest_window(ret_index.iloc[:3])


def test_decision_tree_reproduces_its_class(ret_index):
    classifier = TrendClassifier()
    train_x, train_y = classifier.train(ret_index)

    assert len(train_x) == 120
    assert list(train_y) == EXPECTED_LABELS_FULL
    assert classifier.classify(ret_index) == 0


def test_random_forest_returns_a_valid_class(ret_index):
    classifier = TrendClassifier(name="Random Forest")
    classifier.train(ret_index)
    assert classifier.classify(ret_index) in (0, 1)


def test_a_restored_classifier_trains_on_the_recent_window_only(ret_index):
    first = TrendClassifier()
    first.train(ret_index)

    restored = TrendClassifier(estimator=first.estimator)
    train_x, _ = restored.train(ret_index)
    assert len(train_x) == 1


def test_ridge_reproduces_its_prediction(ret_index, long_prices):
    predictor = PricePredictor()
    predictor.train(ret_index)

    base = long_prices["Adj Close"].iloc[0]
    assert round(predictor.predict(ret_index, base), 2) == 19177.97


def test_classifying_before_training_is_reported(ret_index):
    with pytest.raises(ModelNotTrainedError):
        TrendClassifier().classify(ret_index)


def test_predicting_before_training_is_reported(ret_index):
    with pytest.raises(ModelNotTrainedError):
        PricePredictor().predict(ret_index, 1000)


def test_unknown_estimator_names_are_refused():
    with pytest.raises(ModelError, match="Unknown classifier"):
        new_classifier("Neural Net")
    with pytest.raises(ModelError, match="Unknown regression"):
        new_regression("Elastic Net")


def test_every_advertised_classifier_can_be_built():
    from finance.models import CLASSIFIER_NAMES

    for name in CLASSIFIER_NAMES:
        assert new_classifier(name) is not None
