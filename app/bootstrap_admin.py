import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import auth
import db


def main():
    full_name = input("Administrator full name: ").strip()
    email = input("Administrator email: ").strip().lower()
    password = getpass.getpass("Administrator password (12+ characters): ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        raise SystemExit("Passwords do not match.")
    full_name, email = auth._validate_registration(full_name, email, password)
    password_hash = auth._password_hasher.hash(password)

    def create(cur):
        cur.execute(
            "SELECT GET_LOCK('research_collaboration_admin_bootstrap', 10) AS acquired"
        )
        if int(cur.fetchone()["acquired"] or 0) != 1:
            raise ValueError("Could not acquire the one-time administrator bootstrap lock.")
        cur.execute("SELECT user_id FROM APP_USER WHERE role = 'ADMIN' FOR UPDATE")
        if cur.fetchone() is not None:
            raise ValueError("An administrator already exists; bootstrap is one-time.")
        cur.execute(
            """INSERT INTO APP_USER (full_name, email, password_hash, role)
               VALUES (%s, %s, %s, 'ADMIN')""",
            (full_name, email, password_hash),
        )
        user_id = cur.lastrowid
        auth._audit(
            cur, user_id, "ADMIN_BOOTSTRAPPED", "APP_USER", user_id,
            {"email": email, "role": "ADMIN"},
        )
        return user_id

    print(f"Created initial administrator account (user ID {db.transaction(create)}).")


if __name__ == "__main__":
    main()
