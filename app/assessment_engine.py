from __future__ import annotations

import json
import os
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AssessmentEngine:
    """
    Loads scoring rules and evaluates interpreted actions against case-specific rules.
    Rules file: ../data/scoring_rules.json (relative to this file).
    """

    def __init__(self, rules_path: Optional[str] = None) -> None:
        self._rules_path = rules_path or os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "data", "scoring_rules.json")
        )
        self._rules: List[Dict[str, Any]] = []
        self._load_rules()

    def _load_rules(self) -> None:
        """
        Load rules from JSON.
        On error (file not found or JSON error), log and keep an empty rules list.
        Expected top-level structure: List[case_rule_object].
        """
        try:
            with open(self._rules_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, list):
                self._rules = data
            else:
                logger.error("Invalid rules format (expected list): %s", type(data).__name__)
                self._rules = []
        except FileNotFoundError:
            logger.error("Scoring rules file not found: %s", self._rules_path)
            self._rules = []
        except json.JSONDecodeError as e:
            logger.error("Failed to parse scoring rules JSON: %s", e)
            self._rules = []

    def _find_rule(self, case_id: str, interpreted_action: str) -> Optional[Dict[str, Any]]:
        """
        Find a rule matching the given case_id and interpreted_action.
        Looks inside 'rules' (preferred) or 'actions' (fallback) for entries where
        rule['target_action'] == interpreted_action.
        """
        if not case_id or not interpreted_action:
            return None

        for entry in self._rules:
            if not isinstance(entry, dict):
                continue
            if entry.get("case_id") != case_id:
                continue

            rules_list = entry.get("rules")
            if rules_list is None:
                rules_list = entry.get("actions", [])
            if not isinstance(rules_list, list):
                logger.warning("Rules list for case_id '%s' is not a list.", case_id)
                return None

            for rule in rules_list:
                if isinstance(rule, dict) and rule.get("target_action") == interpreted_action:
                    return rule
            # If case_id matched but no rule matched, stop searching further case entries
            return None

        return None

    def evaluate_action(self, case_id: str, interpretation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate an interpreted action for a specific case.

        Returns:
        - If matched:
            {
              "score": int|float,
              "score_change": int|float,
              "rule_outcome": str,
              "action_effect": Any
            }
        - If not matched:
            {
              "score": 0,
              "score_change": 0,
              "rule_outcome": "Unscored",
              "action_effect": None
            }
        """
        default_result: Dict[str, Any] = {
            "score": 0,
            "score_change": 0,
            "rule_outcome": "Unscored",
            "action_effect": None,
        }

        if not isinstance(interpretation, dict):
            return default_result

        interpreted_action = interpretation.get("interpreted_action")
        if not isinstance(interpreted_action, str) or not interpreted_action.strip():
            return default_result

        rule = self._find_rule(case_id, interpreted_action.strip())
        if not rule:
            return default_result

        score = rule.get("score", 0)
        outcome = rule.get("rule_outcome", "Unscored")
        effect = rule.get("action_effect")

        return {
            "score": score,
            "score_change": score,
            "rule_outcome": outcome,
            "action_effect": effect,
        }