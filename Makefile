.PHONY: up down restart clean

up:
	docker-compose up -d

down:
	docker-compose down

restart:
	docker-compose down && docker-compose up -d

clean:
	docker-compose down -v
	rm -rf logs/* data/minio/*
