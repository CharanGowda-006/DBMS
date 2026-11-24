# Test Execution Log: Full System Verification Matrix

| Test Case | Execution Steps | Expected Outcome | Actual Outcome | Status |
|---|---|---|---|---|
| **Home: 13 table counts** | Query all 13 tables | 13 tables with total 99 rows | Found 13 tables, 99 total rows | **PASS** |
| **Overview: analytical views** | Query analytical views | All 3 views return data | Years: 2, Confs: 3, Topics: 6 | **PASS** |
| **Search: Computer Vision** | Call sp_search('Computer Vision') | Returns papers [1, 2, 5] | Returned papers [1, 2, 5] | **PASS** |
| **Search: empty results** | Search nonsense term and whitespace | Both return 0 rows | Nonsense: 0, Blank: 0 | **PASS** |
| **Insights: v_collaborators** | Query v_collaborators | 6 pairs, all r1 < r2 | 6 pairs, all ordered: True | **PASS** |
| **Insights: similarity slider at max** | Filter v_paper_similarity >= 1.0 | (1,5) and (3,6) present | Pairs found: [(1, 5), (3, 6)] | **PASS** |
| **Citations: paper 6 forward** | Call sp_citations(6, 'forward', 5) | Reaches 2, 3 at depth 1 and 1 at depth 2 | Reached papers [2, 3, 1] | **PASS** |
| **Citations: paper with no outgoing citations** | Call sp_citations(4, 'forward', 5) | 0 rows returned | 0 rows returned | **PASS** |
| **Duplicate insert: email** | Insert duplicate researcher email | 'This record already exists.' | This record already exists. | **PASS** |
| **Duplicate insert: topic** | Insert duplicate topic name | 'This record already exists.' | This record already exists. | **PASS** |
| **Duplicate insert: keyword** | Insert duplicate keyword | 'This record already exists.' | This record already exists. | **PASS** |
| **Duplicate insert: WORKS_ON link** | Insert duplicate link | 'This record already exists.' | This record already exists. | **PASS** |
| **Invalid FK reference** | Insert paper with invalid c_id | 'Referenced record missing or still in use.' | Referenced record missing or still in use. | **PASS** |
| **Self-citation: INSERT** | Insert (1, 1) in CITES | 'A paper cannot cite itself.' | A paper cannot cite itself. | **PASS** |
| **Cycle termination: A<->B** | Add 1->4 and 4->1, call sp_citations(1, 'forward', 10) | Terminates without loop | Terminated cleanly with 1 rows | **PASS** |
| **Delete conference: ON DELETE SET NULL** | Delete conference 1 in transaction | Paper 1 c_id becomes NULL, 'No conference' row appears | Paper 1 c_id: None, No conf count: 2 | **PASS** |
| **Delete researcher: CASCADE** | Delete researcher 4 in transaction | Junction rows in WORKS_ON and AUTHORS cascade | Works_on before: 1, after: 0, Authors after: 0 | **PASS** |
| **Delete paper: CASCADE** | Delete paper 1 in transaction | Junction rows cascade across all 4 tables | Authors: 0, Topics: 0, Keywords: 0, Cites: 0 | **PASS** |

## Authentication, Workflow, and Project Management Unit Tests

| Validation | Result |
|---|---|
| Command | `python -m unittest discover -s tests -q` |
| Outcome | **76 passed** using mocked database connections and Streamlit AppTest |
| Covered | Authentication, role authorization, project ownership, duplicate project names, project detail updates, researcher/dataset assignment and removal, atomic new-resource registration, duplicate relationships, audit events, paper workflows, approved-only SQL visibility, citation and collaboration graph construction, Insights filtering/comparison, and citation/Insights page rendering |
| Python syntax | `python -m compileall -q app tests` — **PASS** |
| Streamlit startup | Projects `AppTest` rendered Explore and role-specific management for student, teacher, and admin; Add Paper and My Submissions smoke tests also passed — **PASS** |
| MySQL integration | **Not run**: no database migrations or writes were attempted. Apply the additive migration and verify against a dedicated test database before production use. |

## Research Network Insights

| Validation | Result |
|---|---|
| Insights unit and page tests | **9 passed**: researcher-specific pair filtering, ranking, duplicate-edge prevention, graph selection/legend, similarity pair orientation and deduplication, score preservation, filter-aware counts, topic/keyword set comparison, and Streamlit page interaction |
| Analytics visibility | Researcher list, collaboration pairs, similarity pairs, and comparison details are queried from approved-only SQL views or explicitly status-filtered parameterized queries. Read-only results use a 30-second Streamlit cache. |
| MySQL integration | **Not run**: verification used mocked database reads; no database writes or migrations were performed. |

## Citation Network Explorer

| Validation | Result |
|---|---|
| Graph and page tests | **11 passed**: forward/reverse edge direction, deduplication, multiple paths, real-edge filtering, unapproved-path filtering, isolated root, graph cap, depth validation, approved-only selector, rendered graph, and empty state |
| Approved-only visibility | Root, graph edges, publication metadata, authors, topics, and keywords are queried with approved-status filters — **PASS in mocked page tests; MySQL integration not run** |
| MySQL integration | **Not run**: citation queries were not executed against the working database. |

## Frontend Modernization

| Validation | Result |
|---|---|
| Streamlit page smoke tests | **5 passed**: login and registration password visibility preserve entered values; dashboard renders mocked metrics, publications, and role links; Add Paper retains the title when advancing to the author step; shared styling does not apply the application font directly to Streamlit's internal icon elements. |
| AppTest navigation note | Isolated page tests mock `st.page_link`; production navigation is registered centrally by `app/Home.py`. |
| Python syntax and patch formatting | `py -3.14 -m compileall -q app tests` and `git diff --check` — **PASS** |
| Browser validation | Login page loaded locally; the sidebar collapse glyph was visually rendered, and browser inspection confirmed Streamlit's Material Symbols spans retain `Material Symbols Rounded`. The password visibility control toggled successfully. Other pages/expander forms and light-theme rendering were not visually checked. |
| MySQL integration | **Not run**: database integrations were not performed. |

## Smart Paper Import

| Validation | Result |
|---|---|
| Complete Python test suite | `py -3.14 -m unittest discover -s tests -q` — **99 passed** |
| Python syntax and patch formatting | `py -3.14 -m compileall -q app tests` and `git diff --check` — **PASS** |
| Upload/review interaction | Streamlit AppTest confirms extracted values can be edited and the flow reaches final review; author removal clears stale widget state — **PASS** |
| Submission and file access | Mocked transaction tests verify rollback cleanup, duplicate DOI rejection, confirmation-only citation writes, teacher ownership checks, and role denial — **PASS** |
| Database migration | Additive `PAPER_INGESTION` table and foreign key verified in `research_collaboration_db`; existing rows were not modified. |
| Extraction regression fixture | Two-page synthetic IEEE-style PDF (591,772 bytes) verifies complete abstract, ordered authors/emails, six keywords, four references, missing year/DOI/venue, and repeated-header handling — **PASS** |
| Topic classification and UI | Alias mapping, title/keyword fallback without an abstract, existing-topic ID resolution, proposed-topic separation, unchecked creation consent, and Streamlit multiselect preselection — **PASS** |
| Parser quality limitations | Fixtures are synthetic. No representative scholarly-PDF accuracy benchmark, OCR test, or cross-layout/browser validation was performed. |
