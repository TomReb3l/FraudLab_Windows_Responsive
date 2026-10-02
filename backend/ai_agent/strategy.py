class FraudStrategy:
    def select(self, memory):
        if memory.resistance > 0:
            return "reassurance"
        return "urgency"
