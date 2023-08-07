#!/bin/bash

set -e

gcloud functions deploy f_scheduled --entry-point main --runtime python311 --trigger-resource ping_schedule --trigger-event google.pubsub.topic.publish --timeout 540s --region europe-west3 --env-vars-file env-vars.yaml --project stupid-schedule

gcloud scheduler jobs delete pubsub_cal_weekly --location europe-west3 --project stupid-schedule
gcloud scheduler jobs delete pubsub_cal_daily --location europe-west3 --project stupid-schedule
gcloud scheduler jobs delete pubsub_org_weekly --location europe-west3 --project stupid-schedule
gcloud scheduler jobs delete pubsub_org_daily --location europe-west3 --project stupid-schedule

gcloud scheduler jobs create pubsub pubsub_cal_weekly --schedule "10 16 * * SUN" --topic projects/stupid-schedule/topics/ping_schedule --message-body '{"kind": "calendar_weekly"}' --location europe-west3 --project stupid-schedule

gcloud scheduler jobs create pubsub pubsub_cal_daily --schedule "0 19 * * *" --topic projects/stupid-schedule/topics/ping_schedule --message-body '{"kind": "calendar_daily"}' --location europe-west3 --project stupid-schedule

gcloud scheduler jobs create pubsub pubsub_org_weekly --schedule "0 16 * * SUN" --topic projects/stupid-schedule/topics/ping_schedule --message-body '{"kind": "org_weekly"}' --location europe-west3 --project stupid-schedule

gcloud scheduler jobs create pubsub pubsub_org_daily --schedule "0 7 * * *" --topic projects/stupid-schedule/topics/ping_schedule --message-body '{"kind": "org_daily"}' --location europe-west3 --project stupid-schedule

