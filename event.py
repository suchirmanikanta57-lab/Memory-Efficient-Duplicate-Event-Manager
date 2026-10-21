from datetime import datetime
import uuid


class Event:
    """Represents an individual event in a computing environment.

    Examples include user logins, payments, and IoT sensor telemetry.
    """

    def __init__(self, payload: str, event_id: str = None, source: str = "SYSTEM"):
        if not payload or not payload.strip():
            raise ValueError("Event payload cannot be null or empty.")

        self.payload = payload.strip()
        self.id = event_id.strip() if event_id and event_id.strip() else str(uuid.uuid4())[:8]
        self.source = source.strip() if source and source.strip() else "SYSTEM"
        self.timestamp = datetime.now()

    def get_identity_string(self) -> str:
        """Returns the canonical string identity used for hashing and duplicate checking."""
        return self.payload

    def __eq__(self, other) -> bool:
        if isinstance(other, Event):
            return self.payload == other.payload
        return False

    def __hash__(self) -> int:
        return hash(self.payload)

    def __repr__(self) -> str:
        return f"Event(id='{self.id}', source='{self.source}', payload='{self.payload}', time='{self.timestamp.isoformat()}')"
