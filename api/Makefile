beauty:
	uv run ruff format && uv run ruff check --fix

migrations:
	alembic revision --autogenerate

migrate:
	alembic upgrade head

test:
	uv run pytest -n 4

test-cov: test
	uv run coverage report --precision=2 --show-missing --skip-empty --skip-covered --fail-under=80

run:
	uv run uvicorn app:get_app --factory --proxy-headers --forwarded-allow-ips '*' --reload
