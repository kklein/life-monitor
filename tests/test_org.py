import os

# TODO: Get rid of path hack.
import sys

import pandas as pd
import pytest

from monitoring import org

sys.path.insert(0, os.path.abspath(".."))


@pytest.fixture(scope="module")
def numeric_series():
    return pd.Series([1, 2, 3, 4, 5])


@pytest.mark.parametrize(
    "data",
    [
        # sd, mean, n_days, is_negative, is_inverted, outcome
        (1, 3, 1, False, False, True),
        (1, 3, 1, True, False, False),
        (1, 3, 1, True, False, False),
        (1, 3, 1, True, True, True),
    ],
)
def test_has_daily_message(numeric_series, data):
    (sd, mean, n_days, is_negative, is_inverted, outcome) = data
    assert (
        org._has_daily_message(
            values=numeric_series.tail(n_days),
            sigma=sd,
            mean=mean,
            n_days=n_days,
            is_negative=is_negative,
            is_inverted=is_inverted,
        )
        == outcome
    )
