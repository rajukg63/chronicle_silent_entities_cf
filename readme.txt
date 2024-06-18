####commands to execute on your cloudtop to setup your cloud function and cloud scheduler, default runs every 10 minutes
####pre-requisites
#### 1. onelogin creds will need to be stored in a json format with keys as "CLIENT_ID" and "CLIENT_SECRET"
#### 2. set your TLA, REGION, TIME_ZONE, TIME_INTERVAL and FUNCTION_REGION
#### REGION is the Chronicle region, US leave blank, EUROPE or ASIA-SOUTHEAST1
gcloud auth login
####define your variables
####find your timezone timedatectl list-timezones - https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
TLA="<TLA>"
TIME_ZONE="Australia/Sydney"
INGESTION_API="ingestion_api.txt"
ONELOGIN_CREDS="onelogin_creds.json"
TIME_INTERVAL="10"
REGION=""
FUNCTION_REGION="us-central1"
####go to designated project
PROJECT_NAME="malachite-$TLA"
gcloud config set project $PROJECT_NAME
####enable cloud functions api, cloud scheduler api, cloud build api and secrets manager api
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable secretmanager.googleapis.com
####define more variables 
SERVICE_ACCOUNT_ID="$(echo $PROJECT_NAME | cut -d "-" -f2)"
SERVICE_ACCOUNT_NAME="$SERVICE_ACCOUNT_ID-cloudfunction"
DESCRIPTION="Service account created by $(whoami)."
DISPLAY_NAME="$SERVICE_ACCOUNT_NAME service account, created by $(whoami)"
####create service account, can be skipped if already exists
gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME --description="$DESCRIPTION" --display-name="$DISPLAY_NAME"
####Grant the service account cloud functions invoker and cloud scheduler service agent roles
gcloud projects add-iam-policy-binding $PROJECT_NAME --member="serviceAccount:$SERVICE_ACCOUNT_NAME@$PROJECT_NAME.iam.gserviceaccount.com" --role="roles/cloudfunctions.invoker"
gcloud projects add-iam-policy-binding $PROJECT_NAME --member="serviceAccount:$SERVICE_ACCOUNT_NAME@$PROJECT_NAME.iam.gserviceaccount.com" --role="roles/cloudscheduler.serviceAgent"
gcloud projects add-iam-policy-binding $PROJECT_NAME --member="serviceAccount:$SERVICE_ACCOUNT_NAME@$PROJECT_NAME.iam.gserviceaccount.com" --role="roles/secretmanager.secretAccessor"
####store secrets
####create your secrets/ingestion api keys
####ingestion api can be skipped if already exists in secrets manager
gcloud secrets create "ingestion_api" --replication-policy "automatic" --data-file=$INGESTION_API
gcloud secrets create "onelogin_creds" --replication-policy "automatic" --data-file=$ONELOGIN_CREDS
####download package
git clone -b onelogin_sso_CF sso://user/lunga/cloud-gophers onelogin_sso_CF
####define CF variables and create CF, if prompted, enter "n" if asked to allow unauthenticated invocations
FUNCTION_NAME="chronicle-onelogin-sso-cloud-gopher-$TLA"
SERVICE_ACCOUNT="$SERVICE_ACCOUNT_NAME@$PROJECT_NAME.iam.gserviceaccount.com"
gcloud beta functions deploy $FUNCTION_NAME --region=$FUNCTION_REGION --runtime=python39 --security-level=secure-always --trigger-http --service-account=$SERVICE_ACCOUNT --set-env-vars=FUNCTION_MINUTE_INTERVAL=$TIME_INTERVAL,REGION=$REGION --entry-point=main --source=onelogin_sso_CF --set-secrets "CHRONICLE_INGESTION_API_KEY=ingestion_api:latest,ONELOGIN_API_DETAILS=onelogin_creds:latest" --timeout=540s
####define schedule variables
HTTP_JOB="onelogin-sso-schedule-cloud-function"
SCHEDULE="*/10 * * * *"
URI="https://$FUNCTION_REGION-$PROJECT_NAME.cloudfunctions.net/$FUNCTION_NAME"
####if this command comes back with error then run second command to create app engine
gcloud app describe
gcloud app create --region=us-central
####create cloud scheduler schedule
gcloud scheduler jobs create http $HTTP_JOB --schedule="$SCHEDULE" --uri=$URI --http-method=POST --oidc-service-account-email=$SERVICE_ACCOUNT --oidc-token-audience=$URI --headers User-Agent=Google-Cloud-Scheduler --time-zone=$TIME_ZONE
