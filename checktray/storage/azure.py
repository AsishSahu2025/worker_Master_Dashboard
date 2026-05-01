# from azure.storage.blob import (
#     BlobServiceClient,
#     generate_blob_sas,
#     BlobSasPermissions)

# from datetime import datetime, timedelta
# from django.conf import settings

# def generate_upload_sas(logical_path: str, expires_in_minutes=5):
#     """
#     Generates an upload-only SAS URL for a blob.
#     """

#     sas_token = generate_blob_sas(
#         account_name=settings.AZURE_STORAGE_ACCOUNT_NAME,
#         container_name=settings.AZURE_STORAGE_CONTAINER,
#         blob_name=logical_path,
#         account_key=settings.AZURE_STORAGE_ACCOUNT_KEY,
#         permission=BlobSasPermissions(write=True, create=True),
#         expiry=datetime.utcnow() + timedelta(minutes=expires_in_minutes),
#         version="2020-10-02",
#         protocol="https",
#         resource="b",

#     )

#     upload_url = (
#         f"https://{settings.AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net/"
#         f"{settings.AZURE_STORAGE_CONTAINER}/{logical_path}?{sas_token}"
#     )

#     return upload_url

# def generate_read_sas(logical_path: str, expires_in_minutes=10):
#     sas_token = generate_blob_sas(
#         account_name=settings.AZURE_STORAGE_ACCOUNT_NAME,
#         container_name=settings.AZURE_STORAGE_CONTAINER,
#         blob_name=logical_path,
#         account_key=settings.AZURE_STORAGE_ACCOUNT_KEY,
#         permission=BlobSasPermissions(read=True),
#         expiry=datetime.utcnow() + timedelta(minutes=120),
#         version="2020-10-02",
#         protocol="https",
#         resource="b",
#     )

#     return (
#         f"https://{settings.AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net/"
#         f"{settings.AZURE_STORAGE_CONTAINER}/{logical_path}?{sas_token}"
#     )


from minio import Minio
from datetime import timedelta
from django.conf import settings

client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=True  # True if HTTPS
)

BUCKET_NAME = "checktray-storage"


def generate_upload_url(object_name, expires_in_minutes=5):
    url = client.presigned_put_object(
        BUCKET_NAME,
        object_name,
        expires=timedelta(minutes=expires_in_minutes)
    )
    print(url)
    return url


def generate_read_url(object_name, expires_in_minutes=10):
    url = client.presigned_get_object(
        BUCKET_NAME,
        object_name,
        expires=timedelta(minutes=expires_in_minutes)
    )
    print(url)
    return url

