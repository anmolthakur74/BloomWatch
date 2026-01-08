import os
import json
import ee
from google.oauth2 import service_account

def initialize_ee():
    """
    Initialize Google Earth Engine with service account credentials
    stored in the environment variable GEE_SERVICE_ACCOUNT_JSON
    """
    try:
        gee_json_str = os.environ.get("GEE_SERVICE_ACCOUNT_JSON")
        if not gee_json_str:
            raise RuntimeError("GEE_SERVICE_ACCOUNT_JSON not found in environment variables")
        
        # Convert JSON string to dictionary
        gee_info = json.loads(gee_json_str)
        
        # Create credentials and initialize Earth Engine
        credentials = service_account.Credentials.from_service_account_info(gee_info)
        ee.Initialize(credentials)
        print("Earth Engine initialized successfully")
    except Exception as e:
        print("Failed to initialize Earth Engine:", e)
        raise
