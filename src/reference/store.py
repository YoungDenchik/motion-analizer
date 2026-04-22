"""
Reference exercise storage.

Reference sequences are the "gold standard" — ideal movement patterns
that user sequences are compared against.

Storage format: one JSON file per exercise, stored in a configurable
directory. JSON was chosen over binary formats (numpy .npy, HDF5) for:
  - Human-readable: coaches can inspect and validate references
  - Portable: share references across machines without compatibility issues
  - Flexible: easy to add metadata fields

Reference files include:
  - name: exercise identifier (e.g., "squat", "deadlift")
  - description: human-readable description
  - feature_names: ordered list of feature names (must match extractor)
  - time_series: serialized TimeSeries dict
  - metadata: arbitrary key-value pairs (author, date, notes)

Multiple reference files per exercise are supported. When multiple
references exist, the comparator uses the one with the closest sequence
length to the query (heuristic: similar length = similar speed preference).
"""

from __future__ import annotations
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from ..timeseries.builder import TimeSeries


DEFAULT_REFERENCES_DIR = Path(__file__).parent.parent.parent / "references"


@dataclass
class ReferenceSequence:
    """A stored reference exercise sequence."""
    name: str
    description: str
    time_series: TimeSeries
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "time_series": self.time_series.to_dict(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ReferenceSequence":
        return cls(
            name=d["name"],
            description=d["description"],
            time_series=TimeSeries.from_dict(d["time_series"]),
            metadata=d.get("metadata", {}),
        )


class ReferenceStore:
    """
    CRUD operations for reference exercise sequences.

    File naming convention: {exercise_name}.json
    If multiple references exist for one exercise, they are named:
      {exercise_name}.json, {exercise_name}_v2.json, etc.
    """

    def __init__(self, directory: str | Path = DEFAULT_REFERENCES_DIR):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        name: str,
        time_series: TimeSeries,
        description: str = "",
        metadata: dict | None = None,
        overwrite: bool = False,
    ) -> Path:
        """
        Save a reference sequence to disk.

        Args:
            name: Exercise name (e.g., "squat"). Used as filename base.
            time_series: The reference TimeSeries to store.
            description: Human-readable description.
            metadata: Arbitrary metadata dict.
            overwrite: If False and file exists, raises FileExistsError.

        Returns:
            Path to the saved file.
        """
        path = self.directory / f"{name}.json"
        if path.exists() and not overwrite:
            raise FileExistsError(
                f"Reference '{name}' already exists at {path}. "
                "Pass overwrite=True to replace it."
            )

        ref = ReferenceSequence(
            name=name,
            description=description,
            time_series=time_series,
            metadata=metadata or {},
        )
        with open(path, "w", encoding="utf-8") as f:
            json.dump(ref.to_dict(), f, indent=2)

        return path

    def load(self, name: str) -> ReferenceSequence:
        """
        Load a reference sequence by exercise name.

        Raises:
            FileNotFoundError: if no reference exists for the given name.
        """
        path = self.directory / f"{name}.json"
        if not path.exists():
            available = self.list_exercises()
            raise FileNotFoundError(
                f"No reference found for exercise '{name}'. "
                f"Available: {available or ['none — record one first']}"
            )

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return ReferenceSequence.from_dict(data)

    def delete(self, name: str) -> None:
        """Delete a reference by exercise name."""
        path = self.directory / f"{name}.json"
        if not path.exists():
            raise FileNotFoundError(f"Reference '{name}' not found.")
        path.unlink()

    def list_exercises(self) -> List[str]:
        """Return names of all stored reference exercises."""
        return sorted(
            p.stem for p in self.directory.glob("*.json")
        )

    def exists(self, name: str) -> bool:
        return (self.directory / f"{name}.json").exists()
