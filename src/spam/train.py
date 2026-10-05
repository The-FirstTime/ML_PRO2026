"""Обучение spam/ham классификатора: проверка данных, обучение, запись в MLflow, регистрация и гейт.

  MLFLOW_TRACKING_URI=http://127.0.0.1:5000 uv run python -m spam.train

Новая версия всегда получает алиас challenger. Алиас champion она получает, только если
ROC-AUC на отложенной выборке лучше, чем у текущего champion (или champion ещё нет).
"""
import json
import os
from pathlib import Path

import mlflow
import pandas as pd
import sklearn
from mlflow import MlflowClient
from mlflow.exceptions import MlflowException
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, precision_recall_curve, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

DATA_PATH = Path(os.getenv("DATA_PATH", "datasets/SMSSpamCollection.csv"))
MODEL_NAME = os.getenv("MODEL_NAME", "spam")
EXPERIMENT = os.getenv("MLFLOW_EXPERIMENT", "spam")
C = float(os.getenv("C", "1.0"))
MIN_GAIN = float(os.getenv("GATE_MIN_GAIN", "0.0"))
SEED = 42
SKOPS_TRUSTED = ["numpy.dtype"]

FEATURES = ["text"]
TARGET_NAMES = {0: "ham", 1: "spam"}


def load_and_validate(path: Path) -> pd.DataFrame:
    # исходный файл UCI SMS Spam Collection: TSV без заголовка, колонки label/text
    df = pd.read_csv(path, sep="\t", header=None, names=["label", "text"])
    missing = {"label", "text"} - set(df.columns)
    if missing:
        raise ValueError(f"в данных нет колонок: {sorted(missing)}")
    if len(df) < 1000:
        raise ValueError(f"слишком мало строк: {len(df)}")
    if not set(df["label"].unique()) <= {"ham", "spam"}:
        raise ValueError(f"неожиданные значения таргета: {df['label'].unique()[:5]}")
    df["target"] = (df["label"] == "spam").astype(int)
    return df


def build_pipeline(c: float) -> Pipeline:
    return Pipeline([
        ("tfidf", TfidfVectorizer(lowercase=True, stop_words="english", ngram_range=(1, 2), max_features=5000)),
        ("clf", LogisticRegression(max_iter=1000, C=c, class_weight="balanced")),
    ])


def champion_auc(client: MlflowClient) -> tuple[str | None, float | None]:
    try:
        mv = client.get_model_version_by_alias(MODEL_NAME, "champion")
    except MlflowException:
        return None, None
    return mv.version, client.get_run(mv.run_id).data.metrics.get("roc_auc")


def main() -> dict:
    df = load_and_validate(DATA_PATH)
    x_train, x_test, y_train, y_test = train_test_split(
        df["text"], df["target"], test_size=0.2, stratify=df["target"], random_state=SEED)

    pipeline = build_pipeline(C).fit(x_train, y_train)
    proba = pipeline.predict_proba(x_test)[:, 1]
    auc = float(roc_auc_score(y_test, proba))
    precision, recall, thresholds = precision_recall_curve(y_test, proba)
    threshold = float(thresholds[recall[:-1] >= 0.70].max())

    mlflow.set_experiment(EXPERIMENT)
    client = MlflowClient()
    with mlflow.start_run() as run:
        metadata = {"features": FEATURES, "threshold": round(threshold, 4), "target_names": TARGET_NAMES,
                    "n_train": len(x_train), "data_rows": len(df), "sklearn": sklearn.__version__}
        mlflow.log_params({"C": C, "model": "LogisticRegression", "vectorizer": "TfidfVectorizer",
                           "seed": SEED, "data": str(DATA_PATH)})
        mlflow.log_metrics({"roc_auc": auc, "pr_auc": float(average_precision_score(y_test, proba)), "threshold": threshold})
        mlflow.log_dict(metadata, "metadata.json")
        info = mlflow.sklearn.log_model(pipeline, name="model", registered_model_name=MODEL_NAME,
                                        skops_trusted_types=SKOPS_TRUSTED)
        version = info.registered_model_version

    old_version, old_auc = champion_auc(client)
    promoted = old_auc is None or auc > old_auc + MIN_GAIN
    client.set_registered_model_alias(MODEL_NAME, "challenger", version)
    if promoted:
        client.set_registered_model_alias(MODEL_NAME, "champion", version)

    result = {"run_id": run.info.run_id, "version": version, "roc_auc": round(auc, 4),
              "champion_before": old_version, "champion_auc_before": old_auc, "promoted": promoted}
    print(json.dumps(result, ensure_ascii=False))
    xcom = Path("/airflow/xcom")
    if xcom.is_dir():
        (xcom / "return.json").write_text(json.dumps(result))
    return result


if __name__ == "__main__":
    main()