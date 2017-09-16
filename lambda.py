#!/usr/bin/env python3.6
import os
import logging
import aws_lambda_logging
import json
import re
import ruamel.yaml as yaml
import mysql.connector
from urllib.parse import urlparse, parse_qs
from urllib.parse import urlencode, quote_plus
import unittest
from unittest.mock import patch
from timeit import default_timer as timer
import time
import uuid


aws_lambda_logging.setup(level=os.environ.get('LOGLEVEL', 'INFO'), env=os.environ.get('ENV'), timestamp=int(time.time()))
aws_lambda_logging.setup(level=os.environ.get('LOGLEVEL', 'INFO'), env=os.environ.get('ENV'), timestamp=int(time.time()))


def button_handler(event, context):
    """Handler for button events"""

    aws_lambda_logging.setup(level=os.environ.get('LOGLEVEL', 'INFO'), env=os.environ.get('ENV'))
    aws_lambda_logging.setup(level=os.environ.get('LOGLEVEL', 'INFO'), env=os.environ.get('ENV'))
    logging.debug(json.dumps({'action': 'initialising'}))
    try:
        logging.debug(json.dumps({'action': 'logging event', 'status': 'success', 'event': event}))
    except:
        logging.exception(json.dumps({'action': 'logging event', 'status': 'failed'}))

    try:
        body = parse_qs(event['body'])
        payload = json.loads(body['payload'][0])
    except:
        logging.exception(json.dumps({'action': 'parse payload', 'status': 'failed'}))
        raise
    else:
        logging.debug(json.dumps({'action': 'parse payload', 'status': 'success', 'payload': payload}))

    try:
        correlation_id = get_correlation_id(payload=payload)
        aws_lambda_logging.setup(level=os.environ.get('LOGLEVEL', 'INFO'), env=os.environ.get('ENV'), correlation_id=correlation_id)
    except:
        logging.exception(json.dumps({"action": "get correlation-id", "status": "failed"}))
        response = {
            "statusCode": 503,
            'headers': {
                'Content-Type': 'application/json',
            }
        }
        return response
    else:
        logging.debug(json.dumps({'action': 'get correlation-id', 'status': 'success', 'correlation_id': correlation_id}))

    try:
        selected_alias = payload['actions'][0]['value']
    except:
        logging.exception(json.dumps({'action': 'get selected_alias', 'status': 'failed'}))
    else:
        logging.info(json.dumps({'action': 'get selected_alias', 'status': 'success', 'selected_alias': selected_alias}))

    try:
        response = lookup_alias_and_execute(selected_alias)
    except mysql.connector.errors.InterfaceError:
        response = {
            "statusCode": 200,
            "body": json.dumps({"text": "Failed to execute MySQL query"}),
            'headers': {
                'Content-Type': 'application/json',
            }
        }
        return response

    logging.info(json.dumps({'action': 'responding', 'response': response}))
    return response


def get_correlation_id(body=None, payload=None, event=None):
    if body is not None:
        correlation_id = body['trigger_id'][0]
    elif payload is not None:
        correlation_id = payload['trigger_id']
    elif event is not None:
        correlation_id = event['headers']['X-Amzn-Trace-Id'].split('=')[1]
    else:
        correlation_id = str(uuid.uuid4())
    return correlation_id


def handler(event, context):
    """Main entrypoint"""

    aws_lambda_logging.setup(level=os.environ.get('LOGLEVEL', 'INFO'), env=os.environ.get('ENV'))
    aws_lambda_logging.setup(level=os.environ.get('LOGLEVEL', 'INFO'), env=os.environ.get('ENV'))
    logging.debug(json.dumps({'action': 'initialising'}))
    try:
        logging.debug(json.dumps({'action': 'logging event', 'status': 'success', 'event': event}))
    except:
        logging.exception(json.dumps({'action': 'logging event', 'status': 'failed'}))

    try:
        body = parse_qs(event['body'])
    except Exception:
        logging.exception(json.dumps({'action': 'parse body', 'status': 'failed'}))
        raise
    else:
        logging.debug(json.dumps({'action': 'parse body', 'status': 'success', 'body': body}))

    try:
        correlation_id = get_correlation_id(body=body)
        aws_lambda_logging.setup(level=os.environ.get('LOGLEVEL', 'INFO'), env=os.environ.get('ENV'), correlation_id=correlation_id)
    except:
        logging.exception(json.dumps({"action": "get correlation-id", "status": "failed"}))
        response = {
            "statusCode": 503,
            'headers': {
                'Content-Type': 'application/json',
            }
        }
        return response
    else:
        logging.debug(json.dumps({'action': 'get correlation-id', 'status': 'success', 'correlation_id': correlation_id}))

    try:
        selected_alias = body['text'][0]
    except KeyError:
        logging.exception(json.dumps({'action': 'get selected_alias', 'status': 'failed'}))
        response = {
            "statusCode": 200,
            "body": json.dumps({"text": "Failed to validate user's selected alias"}),
            'headers': {
                'Content-Type': 'application/json',
            }
        }
        return response
    else:
        logging.info(json.dumps({'action': 'get selected_alias', 'status': 'success', 'selected_alias': selected_alias}))

    try:
        response = lookup_alias_and_execute(selected_alias)
    except mysql.connector.errors.InterfaceError:
        response = {
            "statusCode": 200,
            "body": json.dumps({"text": "Failed to execute MySQL query"}),
            'headers': {
                'Content-Type': 'application/json',
            }
        }
        return response

    logging.info(json.dumps({'action': 'responding', 'response': response}))
    return response


def get_config():
    with open("example.yml") as stream:
        try:
            config = yaml.safe_load(stream)
        except yaml.YAMLError:
            logging.exception(json.dumps({'action': 'load yaml', 'status': 'failed'}))
            raise
        else:
            logging.debug(json.dumps({'action': 'load yaml', 'status': 'success', 'config': config}))
    return config


class FunctionTests(unittest.TestCase):
    @patch('__main__.get_correlation_id', return_value='asdfasdfasdf')
    @patch('__main__.get_config', return_value={'queries': []})
    def test_lookup_alias_and_execute(self, get_config, get_correlation_id):
        self.assertEqual(get_correlation_id(), 'asdfasdfasdf')
        self.assertNotEqual(get_correlation_id(), 'asdfasdfasdfx')
        selected_alias = '23452345'
        response = lookup_alias_and_execute(selected_alias)
        self.assertEqual(json.loads(response['body'])['text'], "The alias `{}` doesn't exist. Here are the available aliases you may call:".format(selected_alias))
        self.assertEqual(response['statusCode'], 200)

    def test_missing_alias_message(self):
        queries = [{'alias': 'testalias', 'sql': 'select * from testsql', 'mysql_host': 'test.com.au', 'mysql_database': 'testdb'}, {'alias': 'testalias', 'sql': 'select * from testsql', 'mysql_host': 'test.com.au', 'mysql_database': 'testdb'}, {'anotheralias': 'testalias', 'sql': 'select * from testsql', 'mysql_host': 'test.com.au', 'mysql_database': 'testdb'}]
        selected_alias = 'testalias'
        response = missing_alias_message(queries, selected_alias)
        self.assertEqual(json.loads(response['body'])['text'], "The alias `{}` doesn't exist. Here are the available aliases you may call:".format(selected_alias))

        attachments = json.loads(response['body'])['attachments']

        self.assertTrue(attachments)

        fields = [x["fields"] for x in attachments]
        logging.debug(json.dumps({'fields': fields, 'action': 'logging fields'}))
        titles = [x["title"] for x in fields[0]]
        logging.debug(json.dumps({'titles': titles, 'action': 'logging titles'}))
        values = [x["value"] for x in fields[0]]
        logging.debug(json.dumps({'values': values, 'action': 'logging values'}))

        self.assertTrue("Alias" in titles)
        self.assertTrue("test.com.au" in str(values))


def lookup_alias_and_execute(selected_alias):
    """Executes a user's selected alias by looking up details from the config file, returns a message that can be returned to Slack"""

    config = get_config()

    try:
        query = [query for query in config['queries'] if query['alias'] == selected_alias][0]
    except:
        logging.warning(json.dumps({'action': 'get query using selected_alias', 'status': 'failed', 'selected_alias': selected_alias, 'config': str(config)}))
        return missing_alias_message(config['queries'], selected_alias)
    else:
        logging.debug(json.dumps({'action': 'get query using selected_alias', 'status': 'success', 'selected_alias': selected_alias, 'query': query, 'config': config}))

    try:
        result = run_query(query)
    except mysql.connector.errors.ProgrammingError:
        logging.exception(json.dumps({"action": "getting query results", "status": "failed"}))
        return format_response({"text": "The SQL query (alias: {}) failed, please check the logs for more information".format(selected_alias)})
    except KeyError:
        logging.exception(json.dumps({"action": "getting query results", "status": "failed"}))
        return format_response({"text": "The SQL query (alias: {}) failed, are the credentials for this query configured?".format(selected_alias)})
    else:
        logging.debug(json.dumps({"action": "getting query results", "status": "success", "result": "results are not JSON serialisable, skipping"}))

    response = format_query_result(result, query)
    return response


def missing_alias_message(queries, selected_alias):
    """Returns a mesage about the alias missing and provides valid aliases to execute"""

    try:
        attachments = []
        for query in queries:
            attachments.append({
                "color": "#36a64f",
                "callback_id": "comic_1234_xyz",
                "fields": [
                    {
                        "title": "Alias",
                        "value": query['alias'],
                        "short": True
                    },
                    {
                        "title": "SQL statement",
                        "value": query['sql'],
                        "short": False
                    },
                    {
                        "title": "MySQL Server",
                        "value": query['mysql_host'],
                        "short": True
                    },
                    {
                        "title": "Database",
                        "value": query['mysql_database'],
                        "short": True
                    }
                ],
                "actions": [
                    {
                        "name": "execute",
                        "text": "execute",
                        "type": "button",
                        "value": query['alias']
                    }
                ],
                "fallback": "alias: {}, statement: {}".format(query['alias'], query['sql'])
            })
    except:
        logging.exception(json.dumps({'action': 'formatting attachments', 'status': 'failed', 'queries': queries, 'selected_alias': selected_alias}))
    else:
        logging.exception(json.dumps({'action': 'formatting attachments', 'status': 'success', 'attachments': attachments}))

    body = {
        "response_type": "in_channel",
        "replace_original": False,
        "text": "The alias `{}` doesn't exist. Here are the available aliases you may call:".format(selected_alias),
        "attachments": attachments
    }
    response = format_response(body)
    return response


def run_query(query):
    """Takes a query from the configuration file, executes it and returns the result"""

    start = timer()
    attempts = 0
    connected = False
    while not connected:
        try:
            cnx = mysql.connector.connect(
                charset='utf8',
                connect_timeout=20,
                user=os.environ['MYSQL_USER'],
                password=os.environ['MYSQL_PASSWORD'],
                database=query['mysql_database'],
                host=query['mysql_host']
            )
            connected = True
        except (mysql.connector.errors.InterfaceError, mysql.connector.errors.ProgrammingError):
            elapsed = timer() - start
            logging.info(json.dumps({"action": "connect to mysql", "status": "failed", "attempts": attempts, "elapsed": elapsed}))
            if elapsed > 10 or attempts > 10:
                logging.exception("Failed to connect to MySQL database")
                raise
            attempts += 1
            time.sleep(1)
        except KeyError:
            logging.exception(json.dumps({'action': 'connect to mysql', 'status': 'failed', 'credentials': 'absent'}))
            raise

    try:
        start = timer()
        cur = cnx.cursor(buffered=True, dictionary=True)
        cur.execute(query['sql'])
        result = cur.fetchall()
    except:
        elapsed = timer() - start
        logging.exception(json.dumps({'action': 'running query', 'status': 'failed', "elapsed": elapsed, 'query': query['sql']}))
        raise
    else:
        elapsed = timer() - start
        logging.info(json.dumps({'action': 'running query', 'status': 'success', "elapsed": elapsed, 'query': query['sql']}))

    try:
        cnx.close()
    except:
        logging.exception(json.dumps({'action': 'disconnect from MySQL', 'status': 'failed'}))
    else:
        logging.debug(json.dumps({'action': 'running query', 'status': 'success', "elapsed": elapsed}))

    return result


def format_response(body):
    """Formats the Slack response to work with lambda-proxy"""

    response = {
        "statusCode": 200,
        "body": json.dumps(body),
        'headers': {
            'Content-Type': 'application/json',
        }
    }
    return response


def format_table(myDict, colList=None):
    """ Pretty print a list of dictionaries (myDict) as a dynamically sized table.
    If column names (colList) aren't specified, they will show in random order.
    Author: Thierry Husson - Use it as you want but don't blame me.
    """
    table = ""
    if not colList:
        colList = list(myDict[0].keys() if myDict else [])
    myList = [colList]  # 1st row = header
    for item in myDict:
        myList.append([str(item[col] or '') for col in colList])
    colSize = [max(map(len, col)) for col in zip(*myList)]
    formatStr = ' | '.join(["{{:<{}}}".format(i) for i in colSize])
    myList.insert(1, ['-' * i for i in colSize])  # Seperating line
    for item in myList:
        table = table + formatStr.format(*item) + "\n"
    return table


def format_query_result(result, query):
    """Formats the query results in to a format accepted by Slack"""

    rows = []
    try:
        for row in result:
            for item in row:
                try:
                    row[item] = row[item].decode('ascii', 'ignore')
                except:
                    pass
                try:
                    row[item] = str(row[item])
                except:
                    pass
            rows.append(row)

        table = format_table(rows)

        attachments = []
        attachments.append({
            "color": "#36a64f",
            "callback_id": "comic_1234_xyz",
            "mrkdwn_in": ["fields"],
            "fields": [
                {
                    "title": "Alias",
                    "value": query['alias'],
                    "short": True
                },
                {
                    "title": "SQL statement",
                    "value": query['sql'],
                    "short": False
                },
                {
                    "title": "MySQL Server",
                    "value": query['mysql_host'],
                    "short": True
                },
                {
                    "title": "Database",
                    "value": query['mysql_database'],
                    "short": True
                },
                {
                    "title": "Result",
                    "value": "```{}```".format(rows),
                    "short": False
                },
            ],
            "fallback": str(result)
        })
    except:
        logging.exception(json.dumps({'action': 'formatting results', 'status': 'failed'}))
    else:
        logging.debug(json.dumps({'action': 'formatting results', 'status': 'success', 'attachments': attachments}))

    body = {
        "response_type": "in_channel",
        "attachments": attachments
    }
    response = format_response(body)
    return response


class MissingAliasTest(unittest.TestCase):
    def setUp(self):
        logging.debug(json.dumps({"action": "setting up new test MissingAliasTest"}))
        event = {
            'resource': '/command',
            'path': '/command',
            'httpMethod': 'POST',
            'headers': {
                'Accept': 'application/json,*/*',
                'Accept-Encoding': 'gzip,deflate',
                'CloudFront-Forwarded-Proto': 'https',
                'CloudFront-Is-Desktop-Viewer': 'true',
                'CloudFront-Is-Mobile-Viewer': 'false',
                'CloudFront-Is-SmartTV-Viewer': 'false',
                'CloudFront-Is-Tablet-Viewer': 'false',
                'CloudFront-Viewer-Country': 'US',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Host': '8bixd3am45.execute-api.ap-southeast-2.amazonaws.com',
                'User-Agent': 'Slackbot 1.0 (+https://api.slack.com/robots)',
                'Via': '1.1 a0dce0e49d06dce2c392604440772209.cloudfront.net (CloudFront)',
                'X-Amz-Cf-Id': 'TL3kJqaV6y7kXC6hkru8zOJZzGXBX13rQ-0tc34hlabd-K18qKLVFg==',
                'X-Amzn-Trace-Id': 'Root=1-59b4e895-024869162e9972bf6b358970',
                'X-Forwarded-For': '54.209.231.248, 54.182.230.57',
                'X-Forwarded-Port': '443',
                'X-Forwarded-Proto': 'https'},
            'queryStringParameters': None,
            'pathParameters': None,
            'stageVariables': None,
            'requestContext': {
                'path': '/Devaaron/command',
                'accountId': '979598289034',
                'resourceId': 'i5luku',
                'stage': 'Devaaron',
                'requestId': '071aeddc-95f9-11e7-8cd9-7ff34cfce32b',
                'identity': {
                    'cognitoIdentityPoolId': None,
                    'accountId': None,
                    'cognitoIdentityId': None,
                    'caller': None,
                    'apiKey': '',
                    'sourceIp': '54.209.231.248',
                    'accessKey': None,
                    'cognitoAuthenticationType': None,
                    'cognitoAuthenticationProvider': None,
                    'userArn': None,
                    'userAgent': 'Slackbot 1.0 (+https://api.slack.com/robots)',
                    'user': None},
                'resourcePath': '/command',
                'httpMethod': 'POST',
                'apiId': '8bixd3am45'},
            'body': urlencode({
                'token': 'UKN4Z6UE5',
                'team_id': 'T704EFPPF',
                'team_domain': 'aarongorka',
                'channel_id': 'C704EFSF7',
                'channel_name': 'general',
                'user_id': 'U6ZAMUH7S',
                'user_name': 'aarongorka',
                'command': '/sql',
                'text': 'missingalias',
                'response_url': 'https://hooks.slack.com/commands/T704EFPPF/239872535367/4ERft7zrhxf5c0YtZpWSXeqk',
                'trigger_id': 'MissingAliasTest'}),
            'isBase64Encoded': False}
        self.response = handler(event, {})
        self.body = json.loads(self.response['body'])

    def test_response(self):
        self.assertEqual(self.response['statusCode'], 200)

    def test_text(self):
        self.assertEqual(self.body['text'], 'The alias `missingalias` doesn\'t exist. Here are the available aliases you may call:')

    def test_field_0(self):
        attachments = self.body['attachments']
        fields = [x["fields"] for x in attachments]
        logging.debug(json.dumps({'fields': fields}))
        titles = [x[0]["title"] for x in fields]
        logging.debug(json.dumps({'titles': titles}))
        values = [x[0]["value"] for x in fields]
        logging.debug(json.dumps({'values': values}))

        self.assertTrue("Alias" in titles)
        self.assertTrue("getemployees" in values)


class InvalidMessageTest(unittest.TestCase):
    def setUp(self):
        event = {
            'resource': '/command',
            'path': '/command',
            'httpMethod': 'POST',
            'headers': {
                'Accept': 'application/json,*/*',
                'Accept-Encoding': 'gzip,deflate',
                'CloudFront-Forwarded-Proto': 'https',
                'CloudFront-Is-Desktop-Viewer': 'true',
                'CloudFront-Is-Mobile-Viewer': 'false',
                'CloudFront-Is-SmartTV-Viewer': 'false',
                'CloudFront-Is-Tablet-Viewer': 'false',
                'CloudFront-Viewer-Country': 'US',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Host': '8bixd3am45.execute-api.ap-southeast-2.amazonaws.com',
                'User-Agent': 'Slackbot 1.0 (+https://api.slack.com/robots)',
                'Via': '1.1 a0dce0e49d06dce2c392604440772209.cloudfront.net (CloudFront)',
                'X-Amz-Cf-Id': 'TL3kJqaV6y7kXC6hkru8zOJZzGXBX13rQ-0tc34hlabd-K18qKLVFg==',
                'X-Amzn-Trace-Id': 'Root=1-59b4e895-024869162e9972bf6b358970',
                'X-Forwarded-For': '54.209.231.248, 54.182.230.57',
                'X-Forwarded-Port': '443',
                'X-Forwarded-Proto': 'https'},
            'queryStringParameters': None,
            'pathParameters': None,
            'stageVariables': None,
            'requestContext': {
                'path': '/Devaaron/command',
                'accountId': '979598289034',
                'resourceId': 'i5luku',
                'stage': 'Devaaron',
                'requestId': '071aeddc-95f9-11e7-8cd9-7ff34cfce32b',
                'identity': {
                    'cognitoIdentityPoolId': None,
                    'accountId': None,
                    'cognitoIdentityId': None,
                    'caller': None,
                    'apiKey': '',
                    'sourceIp': '54.209.231.248',
                    'accessKey': None,
                    'cognitoAuthenticationType': None,
                    'cognitoAuthenticationProvider': None,
                    'userArn': None,
                    'userAgent': 'Slackbot 1.0 (+https://api.slack.com/robots)',
                    'user': None},
                'resourcePath': '/command',
                'httpMethod': 'POST',
                'apiId': '8bixd3am45'},
            'body': 'Invaild body',
            'isBase64Encoded': False}
        logging.debug(json.dumps({"action": "setting up new test InvalidMessageTest"}))
        self.response = handler(event, {})

    def test_response(self):
        self.assertEqual(self.response['statusCode'], 503)


class ValidAliasTest(unittest.TestCase):
    def setUp(self):
        event = {
            'resource': '/command',
            'path': '/command',
            'httpMethod': 'POST',
            'headers': {
                'Accept': 'application/json,*/*',
                'Accept-Encoding': 'gzip,deflate',
                'CloudFront-Forwarded-Proto': 'https',
                'CloudFront-Is-Desktop-Viewer': 'true',
                'CloudFront-Is-Mobile-Viewer': 'false',
                'CloudFront-Is-SmartTV-Viewer': 'false',
                'CloudFront-Is-Tablet-Viewer': 'false',
                'CloudFront-Viewer-Country': 'US',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Host': '8bixd3am45.execute-api.ap-southeast-2.amazonaws.com',
                'User-Agent': 'Slackbot 1.0 (+https://api.slack.com/robots)',
                'Via': '1.1 a0dce0e49d06dce2c392604440772209.cloudfront.net (CloudFront)',
                'X-Amz-Cf-Id': 'TL3kJqaV6y7kXC6hkru8zOJZzGXBX13rQ-0tc34hlabd-K18qKLVFg==',
                'X-Amzn-Trace-Id': 'Root=1-59b4e895-024869162e9972bf6b358970',
                'X-Forwarded-For': '54.209.231.248, 54.182.230.57',
                'X-Forwarded-Port': '443',
                'X-Forwarded-Proto': 'https'},
            'queryStringParameters': None,
            'pathParameters': None,
            'stageVariables': None,
            'requestContext': {
                'path': '/Devaaron/command',
                'accountId': '979598289034',
                'resourceId': 'i5luku',
                'stage': 'Devaaron',
                'requestId': '071aeddc-95f9-11e7-8cd9-7ff34cfce32b',
                'identity': {
                    'cognitoIdentityPoolId': None,
                    'accountId': None,
                    'cognitoIdentityId': None,
                    'caller': None,
                    'apiKey': '',
                    'sourceIp': '54.209.231.248',
                    'accessKey': None,
                    'cognitoAuthenticationType': None,
                    'cognitoAuthenticationProvider': None,
                    'userArn': None,
                    'userAgent': 'Slackbot 1.0 (+https://api.slack.com/robots)',
                    'user': None},
                'resourcePath': '/command',
                'httpMethod': 'POST',
                'apiId': '8bixd3am45'},
            'body': urlencode({
                'token': 'UKN4Z6UE5',
                'team_id': 'T704EFPPF',
                'team_domain': 'aarongorka',
                'channel_id': 'C704EFSF7',
                'channel_name': 'general',
                'user_id': 'U6ZAMUH7S',
                'user_name': 'aarongorka',
                'command': '/sql',
                'text': 'getemployees',
                'response_url': 'https://hooks.slack.com/commands/T704EFPPF/239872535367/4ERft7zrhxf5c0YtZpWSXeqk',
                'trigger_id': 'ValidAliasTest'}),
            'isBase64Encoded': False}
        logging.debug(json.dumps({"action": "setting up new test ValidAliasTest"}))
        self.response = handler(event, {})
        self.body = json.loads(self.response['body'])

    def test_response(self):
        self.assertEqual(self.response['statusCode'], 200)

    def test_text(self):
        attachments = self.body['attachments']
        fields = [x["fields"] for x in attachments]
        logging.debug(json.dumps({'fields': fields, 'action': 'logging fields'}))
        titles = [x["title"] for x in fields[0]]
        logging.debug(json.dumps({'titles': titles, 'action': 'logging titles'}))
        values = [x["value"] for x in fields[0]]
        logging.debug(json.dumps({'values': values, 'action': 'logging values'}))

        self.assertTrue("Result" in titles)
        self.assertTrue("Nagasaki" in str(values))


class ValidAliasInvalidQueryTest(unittest.TestCase):
    def setUp(self):
        event = {
            'resource': '/command',
            'path': '/command',
            'httpMethod': 'POST',
            'headers': {
                'Accept': 'application/json,*/*',
                'Accept-Encoding': 'gzip,deflate',
                'CloudFront-Forwarded-Proto': 'https',
                'CloudFront-Is-Desktop-Viewer': 'true',
                'CloudFront-Is-Mobile-Viewer': 'false',
                'CloudFront-Is-SmartTV-Viewer': 'false',
                'CloudFront-Is-Tablet-Viewer': 'false',
                'CloudFront-Viewer-Country': 'US',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Host': '8bixd3am45.execute-api.ap-southeast-2.amazonaws.com',
                'User-Agent': 'Slackbot 1.0 (+https://api.slack.com/robots)',
                'Via': '1.1 a0dce0e49d06dce2c392604440772209.cloudfront.net (CloudFront)',
                'X-Amz-Cf-Id': 'TL3kJqaV6y7kXC6hkru8zOJZzGXBX13rQ-0tc34hlabd-K18qKLVFg==',
                'X-Amzn-Trace-Id': 'Root=1-59b4e895-024869162e9972bf6b358970',
                'X-Forwarded-For': '54.209.231.248, 54.182.230.57',
                'X-Forwarded-Port': '443',
                'X-Forwarded-Proto': 'https'},
            'queryStringParameters': None,
            'pathParameters': None,
            'stageVariables': None,
            'requestContext': {
                'path': '/Devaaron/command',
                'accountId': '979598289034',
                'resourceId': 'i5luku',
                'stage': 'Devaaron',
                'requestId': '071aeddc-95f9-11e7-8cd9-7ff34cfce32b',
                'identity': {
                    'cognitoIdentityPoolId': None,
                    'accountId': None,
                    'cognitoIdentityId': None,
                    'caller': None,
                    'apiKey': '',
                    'sourceIp': '54.209.231.248',
                    'accessKey': None,
                    'cognitoAuthenticationType': None,
                    'cognitoAuthenticationProvider': None,
                    'userArn': None,
                    'userAgent': 'Slackbot 1.0 (+https://api.slack.com/robots)',
                    'user': None},
                'resourcePath': '/command',
                'httpMethod': 'POST',
                'apiId': '8bixd3am45'},
            'body': urlencode({
                'token': 'UKN4Z6UE5',
                'team_id': 'T704EFPPF',
                'team_domain': 'aarongorka',
                'channel_id': 'C704EFSF7',
                'channel_name': 'general',
                'user_id': 'U6ZAMUH7S',
                'user_name': 'aarongorka',
                'command': '/sql',
                'text': 'invalidquery',
                'response_url': 'https://hooks.slack.com/commands/T704EFPPF/239872535367/4ERft7zrhxf5c0YtZpWSXeqk',
                'trigger_id': 'ValidAliasInvalidQueryTest'}),
            'isBase64Encoded': False}
        logging.debug(json.dumps({"action": "setting up new test ValidAliasInvalidQueryTest"}))
        self.response = handler(event, {})
        self.body = json.loads(self.response['body'])

    def test_response(self):
        self.assertEqual(self.response['statusCode'], 200)

    def test_text(self):
        self.assertEqual(self.body['text'], 'The SQL query failed, please check the logs for more information')


class MysqlConnectivityTest(unittest.TestCase):
    def test_connectivity(self):
        logging.debug(json.dumps({"action": "starting new test MysqlConnectivityTest"}))
        start = timer()
        attempts = 0
        connected = False
        while not connected:
            try:
                logging.debug(json.dumps({"action": "trying to connect to MySQL"}))
                cnx = mysql.connector.connect(
                    connect_timeout=20,
                    user=os.environ['MYSQL_USER'],
                    password=os.environ['MYSQL_PASSWORD'],
                    database=os.environ['MYSQL_DATABASE'],
                    host="db"
                )
                connected = True
            except mysql.connector.errors.InterfaceError:
                elapsed = timer() - start
                logging.info(json.dumps({"action": "connect to mysql", "status": "failed", "attempts": attempts, "elapsed": elapsed}))
                if elapsed > 10 or attempts > 5:
                    logging.exception("Failed to connect to MySQL database")
                    raise
                attempts += 1
            logging.debug(json.dumps({"action": "sleeping"}))
            time.sleep(1)
        try:
            cnx.close()
        except:
            logging.exception(json.dumps({'action': 'disconnect from MySQL', 'status': 'failed'}))
            raise


def main():
    aws_lambda_logging.setup(level=os.environ.get('LOGLEVEL', 'INFO'), env=os.environ.get('ENV'), timestamp=int(time.time()))
    aws_lambda_logging.setup(level=os.environ.get('LOGLEVEL', 'INFO'), env=os.environ.get('ENV'), timestamp=int(time.time()))
    unittest.main()
#        suite = unittest.TestLoader().loadTestsFromTestCase(FunctionTests)
#        unittest.TextTestRunner().run(suite)

#    unittest.main()

if __name__ == '__main__':
    main()

"""
#    suite = unittest.TestLoader().loadTestsFromTestCase(MysqlConnectivityTest)
#    unittest.TextTestRunner().run(suite)
"""
