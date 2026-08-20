"""
State machine for the Aristotle Philosophy Chatbot.

The conversation state is composed of three values:
  - topic:  eudaimonia | doctrine_of_mean | habit_and_practice | phronesis
  - stage:  introduction | examination | challenge | resolution
  - tone:   neutral | approving | skeptical | disappointed | probing

Per-topic counters (reset on every topic change):
  - confusion_count: increments on confusion/evasion, triggers escalating responses
  - correct_streak:  increments on understanding/insight, can skip challenge stage
"""


TOPIC_ORDER = ["eudaimonia", "doctrine_of_mean", "habit_and_practice", "phronesis"]
STAGE_ORDER = ["introduction", "examination", "challenge", "resolution"]

VALID_CLASSIFICATIONS = {
    "demonstrates_understanding",
    "offers_surprising_insight",
    "expresses_confusion",
    "minimal_or_evasive",
    "asks_clarifying_question",
    "off_topic_or_anachronistic",
}


class State:
    def __init__(self):
        self.topic: str = "eudaimonia"
        self.stage: str = "introduction"
        self.tone: str = "neutral"
        self.confusion_count: int = 0
        self.correct_streak: int = 0
        self.is_terminal: bool = False
        self.terminal_type: str | None = None  # "end" or "dismissed"

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def transition(self, classification: str) -> None:
        """Apply the classification and update the state in place."""
        if classification not in VALID_CLASSIFICATIONS:
            raise ValueError(f"Unknown classification: {classification!r}")

        # Terminal state: no further transitions
        if self.is_terminal:
            return

        # Exception: off-topic / anachronistic — bewilderment, no state change
        if classification == "off_topic_or_anachronistic":
            self.tone = "neutral"
            return

        # Clarifying question — answer and re-pose, no stage change
        if classification == "asks_clarifying_question":
            self.tone = "neutral"
            return

        # Confusion or evasion
        if classification in ("expresses_confusion", "minimal_or_evasive"):
            self.correct_streak = 0
            self.confusion_count += 1
            self._apply_confusion_tone()

            if self.confusion_count >= 4:
                self.is_terminal = True
                self.terminal_type = "dismissed"
            elif self.confusion_count == 3:
                # Reset to examination basics
                self.stage = "examination"
                self.tone = "neutral"
            return

        # Understanding or insight
        if classification in ("demonstrates_understanding", "offers_surprising_insight"):
            self.confusion_count = 0
            self.correct_streak += 1
            self._apply_correct_tone()
            self._advance_stage()
            return

    def to_dict(self) -> dict:
        """Serialise state to a plain dict (for JSON responses / session storage)."""
        return {
            "topic": self.topic,
            "stage": self.stage,
            "tone": self.tone,
            "confusion_count": self.confusion_count,
            "correct_streak": self.correct_streak,
            "is_terminal": self.is_terminal,
            "terminal_type": self.terminal_type,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "State":
        """Reconstruct a State from a previously serialised dict."""
        s = cls()
        s.topic = data["topic"]
        s.stage = data["stage"]
        s.tone = data["tone"]
        s.confusion_count = data["confusion_count"]
        s.correct_streak = data["correct_streak"]
        s.is_terminal = data["is_terminal"]
        s.terminal_type = data["terminal_type"]
        return s

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _apply_confusion_tone(self) -> None:
        if self.confusion_count >= 2:
            self.tone = "disappointed"
        else:
            self.tone = "skeptical"

    def _apply_correct_tone(self) -> None:
        # correct_streak >= 2 signals "warm approving" to the generator
        self.tone = "approving"

    def _advance_stage(self) -> None:
        current_stage_idx = STAGE_ORDER.index(self.stage)

        # High streak — skip challenge, jump to resolution
        if self.stage == "examination" and self.correct_streak >= 3:
            self.stage = "resolution"
            return

        if current_stage_idx < len(STAGE_ORDER) - 1:
            next_stage = STAGE_ORDER[current_stage_idx + 1]
            self.stage = next_stage
            if self.stage == "challenge":
                self.tone = "probing"
        else:
            # Completed resolution — advance topic
            current_topic_idx = TOPIC_ORDER.index(self.topic)
            if current_topic_idx < len(TOPIC_ORDER) - 1:
                self.topic = TOPIC_ORDER[current_topic_idx + 1]
                self.stage = "introduction"
                self.tone = "neutral"
                self.confusion_count = 0
                self.correct_streak = 0
            else:
                # Completed phronesis — end of conversation
                self.is_terminal = True
                self.terminal_type = "end"
