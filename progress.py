"""Progress persistence using JSON files."""
from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path

from models import UserProgress

logger = logging.getLogger(__name__)

DEFAULT_PROGRESS_PATH = Path(__file__).parent / "progress.json"


class ProgressManager:
    """Load and save user progress to a JSON file with atomic writes."""

    def __init__(self, path: Path | str = DEFAULT_PROGRESS_PATH) -> None:
        self.path = Path(path)

    def load(self) -> UserProgress:
        """Load progress from JSON. Returns empty progress if file missing or corrupt."""
        if not self.path.exists():
            logger.info("No progress file found at %s, starting fresh.", self.path)
            return UserProgress()
        
        try:
            data = self.path.read_text(encoding="utf-8")
            return UserProgress.model_validate_json(data)
        except (json.JSONDecodeError, ValueError) as e:
            backup_path = self.path.with_suffix(".json.bak")
            logger.warning(
                "Corrupt progress file at %s: %s. Backing up to %s and starting fresh.",
                self.path, e, backup_path,
            )
            try:
                self.path.rename(backup_path)
            except OSError:
                pass
            return UserProgress()

    def save(self, progress: UserProgress) -> None:
        """Save progress atomically (write temp file, then replace)."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = progress.model_dump_json(indent=2)
        
        # Write to temp file in same directory, then atomic replace
        fd, tmp_path = tempfile.mkstemp(
            dir=self.path.parent, suffix=".tmp", prefix=".progress_"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(data)
            os.replace(tmp_path, self.path)
            logger.debug("Progress saved to %s", self.path)
        except Exception:
            # Clean up temp file on failure
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
