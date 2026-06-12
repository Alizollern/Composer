"""
S3-совместимое хранилище (прод): AWS S3, MinIO, Yandex Object Storage и т.п.

boto3 импортируется лениво — офлайн-разработка и тесты на LocalStorage не должны
требовать установленного boto3. Конфиг (endpoint, bucket, ключи) приходит из
product.config.
"""

from __future__ import annotations

from product.storage.base import Storage


class S3Storage(Storage):
    def __init__(self, *, endpoint: str, bucket: str,
                 access_key: str, secret_key: str, region: str = "us-east-1"):
        import boto3  # лениво: нужен только в проде

        self.bucket = bucket
        self._s3 = boto3.client(
            "s3",
            endpoint_url=endpoint or None,
            aws_access_key_id=access_key or None,
            aws_secret_access_key=secret_key or None,
            region_name=region or None,
        )

    def put(self, key: str, data: bytes,
            *, content_type: str = "application/octet-stream") -> str:
        self._s3.put_object(
            Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)
        return key

    def get(self, key: str) -> bytes:
        from botocore.exceptions import ClientError
        try:
            resp = self._s3.get_object(Bucket=self.bucket, Key=key)
        except ClientError as e:
            raise KeyError(key) from e
        return resp["Body"].read()

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError
        try:
            self._s3.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return False
