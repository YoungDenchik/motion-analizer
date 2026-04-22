"""
Human-readable feedback generation from classified error events.

Design philosophy:
  - Rule-based over LLM: deterministic, fast, no external API needed
  - Positive framing: "keep your back straight" not "your back is bad"
  - Prioritized: critical injury-risk feedback appears first
  - Concise: each message is 1-2 sentences, immediately actionable
  - Deduplicated: don't repeat the same advice for bilateral errors
    (left and right) unless they differ in severity

Message structure:
  Each rule maps (feature_name, direction) → (short_cue, explanation)
  where short_cue is a coach-style verbal cue and explanation is
  additional context.

Post-workout summary includes:
  - Overall score and grade
  - Top 3 issues to work on
  - One positive reinforcement message if score > 70
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Optional

from ..evaluation.classifier import ErrorEvent, ErrorSeverity, ErrorDirection
from ..evaluation.scorer import ScoreReport


# ---------------------------------------------------------------------------
# Rule definitions
# Each entry: (feature_name, direction) → {cue, explanation}
# ---------------------------------------------------------------------------
_RULES: Dict[tuple, dict] = {
    # ── Knee angles ─────────────────────────────────────────────────────────
    ("left_knee_angle", ErrorDirection.BELOW_REFERENCE): {
        "cue": "Bend your left knee more",
        "explanation": "You're not reaching full depth. Drive your knee forward over your toes.",
    },
    ("left_knee_angle", ErrorDirection.ABOVE_REFERENCE): {
        "cue": "Don't lock out your left knee",
        "explanation": "Your left knee is hyperextending. Keep a slight bend at the top.",
    },
    ("right_knee_angle", ErrorDirection.BELOW_REFERENCE): {
        "cue": "Bend your right knee more",
        "explanation": "You're not reaching full depth on the right side.",
    },
    ("right_knee_angle", ErrorDirection.ABOVE_REFERENCE): {
        "cue": "Avoid locking your right knee",
        "explanation": "Hyperextension increases joint stress. Maintain a soft knee at full extension.",
    },

    # ── Hip angles ───────────────────────────────────────────────────────────
    ("left_hip_angle", ErrorDirection.BELOW_REFERENCE): {
        "cue": "Open up your left hip",
        "explanation": "You need more hip flexion on the left. Push your hips back further.",
    },
    ("left_hip_angle", ErrorDirection.ABOVE_REFERENCE): {
        "cue": "Hinge at the hips more on the left",
        "explanation": "Reduce left hip angle — you may be over-extending at the top.",
    },
    ("right_hip_angle", ErrorDirection.BELOW_REFERENCE): {
        "cue": "Push your right hip back more",
        "explanation": "Right hip needs greater flexion for optimal depth.",
    },
    ("right_hip_angle", ErrorDirection.ABOVE_REFERENCE): {
        "cue": "Control your right hip extension",
        "explanation": "You're going past optimal range on the right hip.",
    },

    # ── Elbow angles ─────────────────────────────────────────────────────────
    ("left_elbow_angle", ErrorDirection.BELOW_REFERENCE): {
        "cue": "Extend your left arm more",
        "explanation": "Your left elbow isn't reaching full range of motion.",
    },
    ("left_elbow_angle", ErrorDirection.ABOVE_REFERENCE): {
        "cue": "Control your left elbow",
        "explanation": "Your left elbow is flaring beyond the reference position.",
    },
    ("right_elbow_angle", ErrorDirection.BELOW_REFERENCE): {
        "cue": "Extend your right arm fully",
        "explanation": "Incomplete right arm extension reduces power output.",
    },
    ("right_elbow_angle", ErrorDirection.ABOVE_REFERENCE): {
        "cue": "Keep your right elbow in",
        "explanation": "Right elbow flare can stress the joint and reduce efficiency.",
    },

    # ── Shoulder angles ──────────────────────────────────────────────────────
    ("left_shoulder_angle", ErrorDirection.ABOVE_REFERENCE): {
        "cue": "Lower your left shoulder",
        "explanation": "Your left shoulder is rising. Keep it packed and stable.",
    },
    ("left_shoulder_angle", ErrorDirection.BELOW_REFERENCE): {
        "cue": "Raise your left shoulder",
        "explanation": "Left shoulder is too depressed for this movement.",
    },
    ("right_shoulder_angle", ErrorDirection.ABOVE_REFERENCE): {
        "cue": "Lower your right shoulder",
        "explanation": "Right shoulder elevation reduces stability. Keep it down.",
    },
    ("right_shoulder_angle", ErrorDirection.BELOW_REFERENCE): {
        "cue": "Lift your right shoulder",
        "explanation": "Right shoulder needs to come up to match the reference position.",
    },

    # ── Torso lean ───────────────────────────────────────────────────────────
    ("torso_lean", ErrorDirection.ABOVE_REFERENCE): {
        "cue": "Keep your chest up - don't lean forward",
        "explanation": (
            "Excessive forward lean increases spinal load. Brace your core, "
            "keep your chest up, and drive through your heels."
        ),
    },
    ("torso_lean", ErrorDirection.BELOW_REFERENCE): {
        "cue": "Lean forward slightly",
        "explanation": (
            "You're too upright for this movement. A controlled forward lean "
            "is needed for hip engagement."
        ),
    },
}

_POSITIVE_MESSAGES = [
    "Great work overall — your form is solid!",
    "Good technique! Focus on the details to reach the next level.",
    "You're moving well. Small refinements will make a big difference.",
]

_GRADE_MESSAGES = {
    "A": "Excellent technique! You're moving like a pro.",
    "B": "Good technique with room for minor improvements.",
    "C": "Decent form. Consistent practice will help you improve.",
    "D": "Your technique needs work. Focus on the critical cues below.",
    "F": "Significant form issues detected. Consider working with a trainer.",
}


@dataclass
class FeedbackItem:
    """A single feedback message with metadata."""
    cue: str                     # Short coaching cue
    explanation: str             # Longer explanation
    severity: ErrorSeverity
    feature: str
    mean_deviation_deg: float


@dataclass
class FeedbackReport:
    """Complete post-workout feedback."""
    items: List[FeedbackItem]    # Prioritized feedback items
    overall_score: float
    grade: str
    grade_message: str
    summary: str                 # One-paragraph narrative summary

    def print(self):
        """Print a formatted feedback report to stdout."""
        print("\n" + "=" * 60)
        print(f"  TECHNIQUE ANALYSIS REPORT")
        print("=" * 60)
        print(f"  Score:  {self.overall_score:.1f}/100  [{self.grade}]")
        print(f"  {self.grade_message}")
        print("=" * 60)

        if not self.items:
            print("\n  No significant deviations detected. Excellent form!")
        else:
            print(f"\n  FEEDBACK ({len(self.items)} issue(s) found):\n")
            for i, item in enumerate(self.items, 1):
                severity_tag = "[CRITICAL]" if item.severity == ErrorSeverity.CRITICAL else "[TECHNICAL]"
                print(f"  {i}. {severity_tag} {item.cue}")
                print(f"     {item.explanation}")
                print(f"     (avg deviation: {item.mean_deviation_deg:.1f} deg)")
                print()

        print(f"  SUMMARY:\n  {self.summary}")
        print("=" * 60 + "\n")


class FeedbackGenerator:
    """
    Converts ErrorEvents and a ScoreReport into actionable feedback.

    Deduplication: if both left and right sides have the same error type,
    they are merged into a single bilateral cue ("Keep your knees aligned")
    rather than two separate messages.
    """

    def __init__(self, max_items: int = 5):
        """
        Args:
            max_items: Maximum number of feedback items to return.
                       Prioritizes critical errors; truncates technical ones.
        """
        self.max_items = max_items

    def generate(
        self,
        error_events: List[ErrorEvent],
        score_report: ScoreReport,
    ) -> FeedbackReport:
        """
        Generate a FeedbackReport from classified error events and scores.
        """
        items: List[FeedbackItem] = []
        seen_keys: set[tuple] = set()

        for event in error_events:
            key = (event.feature_name, event.direction)
            rule = _RULES.get(key)
            if rule is None:
                continue

            # Deduplicate bilateral errors
            dedup_key = self._bilateral_key(event)
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)

            items.append(FeedbackItem(
                cue=rule["cue"],
                explanation=rule["explanation"],
                severity=event.severity,
                feature=event.feature_name,
                mean_deviation_deg=event.mean_deviation_deg,
            ))

            if len(items) >= self.max_items:
                break

        grade = score_report.grade
        summary = self._build_summary(items, score_report)

        return FeedbackReport(
            items=items,
            overall_score=score_report.overall_score,
            grade=grade,
            grade_message=_GRADE_MESSAGES[grade],
            summary=summary,
        )

    @staticmethod
    def _bilateral_key(event: ErrorEvent) -> tuple:
        """
        Collapse left/right variants of the same feature to a single key,
        so we don't output duplicate messages for symmetric issues.
        """
        name = event.feature_name.replace("left_", "").replace("right_", "")
        return (name, event.direction)

    @staticmethod
    def _build_summary(items: List[FeedbackItem], score: ScoreReport) -> str:
        if not items:
            return (
                f"Outstanding form with a score of {score.overall_score:.0f}/100. "
                "Keep up the great work!"
            )

        critical = [i for i in items if i.severity == ErrorSeverity.CRITICAL]
        technical = [i for i in items if i.severity == ErrorSeverity.TECHNICAL]

        parts = [f"Your score is {score.overall_score:.0f}/100."]

        if critical:
            issues = ", ".join(i.feature.replace("_", " ") for i in critical[:2])
            parts.append(
                f"Priority: address the critical issue(s) with {issues} "
                "to reduce injury risk."
            )

        if technical:
            issues = ", ".join(i.feature.replace("_", " ") for i in technical[:2])
            parts.append(
                f"For efficiency, also work on your {issues}."
            )

        if score.overall_score >= 70:
            parts.append("Overall, you have a solid base to build on.")

        return " ".join(parts)
