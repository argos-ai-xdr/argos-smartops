.PHONY: bootstrap validate test lint run

bootstrap:
	./scripts/bootstrap.sh

validate:
	./scripts/validate.sh

test:
	./scripts/test.sh

lint: validate

run:
	uvicorn api.app:create_app --factory --reload
