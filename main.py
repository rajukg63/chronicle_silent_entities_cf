import os
import json
from google.oauth2 import service_account 
from google.cloud import secretmanager
from google.cloud import bigquery
from urllib.parse import urlencode
import datetime

SCOPES = ['https://www.googleapis.com/auth/cloud-platform']
VERBOSE = False

def debug(data):
    if VERBOSE:
        print(data)


def get_credential_from_the_secret_manager ():
    client = secretmanager.SecretManagerServiceClient()
    secret_name = os.environ["SECRET_NAME"]
    project_id = os.environ["SECRET_PROJECT_NAME"]
    request = {"name": f"projects/{project_id}/secrets/{secret_name}/versions/latest"}
    response = client.access_secret_version(request)
    
    secret_string = response.payload.data.decode("UTF-8")
    service_account_info = json.loads(secret_string)
    return (service_account_info)

def get_authorized_session (service_account_info):   
    CREDENTIALS = service_account.Credentials.from_service_account_info(service_account_info,scopes=SCOPES)
    project_id = os.environ["BQ_PROJECT_NAME"]
    client = bigquery.Client(credentials=CREDENTIALS, project=project_id)
    return (client)

def bigquery_query(client):
    """Cloud Function to execute a BigQuery query using a service account.

    Returns:
        The query results as a JSON-formatted string or an error message.
    """

    try:
        
        query = "SELECT principal.hostname as gateway, MAX(metadata.event_timestamp.seconds) as maxtime, count(*) \
            FROM `datalake.events` as events \
            WHERE DATE(hour_time_bucket) > DATE_SUB(CURRENT_DATE(), INTERVAL 3 DAY) \
            group by 1 \
            having count(*) > 10 \
            and (unix_seconds(current_timestamp()) - maxtime ) > 60*60 \
            ORDER BY gateway \
            LIMIT 100"

        # Execute the query
        query_job = client.query(query)
        results = query_job.result()

        # Convert results to a list of dictionaries for JSON serialization
        rows = [dict(row) for row in results]

        # Return the results as a JSON response
        return json.dumps(rows), 200
    except KeyError:
        return json.dumps({"error": "Missing 'query' parameter in request"}), 400
    except Exception as e:
        # Log the error for debugging
        print(f"Error executing BigQuery query: {e}")
        # Return an error response to the client
        return json.dumps({"error": "Internal error executing BigQuery query"}), 500

def main(request):
    
    service_account_info=get_credential_from_the_secret_manager()
    debug({"service_account_info":service_account_info})
    client=get_authorized_session(service_account_info)
  
    return(bigquery_query(client))
