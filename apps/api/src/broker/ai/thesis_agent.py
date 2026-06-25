from sqlalchemy.orm import Session


class ThesisAgent:
    def __init__(self, db: Session) -> None:
        self.db = db

    def generate(self, ticker: str, scan_result_id: int | None = None, force_refresh: bool = False) -> None:
        # Sprint 3: implement Claude-powered thesis generation
        raise NotImplementedError("Thesis agent not yet implemented — coming in Sprint 3")
