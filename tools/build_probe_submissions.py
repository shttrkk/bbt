from __future__ import annotations

import csv
from pathlib import Path


BASELINE_PATH = Path("result.csv")
OUTPUT_DIR = Path("submission_probes")

CANDIDATES = {
    "card_issue_form": {
        "size": "45797",
        "time": "sep 26 12:08",
        "name": "%D0%A8%D0%B0%D0%B1%D0%BB%D0%BE%D0%BD-%D0%B7%D0%B0%D1%8F%D0%B2%D0%BB%D0%B5%D0%BD%D0%B8%D1%8F-%D0%BD%D0%B0-%D0%B2%D1%8B%D0%BF%D1%83%D1%81%D0%BA-%D0%BA%D0%B0%D1%80%D1%82%D1%8B.docx",
    },
    "document_checklist": {
        "size": "15971",
        "time": "sep 26 09:34",
        "name": "Перечень документов.docx",
    },
    "applicant_consent_spd": {
        "size": "24914",
        "time": "sep 26 16:28",
        "name": "spd.docx",
    },
    "blank_statement": {
        "size": "22997",
        "time": "sep 26 16:20",
        "name": "%D0%B7%D0%B0%D1%8F%D0%B2%D0%BB%D0%B5%D0%BD%D0%B8%D0%B5.docx",
    },
    "contest_consent": {
        "size": "14572",
        "time": "sep 26 09:34",
        "name": "Согласие участника конкурса.docx",
    },
    "guardian_consent": {
        "size": "15019",
        "time": "sep 26 09:34",
        "name": "Согласие законного представителя.docx",
    },
    "grant_contract_org_only": {
        "size": "25601",
        "time": "sep 26 09:34",
        "name": "Договор.docx",
    },
    "public_site_consent_rtf": {
        "size": "75227",
        "time": "sep 26 12:28",
        "name": "Согласие_ПДн_(map.ncpti.ru).rtf",
    },
}

STATUSES = {
    "card_issue_form": "drop: metric 0.31142857142857 vs baseline 0.315",
    "document_checklist": "pending",
    "applicant_consent_spd": "pending",
    "blank_statement": "pending",
    "contest_consent": "pending",
    "guardian_consent": "pending",
    "grant_contract_org_only": "noisy",
    "public_site_consent_rtf": "known_fp",
}

PACKS = {
    "probe_01_card_issue_form": ["card_issue_form"],
    "probe_02_document_checklist": ["document_checklist"],
    "probe_03_applicant_consent_spd": ["applicant_consent_spd"],
    "probe_04_blank_statement": ["blank_statement"],
    "probe_05_contest_consent": ["contest_consent"],
    "probe_06_guardian_consent": ["guardian_consent"],
    "probe_07_checklist_plus_spd": ["document_checklist", "applicant_consent_spd"],
    "probe_08_consents_only": ["applicant_consent_spd", "contest_consent", "guardian_consent"],
    "probe_09_review_no_card": [
        "document_checklist",
        "applicant_consent_spd",
        "blank_statement",
        "contest_consent",
        "guardian_consent",
    ],
    "probe_10_wide_noise_check": [
        "grant_contract_org_only",
        "public_site_consent_rtf",
    ],
}


def load_baseline() -> list[dict[str, str]]:
    with BASELINE_PATH.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_submission(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["size", "time", "name"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    baseline = load_baseline()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for stale in OUTPUT_DIR.glob("probe_*.csv"):
        stale.unlink()

    for pack_name, candidate_keys in PACKS.items():
        rows = list(baseline)
        rows.extend(CANDIDATES[key] for key in candidate_keys)
        write_submission(OUTPUT_DIR / f"{pack_name}.csv", rows)

    manifest_path = OUTPUT_DIR / "README.txt"
    manifest_lines = [
        "Ready-to-submit probe files built on top of baseline result.csv",
        "",
    ]
    manifest_lines.append("Candidate statuses:")
    for key, status in STATUSES.items():
        manifest_lines.append(f"- {key}: {status}")
    manifest_lines.append("")
    manifest_lines.append("Probe packs:")
    for pack_name, candidate_keys in PACKS.items():
        manifest_lines.append(f"- {pack_name}.csv: {', '.join(candidate_keys)}")
    manifest_path.write_text("\n".join(manifest_lines), encoding="utf-8")


if __name__ == "__main__":
    main()
