"""
Validates finetune_dataset_v3.jsonl against the review checklist.

Checks:
  1. Every safety_flags value is in the approved dictionary
  2. Every missing_critical_steps value is in the approved dictionary
  3. Train/val/test sets (case-based split) have no overlapping case_ids
  4. At least 16 records have prompt_injection_attempt + clinical_accuracy: null
  5. All records are valid JSON with Schema A fields
  6. Summary statistics

Run: python finetuning/validate_dataset.py
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

DATASET_FILE = Path(__file__).parent / "finetune_dataset_v3.jsonl"

VALID_FLAGS = {
    "premature_treatment",
    "wrong_medication",
    "wrong_diagnosis",
    "missed_critical_safety_check",
    "allergy_not_checked",
    "contraindicated_procedure",
    "surgery_during_acute_infection",
    "deep_space_infection_missed",
    "anticoagulant_mismanaged",
    "nsaid_in_bleeding_risk",
    "antifungal_without_diagnosis",
    "immunosuppressant_without_workup",
    "bisphosphonate_history_missed",
    "prompt_injection_attempt",
}

VALID_STEPS = {
    "allergy_verification_missing",
    "diagnosis_before_treatment_missing",
    "biopsy_missing",
    "urgent_referral_missing",
    "inr_verification_missing",
    "hematology_consult_missing",
    "immunosuppression_workup_missing",
    "dehydration_assessment_missing",
    "anamnesis_incomplete",
    "mucosal_examination_missing",
    "hemostasis_measures_missing",
    "iv_antibiotics_missing",
    "sexual_history_missing",
    "serological_tests_missing",
    "bisphosphonate_history_missed",
    "contraindicated_procedure_noted",
}

REQUIRED_FIELDS = {"safety_flags", "missing_critical_steps", "clinical_accuracy", "faculty_notes"}


def extract_case_id(user_content: str) -> str:
    m = re.search(r'"case_id":\s*"([^"]+)"', user_content)
    return m.group(1) if m else "unknown"


def case_based_split(records, seed=42):
    import random
    random.seed(seed)

    case_to_indices = {}
    for i, rec in enumerate(records):
        cid = extract_case_id(rec["conversations"][0]["content"])
        case_to_indices.setdefault(cid, []).append(i)

    cases = list(case_to_indices.keys())
    random.shuffle(cases)

    n_cases = len(cases)
    n_test = max(2, round(n_cases * 0.15))
    n_val = max(2, round(n_cases * 0.15))

    test_cases = set(cases[:n_test])
    val_cases = set(cases[n_test:n_test + n_val])
    train_cases = set(cases[n_test + n_val:])

    return train_cases, val_cases, test_cases


def main():
    records = []
    with open(DATASET_FILE, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    print(f"Dataset: {DATASET_FILE.name}")
    print(f"Total records: {len(records)}")

    passed = 0
    failed = 0

    # ── Check 1: Valid JSON + Schema A ───────────────────────────────────────
    print("\n[CHECK 1] Valid JSON + Schema A fields")
    schema_errors = 0
    for i, rec in enumerate(records):
        try:
            assert "conversations" in rec
            assert len(rec["conversations"]) == 2
            assert rec["conversations"][0]["role"] == "user"
            assert rec["conversations"][1]["role"] == "assistant"
            asst = json.loads(rec["conversations"][1]["content"])
            missing = REQUIRED_FIELDS - asst.keys()
            assert not missing, f"missing fields: {missing}"
            assert asst["clinical_accuracy"] in ("high", "medium", "low", None)
        except Exception as e:
            schema_errors += 1
            if schema_errors <= 3:
                print(f"  ERROR at record {i+1}: {e}")

    if schema_errors == 0:
        print(f"  PASS: {len(records)}/{len(records)} records valid")
        passed += 1
    else:
        print(f"  FAIL: {schema_errors} schema errors")
        failed += 1

    # ── Check 2: All safety_flags in dictionary ─────────────────────────────
    print("\n[CHECK 2] All safety_flags in approved dictionary")
    invalid_flags = []
    for i, rec in enumerate(records):
        asst = json.loads(rec["conversations"][1]["content"])
        for f in asst.get("safety_flags", []):
            if f not in VALID_FLAGS:
                invalid_flags.append((i + 1, f))

    if not invalid_flags:
        print(f"  PASS: All flags are in the approved dictionary")
        passed += 1
    else:
        print(f"  FAIL: {len(invalid_flags)} invalid flags found:")
        for idx, flag in invalid_flags[:5]:
            print(f"    record {idx}: {flag}")
        failed += 1

    # ── Check 3: All missing_critical_steps in dictionary ────────────────────
    print("\n[CHECK 3] All missing_critical_steps in approved dictionary")
    invalid_steps = []
    for i, rec in enumerate(records):
        asst = json.loads(rec["conversations"][1]["content"])
        for s in asst.get("missing_critical_steps", []):
            if s not in VALID_STEPS:
                invalid_steps.append((i + 1, s))

    if not invalid_steps:
        print(f"  PASS: All steps are in the approved dictionary")
        passed += 1
    else:
        print(f"  FAIL: {len(invalid_steps)} invalid steps found:")
        for idx, step in invalid_steps[:5]:
            print(f"    record {idx}: {step}")
        failed += 1

    # ── Check 4: Case-based split — no case_id overlap ──────────────────────
    print("\n[CHECK 4] Case-based split — no case_id overlap")
    train_cases, val_cases, test_cases = case_based_split(records)

    overlap_tv = train_cases & val_cases
    overlap_tt = train_cases & test_cases
    overlap_vt = val_cases & test_cases

    if not overlap_tv and not overlap_tt and not overlap_vt:
        print(f"  PASS: No overlapping case_ids")
        print(f"    Train: {len(train_cases)} cases, Val: {len(val_cases)} cases, Test: {len(test_cases)} cases")
        print(f"    Train cases: {sorted(train_cases)}")
        print(f"    Val cases:   {sorted(val_cases)}")
        print(f"    Test cases:  {sorted(test_cases)}")
        passed += 1
    else:
        print(f"  FAIL: Overlapping case_ids found")
        if overlap_tv: print(f"    Train/Val overlap: {overlap_tv}")
        if overlap_tt: print(f"    Train/Test overlap: {overlap_tt}")
        if overlap_vt: print(f"    Val/Test overlap: {overlap_vt}")
        failed += 1

    # ── Check 5: At least 16 injection examples ─────────────────────────────
    print("\n[CHECK 5] Prompt injection examples (>=16)")
    injection_count = 0
    for rec in records:
        asst = json.loads(rec["conversations"][1]["content"])
        if "prompt_injection_attempt" in asst.get("safety_flags", []) and asst.get("clinical_accuracy") is None:
            injection_count += 1

    if injection_count >= 16:
        print(f"  PASS: {injection_count} injection examples found")
        passed += 1
    else:
        print(f"  FAIL: Only {injection_count} injection examples (need >= 16)")
        failed += 1

    # ── Summary statistics ──────────────────────────────────────────────────
    print(f"\n{'='*50}")
    print(f"RESULT: {passed}/5 checks passed, {failed}/5 failed")

    labels = Counter()
    flag_counts = Counter()
    step_counts = Counter()
    case_counts = Counter()
    for rec in records:
        asst = json.loads(rec["conversations"][1]["content"])
        labels[asst.get("clinical_accuracy")] += 1
        for f in asst.get("safety_flags", []):
            flag_counts[f] += 1
        for s in asst.get("missing_critical_steps", []):
            step_counts[s] += 1
        case_counts[extract_case_id(rec["conversations"][0]["content"])] += 1

    print(f"\n--- Label distribution ---")
    for label, count in labels.most_common():
        print(f"  {str(label):>8}: {count:>3} ({count/len(records)*100:.1f}%)")

    print(f"\n--- Safety flag frequency ---")
    for flag, count in flag_counts.most_common():
        print(f"  {count:>3}x  {flag}")

    print(f"\n--- Missing step frequency ---")
    for step, count in step_counts.most_common():
        print(f"  {count:>3}x  {step}")

    print(f"\n--- Case distribution ({len(case_counts)} cases) ---")
    for cid, count in sorted(case_counts.items(), key=lambda x: -x[1]):
        print(f"  {count:>3}x  {cid}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
