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
            answer["id"]: {
                **answer,
                "intent_id": intent["id"],
                "tag": intent["tag"],
            }
            for intent in knowledge["intents"]
            for answer in intent["answers"]
        }
        self.question_list = list(self.questions.values())
        self.rules = sorted(
            (
                {**rule, "intent_id": intent["id"]}
                for intent in knowledge["intents"]
                for rule in intent["rules"]
            ),
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
        return similarity(message, " ".join(question["patterns"]))

    def _best_question(self, message, questions):
        return max(
            questions,
            key=lambda question: self._question_score(message, question),
        )

    def best_match(self, message):
        question = self._best_question(message, self.question_list)
        return question, self._question_score(message, question)

    def _select_question(self, message, rule):
        candidates = [
            self.questions[answer_id]
            for answer_id in rule["answer_ids"]
            if answer_id in self.questions
        ]
        if not candidates:
            raise ValueError(f"Rule {rule['id']} tidak memiliki respons Q&A yang valid.")
        return self._best_question(message, candidates)

    def reply(self, message):
        normalized = normalize(message)
        best_question, best_score = self.best_match(normalized)
        for rule in self.rules:
            if self._matches_condition(normalized, rule["when"]):
                question = self._select_question(normalized, rule)
                score = self._question_score(normalized, question)
                if score >= self.threshold:
                    return {
                        "reply": question["response"],
                        "intent": rule["intent_id"],
                        "intent_name": question["tag"],
                        "category": question["category"],
                        "rule_id": rule["id"],
                        "matched_question": question["question"],
                        "score": score,
                    }

        if best_score >= self.threshold:
            matching_rule = next(
                (
                    rule
                    for rule in self.rules
                    if best_question["id"] in rule["answer_ids"]
                ),
                None,
            )
            return {
                "reply": best_question["response"],
                "intent": best_question["intent_id"],
                "intent_name": best_question["tag"],
                "category": best_question["category"],
                "rule_id": matching_rule["id"] if matching_rule else None,
                "matched_question": best_question["question"],
                "score": best_score,
            }

        fallback = self.knowledge["fallback"]
        return {
            "reply": fallback["response"],
            "intent": fallback["intent_id"],
            "intent_name": fallback["tag"],
            "category": fallback["category"],
            "rule_id": fallback["rule_id"],
            "matched_question": None,
            "score": best_score,
        }
