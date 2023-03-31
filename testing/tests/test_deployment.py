import os
import datetime
import pandas as pd
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)


def connect_to_snowflake():
    with open(os.environ.get("SNOWFLAKE_RSA_KEY_PATH"), "rb") as key:
        p_key = serialization.load_pem_private_key(
            key.read(), password=None, backend=default_backend()
        )

    pkb = p_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    conn = snowflake.connector.connect(
        user=os.environ.get("SNOWFLAKE_USER_NAME"),
        role="SYSADMIN",
        account=os.environ.get("SNOWFLAKE_ACCOUNT_ID"),
        region=os.environ.get("SNOWFLAKE_REGION"),
        warehouse="COMPUTE_WH",
        private_key=pkb,
    )

    return conn


def test_conn():
    conn = connect_to_snowflake()

    cur = conn.cursor()
    try:
        cur.execute("SELECT CURRENT_VERSION()")
        df = cur.fetch_pandas_all()

        print()
        print(df.head())
    finally:
        cur.close()


def setup_module():
    conn = connect_to_snowflake()
    cur = conn.cursor()

    # Clear any previous data
    cur.execute("USE TEST_PLAYGROUND.ADMINISTRATION")
    cur.execute("TRUNCATE TABLE TEST_PLAYGROUND.ADMINISTRATION.STATIC_OBJECT_AGES")

    # Load the fake data
    fake_data = pd.read_csv("data/object_ages.csv")
    write_pandas(conn, fake_data, "STATIC_OBJECT_AGES")

    # Update the tag values to match those dynamically generated by Terraform
    cur.execute(
        """
        UPDATE TEST_PLAYGROUND.ADMINISTRATION.STATIC_OBJECT_AGES
            SET EXPIRY_DATE = DATEADD(hour, 960, CURRENT_TIMESTAMP)
            WHERE OBJECT_NAME = '"TABLE_2"'
    """
    )
    cur.execute(
        """
        UPDATE TEST_PLAYGROUND.ADMINISTRATION.STATIC_OBJECT_AGES
            SET EXPIRY_DATE = '2020-01-01'
            WHERE OBJECT_NAME = '"TASK_1"'
    """
    )
    cur.execute(
        """
        UPDATE TEST_PLAYGROUND.ADMINISTRATION.STATIC_OBJECT_AGES
            SET EXPIRY_DATE = DATEADD(hour, 1200, CURRENT_TIMESTAMP)
            WHERE OBJECT_NAME = '"STAGE_1"'
    """
    )
    cur.execute(
        """
        UPDATE TEST_PLAYGROUND.ADMINISTRATION.STATIC_OBJECT_AGES
            SET EXPIRY_DATE = '2020-01-01'
            WHERE OBJECT_NAME = '"VIEW_6"'
    """
    )

    # Update the tag values for non-date values
    cur.execute(
        """
        UPDATE TEST_PLAYGROUND.ADMINISTRATION.STATIC_OBJECT_AGES
            SET EXPIRY_DATE = TRY_TO_DATE('not_a_date')
            WHERE OBJECT_NAME = '"VIEW_1"'
    """
    )
    cur.execute(
        """
        UPDATE TEST_PLAYGROUND.ADMINISTRATION.STATIC_OBJECT_AGES
            SET EXPIRY_DATE = TRY_TO_DATE('not_a_date')
            WHERE OBJECT_NAME = '"VIEW_4"'
    """
    )


def test_streams_objects(snapshot):
    print()
    conn = connect_to_snowflake()

    cur = conn.cursor()
    try:
        cur.execute("CALL TEST_PLAYGROUND.ADMINISTRATION.UPDATE_OBJECTS('streams')")
        cur.execute("SELECT * FROM TEST_PLAYGROUND.ADMINISTRATION.STREAMS")
        df = cur.fetch_pandas_all()

    finally:
        cur.close()

    df.drop(columns=["CREATED_ON", "STALE_AFTER", "STALE"], inplace=True)
    print(df.head())
    print(df.dtypes)

    snapshot.assert_match(df)


def test_tasks_objects(snapshot):
    print()
    conn = connect_to_snowflake()

    cur = conn.cursor()
    try:
        cur.execute("CALL TEST_PLAYGROUND.ADMINISTRATION.UPDATE_OBJECTS('tasks')")
        cur.execute("SELECT * FROM TEST_PLAYGROUND.ADMINISTRATION.TASKS")
        df = cur.fetch_pandas_all()

    finally:
        cur.close()

    df.drop(
        columns=[
            "CREATED_ON",
            "ID",
            "LAST_COMMITTED_ON",
            "LAST_SUSPENDED_ON",
            "ALLOW_OVERLAPPING_EXECUTION",
        ],
        inplace=True,
    )
    print(df.head())
    print(df.dtypes)

    snapshot.assert_match(df)


def test_tidy_playground(snapshot):
    """Test cases to check that the tidy_playground procedure works as expected

    Test cases:
        1. Object within max age, no tag - no action | TABLE_1
        2. Object within max age, tag - no action | TABLE_2
        3. Object within max age, tag, but tag value not a date - no action | VIEW_1
        4. Object within max age, tag, but tag value illegal - re-date tag | VIEW_2
        5. Object within max age, tag, but tag value expired - drop | TASK_1
        6. Object outside max age, illegal tag - re-date tag | STREAM_1
        7. Object outside max age, tag - no action | STAGE_1
        8. Object outside max age, no tag - drop | PROC_1
        9. Object outside max age, tag, but tag value not a date - drop | VIEW_4
        10. Object outside max age, tag, but tag value illegal - re-date tag | STREAM_1
        11. Object outside max age, tag, but tag value expired - drop | VIEW_5
        12. No permission to see / drop object - no action & not logged | TABLE_2

    (Objects with no permissions are not logged because the they do not have permission
    to see them in the metadata tables.)
    """
    print()

    MAX_EXPIRY_DAYS = 90
    MAX_OBJECT_AGE_WITHOUT_TAG = 31
    MAX_EXPIRY_TAG_DATE = (
        datetime.date.today() + datetime.timedelta(days=MAX_EXPIRY_DAYS)
    ).strftime("%Y-%m-%d")

    conn = connect_to_snowflake()
    cur = conn.cursor()

    try:
        cur.execute(
            f"""CALL TEST_PLAYGROUND.ADMINISTRATION.TIDY_PLAYGROUND(
                'false',
                'TEST_PLAYGROUND.ADMINISTRATION.EXPIRY_DATE',
                {MAX_EXPIRY_DAYS},
                {MAX_OBJECT_AGE_WITHOUT_TAG},
                'TEST_PLAYGROUND.ADMINISTRATION.STATIC_OBJECT_AGES',
                'TEST_PLAYGROUND.ADMINISTRATION.LOG'
            )"""
        )

        cur.execute(
            "SELECT * FROM TEST_PLAYGROUND.ADMINISTRATION.LOG_VIEW ORDER BY SQL_CMD"
        )
        log = cur.fetch_pandas_all()
        log.drop(columns=["EVENT_TIME", "RUN_ID"], inplace=True)
        log["SQL_CMD"] = log["SQL_CMD"].str.replace(
            r"(\d\d\d\d-\d\d-\d\d)", MAX_EXPIRY_TAG_DATE, regex=True
        )

        snapshot.assert_match(log)

        cur.execute(
            """SELECT
                *
               FROM
                TEST_PLAYGROUND.ADMINISTRATION.LOG_SUMMARY
               ORDER BY
                ACTION, OBJECT_TYPE, STATUS, CMD_RESULT
            """
        )
        log_summary = cur.fetch_pandas_all()
        log_summary.drop(columns=["RUN_START_TIME", "RUN_ID"], inplace=True)
        snapshot.assert_match(log_summary)

    finally:
        cur.close()
