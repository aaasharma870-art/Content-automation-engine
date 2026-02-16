import boto3
from botocore.client import Config
import os

AWS_ACCESS_KEY_ID = "minioadmin"
AWS_SECRET_ACCESS_KEY = "minioadmin"
ENDPOINT_URL = "http://localhost:9000"
BUCKET_NAME = "aibrain-assets"

# The key from the previous successful run
# Video URL: http://minio:9000/aibrain-assets/renders/test-cinema-1770768226/output.mp4
OBJECT_KEY = "renders/test-cinema-1770768226/output.mp4"
LOCAL_FILENAME = "cinema_final.mp4"

s3 = boto3.client('s3',
                  endpoint_url=ENDPOINT_URL,
                  aws_access_key_id=AWS_ACCESS_KEY_ID,
                  aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                  config=Config(signature_version='s3v4'),
                  region_name='us-east-1')

try:
    print(f"Downloading {OBJECT_KEY} to {LOCAL_FILENAME}...")
    s3.download_file(BUCKET_NAME, OBJECT_KEY, LOCAL_FILENAME)
    print(f"Successfully downloaded to {os.path.abspath(LOCAL_FILENAME)}")
except Exception as e:
    print(f"Error downloading file: {e}")
