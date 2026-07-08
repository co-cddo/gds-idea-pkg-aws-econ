def _list_objects(s3_client, bucket, folder):
    if len(folder) != 0 and folder[-1] != "/":
        folder = folder + "/"
    contents_prefixes = []
    contents = []
    response = s3_client.list_objects_v2(Bucket=bucket, Prefix=folder, Delimiter="/")
    if "CommonPrefixes" in response:
        contents_prefixes += response["CommonPrefixes"]
    if "Contents" in response:
        contents += response["Contents"]
    while response["IsTruncated"]:
        token = response["NextContinuationToken"]
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=folder, Delimiter="/", ContinuationToken=token)
        if "CommonPrefixes" in response:
            contents_prefixes += response["CommonPrefixes"]
        if "Contents" in response:
            contents += response["Contents"]

    return contents_prefixes, contents


def _list_folders(folder, contents):
    if len(folder) != 0 and folder[-1] != "/":
        folder = folder + "/"
    listdir = [c["Prefix"] for c in contents]
    if len(folder) != 0:
        listdir = [dir.split(folder)[1] for dir in listdir]
    listdir = [dir[:-1] for dir in listdir]
    return listdir


def _list_files(folder, contents):
    if len(folder) != 0 and folder[-1] != "/":
        folder = folder + "/"
    listdir = [c["Key"] for c in contents if c["Key"][-1] != "/"]
    if len(folder) != 0:
        listdir = [d.split(folder)[1] for d in listdir]
    return listdir
