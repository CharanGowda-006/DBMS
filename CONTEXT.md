# CONTEXT.md: Research Collaboration Database & Dashboard

## 1. Stack & System Config
- **Database**: MySQL 8.0 / 9.x (`research_collaboration_db`)
- **Backend / Frontend**: Python 3.11, Streamlit, pandas, mysql-connector-python
- **DB Connection**: host=localhost, port=3306, user=root, db=research_collaboration_db

## 2. Schema Summary (13 Tables)
### Core Entities
1. `RESEARCHER` (`r_id` PK, `r_name` VARCHAR(150), `email` VARCHAR(255) UNIQUE, `institution` VARCHAR(255))
2. `CONFERENCE` (`c_id` PK, `c_name` VARCHAR(255), `c_year` SMALLINT UNSIGNED, `c_location` VARCHAR(255))
3. `PAPER` (`p_id` PK, `p_title` VARCHAR(500), `abstract` TEXT, `pub_year` SMALLINT UNSIGNED, `c_id` FK -> CONFERENCE ON DELETE SET NULL)
4. `TOPIC` (`t_id` PK, `t_name` VARCHAR(150) UNIQUE)
5. `KEYWORD` (`key_id` PK, `keyword` VARCHAR(150) UNIQUE)
6. `PROJECT` (`project_id` PK, `name` VARCHAR(255), `description` TEXT)
7. `DATASET` (`dataset_id` PK, `name` VARCHAR(255), `source` VARCHAR(1000))

### Relationship / Junction Tables
8. `AUTHORS` (`r_id` FK, `p_id` FK, `author_order` INT) - PK(`r_id`, `p_id`), UNIQUE(`p_id`, `author_order`)
9. `CITES` (`citing_p_id` FK, `cited_p_id` FK) - PK(`citing_p_id`, `cited_p_id`)
10. `HAS_TOPIC` (`p_id` FK, `t_id` FK) - PK(`p_id`, `t_id`)
11. `HAS_KEYWORD` (`p_id` FK, `key_id` FK) - PK(`p_id`, `key_id`)
12. `WORKS_ON` (`r_id` FK, `project_id` FK) - PK(`r_id`, `project_id`)
13. `USES` (`project_id` FK, `dataset_id` FK) - PK(`project_id`, `dataset_id`)

## 3. Expected Table Row Counts
| Table Name | Expected Count |
|---|---|
| RESEARCHER | 5 |
| CONFERENCE | 3 |
| PAPER | 6 |
| TOPIC | 6 |
| KEYWORD | 8 |
| PROJECT | 3 |
| DATASET | 4 |
| AUTHORS | 10 |
| CITES | 5 |
| HAS_TOPIC | 16 |
| HAS_KEYWORD | 21 |
| WORKS_ON | 8 |
| USES | 4 |
**Total tables**: 13

## 4. Business Rules & Triggers
- **Self-Citation Prevention**: A paper cannot cite itself (`citing_p_id = cited_p_id`).
  - Trigger error: SQLSTATE '45000', Message: `'A paper cannot cite itself'`.
  - Must apply to both `INSERT` and `UPDATE` on `CITES`.

## 5. View & Stored Procedure Contracts
- `v_collaborators`: `r1_id`, `r1_name`, `r2_id`, `r2_name`, `shared_topic_count`, `shared_topics`, `already_coauthored` (`r1_id < r2_id`, `shared_topic_count >= 2`).
- `v_paper_topic_sim`: `p1_id`, `p2_id`, `shared_count`, `union_count`, `topic_jaccard` (`p1_id < p2_id`, `shared_count > 0`).
- `v_paper_keyword_sim`: `p1_id`, `p2_id`, `shared_count`, `union_count`, `keyword_jaccard` (`p1_id < p2_id`, `shared_count > 0`).
- `v_paper_similarity`: `p1_id`, `p1_title`, `p2_id`, `p2_title`, `topic_jaccard`, `keyword_jaccard`, `similarity_score`, `overlap_band`, `shared_topics`, `shared_keywords`.
- `sp_citations(IN start_p_id INT, IN direction VARCHAR(7), IN max_depth INT)`: returns `(depth, p_id, p_title, path)`. Cycle-safe recursive CTE.
- `sp_search(IN term VARCHAR(100))`: returns `(result_type, ref_id, label, detail)`.
- `v_project_team`: `(project_id, project_name, r_id, r_name, institution)`
- `v_project_datasets`: `(project_id, project_name, dataset_id, dataset_name, source)`
- `v_projects_shared`: `(p1_id, p1_name, p2_id, p2_name, shared_researcher_count, shared_dataset_count)`
- `v_papers_per_conference`: `(c_id, c_name, paper_count)` (includes 0 and "No conference")
- `v_papers_per_year`: `(pub_year, paper_count)`
- `v_papers_per_topic`: `(t_id, t_name, paper_count)` (includes 0)

## 6. Verified Facts
- **Verification Date**: 2026-11-11
- **Database Engine**: MySQL 8.0.41 (InnoDB)
- **Table Count**: 13 tables confirmed (`RESEARCHER`, `CONFERENCE`, `PAPER`, `TOPIC`, `KEYWORD`, `PROJECT`, `DATASET`, `AUTHORS`, `CITES`, `HAS_TOPIC`, `HAS_KEYWORD`, `WORKS_ON`, `USES`).
- **Verified Row Counts**:
  - `RESEARCHER`: 5
  - `CONFERENCE`: 3
  - `PAPER`: 6
  - `TOPIC`: 6
  - `KEYWORD`: 8
  - `PROJECT`: 3
  - `DATASET`: 4
  - `AUTHORS`: 10
  - `CITES`: 5
  - `HAS_TOPIC`: 16
  - `HAS_KEYWORD`: 21
  - `WORKS_ON`: 8
  - `USES`: 4
- **Trigger Behavior**:
  - `prevent_self_citation` (`BEFORE INSERT ON CITES`) and `prevent_self_citation_update` (`BEFORE UPDATE ON CITES`) active.
  - Self-citation test rejection code: Error `1644` (SQLSTATE `45000`), Message: `'A paper cannot cite itself'`.
  - Both `INSERT` and `UPDATE` tests reject as expected.
  - `CITES` row count confirmed unchanged (exactly 5 rows) after transaction rollback.
- **Join Verification**:
  - `RESEARCHER-AUTHORS-PAPER` returns 10 authored pairs ordered by `p_id, author_order`.


