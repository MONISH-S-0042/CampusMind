import os
import boto3
from dotenv import load_dotenv

load_dotenv()

r2_client = boto3.client(
    "s3",
    endpoint_url=f"{os.getenv('R2_ENDPOINT')}",
    aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
    region_name="auto",
)

BUCKET_NAME = os.getenv("R2_BUCKET_NAME")