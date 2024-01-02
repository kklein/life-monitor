import numpy as np
import pandas as pd
from . import utils


def observed_disciplines(df: pd.DataFrame) -> list[str]:
    return df["title"].unique().tolist()


def yearly_counts(df: pd.DataFrame) -> dict[int, int]:
    return df.groupby("year")["title"].count().to_dict()


def yearly_discipline_counts(df: pd.DataFrame) -> dict[int, dict[str, int]]:
    disciplines = observed_disciplines(df)
    years = observed_years(df)
    counts = {year: {d: 0.0 for d in disciplines} for year in years}
    counts |= (
        df.groupby(["year", "title"])["date_string"]
        .count()
        .unstack(level=-1)
        .fillna(0)
        .to_dict(orient="index")
    )
    return counts


def counts_to_probabilities(
    counts: dict[int, dict[str, int]], yearly_sums
) -> dict[int, dict[str, float]]:
    probabilities = {}
    for year in counts.keys():
        probabilities[year] = {
            discipline: count / yearly_sums[year]
            for discipline, count in counts[year].items()
        }
    return probabilities


def observed_years(df: pd.DataFrame) -> list[int]:
    return df["year"].unique().tolist()


def variety(df: pd.DataFrame) -> tuple[dict[int, dict[str, float]], dict[int, float]]:
    years = observed_years(df)
    counts = yearly_discipline_counts(df)
    yearly_sums = yearly_counts(df)
    probabilities = counts_to_probabilities(counts, yearly_sums)
    entropies = {year: utils.kl(probabilities[year].values()) for year in years}
    return (probabilities, entropies)

class Radar(object):
    def __init__(self, figure, title, labels, rect=None):
        if rect is None:
            rect = [0.05, 0.05, 0.9, 0.9]

        self.n = len(title)
        self.angles = np.arange(0, 360, 360.0/self.n)

        self.axes = [figure.add_axes(rect, projection='polar', label='axes%d' % i) for i in range(self.n)]

        self.ax = self.axes[0]
        self.ax.set_thetagrids(self.angles, labels=title, fontsize=14)
        self.ax.xaxis.set_tick_params(pad=10)

        for ax in self.axes[1:]:
            ax.patch.set_visible(False)
            ax.grid(False)
            ax.xaxis.set_visible(False)

        for ax, angle, label in zip(self.axes, self.angles, labels):
            ax.set_rgrids([0.05, .25, .5, .75, 1], angle=angle, labels=label)
            ax.spines['polar'].set_visible(False)
            ax.set_ylim(0, 1)

    def plot(self, values, *args, **kw):
        angle = np.deg2rad(np.r_[self.angles, self.angles[0]])
        values = np.r_[values, values[0]]
        self.ax.plot(angle, values, *args, **kw)


    def fill(self, values, *args, **kw):
        angle = np.deg2rad(np.r_[self.angles, self.angles[0]])
        values = np.r_[values, values[0]]
        self.ax.fill(angle, values, *args, **kw)
