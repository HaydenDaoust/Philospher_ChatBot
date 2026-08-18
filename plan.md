# Aristotle Philosophy Chatbot — Development Plan

## Project Overview

A conversational web application that simulates a dialogue with Aristotle about virtue ethics. The application uses retrieval-augmented generation (RAG) to ground responses in the actual text of the Nicomachean Ethics, a state machine to drive the flow and tone of conversation, and a two-step LLM pipeline to classify student input and generate Aristotle's response.

**Source Text:** Nicomachean Ethics, translated by W. D. Ross (MIT Internet Classics Archive)  
**Backend:** Python / FastAPI  
**Frontend:** HTML, CSS, vanilla JavaScript  
**Vector Database:** ChromaDB  
**Embeddings:** sentence-transformers  
**LLM:** OpenAI API  

---

## Folder Structure

```
aristotle-chatbot/
├── backend/
│   ├── main.py              # FastAPI app and /chat endpoint
│   ├── state_machine.py     # State class, transition logic, counters
│   ├── classifier.py        # First LLM call — classifies student input
│   ├── generator.py         # Second LLM call — generates Aristotle's response
│   ├── retriever.py         # ChromaDB queries and RAG logic
│   ├── loader.py            # One-time script to chunk and load source text
│   └── prompts.py           # All prompt templates in one place
├── frontend/
│   ├── index.html           # Main page layout
│   ├── style.css            # Styling and pottery image display
│   └── script.js            # API calls and UI state management
├── texts/
│   └── nicomachean_ethics.txt   # Raw source text (stripped of HTML)
├── images/
│   ├── neutral.png
│   ├── approving.png
│   ├── skeptical.png
│   ├── disappointed.png
│   └── probing.png
└── .env                     # API key — never commit this to GitHub
```

---

## State Machine

### State Components

The full state at any moment is the combination of three values:

| Component | Possible Values |
|-----------|----------------|
| Topic | eudaimonia, doctrine_of_mean, habit_and_practice, phronesis |
| Stage | introduction, examination, challenge, resolution |
| Tone | neutral, approving, skeptical, disappointed, probing |

### Topic Order
```
eudaimonia → doctrine_of_mean → habit_and_practice → phronesis → END
```

### Per-Topic Counters (reset to 0 on every topic change)

**confusion_count** — increments when classifier returns `expresses_confusion` or `minimal_or_evasive`
- 1–2: disappointed tone, Aristotle rephrases and tries a different angle
- 3: reset to neutral, Aristotle steps all the way back to basics and restarts examination stage
- 4: formal dismissal — conversation ends, student must restart

**correct_streak** — increments when classifier returns `demonstrates_understanding` or `offers_surprising_insight`, resets to 0 on any other classification
- 1: approving tone
- 2: warm approving tone, Aristotle acknowledges genuine understanding
- 3+: challenge stage may be shortened or skipped

### Stage Transitions

**Introduction**
- Any substantive response → advance to examination, tone shifts to probing
- Off-topic or anachronistic → bewilderment response, no state change

**Examination**
- `demonstrates_understanding` → advance to challenge, tone shifts to approving then probing, increment correct_streak
- `offers_surprising_insight` → advance to challenge, tone shifts to warm approving, increment correct_streak
- `expresses_confusion` → stay in examination, tone shifts to disappointed, rephrase, increment confusion_count
- `minimal_or_evasive` → stay in examination, tone shifts to skeptical, increment confusion_count
- `asks_clarifying_question` → stay in examination, tone stays neutral, Aristotle answers then re-poses question

**Challenge**
- `demonstrates_understanding` → advance to resolution, tone shifts to approving
- `offers_surprising_insight` → advance to resolution, tone shifts to warm approving
- `expresses_confusion` → stay in challenge, tone shifts to disappointed, increment confusion_count
- `minimal_or_evasive` → stay in challenge, tone shifts to skeptical, increment confusion_count

**Resolution**
- Any substantive response → advance to next topic, reset stage to introduction, reset counters
- Final topic (phronesis) resolution → advance to END state, trigger benediction response

### Exception State
- `off_topic_or_anachronistic` (any stage, any topic) → Aristotle responds with genuine bewilderment, firm redirect back to topic, no state change, no counter change

### Terminal States
- **END (benediction)** — student completed all four topics successfully. Aristotle delivers a closing statement and assigns a reflective question as homework.
- **DISMISSED** — confusion_count hit 4 on any topic. Aristotle formally closes the session and instructs the student to return when ready.

---

## Classifier Categories

The first LLM call maps the student's input to exactly one of these categories. Output must be a structured JSON value, never free text.

| Category | Description |
|----------|-------------|
| `demonstrates_understanding` | Student shows clear grasp of the concept |
| `expresses_confusion` | Student is genuinely lost or uncertain |
| `offers_surprising_insight` | Student makes an unexpected but relevant connection |
| `asks_clarifying_question` | Student asks for explanation or definition |
| `minimal_or_evasive` | Student gives a non-answer or avoids committing |
| `off_topic_or_anachronistic` | Student references something outside Aristotle's world |

---

## RAG Setup

### Source Text Preparation
- Download the W. D. Ross translation from MIT Internet Classics Archive
- Strip all HTML tags
- Remove chapter headers and section numbers that could pollute chunks
- Save as plain text in `/texts/nicomachean_ethics.txt`

### Chunking Parameters
- **Chunk size:** ~400 words
- **Overlap:** 50–75 words between adjacent chunks
- **Topic tagging:** each chunk is manually or heuristically tagged with one of the four topics based on which book and chapter it comes from

### Topic-to-Source Mapping
| Topic | Primary Chapters |
|-------|-----------------|
| eudaimonia | Book I, Ch. 1–2, 7, 10 |
| doctrine_of_mean | Book II, Ch. 6, 9; Book III, Ch. 6–12 |
| habit_and_practice | Book II, Ch. 1–2; Book X, Ch. 9 |
| phronesis | Book VI, Ch. 5, 7, 12–13 |

### ChromaDB Collection Structure
Each chunk is stored with:
- `document`: the raw text of the chunk
- `metadata`: `{ "topic": "<topic_name>", "chunk_id": <int> }`
- `embedding`: generated by sentence-transformers

### Query Flow (every conversation turn)
1. Convert student input to embedding vector
2. Query ChromaDB filtered by current topic tag
3. Retrieve top 3–5 most similar chunks
4. Pass chunk text into generation prompt as context

---

## Two-Step LLM Pipeline

### Call 1 — Classifier (`classifier.py`)

**Input:** raw student text  
**Prompt:** minimal, focused. Provide the six category names and their descriptions. Instruct the model to return only a JSON object like `{"classification": "demonstrates_understanding"}`. No preamble, no explanation.  
**Output:** parsed JSON, single classification string  
**Model:** OpenAI (gpt-4o recommended for accuracy on structured output)

### Call 2 — Generator (`generator.py`)

**Input:** current state (topic, stage, tone), classification result, RAG chunks, conversation history  
**System prompt:** Aristotle character document (personality, rhetorical style, values, exception handling)  
**User prompt:** structured context block containing:
  - Current topic and stage
  - Current tone instruction
  - Classification of student's last response
  - Relevant RAG passages
  - Last few turns of conversation history
  - Instruction on response length (keep it focused, 3–5 sentences max unless resolving a topic)

**Output:** Aristotle's next response as plain text  
**Model:** OpenAI (gpt-4o)

---

## `state_machine.py` — Implementation Blueprint

```python
class State:
    def __init__(self):
        self.topic = "eudaimonia"
        self.stage = "introduction"
        self.tone = "neutral"
        self.confusion_count = 0
        self.correct_streak = 0
        self.is_terminal = False
        self.terminal_type = None  # "end" or "dismissed"

    def transition(self, classification: str) -> None:
        # Handle exception state first regardless of stage
        if classification == "off_topic_or_anachronistic":
            self.tone = "neutral"
            return  # no other state changes

        # Handle confusion and evasion counters
        if classification in ("expresses_confusion", "minimal_or_evasive"):
            self.correct_streak = 0
            self.confusion_count += 1
            self._apply_confusion_tone()
            if self.confusion_count >= 4:
                self.is_terminal = True
                self.terminal_type = "dismissed"
            elif self.confusion_count == 3:
                self.stage = "examination"  # reset to basics
                self.tone = "neutral"
            return

        # Handle correct/insightful responses
        if classification in ("demonstrates_understanding", "offers_surprising_insight"):
            self.confusion_count = 0
            self.correct_streak += 1
            self._apply_correct_tone()
            self._advance_stage()
            return

        # Handle clarifying questions
        if classification == "asks_clarifying_question":
            self.tone = "neutral"
            return  # stay in place, answer the question

    def _apply_confusion_tone(self):
        if self.confusion_count >= 2:
            self.tone = "disappointed"
        else:
            self.tone = "skeptical"

    def _apply_correct_tone(self):
        if self.correct_streak >= 2:
            self.tone = "approving"  # warm approving variant signaled via streak value
        else:
            self.tone = "approving"

    def _advance_stage(self):
        topic_order = ["eudaimonia", "doctrine_of_mean", "habit_and_practice", "phronesis"]
        stage_order = ["introduction", "examination", "challenge", "resolution"]

        current_stage_idx = stage_order.index(self.stage)

        # Skip or shorten challenge if correct_streak is high
        if self.stage == "examination" and self.correct_streak >= 3:
            next_stage = "resolution"
        elif current_stage_idx < len(stage_order) - 1:
            next_stage = stage_order[current_stage_idx + 1]
        else:
            # End of stage — advance topic
            current_topic_idx = topic_order.index(self.topic)
            if current_topic_idx < len(topic_order) - 1:
                self.topic = topic_order[current_topic_idx + 1]
                self.stage = "introduction"
                self.tone = "neutral"
                self.confusion_count = 0
                self.correct_streak = 0
            else:
                # Completed phronesis — end of conversation
                self.is_terminal = True
                self.terminal_type = "end"
            return

        self.stage = next_stage
        if self.stage == "challenge":
            self.tone = "probing"
```

---

## `loader.py` — Implementation Blueprint

```python
# Run this script once before starting the app
# Steps:
# 1. Read nicomachean_ethics.txt
# 2. Split into chunks of ~400 words with ~60 word overlap
# 3. Tag each chunk with a topic based on position in text
#    (use approximate character/word offsets matching the book/chapter map above)
# 4. Generate embeddings using sentence-transformers
#    model = SentenceTransformer('all-MiniLM-L6-v2')
# 5. Store in ChromaDB local collection named "aristotle"
```

---

## `main.py` — Implementation Blueprint

```python
# Single POST endpoint: /chat
# Request body: { "user_input": str, "conversation_history": list }
# 
# Flow:
# 1. Load current state (or initialize new state if first turn)
# 2. Call classifier(user_input) → classification string
# 3. Call state.transition(classification)
# 4. If state.is_terminal → call generator with terminal context, return response
# 5. Call retriever(user_input, current_topic) → list of RAG chunks
# 6. Call generator(state, classification, rag_chunks, conversation_history) → response text
# 7. Return { "response": str, "tone": str, "is_terminal": bool, "terminal_type": str }
#
# Note: state must be managed per session.
# Simple approach: store state in a server-side dict keyed by session_id
# session_id can be generated on first request and stored in browser localStorage
```

---

## Frontend Blueprint (`index.html`, `style.css`, `script.js`)

### Layout
- Left or center panel: pottery image of Aristotle (changes based on tone)
- Text area below or beside image: Aristotle's current response
- Input box at bottom: student types their response
- Submit button

### Tone-to-Image Mapping
| Tone | Image File |
|------|-----------|
| neutral | neutral.png |
| approving | approving.png |
| skeptical | skeptical.png |
| disappointed | disappointed.png |
| probing | probing.png |

### script.js Flow
1. On page load, generate a session_id (UUID) and store in memory
2. On submit, POST to `/chat` with `{ user_input, conversation_history, session_id }`
3. Receive `{ response, tone, is_terminal, terminal_type }`
4. Update Aristotle's text display
5. Swap pottery image based on tone value
6. If `is_terminal` is true, disable input and show appropriate closing message
7. Append turn to local conversation_history array for next request

---

## Build Order

Build and test each component in isolation before connecting them:

1. **`loader.py`** — chunk the text, load into ChromaDB, verify retrieval works with a test query
2. **`state_machine.py`** — test all transitions with hardcoded classification inputs, no LLM needed
3. **`classifier.py`** — test with sample student sentences, verify structured JSON output
4. **`retriever.py`** — test topic-filtered queries, verify relevant chunks are returned
5. **`generator.py`** — test with mock state and RAG context, verify character voice and length
6. **`main.py`** — wire everything together, test full turn via curl or Postman
7. **Frontend** — build last, connect to working backend

---

## Key Design Decisions Summary

| Decision | Choice | Reason |
|----------|--------|--------|
| Chunk size | ~400 words with 60-word overlap | Preserves complete arguments, avoids context loss at boundaries |
| Topic filtering in RAG | Filter by current topic tag | Keeps retrieval focused, prevents cross-topic noise |
| Classifier output | Structured JSON only | Machine-readable, directly drives state transitions |
| State storage | Server-side dict by session_id | Simple, no database needed for a single-user project |
| Response length | 3–5 sentences max | Keeps Aristotle focused and in character, avoids walls of text |
| Streak/confusion counters | Reset per topic | Treats each concept as an independent domain of understanding |

---

## Environment Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install fastapi uvicorn openai chromadb sentence-transformers python-dotenv

# Run loader (once)
python backend/loader.py

# Run server
uvicorn backend.main:app --reload
```

**.env file:**
```
OPENAI_API_KEY=your_key_here
```

---

## Notes and Reminders

- Never commit `.env` to GitHub — add it to `.gitignore` immediately
- The loader script only needs to be run once unless you change the source text or chunking parameters
- Test the state machine thoroughly before touching LLM code — most conversation bugs come from transition logic, not generation
- Keep prompt templates in `prompts.py` so they are easy to iterate on without touching logic files
- The character document is the foundation of the generator system prompt — paste it in directly