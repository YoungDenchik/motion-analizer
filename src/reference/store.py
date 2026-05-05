"""
Reference exercise storage.

Reference sequences are the "gold standard" — ideal movement patterns
that user sequences are compared against.

Storage format: one JSON file per exercise variant, stored in a configurable
directory. JSON was chosen over binary formats for human-readability and
portability.

Naming convention
─────────────────
A single reference per exercise:
    references/squat.json

Multiple variants (different angles, technique styles, etc.):
    references/squat.json          ← default / side-view
    references/squat_front.json    ← front-facing camera
    references/squat_lowbar.json   ← powerlifting low-bar technique

ReferenceStore.find_best_match() selects the variant whose MotionSignature
is closest to the incoming user time series (cosine similarity on a 99-dim
embedding).  When only one variant exists it is returned directly without
computing signatures.

Backward compatibility
──────────────────────
Older JSON files without a "signature" field are supported — the signature
is recomputed on load and written back only if explicitly re-saved.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from ..timeseries.builder import TimeSeries
from .signature import MotionSignature


DEFAULT_REFERENCES_DIR = Path(__file__).parent.parent.parent / "references"


@dataclass
class ReferenceSequence:
    """A stored reference exercise sequence with its motion signature."""

    name: str
    description: str
    time_series: TimeSeries
    signature: MotionSignature
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "time_series": self.time_series.to_dict(),
            "signature": self.signature.to_dict(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ReferenceSequence":
        ts = TimeSeries.from_dict(d["time_series"])
        if "signature" in d:
            sig = MotionSignature.from_dict(d["signature"])
        else:
            # Older file — compute on the fly (backward compat)
            sig = MotionSignature.from_timeseries(ts)
        return cls(
            name=d["name"],
            description=d["description"],
            time_series=ts,
            signature=sig,
            metadata=d.get("metadata", {}),
        )


class ReferenceStore:
    """
    CRUD operations for reference exercise sequences.

    Supports multiple variants per exercise (different camera angles,
    technique styles) via a shared name prefix:
        squat.json, squat_front.json, squat_lowbar.json
    all belong to the "squat" exercise family.
    """

    def __init__(self, directory: str | Path = DEFAULT_REFERENCES_DIR):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    # ── Write ─────────────────────────────────────────────────────────────────

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

        The MotionSignature is computed automatically and stored alongside
        the time series data so that find_best_match() can run without
        re-processing the full pose pipeline.

        Args:
            name: Unique identifier (e.g. "squat", "squat_front").
            time_series: The reference TimeSeries to store.
            description: Human-readable label.
            metadata: Arbitrary key-value pairs (author, date, notes, …).
            overwrite: If False and file exists, raises FileExistsError.
        """
        path = self.directory / f"{name}.json"
        if path.exists() and not overwrite:
            raise FileExistsError(
                f"Reference '{name}' already exists at {path}. "
                "Pass overwrite=True to replace it."
            )

        sig = MotionSignature.from_timeseries(time_series)
        ref = ReferenceSequence(
            name=name,
            description=description,
            time_series=time_series,
            signature=sig,
            metadata=metadata or {},
        )
        with open(path, "w", encoding="utf-8") as f:
            json.dump(ref.to_dict(), f, indent=2)

        return path

    # ── Read ──────────────────────────────────────────────────────────────────

    def load(self, name: str) -> ReferenceSequence:
        """
        Load a reference by its exact name.

        Raises FileNotFoundError if the name does not exist.
        """
        path = self.directory / f"{name}.json"
        if not path.exists():
            available = self.list_exercises()
            raise FileNotFoundError(
                f"No reference found for '{name}'. "
                f"Available: {available or ['none — record one first']}"
            )
        return self._load_path(path)

    def load_family(self, exercise: str) -> List[ReferenceSequence]:
        """
        Load all references whose name matches the exercise family.

        A file belongs to the family when its stem equals the exercise name
        exactly (e.g. 'squat') or starts with '{exercise}_' (e.g.
        'squat_front', 'squat_lowbar').  This avoids 'squats.json' being
        matched when searching for 'squat'.

        Raises FileNotFoundError if no files match.
        """
        refs = []
        for path in sorted(self.directory.glob("*.json")):
            stem = path.stem
            if stem == exercise or stem.startswith(exercise + "_"):
                refs.append(self._load_path(path))

        if not refs:
            available = self.list_exercises()
            raise FileNotFoundError(
                f"No references found for exercise family '{exercise}'. "
                f"Available: {available or ['none — record one first']}"
            )
        return refs

    def find_best_match(
        self,
        user_ts: TimeSeries,
        exercise: str,
    ) -> ReferenceSequence:
        """
        Return the reference variant whose motion signature best matches
        the user's time series.

        When only one variant exists it is returned immediately (no
        signature computation needed).  When multiple variants exist the
        user's signature is compared against each stored signature using
        cosine distance; the closest match is returned.

        Args:
            user_ts: The user's full-session time series.
            exercise: Exercise family name (e.g. "squat").

        Returns:
            The best-matching ReferenceSequence.
        """
        candidates = self.load_family(exercise)

        if len(candidates) == 1:
            return candidates[0]

        user_sig = MotionSignature.from_timeseries(user_ts)
        ranked = sorted(candidates, key=lambda r: user_sig.distance(r.signature))

        best = ranked[0]
        print(
            f"[ReferenceStore] {len(candidates)} variants for '{exercise}' — "
            f"best match: '{best.name}' "
            f"(dist={user_sig.distance(best.signature):.3f})"
        )
        for ref in ranked[1:]:
            print(
                f"[ReferenceStore]   skipped: '{ref.name}' "
                f"(dist={user_sig.distance(ref.signature):.3f})"
            )

        return best

    # ── Introspection ─────────────────────────────────────────────────────────

    def delete(self, name: str) -> None:
        path = self.directory / f"{name}.json"
        if not path.exists():
            raise FileNotFoundError(f"Reference '{name}' not found.")
        path.unlink()

    def list_exercises(self) -> List[str]:
        """Return names of all stored reference files (stems)."""
        return sorted(p.stem for p in self.directory.glob("*.json"))

    def exists(self, name: str) -> bool:
        return (self.directory / f"{name}.json").exists()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _load_path(self, path: Path) -> ReferenceSequence:
        with open(path, "r", encoding="utf-8") as f:
            return ReferenceSequence.from_dict(json.load(f))
