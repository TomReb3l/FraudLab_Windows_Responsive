class FraudsterPersona:
    def __init__(self):
        self.name = "Nikos"
        self.role = "fake_relative"
        self.emotion = "panic"
        self.goal = "create_trust"

    def context(self):
        return {
            "name": self.name,
            "role": self.role,
            "emotion": self.emotion,
            "goal": self.goal
        }
