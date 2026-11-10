import json
import re
from pathlib import Path


def normalize(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return " ".join(text.split())


def _has_phrase(text, phrase):
    return f" {normalize(phrase)} " in f" {text} "


class ChatbotEngine:
    def __init__(self, knowledge):
        self.knowledge = knowledge
        self.questions = {
            item["QA ID"]: item for item in knowledge["questions"]
        }
        self.rules = sorted(
            (rule for rule in knowledge["rules"] if not rule["condition"].get("fallback")),
            key=lambda rule: rule["priority"],
        )

    @classmethod
    def from_file(cls, path):
        with Path(path).open(encoding="utf-8") as knowledge_file:
            return cls(json.load(knowledge_file))

    @staticmethod
    def _matches_simple(text, phrases):
        return any(_has_phrase(text, phrase) for phrase in phrases)

    def _matches_condition(self, text, condition):
        if "alternatives" in condition:
            return any(
                self._matches_condition(text, alternative)
                for alternative in condition["alternatives"]
            )

        if self._matches_simple(text, condition.get("exclude_any", [])):
            return False
        if any(not _has_phrase(text, phrase) for phrase in condition.get("all", [])):
            return False
        if not self._matches_simple(text, condition.get("any", [])) and condition.get("any"):
            return False

        contains_all = condition.get("contains_all", [])
        if any(phrase not in text for phrase in contains_all):
            return False
        contains_any = condition.get("contains_any", [])
        if contains_any and not any(phrase in text for phrase in contains_any):
            return False
        return bool(
            condition.get("all")
            or condition.get("any")
            or contains_all
            or contains_any
            or condition.get("alternatives")
        )

    @staticmethod
    def _keyword_score(message, question):
        score = 0
        for keyword in question["Keyword Pencocokan"].split(";"):
            keyword = keyword.strip()
            if keyword and _has_phrase(message, keyword):
                score += len(keyword.split()) + 1
        return score

    def _select_question(self, message, rule):
        candidates = [
            self.questions[qa_id]
            for qa_id in rule["qa_ids"]
            if qa_id in self.questions
        ]
        if not candidates:
            raise ValueError(f"Rule {rule['id']} tidak memiliki respons Q&A yang valid.")
        return max(
            candidates,
            key=lambda question: self._keyword_score(message, question),
        )

    def reply(self, message):
        normalized = normalize(message)
        for rule in self.rules:
            if self._matches_condition(normalized, rule["condition"]):
                question = self._select_question(normalized, rule)
                return {
                    "reply": question["Respons Chatbot"],
                    "intent": rule["intent_id"],
                    "intent_name": question["Intent"],
                    "category": question["Kategori"],
                    "rule_id": rule["id"],
                    "matched_question": question["Pertanyaan Pengguna"],
                    "score": 1.0,
                }

        question = self.questions[self.knowledge["fallback_qa_id"]]
        fallback_rule = next(
            rule for rule in self.knowledge["rules"] if rule["condition"].get("fallback")
        )
        return {
            "reply": question["Respons Chatbot"],
            "intent": fallback_rule["intent_id"],
            "intent_name": question["Intent"],
            "category": question["Kategori"],
            "rule_id": fallback_rule["id"],
            "matched_question": None,
            "score": 0.0,
        }
