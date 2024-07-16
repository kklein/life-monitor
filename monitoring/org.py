import datetime
import operator
from math import ceil
from pathlib import Path
from typing import Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pydantic
from orgparse import load

WEEK_ROOT = Path("/Users/kevin/org/weeks")
PROPERTIES = [
    "Sleep",
    "Exercise",
    "Happiness",
    "Wellbeing",
    "Eating",
    "Stress",
    "Fasting",
]
# Property of the underlying org file format.
_FIRST_WEEKDAY_INDEX = 3


def _this_week():
    return datetime.date.today().isocalendar().week


def _find_max_week(path: Path):
    """Find last availabe week org file."""
    return max(int(file.name.split(".org")[0]) for file in path.iterdir())


IntInput = Union[pydantic.conint(ge=0, le=5), pydantic.constr(pattern="x")]  # noqa: F821


class DayData(pydantic.BaseModel):
    Sleep: IntInput
    Exercise: IntInput
    Happiness: IntInput
    Wellbeing: IntInput
    Eating: IntInput
    Stress: IntInput
    Fasting: Union[pydantic.confloat(ge=-1), pydantic.constr(pattern="x")]  # noqa: F821
    week: int


def _validate_data(values: dict):
    for key, value in values.items():
        if not isinstance(key, int) or key < 0 or key > 366:
            raise ValueError(f"Encountered an unexpected day-key: {key}")
        values[key] = dict(DayData(**value))
    return values


def load_data(
    max_week: int = None,
    week_root: Path = WEEK_ROOT,
    first_weekday_index: int = _FIRST_WEEKDAY_INDEX,
) -> pd.DataFrame:
    values = {}
    if max_week is None:
        max_week = _this_week()
    for week in range(1, max_week + 1):
        root = load(week_root / f"{week}.org")
        for child_index in range(first_weekday_index, first_weekday_index + 7):
            day_values = root.children[child_index].properties
            day_values.update({"week": week})
            day = (week - 1) * 7 + (child_index - first_weekday_index)
            values[day] = day_values
    values = _validate_data(values)
    df = pd.DataFrame(values)
    return df.transpose()


def process_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.replace("x", np.nan)
    df = df.replace("-1", np.nan)
    # Float allows for nans, int not.
    df = df.astype(np.float16)
    df = df.assign(week=df["week"].astype(int))
    return df


def _df_this_week(df):
    return df[df["week"] == _this_week()]


def _df_last_week(df):
    return df[df["week"] == _this_week() - 1]


def _df_last_days(df, n_days):
    # There is no straightforward mapping between the current date
    # and the day index.
    return df.dropna().tail(n_days)


def _non_corrected_sd(values):
    """Estimate the non-corrected empirical standard deviation."""
    if values is None or len(values) == 0:
        return 0
    mean = sum(values) / len(values)
    var = sum((value - mean) ** 2 for value in values) / len(values)
    return np.sqrt(var)


def _get_operator(is_negative, is_inverted):
    """Obtain the appropriate operator for a monitoring comparison.

    If ``is_negative``, the comparison attempts to assess whether a 'negative'
    condition is satisfied. An example of that would be to have slept badly.
    If ``is_inverted``, the values to be assess are interpreted as better when
    smaller in value.
    """
    if is_negative != is_inverted:
        return operator.le
    return operator.ge


def _get_threshold(is_negative, is_inverted, mean, deviation):
    """Obtain the appropriate threshold for a monitoring comparison.

    If ``is_negative``, the comparison attempts to assess whether a 'negative'
    condition is satisfied. An example of that would be to have slept badly.
    If ``is_inverted``, the values to be assess are interpreted as better when
    smaller in value.

    If either ``is_negative`` or ``is_inverted``, we define a lower bound.
    Otherwise, we define an upper bound.
    """
    return mean + (-1) ** (is_negative + is_inverted) * deviation


def _has_daily_message(values, sigma, mean, n_days, is_negative, is_inverted):
    op = _get_operator(is_negative, is_inverted)
    if n_days == 1:
        deviation = 2 * sigma
    elif n_days == 2:
        deviation = sigma
    else:
        raise ValueError(f"Unexpected number of days: {n_days}.")
    threshold = _get_threshold(is_negative, is_inverted, mean, deviation)
    return op(values, threshold).all()


def _has_weekly_message(global_values, local_mean, quantile, is_negative, is_inverted):
    threshold = global_values.quantile(q=quantile)
    op = _get_operator(is_negative, is_inverted)
    return op(local_mean, threshold)


def messages_this_week(
    df, columns: list[str] = PROPERTIES, lower_quantile=0.4, upper_quantile=0.6
) -> list[str]:
    df_this_week = _df_this_week(df)
    messages = []
    for column in columns:
        local_mean = df_this_week[column].mean()
        is_inverted = column == "Stress"
        if _has_weekly_message(
            df[column],
            local_mean,
            quantile=lower_quantile,
            is_inverted=is_inverted,
            is_negative=True,
        ):
            messages.append(f"Oh. {column} was not so great this week.")
        if _has_weekly_message(
            df[column],
            local_mean,
            quantile=upper_quantile,
            is_inverted=is_inverted,
            is_negative=False,
        ):
            messages.append(f"Jeez! {column} was truly splendid this week.")
    return messages


def messages_this_day(df, columns: list[str] = PROPERTIES) -> list[str]:
    messages = []
    for column in columns:
        non_nan_values = df[column].dropna()
        global_sigma = _non_corrected_sd(non_nan_values)
        global_mean = sum(non_nan_values) / len(non_nan_values)
        is_inverted = column == "Stress"
        if _has_daily_message(
            _df_last_days(df, n_days=1)[column],
            global_sigma,
            global_mean,
            n_days=1,
            is_negative=True,
            is_inverted=is_inverted,
        ):
            messages.append(
                f"Hmm. {column} looked not good yesterday. What can be done?"
            )
        if _has_daily_message(
            _df_last_days(df, n_days=2)[column],
            global_sigma,
            global_mean,
            n_days=2,
            is_negative=True,
            is_inverted=is_inverted,
        ):
            messages.append(
                f"{column} has looked problematic over the past two days. Take it easy pal."
            )
    return messages


def images_this_week(df, columns: list[str] = PROPERTIES, path=None) -> list[Path]:
    df_this_week = _df_this_week(df)
    n_dims = int(ceil(len(columns) ** 0.5))
    fig, axs = plt.subplots(n_dims, n_dims)
    counter = 0
    for row in axs:
        for ax in row:
            if counter >= len(columns):
                fig.delaxes(ax)
                continue
            column = columns[counter]
            ax.set_title(column)
            df_this_week.plot(y=column, ax=ax, style=".", label="_nolegend")
            ax.axhline(df[column].mean(), label="avg ytd", color="orange")
            ax.axhline(
                _df_last_week(df)[column].mean(), label="avg last week", color="red"
            )
            ax.axhline(df_this_week[column].mean(), label="avg this week", color="blue")
            ax.get_legend().remove()
            counter += 1
    handles, labels = axs[0][0].get_legend_handles_labels()
    fig.suptitle(f"week {_this_week()}")
    fig.legend(handles, labels, loc="lower right")
    fig.subplots_adjust(hspace=0.7)
    file_path = "this_week.png" if path is None else path / "this_week.png"
    fig.savefig(file_path)
    fig.show()
    return [file_path]
