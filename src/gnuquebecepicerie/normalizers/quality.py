"""Bilan local de conversion et de couverture, sans approbation commerciale."""

from __future__ import annotations


def quality_report(report: dict) -> dict:
    """Compte des entrées source, pas des offres (une entrée peut en produire plusieurs)."""
    total = report["source_entries"]
    rejected = {item["index"] for item in report["rejected"]}
    skipped = {item["index"] for item in report["skipped"]}
    incomplete = {item["index"] for item in report["incomplete"]}
    reviewed = {item["index"] for item in report["applied_source_reviews"]}
    all_indices = rejected | skipped | incomplete | reviewed
    if (
        any(type(index) is not int or not 0 <= index < total for index in all_indices)
        or rejected & skipped or incomplete & (rejected | skipped)
        or len(rejected) != report["rejected_entries"]
        or len(skipped) != report["skipped_entries"]
        or len(incomplete) != report["incomplete_entries"]
        or report["accepted_entries"] + len(rejected) + len(skipped) != total
    ):
        raise ValueError("Comptage des entrées incohérent; bilan qualité impossible.")
    accepted = set(range(total)) - rejected - skipped
    reviewed_accepted = accepted & reviewed
    blockers = []
    if not report["offers_count"]:
        blockers.append("no_offers")
    if rejected:
        blockers.append("rejected_entries")
    if incomplete:
        blockers.append("incomplete_conditions")
    if accepted - reviewed:
        blockers.append("accepted_entries_without_recorded_review")
    # Une correction ou une exclusion documentée n'est pas une validation exhaustive.
    blockers.extend(["commercial_validation_not_recorded", "archiving_disabled"])
    return {
        "version": 1,
        "normalizer_version": report["normalizer_version"],
        "review_registry_sha256": report["review_registry_sha256"],
        "source_entries": total,
        "accepted_entries": len(accepted),
        "rejected_entries": len(rejected),
        "skipped_entries": len(skipped),
        "incomplete_entries": len(incomplete),
        "offers_count": report["offers_count"],
        "duplicate_offers_removed": report["duplicate_offers_removed"],
        "review_coverage": {
            "unit": "source_entry",
            "entries_with_recorded_review": len(reviewed),
            "accepted_with_recorded_review": len(reviewed_accepted),
            "accepted_without_recorded_review": len(accepted - reviewed),
            "accepted_review_coverage_percent": (
                round(100 * len(reviewed_accepted) / len(accepted), 2) if accepted else None
            ),
            "commercial_validation": "not_recorded",
        },
        "blocking_reasons": blockers,
        "ready_for_archive": False,
    }


def quality_text(quality: dict) -> str:
    coverage = quality["review_coverage"]
    return (
        "Bilan qualité local — archivage désactivé\n"
        f"{quality['source_entries']} entrées source : "
        f"{quality['accepted_entries']} converties, {quality['rejected_entries']} rejetées, "
        f"{quality['skipped_entries']} blocs ignorés.\n"
        f"{quality['offers_count']} offres; "
        f"{quality['duplicate_offers_removed']} doublons d'offres retirés.\n"
        f"{quality['incomplete_entries']} entrées converties aux conditions incomplètes.\n"
        f"Révision consignée pour {coverage['accepted_with_recorded_review']} / "
        f"{quality['accepted_entries']} entrées converties; "
        f"{coverage['accepted_without_recorded_review']} sans révision consignée.\n"
        "Une révision consignée peut ne couvrir qu'un aspect de l'offre.\n"
        "La validation commerciale exhaustive reste à réaliser.\n"
        "Blocages : " + ", ".join(quality["blocking_reasons"]) + "\n"
    )
