#!/usr/bin/env python3
import os
import logging
import aws_lambda_logging
import json
import re
import ruamel.yaml as yaml
import mysql.connector
from urllib.parse import urlparse, parse_qs


def handler(event, context):
    """Main entrypoint"""

    loglevel = os.environ.get('LOGLEVEL', 'INFO')
    logging.debug('.(setup) #1')
    aws_lambda_logging.setup(level=loglevel)
    logging.debug('.(setup) #2')
    aws_lambda_logging.setup(level=loglevel)  # for some reason you have to do setup twice
    try:
        env = os.environ.get('ENV')
        aws_lambda_logging.setup(env=env)
    except:
        pass
    logging.debug('Dumping event #1...')
    logging.debug(json.dumps({'event': event}))
    logging.debug('Dumping event #2...')

    body = parse_qs(event['body'])

    logging.debug(json.dumps({'body': body}))

    try:
        correlation_id = body['trigger_id'][0]  # Use correlation ID from Slack
        logging.debug(json.dumps({'correlation_id': correlation_id}))
        aws_lambda_logging.setup(correlation_id=correlation_id)
    except:
        pass

    with open("example.yml") as stream:
        try:
            config = yaml.safe_load(stream)
            logging.debug(json.dumps({'config': config}))
        except yaml.YAMLError as e:
            logging.exception(json.dumps({'action': 'load yaml', 'status': 'failed', 'error': str(e)}))

    user_selection = body['text'][0]

    query = retrieve_query(config, user_selection)

    if query:
        try:
            result = run_query(query)
        except Exception as e:
            logging.exception(json.dumps({'action': 'running SQL query', 'status': 'failed', 'error': str(e)}))
    
        body = ""
        try:
            body = format_result(result)
        except Exception as e:
            logging.exception(json.dumps({'action': 'formatting response', 'status': 'failed', 'error': str(e)}))
    else:
        attachments = format_attachments(config['queries'])
        body = {
            "response_type": "in_channel",
            "text": "The alias `{}` doesn't exist. Here are the available aliases you may call:".format(user_selection),
            "attachments": attachments
        }

    response = {
        "statusCode": 200,
        "body": json.dumps(body),
        'headers': {
            'Content-Type': 'application/json',
        }
    }
        
    logging.info(json.dumps({'action': 'responding', 'response': response}))
    return response

def retrieve_query(config, user_selection):
    """Checks that the user's selection exists in the configuration file and returns the data associated with it"""

    for alias in config['queries']:
        if alias == user_selection:
            query = [ x for x in config if config['queries'] == alias ]
            return query
    else:
        logging.debug(json.dumps('The selection the user has made does not exist in the configuration file'))
        return None

def format_attachments(queries):
    """Formats all available queries as a Slack attachment, returns an attachments object"""

    attachments = []
    for query in queries:
        attachments.append({
            "color": "#36a64f",
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
                    "title": "Button",
                    "value": "TODO",  # TODO
                    "short": True
                }
            ],
            "fallback": "alias: {}, statement: {}".format(query['alias'], query['sql'])
        })
    logging.debug(json.dumps({'attachments': attachments}))
    return attachments


def run_query(query):
    """Takes a query from the configuration file, executes it and returns the result"""

    try:
        cnx = mysql.connector.connect(
        user=os.environ['MYSQL_USER'], 
        password=os.environ['MYSQL_PASSWORD'], 
        database=query['mysql_host'], 
        host=query['mysql_host'])
    except:
        logging.exception("Failed to connect to MySQL database")
    cur = cnx.cursor(buffered=True)
    cur.execute(query['sql'])
    result = cur.fetchall()
    return result


def format_result(result):
    """Formats the query results in to a format accepted by Slack"""
    body = "```{}```".format(result)  # Add results as preformatted string
    return body


def main():
    handler(json.loads('{"resource": "/hello", "path": "/hello", "httpMethod": "POST", "headers": {"Accept": "application/json,*/*", "Accept-Encoding": "gzip,deflate", "CloudFront-Forwarded-Proto": "https", "CloudFront-Is-Desktop-Viewer": "true", "CloudFront-Is-Mobile-Viewer": "false", "CloudFront-Is-SmartTV-Viewer": "false", "CloudFront-Is-Tablet-Viewer": "false", "CloudFront-Viewer-Country": "US", "Content-Type": "application/x-www-form-urlencoded", "Host": "foobar.execute-api.ap-southeast-2.amazonaws.com", "User-Agent": "Slackbot 1.0 (+https://api.slack.com/robots)", "Via": "1.1 foobar.cloudfront.net (CloudFront)", "X-Amz-Cf-Id": "foobar", "X-Amzn-Trace-Id": "Root=footraceidbar", "X-Forwarded-For": "0.123.456.789, 0.123.456.789", "X-Forwarded-Port": "443", "X-Forwarded-Proto": "https"}, "queryStringParameters": null, "pathParameters": null, "stageVariables": null, "requestContext": {"path": "/Devaaron/hello", "accountId": "01234556678", "resourceId": "2345sd", "stage": "Devaaron", "requestId": "uuid", "identity": {"cognitoIdentityPoolId": null, "accountId": null, "cognitoIdentityId": null, "caller": null, "apiKey": "", "sourceIp": "0.123.345.123", "accessKey": null, "cognitoAuthenticationType": null, "cognitoAuthenticationProvider": null, "userArn": null, "userAgent": "Slackbot 1.0 (+https://api.slack.com/robots)", "user": null}, "resourcePath": "/hello", "httpMethod": "POST", "apiId": "asdfasd"}, "body": "token=3452345asdf&team_id=SDFSDFSDF&team_domain=asdfaq345&channel_id=345asdf&channel_name=general&user_id=2345asdfas&user_name=2345asdf&command=%2Fsql&text=asdf&response_url=https%3A%2F%2Fhooks.slack.com%2Fcommands%asdfasdf&trigger_id=asdfqw45qwefasdf", "isBase64Encoded": false}'), {})

if __name__ == '__main__': main()
