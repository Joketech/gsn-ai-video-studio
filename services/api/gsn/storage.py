import os
import boto3
from botocore.config import Config

BUCKET = os.getenv('S3_BUCKET', 'gsn-assets')

def client():
    return boto3.client('s3', endpoint_url=os.getenv('S3_ENDPOINT', 'http://localhost:9000'),
        aws_access_key_id=os.getenv('S3_ACCESS_KEY', 'gsnlocal'),
        aws_secret_access_key=os.getenv('S3_SECRET_KEY', 'local-storage-password'),
        region_name='us-east-1', config=Config(signature_version='s3v4', s3={'addressing_style': 'path'}))

def put(key, data, content_type):
    client().put_object(Bucket=BUCKET, Key=key, Body=data, ContentType=content_type)

def read(key):
    return client().get_object(Bucket=BUCKET, Key=key)['Body'].read()
