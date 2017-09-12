#!/usr/bin/env python3
import os
import logging
import aws_lambda_logging
import json
import re
import ruamel.yaml as yaml
import mysql.connector
from urllib.parse import urlparse, parse_qs
import unittest


def button_handler(event, context):
    """Handler for button events"""

    loglevel = os.environ.get('LOGLEVEL', 'INFO')
    aws_lambda_logging.setup(level=loglevel, env=os.environ.get('ENV'))
    logging.debug(json.dumps({'action': 'initialising'}))
    logging.debug(json.dumps({'event': event}))

    try:
        body = parse_qs(event['body'])
        payload = json.loads(body['payload'][0])
    except Exception as e:
        logging.exception(json.dumps({'action': 'parse payload', 'status': 'failed'}))
        raise
    else:
        logging.debug(json.dumps({'action': 'parse payload', 'status': 'success', 'payload': payload}))

    correlation_id = payload['trigger_id']  # Use correlation ID from Slack
    logging.debug(json.dumps({'correlation_id': correlation_id}))
    aws_lambda_logging.setup(level=loglevel, env=os.environ.get('ENV'), correlation_id=correlation_id)

    selected_alias = payload['actions'][0]['value']
    logging.debug(json.dumps({'selected_alias': selected_alias}))

    response = lookup_alias_and_execute(selected_alias)

    logging.info(json.dumps({'action': 'responding', 'response': response}))
    return response


def handler(event, context):
    """Main entrypoint"""

    loglevel = os.environ.get('LOGLEVEL', 'INFO')
    aws_lambda_logging.setup(level=loglevel, env=os.environ.get('ENV'))
    logging.debug(json.dumps({'action': 'initialising'}))
    logging.debug(json.dumps({'event': event}))

    try:
        body = parse_qs(event['body'])
    except Exception as e:
        logging.exception(json.dumps({'action': 'parse body', 'status': 'failed'}))
        raise
    else:
        logging.debug(json.dumps({'action': 'parse body', 'status': 'success', 'body': body}))

    correlation_id = body['trigger_id'][0]  # Use correlation ID from Slack
    logging.debug(json.dumps({'correlation_id': correlation_id}))
    aws_lambda_logging.setup(level=loglevel, env=os.environ.get('ENV'), correlation_id=correlation_id)

    try:
        selected_alias = body['text'][0]
    except KeyError as e:
        logging.exception(json.dumps({'action': 'get selected_alias', 'status': 'failed'}))
        response = {
            "statusCode": 503,
            "body": json.dumps({"text": "Failed to validate user's selected alias"}),
            'headers': {
                'Content-Type': 'application/json',
            }
        }
        return response
    else:
        logging.debug(json.dumps({'action': 'get selected_alias', 'status': 'success', 'selected_alias': selected_alias}))

    # response = lookup_alias_and_execute(selected_alias)
    try:
        response = lookup_alias_and_execute(selected_alias)
    except mysql.connector.errors.InterfaceError:
        response = {
            "statusCode": 503,
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
            logging.debug(json.dumps({'config': config}))
        except yaml.YAMLError as e:
            logging.exception(json.dumps({'action': 'load yaml', 'status': 'failed', 'error': str(e)}))
            raise
        else:
            logging.debug(json.dumps({'action': 'load yaml', 'status': 'success'}))
    return config


def lookup_alias_and_execute(selected_alias):
    """Executes a user's selected alias by looking up details from the config file, returns a message that can be returned to Slack"""

    config = get_config()
    query = get_query_details(config, selected_alias)

    if query == "missing_alias":
        response = missing_alias_message(config['queries'], selected_alias)
    else:
        result = run_query(query)
        response = format_query_result(result, query)
    return response


def get_query_details(config, selected_alias):
    """Checks that the user's selection exists in the configuration file and returns the data associated with it"""

    for query in config['queries']:
        if query['alias'] == selected_alias:
            return query
    else:
        logging.debug(json.dumps('The selection the user has made does not exist in the configuration file'))
        return "missing_alias"


def missing_alias_message(queries, selected_alias):
    """Returns a mesage about the alias missing and provides valid aliases to execute"""

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
    logging.debug(json.dumps({'attachments': attachments}))

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

    try:
        cnx = mysql.connector.connect(
            user=os.environ['MYSQL_USER'],
            password=os.environ['MYSQL_PASSWORD'],
            database=query['mysql_host'],
            host=query['mysql_host']
        )
    except:
        logging.exception("Failed to connect to MySQL database")
        raise
    cur = cnx.cursor(buffered=True)
    cur.execute(query['sql'])
    result = cur.fetchall()
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


def format_query_result(result, query):
    """Formats the query results in to a format accepted by Slack"""

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
                "value": "```{}```".format(result),
                "short": False
            },

        ],
        "fallback": result
    })
    logging.debug(json.dumps({'attachments': attachments}))

    body = {
        "response_type": "in_channel",
        "attachments": attachments
    }
    response = format_response(body)
    return response


class MissingAliasTest(unittest.TestCase):
    def setUp(self):
        event = json.loads('{"resource": "/command", "path": "/command", "httpMethod": "POST", "headers": {"Accept": "application/json,*/*", "Accept-Encoding": "gzip,deflate", "CloudFront-Forwarded-Proto": "https", "CloudFront-Is-Desktop-Viewer": "true", "CloudFront-Is-Mobile-Viewer": "false", "CloudFront-Is-SmartTV-Viewer": "false", "CloudFront-Is-Tablet-Viewer": "false", "CloudFront-Viewer-Country": "US", "Content-Type": "application/x-www-form-urlencoded", "Host": "8bixd3am45.execute-api.ap-southeast-2.amazonaws.com", "User-Agent": "Slackbot 1.0 (+https://api.slack.com/robots)", "Via": "1.1 a0dce0e49d06dce2c392604440772209.cloudfront.net (CloudFront)", "X-Amz-Cf-Id": "TL3kJqaV6y7kXC6hkru8zOJZzGXBX13rQ-0tc34hlabd-K18qKLVFg==", "X-Amzn-Trace-Id": "Root=1-59b4e895-024869162e9972bf6b358970", "X-Forwarded-For": "54.209.231.248, 54.182.230.57", "X-Forwarded-Port": "443", "X-Forwarded-Proto": "https"}, "queryStringParameters": null, "pathParameters": null, "stageVariables": null, "requestContext": {"path": "/Devaaron/command", "accountId": "979598289034", "resourceId": "i5luku", "stage": "Devaaron", "requestId": "071aeddc-95f9-11e7-8cd9-7ff34cfce32b", "identity": {"cognitoIdentityPoolId": null, "accountId": null, "cognitoIdentityId": null, "caller": null, "apiKey": "", "sourceIp": "54.209.231.248", "accessKey": null, "cognitoAuthenticationType": null, "cognitoAuthenticationProvider": null, "userArn": null, "userAgent": "Slackbot 1.0 (+https://api.slack.com/robots)", "user": null}, "resourcePath": "/command", "httpMethod": "POST", "apiId": "8bixd3am45"}, "body": "token=UKN4Z6UE5&team_id=T704EFPPF&team_domain=aarongorka&channel_id=C704EFSF7&channel_name=general&user_id=U6ZAMUH7S&user_name=aarongorka&command=%2Fsql&text=asdf&response_url=https%3A%2F%2Fhooks.slack.com%2Fcommands%2FT704EFPPF%2F239872535367%2F4ERft7zrhxf5c0YtZpWSXeqk&trigger_id=238782064146.238150533797.a27946fa50d0c893cbeaf6c4d90ea9d0", "isBase64Encoded": false}')
        self.response = handler(event, {})
        self.body = json.loads(self.response['body'])

    def test_response(self):
        self.assertEqual(self.response['statusCode'], 200)

    def test_text(self):
        self.assertEqual(self.body['text'], 'The alias `asdf` doesn\'t exist. Here are the available aliases you may call:')

    def test_field_0(self):
        attachments = self.body['attachments']
        self.assertEqual(attachments[0]["fields"][0]['title'], "Alias")
        self.assertEqual(attachments[0]["fields"][0]['value'], "getstats")


class InvalidMessageTest(unittest.TestCase):
    def setUp(self):
        event = json.loads('{"resource": "/command", "path": "/command", "httpMethod": "POST", "headers": {"Accept": "application/json,*/*", "Accept-Encoding": "gzip,deflate", "CloudFront-Forwarded-Proto": "https", "CloudFront-Is-Desktop-Viewer": "true", "CloudFront-Is-Mobile-Viewer": "false", "CloudFront-Is-SmartTV-Viewer": "false", "CloudFront-Is-Tablet-Viewer": "false", "CloudFront-Viewer-Country": "US", "Content-Type": "application/x-www-form-urlencoded", "Host": "8bixd3am45.execute-api.ap-southeast-2.amazonaws.com", "User-Agent": "Slackbot 1.0 (+https://api.slack.com/robots)", "Via": "1.1 a0dce0e49d06dce2c392604440772209.cloudfront.net (CloudFront)", "X-Amz-Cf-Id": "TL3kJqaV6y7kXC6hkru8zOJZzGXBX13rQ-0tc34hlabd-K18qKLVFg==", "X-Amzn-Trace-Id": "Root=1-59b4e895-024869162e9972bf6b358970", "X-Forwarded-For": "54.209.231.248, 54.182.230.57", "X-Forwarded-Port": "443", "X-Forwarded-Proto": "https"}, "queryStringParameters": null, "pathParameters": null, "stageVariables": null, "requestContext": {"path": "/Devaaron/command", "accountId": "979598289034", "resourceId": "i5luku", "stage": "Devaaron", "requestId": "071aeddc-95f9-11e7-8cd9-7ff34cfce32b", "identity": {"cognitoIdentityPoolId": null, "accountId": null, "cognitoIdentityId": null, "caller": null, "apiKey": "", "sourceIp": "54.209.231.248", "accessKey": null, "cognitoAuthenticationType": null, "cognitoAuthenticationProvider": null, "userArn": null, "userAgent": "Slackbot 1.0 (+https://api.slack.com/robots)", "user": null}, "resourcePath": "/command", "httpMethod": "POST", "apiId": "8bixd3am45"}, "body": "token=UKN4Z6UE5&team_id=T704EFPPF&team_domain=aarongorka&channel_id=C704EFSF7&channel_name=general&user_id=U6ZAMUH7S&user_name=aarongorka&command=%2Fsql&text=&response_url=https%3A%2F%2Fhooks.slack.com%2Fcommands%2FT704EFPPF%2F239872535367%2F4ERft7zrhxf5c0YtZpWSXeqk&trigger_id=238782064146.238150533797.a27946fa50d0c893cbeaf6c4d90ea9d0", "isBase64Encoded": false}')
        self.response = handler(event, {})
        self.body = json.loads(self.response['body'])

    def test_response(self):
        self.assertEqual(self.response['statusCode'], 503)


class ValidAliasTest(unittest.TestCase):
    def setUp(self):
        event = json.loads('{"resource": "/command", "path": "/command", "httpMethod": "POST", "headers": {"Accept": "application/json,*/*", "Accept-Encoding": "gzip,deflate", "CloudFront-Forwarded-Proto": "https", "CloudFront-Is-Desktop-Viewer": "true", "CloudFront-Is-Mobile-Viewer": "false", "CloudFront-Is-SmartTV-Viewer": "false", "CloudFront-Is-Tablet-Viewer": "false", "CloudFront-Viewer-Country": "US", "Content-Type": "application/x-www-form-urlencoded", "Host": "8bixd3am45.execute-api.ap-southeast-2.amazonaws.com", "User-Agent": "Slackbot 1.0 (+https://api.slack.com/robots)", "Via": "1.1 a0dce0e49d06dce2c392604440772209.cloudfront.net (CloudFront)", "X-Amz-Cf-Id": "TL3kJqaV6y7kXC6hkru8zOJZzGXBX13rQ-0tc34hlabd-K18qKLVFg==", "X-Amzn-Trace-Id": "Root=1-59b4e895-024869162e9972bf6b358970", "X-Forwarded-For": "54.209.231.248, 54.182.230.57", "X-Forwarded-Port": "443", "X-Forwarded-Proto": "https"}, "queryStringParameters": null, "pathParameters": null, "stageVariables": null, "requestContext": {"path": "/Devaaron/command", "accountId": "979598289034", "resourceId": "i5luku", "stage": "Devaaron", "requestId": "071aeddc-95f9-11e7-8cd9-7ff34cfce32b", "identity": {"cognitoIdentityPoolId": null, "accountId": null, "cognitoIdentityId": null, "caller": null, "apiKey": "", "sourceIp": "54.209.231.248", "accessKey": null, "cognitoAuthenticationType": null, "cognitoAuthenticationProvider": null, "userArn": null, "userAgent": "Slackbot 1.0 (+https://api.slack.com/robots)", "user": null}, "resourcePath": "/command", "httpMethod": "POST", "apiId": "8bixd3am45"}, "body": "token=UKN4Z6UE5&team_id=T704EFPPF&team_domain=aarongorka&channel_id=C704EFSF7&channel_name=general&user_id=U6ZAMUH7S&user_name=aarongorka&command=%2Fsql&text=getemployees&response_url=https%3A%2F%2Fhooks.slack.com%2Fcommands%2FT704EFPPF%2F239872535367%2F4ERft7zrhxf5c0YtZpWSXeqk&trigger_id=238782064146.238150533797.a27946fa50d0c893cbeaf6c4d90ea9d0", "isBase64Encoded": false}')
        self.response = handler(event, {})
        self.body = json.loads(self.response['body'])

    def test_response(self):
        self.assertEqual(self.response['statusCode'], 200)

    def test_text(self):
        self.assertEqual(self.body['text'], 'The alias `asdf` doesn\'t exist. Here are the available aliases you may call:')

    def test_field_0(self):
        attachments = self.body['attachments']
        self.assertEqual(attachments[0]["fields"][0]['title'], "Alias")
        self.assertEqual(attachments[0]["fields"][0]['value'], "getstats")


class ValidAliasInvalidQueryTest(unittest.TestCase):
    def setUp(self):
        event = json.loads('{"resource": "/command", "path": "/command", "httpMethod": "POST", "headers": {"Accept": "application/json,*/*", "Accept-Encoding": "gzip,deflate", "CloudFront-Forwarded-Proto": "https", "CloudFront-Is-Desktop-Viewer": "true", "CloudFront-Is-Mobile-Viewer": "false", "CloudFront-Is-SmartTV-Viewer": "false", "CloudFront-Is-Tablet-Viewer": "false", "CloudFront-Viewer-Country": "US", "Content-Type": "application/x-www-form-urlencoded", "Host": "8bixd3am45.execute-api.ap-southeast-2.amazonaws.com", "User-Agent": "Slackbot 1.0 (+https://api.slack.com/robots)", "Via": "1.1 a0dce0e49d06dce2c392604440772209.cloudfront.net (CloudFront)", "X-Amz-Cf-Id": "TL3kJqaV6y7kXC6hkru8zOJZzGXBX13rQ-0tc34hlabd-K18qKLVFg==", "X-Amzn-Trace-Id": "Root=1-59b4e895-024869162e9972bf6b358970", "X-Forwarded-For": "54.209.231.248, 54.182.230.57", "X-Forwarded-Port": "443", "X-Forwarded-Proto": "https"}, "queryStringParameters": null, "pathParameters": null, "stageVariables": null, "requestContext": {"path": "/Devaaron/command", "accountId": "979598289034", "resourceId": "i5luku", "stage": "Devaaron", "requestId": "071aeddc-95f9-11e7-8cd9-7ff34cfce32b", "identity": {"cognitoIdentityPoolId": null, "accountId": null, "cognitoIdentityId": null, "caller": null, "apiKey": "", "sourceIp": "54.209.231.248", "accessKey": null, "cognitoAuthenticationType": null, "cognitoAuthenticationProvider": null, "userArn": null, "userAgent": "Slackbot 1.0 (+https://api.slack.com/robots)", "user": null}, "resourcePath": "/command", "httpMethod": "POST", "apiId": "8bixd3am45"}, "body": "token=UKN4Z6UE5&team_id=T704EFPPF&team_domain=aarongorka&channel_id=C704EFSF7&channel_name=general&user_id=U6ZAMUH7S&user_name=aarongorka&command=%2Fsql&text=invalidquery&response_url=https%3A%2F%2Fhooks.slack.com%2Fcommands%2FT704EFPPF%2F239872535367%2F4ERft7zrhxf5c0YtZpWSXeqk&trigger_id=238782064146.238150533797.a27946fa50d0c893cbeaf6c4d90ea9d0", "isBase64Encoded": false}')
        self.response = handler(event, {})
        self.body = json.loads(self.response['body'])

    def test_response(self):
        self.assertEqual(self.response['statusCode'], 503)

    def test_text(self):
        self.assertEqual(self.body['text'], 'Failed to execute MySQL query')

if __name__ == '__main__':
    unittest.main()

if __name__ == '__main__':
    main()
