class ConversationMemory:
    def __init__(self):
        self.messages = []
        self.resistance = 0

    def add(self, role, text):
        self.messages.append({
            "role": role,
            "text": text
        })

    def update_resistance(self, text):
        keywords = ["όχι", "δεν", "αστυνομία", "ελέγξω"]
        if any(k in text.lower() for k in keywords):
            self.resistance += 1
