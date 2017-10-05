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
deps: $(DOTENV_TARGET)
	docker-compose run $(USER_SETTINGS) --rm serverless make _deps

build: $(DOTENV_TARGET)
	docker-compose run $(USER_SETTINGS) --rm virtualenv make _build

deploy: $(ENV_RM_REQUIRED) $(DOTENV_TARGET) $(ASSUME_REQUIRED) node_modules.zip $(ARTIFACT_PATH)
	docker-compose run $(USER_SETTINGS) --rm serverless make _deploy

unitTest: $(ASSUME_REQUIRED) $(DOTENV_TARGET)
	docker-compose run $(USER_SETTINGS) --rm make _test

smokeTest: $(DOTENV_TARGET) $(ASSUME_REQUIRED)
	docker-compose run $(USER_SETTINGS) --rm serverless make _smokeTest

remove: $(DOTENV_TARGET)
	docker-compose run $(USER_SETTINGS) --rm serverless make _deps _remove

unzip: $(DOTENV_TARGET) $(ARTIFACT_PATH)
	docker-compose run $(USER_SETTINGS) --rm virtualenv make _unzip

styleTest: $(DOTENV_TARGET)
	docker-compose run $(USER_SETTINGS) --rm virtualenv make _unzip
	docker-compose run $(USER_SETTINGS) --rm pep8 --ignore E501 *.py

assumeRole: $(DOTENV_TARGET)
	docker run --rm -e "AWS_ACCOUNT_ID" -e "AWS_ROLE" amaysim/aws:1.1.1 assume-role.sh >> .env

test: $(DOTENV_TARGET) styleTest

shell: $(DOTENV_TARGET)
	docker-compose run $(USER_SETTINGS) --rm virtualenv sh

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

_pip: requirements.txt
	pip install -r requirements.txt -t $(PACKAGE_DIR)

_build: _pip
	cp lambda.py $(PACKAGE_DIR)
	cp *.yml $(PACKAGE_DIR)
	cd $(PACKAGE_DIR) && zip -rq ../package .

run/example.yml: run/lambda.py

run/lambda.py: $(ARTIFACT_PATH)
	mkdir -p run/
	cd run && unzip -qo -d . ../$(ARTIFACT_PATH)
#	@touch run/lambda.py

_unzip: run/lambda.py

run/.lastrun: $(ARTIFACT_PATH)
	cd run && ./lambda.py
#	@touch run/.lastrun

_run: run/.lastrun

# Install node_modules for serverless plugins
_deps: node_modules.zip

node_modules.zip:
	yarn install --no-bin-links
	zip -rq node_modules.zip node_modules/

_deploy:
	mkdir -p node_modules
	unzip -qo -d . node_modules.zip
	rm -fr .serverless
	sls deploy -v

_remove:
	sls remove -v
	rm -fr .serverless

_clean:
	rm -fr node_modules.zip node_modules .serverless package .requirements venv/ run/ __pycache__/
.PHONY: _deploy _remove _clean
