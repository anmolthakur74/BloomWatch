import os
import json
import ee

def initialize_ee():
    """
    Initialize Google Earth Engine using service account credentials.
    Reads JSON key from environment variable GEE_SERVICE_ACCOUNT_JSON
    """
    if ee.data._initialized:
        return

    service_account_json = os.getenv("GEE_SERVICE_ACCOUNT_JSON")
    if not service_account_json:
        raise RuntimeError("Environment variable GEE_SERVICE_ACCOUNT_JSON not set.")

    try:
        credentials_dict = json.loads(service_account_json)
    except json.JSONDecodeError:
        raise RuntimeError("Invalid JSON in GEE_SERVICE_ACCOUNT_JSON")

    credentials = ee.ServiceAccountCredentials(
        credentials_dict.get("client_email"),
        key_file=None,
        private_key=credentials_dict.get("private_key")
    )
    ee.Initialize(credentials)
