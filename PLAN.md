# PLAN: from verified tables to finished dashboard

Status at start: 13 tables created and populated. Verification, six features, the dashboard and the report are still open.

How to use: one phase = one fresh agent chat. Paste ONLY that phase's brief (section 5) into the agent. Do not make the agent read this whole file. Commit after each phase.

## 1. Rules that keep sessions cheap
1. Agents read `CONTEXT.md`, never the full project doc.
2. One phase, one output file.
3. Logic lives in the database. Every feature ends as a view or stored procedure, so dashboard pages only run `SELECT * FROM v_x` or `CALL sp_x(...)`.
4. Show only the first ~20 rows. Every brief lists its expected result, so checking is a comparison.
5. Any test that writes data runs inside `START TRANSACTION ... ROLLBACK`.

## 2. Phase Map
| # | Phase | Output | Needs |
|---|---|---|---|
| P0 | You: confirm requirements | none | none |
| P1 | Verify DB + fill CONTEXT | `sql/00_verify.sql`, `schema.sql`, `seed.sql` | P0 |
| P2 | Collaboration view | `sql/10_collab.sql` | P1 |
| P3 | Similarity building blocks | `sql/20_sim_parts.sql` | P1 |
| P4 | Combined similarity | `sql/21_sim_final.sql` | P3 |
| P5 | Citation traversal | `sql/30_citations.sql` | P1 |
| P6 | Unified search | `sql/40_search.sql` | P1 |
| P7 | Project + analytics views | `sql/50_projects_analytics.sql` | P1 |
| P8 | App skeleton + DB layer | `app/db.py`, `app/Home.py` | P1 |
| P9 | Overview page | `app/pages/1_Overview.py` | P7, P8 |
| P10 | Search page | `app/pages/2_Search.py` | P6, P8 |
| P11 | Collaboration + similarity page | `app/pages/3_Insights.py` | P2, P4, P8 |
| P12 | Citation explorer | `app/pages/4_Citations.py` | P5, P8 |
| P13 | Projects + datasets page | `app/pages/5_Projects.py` | P7, P8 |
| P14 | Simple add-forms | `app/pages/6_Add_Basic.py` | P8 |
| P15 | Linked add-forms | `app/pages/7_Add_Paper.py` | P14 |
| P16 | Test pass | `tests/test_log.md` | all |
| P17 | Report + demo material | `docs/` | P16 |

## 3. Phase Briefs
See details in individual phase executions.

