import copy

import pytest

from gnuquebecepicerie.normalizers.quality import quality_report


def report():
    return {
        "normalizer_version": "test", "review_registry_sha256": "a" * 64,
        "source_entries": 5, "accepted_entries": 3, "rejected_entries": 1,
        "skipped_entries": 1, "incomplete_entries": 1, "offers_count": 6,
        "duplicate_offers_removed": 2,
        "rejected": [{"index": 3}], "skipped": [{"index": 4}],
        "incomplete": [{"index": 1}],
        "applied_source_reviews": [{"index": 1}, {"index": 3}],
    }


def test_coverage_counts_entries_not_offers_and_does_not_approve_reviews():
    source = report()
    before = copy.deepcopy(source)
    result = quality_report(source)
    assert source == before
    assert result["review_coverage"] == {
        "unit": "source_entry", "entries_with_recorded_review": 2,
        "accepted_with_recorded_review": 1, "accepted_without_recorded_review": 2,
        "accepted_review_coverage_percent": 33.33,
        "commercial_validation": "not_recorded",
    }
    assert not result["ready_for_archive"]
    assert "incomplete_conditions" in result["blocking_reasons"]
    assert "rejected_entries" in result["blocking_reasons"]


def test_all_entries_reviewed_still_requires_commercial_validation():
    source = report()
    source.update(source_entries=1, accepted_entries=1, rejected_entries=0,
                  skipped_entries=0, incomplete_entries=0, rejected=[], skipped=[],
                  incomplete=[], applied_source_reviews=[{"index": 0}])
    result = quality_report(source)
    assert result["review_coverage"]["accepted_review_coverage_percent"] == 100
    assert result["blocking_reasons"] == [
        "commercial_validation_not_recorded", "archiving_disabled",
    ]
    assert not result["ready_for_archive"]


@pytest.mark.parametrize("change", [
    {"source_entries": 6}, {"rejected_entries": 2},
    {"skipped": [{"index": 3}]}, {"incomplete": [{"index": 3}]},
    {"applied_source_reviews": [{"index": 5}]},
    {"applied_source_reviews": [{"index": -1}]},
])
def test_inconsistent_accounting_fails_closed(change):
    with pytest.raises(ValueError, match="Comptage"):
        quality_report({**report(), **change})


def test_no_accepted_entries_has_no_misleading_percentage():
    source = report()
    source.update(source_entries=0, accepted_entries=0, rejected_entries=0,
                  skipped_entries=0, incomplete_entries=0, offers_count=0,
                  rejected=[], skipped=[], incomplete=[], applied_source_reviews=[])
    result = quality_report(source)
    assert result["review_coverage"]["accepted_review_coverage_percent"] is None
    assert "no_offers" in result["blocking_reasons"]
