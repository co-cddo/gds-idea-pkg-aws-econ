"""Core calculator implementation."""

import awswrangler as wr
import boto3

from aws_econ._config import PROD_ROLE_ARN_TO_ASSUME
from aws_econ._s3_io_handler import _list_files, _list_folders, _list_objects


class AwsEcon:
    """AWS access for econ team.

    Provides methods for standard S3 and Athena operations and automatically manages dev and prod access.
    """

    def __init__(self):
        sts_client = boto3.client("sts")
        profile_name = sts_client.get_caller_identity()["Arn"].split("/")[1]
        assumed_role_object = sts_client.assume_role(RoleArn=PROD_ROLE_ARN_TO_ASSUME, RoleSessionName=profile_name)
        credentials = assumed_role_object["Credentials"]
        self.dev_session = boto3.session.Session()
        self.prod_session = boto3.session.Session(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
        )
        self.s3_client_dev = self.dev_session.client("s3")
        self.s3_client_prod = self.prod_session.client("s3")
        self.athena_client_dev = self.dev_session.client("athena")
        self.athena_client_prod = self.prod_session.client("athena")

        self.buckets_dev = wr.s3.list_buckets(boto3_session=self.dev_session)
        self.buckets_prod = wr.s3.list_buckets(boto3_session=self.prod_session)

    def list(self, bucket: str = None, folder: str = None) -> dict:
        """List available buckets or files in dev or prod environments"""

        if bucket is None and folder is not None:
            raise ValueError("bucket cannot be None if key is given")
        elif bucket is None and folder is None:
            return_dict = {}
            return_dict["dev"] = self.buckets_dev
            return_dict["prod"] = self.buckets_prod
        else:
            folder = "" if folder is None else folder
            client = self.s3_client_dev if bucket in self.buckets_dev else self.s3_client_prod
            return_dict = {}
            contents_prefixes, contents = _list_objects(client, bucket, folder)
            return_dict["directories"] = _list_folders(folder, contents_prefixes)
            return_dict["files"] = _list_files(folder, contents)

        return return_dict

    def read(self, bucket: str = None, key: str = None) -> float:
        """Return the sum of a and b."""
        return

    def write(self, bucket: str = None, key: str = None, file_name: str = None) -> float:
        """Return the sum of a and b."""
        return

    def query(self, a: float, b: float) -> float:
        """Return the sum of a and b."""
        return a + b
