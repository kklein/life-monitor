# Much of this module relies on the idea that the 'current' date is the date of the most recent activity.
# It is therefore a users' responsibility to ensure whether this corresponds to their expectations.
# In particular, they might use ``get_time_relevant_events`` to verify this before proceding to use
# functions such as ``running_previous_year``.

import datetime
from functools import partial
from pathlib import Path
from typing import Union

import matplotlib.pyplot as plt
import pandas as pd
import pydantic

from . import utils


def _current_date(df):
    return df["date"].max()


def _current_year(df):
    return df[df["date"] == _current_date(df)]["year"].iloc[0]


def _current_month(df):
    return df[df["date"] == _current_date(df)]["month"].iloc[0]


def _current_week(df):
    return df[df["date"] == _current_date(df)]["week"].iloc[0]


def _previous_month(df):
    # Returning 0 for January is currently intended.
    current_month = _current_month(df)
    return current_month - 1


def _distance_last_event(df):
    # There could be several events on the given date, hence the sum.
    return df[df["date"] == _current_date(df)]["distance"].sum()


def _get_summary_filter(sport: utils.Sport):
    def summary_filter(event):
        # If generic 'gym' is given, we want to select any kind of gym event.
        if sport == utils.Sport.gym:
            return "summary" in event and event["summary"].lower() in [
                utils.Sport.gym.value,
                utils.Sport.gym_c.value,
                utils.Sport.gym_lb.value,
                utils.Sport.gym_ub.value,
            ]
        return (
            "summary" in event
            # Running and Cycling events are excatly called as just spelled.
            # Some social, non-desired events are called 'Running w/ friend'
            # and should not be considered.
            and event["summary"].lower() == sport.value
        )

    return summary_filter


def _get_color_filter(color):
    def color_filter(event):
        return "colorId" in event and event["colorId"] == color

    return color_filter


def get_events(service, timestamp_start, timestamp_end):
    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=timestamp_start,
            timeMax=timestamp_end,
            maxResults=100000,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    return events_result.get("items", [])


def get_time_relevant_events(
    df, interval: utils.TriggerInterval, date: datetime.date = datetime.date.today()
):
    if interval == utils.TriggerInterval.daily:
        return df[
            (df["year"] == date.year)
            & (df["month"] == date.month)
            & (df["day"] == date.day)
        ]
    if interval == utils.TriggerInterval.weekly:
        return df[(df["year"] == date.year) & (df["week"] == date.isocalendar().week)]
    raise ValueError(f"Unexpected TriggerInterval: {interval}.")


def has_time_relevant_event(
    df, interval: utils.TriggerInterval, date: datetime.date = datetime.date.today()
):
    return len(get_time_relevant_events(df, interval, date)) > 0


def get_dataframe(events):
    df = pd.DataFrame(data=prune_events(events))
    if len(df) == 0:
        return df
    df["date"] = pd.to_datetime(df["date_string"], utc=True)
    df["day"] = df["date"].dt.day
    df["week"] = df["date"].dt.isocalendar().week
    df["month"] = df["date"].dt.month
    df["year"] = df["date"].dt.year
    df["distance"] = pd.to_numeric(df["distance"])
    df["hour"] = df["date"].dt.hour
    return df


class EventDatum(pydantic.BaseModel):
    date_string: datetime.datetime
    # Swimming distance can be very short, cycling distance very long.
    distance: Union[pydantic.confloat(ge=0.1, le=250), None]
    title: utils.Sport

    # This is necessary to prevent the entire enum to be stored instead of its value.
    # https://stackoverflow.com/questions/65209934/pydantic-enum-field-does-not-get-converted-to-string
    class Config:
        use_enum_values = True


def _parse_data(raw_data):
    parsed_data = pydantic.parse_obj_as(list[EventDatum], raw_data)
    return [dict(event) for event in parsed_data]


def prune_events(events):
    """Prune event rows as to only include certain columns."""
    raw_data = [
        {
            "date_string": event["start"]["dateTime"],
            "distance": event["description"].split("km")[0]
            if "description" in event
            else None,
            "title": event["summary"].lower(),
        }
        for event in events
    ]
    return _parse_data(raw_data)


def get_filtered_events(
    service, timestamp_start, timestamp_end, filter_kind, filter_value
):
    """Filter row events to only include certain event kinds."""
    events = get_events(service, timestamp_start, timestamp_end)
    if filter_kind == "summary":
        filter_function = _get_summary_filter(sport=filter_value)
    elif filter_kind == "color":
        filter_function = _get_color_filter(color=filter_value)
    else:
        raise ValueError(f"Unexpected filter_kind: {filter_kind}.")
    return list(filter(filter_function, events))


def distance_weekly_vs_year(df, sport: utils.Sport, quantile_threshold=0.6):
    # TODO: Fill up weeks with 0 distance in sport.
    current_date = _current_date(df)
    current_week = _current_week(df)
    current_year = _current_year(df)

    weekly = df[(df["year"] == current_year) & (df["week"] == current_week)][
        "distance"
    ].sum()

    reference_value = (
        df[
            (df["date"] >= current_date - pd.Timedelta(days=365))
            & ((df["week"] < current_week) | (df["year"] < current_year))
        ]
        .groupby("week")["distance"]
        .sum()
        .quantile(quantile_threshold)
    )

    if weekly > reference_value:
        return f"Weekly average {sport.value} volume was considerably higher than usual in past 12 months!"


def frequency_weekly_vs_year(df, sport: utils.Sport, quantile_threshold=0.6):
    # TODO: Fill up weeks with 0 distance in sport.
    current_date = _current_date(df)
    current_week = _current_week(df)
    current_year = _current_year(df)

    weekly = df[(df["year"] == current_year) & (df["week"] == current_week)][
        "date_string"
    ].count()

    reference_value = (
        df[
            (df["date"] >= current_date - pd.Timedelta(days=365))
            & ((df["week"] < current_week) | (df["year"] < current_year))
        ]
        .groupby("week")["date_string"]
        .count()
        .quantile(quantile_threshold)
    )

    if weekly > reference_value:
        return f"Weekly number of {sport.value} activities was considerably higher than usual in past 12 months!"


def distance_weekly_vs_ytd(df, sport: utils.Sport, quantile_threshold=0.6):
    # TODO: Fill up weeks with 0 distance in sport.
    current_week = _current_week(df)
    current_year = _current_year(df)

    weekly = df[(df["year"] == current_year) & (df["week"] == current_week)][
        "distance"
    ].sum()

    reference_value = (
        df[(df["year"] == current_year) & (df["week"] < current_week)]
        .groupby("week")["distance"]
        .sum()
        .quantile(quantile_threshold)
    )

    if weekly > reference_value:
        return f"Weekly average {sport.value} volume was considerably higher than usual in {current_year}!"


def frequency_weekly_vs_ytd(df, sport: utils.Sport, quantile_threshold=0.6):
    # TODO: Fill up weeks with 0 distance in sport.
    current_week = _current_week(df)
    current_year = _current_year(df)

    weekly = df[(df["year"] == current_year) & (df["week"] == current_week)][
        "date_string"
    ].count()

    reference_value = (
        df[(df["year"] == current_year) & (df["week"] < current_week)]
        .groupby("week")["date_string"]
        .count()
        .quantile(quantile_threshold)
    )

    if weekly > reference_value:
        return f"Weekly number of {sport.value} activities was considerably higher than usual in past 12 months!"


def distance_mod_interval(df, sport: utils.Sport, interval=100):
    date_last_event = _current_date(df)
    current_year = _current_year(df)

    yearly_distance_before_last_event = df[
        (df["year"] == current_year) & (df["date"] < date_last_event)
    ]["distance"].sum()
    yearly_distance_after_last_event = (
        yearly_distance_before_last_event + _distance_last_event(df)
    )
    if (
        threshold := (yearly_distance_after_last_event // interval) * interval
    ) > yearly_distance_before_last_event:
        return f"You just crossed {int(threshold)}km in {sport.value}. Congrats!"


def distance_previous_years_month(df, sport: utils.Sport):
    date_last_event = _current_date(df)
    current_month = _current_month(df)
    current_year = _current_year(df)
    previous_year = current_year - 1

    monthly_distance_previous_year = df[
        (df["year"] == previous_year) & (df["month"] == current_month)
    ]["distance"].sum()

    monthly_distance_this_year_before_last_event = df[
        (df["year"] == current_year)
        & (df["month"] == current_month)
        & (df["date"] < date_last_event)
    ]["distance"].sum()

    monthly_distance_this_year_after_last_event = (
        monthly_distance_this_year_before_last_event + _distance_last_event(df)
    )

    if (
        monthly_distance_this_year_before_last_event < monthly_distance_previous_year
    ) and (
        monthly_distance_this_year_after_last_event >= monthly_distance_previous_year
    ):
        return f"You just topped the distance of the same month of last year in {sport.value}!"


def frequency_previous_years_month(df, sport: utils.Sport):
    date_last_event = _current_date(df)
    current_month = _current_month(df)
    current_year = _current_year(df)
    previous_year = current_year - 1

    monthly_frequency_previous_year = df[
        (df["year"] == previous_year) & (df["month"] == current_month)
    ]["date_string"].count()

    monthly_frequency_this_year_before_last_event = df[
        (df["year"] == current_year)
        & (df["month"] == current_month)
        & (df["date"] < date_last_event)
    ]["date_string"].count()

    monthly_frequency_this_year_after_last_event = (
        monthly_frequency_this_year_before_last_event + 1
    )

    if (
        monthly_frequency_this_year_before_last_event < monthly_frequency_previous_year
    ) and (
        monthly_frequency_this_year_after_last_event >= monthly_frequency_previous_year
    ):
        return f"You just topped the number of {sport.value} activities of the same month of last year. Strong."


def distance_previous_year(df, sport: utils.Sport):
    date_last_event = _current_date(df)
    current_year = _current_year(df)
    previous_year = current_year - 1

    yearly_distance_previous_year = df[df["year"] == previous_year]["distance"].sum()
    yearly_distance_this_year_before_last_event = df[
        (df["year"] == current_year) & (df["date"] < date_last_event)
    ]["distance"].sum()
    yearly_distance_this_year_after_last_event = (
        yearly_distance_this_year_before_last_event + _distance_last_event(df)
    )
    if (
        yearly_distance_this_year_before_last_event < yearly_distance_previous_year
    ) and (yearly_distance_this_year_after_last_event >= yearly_distance_previous_year):
        return f"You just surpassed the {sport.value} distance of the last year! Mad!"


def frequency_previous_year(df, sport: utils.Sport):
    date_last_event = _current_date(df)
    current_year = _current_year(df)
    previous_year = current_year - 1

    yearly_frequency_previous_year = df[df["year"] == previous_year][
        "date_string"
    ].count()
    yearly_frequency_this_year_before_last_event = df[
        (df["year"] == current_year) & (df["date"] < date_last_event)
    ]["date_string"].count()
    yearly_frequency_this_year_after_last_event = (
        yearly_frequency_this_year_before_last_event + 1
    )
    if (
        yearly_frequency_this_year_before_last_event < yearly_frequency_previous_year
    ) and (
        yearly_frequency_this_year_after_last_event >= yearly_frequency_previous_year
    ):
        return f"You just suprassed the number of {sport.value} activities of last year! Sick!"


def streak(df, sport: utils.Sport, minimal_duration=3):
    date_last_event = _current_date(df).date()
    has_streak = True
    # TODO: Consider shifting this to data processing step.
    dates = [date for date in df["date"].dt.date]
    n_consecutive_days = 1
    while date_last_event - datetime.timedelta(days=n_consecutive_days) in dates:
        n_consecutive_days += 1
    has_streak = n_consecutive_days >= minimal_duration
    if has_streak:
        return f"Wow! A streak of {n_consecutive_days} {sport.value} activities!"


def _get_cumulative_day_distances(df_year):
    df = df_year.copy()
    df.loc[:, "day_of_year"] = df["date"].dt.dayofyear
    df = (
        df[["distance", "day_of_year"]]
        .groupby("day_of_year")
        .agg({"distance": "sum"})
        .reset_index()
    )
    df = df.set_index("day_of_year").cumsum().reset_index()
    return df


def plot_cumulative_day_distances(
    df, sport: utils.Sport, path: Path, n_years=2, baselines=[]
):
    fig, ax = plt.subplots()

    current_year = _current_year(df)
    df_cums = {
        year: _get_cumulative_day_distances(df[df["year"] == year])
        for year in range(current_year, current_year - n_years - 1, -1)
    }

    for year, df_cum in df_cums.items():
        df_cum.plot(
            x="day_of_year",
            y="distance",
            ax=ax,
            label=str(year),
            drawstyle="steps-post",
        )

    for baseline in baselines:
        x = list(range(365))
        y = [day_of_year * baseline / 365 for day_of_year in x]
        ax.plot(x, y, label=f"{baseline} km")

    ax.legend()
    x_max = df_cums[current_year]["day_of_year"].max()
    y_max = max(
        df_cums[year][df_cums[year]["day_of_year"] <= x_max]["distance"].max()
        for year in range(current_year, current_year - n_years - 1, -1)
    )
    ax.set_xlim(1, x_max)
    ax.set_ylim(0, y_max)
    ax.set_ylabel(f"cumulative distance in {sport.value} [km]")

    image_path = path / f"cumulative_{sport.value}.png"
    fig.savefig(image_path)
    fig.show()
    return image_path


def message_function_registry(sport: utils.Sport, interval: utils.TriggerInterval):
    if sport == utils.Sport.running and interval == utils.TriggerInterval.daily:
        return [
            partial(distance_previous_year, sport=sport),
            partial(distance_previous_years_month, sport=sport),
            partial(distance_mod_interval, sport=sport),
            partial(frequency_previous_year, sport=sport),
            partial(frequency_previous_years_month, sport=sport),
            partial(streak, sport=sport),
        ]
    if sport == utils.Sport.running and interval == utils.TriggerInterval.weekly:
        return [
            partial(distance_weekly_vs_year, sport=sport),
            partial(distance_weekly_vs_ytd, sport=sport),
            partial(frequency_weekly_vs_year, sport=sport),
            partial(frequency_weekly_vs_ytd, sport=sport),
        ]
    if sport == utils.Sport.cycling and interval == utils.TriggerInterval.daily:
        return [
            partial(distance_previous_year, sport=sport),
            partial(distance_previous_years_month, sport=sport),
            partial(distance_mod_interval, sport=sport, interval=250),
            partial(frequency_previous_year, sport=sport),
            partial(frequency_previous_years_month, sport=sport),
            partial(streak, sport=sport),
        ]
    if sport == utils.Sport.cycling and interval == utils.TriggerInterval.weekly:
        return [
            partial(distance_weekly_vs_year, sport=sport),
            partial(distance_weekly_vs_ytd, sport=sport),
        ]
    if sport == utils.Sport.gym and interval == utils.TriggerInterval.daily:
        return [
            partial(frequency_previous_year, sport=sport),
            partial(frequency_previous_years_month, sport=sport),
            partial(streak, sport=sport),
        ]
    if sport == utils.Sport.gym and interval == utils.TriggerInterval.weekly:
        return [
            partial(frequency_weekly_vs_year, sport=sport),
            partial(frequency_weekly_vs_ytd, sport=sport),
        ]
    if sport == utils.Sport.swimming and interval == utils.TriggerInterval.daily:
        return [partial(streak, sport=sport, duration=2)]
    if sport == utils.Sport.swimming and interval == utils.TriggerInterval.weekly:
        return []
    return []


def image_function_registry(
    sport: utils.Sport, interval: utils.TriggerInterval, path: Path
):
    if sport == utils.Sport.running and interval == utils.TriggerInterval.weekly:
        return [
            partial(
                plot_cumulative_day_distances,
                sport=sport,
                path=path,
                baselines=[1400, 1600],
            )
        ]
    if sport == utils.Sport.cycling and interval == utils.TriggerInterval.weekly:
        return [
            partial(
                plot_cumulative_day_distances, sport=sport, path=path, baselines=[2000]
            )
        ]
    if sport == utils.Sport.swimming and interval == utils.TriggerInterval.weekly:
        return [
            partial(plot_cumulative_day_distances, sport=sport, path=path, n_years=1)
        ]
    return []
