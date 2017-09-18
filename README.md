# serverless-slack-curated-sql

This bot allows you to send predefined SQL queries in Slack.

## Requirements

  * Docker
  * docker-compose
  * make(1)
  * AWS Lambda
  * MariaDB/MySQL

## How it works

Queries are defined in a YAML configuration file, with their SQL statement, database hostname, database name and an alias for this query. If you defined a query with an alias of `foobar`, you can then run it by typing `/sql foobar` in Slack.

## Other features

  * Graphical selection of queries
  * Results are returned to the channel for others to see
  * Audit trail via Slack and JSON-formatted logging
  * Runs on Lambda using the Serverless framework

## Limitations

  * AWS Lambda has a runtime limit of 5 minutes
  * The Lambda function must have network connectivity to the database
  * Result is not formatted nicely
  * Currently limited to MySQL/MariaDB databases
