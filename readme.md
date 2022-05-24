This is a project aiming to provide me with notifications about aspects of my life which might otherwise go unnoticed.

I wrote more about this [here](https://kevinkle.in/posts/2022-05-21-life_monitor/).

Currently, two data sources are used:
- Google Calendar API for sports events
- Dropbox for [org files](https://github.com/kklein/org-journal)

This project is hosted on Google Cloud Platform and relies on scheduled cron jobs.

If something appears to be noteworthy, messages are sent via a Telegram bot.

This project assumes an `env-vars.yaml` with the following structure:

```
telegram_token: YOURTOKEN
telegram_owner_id: YOURTOKEN

dropbox_url: https://www.dropbox.com/sh/YOURFOLDER?raw=1

google_refresh_token: YOURREFRESHTOKEN
google_token_uri: https://oauth2.googleapis.com/token
google_client_id: YOURCLIENTID
google_client_secret: YOURCLIENTSECRET
```

