.PHONY: all build run stop test books weights clean

DOCKER_IMAGE = foundationpose-api:latest
CONTAINER_NAME = foundationpose-api

all: build

build:
	docker build -t $(DOCKER_IMAGE) .

run:
	docker run --gpus all \
		--name $(CONTAINER_NAME) \
		-p 8000:8000 \
		-v $(PWD)/data:/app/data \
		-v $(PWD)/weights:/app/weights \
		-e CUDA_VISIBLE_DEVICES=0 \
		-e LOG_LEVEL=INFO \
		--restart unless-stopped \
		-d $(DOCKER_IMAGE)

stop:
	docker stop $(CONTAINER_NAME) 2>/dev/null || true
	docker rm $(CONTAINER_NAME) 2>/dev/null || true

restart: stop run

logs:
	docker logs -f $(CONTAINER_NAME)

shell:
	docker exec -it $(CONTAINER_NAME) bash

# ── Data preparation (run on host) ──────────────────────────────

books:
	pip install -q trimesh numpy
	python3 scripts/generate_book_models.py --output data/objects

weights:
	pip install -q gdown
	bash scripts/download_weights.sh

# ── Testing ─────────────────────────────────────────────────────

test: books
	@echo "=== Testing API ==="
	@echo "Waiting for server…"
	@sleep 3
	@curl -s http://localhost:8000/api/v1/health | python3 -m json.tool
	@echo ""
	@echo "Uploading book model…"
	@UPLOAD=$$(curl -s -X POST http://localhost:8000/api/v1/objects/upload \
		-F "file=@data/objects/book_novel.obj"); \
	ID=$$(echo "$$UPLOAD" | python3 -c "import sys,json; print(json.load(sys.stdin)['object_id'])"); \
	echo "Object ID: $$ID"; \
	echo ""; \
	echo "Predicting…"; \
	curl -s -X POST http://localhost:8000/api/v1/predict/upload \
		-F "object_id=$$ID" \
		-F "file=@scripts/test_book.png" \
		-F "fx=600" -F "fy=600" -F "cx=320" -F "cy=240" \
		-F "tracking_mode=false" | python3 -m json.tool

# ── Cleanup ─────────────────────────────────────────────────────

clean:
	docker rmi $(DOCKER_IMAGE) 2>/dev/null || true
	rm -rf data/objects/* data/output/*
