# Authentication and Publication Approval

## Local setup

1. Use Python 3.11 or newer and MySQL 8.
2. Create and activate `.venv`, install `requirements.txt`, and copy `.env.example` to `.env` if no local `.env` exists.
3. Configure `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, and `DB_NAME` in `.env`.
4. For a database that already contains the Research Collaboration Network, back it up and apply the additive migrations in order:

   ```powershell
   mysql -u root -p -e "SOURCE sql/60_auth_rbac.sql"
   mysql -u root -p -e "SOURCE sql/61_visibility_views.sql"
   mysql -u root -p -e "SOURCE sql/62_researcher_email_unique.sql"
   ```

   Before the last migration, check `RESEARCHER` for normalized duplicate emails using the query in `sql/62_researcher_email_unique.sql`; resolve any matches manually. The migration adds only a unique functional index. Do not rerun `sql/schema.sql` or `sql/seed.sql` when upgrading an existing database. Existing papers without a workflow row are treated as approved and retain their existing visibility.
5. Create the first administrator using an interactive terminal:

   ```powershell
   python -m app.bootstrap_admin
   ```

   The command prompts for a name, email, and hidden password. It creates no predictable demo credentials and refuses a second bootstrap once an administrator exists.
6. Start the portal:

   ```powershell
   python -m streamlit run app/Home.py
   ```

## Permissions

| Capability | Student | Teacher | Admin |
|---|---:|---:|---:|
| Browse approved research, search, citations, analytics, projects | Yes | Yes | Yes |
| Register a public account | Yes | Yes | Yes |
| Submit papers | No | Yes | Yes |
| Edit/resubmit own pending or rejected submissions | No | Yes | No |
| Manage projects they own | No | Yes | Yes |
| Register and assign researchers/datasets within a manageable project | No | Yes | Yes |
| Add citations from an eligible owned paper | No | Yes | Yes |
| Add researchers, topics, and keywords during paper submission | No | Yes | Yes |
| Manage core research entities outside submissions | No | No | Yes |
| Approve/reject/archive or edit publications | No | No | Yes |
| Assign roles and activate/deactivate accounts | No | No | Yes |
| View audit logs | No | No | Yes |

Page navigation is role-aware, and protected writes independently recheck the active account and role in the database. Teacher paper writes also check ownership and lifecycle status inside a transaction.

## Publication lifecycle

```text
New teacher paper -> PENDING -> APPROVED
                            \-> REJECTED -> PENDING (teacher resubmits)
APPROVED -> ARCHIVED (administrator)
```

Administrators must provide remarks when rejecting. Reviews and audit events are committed atomically with the decision. A row lock and status revalidation prevent conflicting concurrent decisions. Legacy publications have no workflow row and are treated as APPROVED until explicitly archived.

The public SQL views and procedures (`v_collaborators`, paper similarity/analytics, `sp_search`, and `sp_citations`) filter out pending, rejected, and archived publications. Teachers can inspect their own non-approved work only in **My Submissions**; administrators use **Publication Review**.

## Demonstration

1. Register a student and log in; verify approved search works and Add Paper is unavailable.
2. As administrator, use **User Management** to promote the student account to TEACHER.
3. Log in as that teacher, submit a paper, and confirm it appears as PENDING under **My Submissions**, but not in public search or analytics.
4. In **Add Paper**, combine existing and new researchers, topics, and keywords. Add new entries, reorder authors, and verify none are persisted until the paper is submitted. The app resolves case-insensitive matches to existing records without overwriting their details.
5. As administrator, reject a submission with a reason; as the teacher, edit its paper details and associations (including adding new reference entries), then resubmit.
6. Approve the resubmitted paper as administrator. Confirm it appears in student search and analytics and the review is recorded in **Audit Logs**.
7. Archive an approved paper and confirm it is no longer returned by public discovery.

Run the Python unit tests with `python -m unittest discover -s tests -v`. They use mocked connections and do not modify a database. For MySQL integration validation, use a separate test database and execute the existing SQL verification suite there.
