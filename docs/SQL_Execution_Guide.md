# SQL Script Execution Guide

This document lists all database migration, schema definition, view generation, and stored procedure scripts in their strict execution order.

---

## Script Execution Order

| Step | Script File | Purpose | Output Artifacts / Objects Created |
|---|---|---|---|
| **1** | `sql/schema.sql` | DDL for core tables, indexes, foreign keys, triggers | 13 tables, primary/foreign keys, indexes, triggers |
| **2** | `sql/seed.sql` | Canonical database population | Initial 99 rows across all 13 tables |
| **3** | `sql/00_verify.sql` | Verification tests, row count checks, trigger integrity checks | Console report; verifies Error 1644 on self-citation |
| **4** | `sql/10_collab.sql` | Collaboration discovery view | `v_collaborators` |
| **5** | `sql/20_sim_parts.sql` | Isolated Jaccard similarity views for topics & keywords | `v_paper_topic_sim`, `v_paper_keyword_sim` |
| **6** | `sql/21_sim_final.sql` | Weighted composite publication similarity view | `v_paper_similarity` |
| **7** | `sql/30_citations.sql` | Recursive CTE citation traversal procedure with cycle guard | `sp_citations(start_p_id, direction, max_depth)` |
| **8** | `sql/40_search.sql` | Unified cross-entity search procedure | `sp_search(term)` |
| **9** | `sql/50_projects_analytics.sql` | Analytical aggregation views & project resource sharing views | `v_project_team`, `v_project_datasets`, `v_projects_shared`, `v_papers_per_conference`, `v_papers_per_year`, `v_papers_per_topic` |

---

## Detailed Script Descriptions

### 1. `sql/schema.sql`
Defines the complete database DDL, including table definitions (`RESEARCHER`, `CONFERENCE`, `PAPER`, `TOPIC`, `KEYWORD`, `PROJECT`, `DATASET`, `AUTHORS`, `CITES`, `HAS_TOPIC`, `HAS_KEYWORD`, `WORKS_ON`, `USES`), check constraints, composite primary keys, foreign key cascade actions, and before-insert/before-update triggers.

### 2. `sql/seed.sql`
Populates all tables with curated academic data representing real-world papers, authors, conferences (e.g. ICML, IEEE CV), topics, keywords, and citation structures.

### 3. `sql/10_collab.sql`
Computes researcher pairs who share at least 2 distinct topics across papers they authored.
- Prevents duplicates and reflexive pairs via `r1_id < r2_id`.
- Flags whether the researchers have already co-authored papers using `already_coauthored = 1`.

### 4. `sql/20_sim_parts.sql` & `sql/21_sim_final.sql`
Calculates set-theoretic Jaccard similarity:
$$\text{Jaccard}(A, B) = \frac{|A \cap B|}{|A \cup B|} = \frac{|A \cap B|}{|A| + |B| - |A \cap B|}$$
- Computes topic similarity and keyword similarity in independent views to avoid Cartesian fan-out.
- Weights: $w_t = 0.4$ (topic overlap), $w_k = 0.6$ (keyword overlap).
- Classifies overlap bands: $\ge 0.6$ ("High potential overlap"), $\ge 0.3$ ("Moderate potential overlap"), else ("Low potential overlap").

### 5. `sql/30_citations.sql`
Implements recursive common table expressions (CTEs) traversing multi-level citation pathways in both `forward` (papers cited) and `reverse` (papers citing) directions.
- Carries path string `,id1,id2,id3,` to detect cycles and prevent infinite loops.
- Enforces depth capping with default depth 5.

### 6. `sql/40_search.sql`
Executes single-term cross-entity search returning standardized `(result_type, ref_id, label, detail)` tuples across papers, researchers, conferences, projects, and datasets.

### 7. `sql/50_projects_analytics.sql`
Supplies aggregated metrics for dashboard charting, including publications per conference (handling conferences with 0 papers and unassigned papers), publications per year, and cross-project personnel/dataset sharing.
