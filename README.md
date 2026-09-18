# ML_PRO2026

## Проверка в Kubernetes

Требуются запущенный Kubernetes-кластер и установленный `kubectl`. Для локального Docker Desktop Kubernetes образ `spam-service:1.0` должен быть доступен кластеру.

Проверить текущий контекст и валидировать манифесты:

```bash
kubectl config current-context
kubectl apply --dry-run=client -f k8s/
```

Применить приложение:

```bash
kubectl apply -f k8s/
kubectl rollout status deployment/spam-service
kubectl get pods -l app=spam
kubectl get service spam-service
```

Открыть API локально через port-forward:

```bash
kubectl port-forward service/spam-service 8000:80
```

В другом терминале проверить endpoints:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl -X POST http://localhost:8000/v1/predict \
	-H "Content-Type: application/json" \
	--data @good.json
```

При проблемах посмотреть состояние и логи:

```bash
kubectl describe pods -l app=spam
kubectl logs deployment/spam-service
```

Удалить приложение после проверки:

```bash
kubectl delete -f k8s/
```
