import re

MAX_INPUT_LEN = 1000

BLOCKED_PATTERNS = [
    r"(.)\1{10,}",       # repeated chars (aaaaaaaaaa...)
    r"(https?://\S+){3,}", # flood of links
]


class GuardrailError(Exception):
    """Raised when input/output fails validation. message is shown to the user."""

    def __init__(self, user_message: str):
        self.user_message = user_message
        super().__init__(user_message)


def validate_input(text: str) -> str:
    """Sanitize and validate inbound message. Returns cleaned text or raises GuardrailError."""
    text = text.strip()

    if not text:
        raise GuardrailError("Pode me contar o que você está buscando? 😊")

    if len(text) > MAX_INPUT_LEN:
        raise GuardrailError(
            f"Mensagem muito longa! Resume em até {MAX_INPUT_LEN} caracteres, por favor."
        )

    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, text):
            raise GuardrailError("Não entendi sua mensagem. Pode reformular? 😊")

    return text


def validate_output(text: str) -> str:
    """Post-process agent output: inject disclaimer, enforce WhatsApp length limit."""
    # Inject price disclaimer if prices present and disclaimer absent
    if re.search(r"R\$\s*\d+", text) and "estimad" not in text.lower() and "confirme" not in text.lower():
        text += "\n\n_Valores estimados — confirme disponibilidade no momento da reserva._"

    # WhatsApp max ~4096 chars
    if len(text) > 4000:
        text = text[:3990] + "\n[...]"

    return text
