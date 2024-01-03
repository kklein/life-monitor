import io
import os
import tempfile
import zipfile
from pathlib import Path

import requests
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


def create_and_get_week_dir(week: str = "23-weeks") -> Path:
    username = os.environ["github_username"]
    repo = os.environ["github_repo"]
    ref = os.environ["github_ref"]
    pat = os.environ["github_pat"]

    url = f"https://api.github.com/repos/{username}/{repo}/zipball/{ref}"

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {pat}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    response = requests.get(url, headers=headers)

    tmpdir = get_tmpdir() / "org"
    tmpdir.mkdir(exist_ok=True)

    z = zipfile.ZipFile(io.BytesIO(response.content))
    z.extractall(tmpdir)

    weeks_dir = tmpdir / z.filelist[0].filename / week
    return weeks_dir
