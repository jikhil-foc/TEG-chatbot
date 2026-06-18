"""Canned greeting and fallback responses for QA nodes.

Bilingual message tables keep greeting and off-topic replies consistent across
nodes without another LLM call. ``OFF_TOPIC_MARKERS`` lets citation parsing
treat model-generated fallback text as having no citable sources.
"""

from __future__ import annotations

_DEFAULT_LANGUAGE = "English"

FALLBACK_MESSAGES = {
    "English": "Please ask questions related to TEG. I'm here to help with TEG website content.",
    "Irish": "Cuir ceist a bhaineann le TEG, le do thoil. Tá mé anseo chun cabhrú le hábhar láithreán TEG.",
}

GREETING_MESSAGES = {
    "hello": {
        "English": (
            "Hello! I can help answer questions about TEG based on our published "
            "content. What would you like to know?"
        ),
        "Irish": (
            "Dia dhuit! Is féidir liom cabhrú le ceisteanna faoi TEG bunaithe ar "
            "ár n-ábhar foilsithe. Cad ba mhaith leat a fháil amach?"
        ),
    },
    "thanks": {
        "English": "You're welcome! Let me know if you have any other TEG questions.",
        "Irish": "Tá fáilte romhat! Cuir ceist eile faoi TEG orm más gá.",
    },
    "farewell": {
        "English": (
            "Goodbye! Feel free to come back if you have more questions about TEG."
        ),
        "Irish": (
            "Slán! Tar ar ais má bhíonn tuilleadh ceisteanna agat faoi TEG."
        ),
    },
}

OFF_TOPIC_MARKERS = tuple(
    phrase.lower()
    for phrase in (
        *FALLBACK_MESSAGES.values(),
        "Please ask questions related to TEG.",
        "I'm here to help with TEG website content.",
    )
)

DEFAULT_LANGUAGE = _DEFAULT_LANGUAGE
