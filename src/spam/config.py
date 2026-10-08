from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_path: str = "artifacts/model_bundle.joblib"
    model_name: str = ""          # пусто = брать файл, как раньше (тесты в CI)
    model_alias: str = "champion"
    mlflow_tracking_uri: str = "http://mlflow.mlops:5000"
    database_url: str | None = None
    log_level: str = "INFO"

    model_config = {"env_file": ".env"}