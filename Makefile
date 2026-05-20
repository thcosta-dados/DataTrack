.PHONY: build up down restart clean

build:
	docker-compose build

up:
	docker-compose up -d --build

down:
	docker-compose down

restart:
	docker-compose down && docker-compose up -d --build

clean:
	docker-compose down -v
	rm -rf logs/* data/minio/*
