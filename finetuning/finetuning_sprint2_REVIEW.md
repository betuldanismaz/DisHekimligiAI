GİT# Finetuning Sprint 2 — İnceleme ve Düzeltme Listesi

**Hazırlayan:** Emre (review)
**Tarih:** 2026-07-17
**İncelenen dosyalar:**
- `finetuning_sprint2.md`
- `finetune_dataset_v2.jsonl` (337 kayıt, tümü geçerli JSON)
- `gemma2_finetune_v2.ipynb`

**Amaç:** Bu dosya, eğitime başlamadan önce düzeltilmesi gereken maddeleri referans olarak listeler. Her madde; kanıt, etki ve yapılması gereken şeklinde yazılmıştır.

---

## Öncelik özeti

| # | Konu | Öncelik | Eğitimi bloklar mı? |
|---|---|---|---|
| 1 | Train/test veri sızıntısı (split) | Yüksek | Evet |
| 2 | `safety_flags` format tutarsızlığı | Yüksek | Evet |
| 3 | `missing_critical_steps` semantik sapması | Yüksek | Evet |
| 4 | Prompt-injection örnekleri eksik | Yüksek | Kısmen |
| 5 | Klinik `high` etiket çelişkileri | Orta | Hayır |
| 6 | Paket sürümleri / dosya konumu | Orta | Hayır |

> "Bloklar mı?" = Düzeltilmezse ya model yanlış şey öğrenir ya da eval skoru anlamsız olur.

---

## 1. Train/Test veri sızıntısı (BLOKLAYICI)

**Sorun:** Notebook `seed=42` ile **kayıt bazlı** %80/%10/%10 ayırıyor. Dataset yalnızca **18 farklı vaka (case_context)** içeriyor ve her vaka ~10–40 varyanta sahip. Bu yüzden aynı vaka hem eğitimde hem testte kalıyor.

**Kanıt (mevcut seed=42 ile ölçüldü):**
- Test setindeki **33/33** örneğin `case_context`'i eğitim setinde de var.
- Test'teki benzersiz context sayısı: 11 → **11'inin tamamı** eğitimde mevcut.
- Validation için de aynı durum: 16/16 context eğitimde var.

**Etki:** Model vakayı ezberler; eval "genelleme" yerine "ezber" ölçer. Baseline vs fine-tuned karşılaştırması güvenilmez olur.

**Yapılması gereken:**
- Split'i **vaka bazlı (case-based)** yap. Aynı `case_context` / `case_id` yalnızca tek sette olsun.
- Öneri: her kayda açık bir `case_id` alanı ekle, split'i bu alana göre grupla (ör. `sklearn` `GroupShuffleSplit` veya elle vaka listesini train/val/test'e böl).
- 18 vaka için öneri: ~13 vaka train, ~2–3 vaka val, ~2–3 vaka test.

---

## 2. `safety_flags` format tutarsızlığı (BLOKLAYICI)

**Sorun:** 337 kayıtta **33 farklı flag** var; yaklaşık yarısı `snake_case`, yarısı serbest cümle.

**Kanıt:**
- Stil dağılımı: snake_case ~50 kullanım, serbest metin ~53 kullanım.
- snake_case örnekleri: `premature_treatment`, `wrong_medication`, `missed_critical_safety_check`, `wrong_diagnosis`
- serbest metin örnekleri: `Prescribed penicillin without checking allergy`, `Operculectomy during acute infection`, `Prescribing NSAIDs in potential bleeding disorder`

**Aynı kavramın tekrarları (birleştirilmeli):**
- Alerji kontrolü: `Prescribed penicillin without checking allergy` (8), `No allergy check before prescription` (1), `Prescribing medications without allergy check` (1), `Ignoring hepatotoxicity/allergy checks` (2)
- Derin boşluk / Ludwig: `Ignored Ludwig's angina signs` (1), `Ignored Ludwig's angina emergency` (1), `Ignored deep space infection signs` (1), `Discharged patient with deep space infection signs` (1), `Surgical intervention during acute deep space infection` (2)
- Antikoagülan: `Unilateral cessation of anticoagulant` (3), `Unilateral dose adjustment of anticoagulant` (1), `Prescribing NSAID with Warfarin` (2), `Extraction with INR > 3.5` (1)

**Etki:** Model iki farklı format öğrenir; backend (`app/services/med_gemma_service.py`) flag'leri string listesi olarak işler, serbest metinler analytics/dashboard'da gruplanamaz. `safety_flag_precision` metriği yapay olarak düşer.

**Yapılması gereken:**
- Kapalı bir **flag sözlüğü** tanımla, tüm flag'leri `snake_case`'e çevir.
- Önerilen başlangıç sözlüğü:
  - `premature_treatment`
  - `wrong_medication`
  - `wrong_diagnosis`
  - `missed_critical_safety_check`
  - `allergy_not_checked`
  - `contraindicated_procedure`
  - `surgery_during_acute_infection`
  - `deep_space_infection_missed`
  - `anticoagulant_mismanaged`
  - `nsaid_in_bleeding_risk`
  - `antifungal_without_diagnosis`
  - `immunosuppressant_without_workup`
  - `bisphosphonate_history_missed`
  - `prompt_injection_attempt` (bkz. madde 4)
- Sözlük dışı flag kalmadığını bir doğrulama scriptiyle kontrol et.

---

## 3. `missing_critical_steps` semantik sapması (BLOKLAYICI)

**Sorun:** Bu alan "eksik kalan adımın kimliği" olmalı; ama çoğunlukla **yapılacak tedavi talimatı** veya doğrudan **kural metninin kopyası** olmuş.

**Kanıt:**
- snake_case ID: **25** kullanım
- serbest metin: **385** kullanım
- Bunların **171'i** `clinical_rules` içindeki bir maddenin **birebir kopyası**
- 89 benzersiz farklı değer var (çoğu aynı kavramın varyasyonu)

**Örnek sapmalar:**
- `Check drug allergies` (38 kez) — talimat, kimlik değil
- `Prescribe IV antibiotics` (17) — tedavi talimatı
- `Verify INR <3.5 before any invasive dental procedure...` — kural metni kopyası
- `Consult hematology before any invasive dental procedure...` (27) — kural metni kopyası

**Etki:** Model "eksik adım" yerine "kural tekrarı / tedavi reçetesi" üretmeyi öğrenir. `accuracy_match_rate` ve tutarlılık düşer.

**Yapılması gereken:**
- Kapalı bir **missing-step sözlüğü** tanımla, hepsini `snake_case` ID'ye çevir.
- Önerilen başlangıç sözlüğü:
  - `allergy_verification_missing`
  - `diagnosis_before_treatment_missing`
  - `biopsy_missing`
  - `urgent_referral_missing`
  - `inr_verification_missing`
  - `hematology_consult_missing`
  - `immunosuppression_workup_missing`
  - `dehydration_assessment_missing`
  - `anamnesis_incomplete`
  - `mucosal_examination_missing`
- `clinical_rules` metnini bu alana kopyalamayı bırak.

---

## 4. Prompt-injection örnekleri eksik (YÜKSEK)

**Sorun:** `finetuning_sprint2.md` 16 adversarial örnek planlıyor; dataset'te **0** tane var. Notebook (Cell 12) yine de injection sanity check yapıyor.

**Kanıt:**
- `student_action_untrusted` alanında gerçek injection kalıbı (ör. "ignore previous instructions", "you are now", "system prompt") arandı: **0 eşleşme**.
- Dokümandaki checklist maddesi: `[ ] Generate adversarial/injection examples (16 planned, 0 done)`

**Etki:** Model injection'a karşı eğitilmemiş olur; güvenlik testinde büyük olasılıkla başarısız olur.

**Yapılması gereken:**
- Planlanan 16 örneği üret. Her biri:
  - `student_action_untrusted` içinde injection denemesi barındırsın (rol değiştirme, sistem prompt çıkarma, gömülü JSON override, admin iddiası, jailbreak, dil değiştirme, vb.)
  - Doğru cevapta `safety_flags` içine `prompt_injection_attempt` eklensin
  - `clinical_accuracy: null` olsun
- Not: Bu madde v3'e ertelenebilir; ama ertelenirse notebook'un injection testi "bilinen başarısız" olarak işaretlenmeli.

---

## 5. Klinik `high` etiket çelişkileri (ORTA)

**Sorun:** Bazı `high` etiketli örnekler, aynı kayıttaki `clinical_rules` ile çelişiyor.

**Kanıt — kayıt #3:**
- Kural: `Rule out pemphigus/pemphigoid before corticosteroids.`
- Öğrenci aksiyonu: "Tanıyı kesinleştirmek için topikal kortikosteroid tedavisine başlıyorum..." (tanı öncesi steroid)
- Etiket: `clinical_accuracy: high`, `safety_flags: []`

**Etki:** Model "tanı öncesi steroid = iyi" gibi güvenli olmayan bir davranışı öğrenebilir.

**Yapılması gereken:**
- Özellikle erken tedavi (`kortikosteroid`, `sistemik`, `çekim`, `reçete`) içeren `high` etiketli örnekleri klinik gözle gözden geçir.
- Kuralla çelişenleri `medium`/`low` + uygun flag ile düzelt.

---

## 6. Paket sürümleri ve dosya konumu (ORTA)

**Sorun A — pinsiz bağımlılıklar:** Notebook `!pip install unsloth` ve `!pip install --upgrade trl peft accelerate bitsandbytes datasets` kullanıyor. Sürümler sabit değil; Colab'da API kırılması riski var.

**Yapılması gereken:** Kritik paketleri sabitle (ör. `unsloth==...`, `trl==...`, `peft==...`). Çalışan sürümleri not düş.

**Sorun B — dosya konumu:** Üç dosya şu an repo kökü (`Dentistry_Project`) dışında, üst klasörde. Versiyon kontrolüne girmiyorlar.

**Yapılması gereken:** Dataset + notebook + plan dosyalarını `Dentistry_Project/finetuning/` altına taşı ve commit et.

---

## Eğitim öncesi checklist (önerilen sıra)

- [x] 1. Case-based split'e geç (aynı vaka tek sette) — `normalize_dataset.py` + notebook güncellendi
- [x] 2. `safety_flags` → kapalı snake_case sözlük + normalize — 14 flag, 33 mapping
- [x] 3. `missing_critical_steps` → kapalı snake_case sözlük + kural kopyalarını temizle — 16 step, 80+ mapping
- [x] 4. 16 adversarial/injection örneği ekle — `generate_adversarial.py`
- [x] 5. `high` etiketli erken tedavi örneklerini klinik audit — record #3 düzeltildi (high → low)
- [x] 6. Paketleri pinle + dosyaları `finetuning/` altına taşı — notebook'ta pinlendi
- [x] 7. Doğrulama scripti: `validate_dataset.py` — 5/5 check geçti
- [ ] 8. Colab: baseline → train → eval → HF push

## Doğrulama önerisi

Düzeltmeden sonra hızlı bir kontrol scripti şunları teyit etmeli:
1. Her `safety_flags` ve `missing_critical_steps` değeri onaylı sözlükte mi?
2. Train/val/test setleri arasında ortak `case_id` var mı? (olmamalı)
3. En az 16 kayıtta `prompt_injection_attempt` + `clinical_accuracy: null` var mı?
4. Tüm satırlar geçerli JSON ve Schema A mı? (şu an: 337/337 geçerli — korunmalı)
