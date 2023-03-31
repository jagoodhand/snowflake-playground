# -*- coding: utf-8 -*-
# snapshottest: v1 - https://goo.gl/zC4yUc
from __future__ import unicode_literals

from snapshottest import GenericRepr, Snapshot


snapshots = Snapshot()

snapshots['test_streams_objects 1'] = GenericRepr('       NAME    DATABASE_NAME SCHEMA_NAME     OWNER COMMENT  \\\n0  STREAM_1  TEST_PLAYGROUND      GROUND  SYSADMIN           \n\n                       TABLE_NAME SOURCE_NAME                     BASE_TABLES  \\\n0  TEST_PLAYGROUND.GROUND.TABLE_1       Table  TEST_PLAYGROUND.GROUND.TABLE_1   \n\n    TYPE     MODE INVALID_REASON  \n0  DELTA  DEFAULT            N/A  ')

snapshots['test_tasks_objects 1'] = GenericRepr('     NAME    DATABASE_NAME SCHEMA_NAME     OWNER COMMENT   WAREHOUSE  \\\n0  TASK_1  TEST_PLAYGROUND      GROUND  SYSADMIN          COMPUTE_WH   \n\n    SCHEDULE PREDECESSORS      STATE             DEFINITION CONDITION  \\\n0  10 MINUTE           []  suspended  select * from table_1      None   \n\n  ERROR_INTEGRATION  \n0              null  ')

snapshots['test_tidy_playground 1'] = GenericRepr('                                             SQL_CMD  \\\n0  ALTER STREAM "TEST_PLAYGROUND"."GROUND"."STREA...   \n1  ALTER VIEW "TEST_PLAYGROUND"."GROUND"."VIEW_2"...   \n2  ALTER VIEW "TEST_PLAYGROUND"."GROUND"."VIEW_5"...   \n3  DROP PROCEDURE "TEST_PLAYGROUND"."GROUND"."PRO...   \n4      DROP TASK "TEST_PLAYGROUND"."GROUND"."TASK_1"   \n5      DROP VIEW "TEST_PLAYGROUND"."GROUND"."VIEW_4"   \n6      DROP VIEW "TEST_PLAYGROUND"."GROUND"."VIEW_6"   \n\n                                     OBJECT_PATH OBJECT_TYPE  \\\n0              TEST_PLAYGROUND.GROUND."STREAM_1"      STREAM   \n1                TEST_PLAYGROUND.GROUND."VIEW_2"        VIEW   \n2                TEST_PLAYGROUND.GROUND."VIEW_5"        VIEW   \n3  TEST_PLAYGROUND.GROUND."PROC_1"(VARCHAR,DATE)   PROCEDURE   \n4                TEST_PLAYGROUND.GROUND."TASK_1"        TASK   \n5                TEST_PLAYGROUND.GROUND."VIEW_4"        VIEW   \n6                TEST_PLAYGROUND.GROUND."VIEW_6"        VIEW   \n\n              ACTION          STATUS  \\\n0  ALTER_EXPIRY_DATE     ILLEGAL_TAG   \n1  ALTER_EXPIRY_DATE     ILLEGAL_TAG   \n2  ALTER_EXPIRY_DATE     ILLEGAL_TAG   \n3        DROP_OBJECT  EXPIRED_OBJECT   \n4        DROP_OBJECT     EXPIRED_TAG   \n5        DROP_OBJECT  EXPIRED_OBJECT   \n6        DROP_OBJECT     EXPIRED_TAG   \n\n                                              REASON  OBJECT_AGE  \\\n0  Expiry tag date is more than 90 days in the fu...          50   \n1  Expiry tag date is more than 90 days in the fu...          10   \n2  Expiry tag date is more than 90 days in the fu...          80   \n3                  Expiry date for object has passed          32   \n4      Object older than 31 days without expiry tag.          31   \n5                  Expiry date for object has passed          70   \n6      Object older than 31 days without expiry tag.          90   \n\n  DAYS_SINCE_LAST_OBJECT_ALTERATION OBJECT_EXPIRY_DATE  \\\n0                              None         9999-12-31   \n1                                 0         9999-12-31   \n2                                 0         9999-12-31   \n3                                 0               None   \n4                              None         2020-01-01   \n5                                 0               None   \n6                                 0         2020-01-01   \n\n                         CMD_RESULT  \n0  Statement executed successfully.  \n1  Statement executed successfully.  \n2  Statement executed successfully.  \n3      PROC_1 successfully dropped.  \n4      TASK_1 successfully dropped.  \n5      VIEW_4 successfully dropped.  \n6      VIEW_6 successfully dropped.  ')

snapshots['test_tidy_playground 2'] = GenericRepr('              ACTION OBJECT_TYPE          STATUS  \\\n0  ALTER_EXPIRY_DATE      STREAM     ILLEGAL_TAG   \n1  ALTER_EXPIRY_DATE        VIEW     ILLEGAL_TAG   \n2        DROP_OBJECT   PROCEDURE  EXPIRED_OBJECT   \n3        DROP_OBJECT        TASK     EXPIRED_TAG   \n4        DROP_OBJECT        VIEW  EXPIRED_OBJECT   \n5        DROP_OBJECT        VIEW     EXPIRED_TAG   \n\n                         CMD_RESULT  COUNT  \n0  Statement executed successfully.      0  \n1  Statement executed successfully.     14  \n2      PROC_1 successfully dropped.      0  \n3      TASK_1 successfully dropped.      0  \n4      VIEW_4 successfully dropped.      0  \n5      VIEW_6 successfully dropped.      7  ')