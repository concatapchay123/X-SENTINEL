from __future__ import annotations

from sqlalchemy import select

from x_sentinel.database.models import Role
from x_sentinel.database.session import SessionLocal

ROLES = {
    "admin": "System administrator",
    "analyst": "SOC / analysis user",
    "evaluator": "Blind evaluation role",
}


def main() -> None:
    with SessionLocal() as session, session.begin():
        existing = {r.code for r in session.scalars(select(Role)).all()}
        for code, description in ROLES.items():
            if code not in existing:
                session.add(Role(code=code, description=description))
    print("development seed complete")


if __name__ == "__main__":
    main()
