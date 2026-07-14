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

    Class sets up following attributes:
    - dev_session - boto3 session for dev AWS account
    - prod_session - boto3 session for prod AWS account
    - s3_client_dev - boto3 S3 client for dev AWS account
    - s3_client_prod - boto3 S3 client for prod AWS account
    - athena_client_dev - boto3 Athena client for dev AWS account
    - athena_client_prod - boto3 Athena client for prod AWS account
    - buckets_dev - S3 buckets in dev AWS account
    - buckets_prod - S3 buckets in prod AWS account

    Class sets up following functions:
    - list - list bucket and folder objects
    - read - read file from S3 and return as DataFrame if possible
    - write - write dataframe to S3 econ bucket
    - download - download S3 file to local space
    - upload - upload local file to S3 econ bucket
    - delete - delete file from S3 econ bucket
    - rename - rename file in S3 econ bucket
    - query - query Athena tables

    Examples
    --------
    Initialize object.

    >>> from aws_econ import aws_econ
    >>> aws = AwsEcon()


    List files and directories in a bucket.

    >>> result = aws.list("data", "bucket")
    >>> result
    {"directories": [], "files": ["csv.csv"]}

    Notice that both arguments folder and bucket are optional.
    If folder is not given, top bucket folder will be listed.
    If bucket is not given, default econ bucket will be listed.


    Read file from S3.
    >>> df = aws.read("project1/data.csv", "bucket")
    >>> df
        0   1
    0   3   4
    1   5   6

    Notice that second argument bucket is optional.
    If bucket is not given, default econ bucket will be used.
    If possible data you read will be returned as DataFrame.


    Write file to S3.
    >>> df = pd.DataFrame([[1,2],[3,4]])
    >>> df = aws.write("save/data.parquet", df)

    Notice that function can only saves DataFrames to econ bucket.


    Download file from S3 to local space.
    >>> aws.download("project1/data.csv", "./data.csv", "bucket")

    Notice that first argument is source location in S3,
    second argument target in local space,
    third argument bucket is optional.
    If bucket is not given, default econ bucket will be used.


    Upload file to S3 econ bucket from local space.
    >>> aws.upload("project1/data.csv", "./data1.csv")

    Notice that first argument is target location in S3,
    second argument is source in local space.


    Delete file from S3 econ bucket.
    >>> aws.delete("project1/data.csv")


    Rename or relocate file in S3 econ bucket.
    >>> aws.rename("project1/data.csv", "archive/project1/old_data.csv", keep_current=True)

    Notice that first argument is source location in S3,
    second argument is target in S3.
    third argument keep_current is optional, default value False will delete source file.


    Query data from Athena.
    >>> df = aws.query("SELECT * FROM table", database="database_project1", s3tables=True)
    >>> df
        0   1
    0   3   4
    1   5   6

    Notice that first argument is SQL query,
    second argument database is optional, deafult value is default.
    third argument s3tables is optional, default value False will read data from S3 data catalogue,
    True will read data from S3Tables data catalogue.

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
        """
        List available folders or files in dev or prod environments

        Args:
            folder: folder to list data from
            bucket: bucket to list data from

        Returns:
            Dictionary with folders and files available
        """

        folder = "" if folder is None else folder
        client = self.s3_client_dev if bucket in self.buckets_dev else self.s3_client_prod
        return_dict = {}
        contents_prefixes, contents = _list_objects(client, bucket, folder)
        return_dict["directories"] = _list_folders(folder, contents_prefixes)
        return_dict["files"] = _list_files(folder, contents)

        return return_dict

    def read(self, file: str, bucket: str = ECON_BUCKET_NAME, buffer=False) -> pd.DataFrame | io.BytesIO | bytes:
        """
        Read file from S3 bucket. CSV and PARQUET files are returnet as pandas dataframes,
        remaining files as bytes or bytes stream.

        Args:
            file: file to read
            bucket: bucket to read data from
            buffer: whether to return data as buffer, only applicable if file is not csv or parquet

        Returns:
            pandas Dataframe, io Bytes stream or bytes
        """

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
        """
        Write file to S3 econ bucket

        Args:
            file: file to read
            df: pandas dataframe
        """

        session = self.dev_session
        file_type = file.rsplit(".", 1)[-1].lower()

        if file_type == "csv":
            file = wr.s3.to_csv(df, f"s3://{ECON_BUCKET_NAME}/{file}", boto3_session=session, index=False)
        elif file_type in ["parquet", "pq"]:
            file = wr.s3.to_parquet(df, f"s3://{ECON_BUCKET_NAME}/{file}", boto3_session=session, index=False)
        else:
            raise ValueError("file extension is not supported")

    def download(
        self,
        file: str,
        local_file: str,
        bucket: str = ECON_BUCKET_NAME,
    ) -> None:
        """
        Download file from S3 bucket to local space

        Args:
            file: file to read
            local_file: local path to save file to
            bucket: S3 bucket to read file from
        """

        session = self.dev_session if bucket in self.buckets_dev else self.prod_session

        wr.s3.download(path=f"s3://{bucket}/{file}", local_file=local_file, boto3_session=session)

    def upload(self, file: str, local_file: str) -> None:
        """
        Upload file from local space to S3 econ bucket

        Args:
            file: file to read
            local_file: local path to save file to
        """

        session = self.dev_session

        wr.s3.upload(path=f"s3://{ECON_BUCKET_NAME}/{file}", local_file=local_file, boto3_session=session)

    def delete(self, file: str) -> None:
        """
        Delete file from S3 econ bucket

        Args:
            file: file to delete
        """

        session = self.dev_session

        wr.s3.delete_objects([f"s3://{ECON_BUCKET_NAME}/{file}"], boto3_session=session)

    def rename(self, file_source: str, file_target: str, keep_current: bool = None):
        """
        Rename or relocate file in S3 econ bucket

        Args:
            file_source: current file name and location
            file_target: new file name and location
            keep_current: keep current file after renaming
        """
        keep_current = False if keep_current is None else keep_current

        session = self.dev_session

        current_file_path, current_file_name = file_source.rsplit("/", 1)
        new_file_path, new_file_name = file_target.rsplit("/", 1)
        wr.s3.copy_objects(
            paths=[f"s3://{ECON_BUCKET_NAME}/{file_source}"],
            source_path=f"s3://{ECON_BUCKET_NAME}/{current_file_path}",
            target_path=f"s3://{ECON_BUCKET_NAME}/{new_file_path}",
            replace_filenames={current_file_name: new_file_name},
            boto3_session=session,
        )

        if not keep_current:
            self.delete(file_source)

    def query(self, sql_query: str, database: str = "default", s3tables=False) -> pd.DataFrame:
        """
        Execute SQL query and return data as dataframe

        Args:
            sql_query: SQL query to execute
            database: databaase name to execute query on
            s3tables: whether queried table is S3Table

        Returns:
            pandas Dataframe
        """

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

        if len(data) > 0:
            df = pd.DataFrame(data=data[1:], columns=data[0])
        else:
            df = pd.DataFrame()

        return df
