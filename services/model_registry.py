import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


class ModelRegistry:
    """Simple model registry for versioned ML artifacts."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), "models"))
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_path = self.base_dir / "model_metadata.json"
        self._metadata = self._load_metadata()

    def _load_metadata(self) -> Dict[str, Any]:
        if not self.metadata_path.exists():
            return {}
        try:
            return json.loads(self.metadata_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_metadata(self) -> None:
        self.metadata_path.write_text(json.dumps(self._metadata, indent=2, sort_keys=True), encoding="utf-8")

    def register_model(self, model_name: str, artifact_path: os.PathLike | str, version: str, source: str = "unknown", status: str = "ready") -> Dict[str, Any]:
        artifact_path = Path(artifact_path)
        metadata = {
            "version": version,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "status": status,
            "artifact_path": str(artifact_path),
        }
        models = self._metadata.setdefault(model_name, {})
        models[version] = metadata
        self._metadata[model_name] = models
        if self.get_active_model_version(model_name) is None:
            self.set_active_version(model_name, version)
        self._save_metadata()
        return metadata

    def set_active_version(self, model_name: str, version: str) -> Optional[Dict[str, Any]]:
        models = self._metadata.get(model_name, {})
        if version not in models:
            return None
        self._metadata.setdefault("active_versions", {})[model_name] = version
        self._save_metadata()
        return models[version]

    def get_active_model_version(self, model_name: str) -> Optional[str]:
        return self._metadata.get("active_versions", {}).get(model_name)

    def get_model_metadata(self, model_name: str, version: Optional[str] = None) -> Optional[Dict[str, Any]]:
        models = self._metadata.get(model_name, {})
        if not models:
            return None
        if version is None:
            version = self.get_active_model_version(model_name)
        if version is None:
            return None
        return models.get(version)

    def get_available_versions(self, model_name: str) -> list[str]:
        return sorted(self._metadata.get(model_name, {}).keys())

    def load_model(self, model_name: str, version: Optional[str] = None, loader: Optional[Any] = None) -> Any:
        target_version = version or self.get_active_model_version(model_name)
        if target_version is None:
            raise FileNotFoundError(f"No active model version found for {model_name}")
        metadata = self.get_model_metadata(model_name, target_version)
        if metadata is None:
            raise FileNotFoundError(f"Model {model_name} version {target_version} was not registered")
        artifact_path = Path(metadata.get("artifact_path", ""))
        if not artifact_path.exists():
            raise FileNotFoundError(f"Artifact not found: {artifact_path}")
        if loader is None:
            return artifact_path
        return loader(artifact_path)

    def promote_model(self, model_name: str, version: str) -> Optional[Dict[str, Any]]:
        models = self._metadata.get(model_name, {})
        if version not in models:
            return None
        metadata = models[version]
        metadata["status"] = "ready"
        models[version] = metadata
        self._metadata[model_name] = models
        self.set_active_version(model_name, version)
        self._save_metadata()
        return metadata

    def rollback(self, model_name: str) -> Optional[str]:
        versions = self.get_available_versions(model_name)
        if not versions:
            return None
        previous_version = versions[-2] if len(versions) > 1 else versions[0]
        self.set_active_version(model_name, previous_version)
        return previous_version


model_registry = ModelRegistry()
