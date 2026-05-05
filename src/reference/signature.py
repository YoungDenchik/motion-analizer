"""
Motion signature: compact fixed-length embedding of a TimeSeries.

Used to automatically select the best-matching reference when multiple
references exist for the same exercise (different camera angles, technique
variants, etc.).

Why canonical rep, not the whole session
─────────────────────────────────────────
The signature is computed on the *canonical rep* — the single averaged rep
produced by RepSegmenter + _build_canonical_rep — rather than on the full
recording.  Computing on the whole session would contaminate every statistic:

  • mean / p10 / p90 are diluted by approach and cooldown frames where the
    person is standing still, not exercising.
  • skewness measures session-level asymmetry instead of within-rep motion
    pattern (slow descent vs slow ascent).
  • vel_asymmetry is pulled toward 0.5 by the many near-zero-velocity frames
    between reps and at the start/end of the recording.
  • correlations are polluted by the at-rest frames where joints don't move
    at all, washing out the genuine within-rep coupling pattern.
  • Two recordings of the exact same technique but different rep counts
    produce different whole-session signatures purely because the
    rest-vs-exercise frame ratio differs.

Computing on the canonical rep eliminates all of these problems: the signal
contains one clean, complete oscillation cycle with no extraneous frames,
and the statistics are invariant to how many reps were performed.

Dimension breakdown (F = number of features = 9 in this project):

  Component           Dims    What it captures
  ──────────────────────────────────────────────────────────────────────
  mean                F       Mid-movement posture (not diluted by rest).
                              Also encodes camera projection — the same
                              knee angle appears ~130° from the side,
                              ~155° from the front.

  std                 F       Range of motion per joint within one rep.
                              Lower from the front (depth projects away).

  p10 / p90           2F      Robust low / high extremes — how deep the
                              squat goes, how straight the joint returns.
                              More stable than min/max on short sequences.

  skewness            F       Within-rep time asymmetry.  Negative = more
                              time near the low extreme (slow descent, fast
                              ascent).  Positive = the opposite.

  mean_abs_velocity   F       Mean |velocity| in deg/s within the rep.
                              Separates tempo work from explosive lifting.

  velocity_asymmetry  F       Fraction of rep frames where each joint is
                              moving in the extending / opening direction.
                              0.5 = symmetric.  >0.5 = faster extension
                              (explosive concentric); <0.5 = faster flexion.

  correlations     F(F-1)/2   Pearson pairwise coupling between all joints
                              within the rep.  Fingerprints technique style:
                              hip-dominant vs quad-dominant squat have
                              different knee/hip correlation.

  For F=9: 7×9 + 36 = 99 dimensions total.

Matching
────────
Cosine similarity (not Euclidean distance) is used so that large-scale
features (mean knee_angle ≈ 120°) don't drown small-scale features (mean
torso_lean ≈ 10°).  Only the direction of the embedding matters — capturing
the shape of the movement pattern rather than its absolute magnitude.
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
        """
        Compute the signature from a TimeSeries.

        Internally segments the sequence, builds the canonical (averaged) rep,
        and computes all statistics on that single clean cycle.  Falls back to
        the whole sequence when only one rep is detected — this happens for
        short reference recordings that already contain exactly one rep, which
        is fine: a 1-rep sequence IS the canonical rep.
        """
        canonical = cls._extract_canonical(ts)
        return cls._from_array(canonical.data, canonical.fps, ts.feature_names)

    @staticmethod
    def _extract_canonical(ts: TimeSeries) -> TimeSeries:
        """
        Segment ts and return the averaged canonical rep.

        Uses lazy imports to avoid module-level circular-import issues;
        neither segmentation nor rep_comparator imports from reference/.
        """
        from ..timeseries.segmentation import RepSegmenter
        from ..comparison.rep_comparator import RepComparator

        seg = RepSegmenter().segment(ts)
        canonical, _ = RepComparator._build_canonical_rep(seg.reps)
        return canonical

    @classmethod
    def _from_array(
        cls,
        data: np.ndarray,
        fps: float,
        feature_names: List[str],
    ) -> "MotionSignature":
        """
        Pure statistics computation on a (T, F) array.

        Separated from _extract_canonical so it can be called directly
        when the canonical rep is already available (e.g. in tests or when
        the RepComparator has already done the segmentation).
        """
        data = data.astype(float)
        T, F = data.shape

        # ── Per-feature statistics ────────────────────────────────────────────
        mean = data.mean(axis=0)                              # (F,)
        std  = data.std(axis=0)                               # (F,)
        p10  = np.percentile(data, 10, axis=0)                # (F,)
        p90  = np.percentile(data, 90, axis=0)                # (F,)

        skewness = scipy_skew(data, axis=0)                   # (F,)
        skewness = np.nan_to_num(skewness, nan=0.0)

        if T > 1:
            vel = np.diff(data, axis=0) * fps                 # (T-1, F)  deg/s
            mean_abs_vel  = np.abs(vel).mean(axis=0)          # (F,)
            vel_asymmetry = (vel > 0).mean(axis=0)            # (F,)
        else:
            mean_abs_vel  = np.zeros(F)
            vel_asymmetry = np.full(F, 0.5)

        per_feature = np.concatenate([
            mean, std, p10, p90, skewness, mean_abs_vel, vel_asymmetry,
        ])   # 7F = 63

        # ── Inter-joint correlations (upper triangle) ─────────────────────────
        if T > 1 and (std > 0).sum() >= 2:
            corr = np.corrcoef(data.T)                        # (F, F)
        else:
            corr = np.eye(F)

        rows, cols = np.triu_indices(F, k=1)
        correlations = np.nan_to_num(corr[rows, cols], nan=0.0)   # F(F-1)/2 = 36

        vector = np.concatenate([per_feature, correlations]).astype(np.float32)
        return cls(vector=vector, feature_names=list(feature_names))

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
