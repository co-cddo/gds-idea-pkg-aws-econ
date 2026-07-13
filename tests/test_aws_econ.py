import io
import os

import awswrangler as wr
import pandas as pd

from aws_econ import AwsEcon
from aws_econ._config import ECON_BUCKET_NAME


def test___init__(create_mock_aws_s3_buckets):
    aws = AwsEcon()

    assert aws.buckets_dev == [ECON_BUCKET_NAME, "dev"]

    assert aws.buckets_prod == ["prod"]


def test_list(create_mock_aws_s3_objects):
    aws = AwsEcon()

    assert aws.list() == {"directories": ["csv"], "files": []}

    assert aws.list("", "dev") == {"directories": [], "files": ["csv.csv"]}

    assert aws.list("", "prod") == {"directories": [], "files": ["json.json"]}


def test_read(data_frame, create_mock_aws_s3_objects):
    aws = AwsEcon()

    df = data_frame

    pd.testing.assert_frame_equal(df, aws.read("csv/csv.csv"), check_dtype=False)

    pd.testing.assert_frame_equal(df, aws.read("csv.csv", "dev"), check_dtype=False)

    buffer = io.BytesIO()
    df.to_json(buffer)
    buffer.seek(0)
    assert buffer.read() == aws.read("json.json", "prod")


def test_write(data_frame, create_mock_aws_s3_objects):
    aws = AwsEcon()

    df = data_frame

    aws.write("file.csv", df)

    pd.testing.assert_frame_equal(
        df, wr.s3.read_csv(f"s3://{ECON_BUCKET_NAME}/file.csv", boto3_session=aws.dev_session), check_dtype=False
    )


def test_download(tmp_path, create_mock_aws_s3_objects):
    aws = AwsEcon()

    d = tmp_path / "sub"
    d.mkdir()
    p = d / "file.csv"

    aws.download("json.json", str(p), "prod")

    assert ["file.csv"] == os.listdir(d)


def test_upload(tmp_path, create_mock_aws_s3_objects):
    aws = AwsEcon()

    d = tmp_path / "sub"
    d.mkdir()
    p = d / "file.txt"
    p.write_text("Example Text")

    aws.upload("upload/json.json", str(p))

    assert [f"s3://{ECON_BUCKET_NAME}/upload/json.json"] == wr.s3.list_objects(f"s3://{ECON_BUCKET_NAME}/upload/")


def test_delete(create_mock_aws_s3_objects):
    aws = AwsEcon()

    aws.delete("csv/")

    assert 1 == len(wr.s3.list_objects(f"s3://{ECON_BUCKET_NAME}/csv/"))

    aws.delete("csv/csv.csv")

    assert 0 == len(wr.s3.list_objects(f"s3://{ECON_BUCKET_NAME}/csv/"))


def test_rename(create_mock_aws_s3_objects):
    aws = AwsEcon()

    aws.rename("csv/csv.csv", "copy/keep.csv", keep_current=True)

    assert [f"s3://{ECON_BUCKET_NAME}/csv/csv.csv"] == wr.s3.list_objects(f"s3://{ECON_BUCKET_NAME}/csv/")
    assert [f"s3://{ECON_BUCKET_NAME}/copy/keep.csv"] == wr.s3.list_objects(f"s3://{ECON_BUCKET_NAME}/copy/")

    aws.rename("csv/csv.csv", "copy/keep_second.csv")

    assert [
        f"s3://{ECON_BUCKET_NAME}/copy/keep.csv",
        f"s3://{ECON_BUCKET_NAME}/copy/keep_second.csv",
    ] == wr.s3.list_objects(f"s3://{ECON_BUCKET_NAME}/copy/")


def test_query(mocked_aws):
    aws = AwsEcon()

    df = aws.query("SELECT * FROM table")
    pd.testing.assert_frame_equal(df, pd.DataFrame(), check_dtype=False)
