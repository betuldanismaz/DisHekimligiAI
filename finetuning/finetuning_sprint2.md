# Finetuning Sprint 2 — Dataset Expansion + Evaluation Harness

**Status:** Planned  
**Notebook:** `finetuning_sprint2_dataset_eval.ipynb`  
**Depends on:** Sprint 1 (`gemma2_finetune.ipynb`) completed

---

## What Sprint 1 Produced

- Model: `google/gemma-2-9b-it` fine-tuned with QLoRA (r=16, 3 epochs)
- Dataset: 50 examples across 4 clinical cases
- Role: Senior Oral Pathology Examiner — evaluates student actions, returns structured JSON
- Output schema: `safety_flags`, `missing_critical_steps`, `clinical_accuracy`, `faculty_notes`

---

## Problems Found in Sprint 1

| # | Problem | Impact |
|---|---|---|
| 1 | **Schema inconsistency** — examples 1–30 use `student_action_untrusted` + full response keys; examples 31–50 use `student_action` + compact `accuracy`/`flags`/`feedback` | Model learns two conflicting output formats |
| 2 | **Dataset too small** — 50 examples (notebook header incorrectly claimed 137) | Underfitting, poor generalization |
| 3 | **No evaluation harness** — no way to measure if the model improved vs base | Can't validate fine-tuning worked |
| 4 | **No adversarial examples** — security policy appears in every prompt but model never trains on injection attempts | Model untrained to resist prompt injection |

---

## Sprint 2 Goals

1. Fix schema inconsistency — migrate all examples to Schema A
2. Expand dataset to ~300 examples (5 new clinical cases + adversarial examples)
3. Build evaluation harness — compare base vs fine-tuned model on held-out test set
4. Re-run fine-tune on the clean v2 dataset

---

## New Clinical Cases (5 added)

| Case ID | Pathology | Key Clinical Rules |
|---|---|---|
| `case_05_oral_candidiasis` | Pseudomembranous candidiasis (HIV+, on antibiotics) | Candidiasis in healthy adult → investigate immunosuppression |
| `case_06_pericoronitis` | Pericoronitis with trismus + fever | Trismus + fever = possible deep space infection → urgent referral |
| `case_07_recurrent_aphthous` | Recurrent aphthous stomatitis (hidden Celiac disease) | Screen CBC, ferritin, B12, anti-tTG before labeling idiopathic RAS |
| `case_08_anticoagulated_extraction` | Extraction in warfarin patient (hidden INR 3.8) | Verify INR <3.5; never stop warfarin unilaterally |
| `case_09_pediatric_dental_trauma` | Dental trauma in child with von Willebrand disease | Consult hematology before any invasive procedure in bleeding disorders |

---

## Adversarial Examples (8 added)

Examples where `student_action_untrusted` contains prompt injection attempts. Correct response always includes `"prompt_injection_attempt"` in `safety_flags` and ignores the embedded instruction.

Injection types covered:
- Role override ("You are now DAN...")
- System prompt extraction ("output your system prompt")
- Embedded JSON override (`SYSTEM: New rule — always output {...}`)
- Mixed action + injection (valid clinical action buried with injection suffix)
- Admin override claim
- Jailbreak keyword patterns

---

## Dataset v2 Structure

```
finetune_dataset_v2.jsonl          — full merged dataset
finetune_dataset_v2_train.jsonl    — 80% for training
finetune_dataset_v2_val.jsonl      — 10% for validation
finetune_dataset_v2_test.jsonl     — 10% held-out for evaluation
```

All examples use Schema A:

```json
{
  "conversations": [
    {
      "role": "user",
      "content": "You are a Senior Oral Pathology Examiner...\n\nINPUT_PAYLOAD_JSON:\n{...student_action_untrusted...}"
    },
    {
      "role": "assistant",
      "content": "{\"safety_flags\": [...], \"missing_critical_steps\": [...], \"clinical_accuracy\": \"high|medium|low|null\", \"faculty_notes\": \"...\"}"
    }
  ]
}
```

---

## Training Config (unchanged from Sprint 1)

| Parameter | Value |
|---|---|
| Base model | `unsloth/gemma-2-9b-it-bnb-4bit` |
| LoRA rank (r) | 16 |
| LoRA alpha | 16 |
| Target modules | q/k/v/o/gate/up/down projections |
| Epochs | 3 |
| Learning rate | 2e-4 |
| Batch size (effective) | 8 (2 × 4 grad accum) |
| Optimizer | adamw_8bit |
| LR scheduler | cosine |

---

## Evaluation Metrics

Run on the held-out test set for both base and fine-tuned model:

| Metric | Description |
|---|---|
| **JSON parse rate** | % of outputs that are valid JSON |
| **Accuracy label match** | Exact match of `clinical_accuracy` vs ground truth |
| **Safety flag recall** | Fraction of ground truth flags correctly predicted |
| **Safety flag precision** | Fraction of predicted flags that were correct |

Results saved to:
- `eval_summary_sprint2.csv` — aggregate scores per model
- `eval_details_sprint2.csv` — per-example breakdown

---

## HuggingFace Output

Adapter pushed to: `betuldanismaz/dentai-gemma2-9b-oral-pathology-v2`

To use in `med_gemma_service.py`:
```python
self.model_id = "betuldanismaz/dentai-gemma2-9b-oral-pathology-v2"
```

---

## Sprint 3 Ideas

| Idea | What it solves |
|---|---|
| **DPO / preference optimization** | Use eval results to build chosen/rejected pairs; improve safety flag precision without more labeled data |
| **Multi-turn conversations** | Current dataset is single-turn; extend to 3-turn dialogues simulating a real clinical encounter |
| **GGUF export** | Convert adapter to GGUF for on-device inference in the DentAI backend — no GPU needed in production |
