import os

os.chdir("/Users/kevin/Code/life-monitor")

from monitoring import org, setup, utils

_FIRST_YEAR = 2021

import yaml

with open("env-vars.yaml", "r") as stream:
    try:
        env_vars = yaml.safe_load(stream)
        for key, value in env_vars.items():
            os.environ[key] = value
    except yaml.YAMLError as exc:
        print(exc)

weeks_dir = setup.create_and_get_week_dir()
df = org.load_data(week_root=weeks_dir, first_weekday_index=3)
df = org.process_data(df)


from importlib import reload
reload(cal)
reload(setup)
reload(utils)
reload(org)
df.dropna().tail()

messages = org.messages_this_day(df)
print(messages)

df
