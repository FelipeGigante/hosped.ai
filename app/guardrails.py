"""Input and output guardrails.

Input guardrail runs BEFORE the agent — rejects spam, injection attempts,
out-of-scope requests without wasting LLM tokens.

Output guardrail runs AFTER the agent — enforces disclaimers and length limits.
"""

import re

MAX_INPUT_LEN = 1000

# Patterns that indicate spam or malformed input
_BLOCKED_PATTERNS = [
    r"(.)\1{10,}",            # repeated chars (aaaaaaaaaaaa...)
    r"(https?://\S+\s*){3,}", # flood of URLs
    r"<[a-z]+[^>]*>",         # HTML injection attempt
]

# Keywords that suggest prompt injection attempts
_INJECTION_KEYWORDS = [
    "ignore previous instructions",
    "ignore all instructions",
    "disregard your instructions",
    "you are now",
    "new persona",
    "forget everything",
    "system prompt",
]

# Out-of-scope topics that don't need the agent at all
_OUT_OF_SCOPE_PATTERNS = [
    r"\b(passagem|voo|avião|aéreo|aérea|flight|airline)\b",
    r"\b(aluguel de carro|rent.?a.?car|locadora)\b",
    r"\b(seguro.?(viagem|vida|saúde))\b",
]

_OUT_OF_SCOPE_RESPONSES = {
    "flight": "Passagens aéreas são com as companhias aéreas — recomendo o Google Voos ou Decolar! ✈️ Mas posso ajudar com seu hotel? 😊",
    "car": "Aluguel de carro não é minha especialidade — tente Localiza ou Movida! 🚗 Mas posso achar seu hotel? 😊",
    "insurance": "Seguro viagem recomendo a Assist Card ou sua seguradora! 🛡️ Mas posso achar seu hotel? 😊",
}


class GuardrailError(Exception):
    """Raised when input fails validation. user_message is shown to the user."""

    def __init__(self, user_message: str):
        self.user_message = user_message
        super().__init__(user_message)


class OutOfScopeError(GuardrailError):
    """Raised for out-of-scope requests — has a helpful redirect message."""
    pass


def validate_input(text: str) -> str:
    """Sanitize and validate inbound message.

    Returns cleaned text on success.
    Raises GuardrailError with user-facing message on failure.
    Does NOT initialize the agent — cheap, deterministic checks only.
    """
    text = text.strip()

    if not text:
        raise GuardrailError("Pode me contar o que você está buscando? 😊")

    if len(text) > MAX_INPUT_LEN:
        raise GuardrailError(f"Mensagem muito longa! Pode resumir em até {MAX_INPUT_LEN} caracteres? 😊")

    # Spam / malformed
    for pattern in _BLOCKED_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            raise GuardrailError("Não entendi sua mensagem. Pode reformular? 😊")

    # Prompt injection
    lower = text.lower()
    for kw in _INJECTION_KEYWORDS:
        if kw in lower:
            raise GuardrailError("Só consigo ajudar com hospedagem no Brasil! Como posso te ajudar? 😊")

    # Out-of-scope (deterministic, no LLM needed)
    if re.search(_OUT_OF_SCOPE_PATTERNS[0], text, re.IGNORECASE):
        raise OutOfScopeError(_OUT_OF_SCOPE_RESPONSES["flight"])
    if re.search(_OUT_OF_SCOPE_PATTERNS[1], text, re.IGNORECASE):
        raise OutOfScopeError(_OUT_OF_SCOPE_RESPONSES["car"])
    if re.search(_OUT_OF_SCOPE_PATTERNS[2], text, re.IGNORECASE):
        raise OutOfScopeError(_OUT_OF_SCOPE_RESPONSES["insurance"])

    return text


def validate_output(text: str) -> str:
    """Post-process agent output.

    - Injects price disclaimer if prices present without one
    - Enforces WhatsApp character limit
    """
    if not text:
        return "Desculpe, tive um problema interno. Pode repetir? 🙏"

    # Inject disclaimer when prices shown but no disclaimer present
    has_price = bool(re.search(r"R\$\s*\d+", text))
    has_disclaimer = any(w in text.lower() for w in ["estimad", "confirme", "confirm"])
    if has_price and not has_disclaimer:
        text += "\n\n_Valores estimados — confirme disponibilidade no momento da reserva._"

    # WhatsApp limit ~4096 chars
    if len(text) > 4000:
        text = text[:3990] + "\n\n[...]"

    return text
