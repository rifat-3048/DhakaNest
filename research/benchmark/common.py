"""Shared safe paths, deterministic serialization, and backend import adapter."""

import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
RESEARCH = ROOT / "research"
DATA = RESEARCH / "datasets" / "benchmark_v1"
SEED = 42


def encode(value):
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def digest(value):
    return hashlib.sha256(encode(value).encode()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_once(path, value):
    path = Path(path).resolve()
    if not path.is_relative_to(RESEARCH.resolve()):
        raise ValueError("Outputs must remain inside research/.")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as output:
        output.write(encode(value))


def finite(value, positive=False):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and (value > 0 if positive else value >= 0))


def backend():
    """Import pure services with inert settings, without reading backend/.env.

    Use a dedicated research process. Refuse an already configured production
    process, since replacing its settings would be unsafe.
    """
    if "app.config" not in sys.modules:
        sys.path.insert(0, str(ROOT / "backend"))
        inert = {
            "APP_ENV": "test", "MONGO_URI": "mongodb://127.0.0.1:1",
            "DATABASE_NAME": "research_offline_do_not_connect",
            "JWT_SECRET_KEY": "research-inert-not-an-api-credential",
            "CLOUDINARY_CLOUD_NAME": "offline", "CLOUDINARY_API_KEY": "offline",
            "CLOUDINARY_API_SECRET": "offline", "TRANSPORT_COST_PER_KM_BDT": "5",
        }
        old_cwd = Path.cwd()
        # Settings loads .env relative to cwd. An empty directory prevents this.
        with TemporaryDirectory() as temporary, patch.dict(os.environ, inert, clear=True):
            try:
                os.chdir(temporary)
                importlib.import_module("app.config")
            finally:
                os.chdir(old_cwd)
    config = sys.modules["app.config"]
    if config.settings.database_name != "research_offline_do_not_connect":
        raise RuntimeError("Run this adapter in a separate offline research process.")
    return importlib.import_module("app.services.recommendation_service")


def request_schema():
    backend()
    return importlib.import_module("app.schemas.recommendation_schema").TenantRecommendationRequest


def verify_prior_manifests():
    checked = 0
    for phase in range(3):
        manifest = read(RESEARCH / f"results/phase_{phase}/phase_{phase}_manifest.json")
        for item in manifest["outputs"]:
            path = RESEARCH / item["path"]
            if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
                raise ValueError(f"Prior artifact changed: {path}")
            checked += 1
        item = manifest["dataset"]
        if hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError("Prior manifest dataset changed.")
    return checked
