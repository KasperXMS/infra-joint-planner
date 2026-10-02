"""Versioned secondary metric; never replaces the benchmark's original evaluator."""

import re
from typing import Literal

from infra_joint.core.base import ContractModel

METRIC_ID = "multihop_yesno_canonical_v1"
Direction = Literal["yes", "no", "unresolved"]


class YesNoAuditResult(ContractModel):
    metric_id: str = METRIC_ID
    metric_role: str = "post-hoc audit metric, not original benchmark score"
    canonical_yesno: Direction
    format_category: str
    canonical_score: float | None


def canonical_yesno(answer: str | None) -> Direction:
    """Read an explicit leading label only; never infer from explanatory prose.

    Balanced leading bold/italic markup is supported. Immediate alternatives such
    as 'Yes/no', 'Yes or no', and 'Yes and no' are ambiguous and fail closed.
    Question marks and unfinished markup are not assertions.
    """
    if answer is None:
        return "unresolved"
    text = answer.strip()
    for marker in ("**", "__", "*", "_"):
        if text.startswith(marker):
            end = text.find(marker, len(marker))
            if end < 0:
                return "unresolved"
            label = text[len(marker) : end]
            if re.fullmatch(r"(?i)(yes|no)[.,:!]?", label) is None:
                return "unresolved"
            text = label + text[end + len(marker) :]
            break
    match = re.match(r"(?i)^(yes|no)(?=$|[\s.,:!/?;])", text)
    if match is None:
        return "unresolved"
    rest = text[match.end() :]
    if rest.startswith("?") or re.match(r"(?i)^[\s.,:!;/]*(?:or\s+|and\s+)?(?:yes|no)\b", rest):
        return "unresolved"
    return "yes" if match.group(1).lower() == "yes" else "no"


def audit_yesno(answer: str | None, *, reference: str | None = None) -> YesNoAuditResult:
    """Extraction is independent of the private reference. Unknown is never scored."""
    direction = canonical_yesno(answer)
    if answer is None or not answer.strip():
        category = "no terminal answer"
    elif direction == "unresolved":
        category = "unresolved"
    elif direction == "no":
        category = "negative/no"
    elif answer.strip().lower() == "yes":
        category = "exact yes"
    elif answer.lstrip().startswith(("**", "__", "*", "_")):
        category = "markdown yes"
    elif re.match(r"(?i)^yes[.,:!]", answer.strip()):
        category = "punctuated yes"
    else:
        category = "affirmative prose"
    score = None
    if reference is not None:
        # Only a private, canonical label can supply a reference; no gold prose inference.
        target = reference.strip().lower()
        if target not in {"yes", "no"}:
            raise ValueError("secondary yes/no metric requires a canonical yes/no reference")
        if direction != "unresolved":
            score = float(direction == target)
    return YesNoAuditResult(
        canonical_yesno=direction,
        format_category=category,
        canonical_score=score,
    )
