from __future__ import annotations

import json
import os
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Global in-memory store simulating a database
_STUDENT_STATES: Dict[str, Dict[str, Any]] = {}


class ScenarioManager:
    """
    Loads case scenarios and manages per-student scenario state.
    """

    def __init__(self, cases_path: Optional[str] = None) -> None:
        self._cases_path = cases_path or os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "data", "case_scenarios.json")
        )
        self.case_data: List[Dict[str, Any]] = []
        self._default_case_id: str = "olp_001"
        self._load_cases()

    def _load_cases(self) -> None:
        """
        Load all cases from JSON.
        - On error, log and keep an empty list.
        - Accepts top-level list, or dict with "cases" list.
        """
        try:
            with open(self._cases_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, list):
                self.case_data = data
            elif isinstance(data, dict) and isinstance(data.get("cases"), list):
                self.case_data = data.get("cases", [])
            else:
                logger.error("Unexpected structure in case_scenarios.json; expected a list or a dict with 'cases'.")
                self.case_data = []

            # Determine default case_id from the first case, if available
            if self.case_data:
                first_case = self.case_data[0]
                cid = first_case.get("case_id")
                if isinstance(cid, str) and cid:
                    self._default_case_id = cid

        except FileNotFoundError:
            logger.error("Case scenarios file not found: %s", self._cases_path)
            self.case_data = []
        except json.JSONDecodeError as e:
            logger.error("Failed to parse case scenarios JSON: %s", e)
            self.case_data = []

    def get_state(self, student_id: str) -> Dict[str, Any]:
        """
        Retrieve (or initialize) the state for a student.
        - If new, initialize with the first case's case_id (or default) and current_score=0.
        """
        if student_id not in _STUDENT_STATES:
            # Determine initial case and optional patient info
            first_case = self.case_data[0] if self.case_data else {}
            case_id = first_case.get("case_id") or self._default_case_id

            initial_state: Dict[str, Any] = {
                "case_id": case_id,
                "current_score": 0,
            }
            # Optionally include common fields if available
            if "patient" in first_case and isinstance(first_case["patient"], dict):
                initial_state["patient"] = first_case["patient"]
            if "name" in first_case and isinstance(first_case["name"], str):
                initial_state["case_name"] = first_case["name"]

            _STUDENT_STATES[student_id] = initial_state

        return _STUDENT_STATES[student_id]

    def update_state(self, student_id: str, updates: Dict[str, Any]) -> None:
        """
        Apply updates from the assessment engine to the student's state.
        - If 'score_change' is present and numeric, add it to 'current_score' (do not replace).
        - Merge remaining keys into the student's state.
        """
        if not isinstance(updates, dict):
            return

        state = self.get_state(student_id)  # ensure initialized

        # Handle score change additively
        score_delta = updates.get("score_change")
        if isinstance(score_delta, (int, float)):
            state["current_score"] = state.get("current_score", 0) + score_delta

        # Merge other fields (avoid replacing current_score directly)
        for k, v in updates.items():
            if k in ("score_change", "current_score"):
                continue

            if k not in state:
                state[k] = v
            else:
                # Shallow merge for dicts; extend for lists; replace otherwise
                if isinstance(state[k], dict) and isinstance(v, dict):
                    state[k].update(v)
                elif isinstance(state[k], list) and isinstance(v, list):
                    state[k].extend(v)
                else:
                    state[k] = v


def load_scenarios_flex(path: str) -> List[Dict[str, Any]]:
    """
    Esnek senaryo yükleyici:
    - Eğer dosya bir liste ise listeyi döndürür.
    - Eğer dosya {'cases': [...]} ise 'cases' listesini döndürür.
    - Eğer dosya tek bir vaka objesi ise [obj] olarak döndürür.
    - Aksi halde boş liste döndürür ve bir uyarı loglar.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception as e:
        LOGGER.exception("Senaryo dosyası açılamadı: %s", e)
        return []

    # Listeyse direkt döndür
    if isinstance(raw, list):
        return raw

    # Sözlükse farklı anahtarları kontrol et
    if isinstance(raw, dict):
        # yaygın anahtar 'cases'
        if "cases" in raw and isinstance(raw["cases"], list):
            return raw["cases"]
        # bazen 'data' veya 'scenarios' olabilir
        for key in ("data", "scenarios", "items"):
            if key in raw and isinstance(raw[key], list):
                return raw[key]
        # eğer dict tek vaka objesi ise onu listeye sar
        # (ör: {"case_id": "...", ...})
        # basit kontrol: varsa 'case_id' anahtarı tek vaka varsay
        if "case_id" in raw or "id" in raw:
            return [raw]

    LOGGER.warning("Unexpected structure in %s; expected a list or a dict with 'cases' (found %s).", path, type(raw).__name__)
    return []