#!/usr/bin/env python3
import os
import logging
import aws_lambda_logging
import json
import re
import ruamel.yaml as yaml


def handler(event, context):
    """Main entrypoint"""

    loglevel = os.environ.get('LOGLEVEL', 'INFO')
    logging.debug('.(setup) #1')
    aws_lambda_logging.setup(level=loglevel)  # for some reason you have to do setup twice
    logging.debug('.(setup) #2')
    aws_lambda_logging.setup(level=loglevel)
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
    logging.debug(json.dumps(event))
    logging.debug('Dumping event #2...')
#    logging.debug(event)

    with open("example.yaml") as stream:
        try:
            yaml = yaml.safe_load(stream)
            logging.debug(json.dumps(yaml))
        except yaml.YAMLError as e:
            logging.exception(json.dumps({'query': 'load yaml', 'status': 'failed', 'error': str(e)}))

    if event['query']:
        result = run_query(event['query'])

    response = format_result(result)

    response = {
        "statusCode": 200,
        "body": response
    }
    return response


def run_query(query):
    """Takes a query from the configuration file, executes it and returns the result"""

    cnx = mysql.connector.connect(
        user=os.environ['MYSQL_USER'], 
        password=os.environ['MYSQL_PASSWORD'], 
        database=query['mysql_host'], 
        host=query['mysql_host'])
    cur = cnx.cursor(buffered=True)
    cur.execute(query['sql'])
    result = cur.fetchall()
    return result


def format_result(result):
    """Formats the query results in to a format accepted by Slack"""

    return response


def main():
    handler({'query': 'getstats'}, {})

if __name__ == '__main__': main()
