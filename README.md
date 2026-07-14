# gds-idea-pkg-aws-econ

The package simplifies access to S3 and Athena for GDS IDEA team.

## How to use

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

>>> from aws_econ import aws_econ \
>>> aws = AwsEcon()


List files and directories in a bucket.

>>> result = aws.list("data", "bucket") \
>>> result \
{"directories": [], "files": ["csv.csv"]}

Notice that both arguments folder and bucket are optional.
If folder is not given, top bucket folder will be listed.
If bucket is not given, default econ bucket will be listed.


Read file from S3.
>>> df = aws.read("project1/data.csv", "bucket") \
>>> df \
&ensp; 0   1 \
0   3   4 \
1   5   6

Notice that second argument bucket is optional.
If bucket is not given, default econ bucket will be used.
If possible data you read will be returned as DataFrame.


Write file to S3.
>>> df = pd.DataFrame([[1,2],[3,4]]) \
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
>>> df = aws.query("SELECT * FROM table", database="database_project1", s3tables=True) \
>>> df \
&ensp; 0   1 \
0   3   4 \
1   5   6

Notice that first argument is SQL query,
second argument database is optional, deafult value is default.
third argument s3tables is optional, default value False will read data from S3 data catalogue,
True will read data from S3Tables data catalogue.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) for Python package management
- [git](https://git-scm.com/)
- [gitleaks](https://github.com/gitleaks/gitleaks) for pre-commit secret scanning (`brew install gitleaks`)

## Getting started

1. Clone the repository:

   ```bash
   git clone git@github.com:co-cddo/gds-idea-pkg-aws-econ.git
   cd gds-idea-pkg-aws-econ
   ```

2. Install dependencies:

   ```bash
   uv sync
   ```

3. Set up pre-commit hooks:

   ```bash
   uv run pre-commit install
   ```

   This is done automatically when the project is first scaffolded.
   Pre-commit runs [ruff](https://docs.astral.sh/ruff/) on every commit
   to auto-fix lint issues and enforce formatting.

## Development

### Running tests

```bash
uv run pytest
```

### Running linting manually

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
```

### Pre-commit hooks

Pre-commit hooks run automatically on `git commit`. They will:

- **Auto-fix** lint issues detected by `ruff check --fix`
- **Auto-format** code with `ruff format`
- **Check** YAML/TOML syntax, trailing whitespace, merge conflicts
- **Scan** for leaked secrets with gitleaks
- **Prevent** direct commits to `main`

If files are modified by the hooks, the commit will be aborted.
Review the changes, `git add` them, and commit again.

To run hooks against all files manually:

```bash
uv run pre-commit run --all-files
```

## Versioning

This project uses [hatch-vcs](https://github.com/ofek/hatch-vcs) for
automatic versioning from git tags. Versions are never set manually.

On merge to `main`, the auto-release workflow creates a new tag based on
PR labels:

- `bump:major` — major version bump
- `bump:minor` — minor version bump
- (default) — patch version bump

## Licence

[MIT License](LICENCE)
