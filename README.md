# Research Collaboration Network

An academic research collaboration and discovery portal built with **MySQL 8**, **Python 3.11+**, **Streamlit**, and **pandas**. It includes student, teacher, and administrator accounts with a teacher-submission and administrator-approval workflow.

Core analytics run in MySQL through views and stored procedures, keeping the Streamlit frontend focused on presentation and interaction.

## Features

- **Live database overview** with entity and relationship-table counts
- **Publication analytics** by year, conference, and research topic
- **Unified search** across papers, researchers, conferences, projects, and datasets
- **Collaborator Discovery** with researcher-focused recommendations and an interactive collaboration network
- **Publication similarity** with paper comparison, overlap explanations, and weighted Jaccard scores:
  - 40% topic similarity
  - 60% keyword similarity
- **Citation traversal** in forward and reverse directions using a cycle-safe recursive CTE
- **Project analytics** for project teams, datasets, and shared resources
- **Project exploration and management** with owner-scoped team/dataset updates and detailed shared-resource collaboration
- **Validated data-entry forms** for core entities, papers, citations, project assignments, and dataset links
- **Dynamic paper submission** that combines existing and new researchers, topics, and keywords without leaving Add Paper
- **Atomic paper registration** that rolls back all related inserts if one step fails
- **Argon2id password hashing**, database-backed login, expiring sessions, and role-based navigation
- **Teacher-owned submissions** with edit/resubmit controls and administrator review history
- **Approved-only publication discovery** across search, citations, collaboration, similarity, and public analytics
- **Audit logging** for account, publication, project, and review changes

Similarity and overlap values represent **potential topical overlap**, not plagiarism or duplicate detection.

## Project Explorer and Management

The Projects page separates read-only **Explore Projects**, role-gated **Manage Projects**, and **Cross-Project Collaboration**. All signed-in users can browse project descriptions, team members, datasets, and SQL-derived resource-sharing details. Teachers can manage only their owned projects; administrators can manage every project, including legacy projects without an owner record.

Project managers can update details, assign or register researchers, link or register datasets, and remove only the relevant project relationships. Resource creation, association changes, ownership checks, and audit events are handled by transactional workflow services. No additional schema migration is required for these project page enhancements.

## Technology Stack

| Component | Technology |
|---|---|
| Database | MySQL 8.0 / 8.0.41 |
| Application | Streamlit |
| Backend language | Python 3.11 |
| MySQL driver | `mysql-connector-python` |
| Data handling | pandas |
| Password hashing | Argon2id (`argon2-cffi`) |

## Database Model

The research network retains its original 13 tables:

### Core entities

- `RESEARCHER`
- `CONFERENCE`
- `PAPER`
- `TOPIC`
- `KEYWORD`
- `PROJECT`
- `DATASET`

### Relationship tables

- `AUTHORS`
- `CITES`
- `HAS_TOPIC`
- `HAS_KEYWORD`
- `WORKS_ON`
- `USES`

The schema enforces primary keys, foreign keys, unique constraints, cascade actions, and positive-value checks. Before-insert and before-update triggers prevent a paper from citing itself. See [ER_and_Schema_Design.md](docs/ER_and_Schema_Design.md) for the complete relationship model.

Additive migrations add `APP_USER`, `PAPER_OWNERSHIP`, `PROJECT_OWNERSHIP`, `PAPER_WORKFLOW`, `PUBLICATION_REVIEW`, and `AUDIT_LOG`. A paper with no `PAPER_WORKFLOW` row is a legacy publication and remains approved.

## Project Structure

```text
app/
  Home.py                 # Role-aware navigation entry point
  auth.py                 # Authentication and role checks
  db.py                   # MySQL connection and query helpers
  workflow.py             # Authorized transactional write services
  bootstrap_admin.py      # One-time administrator bootstrap
  pages/                  # Streamlit feature pages
sql/
  00_verify.sql           # Database verification
  10_collab.sql           # Collaboration view
  20_sim_parts.sql        # Topic and keyword similarity views
  21_sim_final.sql        # Weighted publication similarity view
  30_citations.sql        # Citation traversal stored procedure
  40_search.sql           # Unified search stored procedure
  50_projects_analytics.sql
  60_auth_rbac.sql        # Additive authentication/workflow tables
  61_visibility_views.sql # Approved-only discovery SQL
  62_researcher_email_unique.sql # Concurrent-safe normalized researcher emails
  schema.sql
  seed.sql
basicSQL/                 # Alternative introductory SQL walkthrough
docs/                     # Report, schema, demo, and limitations documentation
tests/test_log.md         # Executed verification test matrix
requirements.txt
run_sql.py
```

## Prerequisites

- Python 3.11 or newer
- MySQL 8.0 or newer
- A local MySQL account with privileges to create and populate `research_collaboration_db`

## Installation

1. Clone the repository and enter the project directory:

   ```powershell
   git clone https://github.com/CharanGowda-006/DBMS.git
   cd DBMS
   ```

2. Create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. Create the local environment file if it does not already exist:

   ```powershell
   Copy-Item .env.example .env
   ```

5. Set the MySQL credentials in `.env`:

   ```dotenv
   DB_HOST=localhost
   DB_PORT=3306
   DB_USER=root
   DB_PASSWORD=your_password
   DB_NAME=research_collaboration_db
   ```

   `.env` is local configuration and should not contain credentials that are committed to version control.

## Database Setup

For a **new database**, run the canonical scripts in the following order. Use MySQL Workbench or the MySQL command-line client.

| Order | Script | Creates |
|---:|---|---|
| 1 | `sql/schema.sql` | Database tables, keys, indexes, and triggers |
| 2 | `sql/seed.sql` | Initial sample records |
| 3 | `sql/00_verify.sql` | Verification checks |
| 4 | `sql/10_collab.sql` | `v_collaborators` |
| 5 | `sql/20_sim_parts.sql` | Topic and keyword similarity views |
| 6 | `sql/21_sim_final.sql` | `v_paper_similarity` |
| 7 | `sql/30_citations.sql` | `sp_citations` |
| 8 | `sql/40_search.sql` | `sp_search` |
| 9 | `sql/50_projects_analytics.sql` | Project and publication analytics views |
| 10 | `sql/60_auth_rbac.sql` | Additive accounts, ownership, reviews, and audit tables |
| 11 | `sql/61_visibility_views.sql` | Approved-only views and procedures |
| 12 | `sql/62_researcher_email_unique.sql` | Case-insensitive normalized researcher email uniqueness |

The root-level `schema.sql` and `seed.sql` are copies of the canonical files under `sql/`. Prefer the `sql/` scripts documented above.

Do not apply both the `sql/` pipeline and `basicSQL/` scripts to the same database because they create the same logical objects.

### MySQL command-line alternative

```powershell
mysql -u root -p -e "SOURCE sql/schema.sql"
mysql -u root -p -e "SOURCE sql/seed.sql"
mysql -u root -p -e "SOURCE sql/10_collab.sql"
mysql -u root -p -e "SOURCE sql/20_sim_parts.sql"
mysql -u root -p -e "SOURCE sql/21_sim_final.sql"
mysql -u root -p -e "SOURCE sql/30_citations.sql"
mysql -u root -p -e "SOURCE sql/40_search.sql"
mysql -u root -p -e "SOURCE sql/50_projects_analytics.sql"
mysql -u root -p -e "SOURCE sql/60_auth_rbac.sql"
mysql -u root -p -e "SOURCE sql/61_visibility_views.sql"
mysql -u root -p -e "SOURCE sql/62_researcher_email_unique.sql"
```

Run `sql/00_verify.sql` in MySQL Workbench or MySQL CLI after setup.

### Upgrade an existing database

Back up the database first. For an existing installation, **do not rerun `schema.sql` or `seed.sql`**. Apply the additive migrations in order; the legacy papers and the original 13 tables are preserved. Before the final migration, check for normalized duplicate researcher emails and resolve any matches manually:

```powershell
mysql -u root -p -e "SOURCE sql/60_auth_rbac.sql"
mysql -u root -p -e "SOURCE sql/61_visibility_views.sql"
mysql -u root -p -e "SOURCE sql/62_researcher_email_unique.sql"
```

The first migration uses `CREATE TABLE IF NOT EXISTS`, the second replaces public discovery views and procedures, and the third adds a unique normalized-email index. These migrations do not delete publication records.

After migrations and `.env` configuration, create the first administrator from an interactive PowerShell terminal. Password input is hidden and no default account or password is seeded:

```powershell
python -m app.bootstrap_admin
```

Bootstrap is guarded by a MySQL named lock and refuses to create another administrator once one exists. Afterward, use **User Management** to promote student accounts to teachers.

## Run the Dashboard

From the repository root:

```powershell
python -m streamlit run app/Home.py
```

Streamlit normally opens the application at `http://localhost:8501`.

### Application pages

1. **Overview**: KPIs and analytics charts
2. **Search**: cross-entity search and detailed paper inspection
3. **Insights**: potential collaborators and publication similarity
4. **Citations**: interactive, approved-only forward and reverse citation graph with traversal analytics and paper details
5. **Projects**: project teams, datasets, and shared resources
6. **Add Basic**: register core entities
7. **Add Paper**: teacher submissions and eligible citation management
8. **My Submissions**: edit pending/rejected papers and resubmit
9. **Administration**: review/archive publications, manage accounts, and inspect audit logs (admins only)

Public registration creates **STUDENT** accounts only. Administrators assign teacher roles through User Management. Teachers' papers are pending until an administrator approves them; rejected papers require remarks and can be edited and resubmitted. Existing legacy papers without workflow rows remain approved.

See [Auth and Approval Guide](docs/Auth_and_Approval_Guide.md) for the permission matrix and complete demonstration flow.

## SQL Features

### Views

- `v_collaborators`
- `v_paper_topic_sim`
- `v_paper_keyword_sim`
- `v_paper_similarity`
- `v_project_team`
- `v_project_datasets`
- `v_projects_shared`
- `v_papers_per_conference`
- `v_papers_per_year`
- `v_papers_per_topic`

### Stored procedures

- `sp_citations(start_p_id, direction, max_depth)`
- `sp_search(term)`

Example queries:

```sql
SELECT * FROM v_paper_similarity LIMIT 20;
CALL sp_search('Computer Vision');
CALL sp_citations(6, 'forward', 5);
CALL sp_citations(1, 'reverse', 5);
```

## Seed Dataset

The canonical seed contains 99 rows across the 13 tables. It includes:

- 5 researchers
- 3 conferences
- 6 papers
- 6 topics
- 8 keywords
- 3 projects
- 4 datasets
- 10 authorships
- 5 citations
- 16 topic associations
- 21 keyword associations
- 8 project assignments
- 4 project-dataset links

## Verification

Run the unit tests and inspect [tests/test_log.md](tests/test_log.md):

```powershell
python -m unittest discover -s tests -v
```

The original database verification matrix covers table counts, search, similarity, citations, constraints, and self-citation prevention. Workflow unit tests use mocked database connections; run the SQL verification scripts against a separately configured test database for MySQL-specific integration checks.

Self-citation rejection should return SQLSTATE `45000` with:

```text
A paper cannot cite itself
```

## Helper Script

`run_sql.py` requires a `.env` file and is a lightweight script runner:

```powershell
python run_sql.py sql/00_verify.sql
```

It splits scripts on semicolons and is not suitable for procedures or triggers that contain `DELIMITER` blocks. Use MySQL Workbench or the MySQL CLI for `sql/schema.sql` and other routine SQL with stored procedure bodies.

## Documentation

- [ER and Schema Design](docs/ER_and_Schema_Design.md)
- [SQL Execution Guide](docs/SQL_Execution_Guide.md)
- [System Report and Limitations](docs/System_Report_and_Limitations.md)
- [Demo Script and Screenshot Guide](docs/Demo_Script_and_Screenshots.md)
- [Authentication and Approval Guide](docs/Auth_and_Approval_Guide.md)
- [Verification Log](tests/test_log.md)

## Limitations

- Jaccard similarity is lexical/set-based and does not detect semantic equivalence.
- Seed-data results are intended for a PBL demonstration rather than production-scale analytics.
- Recursive traversal performance should be considered when expanding beyond the small demonstration dataset.
- Production deployment should use a least-privilege MySQL account, TLS, backups, and a managed secrets store.