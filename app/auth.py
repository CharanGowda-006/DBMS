import re
import time

import streamlit as st
from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError

import db

SESSION_TTL_SECONDS = 8 * 60 * 60
_password_hasher = PasswordHasher(type=Type.ID)


class AuthenticationError(ValueError):
    pass


class AuthorizationError(PermissionError):
    pass


def _validate_registration(full_name, email, password):
    full_name = (full_name or "").strip()
    email = (email or "").strip().lower()
    if not full_name or len(full_name) > 150:
        raise AuthenticationError("Enter a name of 1 to 150 characters.")
    if len(email) > 255 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise AuthenticationError("Enter a valid email address.")
    if not password or len(password) < 12:
        raise AuthenticationError("Password must contain at least 12 characters.")
    return full_name, email


def _audit(cur, actor_user_id, action, entity_type, entity_id, new_values=None):
    import json

    cur.execute(
        """INSERT INTO AUDIT_LOG
           (actor_user_id, action, entity_type, entity_id, new_values)
           VALUES (%s, %s, %s, %s, %s)""",
        (
            actor_user_id,
            action,
            entity_type,
            entity_id,
            json.dumps(new_values) if new_values is not None else None,
        ),
    )


def register_user(full_name, email, password):
    full_name, email = _validate_registration(full_name, email, password)
    password_hash = _password_hasher.hash(password)

    def create(cur):
        cur.execute(
            """INSERT INTO APP_USER (full_name, email, password_hash, role)
               VALUES (%s, %s, %s, 'STUDENT')""",
            (full_name, email, password_hash),
        )
        user_id = cur.lastrowid
        _audit(
            cur, user_id, "USER_REGISTERED", "APP_USER", user_id,
            {"email": email, "role": "STUDENT"},
        )
        return user_id

    return db.transaction(create)


def authenticate_user(email, password):
    email = (email or "").strip().lower()
    if not email or not password:
        return None
    rows = db.query(
        """SELECT user_id, full_name, email, password_hash, role, is_active
           FROM APP_USER WHERE email = %s""",
        (email,),
    )
    if rows.empty:
        return None

    account = rows.iloc[0].to_dict()
    if not account["is_active"]:
        return None
    try:
        valid = _password_hasher.verify(account["password_hash"], password)
    except (VerificationError, InvalidHashError):
        return None
    if not valid:
        return None

    if _password_hasher.check_needs_rehash(account["password_hash"]):
        db.execute(
            "UPDATE APP_USER SET password_hash = %s WHERE user_id = %s",
            (_password_hasher.hash(password), int(account["user_id"])),
        )
    return {key: account[key] for key in ("user_id", "full_name", "email", "role")}


def login_user(email, password, state=None):
    state = st.session_state if state is None else state
    state.pop("auth_user_id", None)
    state.pop("auth_started_at", None)
    account = authenticate_user(email, password)
    if account is None:
        return False
    state["auth_user_id"] = int(account["user_id"])
    state["auth_started_at"] = time.time()
    return True


def logout_user(state=None):
    state = st.session_state if state is None else state
    state.pop("auth_user_id", None)
    state.pop("auth_started_at", None)


def _session_user_id(state):
    user_id = state.get("auth_user_id")
    started_at = state.get("auth_started_at")
    if user_id is None or started_at is None:
        logout_user(state)
        return None
    try:
        user_id = int(user_id)
        age = time.time() - float(started_at)
    except (TypeError, ValueError):
        logout_user(state)
        return None
    if user_id < 1 or age < 0 or age > SESSION_TTL_SECONDS:
        logout_user(state)
        return None
    return user_id


def get_current_user(state=None):
    state = st.session_state if state is None else state
    user_id = _session_user_id(state)
    if user_id is None:
        return None

    rows = db.query(
        """SELECT user_id, full_name, email, role
           FROM APP_USER WHERE user_id = %s AND is_active = TRUE""",
        (int(user_id),),
    )
    if rows.empty:
        logout_user(state)
        return None
    return rows.iloc[0].to_dict()


def require_actor(cur, allowed_roles):
    state = st.session_state
    user_id = _session_user_id(state)
    if user_id is None:
        raise AuthorizationError("Login is required.")

    cur.execute(
        """SELECT user_id, full_name, email, role
           FROM APP_USER WHERE user_id = %s AND is_active = TRUE
           FOR UPDATE""",
        (user_id,),
    )
    actor = cur.fetchone()
    if actor is None:
        logout_user(state)
        raise AuthorizationError("Your account is unavailable. Please log in again.")
    if actor["role"] not in set(allowed_roles):
        raise AuthorizationError("You do not have permission to perform this action.")
    return actor


def require_actor_id_for_read(allowed_roles):
    state = st.session_state
    user_id = _session_user_id(state)
    if user_id is None:
        raise AuthorizationError("Login is required.")
    rows = db.query(
        """SELECT user_id, role FROM APP_USER
           WHERE user_id = %s AND is_active = TRUE""",
        (user_id,),
    )
    if rows.empty:
        logout_user(state)
        raise AuthorizationError("Your account is unavailable. Please log in again.")
    actor = rows.iloc[0].to_dict()
    if actor["role"] not in set(allowed_roles):
        raise AuthorizationError("You do not have permission to perform this action.")
    return int(actor["user_id"])


def require_login():
    actor = get_current_user()
    if actor is None:
        st.error("Please log in to continue.")
        st.stop()
    return actor


def require_role(*allowed_roles):
    actor = require_login()
    if actor["role"] not in set(allowed_roles):
        st.error("You do not have permission to access this page.")
        st.stop()
    return actor
