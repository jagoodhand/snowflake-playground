import datetime
import json
import uuid

def get_illegal_objects(session,
                        object_ages_view_path,
                        max_object_age_without_tag,
                        max_expiry_tag_date):
  return session.sql(f"""
    SELECT
      OBJECT_DATABASE,
      OBJECT_SCHEMA,
      OBJECT_NAME,
      OBJECT_TYPE,
      SQL_OBJECT_TYPE,
      OBJECT_DOMAIN,
      DAYS_SINCE_CREATION,
      DAYS_SINCE_LAST_ALTERATION,
      EXPIRY_DATE,
      OBJECT_OWNER,
      CASE
        WHEN (DAYS_SINCE_CREATION > {max_object_age_without_tag}) AND (EXPIRY_DATE IS NULL) THEN 'EXPIRED_OBJECT'
        WHEN (EXPIRY_DATE < CURRENT_DATE()) THEN 'EXPIRED_TAG'
        WHEN (EXPIRY_DATE > {max_expiry_tag_date}) THEN 'ILLEGAL_TAG'
      END AS STATUS
    FROM
      {object_ages_view_path}
    WHERE
      (
        DAYS_SINCE_CREATION > {max_object_age_without_tag}
        AND EXPIRY_DATE IS NULL
      ) OR (
        EXPIRY_DATE < CURRENT_DATE()
      ) OR (
        EXPIRY_DATE > {max_expiry_tag_date}
      )
  ;""").collect()

def determine_actions_from_status(object_details,
                                  expiry_date_tag,
                                  max_object_age_without_tag,
                                  max_expiry_days,
                                  max_expiry_tag_date):
  """Determine the action to take for a given object.

  The 'STATUS' result for a given object is used to determine the action to take.
  Use this information to generate the SQL statement to execute, and the reason / action for the log.

  Args:
    - object_details: a row from the illegal_objects view
    - expiry_date_tag: the name of the expiry date tag
    - max_object_age_without_tag: the maximum age of an object without an expiry date tag
    - max_expiry_days: the maximum number of days in the future that an expiry date tag can be set
    - max_expiry_tag_date: the maximum date that an expiry date tag can be set

  Returns:
    - a dictionary containing the reason, action and SQL statement to take for the object
  """
  if object_details['STATUS'] == 'EXPIRED_OBJECT':
    reason = "Expiry date for object has passed"
    action = "DROP_OBJECT"
    sql = f"DROP {object_details['OBJECT_TYPE']} \"{object_details['OBJECT_DATABASE']}\".\"{object_details['OBJECT_SCHEMA']}\".{object_details['OBJECT_NAME']};"

    return {
      'reason': reason,
      'action': action,
      'sql': sql
    }
  elif object_details['STATUS'] == 'EXPIRED_TAG':
    reason = f"Object older than {max_object_age_without_tag} days without expiry tag."
    action = "DROP_OBJECT"
    sql = f"DROP {object_details['OBJECT_TYPE']} \"{object_details['OBJECT_DATABASE']}\".\"{object_details['OBJECT_SCHEMA']}\".{object_details['OBJECT_NAME']};"

    return {
      'reason': reason,
      'action': action,
      'sql': sql
    }
  elif object_details['STATUS'] == 'ILLEGAL_TAG':
    reason = f"Expiry tag date is more than {max_expiry_days} days in the future."
    action = "ALTER_EXPIRY_DATE"
    sql = f"ALTER {object_details['OBJECT_TYPE']} \"{object_details['OBJECT_DATABASE']}\".\"{object_details['OBJECT_SCHEMA']}\".{object_details['OBJECT_NAME']} SET TAG {expiry_date_tag} = '{max_expiry_tag_date}';"

    return {
      'reason': reason,
      'action': action,
      'sql': sql
    }
  else:
    raise ValueError(f"Unknown status: {object_details['STATUS']}")

def generate_log_record(row, actions, result):
  return {
      'sql': actions['sql'],
      'action': actions['action'],
      'object_type': row['OBJECT_TYPE'],
      'status': row['STATUS'],
      'reason': actions['sql'],
      'justification': {
        'age': row['DAYS_SINCE_CREATION'],
        'days_since_last_alteration': row['DAYS_SINCE_LAST_ALTERATION'],
        'expiry_date': row['EXPIRY_DATE']
      },
      'result': result
    }

def main(session,
         is_dry_run,
         expiry_date_tag,
         max_expiry_days,
         max_object_age_without_tag,
         object_ages_view_path,
         log_table_path):
  """Tidy the Playground Environment of 'illegal' objects.

  Find all objects in the Playground environment that:
    - are older than max_object_age_without_tag days and have no expiry date tag
      - DROP
    - have an expiry date tag that is in the past
      - DROP
    - have an expiry date tag that is more than max_expiry_days in the future
      - ALTER Tag to be max_expiry_days in the future

  Args:
    - session: inserted snowpark session
    - is_dry_run: Whether the script should run in dry run mode.
    - expiry_date_tag: Path to the expiry date tag
    - max_expiry_days: Max number of days in the future that an expiry date tag can be set to
    - max_object_age_without_tag: Max number of days that an object can be without an expiry date tag
    - object_ages_view_path: Path to the view that contains the object ages
    - log_table: Path to the log table

  Returns:
    - string: result summary
  """

  MAX_EXPIRY_TAG_DATE = datetime.date.today()+ datetime.timedelta(days = max_object_age_without_tag)
  RUN_ID = str(uuid.uuid4())

  illegal_objects = get_illegal_objects(session,
                                        object_ages_view_path,
                                        max_object_age_without_tag,
                                        MAX_EXPIRY_TAG_DATE)

  for _, row in illegal_objects.iterrows():
    actions = determine_actions_from_status(row['STATUS'],
                                            expiry_date_tag,
                                            max_object_age_without_tag,
                                            max_expiry_days,
                                            MAX_EXPIRY_TAG_DATE)

    if is_dry_run:
      result = 'DRY_RUN'
    else:
      result_df = session.sql(actions['sql']).collect()
      result = result_df.iloc[0,0]

    log_record = generate_log_record(row, actions, result)
    session.sql(f"""INSERT INTO {log_table_path} (event_time, run_id, record)
                      SELECT CURRENT_TIMESTAMP(),
                      '{RUN_ID}',
                      PARSE_JSON('{json.dumps(log_record)}')'
                ;""")

  return f"Success."

# TODO: Catch permission denied errors.
# TODO: Add doc strings / comments
# TODO: Have properties in a table, rather than passing in as arguments?
