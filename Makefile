PACKAGE_DIR=package/package
ARTIFACT_NAME=package.zip
ARTIFACT_PATH=package/$(ARTIFACT_NAME)
ifdef DOTENV
	DOTENV_TARGET=dotenv
else
	DOTENV_TARGET=.env
endif
ifdef AWS_ROLE
	ASSUME_REQUIRED?=assumeRole
endif
ifdef GO_PIPELINE_NAME
	ENV_RM_REQUIRED?=rm_env
endif


################
# Entry Points #
################

build: $(DOTENV_TARGET)
	docker-compose run --rm serverless make _deps _build

deploy: $(ENV_RM_REQUIRED) $(ARTIFACT_PATH) .env $(ASSUME_REQUIRED)
	docker-compose run --rm serverless make _deps _deploy

smoketest: .env $(ASSUME_REQUIRED)
	docker-compose run --rm serverless make _smokeTest

remove: $(DOTENV_TARGET)
	docker-compose run --rm serverless make _deps _remove

shell: $(DOTENV_TARGET)
	docker-compose run --rm serverless bash

test: *.py .env
	docker-compose run --rm pep8 --ignore E501 *.py

assumeRole: .env
	docker run --rm -e "AWS_ACCOUNT_ID" -e "AWS_ROLE" amaysim/aws:1.1.1 assume-role.sh >> .env
.PHONY: build deploy smoketest remove shell test assumeRole

##########
# Others #
##########

# Removes the .env file before each deploy to force regeneration without cleaning the whole environment
rm_env:
	rm -f .env
.PHONY: rm_env

# Create .env based on .env.template if .env does not exist
.env:
	@echo "Create .env with .env.template"
	cp .env.template .env

# Create/Overwrite .env with $(DOTENV)
dotenv:
	@echo "Overwrite .env with $(DOTENV)"
	cp $(DOTENV) .env

$(ARTIFACT_PATH): build

$(DOTENV):
	$(info overwriting .env file with $(DOTENV))
	cp $(DOTENV) .env
.PHONY: $(DOTENV)

_deps: node_modules
.PHONY: _deps

node_modules: package.json
	# work around due to https://github.com/yarnpkg/yarn/issues/1961
	yarn --no-bin-links

_smokeTest:
	sls invoke -f testconnectivity

_build:

_deploy:
	rm -fr .serverless
	sls deploy -v

_remove:
	sls remove -v
	rm -fr .serverless

_clean:
	rm -fr node_modules .serverless package .requirements
.PHONY: _deploy _remove _clean
