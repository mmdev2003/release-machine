.PHONY: deploy build-all stop-all update-all rebuild-all
.PHONY: rebuild-app stop-app
.PHONY: rebuild-monitoring stop-monitoring
.PHONY: rebuild-db stop-db
.PHONY: set-env set-env-to-config-template

set-env:
	@export $(cat env/.env.app env/.env.db env/.env.monitoring | xargs)

set-env-to-config-template:
	@envsubst < ${NAME_LOKI_CONFIG_FILE}.template > ${NAME_LOKI_CONFIG_FILE}
	@envsubst < ${NAME_MONITORING_REDIS_CONFIG_FILE}.template > ${NAME_MONITORING_REDIS_CONFIG_FILE}
	@envsubst < ${NAME_TEMPO_CONFIG_FILE}.template > ${NAME_TEMPO_CONFIG_FILE}
	@envsubst < ${NAME_OTEL_COLLECTOR_CONFIG_FILE}.template > ${NAME_OTEL_COLLECTOR_CONFIG_FILE}

deploy:
	@apt update && apt upgrade -y
	@apt install python3-pip git make
	@pip install requests --break-system-packages
	@cd ..
	@git clone git@github.com:Name/name-release-tg-bot.git
	@git clone git@github.com:Name/name-account.git
	@git clone git@github.com:Name/name-authorization.git
	@cd name-system
	@./infrastructure/nginx/install.sh
	@./infrastructure/docker/install.sh
	@mkdir -p volumes/{grafana,loki,tempo,redis,postgresql,victoria-metrics,tg-bot-api}
	@mkdir -p volumes/redis/monitoring
	@mkdir -p volumes/weed
	@mkdir -p volumes/postgresql/{release-tg-bot,account,authorization,grafana}
	@chmod -R 777 volumes

build-all: set-env-to-config-template
	@docker compose -f ./docker-compose/db.yaml up --build
	sleep 20
	@docker compose -f ./docker-compose/monitoring.yaml up --build
	sleep 20
	@docker compose -f ./docker-compose/app.yaml up --build


stop-all:
	@docker compose -f ./docker-compose/app.yaml down
	@docker compose -f ./docker-compose/monitoring.yaml down
	@docker compose -f ./docker-compose/db.yaml down

update-all:
	@git pull
	@cd ../name-release-tg-bot/ && git fetch origin && git checkout main && git reset --hard origin/main && cd ../name-system/
	@cd ../name-account/ && git fetch origin && git checkout main && git reset --hard origin/main && cd ../name-system/
	@cd ../name-authorization/ && git fetch origin && git checkout main && git reset --hard origin/main && cd ../name-system/

rebuild-all: update-all build-all

rebuild-app: update-all set-env-to-config-template
	@docker compose -f ./docker-compose/apps.yaml up -d --build

stop-app:
	@docker compose -f ./docker-compose/apps.yaml down

stop-monitoring:
	@docker compose -f ./docker-compose/monitoring.yaml down

stop-db:
	@docker compose -f ./docker-compose/db.yaml down

rebuild-monitoring: update-all set-env-to-config-template
	@docker compose -f ./docker-compose/monitoring.yaml down
	@docker compose -f ./docker-compose/monitoring.yaml up -d --build

rebuild-db: update-all set-env-to-config-template
	@docker compose -f ./docker-compose/db.yaml down
	@docker compose -f ./docker-compose/db.yaml up -d --build