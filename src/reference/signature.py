"""
Motion signature: compact fixed-length embedding of a TimeSeries.

Used to automatically select the best-matching reference when multiple
references exist for the same exercise (different camera angles, technique
variants, etc.).

Dimension breakdown (F = number of features = 9 in this project):

  Component           Dims    What it captures
  ──────────────────────────────────────────────────────────────────────
  mean                F       Typical joint angle.  Encodes habitual
                              posture AND camera projection angle — the
                              same knee angle looks different from the
                              side (~130° mean) vs the front (~155°).

  std                 F       Range of motion per joint.  Side-view
                              recordings show full amplitude; front-view
                              recordings project most depth-axis motion
                              away, so std is lower.

  p10 / p90           2F      Robust low / high extremes (10th and 90th
                              percentile).  Better than min/max for noisy
                              signals.  p10 captures how deep the squat
                              goes; p90 captures how straight it returns.

  skewness            F       Time asymmetry of each joint.  Negative =
                              more time at low extreme (long descent, fast
                              ascent).  Positive = more time at high
                              extreme (explosive descent, slow ascent).
                              Distinguishes technique styles even at the
                              same camera angle.

  mean_abs_velocity   F       Mean |velocity| in deg/s.  Separates tempo
                              work (low) from explosive lifting (high).
                              Also differs by camera angle — faster-
                              appearing motion from the side than the front.

  velocity_asymmetry  F       Fraction of frames where each joint is
                              moving in the positive direction (extending /
                              opening).  0.5 = symmetric speed.  >0.5 =
                              faster extension (explosive concentric).
                              <0.5 = faster flexion (slow eccentric).

  correlations     F(F-1)/2   Upper triangle of the F×F Pearson
                              correlation matrix.  Encodes joint coupling
                              patterns — how much do the hip and knee move
                              together?  This fingerprints technique style
                              (hip-dominant vs quad-dominant squat) better
                              than any single-joint statistic.

  For F=9: 7×9 + 36 = 99 dimensions total.

Matching
────────
Cosine similarity is used instead of Euclidean distance so that features
with large natural scale (mean knee_angle ≈ 120°) do not dominate features
with small natural scale (mean torso_lean ≈ 10°).  Both vectors are L2-
normalised before the dot product, so only the *direction* of the embedding
matters — capturing the shape of the movement pattern rather than its
absolute magnitude.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np
from scipy.stats import skew as scipy_skew

from ..timeseries.builder import TimeSeries


@dataclass
class MotionSignature:
    """Fixed-length embedding of a TimeSeries for reference matching."""

    vector: np.ndarray        # (DIM,) float32
    feature_names: List[str]  # kept for debugging / introspection

    # ── Construction ──────────────────────────────────────────────────────────

    @classmethod
    def from_timeseries(cls, ts: TimeSeries) -> "MotionSignature":
        """Compute the full signature from a TimeSeries."""
        data = ts.data.astype(float)   # (T, F)
        T, F = data.shape

        # ── Per-feature statistics ────────────────────────────────────────────
        mean = data.mean(axis=0)                          # (F,)
        std  = data.std(axis=0)                           # (F,)
        p10  = np.percentile(data, 10, axis=0)            # (F,)
        p90  = np.percentile(data, 90, axis=0)            # (F,)

        skewness = scipy_skew(data, axis=0)               # (F,)
        skewness = np.nan_to_num(skewness, nan=0.0)

        if T > 1:
            vel = np.diff(data, axis=0) * ts.fps          # (T-1, F)  deg/s
            mean_abs_vel   = np.abs(vel).mean(axis=0)     # (F,)
            vel_asymmetry  = (vel > 0).mean(axis=0)       # (F,)  fraction positive
        else:
            mean_abs_vel  = np.zeros(F)
            vel_asymmetry = np.full(F, 0.5)

        per_feature = np.concatenate([
            mean, std, p10, p90, skewness, mean_abs_vel, vel_asymmetry,
        ])   # 7F = 63

        # ── Inter-joint correlations (upper triangle) ─────────────────────────
        # Only meaningful when joints actually move (std > 0 for at least 2).
        if T > 1 and (std > 0).sum() >= 2:
            corr = np.corrcoef(data.T)                    # (F, F)
        else:
            corr = np.eye(F)

        rows, cols = np.triu_indices(F, k=1)              # upper triangle, no diag
        correlations = np.nan_to_num(corr[rows, cols], nan=0.0)   # F(F-1)/2 = 36

        vector = np.concatenate([per_feature, correlations]).astype(np.float32)
        return cls(vector=vector, feature_names=list(ts.feature_names))

    # ── Similarity ────────────────────────────────────────────────────────────

    def cosine_similarity(self, other: "MotionSignature") -> float:
        """
        Cosine similarity in [-1, 1].  Higher = more similar.

        Scale-invariant: a side-view knee angle oscillating over 80° and
        a torso_lean oscillating over 15° contribute equally to the match
        score.  Raw Euclidean distance would let the large-scale feature
        dominate entirely.
        """
        a, b = self.vector, other.vector
        na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
        if na == 0.0 or nb == 0.0:
            return 0.0
        return float(np.dot(a, b) / (na * nb))

    def distance(self, other: "MotionSignature") -> float:
        """Cosine distance in [0, 2].  Lower = more similar."""
        return 1.0 - self.cosine_similarity(other)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "vector": self.vector.tolist(),
            "feature_names": self.feature_names,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MotionSignature":
        return cls(
            vector=np.array(d["vector"], dtype=np.float32),
            feature_names=d["feature_names"],
        )

    # ── Diagnostics ───────────────────────────────────────────────────────────

    def describe(self) -> str:
        """Human-readable breakdown of the signature components."""
        F = len(self.feature_names)
        labels = [
            "mean", "std", "p10", "p90",
            "skewness", "mean_abs_vel", "vel_asymmetry",
        ]
        lines = [f"MotionSignature  dim={len(self.vector)}"]
        for i, label in enumerate(labels):
            block = self.vector[i * F: (i + 1) * F]
            lines.append(
                f"  {label:18s}  "
                + "  ".join(f"{v:+.2f}" for v in block)
            )
        corr_block = self.vector[7 * F:]
        lines.append(
            f"  {'correlations':18s}  "
            f"min={corr_block.min():+.2f}  "
            f"mean={corr_block.mean():+.2f}  "
            f"max={corr_block.max():+.2f}"
        )
        return "\n".join(lines)
