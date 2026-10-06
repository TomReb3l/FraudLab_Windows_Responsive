from .persona import FraudsterPersona
from .memory import ConversationMemory
from .strategy import FraudStrategy
from .guardrails import validate_response

class FraudsterAgent:
    def __init__(self):
        self.persona = FraudsterPersona()
        self.memory = ConversationMemory()
        self.strategy = FraudStrategy()

    def chat(self, visitor_text):
        self.memory.add("visitor", visitor_text)
        self.memory.update_resistance(visitor_text)

        tactic = self.strategy.select(self.memory)

        if tactic == "reassurance":
            response = (
                "Καταλαβαίνω ότι έχεις αμφιβολίες. "
                "Σκέψου προσεκτικά την κατάσταση και έλεγξε τις πληροφορίες."
            )
        else:
            response = (
                "Υπάρχει μια επείγουσα κατάσταση. "
                "Πριν πάρεις οποιαδήποτε απόφαση, σταμάτησε και επιβεβαίωσε τα στοιχεία."
            )

        self.memory.add("agent", response)
        return validate_response(response)
