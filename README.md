# ML_PRO2026

```bash
uv run pytest
```

```bash
docker compose up -d --build
docker compose ps
```

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl -X POST http://localhost:8000/v1/predict \
	-H "Content-Type: application/json" \
	--data @good.json
```

```bash
docker compose exec db psql -U postgres -d spam \
	-c "SELECT request_id, model_version, score, spam, latency_ms FROM predictions;"
```

```bash
docker compose logs api
docker compose logs db
docker compose logs -f api
```


```bash
kind create cluster --name mlpro
```


```bash
docker compose down
docker compose down -v
```

##Ссылка на отчет:
```url
https://docs.google.com/document/d/1AWy_UTxFYShH4ozGbVsLSD4ZTn0ZN5yusoS8ODJhtpI/edit?usp=sharing
```

