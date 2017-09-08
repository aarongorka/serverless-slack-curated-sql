#!/usr/bin/env python3
import os
import logging
from bs4 import BeautifulSoup
import requests
import aws_lambda_logging
import json
import re


def get_token(text):
    soup = BeautifulSoup(text, 'html.parser')
    inputs = soup.find_all('input')
    for input in inputs:
        if input['name'] == 'centreon_token':
            return input['value']


def get_login(url, useralias, password, correlation_id):
    r = requests.get(url + 'index.php', timeout=5)
    token = get_token(r.text)
    jar = r.cookies
    data = {}
    data = {'useralias': useralias,
            'password': password,
            'submitLogin': 'Connect',
            'centreon_token': token}
    r = requests.post(url + 'index.php', data=data, cookies=jar, timeout=5, headers={'Correlation-Id': correlation_id})
    logging.debug(json.dumps({'cookies': str(jar)}))
    if useralias not in r.text:
        raise Exception("Failed to log in.")
    else:
        logging.info(json.dumps({'action': 'logged in'}))
    return jar


def logout(url, jar, correlation_id):
    requests.get(url + 'index.php?disconnect=1', timeout=5, headers={'Correlation-Id': correlation_id})
    logging.info(json.dumps({'action': 'logged out'}))


def ack_service(jar, url, service, host, useralias, correlation_id):
    fullurl = '{url}main.php?p=20201&o=svcak&cmd=15&host_name={host}&service_description={service}&en=1'.format(
        url=url, host=host, service=service)
    r = requests.get(fullurl, cookies=jar, timeout=5, headers={'Correlation-Id': correlation_id})
    logging.debug(json.dumps(r.text))

    token = get_token(r.text)

    logging.debug(json.dumps({'token': token}))

    data = {}
    data = {'comment': "Automated acknowledgement",
            'force_check': '1',
            'submit': 'Add',
            'host_name': host,
            'service_description': service,
            'author': useralias,
            'cmd': '15',
            'p': '20201',
            'en': '1',
            'centreon_token': token,
            'o': 'svcd'}

    logging.debug(json.dumps({"action": "post", "data": data}))
    logging.info(json.dumps({"action": "acknowledgement"}))
    r = requests.post(
        '{url}main.php?p=20201&host_name={host}&service_description={service}'.format(
            url=url, host=host, service=service), data=data, cookies=jar, timeout=5, headers={'Correlation-Id': correlation_id})

    if useralias not in r.text:
        raise Exception("Failed to log in.")
    return(r)


def ack_host(jar, url, host, useralias, correlation_id):
    r = requests.get(
        '{url}main.php?p=20202&o=hak&cmd=14&host_name={host}&en=1'.format(
            url=url, host=host), cookies=jar, timeout=5, headers={'Correlation-Id': correlation_id})
    logging.debug(json.dumps({'text': r.text}))

    token = get_token(r.text)

    logging.debug(json.dumps({'token': token}))

    data = {}
    data = {'comment': "Automated acknowledgement",
            'persistent': '1',
            'sticky': '1',
            'submit': 'Add',
            'host_name': host,
            'author': useralias,
            'cmd': '14',
            'p': '20202',
            'en': '1',
            'centreon_token': token,
            'o': 'hd'}

    logging.debug(json.dumps({"action": "post", "data": data}))
    logging.info(json.dumps({"action": "acknowledgement", "host": host}))
    r = requests.post(
        '{url}main.php?p=20202&host_name={host}'.format(
            url=url, host=host), data=data, cookies=jar, timeout=5, headers={'Correlation-Id': correlation_id})
    return(r)


def handler(event, context):
    loglevel = os.environ.get('LOGLEVEL', 'INFO')
    correlation_id = context.aws_request_id
    aws_lambda_logging.setup(level=loglevel, correlation_id=correlation_id)  # for some reason you have to do setup twice
    logging.debug('Initialising logging...')
    aws_lambda_logging.setup(level=loglevel, correlation_id=correlation_id)
    try:
        aws_lambda_logging.setup(env=os.environ.get('ENV'))
    except:
        pass
    logging.debug(json.dumps(event))
    logging.debug(event)

    response = {
        "statusCode": 200,
        "body": 'OK'
    }
    return response


def local_test():
    url = os.environ['CENTREON_URL']
    useralias = os.environ['CENTREON_USERALIAS']
    password = os.environ['CENTREON_PASSWORD']
    service = 'testservice'
    host = 'testhost'
    jar = get_login(url, useralias, password, correlation_id)
    ack_service(jar, url, service, host, useralias, correlation_id)
    ack_host(jar, url, host, useralias, correlation_id)


def test_connectivity(event, context):
    loglevel = os.environ.get('LOGLEVEL', 'DEBUG')
    correlation_id = context.aws_request_id
    aws_lambda_logging.setup(level=loglevel, correlation_id=correlation_id)
    try:
        aws_lambda_logging.setup(env=os.environ.get('ENV'))
    except:
        pass
    logging.debug(json.dumps({'event': event}))

    url = os.environ['CENTREON_URL']
    useralias = os.environ['CENTREON_USERALIAS']
    password = os.environ['CENTREON_PASSWORD']

    jar = get_login(url, useralias, password, correlation_id)
    logout(url, jar, correlation_id)
    logging.info(json.dumps({'action': 'finished', 'status': 'success'}))
