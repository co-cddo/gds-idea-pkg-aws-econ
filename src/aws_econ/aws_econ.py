"""Core calculator implementation."""

import io
import json
import logging

import awswrangler as wr
import boto3
import pandas as pd

from aws_econ._athena_io_handler import _get_query_results, _has_query_succeeded, _start_query
from aws_econ._config import ECON_BUCKET_NAME, PROD_ROLE_ARN_TO_ASSUME, S3_TABLES_CATALOGUE
from aws_econ._s3_io_handler import _list_files, _list_folders, _list_objects

logger = logging.getLogger(__name__)


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

    def list(self, folder: str = None, bucket: str = ECON_BUCKET_NAME) -> dict:
        """List available buckets or files in dev or prod environments"""

        folder = "" if folder is None else folder
        client = self.s3_client_dev if bucket in self.buckets_dev else self.s3_client_prod
        return_dict = {}
        contents_prefixes, contents = _list_objects(client, bucket, folder)
        return_dict["directories"] = _list_folders(folder, contents_prefixes)
        return_dict["files"] = _list_files(folder, contents)

        return return_dict

    def read(self, file: str, bucket: str = ECON_BUCKET_NAME, buffer=False) -> pd.DataFrame | io.BytesIO:
        """Read file from S3 bucket"""

        session = self.dev_session if bucket in self.buckets_dev else self.prod_session
        file_type = file.rsplit(".", 1)[-1].lower()

        if file_type == "csv":
            file = wr.s3.read_csv(f"s3://{bucket}/{file}", boto3_session=session)
        elif file_type in ["parquet", "pq"]:
            file = wr.s3.read_parquet(f"s3://{bucket}/{file}", boto3_session=session)
        else:
            with io.BytesIO() as data:
                wr.s3.download(path=f"s3://{bucket}/{file}", local_file=data, boto3_session=session)
                data.seek(0)
                file = data.read()
            file = io.BytesIO(file) if buffer else file

        return file

    def write(self, file: str, df: pd.DataFrame) -> None:
        """Return the sum of a and b."""

        session = self.dev_session
        file_type = file.rsplit(".", 1)[-1].lower()

        if file_type == "csv":
            file = wr.s3.to_csv(df, f"s3://{ECON_BUCKET_NAME}/{file}", boto3_session=session)
        elif file_type in ["parquet", "pq"]:
            file = wr.s3.to_parquet(df, f"s3://{ECON_BUCKET_NAME}/{file}", boto3_session=session)
        else:
            raise ValueError("file extension is not supported")

    def download(
        self,
        file: str,
        local_file: str,
        bucket: str = ECON_BUCKET_NAME,
    ) -> None:
        """Return the sum of a and b."""

        session = self.dev_session if bucket in self.buckets_dev else self.prod_session

        wr.s3.download(path=f"s3://{bucket}/{file}", local_file=local_file, boto3_session=session)

    def upload(self, file: str, local_file: str) -> None:
        """Return the sum of a and b."""

        session = self.dev_session

        wr.s3.upload(path=f"s3://{ECON_BUCKET_NAME}/{file}", local_file=local_file, boto3_session=session)

    def query(self, sql_query: str, database: str = "default", s3tables=False):
        athena_client = self.athena_client_prod

        query_start_response = _start_query(
            athena_client, sql_query, database, S3_TABLES_CATALOGUE if s3tables else None
        )

        try:
            _has_query_succeeded(athena_client=athena_client, execution_id=query_start_response["QueryExecutionId"])
        except Exception as e:
            error_message = json.loads(str(e))
            raise Exception(
                json.dumps(
                    {
                        "QueryExecutionId": error_message["QueryExecution"]["QueryExecutionId"],
                        "ErrorMessage": error_message["QueryExecution"]["Status"]["AthenaError"]["ErrorMessage"],
                    },
                    default=str,
                )
            ) from e

        data = _get_query_results(
            athena_client=athena_client,
            execution_id=query_start_response["QueryExecutionId"],
        )

        df = pd.DataFrame(data=data[1:], columns=data[0])

        return df
