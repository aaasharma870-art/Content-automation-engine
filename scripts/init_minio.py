import boto3
from botocore.client import Config
import os

AWS_ACCESS_KEY_ID = "minioadmin"
AWS_SECRET_ACCESS_KEY = "minioadmin"
ENDPOINT_URL = "http://localhost:9000"
BUCKET_NAME = "aibrain-assets"

s3 = boto3.client('s3',
                  endpoint_url=ENDPOINT_URL,
                  aws_access_key_id=AWS_ACCESS_KEY_ID,
                  aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                  config=Config(signature_version='s3v4'),
                  region_name='us-east-1')

try:
    s3.create_bucket(Bucket=BUCKET_NAME)
    print(f"Bucket '{BUCKET_NAME}' created successfully.")
except Exception as e:
    print(f"Error creating bucket: {e}")
    # Check if bucket exists
    try:
        s3.head_bucket(Bucket=BUCKET_NAME)
        print(f"Bucket '{BUCKET_NAME}' already exists.")
    except:
        pass
