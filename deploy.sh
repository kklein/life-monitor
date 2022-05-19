gcloud functions deploy f_scheduled --entry-point main --runtime python39 --trigger-resource ping_schedule --trigger-event google.pubsub.topic.publish --timeout 540s --region europe-west3 --env-vars-file env-vars.yaml

gcloud scheduler jobs delete pubsub_cal_weekly --location europe-west3
gcloud scheduler jobs delete pubsub_cal_daily --location europe-west3
gcloud scheduler jobs delete pubsub_org --location europe-west3

gcloud scheduler jobs create pubsub pubsub_cal_weekly --schedule "10 16 * * SUN" --topic ping_schedule --message-body '{"kind": "calendar_weekly"}' --location europe-west3

gcloud scheduler jobs create pubsub pubsub_cal_daily --schedule "0 19 * * *" --topic ping_schedule --message-body '{"kind": "calendar"}' --location europe-west3

gcloud scheduler jobs create pubsub pubsub_org --schedule "0 16 * * SUN" --topic ping_schedule --message-body '{"kind": "org"}' --location europe-west3

