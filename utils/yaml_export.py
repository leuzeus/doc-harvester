"""Utilities to export sources from the database to YAML files."""

# Standard library imports
from pathlib import Path
from typing import Any

# Third-party imports
import yaml
from sqlmodel import Session, select

# Local application imports
from models import Source


# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------
def _parse_extra(extra: str | None) -> Any:
    """Return a structured representation of the extra configuration if possible."""

    if extra is None:
        return None

    trimmed = extra.strip()
    if not trimmed:
        return None

    try:
        return yaml.safe_load(trimmed)
    except yaml.YAMLError:
        return extra


# --------------------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------------------
def export_sources_to_yaml(session: Session, target_path: Path) -> str:
    """Serialize all sources to YAML and persist the payload to ``target_path``."""

    result = session.exec(select(Source))
    sources = result.all()

    payload: list[dict[str, Any]] = []
    for source in sources:
        item: dict[str, Any] = {
            "name": source.name,
            "kind": source.kind,
            "enabled": source.enabled,
        }

        if source.url:
            item["url"] = source.url

        extra_data = _parse_extra(source.extra)
        if extra_data is not None:
            item["extra"] = extra_data

        payload.append(item)

    document = {"sources": payload}
    yaml_text = yaml.safe_dump(document, sort_keys=False, allow_unicode=True)

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(yaml_text, encoding="utf-8")

    return yaml_text

