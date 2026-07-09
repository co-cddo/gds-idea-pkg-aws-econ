"""Shared test configuration and fixtures."""

import os

import awswrangler as wr
import pandas as pd
import pytest
from moto import mock_aws

from aws_econ import AwsEcon
from aws_econ._config import ECON_BUCKET_NAME


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "integration: tests that require external services")


@pytest.fixture(scope="function")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture(scope="function")
def mocked_aws(aws_credentials):
    """
    Mock all AWS interactions as dev account
    Requires you to create your own boto3 clients
    """
    with mock_aws():
        yield


@pytest.fixture()
def create_mock_aws_s3_buckets(mocked_aws):
    aws = AwsEcon()
    aws.s3_client_dev.create_bucket(Bucket=ECON_BUCKET_NAME)
    aws.s3_client_dev.create_bucket(Bucket="dev")

    aws.s3_client_prod.create_bucket(Bucket="prod")


@pytest.fixture(scope="function")
def data_frame():
    df = pd.DataFrame([["a", "b", "c"], ["d", "e", "f"]], index=[0, 1], columns=["c1", "c2", "c3"])
    return df


@pytest.fixture()
def create_mock_aws_s3_objects(data_frame, create_mock_aws_s3_buckets):
    aws = AwsEcon()

    df = data_frame

    wr.s3.to_csv(df, f"s3://{ECON_BUCKET_NAME}/csv/csv.csv", boto3_session=aws.dev_session, index=False)
    wr.s3.to_csv(df, "s3://dev/csv.csv", boto3_session=aws.dev_session, index=False)

    wr.s3.to_json(df, "s3://prod/json.json", boto3_session=aws.prod_session, index=False)
