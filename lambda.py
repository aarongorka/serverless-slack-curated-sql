#!/usr/bin/env python3
import os
import logging
import aws_lambda_logging
import json
import re
import ruamel.yaml as yaml
import mysql.connector
from urllib.parse import urlparse, parse_qs


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
        logging.exception(json.dumps({'action': 'parse payload', 'status': 'failed', 'error': str(e)}))
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
        logging.exception(json.dumps({'action': 'parse body', 'status': 'failed', 'error': str(e)}))
    else:
        logging.debug(json.dumps({'action': 'parse body', 'status': 'success', 'body': body}))

    correlation_id = body['trigger_id'][0]  # Use correlation ID from Slack
    logging.debug(json.dumps({'correlation_id': correlation_id}))
    aws_lambda_logging.setup(level=loglevel, env=os.environ.get('ENV'), correlation_id=correlation_id)

    message_type = categorise_message(body)
    logging.debug(json.dumps({'message type': message_type}))

    if body.get('text'):
        try:
            selected_alias = body['text'][0]
        except KeyError as e:
            logging.exception(json.dumps({'action': 'get selected_alias', 'status': 'failed', 'error': str(e)}))
        else:
            logging.debug(json.dumps({'action': 'get selected_alias', 'status': 'success'}))
    elif body.get('actions'):
        selected_alias = body['actions'][0]['value']

    response = lookup_alias_and_execute(selected_alias)

    logging.info(json.dumps({'action': 'responding', 'response': response}))
    return response


def get_config():
    with open("example.yml") as stream:
        try:
            config = yaml.safe_load(stream)
            logging.debug(json.dumps({'config': config}))
        except yaml.YAMLError as e:
            logging.exception(json.dumps({'action': 'load yaml', 'status': 'failed', 'error': str(e)}))
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


def categorise_message(body):
    command = body.get('command', None)
    actions = body.get('actions', None)
    if command is not None and "/sql" in command:
        input_type = 'slashcommand'
    elif actions is not None:
        input_type = 'executebutton'
    else:
        input_type = 'other'
    return input_type


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

    #try:
    #    cnx = mysql.connector.connect(
    #        user=os.environ['MYSQL_USER'],
    #        password=os.environ['MYSQL_PASSWORD'],
    #        database=query['mysql_host'],
    #        host=query['mysql_host']
    #    )
    #except:
    #    logging.exception("Failed to connect to MySQL database")
    #cur = cnx.cursor(buffered=True)
    #cur.execute(query['sql'])
    #result = cur.fetchall()
    return "some sql result asdfasdfasdf\nasdfasdfasdf\nasdfasdfasdf\nasdffdsaasdfasdfasdf"


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


def main():
    pass

if __name__ == '__main__':
    main()
