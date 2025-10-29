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


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


DENTAL_EDUCATOR_PROMPT = """
You are a dental education assistant helping to interpret student actions within a simulated clinical scenario.
Your job is to:
1) Interpret the student's raw action text into a normalized action key that can be scored by a rule engine.
2) Identify the clinical intent category.
3) Flag any safety concerns if present.
4) Provide a short, neutral, and professional explanation for the student (1-3 sentences max).
5) Output STRICT JSON ONLY, without additional commentary or code fences.

CRITICAL OUTPUT REQUIREMENTS:
- Respond with ONLY a JSON object. No markdown, no code blocks, no prose.
- The JSON schema must be:
{
  "interpreted_action": "string: normalized action key, snake_case (e.g., 'check_allergy_history')",
  "clinical_intent": "string: e.g., 'history_taking' | 'diagnosis_gathering' | 'treatment_planning' | 'patient_education' | 'infection_control' | 'radiography' | 'anesthesia' | 'restorative' | 'periodontics' | 'endodontics' | 'oral_surgery' | 'prosthodontics' | 'orthodontics' | 'follow_up' | 'other'",
  "priority": "string: 'high' | 'medium' | 'low'",
  "safety_concerns": ["array of strings; empty if none"],
  "explanatory_feedback": "string: concise explanation for the learner (<= 3 sentences).",
  "structured_args": { "optional object with any arguments relevant to the action" }
}

Guidance:
- **USE ONLY THE FOLLOWING ACTION KEYS:** ['gather_medical_history', 'check_allergies_meds', 'order_radiograph', 'diagnose_pulpitis', 'prescribe_antibiotics', 'refer_oral_surgery']. If none fit, use 'unspecified_action'.
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
        model_name: str = "gemini-2.5-flash",
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

    def interpret_action(self, action: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use Gemini to convert a student's raw action into a strict JSON interpretation.

        Returns a dict with keys:
          - interpreted_action (str)
          - clinical_intent (str)
          - priority (str)
          - safety_concerns (list[str])
          - explanatory_feedback (str)
          - structured_args (dict)
        """
        # Provide minimal, relevant state to the prompt to reduce token usage
        context_snippet = {
            "case_id": state.get("case_id"),
            "patient_age": state.get("patient", {}).get("age"),
            "patient_gender": state.get("patient", {}).get("gender"),
            "chief_complaint": state.get("patient", {}).get("chief_complaint"),
            "known_allergies": state.get("patient", {}).get("allergies"),
            "known_conditions": state.get("patient", {}).get("medical_history"),
            "revealed_findings": state.get("revealed_findings"),
            "progress": state.get("progress"),
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
                raise ValueError("Failed to extract JSON from model response.")

            data = json.loads(json_str)

            # Minimal schema normalization and defaults
            interpreted = {
                "interpreted_action": data.get("interpreted_action", "").strip(),
                "clinical_intent": data.get("clinical_intent", "other").strip() or "other",
                "priority": data.get("priority", "medium").strip() or "medium",
                "safety_concerns": data.get("safety_concerns", []) or [],
                "explanatory_feedback": data.get("explanatory_feedback", "").strip(),
                "structured_args": data.get("structured_args", {}) or {},
            }

            # Guardrails
            if not interpreted["interpreted_action"]:
                # Conservative fallback if the model omitted the key
                interpreted["interpreted_action"] = "unspecified_action"

            if not isinstance(interpreted["safety_concerns"], list):
                interpreted["safety_concerns"] = [str(interpreted["safety_concerns"])]

            if not isinstance(interpreted["structured_args"], dict):
                interpreted["structured_args"] = {}

            return interpreted

        except Exception as e:
            logger.exception("LLM interpretation failed: %s", e)
            # Safe fallback to keep pipeline running
            return {
                "interpreted_action": "unspecified_action",
                "clinical_intent": "other",
                "priority": "medium",
                "safety_concerns": ["LLM_interpretation_failed"],
                "explanatory_feedback": "Your action could not be fully interpreted. Please clarify or try a more specific step.",
                "structured_args": {},
            }

    def _compose_final_feedback(
        self,
        interpretation: Dict[str, Any],
        assessment: Dict[str, Any],
    ) -> str:
        """
        Combine LLM interpretation (tone/explanation) with objective scoring (accuracy).
        """
        explanation = interpretation.get("explanatory_feedback", "").strip()
        interpreted_action = interpretation.get("interpreted_action", "unspecified_action")
        score = assessment.get("score")
        outcome = assessment.get("outcome") or assessment.get("rule_outcome")
        hints = assessment.get("hints") or assessment.get("rationale")
        safety_notes = interpretation.get("safety_concerns") or []

        parts = []
        if explanation:
            parts.append(explanation)
        else:
            parts.append(f"Interpreted your action as: {interpreted_action}.")

        if score is not None:
            parts.append(f"Objective score: {score}.")
        if outcome:
            parts.append(f"Outcome: {outcome}.")

        if safety_notes:
            parts.append("Safety considerations: " + "; ".join(map(str, safety_notes)) + ".")

        if hints:
            if isinstance(hints, list):
                hint_text = "; ".join(map(str, hints))
            else:
                hint_text = str(hints)
            parts.append(f"Tip: {hint_text}")

        return " ".join(p.strip() for p in parts if p and str(p).strip())

    def process_student_action(self, student_id: str, raw_action: str) -> Dict[str, Any]:
        """
        Orchestrates the hybrid pipeline:
        1) Retrieve scenario state.
        2) LLM interpretation to strict JSON.
        3) Objective scoring via AssessmentEngine.
        4) Generate final feedback.
        5) Update scenario state using assessment outcomes.

        Returns a dict:
        {
          "student_id": str,
          "case_id": str,
          "llm_interpretation": dict,
          "assessment": dict,
          "final_feedback": str,
          "updated_state": dict
        }
        """
        # Step 1: Get Context
        state = self.scenario_manager.get_state(student_id) or {}
        case_id = state.get("case_id") or "default_case"

        # Step 2: LLM Interpretation
        interpretation = self.interpret_action(raw_action, state)

        # Step 3: Objective Scoring
        assessment = self.assessment_engine.evaluate_action(case_id, interpretation) or {}

        # Step 4: Final Feedback
        final_feedback = self._compose_final_feedback(interpretation, assessment)

        # Step 5: Update State
        # Expecting the assessment engine to optionally return state updates.
        # Gracefully handle different possible keys: 'state_updates', 'state_update', 'new_state_data'
        state_updates = (
            assessment.get("state_updates")
            or assessment.get("state_update")
            or assessment.get("new_state_data")
            or {}
        )
        if isinstance(state_updates, dict) and state_updates:
            try:
                self.scenario_manager.update_state(student_id, state_updates)
            except Exception as e:
                logger.exception("Failed to update scenario state: %s", e)

        updated_state = self.scenario_manager.get_state(student_id) or state

        return {
            "student_id": student_id,
            "case_id": case_id,
            "llm_interpretation": interpretation,
            "assessment": assessment,
            "final_feedback": final_feedback,
            "updated_state": updated_state,
        }
# ...existing code...

# app/agent.py dosyasının en altı

# app/agent.py dosyasının en altındaki blok

if __name__ == "__main__":
    # Gerekli importları burada yapıyoruz
    from dotenv import load_dotenv
    load_dotenv()
    
    try:
        agent = DentalEducationAgent()
        
        # 2. Test İçin Öğrenci Aksiyonu ve ID tanımla
        test_student_id = "test_user_003"  # <-- TANIMLANAN DEĞİŞKEN ADI BU!
        test_action = "Hastanın alerji geçmişini ve kullandığı ilaçları sorguluyorum."
        
        print("-" * 50)
        # BURADA DÜZELTİLDİ: 'test_user_id' yerine 'test_student_id' kullanıldı.
        print(f"[{test_student_id}] İçin Eylem İşleniyor: {test_action}")
        
        # 3. Ajanın ana metodunu çağır
        result = agent.process_student_action(test_student_id, test_action)
        
        # 4. Sonuçları yazdır
        print("-" * 50)
        print("Final Geri Bildirim:", result['final_feedback'])
        print("\nObjektif Puan:", result['assessment']['score'])
        print("LLM Yorumu:", result['llm_interpretation']['interpreted_action'])
        print("-" * 50)
        
    except ValueError as e:
        print(f"HATA: Ajan başlatılamadı. {e}")
    except Exception as e:
        print(f"HATA: İşlem sırasında beklenmedik hata oluştu. {e}")