import json
import re

import auth
import db
import mysql.connector

READ_ROLES = {"STUDENT", "TEACHER", "ADMIN"}
EDITOR_ROLES = {"TEACHER", "ADMIN"}
_EMAIL_PATTERN = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


def _audit(cur, actor_id, action, entity_type, entity_id, old_values=None, new_values=None):
    cur.execute(
        """INSERT INTO AUDIT_LOG
           (actor_user_id, action, entity_type, entity_id, old_values, new_values)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (
            actor_id,
            action,
            entity_type,
            entity_id,
            json.dumps(old_values) if old_values is not None else None,
            json.dumps(new_values) if new_values is not None else None,
        ),
    )


def _normalized_email(value):
    if not isinstance(value, str):
        raise ValueError("Enter a valid researcher email address.")
    email = value.strip().lower()
    if len(email) > 245 or not _EMAIL_PATTERN.fullmatch(email):
        raise ValueError("Enter a valid researcher email address.")
    return email


def _resolve_researcher(cur, entry, actor_id):
    if isinstance(entry, int):
        return int(entry)
    if not isinstance(entry, dict) or not isinstance(entry.get("new"), dict):
        raise ValueError("Researcher selection is invalid.")

    researcher = entry["new"]
    if not isinstance(researcher.get("name"), str):
        raise ValueError("Researcher name must contain 1 to 150 characters.")
    name = (researcher.get("name") or "").strip()
    email = _normalized_email(researcher.get("email"))
    if researcher.get("institution") is not None and not isinstance(
        researcher.get("institution"), str
    ):
        raise ValueError("Institution must be text.")
    institution = (researcher.get("institution") or "").strip() or None
    if not name or len(name) > 150:
        raise ValueError("Researcher name must contain 1 to 150 characters.")
    if institution and len(institution) > 255:
        raise ValueError("Institution must contain at most 255 characters.")

    cur.execute(
        """SELECT r_id FROM RESEARCHER
           WHERE LOWER(TRIM(email)) = %s
           ORDER BY r_id LIMIT 1 FOR UPDATE""",
        (email,),
    )
    existing = cur.fetchone()
    if existing is not None:
        return int(existing["r_id"])

    try:
        cur.execute(
            """INSERT INTO RESEARCHER (r_name, email, institution)
               VALUES (%s, %s, %s)""",
            (name, email, institution),
        )
    except mysql.connector.IntegrityError as exc:
        if exc.errno != 1062:
            raise
        cur.execute(
            """SELECT r_id FROM RESEARCHER
               WHERE LOWER(TRIM(email)) = %s
               ORDER BY r_id LIMIT 1 FOR UPDATE""",
            (email,),
        )
        existing = cur.fetchone()
        if existing is None:
            raise
        return int(existing["r_id"])

    researcher_id = int(cur.lastrowid)
    _audit(
        cur, actor_id, "RESEARCHER_CREATED", "RESEARCHER", researcher_id,
        new_values={"r_name": name, "email": email, "institution": institution},
    )
    return researcher_id


def _resolve_named_entity(cur, entry, actor_id, entity, column, max_length):
    if isinstance(entry, int):
        return int(entry)
    if not isinstance(entry, dict) or not isinstance(entry.get("new"), str):
        raise ValueError(f"{entity.title()} selection is invalid.")

    name = entry["new"].strip()
    if not name or len(name) > max_length:
        raise ValueError(f"{entity.title()} must contain 1 to {max_length} characters.")
    table = "TOPIC" if entity == "topic" else "KEYWORD"
    id_column = "t_id" if entity == "topic" else "key_id"
    cur.execute(
        f"""SELECT {id_column} FROM {table}
            WHERE LOWER(TRIM({column})) = %s
            ORDER BY {id_column} LIMIT 1 FOR UPDATE""",
        (name.lower(),),
    )
    existing = cur.fetchone()
    if existing is not None:
        return int(existing[id_column])

    try:
        cur.execute(f"INSERT INTO {table} ({column}) VALUES (%s)", (name,))
    except mysql.connector.IntegrityError as exc:
        if exc.errno != 1062:
            raise
        cur.execute(
            f"""SELECT {id_column} FROM {table}
                WHERE LOWER(TRIM({column})) = %s
                ORDER BY {id_column} LIMIT 1 FOR UPDATE""",
            (name.lower(),),
        )
        existing = cur.fetchone()
        if existing is None:
            raise
        return int(existing[id_column])

    entity_id = int(cur.lastrowid)
    _audit(
        cur, actor_id, entity.upper() + "_CREATED", entity.upper(), entity_id,
        new_values={column: name},
    )
    return entity_id


def _resolve_entries(cur, entries, resolver, actor_id):
    resolved = []
    seen = set()
    for entry in entries:
        entity_id = resolver(cur, entry, actor_id)
        if entity_id not in seen:
            seen.add(entity_id)
            resolved.append(entity_id)
    return resolved


def submit_paper(title, abstract, pub_year, conference_id, author_ids, topic_ids, keyword_ids):
    title = (title or "").strip()
    if not title or len(title) > 500:
        raise ValueError("Paper title must contain 1 to 500 characters.")
    if not isinstance(pub_year, int) or pub_year < 1 or pub_year > 65535:
        raise ValueError("Publication year must be a positive year.")
    author_ids = list(author_ids)
    topic_ids = list(topic_ids)
    keyword_ids = list(keyword_ids)
    if not author_ids or not topic_ids or not keyword_ids:
        raise ValueError("Select at least one author, topic, and keyword.")

    def create(cur):
        actor = auth.require_actor(cur, EDITOR_ROLES)
        status = "PENDING" if actor["role"] == "TEACHER" else "APPROVED"
        author_ids_resolved = _resolve_entries(
            cur, author_ids, _resolve_researcher, actor["user_id"]
        )
        topic_ids_resolved = _resolve_entries(
            cur, topic_ids,
            lambda cursor, entry, actor_id: _resolve_named_entity(
                cursor, entry, actor_id, "topic", "t_name", 150
            ),
            actor["user_id"],
        )
        keyword_ids_resolved = _resolve_entries(
            cur, keyword_ids,
            lambda cursor, entry, actor_id: _resolve_named_entity(
                cursor, entry, actor_id, "keyword", "keyword", 150
            ),
            actor["user_id"],
        )
        if not author_ids_resolved or not topic_ids_resolved or not keyword_ids_resolved:
            raise ValueError("Select at least one author, topic, and keyword.")
        cur.execute(
            """INSERT INTO PAPER (p_title, abstract, pub_year, c_id)
               VALUES (%s, %s, %s, %s)""",
            (title, (abstract or "").strip() or None, pub_year, conference_id),
        )
        paper_id = cur.lastrowid
        for author_order, researcher_id in enumerate(author_ids_resolved, start=1):
            cur.execute(
                "INSERT INTO AUTHORS (r_id, p_id, author_order) VALUES (%s, %s, %s)",
                (researcher_id, paper_id, author_order),
            )
        for topic_id in topic_ids_resolved:
            cur.execute(
                "INSERT INTO HAS_TOPIC (p_id, t_id) VALUES (%s, %s)",
                (paper_id, topic_id),
            )
        for keyword_id in keyword_ids_resolved:
            cur.execute(
                "INSERT INTO HAS_KEYWORD (p_id, key_id) VALUES (%s, %s)",
                (paper_id, keyword_id),
            )
        cur.execute(
            """INSERT INTO PAPER_OWNERSHIP (p_id, owner_user_id)
               VALUES (%s, %s)""",
            (paper_id, actor["user_id"]),
        )
        cur.execute(
            """INSERT INTO PAPER_WORKFLOW (p_id, status)
               VALUES (%s, %s)""",
            (paper_id, status),
        )
        _audit(
            cur, actor["user_id"], "PAPER_SUBMITTED", "PAPER", paper_id,
            new_values={
                "status": status, "title": title,
                "author_ids": author_ids_resolved,
                "topic_ids": topic_ids_resolved,
                "keyword_ids": keyword_ids_resolved,
            },
        )
        return paper_id, status

    return db.transaction(create)


def list_my_submissions():
    actor_id = auth.require_actor_id_for_read(EDITOR_ROLES)
    return db.query(
        """SELECT p.p_id, p.p_title, p.pub_year,
                  COALESCE(w.status, 'APPROVED') AS status,
                  w.submitted_at,
                  (SELECT r.remarks FROM PUBLICATION_REVIEW r
                   WHERE r.p_id = p.p_id AND r.decision = 'REJECTED'
                   ORDER BY r.reviewed_at DESC, r.review_id DESC LIMIT 1) AS rejection_remarks
           FROM PAPER_OWNERSHIP o
           JOIN PAPER p ON p.p_id = o.p_id
           LEFT JOIN PAPER_WORKFLOW w ON w.p_id = p.p_id
           WHERE o.owner_user_id = %s
             AND EXISTS (SELECT 1 FROM APP_USER actor
                         WHERE actor.user_id = %s AND actor.is_active = TRUE
                           AND actor.role IN ('TEACHER', 'ADMIN'))
           ORDER BY COALESCE(w.submitted_at, o.created_at) DESC""",
        (actor_id, actor_id),
    )


def edit_my_submission(
    paper_id, title, abstract, pub_year, conference_id,
    author_ids=None, topic_ids=None, keyword_ids=None, resubmit=False,
):
    title = (title or "").strip()
    if not title or len(title) > 500:
        raise ValueError("Paper title must contain 1 to 500 characters.")
    if not isinstance(pub_year, int) or pub_year < 1 or pub_year > 65535:
        raise ValueError("Publication year must be a positive year.")
    if author_ids is not None:
        author_ids = list(author_ids)
        if not author_ids:
            raise ValueError("Select at least one author.")
    if topic_ids is not None:
        topic_ids = list(topic_ids)
        if not topic_ids:
            raise ValueError("Select at least one topic.")
    if keyword_ids is not None:
        keyword_ids = list(keyword_ids)
        if not keyword_ids:
            raise ValueError("Select at least one keyword.")

    def update(cur):
        actor = auth.require_actor(cur, {"TEACHER"})
        cur.execute(
            """SELECT COALESCE(w.status, 'APPROVED') AS status, p.p_title, p.abstract,
                      p.pub_year, p.c_id
               FROM PAPER_OWNERSHIP o JOIN PAPER p ON p.p_id = o.p_id
               LEFT JOIN PAPER_WORKFLOW w ON w.p_id = p.p_id
               WHERE o.p_id = %s AND o.owner_user_id = %s FOR UPDATE""",
            (int(paper_id), actor["user_id"]),
        )
        current = cur.fetchone()
        if current is None or current["status"] not in ("PENDING", "REJECTED"):
            raise auth.AuthorizationError("Only your pending or rejected submissions can be edited.")
        cur.execute("SELECT r_id FROM AUTHORS WHERE p_id = %s ORDER BY author_order", (int(paper_id),))
        old_authors = [item["r_id"] for item in cur.fetchall()]
        cur.execute("SELECT t_id FROM HAS_TOPIC WHERE p_id = %s ORDER BY t_id", (int(paper_id),))
        old_topics = [item["t_id"] for item in cur.fetchall()]
        cur.execute(
            "SELECT key_id FROM HAS_KEYWORD WHERE p_id = %s ORDER BY key_id",
            (int(paper_id),),
        )
        old_keywords = [item["key_id"] for item in cur.fetchall()]
        resolved_authors = (
            _resolve_entries(cur, author_ids, _resolve_researcher, actor["user_id"])
            if author_ids is not None else None
        )
        resolved_topics = (
            _resolve_entries(
                cur, topic_ids,
                lambda cursor, entry, actor_id: _resolve_named_entity(
                    cursor, entry, actor_id, "topic", "t_name", 150
                ),
                actor["user_id"],
            )
            if topic_ids is not None else None
        )
        resolved_keywords = (
            _resolve_entries(
                cur, keyword_ids,
                lambda cursor, entry, actor_id: _resolve_named_entity(
                    cursor, entry, actor_id, "keyword", "keyword", 150
                ),
                actor["user_id"],
            )
            if keyword_ids is not None else None
        )
        if resolved_authors is not None and not resolved_authors:
            raise ValueError("Select at least one author.")
        if resolved_topics is not None and not resolved_topics:
            raise ValueError("Select at least one topic.")
        if resolved_keywords is not None and not resolved_keywords:
            raise ValueError("Select at least one keyword.")
        cur.execute(
            """UPDATE PAPER SET p_title = %s, abstract = %s, pub_year = %s, c_id = %s
               WHERE p_id = %s""",
            (title, (abstract or "").strip() or None, pub_year, conference_id, int(paper_id)),
        )
        if resolved_authors is not None:
            cur.execute("DELETE FROM AUTHORS WHERE p_id = %s", (int(paper_id),))
            for author_order, researcher_id in enumerate(resolved_authors, start=1):
                cur.execute(
                    "INSERT INTO AUTHORS (r_id, p_id, author_order) VALUES (%s, %s, %s)",
                    (researcher_id, int(paper_id), author_order),
                )
        if resolved_topics is not None:
            cur.execute("DELETE FROM HAS_TOPIC WHERE p_id = %s", (int(paper_id),))
            for topic_id in resolved_topics:
                cur.execute(
                    "INSERT INTO HAS_TOPIC (p_id, t_id) VALUES (%s, %s)",
                    (int(paper_id), topic_id),
                )
        if resolved_keywords is not None:
            cur.execute("DELETE FROM HAS_KEYWORD WHERE p_id = %s", (int(paper_id),))
            for keyword_id in resolved_keywords:
                cur.execute(
                    "INSERT INTO HAS_KEYWORD (p_id, key_id) VALUES (%s, %s)",
                    (int(paper_id), keyword_id),
                )
        _audit(
            cur, actor["user_id"], "PAPER_UPDATED", "PAPER", int(paper_id),
            old_values={
                **{key: current[key] for key in ("p_title", "abstract", "pub_year", "c_id")},
                "author_ids": old_authors,
                "topic_ids": old_topics,
                "keyword_ids": old_keywords,
            },
            new_values={"p_title": title, "abstract": (abstract or "").strip() or None,
                        "pub_year": pub_year, "c_id": conference_id,
                        "author_ids": resolved_authors, "topic_ids": resolved_topics,
                        "keyword_ids": resolved_keywords},
        )
        if resubmit:
            if current["status"] != "REJECTED":
                raise ValueError("Only rejected submissions can be resubmitted.")
            cur.execute(
                """UPDATE PAPER_WORKFLOW SET status = 'PENDING',
                          submitted_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                   WHERE p_id = %s AND status = 'REJECTED'""",
                (int(paper_id),),
            )
            if cur.rowcount != 1:
                raise ValueError("This submission status changed before it could be resubmitted.")
            _audit(
                cur, actor["user_id"], "PAPER_RESUBMITTED", "PAPER", int(paper_id),
                old_values={"status": "REJECTED"}, new_values={"status": "PENDING"},
            )

    return db.transaction(update)


def resubmit_paper(paper_id):
    def update(cur):
        actor = auth.require_actor(cur, {"TEACHER"})
        cur.execute(
            """SELECT w.status FROM PAPER_OWNERSHIP o
               JOIN PAPER_WORKFLOW w ON w.p_id = o.p_id
               WHERE o.p_id = %s AND o.owner_user_id = %s FOR UPDATE""",
            (int(paper_id), actor["user_id"]),
        )
        current = cur.fetchone()
        if current is None or current["status"] != "REJECTED":
            raise ValueError("Only rejected submissions can be resubmitted.")
        cur.execute(
            """UPDATE PAPER_WORKFLOW SET status = 'PENDING',
                      submitted_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
               WHERE p_id = %s""",
            (int(paper_id),),
        )
        _audit(
            cur, actor["user_id"], "PAPER_RESUBMITTED", "PAPER", int(paper_id),
            old_values={"status": "REJECTED"}, new_values={"status": "PENDING"},
        )

    return db.transaction(update)


def review_paper(paper_id, decision, remarks=""):
    decision = (decision or "").strip().upper()
    remarks = (remarks or "").strip()
    if decision not in ("APPROVED", "REJECTED"):
        raise ValueError("Decision must be APPROVED or REJECTED.")
    if decision == "REJECTED" and not remarks:
        raise ValueError("An explanation is required when rejecting a submission.")

    def review(cur):
        actor = auth.require_actor(cur, {"ADMIN"})
        cur.execute(
            "SELECT status FROM PAPER_WORKFLOW WHERE p_id = %s FOR UPDATE",
            (int(paper_id),),
        )
        current = cur.fetchone()
        if current is None or current["status"] != "PENDING":
            raise ValueError("This publication is no longer pending review.")
        cur.execute(
            """UPDATE PAPER_WORKFLOW SET status = %s, updated_at = CURRENT_TIMESTAMP
               WHERE p_id = %s AND status = 'PENDING'""",
            (decision, int(paper_id)),
        )
        if cur.rowcount != 1:
            raise ValueError("This publication was reviewed by another administrator.")
        cur.execute(
            """INSERT INTO PUBLICATION_REVIEW
               (p_id, reviewer_user_id, decision, remarks)
               VALUES (%s, %s, %s, %s)""",
            (int(paper_id), actor["user_id"], decision, remarks or None),
        )
        _audit(
            cur, actor["user_id"], "PAPER_" + decision, "PAPER", int(paper_id),
            old_values={"status": "PENDING"},
            new_values={"status": decision, "remarks": remarks or None},
        )

    return db.transaction(review)


def list_pending_publications():
    actor_id = auth.require_actor_id_for_read({"ADMIN"})
    return db.query(
        """SELECT p.p_id, p.p_title, p.abstract, p.pub_year, w.submitted_at,
                  u.user_id AS owner_user_id, u.full_name AS owner_name,
                  (SELECT GROUP_CONCAT(r.r_name ORDER BY a.author_order SEPARATOR ', ')
                   FROM AUTHORS a JOIN RESEARCHER r ON r.r_id = a.r_id
                   WHERE a.p_id = p.p_id) AS authors,
                  (SELECT GROUP_CONCAT(t.t_name ORDER BY t.t_name SEPARATOR ', ')
                   FROM HAS_TOPIC ht JOIN TOPIC t ON t.t_id = ht.t_id
                   WHERE ht.p_id = p.p_id) AS topics,
                  (SELECT GROUP_CONCAT(k.keyword ORDER BY k.keyword SEPARATOR ', ')
                   FROM HAS_KEYWORD hk JOIN KEYWORD k ON k.key_id = hk.key_id
                   WHERE hk.p_id = p.p_id) AS keywords
           FROM PAPER_WORKFLOW w
           JOIN PAPER p ON p.p_id = w.p_id
           JOIN PAPER_OWNERSHIP o ON o.p_id = p.p_id
           JOIN APP_USER u ON u.user_id = o.owner_user_id
           WHERE w.status = 'PENDING'
             AND EXISTS (SELECT 1 FROM APP_USER actor
                         WHERE actor.user_id = %s AND actor.is_active = TRUE
                           AND actor.role = 'ADMIN')
           ORDER BY w.submitted_at, p.p_id""",
        (actor_id,),
    )


def admin_list_publications():
    actor_id = auth.require_actor_id_for_read({"ADMIN"})
    return db.query(
        """SELECT p.p_id, p.p_title,
                  COALESCE(w.status, 'APPROVED') AS status
           FROM PAPER p LEFT JOIN PAPER_WORKFLOW w ON w.p_id = p.p_id
           WHERE EXISTS (SELECT 1 FROM APP_USER actor
                         WHERE actor.user_id = %s AND actor.is_active = TRUE
                           AND actor.role = 'ADMIN')
           ORDER BY p.p_id DESC""",
        (actor_id,),
    )


def admin_get_publication(paper_id):
    actor_id = auth.require_actor_id_for_read({"ADMIN"})
    rows = db.query(
        """SELECT p.p_id, p.p_title, p.abstract, p.pub_year, p.c_id,
                  COALESCE(w.status, 'APPROVED') AS status
           FROM PAPER p LEFT JOIN PAPER_WORKFLOW w ON w.p_id = p.p_id
           WHERE p.p_id = %s
             AND EXISTS (SELECT 1 FROM APP_USER actor
                         WHERE actor.user_id = %s AND actor.is_active = TRUE
                           AND actor.role = 'ADMIN')""",
        (int(paper_id), actor_id),
    )
    if rows.empty:
        raise ValueError("Publication not found.")
    return rows.iloc[0].to_dict()


def archive_paper(paper_id):
    def archive(cur):
        actor = auth.require_actor(cur, {"ADMIN"})
        cur.execute("SELECT p_id FROM PAPER WHERE p_id = %s FOR UPDATE", (int(paper_id),))
        if cur.fetchone() is None:
            raise ValueError("Publication not found.")
        cur.execute(
            "SELECT status FROM PAPER_WORKFLOW WHERE p_id = %s FOR UPDATE",
            (int(paper_id),),
        )
        current = cur.fetchone()
        if current is not None and current["status"] != "APPROVED":
            raise ValueError("Only approved publications can be archived.")
        if current is None:
            cur.execute(
                "INSERT INTO PAPER_WORKFLOW (p_id, status) VALUES (%s, 'ARCHIVED')",
                (int(paper_id),),
            )
        else:
            cur.execute(
                """UPDATE PAPER_WORKFLOW SET status = 'ARCHIVED', updated_at = CURRENT_TIMESTAMP
                   WHERE p_id = %s AND status = 'APPROVED'""",
                (int(paper_id),),
            )
            if cur.rowcount != 1:
                raise ValueError("This publication status changed before it could be archived.")
        _audit(
            cur, actor["user_id"], "PAPER_ARCHIVED", "PAPER", int(paper_id),
            old_values={"status": "APPROVED"}, new_values={"status": "ARCHIVED"},
        )

    return db.transaction(archive)


def admin_update_paper(paper_id, title, abstract, pub_year, conference_id):
    title = (title or "").strip()
    if not title or len(title) > 500:
        raise ValueError("Paper title must contain 1 to 500 characters.")
    if not isinstance(pub_year, int) or pub_year < 1 or pub_year > 65535:
        raise ValueError("Publication year must be a positive year.")

    def update(cur):
        actor = auth.require_actor(cur, {"ADMIN"})
        cur.execute(
            """SELECT p.p_title, p.abstract, p.pub_year, p.c_id,
                      COALESCE(w.status, 'APPROVED') AS status
               FROM PAPER p LEFT JOIN PAPER_WORKFLOW w ON w.p_id = p.p_id
               WHERE p.p_id = %s FOR UPDATE""",
            (int(paper_id),),
        )
        current = cur.fetchone()
        if current is None:
            raise ValueError("Publication not found.")
        cur.execute(
            """UPDATE PAPER SET p_title = %s, abstract = %s, pub_year = %s, c_id = %s
               WHERE p_id = %s""",
            (title, (abstract or "").strip() or None, pub_year, conference_id, int(paper_id)),
        )
        _audit(
            cur, actor["user_id"], "PAPER_UPDATED", "PAPER", int(paper_id),
            old_values={key: current[key] for key in ("p_title", "abstract", "pub_year", "c_id")},
            new_values={"p_title": title, "abstract": (abstract or "").strip() or None,
                        "pub_year": pub_year, "c_id": conference_id},
        )

    return db.transaction(update)


def add_citation(citing_paper_id, cited_paper_id):
    citing_paper_id = int(citing_paper_id)
    cited_paper_id = int(cited_paper_id)
    if citing_paper_id == cited_paper_id:
        raise ValueError("A paper cannot cite itself.")

    def insert(cur):
        actor = auth.require_actor(cur, EDITOR_ROLES)
        if actor["role"] == "TEACHER":
            cur.execute(
                """SELECT 1 FROM PAPER_OWNERSHIP o
                   JOIN PAPER_WORKFLOW w ON w.p_id = o.p_id
                   WHERE o.p_id = %s AND o.owner_user_id = %s
                     AND w.status = 'APPROVED' FOR UPDATE""",
                (citing_paper_id, actor["user_id"]),
            )
            if cur.fetchone() is None:
                raise auth.AuthorizationError("You may cite only from your own approved papers.")
        cur.execute(
            """SELECT COUNT(*) AS approved_count FROM PAPER p
               LEFT JOIN PAPER_WORKFLOW w ON w.p_id = p.p_id
               WHERE p.p_id = %s AND COALESCE(w.status, 'APPROVED') = 'APPROVED'""",
            (cited_paper_id,),
        )
        if int(cur.fetchone()["approved_count"]) != 1:
            raise ValueError("The cited publication is unavailable.")
        cur.execute(
            "INSERT INTO CITES (citing_p_id, cited_p_id) VALUES (%s, %s)",
            (citing_paper_id, cited_paper_id),
        )
        _audit(
            cur, actor["user_id"], "CITATION_CREATED", "CITES", citing_paper_id,
            new_values={"cited_paper_id": cited_paper_id},
        )

    return db.transaction(insert)


def admin_update_user(user_id, role, is_active):
    role = (role or "").strip().upper()
    if role not in ("STUDENT", "TEACHER", "ADMIN"):
        raise ValueError("Select a valid role.")
    auth.require_actor_id_for_read({"ADMIN"})

    def update(cur):
        cur.execute("SELECT user_id FROM APP_USER FOR UPDATE")
        cur.fetchall()
        actor = auth.require_actor(cur, {"ADMIN"})
        cur.execute(
            "SELECT role, is_active FROM APP_USER WHERE user_id = %s FOR UPDATE",
            (int(user_id),),
        )
        old = cur.fetchone()
        if old is None:
            raise ValueError("User account not found.")
        if int(user_id) == int(actor["user_id"]) and (role != "ADMIN" or not is_active):
            raise ValueError("You cannot deactivate or demote your own administrator account.")
        if old["role"] == "ADMIN" and (role != "ADMIN" or not is_active):
            cur.execute(
                """SELECT COUNT(*) AS active_admins FROM APP_USER
                   WHERE role = 'ADMIN' AND is_active = TRUE AND user_id <> %s""",
                (int(user_id),),
            )
            if int(cur.fetchone()["active_admins"]) == 0:
                raise ValueError("At least one active administrator must remain.")
        cur.execute(
            "UPDATE APP_USER SET role = %s, is_active = %s WHERE user_id = %s",
            (role, bool(is_active), int(user_id)),
        )
        if old["role"] != role:
            _audit(
                cur, actor["user_id"], "USER_ROLE_CHANGED", "APP_USER", int(user_id),
                old_values={"role": old["role"]}, new_values={"role": role},
            )
        if bool(old["is_active"]) != bool(is_active):
            action = "USER_ACTIVATED" if is_active else "USER_DEACTIVATED"
            _audit(
                cur, actor["user_id"], action, "APP_USER", int(user_id),
                old_values={"is_active": bool(old["is_active"])},
                new_values={"is_active": bool(is_active)},
            )

    return db.transaction(update)


def list_users():
    actor_id = auth.require_actor_id_for_read({"ADMIN"})
    return db.query(
        """SELECT user_id, full_name, email, role, is_active, researcher_id,
                  created_at, updated_at
           FROM APP_USER
           WHERE EXISTS (SELECT 1 FROM APP_USER actor
                         WHERE actor.user_id = %s AND actor.is_active = TRUE
                           AND actor.role = 'ADMIN')
           ORDER BY created_at DESC, user_id DESC""",
        (actor_id,),
    )


def list_audit_logs(action=None, actor_id=None, start_date=None, end_date=None):
    session_actor_id = auth.require_actor_id_for_read({"ADMIN"})
    clauses = [
        """EXISTS (SELECT 1 FROM APP_USER actor
                   WHERE actor.user_id = %s AND actor.is_active = TRUE
                     AND actor.role = 'ADMIN')"""
    ]
    params = [session_actor_id]
    if action:
        clauses.append("a.action = %s")
        params.append(action)
    if actor_id:
        clauses.append("a.actor_user_id = %s")
        params.append(int(actor_id))
    if start_date:
        clauses.append("a.created_at >= %s")
        params.append(start_date)
    if end_date:
        clauses.append("a.created_at < DATE_ADD(%s, INTERVAL 1 DAY)")
        params.append(end_date)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    return db.query(
        """SELECT a.audit_id, a.actor_user_id, u.full_name AS actor_name,
                  a.action, a.entity_type, a.entity_id, a.old_values,
                  a.new_values, a.created_at
           FROM AUDIT_LOG a LEFT JOIN APP_USER u ON u.user_id = a.actor_user_id"""
        + where + " ORDER BY a.created_at DESC, a.audit_id DESC LIMIT 500",
        tuple(params),
    )


def list_projects():
    return db.query(
        """SELECT p.project_id, p.name, p.description,
                  u.user_id AS owner_user_id, u.full_name AS owner_name,
                  (SELECT COUNT(*) FROM WORKS_ON wo
                   WHERE wo.project_id = p.project_id) AS researcher_count,
                  (SELECT COUNT(*) FROM USES us
                   WHERE us.project_id = p.project_id) AS dataset_count
           FROM PROJECT p
           LEFT JOIN PROJECT_OWNERSHIP o ON o.project_id = p.project_id
           LEFT JOIN APP_USER u ON u.user_id = o.owner_user_id
           ORDER BY p.name, p.project_id"""
    )


def get_project(project_id):
    rows = db.query(
        """SELECT p.project_id, p.name, p.description,
                  u.user_id AS owner_user_id, u.full_name AS owner_name,
                  (SELECT COUNT(*) FROM WORKS_ON wo
                   WHERE wo.project_id = p.project_id) AS researcher_count,
                  (SELECT COUNT(*) FROM USES us
                   WHERE us.project_id = p.project_id) AS dataset_count
           FROM PROJECT p
           LEFT JOIN PROJECT_OWNERSHIP o ON o.project_id = p.project_id
           LEFT JOIN APP_USER u ON u.user_id = o.owner_user_id
           WHERE p.project_id = %s""",
        (int(project_id),),
    )
    return None if rows.empty else rows.iloc[0].to_dict()


def list_project_team(project_id):
    return db.query(
        """SELECT r.r_id, r.r_name, r.institution
           FROM WORKS_ON wo JOIN RESEARCHER r ON r.r_id = wo.r_id
           WHERE wo.project_id = %s ORDER BY r.r_name, r.r_id""",
        (int(project_id),),
    )


def list_project_datasets(project_id):
    return db.query(
        """SELECT d.dataset_id, d.name AS dataset_name, d.source
           FROM USES us JOIN DATASET d ON d.dataset_id = us.dataset_id
           WHERE us.project_id = %s ORDER BY d.name, d.dataset_id""",
        (int(project_id),),
    )


def list_shared_project_pairs():
    return db.query(
        """SELECT p1_id, p1_name, p2_id, p2_name,
                  shared_researcher_count, shared_dataset_count
           FROM v_projects_shared ORDER BY p1_name, p2_name"""
    )


def list_shared_researchers(project1_id, project2_id):
    return db.query(
        """SELECT r.r_id, r.r_name, r.institution
           FROM WORKS_ON a
           JOIN WORKS_ON b ON b.r_id = a.r_id
           JOIN RESEARCHER r ON r.r_id = a.r_id
           WHERE a.project_id = %s AND b.project_id = %s
           ORDER BY r.r_name, r.r_id""",
        (int(project1_id), int(project2_id)),
    )


def list_shared_datasets(project1_id, project2_id):
    return db.query(
        """SELECT d.dataset_id, d.name AS dataset_name, d.source
           FROM USES a
           JOIN USES b ON b.dataset_id = a.dataset_id
           JOIN DATASET d ON d.dataset_id = a.dataset_id
           WHERE a.project_id = %s AND b.project_id = %s
           ORDER BY d.name, d.dataset_id""",
        (int(project1_id), int(project2_id)),
    )


def list_manageable_projects():
    actor_id = auth.require_actor_id_for_read(EDITOR_ROLES)
    actor = auth.get_current_user()
    if actor["role"] == "ADMIN":
        return list_projects()
    return db.query(
        """SELECT p.project_id, p.name, p.description,
                  u.user_id AS owner_user_id, u.full_name AS owner_name,
                  (SELECT COUNT(*) FROM WORKS_ON wo
                   WHERE wo.project_id = p.project_id) AS researcher_count,
                  (SELECT COUNT(*) FROM USES us
                   WHERE us.project_id = p.project_id) AS dataset_count
           FROM PROJECT p JOIN PROJECT_OWNERSHIP o ON o.project_id = p.project_id
           LEFT JOIN APP_USER u ON u.user_id = o.owner_user_id
           WHERE o.owner_user_id = %s ORDER BY p.name, p.project_id""",
        (actor_id,),
    )


def create_project(name, description):
    name = (name or "").strip()
    if not name or len(name) > 255:
        raise ValueError("Project name must contain 1 to 255 characters.")

    def create(cur):
        actor = auth.require_actor(cur, EDITOR_ROLES)
        cur.execute(
            """SELECT project_id FROM PROJECT
               WHERE LOWER(TRIM(name)) = %s LIMIT 1 FOR UPDATE""",
            (name.lower(),),
        )
        if cur.fetchone() is not None:
            raise ValueError("A project with this name already exists.")
        cur.execute(
            "INSERT INTO PROJECT (name, description) VALUES (%s, %s)",
            (name, (description or "").strip() or None),
        )
        project_id = cur.lastrowid
        cur.execute(
            "INSERT INTO PROJECT_OWNERSHIP (project_id, owner_user_id) VALUES (%s, %s)",
            (project_id, actor["user_id"]),
        )
        _audit(
            cur, actor["user_id"], "PROJECT_CREATED", "PROJECT", project_id,
            new_values={"name": name, "description": (description or "").strip() or None},
        )
        return project_id

    return db.transaction(create)


def update_project(project_id, name, description):
    name = (name or "").strip()
    description = (description or "").strip() or None
    if not name or len(name) > 255:
        raise ValueError("Project name must contain 1 to 255 characters.")

    def update(cur):
        actor = auth.require_actor(cur, EDITOR_ROLES)
        _assert_project_access(cur, actor, project_id)
        cur.execute(
            "SELECT name, description FROM PROJECT WHERE project_id = %s FOR UPDATE",
            (int(project_id),),
        )
        current = cur.fetchone()
        if current is None:
            raise ValueError("Project not found.")
        cur.execute(
            """SELECT project_id FROM PROJECT
               WHERE LOWER(TRIM(name)) = %s AND project_id <> %s
               LIMIT 1 FOR UPDATE""",
            (name.lower(), int(project_id)),
        )
        if cur.fetchone() is not None:
            raise ValueError("Another project already uses this name.")
        changed = {}
        old_values = {}
        if current["name"] != name:
            old_values["name"] = current["name"]
            changed["name"] = name
        if current["description"] != description:
            old_values["description"] = current["description"]
            changed["description"] = description
        if not changed:
            return
        cur.execute(
            "UPDATE PROJECT SET name = %s, description = %s WHERE project_id = %s",
            (name, description, int(project_id)),
        )
        _audit(
            cur, actor["user_id"], "PROJECT_UPDATED", "PROJECT", int(project_id),
            old_values=old_values,
            new_values=changed,
        )

    return db.transaction(update)


def _assert_project_access(cur, actor, project_id):
    cur.execute(
        "SELECT project_id FROM PROJECT WHERE project_id = %s FOR UPDATE",
        (int(project_id),),
    )
    if cur.fetchone() is None:
        raise ValueError("Project not found.")
    if actor["role"] == "ADMIN":
        return
    cur.execute(
        """SELECT 1 FROM PROJECT_OWNERSHIP
           WHERE project_id = %s AND owner_user_id = %s FOR UPDATE""",
        (int(project_id), actor["user_id"]),
    )
    if cur.fetchone() is None:
        raise auth.AuthorizationError("You can manage only projects you own.")


def assign_researcher(project_id, researcher_id):
    def assign(cur):
        actor = auth.require_actor(cur, EDITOR_ROLES)
        _assert_project_access(cur, actor, project_id)
        _link_researcher(cur, actor, project_id, researcher_id)
    return db.transaction(assign)


def _link_researcher(cur, actor, project_id, researcher_id):
    researcher_id = int(researcher_id)
    cur.execute(
        "SELECT r_id FROM RESEARCHER WHERE r_id = %s FOR UPDATE",
        (researcher_id,),
    )
    if cur.fetchone() is None:
        raise ValueError("Researcher not found.")
    cur.execute(
        "SELECT 1 FROM WORKS_ON WHERE project_id = %s AND r_id = %s",
        (int(project_id), researcher_id),
    )
    if cur.fetchone() is not None:
        raise ValueError("This researcher is already assigned to the project.")
    try:
        cur.execute(
            "INSERT INTO WORKS_ON (project_id, r_id) VALUES (%s, %s)",
            (int(project_id), researcher_id),
        )
    except mysql.connector.IntegrityError as exc:
        if exc.errno == 1062:
            raise ValueError("This researcher is already assigned to the project.") from exc
        raise
    _audit(
        cur, actor["user_id"], "PROJECT_RESEARCHER_ADDED", "PROJECT",
        int(project_id), new_values={"researcher_id": researcher_id},
    )


def add_researcher_to_project(project_id, name, email, institution=None):
    entry = {"new": {"name": name, "email": email, "institution": institution}}

    def add(cur):
        actor = auth.require_actor(cur, EDITOR_ROLES)
        _assert_project_access(cur, actor, project_id)
        researcher_id = _resolve_researcher(cur, entry, actor["user_id"])
        _link_researcher(cur, actor, project_id, researcher_id)
        return researcher_id

    return db.transaction(add)


def remove_researcher_from_project(project_id, researcher_id):
    def remove(cur):
        actor = auth.require_actor(cur, EDITOR_ROLES)
        _assert_project_access(cur, actor, project_id)
        cur.execute(
            "DELETE FROM WORKS_ON WHERE project_id = %s AND r_id = %s",
            (int(project_id), int(researcher_id)),
        )
        if cur.rowcount != 1:
            raise ValueError("Researcher is not assigned to this project.")
        _audit(
            cur, actor["user_id"], "PROJECT_RESEARCHER_REMOVED", "PROJECT",
            int(project_id), old_values={"researcher_id": int(researcher_id)},
        )

    return db.transaction(remove)


def link_dataset(project_id, dataset_id):
    def link(cur):
        actor = auth.require_actor(cur, EDITOR_ROLES)
        _assert_project_access(cur, actor, project_id)
        _link_dataset(cur, actor, project_id, dataset_id)
    return db.transaction(link)


def _link_dataset(cur, actor, project_id, dataset_id):
    dataset_id = int(dataset_id)
    cur.execute(
        "SELECT dataset_id FROM DATASET WHERE dataset_id = %s FOR UPDATE",
        (dataset_id,),
    )
    if cur.fetchone() is None:
        raise ValueError("Dataset not found.")
    cur.execute(
        "SELECT 1 FROM USES WHERE project_id = %s AND dataset_id = %s",
        (int(project_id), dataset_id),
    )
    if cur.fetchone() is not None:
        raise ValueError("This dataset is already linked to the project.")
    try:
        cur.execute(
            "INSERT INTO USES (project_id, dataset_id) VALUES (%s, %s)",
            (int(project_id), dataset_id),
        )
    except mysql.connector.IntegrityError as exc:
        if exc.errno == 1062:
            raise ValueError("This dataset is already linked to the project.") from exc
        raise
    _audit(
        cur, actor["user_id"], "PROJECT_DATASET_LINKED", "PROJECT",
        int(project_id), new_values={"dataset_id": dataset_id},
    )


def add_dataset_to_project(project_id, name, source):
    name = (name or "").strip()
    source = (source or "").strip()
    if not name or len(name) > 255:
        raise ValueError("Dataset name must contain 1 to 255 characters.")
    if not source or len(source) > 1000:
        raise ValueError("Dataset source must contain 1 to 1000 characters.")

    def add(cur):
        actor = auth.require_actor(cur, EDITOR_ROLES)
        _assert_project_access(cur, actor, project_id)
        cur.execute(
            """SELECT dataset_id FROM DATASET
               WHERE LOWER(TRIM(name)) = %s AND LOWER(TRIM(source)) = %s
               ORDER BY dataset_id LIMIT 1 FOR UPDATE""",
            (name.lower(), source.lower()),
        )
        existing = cur.fetchone()
        if existing is None:
            cur.execute(
                "INSERT INTO DATASET (name, source) VALUES (%s, %s)",
                (name, source),
            )
            dataset_id = int(cur.lastrowid)
            created = True
            _audit(
                cur, actor["user_id"], "DATASET_CREATED", "DATASET", dataset_id,
                new_values={"name": name, "source": source},
            )
        else:
            dataset_id = int(existing["dataset_id"])
            created = False
        _link_dataset(cur, actor, project_id, dataset_id)
        return dataset_id, created

    return db.transaction(add)


def unlink_dataset_from_project(project_id, dataset_id):
    def unlink(cur):
        actor = auth.require_actor(cur, EDITOR_ROLES)
        _assert_project_access(cur, actor, project_id)
        cur.execute(
            "DELETE FROM USES WHERE project_id = %s AND dataset_id = %s",
            (int(project_id), int(dataset_id)),
        )
        if cur.rowcount != 1:
            raise ValueError("Dataset is not linked to this project.")
        _audit(
            cur, actor["user_id"], "PROJECT_DATASET_UNLINKED", "PROJECT",
            int(project_id), old_values={"dataset_id": int(dataset_id)},
        )

    return db.transaction(unlink)


def admin_create_entity(entity, values):
    specifications = {
        "RESEARCHER": ("r_name", "email", "institution"),
        "CONFERENCE": ("c_name", "c_year", "c_location"),
        "TOPIC": ("t_name",),
        "KEYWORD": ("keyword",),
        "DATASET": ("name", "source"),
    }
    if entity not in specifications:
        raise ValueError("Entity type is not supported.")
    if entity == "RESEARCHER":
        values = dict(values)
        if not isinstance(values.get("r_name"), str) or not values["r_name"].strip():
            raise ValueError("Researcher name is required.")
        values["r_name"] = values["r_name"].strip()
        if len(values["r_name"]) > 150:
            raise ValueError("Researcher name must contain at most 150 characters.")
        values["email"] = _normalized_email(values.get("email"))
        institution = values.get("institution")
        if institution is not None and not isinstance(institution, str):
            raise ValueError("Institution must be text.")
        values["institution"] = (institution or "").strip() or None
        if values["institution"] and len(values["institution"]) > 255:
            raise ValueError("Institution must contain at most 255 characters.")
    columns = tuple(column for column in specifications[entity] if column in values)
    if not columns or any(column not in specifications[entity] for column in values):
        raise ValueError("Entity fields are invalid.")
    placeholders = ", ".join(["%s"] * len(columns))

    def insert(cur):
        actor = auth.require_actor(cur, {"ADMIN"})
        if entity == "RESEARCHER":
            cur.execute(
                """SELECT r_id FROM RESEARCHER
                   WHERE LOWER(TRIM(email)) = %s LIMIT 1 FOR UPDATE""",
                (values["email"],),
            )
            if cur.fetchone() is not None:
                raise ValueError("A researcher with this email address already exists.")
        cur.execute(
            f"INSERT INTO {entity} ({', '.join(columns)}) VALUES ({placeholders})",
            tuple(values[column] for column in columns),
        )
        entity_id = cur.lastrowid
        _audit(
            cur, actor["user_id"], entity + "_CREATED", entity, entity_id,
            new_values={column: values[column] for column in columns},
        )
        return entity_id

    return db.transaction(insert)
