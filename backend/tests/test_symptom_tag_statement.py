"""Public symptom-tag wording uses observed counts even when lift is the gate."""

from types import SimpleNamespace

from app.services.insights.symptoms import _symptom_tag_statement


def test_statement_uses_natural_frequencies_for_both_lift_directions() -> None:
    for lift in (0.5, 2.1):
        finding = SimpleNamespace(
            symptom=SimpleNamespace(label="Headache"),
            tag=SimpleNamespace(label="Sport"),
            co_count=4,
            symptom_count=6,
            tag_count=8,
            lift=lift,
            weekday_confounded=False,
            work_context_confounded=False,
            calendar_context_confounded=False,
        )
        statement = _symptom_tag_statement(finding)
        assert "4 of 6 days" in statement
        assert "8 days with the tag" in statement
        assert "expected" not in statement
