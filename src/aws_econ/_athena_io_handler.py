import hashlib
import json
import time


def _start_query(athena_client, query, database, catalog=None, workgroup="primary", query_parameters=None):
    kwargs = {}
    if query_parameters is not None:
        kwargs["ExecutionParameters"] = query_parameters

    response = athena_client.start_query_execution(
        QueryString=query,
        ClientRequestToken=hashlib.sha1(bytes(query + str(time.time()), encoding="utf-8")).hexdigest(),
        QueryExecutionContext={"Database": database, "Catalog": catalog} if catalog else {"Database": database},
        WorkGroup=workgroup,
        **kwargs,
    )

    return response


def _has_query_succeeded(athena_client, execution_id, sleep=2):
    state = "RUNNING"
    max_execution = 5

    while state in ["RUNNING", "QUEUED"]:
        max_execution -= 1
        response = athena_client.get_query_execution(QueryExecutionId=execution_id)
        if (
            "QueryExecution" in response
            and "Status" in response["QueryExecution"]
            and "State" in response["QueryExecution"]["Status"]
        ):
            state = response["QueryExecution"]["Status"]["State"]
            if state == "SUCCEEDED":
                return True

        time.sleep(sleep)

    raise Exception(json.dumps(response, default=str))


def _get_query_results(athena_client, execution_id):
    data = []
    response = athena_client.get_query_results(
        QueryExecutionId=execution_id,
    )

    if "ResultSet" in response:
        data = response["ResultSet"]["Rows"]
    while response.get("NextToken") is not None:
        response = athena_client.get_query_results(QueryExecutionId=execution_id, NextToken=response.get("NextToken"))
        if "ResultSet" in response:
            data += response["ResultSet"]["Rows"]

    data = [[element.get("VarCharValue", None) for element in row["Data"]] for row in data]

    return data
