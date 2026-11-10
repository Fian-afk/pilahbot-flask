import json
import re
from difflib import SequenceMatcher
from pathlib import Path


DEFAULT_THRESHOLD = 0.45
STOPWORDS = {
    "yang", "di", "ke", "dari", "dan", "atau", "itu", "ini", "untuk", "dengan",
    "adalah", "apa", "saya", "mau", "ingin", "tolong", "bisa", "boleh", "kah",
    "pada", "akan", "juga", "ada", "tentang", "mohon", "info", "informasi",
}


def normalize(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return " ".join(text.split())


def preprocess(text):
    return [word for word in normalize(text).split() if word not in STOPWORDS]


def similarity(text, pattern):
    tokens_a = preprocess(text)
    tokens_b = preprocess(pattern)
    if not tokens_a or not tokens_b:
        return 0.0

    set_a, set_b = set(tokens_a), set(tokens_b)
    matched_b = {
        token_b
        for token_b in set_b
        if any(
            token_a == token_b or (len(token_b) >= 4 and token_b in token_a)
            for token_a in set_a
        )
    }
    intersection = len(matched_b)
    jaccard = intersection / (len(set_a) + len(set_b) - intersection)
    fuzzy = SequenceMatcher(None, " ".join(tokens_a), " ".join(tokens_b)).ratio()
    coverage = intersection / len(set_b)
    return round(0.4 * jaccard + 0.3 * fuzzy + 0.3 * coverage, 4)


def _has_phrase(text, phrase):
    return f" {normalize(phrase)} " in f" {text} "


class ChatbotEngine:
    def __init__(self, knowledge, threshold=DEFAULT_THRESHOLD):
        self.knowledge = knowledge
        self.threshold = threshold
        self.questions = {
            item["QA ID"]: item for item in knowledge["questions"]
        }
        self.rules = sorted(
            (rule for rule in knowledge["rules"] if not rule["condition"].get("fallback")),
            key=lambda rule: rule["priority"],
        )

    @classmethod
    def from_file(cls, path, threshold=DEFAULT_THRESHOLD):
        with Path(path).open(encoding="utf-8") as knowledge_file:
            return cls(json.load(knowledge_file), threshold)

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
    def _question_score(message, question):
        return similarity(message, question["Keyword Pencocokan"].replace(";", " "))

    def _best_question(self, message, questions):
        return max(
            questions,
            key=lambda question: self._question_score(message, question),
        )

    def best_match(self, message):
        candidates = [
            question
            for question in self.knowledge["questions"]
            if question["QA ID"] != self.knowledge["fallback_qa_id"]
        ]
        question = self._best_question(message, candidates)
        return question, self._question_score(message, question)

    def _select_question(self, message, rule):
        candidates = [
            self.questions[qa_id]
            for qa_id in rule["qa_ids"]
            if qa_id in self.questions
        ]
        if not candidates:
            raise ValueError(f"Rule {rule['id']} tidak memiliki respons Q&A yang valid.")
        return self._best_question(message, candidates)

    def reply(self, message):
        normalized = normalize(message)
        best_question, best_score = self.best_match(normalized)
        for rule in self.rules:
            if self._matches_condition(normalized, rule["condition"]):
                question = self._select_question(normalized, rule)
                score = self._question_score(normalized, question)
                if score >= self.threshold:
                    return {
                        "reply": question["Respons Chatbot"],
                        "intent": rule["intent_id"],
                        "intent_name": question["Intent"],
                        "category": question["Kategori"],
                        "rule_id": rule["id"],
                        "matched_question": question["Pertanyaan Pengguna"],
                        "score": score,
                    }

        if best_score >= self.threshold:
            matching_rule = next(
                (
                    rule
                    for rule in self.rules
                    if best_question["QA ID"] in rule["qa_ids"]
                ),
                None,
            )
            return {
                "reply": best_question["Respons Chatbot"],
                "intent": best_question["Intent ID"],
                "intent_name": best_question["Intent"],
                "category": best_question["Kategori"],
                "rule_id": matching_rule["id"] if matching_rule else None,
                "matched_question": best_question["Pertanyaan Pengguna"],
                "score": best_score,
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
            "score": best_score,
        }
