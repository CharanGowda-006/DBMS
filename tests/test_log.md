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
