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