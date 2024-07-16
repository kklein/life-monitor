import os

# TODO: Get rid of path hack.
import sys

import pytest

from monitoring import cal, utils

sys.path.insert(0, os.path.abspath(".."))


@pytest.fixture(scope="module")
def events():
    return [
        {
            "kind": "calendar#event",
            "created": "2020-01-01T21:34:53.000Z",
            "updated": "2020-01-01T21:34:53.480Z",
            "summary": "Running",
            "description": "14.91 km",
            "colorId": "4",
            "start": {
                "dateTime": "2020-01-01T08:30:00+01:00",
                "timeZone": "Europe/Rome",
            },
            "end": {"dateTime": "2020-01-01T10:00:00+01:00", "timeZone": "Europe/Rome"},
            "eventType": "default",
        },
        {
            "kind": "calendar#event",
            "created": "2020-01-02T21:34:53.000Z",
            "updated": "2020-01-02T21:34:53.480Z",
            "summary": "Gym",
            "colorId": "4",
            "start": {
                "dateTime": "2020-01-02T08:30:00+01:00",
                "timeZone": "Europe/Rome",
            },
            "end": {"dateTime": "2020-01-02T10:00:00+01:00", "timeZone": "Europe/Rome"},
            "eventType": "default",
        },
        {
            "kind": "calendar#event",
            "created": "2020-01-03T21:34:53.000Z",
            "updated": "2020-01-03T21:34:53.480Z",
            "summary": "Swimming",
            "description": ".6km",
            "colorId": "4",
            "start": {
                "dateTime": "2020-01-03T08:30:00+01:00",
                "timeZone": "Europe/Rome",
            },
            "end": {"dateTime": "2020-01-03T10:00:00+01:00", "timeZone": "Europe/Rome"},
            "eventType": "default",
        },
        {
            "kind": "calendar#event",
            "created": "2020-01-04T21:34:53.000Z",
            "updated": "2020-01-04T21:34:53.480Z",
            "summary": "Gym: ub",
            "colorId": "4",
            "start": {
                "dateTime": "2020-01-04T08:30:00+01:00",
                "timeZone": "Europe/Rome",
            },
            "end": {"dateTime": "2020-01-04T10:00:00+01:00", "timeZone": "Europe/Rome"},
            "eventType": "default",
        },
        *[
            {
                "kind": "calendar#event",
                "created": f"2020-01-0{day}T21:34:53.000Z",
                "updated": f"2020-01-0{day}T21:34:53.480Z",
                "summary": "Running",
                "description": "14.91 km",
                "colorId": "4",
                "start": {
                    "dateTime": f"2020-01-{day}T08:30:00+01:00",
                    "timeZone": "Europe/Rome",
                },
                "end": {
                    "dateTime": f"2020-01-0{day}T10:00:00+01:00",
                    "timeZone": "Europe/Rome",
                },
                "eventType": "default",
            }
            for day in range(5, 8)
        ],
    ]


def test_smoke_get_getdataframe(events):
    cal.get_dataframe(events)


@pytest.mark.parametrize(
    "data",
    [
        (utils.Sport.running, 4),
        (utils.Sport.gym, 2),
        (utils.Sport.gym_ub, 1),
        (utils.Sport.cycling, 0),
    ],
)
def test_get_summary_filter(data, events):
    sport, expected_count = data
    filter_function = cal._get_summary_filter(sport)
    actual_count = len(list(filter(filter_function, events)))
    assert actual_count == expected_count


@pytest.mark.parametrize("sport", [utils.Sport.swimming, utils.Sport.running])
def test_prune_events_distance(events, sport):
    filter_function = cal._get_summary_filter(sport)
    sport_events = list(filter(filter_function, events))
    pruned_events = cal.prune_events(sport_events)
    for event in pruned_events:
        assert isinstance(event["distance"], float)


@pytest.mark.parametrize(
    "flawed_event",
    [
        # Invalid sport kind.
        {
            "kind": "calendar#event",
            "created": "2020-01-01T21:34:53.000Z",
            "updated": "2020-01-01T21:34:53.480Z",
            "summary": "Running w/ Bob",
            "description": "14.91 km",
            "colorId": "4",
            "start": {
                "dateTime": "2020-01-01T08:30:00+01:00",
                "timeZone": "Europe/Rome",
            },
            "end": {"dateTime": "2020-01-01T10:00:00+01:00", "timeZone": "Europe/Rome"},
            "eventType": "default",
        },
        # Distance not convertible.
        {
            "kind": "calendar#event",
            "created": "2020-01-01T21:34:53.000Z",
            "updated": "2020-01-01T21:34:53.480Z",
            "summary": "Running",
            "description": "14.a91 km",
            "colorId": "4",
            "start": {
                "dateTime": "2020-01-01T08:30:00+01:00",
                "timeZone": "Europe/Rome",
            },
            "end": {"dateTime": "2020-01-01T10:00:00+01:00", "timeZone": "Europe/Rome"},
            "eventType": "default",
        },
        # dateTime filed not a valid Datetime
        {
            "kind": "calendar#event",
            "created": "2020-01-01T21:34:53.000Z",
            "updated": "2020-01-01T21:34:53.480Z",
            "summary": "Running",
            "description": "14.91 km",
            "colorId": "4",
            "start": {"dateTime": "2020-01-z8:30:00+01:00", "timeZone": "Europe/Rome"},
            "end": {"dateTime": "2020-01-01T10:00:00+01:00", "timeZone": "Europe/Rome"},
            "eventType": "default",
        },
    ],
)
def test_prune_events_failure(flawed_event):
    with pytest.raises(Exception):
        cal.prune_events([flawed_event])


@pytest.mark.parametrize("data", [(i, True) for i in range(1, 4)] + [(4, False)])
def test_streak(events, data):
    sport = utils.Sport.running
    duration, expected_result = data
    filter_function = cal._get_summary_filter(sport)
    running_events = list(filter(filter_function, events))
    df = cal.get_dataframe(running_events)
    actual_result = cal.streak(df, utils.Sport.running, minimal_duration=duration) is not None
    assert actual_result == expected_result
