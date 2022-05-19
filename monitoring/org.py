import datetime
import operator
from math import ceil
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
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

    df = pd.DataFrame(values)
    return df.transpose()


def process_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.replace("x", np.nan)
    # Float allows for nans, int not.
    df = df.astype(np.float16)
    df = df.assign(week=df["week"].astype(int))
    return df


def _df_this_week(df):
    return df[df["week"] == _this_week()]


def _df_last_week(df):
    return df[df["week"] == _this_week() - 1]


def messages_this_week(
    df, columns: list[str] = PROPERTIES, lower_quantile=0.4, upper_quantile=0.6
) -> list[str]:
    df_this_week = _df_this_week(df)
    messages = []
    for column in columns:
        lower_threshold = df[column].quantile(q=lower_quantile)
        upper_threshold = df[column].quantile(q=upper_quantile)
        mean = df_this_week[column].mean()
        negative_operator = operator.lt if column != "Stress" else operator.gt
        positive_operator = operator.gt if column != "Stress" else operator.lt
        if negative_operator(mean, lower_threshold):
            messages.append(f"Oh. {column} was not so great this week.")
        if positive_operator(mean, upper_threshold):
            messages.append(f"Jeez! {column} was truly splendid this week.")
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
