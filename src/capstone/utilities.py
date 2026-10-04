"""Cross-project helpers: logging, model persistence, and human-readable data caches."""

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
import sklearn
from loguru import logger

from capstone.config import PATHS


def setup_logging(level: str = "INFO", log_file: Path = PATHS.logs / "capstone.log") -> None:
    """Log `level` and above to stderr and everything from DEBUG up to a rotating file."""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(sys.stderr, level=level)
    logger.add(log_file, level="DEBUG", rotation="5 MB", retention=5)


def frame_hash(df: pd.DataFrame) -> str:
    """Stable content hash of a frame (values and index), used to detect stale artifacts."""
    return hashlib.sha256(pd.util.hash_pandas_object(df, index=True).to_numpy().tobytes()).hexdigest()[:16]


def _meta_path(model_path: Path) -> Path:
    return model_path.with_suffix(".meta.json")


def save_model(model: Any, name: str, data_hash: str) -> Path:
    """Pickle a fitted model to PATHS.models/<name>.joblib with a metadata sidecar
    recording the sklearn version, training-data hash, and fit time."""
    path = PATHS.models / f"{name}.joblib"
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)
    meta = {"sklearn_version": sklearn.__version__, "data_hash": data_hash, "fitted_at": datetime.now(UTC).isoformat()}
    write_json(meta, _meta_path(path))
    logger.info("saved model {} ({})", path.name, data_hash)
    return path


def load_model(name: str, data_hash: str) -> Any | None:
    """Load a pickled model, or None if it is missing or stale (different sklearn
    version or training data than `data_hash`)."""
    path = PATHS.models / f"{name}.joblib"
    if not path.exists() or not _meta_path(path).exists():
        logger.debug("no cached model {}", path.name)
        return None
    meta = read_json(_meta_path(path))
    if meta.get("sklearn_version") != sklearn.__version__ or meta.get("data_hash") != data_hash:
        logger.warning("cached model {} is stale ({}); refitting", path.name, meta)
        return None
    logger.debug("loaded cached model {}", path.name)
    return joblib.load(path)


def write_json(obj: Any, path: Path) -> Path:
    """Write an object as indented JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str) + "\n")
    return path


def read_json(path: Path) -> Any:
    """Read a JSON file."""
    return json.loads(path.read_text())


def write_jsonl(df: pd.DataFrame, path: Path) -> Path:
    """Write a frame as JSON Lines, one record per row, keeping the index as a column."""
    path.parent.mkdir(parents=True, exist_ok=True)
    records = df.reset_index().to_dict(orient="records")
    path.write_text("".join(json.dumps(r, default=str) + "\n" for r in records))
    logger.debug("wrote {} rows to {}", len(df), path)
    return path


def read_jsonl(path: Path, index: str | None = None) -> pd.DataFrame:
    """Read a JSON Lines file, optionally restoring `index` as the frame index."""
    df = pd.read_json(path, orient="records", lines=True)
    return df.set_index(index) if index else df
