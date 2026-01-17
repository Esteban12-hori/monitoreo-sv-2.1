
class AgentPlugin:
    """Base class for all metrics plugins"""
    def collect(self) -> dict:
        raise NotImplementedError
