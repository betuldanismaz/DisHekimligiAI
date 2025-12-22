import os
import json
import logging
import re
from typing import Any, Dict, Optional

# Kütüphane ve modül importları burada kalmalı
try:
    import google.generativeai as genai
except ImportError as e:
    raise ImportError(
        "google-generativeai is not installed. Install with:\n"
        "pip install google-generativeai"
    ) from e

from app.assessment_engine import AssessmentEngine
from app.scenario_manager import ScenarioManager
from app.mock_responses import get_mock_interpretation
from app.services.med_gemma_service import MedGemmaService
from app.services.rule_service import rule_service


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


DENTAL_EDUCATOR_PROMPT = """
You are a dental education assistant helping to interpret student actions within a simulated clinical scenario.
Your job is to:
1) Classify if the input is CHAT (casual conversation) or ACTION (clinical action).
2) Interpret the student's raw action text into a normalized action key that can be scored by a rule engine.
3) Identify the clinical intent category.
4) Flag any safety concerns if present.
5) Provide a short, neutral, and professional explanation for the student (1-3 sentences max).
6) Output STRICT JSON ONLY, without additional commentary or code fences.
7) Respect the language policy: INTERNAL LOGIC (keys) must be in English (e.g., 'check_allergies'), while EXTERNAL RESPONSE (explanatory_feedback) must be in TURKISH.

CRITICAL OUTPUT REQUIREMENTS:
- Respond with ONLY a JSON object. No markdown, no code blocks, no prose.
- The JSON schema must be:
{
  "intent_type": "string: 'CHAT' | 'ACTION'. Use CHAT for greetings/questions, ACTION for clinical steps.",
  "interpreted_action": "string: normalized action key, snake_case (e.g., 'check_allergy_history')",
  "clinical_intent": "string: e.g., 'history_taking' | 'diagnosis_gathering' | 'treatment_planning' | 'patient_education' | 'infection_control' | 'radiography' | 'anesthesia' | 'restorative' | 'periodontics' | 'endodontics' | 'oral_surgery' | 'prosthodontics' | 'orthodontics' | 'follow_up' | 'other'",
  "priority": "string: 'high' | 'medium' | 'low'",
  "safety_concerns": ["array of strings; empty if none"],
  "explanatory_feedback": "string: concise explanation for the learner (<= 3 sentences).",
  "structured_args": { "optional object with any arguments relevant to the action" }
}

Guidance:
- **USE ONLY THE FOLLOWING ACTION KEYS:** ['gather_medical_history', 'gather_personal_info', 'check_allergies_meds', 'order_radiograph', 'diagnose_pulpitis', 'prescribe_antibiotics', 'refer_oral_surgery', 'check_pacemaker', 'check_bleeding_disorder', 'check_diabetes', 'check_oral_hygiene_habits', 'check_vital_signs', 'prescribe_palliative_care', 'ask_systemic_symptoms', 'perform_pathergy_test', 'request_serology_tests', 'perform_oral_exam', 'perform_extraoral_exam', 'perform_nikolsky_test', 'request_dif_biopsy', 'diagnose_herpetic_gingivostomatitis', 'diagnose_behcet_disease', 'diagnose_secondary_syphilis', 'diagnose_mucous_membrane_pemphigoid']. If none fit, use 'unspecified_action'.
- If the student's action is unclear or unsafe, set "priority" accordingly and add a safety note in "safety_concerns".
- Prefer conservative, safety-first interpretations.
- Use the provided scenario state context to disambiguate intent when possible.
"""

# Bu fonksiyon, LLM'in gönderdiği gereksiz metni temizleyerek JSON'a ulaşmaya çalışır.
def _extract_first_json_block(text: str) -> Optional[str]:
    # ... (Buraya daha önce verdiğin _extract_first_json_block fonksiyonunun tamamı gelecek) ...
    # Bu fonksiyon doğru çalıştığı varsayılıyor.
    # ...
    text = text.strip()

    # 1) Try direct parse
    try:
        json.loads(text)
        return text
    except Exception:
        pass

    # 2) Try fenced blocks ```json ... ``` or ``` ... ```
    fence_patterns = [
        r"```json\s*(\{.*?\})\s*```",
        r"```\s*(\{.*?\})\s*```",
    ]
    for pat in fence_patterns:
        m = re.search(pat, text, flags=re.DOTALL)
        if m:
            candidate = m.group(1).strip()
            try:
                json.loads(candidate)
                return candidate
            except Exception:
                continue

    # 3) Fallback: greedy first {...}
    m = re.search(r"(\{.*\})", text, flags=re.DOTALL)
    if m:
        candidate = m.group(1).strip()
        try:
            # En son { veya } karakterine kadar olan kısmı kesebilirsin
            # Bu, basit bir regexp yaklaşımıdır
            return candidate
        except Exception:
            return None

    return None

class DentalEducationAgent:
    """
    Orchestrator agent for the hybrid AI workflow:
    - Uses Gemini to interpret the student's raw text action into structured JSON.
    - Uses AssessmentEngine for objective scoring against rules.
    - Combines interpretation + scoring into final feedback.
    - Updates the scenario state via ScenarioManager.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "models/gemini-2.5-flash-lite",  # Varsayılan: lite model (düşük maliyet)
        temperature: float = 0.2,
        assessment_engine: Optional[AssessmentEngine] = None,
        scenario_manager: Optional[ScenarioManager] = None,
    ) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY not set. Provide api_key param or set environment variable GEMINI_API_KEY."
            )

        genai.configure(api_key=self.api_key)

        self.model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=DENTAL_EDUCATOR_PROMPT,
            generation_config={
                "temperature": temperature,
                "top_p": 0.9,
                "top_k": 40,
                "max_output_tokens": 512,
                # Hint to return JSON. Some SDK versions honor this directly.
                "response_mime_type": "application/json",
            },
        )

        self.assessment_engine = assessment_engine or AssessmentEngine()
        self.scenario_manager = scenario_manager or ScenarioManager()
        
        # MedGemma: Silent Grader (Arka planda çalışır)
        try:
            self.med_gemma = MedGemmaService()
            logger.info("MedGemma servis başarıyla başlatıldı (Silent Evaluator)")
        except Exception as e:
            logger.warning(f"MedGemma başlatılamadı: {e}. Sessiz değerlendirme olmadan devam edilecek.")
            self.med_gemma = None

    def interpret_action(self, action: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use Gemini (Single Call) to convert raw action into structured JSON.
        """
        context_snippet = {
            "case_id": state.get("case_id"),
            "patient_age": state.get("patient", {}).get("age"),
            "chief_complaint": state.get("patient", {}).get("chief_complaint"),
            "revealed_findings": state.get("revealed_findings"),
        }

        user_prompt = (
            "Student action:\n"
            f"{action}\n\n"
            "Scenario state (partial):\n"
            f"{json.dumps(context_snippet, ensure_ascii=False)}\n\n"
            "Return STRICT JSON ONLY following the required schema."
        )

        try:
            response = self.model.generate_content(user_prompt)
            raw_text = getattr(response, "text", "") or ""
            json_str = _extract_first_json_block(raw_text)

            if not json_str:
                # Eğer JSON yoksa, ama metin varsa, bunu CHAT olarak kabul et (Fallback)
                if raw_text and len(raw_text) < 200:
                    return {
                        "intent_type": "CHAT",
                        "interpreted_action": "general_chat",
                        "explanatory_feedback": raw_text.strip(),
                        "clinical_intent": "other",
                        "priority": "low",
                        "safety_concerns": [],
                        "structured_args": {},
                    }
                raise ValueError("Failed to extract JSON from model response.")

            data = json.loads(json_str)

            # Normalize data
            interpreted = {
                "intent_type": data.get("intent_type", "ACTION").strip(),
                "interpreted_action": data.get("interpreted_action", "").strip(),
                "clinical_intent": data.get("clinical_intent", "other").strip() or "other",
                "priority": data.get("priority", "medium").strip() or "medium",
                "safety_concerns": data.get("safety_concerns", []) or [],
                "explanatory_feedback": data.get("explanatory_feedback", "").strip(),
                "structured_args": data.get("structured_args", {}) or {},
            }
            return interpreted

        except Exception as e:
            logger.exception(f"LLM interpretation failed: {e}")
            
            # Kullanıcı dostu hata mesajı ve kota aşımında mock yanıt
            error_msg = str(e)
            if "quota" in error_msg.lower() or "429" in error_msg:
                logger.warning("API quota exceeded. Using mock interpretation fallback.")
                # KOTA AŞIMI: Mock sistem ile devam et
                try:
                    mock_result = get_mock_interpretation(action)
                    mock_result["explanatory_feedback"] = "⚠️ API kotası doldu (Mock sistem aktif). " + mock_result["explanatory_feedback"]
                    return mock_result
                except Exception as mock_err:
                    logger.error(f"Mock interpretation failed: {mock_err}")
                    feedback = "⏳ API günlük kullanım limiti doldu. Lütfen yarın tekrar deneyin."
            else:
                feedback = "Anlaşılamadı (Teknik Hata). Lütfen tekrar dener misiniz?"
            
            # HATA DURUMUNDA 'CHAT' OLARAK DÖN (PUANI GİZLEMEK İÇİN)
            return {
                "intent_type": "CHAT",
                "interpreted_action": "error",
                "explanatory_feedback": feedback,
                "safety_concerns": [],
                "clinical_intent": "other",
                "priority": "low",
                "structured_args": {},
            }

    def _silent_evaluation(
        self, 
        student_input: str, 
        interpreted_action: str, 
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        MedGemma sessizce arka planda değerlendirme yapar.
        Bu fonksiyon konuşma akışını ENGELLEMEZ.
        Değerlendirme başarısız olursa boş dict döner.
        """
        if not self.med_gemma:
            logger.debug("MedGemma mevcut değil, sessiz değerlendirme atlanıyor")
            return {}

        try:
            case_id = state.get("case_id", "default_case")
            category = state.get("category", "GENERAL")
            
            # Kategori için aktif kuralları al
            rules = rule_service.get_active_rules(category)
            
            # Hasta bağlamı özeti oluştur
            patient = state.get("patient", {})
            context_summary = (
                f"Hasta: {patient.get('age', 'Bilinmiyor')} yaşında. "
                f"Şikayet: {patient.get('chief_complaint', 'Belirtilmemiş')}. "
                f"Bulgular: {', '.join(state.get('revealed_findings', []))}"
            )
            
            # MedGemma'yı çağır (sessiz değerlendirme)
            logger.info(f"[Sessiz Değerlendirme] Başlatılıyor: {interpreted_action}")
            evaluation = self.med_gemma.validate_clinical_action(
                student_text=student_input,
                rules=rules,
                context_summary=context_summary
            )
            
            logger.info(f"[Sessiz Değerlendirme] Tamamlandı: {evaluation.get('is_clinically_accurate', 'Bilinmiyor')}")
            return evaluation
            
        except Exception as e:
            logger.warning(f"Sessiz değerlendirme başarısız (kritik değil): {e}")
            return {}

    def _compose_final_feedback(
        self, 
        interpretation: Dict[str, Any], 
        assessment: Dict[str, Any]
    ) -> str:
        """
        Gemini yorumu ve kural motoru puanından final geri bildirim oluşturur.
        Öğrenciye gösterilecek olan metni döner.
        """
        # Gemini'nin açıklayıcı geri bildirimi önceliklidir
        explanatory = interpretation.get("explanatory_feedback", "")
        
        # Eğer CHAT tipindeyse, sadece açıklayıcı geri bildirimi döndür
        if interpretation.get("intent_type") == "CHAT":
            return explanatory
        
        # ACTION tipindeyse, puan bilgisini de ekleyebiliriz (opsiyonel)
        # Ama Silent Evaluator mimarisinde, UI'da puan göstermiyoruz
        # Bu yüzden sadece açıklayıcı metni dönüyoruz
        return explanatory

    def process_student_input(self, student_id: str, raw_action: str, case_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Silent Evaluator Architecture ile Hibrit Pipeline:
        
        1) Gemini: Öğrenci eylemini yorumlar (Eğitim Asistanı rolünde)
        2) AssessmentEngine: Kural bazlı puanlama yapar
        3) MedGemma: ARKA PLANDA sessizce değerlendirir (konuşmayı engellemez)
        4) Final feedback oluşturulur ve tüm sonuçlar döner
        
        Args:
            student_id: Öğrenci kimliği
            raw_action: Öğrencinin ham girişi
            case_id: Aktif vaka kimliği (opsiyonel, state'den alınabilir)
        
        Returns:
        {
          "student_id": str,
          "case_id": str,
          "llm_interpretation": dict (Gemini yorumu - response_text içerir),
          "assessment": dict (Kural motoru puanı),
          "silent_evaluation": dict (MedGemma arka plan değerlendirmesi),
          "final_feedback": str (Öğrenciye gösterilen geri bildirim),
          "updated_state": dict
        }
        """
        # Step 1: Get Context (persistent)
        # If case_id is provided, bind to that session/case so state is stored correctly.
        state = self.scenario_manager.get_state(student_id, case_id=case_id) if case_id else self.scenario_manager.get_state(student_id)
        state = state or {}

        # Use provided case_id or fallback to state
        if not case_id:
            case_id = state.get("case_id", "default_case")
        else:
            state["case_id"] = case_id

        # Step 2: Gemini Interpretation (Eğitim Asistanı)
        interpretation = self.interpret_action(raw_action, state)
        interpreted_action = interpretation.get("interpreted_action", "")

        # Step 3: Objective Scoring (Kural Motoru)
        assessment = self.assessment_engine.evaluate_action(case_id, interpretation) or {}

        # Step 4: Silent Evaluation (MedGemma - Arka Plan)
        # Bu çağrı BAŞARISIZ olsa bile diğer işlemler devam eder
        silent_evaluation = self._silent_evaluation(raw_action, interpreted_action, state)

        # Step 5: Final Feedback (Gemini + Puanlama)
        final_feedback = self._compose_final_feedback(interpretation, assessment)

        # Step 6: Update State
        # Always propagate score_change (even when a rule has no state_updates).
        score_delta = assessment.get("score_change")
        state_updates = (
            assessment.get("state_updates")
            or assessment.get("state_update")
            or assessment.get("new_state_data")
            or {}
        )
        combined_updates: Dict[str, Any] = {}
        if isinstance(score_delta, (int, float)) and score_delta:
            combined_updates["score_change"] = score_delta
        if isinstance(state_updates, dict) and state_updates:
            combined_updates.update(state_updates)

        if combined_updates:
            try:
                self.scenario_manager.update_state(student_id, combined_updates, case_id=case_id)
            except Exception as e:
                logger.exception("Failed to update scenario state: %s", e)

        updated_state = self.scenario_manager.get_state(student_id, case_id=case_id) or state

        return {
            "student_id": student_id,
            "case_id": case_id,
            "llm_interpretation": interpretation,  # içinde 'explanatory_feedback' var (response_text gibi)
            "assessment": assessment,
            "silent_evaluation": silent_evaluation,  # YENI: MedGemma değerlendirmesi
            "final_feedback": final_feedback,
            "updated_state": updated_state,
        }


if __name__ == "__main__":
    """
    Test: Silent Evaluator Architecture
    Gemini = Eğitim Asistanı | MedGemma = Sessiz Değerlendirici
    """
    from dotenv import load_dotenv
    load_dotenv()
    
    try:
        print("=" * 60)
        print("SESSIZ DEĞERLENDİRİCİ MİMARİSİ TEST")
        print("=" * 60)
        
        agent = DentalEducationAgent()
        
        test_student_id = "test_student_001"
        test_action = "Hastanın alerji geçmişini ve kullandığı ilaçları sorguluyorum."
        
        print(f"\n👤 [Öğrenci ID]: {test_student_id}")
        print(f"💬 [Öğrenci Girdisi]: {test_action}")
        print("\n" + "-" * 60)
        
        # Silent Evaluator ile işle (test için olp_001 vakası)
        result = agent.process_student_input(test_student_id, test_action, case_id="olp_001")
        
        print("\n🎓 GEMINI YORUMU (Eğitim Asistanı):")
        print(f"   {result['llm_interpretation'].get('explanatory_feedback', 'Yok')}")
        
        print(f"\n🔍 Yorumlanan Eylem:")
        print(f"   {result['llm_interpretation'].get('interpreted_action', 'Yok')}")
        
        print("\n📊 KURAL MOTORU PUANI:")
        print(f"   Puan: {result['assessment'].get('score', 'N/A')}")
        print(f"   Sonuç: {result['assessment'].get('rule_outcome', 'N/A')}")
        
        print("\n🔬 MEDGEMMA SESSIZ DEĞERLENDİRME (Arka Plan):")
        silent_eval = result.get('silent_evaluation', {})
        if silent_eval:
            print(f"   ✓ Klinik Doğruluk: {silent_eval.get('is_clinically_accurate', 'N/A')}")
            print(f"   ⚠️  Güvenlik İhlali: {silent_eval.get('safety_violation', 'N/A')}")
            print(f"   📝 MedGemma Geri Bildirimi: {silent_eval.get('feedback', 'N/A')}")
            if silent_eval.get('missing_critical_info'):
                print(f"   ⚡ Eksik Bilgi: {silent_eval.get('missing_critical_info')}")
        else:
            print("   (MedGemma değerlendirmesi mevcut değil - servis başlatılamadı)")
        
        print("\n📋 ÖĞRENCİYE GÖSTERILEN FİNAL GERİ BİLDİRİM:")
        print(f"   {result['final_feedback']}")
        
        print("\n" + "=" * 60)
        print("TEST TAMAMLANDI ✓")
        print("=" * 60)
        
    except ValueError as e:
        print(f"\n❌ BAŞLATMA HATASI: {e}")
    except Exception as e:
        logger.exception("Test başarısız")
        print(f"\n❌ ÇALIŞMA ZAMANI HATASI: {e}")