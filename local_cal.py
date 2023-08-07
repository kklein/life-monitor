import os

os.chdir("/Users/kevin/Code/life-monitor")

from monitoring import cal, setup, utils

from importlib import reload
reload(cal)
reload(setup)
reload(utils)

_FIRST_YEAR = 2021

import yaml

with open("env-vars.yaml", "r") as stream:
    try:
        env_vars = yaml.safe_load(stream)
        for key, value in env_vars.items():
            os.environ[key] = value
    except yaml.YAMLError as exc:
        print(exc)

service = setup.get_calendar_service()
start = utils.first_of_jan_timestamp(year=_FIRST_YEAR)
end = utils.now_timestamp()
sport = utils.Sport.running
sport = utils.Sport.cycling

events = cal.get_events(service, start, end)

events = cal.get_filtered_events(
    service,
    start,
    end,
    "summary",
    filter_value=sport,
)
end
events[-2:]

y = cal.prune_events(events)

df = cal.get_dataframe(events)

interval = utils.TriggerInterval.weekly

if not cal.has_time_relevant_event(df, interval=interval):
    print(
        f"No event for {interval.value} {sport.value} during this past time interval."
    )

messages = [
    message_function(df) for message_function in cal.message_function_registry(sport, interval)
]
print(f"Generated messages for {interval.value} {sport.value}: {messages}")

tmpdir = setup.get_tmpdir()
image_paths = [
    image_function(df)
    for image_function in
    cal.image_function_registry(sport, interval, path=tmpdir)
]
print(f"Generated images for {interval.value} {sport.value}: {image_paths}.")

cal.image_function_registry(utils.Sport.running, interval, path=tmpdir)

z = [{"date_string": event["start"]["dateTime"],
      "distance": event.get("description", "").split("km")[0],
      "title": event["summary"]
    } for event in x]
