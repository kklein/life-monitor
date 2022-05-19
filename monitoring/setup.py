import os
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from telegram import Bot


def get_telegram_owner_id():
    return os.environ["telegram_owner_id"]


def get_bot():
    token = os.environ["telegram_token"]
    return Bot(token=token)


def _get_calendar_credentials():
    return Credentials(
        "access_token",
        refresh_token=os.environ["google_refresh_token"],
        token_uri=os.environ["google_token_uri"],
        client_id=os.environ["google_client_id"],
        client_secret=os.environ["google_client_secret"],
    )


def get_calendar_service():
    try:
        service = build("calendar", "v3", credentials=_get_calendar_credentials())
    except HttpError as error:
        print("An error occurred: %s" % error)
    return service


def get_tmpdir():
    return Path(tempfile.gettempdir())


def create_and_get_week_dir() -> Path:
    dropbox_url = os.environ["dropbox_url"]

    tmpdir = get_tmpdir()
    zip_path = tmpdir / "org.zip"
    urllib.request.urlretrieve(dropbox_url, zip_path)

    weeks_dir = tmpdir / "weeks"

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(weeks_dir)

    return weeks_dir
