"""
First LLM call — classifies the student's input into one of six categories.
Returns a plain string (the category name), never free text.
"""

import json
import os

from openai import OpenAI
from Backend.prompts import CLASSIFIER_SYSTEM, CLASSIFIER_USER

VALID_CLASSIFICATIONS = {
    "demonstrates_understanding",
    "offers_surprising_insight",
    "expresses_confusion",
    "asks_clarifying_question",
    "minimal_or_evasive",
    "off_topic_or_anachronistic",
}

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _client


def classify(student_input: str, last_aristotle_message: str = "") -> str:
    """
    Classify student_input and return one of the six category strings.
    last_aristotle_message is the preceding Aristotle turn (used for context).
    Raises ValueError if the model returns an unexpected category.
    """
    client = _get_client()

    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": CLASSIFIER_SYSTEM},
            {
                "role": "user",
                "content": CLASSIFIER_USER.format(
                    last_aristotle_message=last_aristotle_message or "(none — this is the first turn)",
                    student_input=student_input,
                ),
            },
        ],
    )

    raw = response.choices[0].message.content
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Classifier returned non-JSON: {raw!r}") from exc

    classification = data.get("classification", "").strip()
    if classification not in VALID_CLASSIFICATIONS:
        raise ValueError(
            f"Classifier returned unknown category: {classification!r}. "
            f"Valid options: {VALID_CLASSIFICATIONS}"
        )

    return classification
