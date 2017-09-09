#!/usr/bin/env python3
import os
import logging
import aws_lambda_logging
import json
import re
import ruamel.yaml as yaml
import mysql.connector


def handler(event, context):
    """Main entrypoint"""

    loglevel = os.environ.get('LOGLEVEL', 'INFO')
    logging.debug('.(setup) #1')
    aws_lambda_logging.setup(level=loglevel)
    logging.debug('.(setup) #2')
    aws_lambda_logging.setup(level=loglevel)  # for some reason you have to do setup twice
    try:
        correlation_id = context.aws_request_id
        aws_lambda_logging.setup(correlation_id=correlation_id)
    except:
        pass
    try:
        env = os.environ.get('ENV')
        aws_lambda_logging.setup(env=env)
    except:
        pass
    logging.debug('Dumping event #1...')
    logging.debug(json.dumps({'event': event}))
    logging.debug('Dumping event #2...')

    with open("example.yml") as stream:
        try:
            config = yaml.safe_load(stream)
            logging.debug(json.dumps(config))
        except yaml.YAMLError as e:
            logging.exception(json.dumps({'action': 'load yaml', 'status': 'failed', 'error': str(e)}))

    try:
        if event['query']:
            result = run_query(config['queries'][event['query']])
    except Exception as e:
        logging.exception(json.dumps({'action': 'running SQL query', 'status': 'failed', 'error': str(e)}))

    body = ""
    try:
        body = format_result(result)
    except Exception as e:
        logging.exception(json.dumps({'action': 'formatting response', 'status': 'failed', 'error': str(e)}))

    if body:
        response = {
            "statusCode": 200,
            "body": body
        }
    else:
        body = {
		    "response_type": "in_channel",
		    "text": "It's 80 degrees right now.",
		    "attachments": [
		        {
		            "text":"Partly cloudy today and tomorrow"
		        }
		    ]
		}
        response = {
            "statusCode": 200,
            "body": body
        }
        
    logging.info(json.dumps({'action': 'responding', 'response': response}))
    return response


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
    response = 'asdf'
    return response


def main():
    handler({'query': 'getstats'}, {})

if __name__ == '__main__': main()
