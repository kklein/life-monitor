import base64
import datetime
import json
from enum import Enum


class Sport(Enum):
    running = "running"
    cycling = "cycling"
    swimming = "swimming"
    hiking = "hiking"
    cross_country_skiing = "cross-country skiing"
    gym = "gym"
    gym_ub = "gym: ub"
    gym_lb = "gym: lb"
    gym_c = "gym: c"


class TriggerInterval(Enum):
    daily = "daily"
    weekly = "weekly"


def now_timestamp():
    # 'Z' indicates UTC time
    return datetime.datetime.utcnow().isoformat() + "Z"


def first_of_jan_timestamp(year):
    return datetime.datetime(year, 1, 1).isoformat() + "Z"


def parse_payload(request):
    # TODO: Use google cloud logging system instead of prints.
    print(f"Received payload: {request}")
    message = base64.b64decode(request["data"]).decode("utf-8")
    try:
        request_json = json.loads(message)
    except ValueError as e:
        print(f"Error decoding JSON: {e}")
        return "JSON Error", 400
    return request_json.get("kind") or "default"
