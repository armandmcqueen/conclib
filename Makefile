# Build the dockerfile

# Build the dockerfile

.PHONY: build
build:
	docker build -t armandmcqueen/conclib .

.PHONY: run
run:
	docker run -it --rm armandmcqueen/conclib

# lint with ruff
.PHONY: lint
lint: format
	ruff check .

# format with ruff
.PHONY: format
format:
	ruff format .

.PHONY: publish
publish:
	FLIT_USERNAME=__token__ FLIT_PASSWORD=$(shell cat .ignore/pypi_token) flit publish
