from canonical.models import Conflict, ResolutionResult


def resolve_conflict(conflict: Conflict) -> ResolutionResult:

    return ResolutionResult(
        conflict_id=conflict.id,
        status="NEEDS_HUMAN_REVIEW",
        selected_value=None,
        reason="Conflicting values require human review.",
        strategy="manual_review"
    )