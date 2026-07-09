import io

import pandas as pd

from aws_econ import AwsEcon
from aws_econ._config import ECON_BUCKET_NAME


def test_s3_buckets_correct_account(create_mock_aws_s3_buckets):
    aws = AwsEcon()

    assert aws.buckets_dev == [ECON_BUCKET_NAME, "dev"]

    assert aws.buckets_prod == ["prod"]


def test_s3_list_buckets_objects(create_mock_aws_s3_objects):
    aws = AwsEcon()

    assert aws.list() == {"directories": ["csv"], "files": []}

    assert aws.list("", "dev") == {"directories": [], "files": ["csv.csv"]}

    assert aws.list("", "prod") == {"directories": [], "files": ["json.json"]}


def test_s3_read_buckets_objects(data_frame, create_mock_aws_s3_objects):
    aws = AwsEcon()

    df = data_frame

    pd.testing.assert_frame_equal(df, aws.read("csv/csv.csv"), check_dtype=False)

    pd.testing.assert_frame_equal(df, aws.read("csv.csv", "dev"), check_dtype=False)

    buffer = io.BytesIO()
    df.to_json(buffer)
    buffer.seek(0)
    assert buffer.read() == aws.read("json.json", "prod")
