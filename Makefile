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
else
	USER_SETTINGS=--user $(shell id -u):$(shell id -g)
endif


################
# Entry Points #
################

build: $(DOTENV_TARGET)
	docker-compose run $(USER_SETTINGS) --rm serverless make _deps _build

deploy: run $(ENV_RM_REQUIRED) $(ARTIFACT_PATH) $(DOTENV_TARGET) $(ASSUME_REQUIRED)
	docker-compose run $(USER_SETTINGS) --rm serverless make _deps _deploy

unitTest: .env $(ASSUME_REQUIRED)
	docker-compose run $(USER_SETTINGS) --rm lambda make _run

smokeTest: .env $(ASSUME_REQUIRED)
	docker-compose run $(USER_SETTINGS) --rm serverless make _smokeTest

remove: $(DOTENV_TARGET)
	docker-compose run $(USER_SETTINGS) --rm serverless make _deps _remove

styleTest: *.py .env
	docker-compose run $(USER_SETTINGS) --rm pep8 --ignore E501 *.py

assumeRole: .env
	docker run --rm -e "AWS_ACCOUNT_ID" -e "AWS_ROLE" amaysim/aws:1.1.1 assume-role.sh >> .env
.PHONY: build deploy smokeTest remove shell styleTest assumeRole

test: $(DOTENV_TARGET) styleTest unitTest
.PHONY: test

shell: $(DOTENV_TARGET)
	docker-compose run $(USER_SETTINGS) --rm virtualenv sh

deps: _requirements
	docker-compose run $(USER_SETTINGS) --rm virtualenv make _requirements
.PHONY: deps

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

$(DOTENV):
	$(info overwriting .env file with $(DOTENV))
	cp $(DOTENV) .env
.PHONY: $(DOTENV)

$(PACKAGE_DIR)/pip_run: requirements.txt
	pip install -r requirements.txt -t $(PACKAGE_DIR)
	touch "$(PACKAGE_DIR)/pip_run"

$(ARTIFACT_PATH): $(DOTENV_TARGET) *.py example.yml $(PACKAGE_DIR)/pip_run
	cp *.py $(PACKAGE_DIR)
	cp example.yml $(PACKAGE_DIR)
	cd $(PACKAGE_DIR) && zip -rq ../package .

run/.lastrun: $(ARTIFACT_PATH)
	mkdir -p run/
	cd run && unzip -qo -d . ../$(ARTIFACT_PATH)
	cd run && ./lambda.py
	@touch run/.lastrun

_run: run/.lastrun
.PHONY: _run

# Install node_modules for serverless plugins
_deps: node_modules
.PHONY: _deps

node_modules: package.json
	# work around due to https://github.com/yarnpkg/yarn/issues/1961
	yarn --no-bin-links

_deploy: $(ARTIFACT_PATH)
	rm -fr .serverless
	sls deploy -v

_remove:
	sls remove -v
	rm -fr .serverless

_clean:
	rm -fr node_modules .serverless package .requirements venv/
.PHONY: _deploy _remove _clean
