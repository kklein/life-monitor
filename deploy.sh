#!/bin/bash

set -e

LOCATION="europe-west3"
PROJECT_NAME="stupid-schedule"
TOPIC="projects/stupid-schedule/topics/ping_schedule"

# Deploy function.

gcloud functions deploy f_scheduled \
       --gen2 \
       --entry-point main \
       --runtime python311 \
       --trigger-resource ping_schedule \
       --trigger-event google.pubsub.topic.publish \
       --timeout 540s \
       --region europe-west3 \
       --env-vars-file env-vars.yaml \
       --project stupid-schedule

# Remove existing triggers.

gcloud scheduler jobs delete pubsub_cal_weekly \
       --location "$LOCATION" \
       --project "$PROJECT_NAME"

gcloud scheduler jobs delete pubsub_cal_daily \
       --location "$LOCATION" \
       --project "$PROJECT_NAME"

gcloud scheduler jobs delete pubsub_org_weekly \
       --location "$LOCATION" \
       --project "$PROJECT_NAME"

gcloud scheduler jobs delete pubsub_org_daily \
       --location "$LOCATION" \
       --project "$PROJECT_NAME"

# Create new triggers.

gcloud scheduler jobs create pubsub pubsub_cal_weekly \
       --schedule "10 16 * * SUN" \
       --topic "$TOPIC" \
       --message-body '{"kind": "calendar_weekly"}' \
       --location "$LOCATION" \
       --project "$PROJECT_NAME"

gcloud scheduler jobs create pubsub pubsub_cal_daily \
       --schedule "0 19 * * *" \
       --topic "$TOPIC" \
       --message-body '{"kind": "calendar_daily"}' \
       --location "$LOCATION" \
       --project "$PROJECT_NAME"

gcloud scheduler jobs create pubsub pubsub_org_weekly \
       --schedule "0 16 * * SUN" \
       --topic "$TOPIC" \
       --message-body '{"kind": "org_weekly"}' \
       --location "$LOCATION" \
       --project "$PROJECT_NAME"

gcloud scheduler jobs create pubsub pubsub_org_daily \
       --schedule "0 7 * * *" \
       --topic "$TOPIC" \
       --message-body '{"kind": "org_daily"}' \
       --location "$LOCATION" \
       --project "$PROJECT_NAME"

