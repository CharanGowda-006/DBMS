# Research Collaboration Network

An academic research collaboration and discovery dashboard built with **MySQL 8**, **Python 3.11**, **Streamlit**, and **pandas**. The application manages researchers, publications, conferences, topics, keywords, projects, datasets, authorship, citations, and cross-project relationships.

Core analytics run in MySQL through views and stored procedures, keeping the Streamlit frontend focused on presentation and interaction.

## Features

- **Live database overview** with entity and relationship-table counts
- **Publication analytics** by year, conference, and research topic
- **Unified search** across papers, researchers, conferences, projects, and datasets
- **Collaboration discovery** for researcher pairs sharing at least two topics
- **Publication similarity** using a weighted Jaccard score:
  - 40% topic similarity
  - 60% keyword similarity
- **Citation traversal** in forward and reverse directions using a cycle-safe recursive CTE
- **Project analytics** for project teams, datasets, and shared resources
- **Validated data-entry forms** for core entities, papers, citations, project assignments, and dataset links
- **Atomic paper registration** that rolls back all related inserts if one step fails

Similarity and overlap values represent **potential topical overlap**, not plagiarism or duplicate detection.

## Technology Stack

| Component | Technology |
|---|---|
| Database | MySQL 8.0 / 8.0.41 |
| Application | Streamlit |
| Backend language | Python 3.11 |
| MySQL driver | `mysql-connector-python` |
| Data handling | pandas |

## Database Model

The system uses 13 tables:

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

## Project Structure

```text
app/
  Home.py                 # Application entry page
  db.py                   # MySQL connection and query helpers
  pages/                  # Streamlit feature pages
sql/
  00_verify.sql           # Database verification
  10_collab.sql           # Collaboration view
  20_sim_parts.sql        # Topic and keyword similarity views
  21_sim_final.sql        # Weighted publication similarity view
  30_citations.sql        # Citation traversal stored procedure
  40_search.sql           # Unified search stored procedure
  50_projects_analytics.sql
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

4. Create the local environment file:

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

For the dashboard, run the canonical scripts in the following order. Use MySQL Workbench or the MySQL command-line client.

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
```

Run `sql/00_verify.sql` in MySQL Workbench or MySQL CLI after setup.

## Run the Dashboard

From the repository root:

```powershell
streamlit run app/Home.py
```

Streamlit normally opens the application at `http://localhost:8501`.

### Application pages

1. **Overview**: KPIs and analytics charts
2. **Search**: cross-entity search and detailed paper inspection
3. **Insights**: potential collaborators and publication similarity
4. **Citations**: forward and reverse citation traversal
5. **Projects**: project teams, datasets, and shared resources
6. **Add Basic**: register core entities
7. **Add Paper**: register linked papers and citations with constraint handling

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

Run the verification script and inspect [tests/test_log.md](tests/test_log.md). The test matrix covers table counts, search behavior, similarity filtering, citation traversal, duplicate constraints, foreign keys, delete cascade actions, and self-citation rejection.

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
- [Verification Log](tests/test_log.md)

## Limitations

- Jaccard similarity is lexical/set-based and does not detect semantic equivalence.
- The open dashboard does not implement authentication or role-based access control.
- Seed-data results are intended for a PBL demonstration rather than production-scale analytics.
- Recursive traversal performance should be considered when expanding beyond the small demonstration dataset.