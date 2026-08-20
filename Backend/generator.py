"""
Second LLM call — generates Aristotle's response.

Takes the current state, classification, RAG chunks, and conversation history.
Returns Aristotle's reply as a plain string.
"""

import os

from openai import OpenAI
from Backend.prompts import GENERATOR_SYSTEM, build_generator_prompt
from Backend.state_machine import State

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _client


def generate(
    state: State,
    classification: str,
    rag_chunks: list[str],
    conversation_history: list[dict],
    student_input: str,
) -> str:
    """
    Generate Aristotle's next response.

    Parameters
    ----------
    state               : current (already-transitioned) State object
    classification      : result from classifier.classify()
    rag_chunks          : list of text chunks from retriever.retrieve()
    conversation_history: list of {"role": "user"|"assistant", "content": str}
    student_input       : raw student message for this turn

    Returns
    -------
    Aristotle's response as a plain string.
    """
    client = _get_client()

    user_prompt = build_generator_prompt(
        state=state,
        classification=classification,
        rag_chunks=rag_chunks,
        conversation_history=conversation_history,
        student_input=student_input,
    )

    response = client.chat.completions.create(
        model="gpt-5-mini",
        max_completion_tokens=4096,
        messages=[
            {"role": "system", "content": GENERATOR_SYSTEM},
            {"role": "user",   "content": user_prompt},
        ],
    )

    return response.choices[0].message.content.strip()
