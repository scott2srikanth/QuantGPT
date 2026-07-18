# Developer guide

## Local development

```sh
cp .env.example .env
make up
make migrate
make health
```

Never commit `.env`, model artifacts, database dumps, or API keys. Use fake/local credentials only.

## Quality checks

```sh
docker compose exec -T backend ruff check app tests
docker compose exec -T backend pytest -q
docker compose exec -T frontend npm run lint
docker compose exec -T frontend npm run build
```

Run the k6 smoke test after bringing up the stack: `k6 run tests/load/smoke.js`. It verifies health endpoint latency only; do not load-test a production broker integration without an approved test plan.

## Adding an API mutation

1. Require authentication/authorisation for the route.
2. Ensure the route is covered by a test and returns safe errors.
3. Do not log tokens, passwords, raw trading credentials, or request bodies.
4. Confirm it remains behind the Risk Engine if it can cause an order to be placed.
5. Preserve the request ID in downstream logs.
