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

## How to

  * Fill in the environment variables needed in `.env.template` either through your CD platform or by filling out `.env`
  * Copy `example.yml` and fill out your aliases
  * Create the env vars `SQL_FOOBAR_USERNAME` and `SQL_FOOBAR_PASSWORD` for each alias, where `FOOBAR` is the alias in uppercase. This must be done in the env file and `serverless.yml`
  * `make deploy`

## Other features

  * Graphical selection of queries via `/sql help`
  * Results are returned to the channel for others to see
  * Audit trail via Slack and JSON-formatted logging
  * Runs on Lambda using the Serverless framework

## Limitations

  * AWS Lambda has a runtime limit of 5 minutes
  * The Lambda function must have network connectivity to the database
  * Result is not formatted nicely
  * Currently limited to MySQL/MariaDB databases
