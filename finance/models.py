#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# finance/models.py: Trend classification and price prediction
#
#  Description:
#  Wrap the two scikit-learn estimators the pipeline applies to a return
#  index: a classifier answering whether the next value rises, and a
#  ridge regression estimating the next value, which the chart caption
#  reports as a price.
#
#  Both are deliberately small. They are a decoration on a chart, not an
#  investment tool, and this module keeps them at the size the charts
#  need rather than growing them into something a reader might trust
#  further than the author does.
#
#  Persistence is not here. A model is fitted, applied and handed back;
#  loading and saving belong to finance/storage.py, so that these
#  classes can be exercised without a filesystem.
#
#  Author: id774 (More info: http://id774.net)
#  Source Code: https://github.com/id774/finance
#  Contact: idnanashi@gmail.com
#
#  Requirements:
#  - Python Version: 3.11 or later
#  - NumPy, pandas, scikit-learn
#
#  Version History:
#  v2.0 2026-08-14
#       Separate persistence from fitting and drop the removed
#       scikit-learn import paths.
#
########################################################################

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.ensemble import AdaBoostClassifier, RandomForestClassifier
from sklearn.linear_model import Lasso, Ridge
from sklearn.naive_bayes import BernoulliNB, GaussianNB, MultinomialNB
from sklearn.tree import DecisionTreeClassifier

from finance import features
from finance.errors import ModelError, ModelNotTrainedError

DEFAULT_CLASSIFIER = "Decision Tree"
DEFAULT_REGRESSION = "Ridge"
DEFAULT_ALPHA = 1.0

# The classifier names the CLI and the tests refer to. The set is the
# one this repository has always offered; only "Decision Tree" is used
# by the nightly run.
CLASSIFIER_NAMES = (
    "Decision Tree",
    "Random Forest",
    "AdaBoost",
    "Gaussian Naive Bayes",
    "Multinomial Naive Bayes",
    "Bernoulli Naive Bayes",
    "LDA",
)

REGRESSION_NAMES = ("Ridge", "Lasso")


def new_classifier(name: str = DEFAULT_CLASSIFIER) -> Any:
    """
    Build an unfitted classifier by name.

    Raises:
        ModelError: The name is not one of CLASSIFIER_NAMES.
    """
    builders = {
        "Decision Tree": lambda: DecisionTreeClassifier(max_depth=5),
        "Random Forest": lambda: RandomForestClassifier(
            max_depth=5, n_estimators=10, max_features=1
        ),
        "AdaBoost": AdaBoostClassifier,
        "Gaussian Naive Bayes": GaussianNB,
        "Multinomial Naive Bayes": MultinomialNB,
        "Bernoulli Naive Bayes": BernoulliNB,
        "LDA": LinearDiscriminantAnalysis,
    }
    if name not in builders:
        raise ModelError(
            "Unknown classifier: {0}. Choose one of {1}".format(name, ", ".join(CLASSIFIER_NAMES))
        )
    return builders[name]()


def new_regression(name: str = DEFAULT_REGRESSION, alpha: float = DEFAULT_ALPHA) -> Any:
    """
    Build an unfitted regression by name.

    Raises:
        ModelError: The name is not one of REGRESSION_NAMES.
    """
    if name == "Ridge":
        return Ridge(alpha=alpha)
    if name == "Lasso":
        return Lasso(alpha=alpha)
    raise ModelError(
        "Unknown regression: {0}. Choose one of {1}".format(name, ", ".join(REGRESSION_NAMES))
    )


class TrendClassifier:
    """ Predict whether the next value of a return index rises. """

    def __init__(self, estimator: Any | None = None, name: str = DEFAULT_CLASSIFIER) -> None:
        """
        Args:
            estimator: A previously fitted estimator to continue from.
                When omitted a fresh one is built.
            name: Which estimator to build when none is supplied.
        """
        self.name = name
        self.estimator = estimator
        self.is_new = estimator is None

    def train(self, ret_index: pd.Series) -> tuple[np.ndarray, np.ndarray]:
        """
        Fit the classifier on the return index.

        A model being seen for the first time is fitted over the whole
        available history; one restored from disk is refreshed on the
        most recent window only, which is what makes the nightly run
        cheap.

        Returns:
            The training features and labels that were used.
        """
        window = len(ret_index) if self.is_new else features.WINDOW_SIZE + 2
        train_x, train_y = features.binary_class(ret_index, window)
        if self.estimator is None:
            self.estimator = new_classifier(self.name)
        try:
            self.estimator.fit(train_x, train_y)
        except Exception as exc:  # noqa: BLE001 - scikit-learn raises several unrelated types
            raise ModelError("Classifier could not be fitted: {0}".format(exc)) from exc
        return train_x, train_y

    def classify(self, ret_index: pd.Series) -> int:
        """
        Return 1 when the next value is predicted to rise, otherwise 0.

        Raises:
            ModelNotTrainedError: train() has not been called.
        """
        if self.estimator is None:
            raise ModelNotTrainedError("The classifier must be trained before it can classify")
        try:
            predicted = self.estimator.predict(features.latest_window(ret_index))
        except Exception as exc:  # noqa: BLE001 - scikit-learn raises several unrelated types
            raise ModelError("Classification failed: {0}".format(exc)) from exc
        return int(predicted[0])


class PricePredictor:
    """ Estimate the next value of a return index and scale it to a price. """

    def __init__(
        self,
        estimator: Any | None = None,
        name: str = DEFAULT_REGRESSION,
        alpha: float = DEFAULT_ALPHA,
    ) -> None:
        """
        Args:
            estimator: A previously fitted estimator to continue from.
            name: Which regression to build when none is supplied.
            alpha: Regularization strength of the built regression.
        """
        self.name = name
        self.alpha = alpha
        self.estimator = estimator
        self.is_new = estimator is None

    def train(self, ret_index: pd.Series) -> tuple[np.ndarray, np.ndarray]:
        """
        Fit the regression on the return index.

        Returns:
            The training features and targets that were used.
        """
        window = len(ret_index) if self.is_new else features.WINDOW_SIZE + 2
        train_x, train_y = features.proportion_class(ret_index, window)
        if self.estimator is None:
            self.estimator = new_regression(self.name, self.alpha)
        try:
            self.estimator.fit(train_x, train_y)
        except Exception as exc:  # noqa: BLE001 - scikit-learn raises several unrelated types
            raise ModelError("Regression could not be fitted: {0}".format(exc)) from exc
        return train_x, train_y

    def predict(self, ret_index: pd.Series, base: float) -> float:
        """
        Return the predicted price.

        The regression works on the return index, which is based at 1 on
        the first row of the window, so its output is multiplied by the
        price of that row to get back to currency.

        Args:
            ret_index: The return index series.
            base: The adjusted close the return index is based on.

        Raises:
            ModelNotTrainedError: train() has not been called.
        """
        if self.estimator is None:
            raise ModelNotTrainedError("The regression must be trained before it can predict")
        try:
            predicted = self.estimator.predict(features.latest_window(ret_index))
        except Exception as exc:  # noqa: BLE001 - scikit-learn raises several unrelated types
            raise ModelError("Prediction failed: {0}".format(exc)) from exc
        return float(predicted[0]) * float(base)
