from __future__ import annotations

import json
import os
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from db.database import SessionLocal, StudentSession


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

    def _find_case(self, case_id: str) -> Dict[str, Any]:
        if not case_id:
            return {}
        for c in self.case_data:
            if isinstance(c, dict) and c.get("case_id") == case_id:
                return c
        return {}

    def _build_initial_state(self, case_id: str) -> Dict[str, Any]:
        case = self._find_case(case_id) or {}

        state: Dict[str, Any] = {
            "case_id": case_id,
            "revealed_findings": [],
            "history": [],
        }

        # Normalize patient fields (case_scenarios.json is primarily Turkish-keyed today)
        patient: Dict[str, Any] = {}
        hp = case.get("hasta_profili")
        if isinstance(hp, dict):
            if "yas" in hp:
                patient["age"] = hp.get("yas")
            if "sikayet" in hp:
                patient["chief_complaint"] = hp.get("sikayet")
            if "tibbi_gecmis" in hp:
                patient["medical_history"] = hp.get("tibbi_gecmis")
            if "sosyal_gecmis" in hp:
                patient["social_history"] = hp.get("sosyal_gecmis")

        # Back-compat: if the case uses the older English schema
        if not patient and isinstance(case.get("patient"), dict):
            patient = case.get("patient", {})

        if patient:
            state["patient"] = patient

        if isinstance(case.get("name"), str):
            state["case_name"] = case.get("name")
        elif isinstance(case.get("dogru_tani"), str):
            # Not a perfect name, but helps with context
            state["case_name"] = case.get("dogru_tani")

        if isinstance(case.get("zorluk_seviyesi"), str):
            state["case_difficulty"] = case.get("zorluk_seviyesi")

        return state

    def get_state(self, student_id: str, case_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieve (or initialize) the persistent state for a student.

        Selection rule:
        - If case_id is provided, use the most recent StudentSession for (student_id, case_id).
        - Else, use the most recent StudentSession for the student.

        If no session exists, create one for the default case.
        """
        if not student_id:
            return {}

        db = SessionLocal()
        try:
            query = db.query(StudentSession).filter(StudentSession.student_id == student_id)
            if case_id:
                query = query.filter(StudentSession.case_id == case_id)

            session = query.order_by(StudentSession.start_time.desc()).first()

            if not session:
                # Create a new persistent session for the default case
                chosen_case_id = case_id or self._default_case_id
                initial_state = self._build_initial_state(chosen_case_id)
                session = StudentSession(
                    student_id=student_id,
                    case_id=chosen_case_id,
                    current_score=0.0,
                    state_json=json.dumps(initial_state, ensure_ascii=False),
                )
                db.add(session)
                db.commit()
                db.refresh(session)
                return initial_state

            # Load and validate state_json
            raw = session.state_json or "{}"
            try:
                state = json.loads(raw) if isinstance(raw, str) else {}
            except Exception:
                logger.warning("Invalid state_json for student_id=%s session_id=%s; resetting.", student_id, session.id)
                state = {}

            if not isinstance(state, dict) or not state:
                state = self._build_initial_state(session.case_id or (case_id or self._default_case_id))

            # Ensure case_id is present and consistent
            effective_case_id = case_id or session.case_id or state.get("case_id") or self._default_case_id
            state["case_id"] = effective_case_id

            # Keep DB score as the source of truth for score
            state["current_score"] = session.current_score or 0.0

            # Persist repaired/initialized state back if needed
            if (session.state_json or "").strip() == "" or raw == "{}" or state.get("case_id") != session.case_id:
                session.case_id = effective_case_id
                session.state_json = json.dumps(state, ensure_ascii=False)
                db.commit()

            return state
        finally:
            db.close()

    def update_state(self, student_id: str, updates: Dict[str, Any], case_id: Optional[str] = None) -> None:
        """
        Apply updates from the assessment engine to the student's persistent state.

        Behavior:
        - Updates StudentSession.current_score additively when 'score_change' is numeric.
        - Merges remaining keys into the state_json dict (shallow merge; list extends).
        - Persists back to StudentSession.state_json.
        """
        if not isinstance(updates, dict):
            return

        if not student_id:
            return

        db = SessionLocal()
        try:
            query = db.query(StudentSession).filter(StudentSession.student_id == student_id)
            if case_id:
                query = query.filter(StudentSession.case_id == case_id)
            session = query.order_by(StudentSession.start_time.desc()).first()

            if not session:
                # Ensure a session exists so we have a place to store state
                _ = self.get_state(student_id, case_id=case_id)
                session = db.query(StudentSession).filter(StudentSession.student_id == student_id)
                if case_id:
                    session = session.filter(StudentSession.case_id == case_id)
                session = session.order_by(StudentSession.start_time.desc()).first()
                if not session:
                    return

            # Load current state
            raw = session.state_json or "{}"
            try:
                state = json.loads(raw) if isinstance(raw, str) else {}
            except Exception:
                state = {}

            if not isinstance(state, dict) or not state:
                state = self._build_initial_state(session.case_id or (case_id or self._default_case_id))

            # Apply score change to DB score (source of truth)
            score_delta = updates.get("score_change")
            if isinstance(score_delta, (int, float)):
                session.current_score = (session.current_score or 0.0) + float(score_delta)
                state["current_score"] = session.current_score

            # Merge other fields into state_json
            for k, v in updates.items():
                if k in ("score_change",):
                    continue

                if k not in state:
                    state[k] = v
                else:
                    if isinstance(state[k], dict) and isinstance(v, dict):
                        state[k].update(v)
                    elif isinstance(state[k], list) and isinstance(v, list):
                        state[k].extend(v)
                    else:
                        state[k] = v

            # Ensure case_id
            effective_case_id = case_id or session.case_id or state.get("case_id") or self._default_case_id
            session.case_id = effective_case_id
            state["case_id"] = effective_case_id

            session.state_json = json.dumps(state, ensure_ascii=False)
            db.commit()
        finally:
            db.close()