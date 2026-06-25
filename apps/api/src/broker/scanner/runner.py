from sqlalchemy.orm import Session


class ScanRunner:
    def __init__(self, db: Session) -> None:
        self.db = db

    def run_full_scan(self) -> None:
        # Sprint 2: implement full scan orchestration
        raise NotImplementedError("Scanner not yet implemented — coming in Sprint 2")
