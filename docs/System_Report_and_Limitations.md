# System Architecture Report & Project Limitations

## 1. Architectural Philosophy
The core principle governing this system is **Database-Centric Computation**. Rather than pulling large volumes of unaggregated raw records into the application tier:
- All business rules, recursive graphs, set intersections, and multi-entity joins are pushed into MySQL views and stored procedures.
- The web tier (Streamlit) operates as a thin presentation layer executing only `SELECT * FROM v_x` or `CALL sp_x(...)`.
- Parameterized queries are universally enforced across all endpoints to prevent SQL injection vulnerabilities.

---

## 2. Technical Limitations & Engineering Trade-Offs

### 1. Lexical vs. Semantic Similarity
- **Current Implementation**: The publication similarity engine employs Jaccard set overlap over assigned topics and keywords:
  $$\text{Score} = 0.4 \times J_{\text{topic}} + 0.6 \times J_{\text{keyword}}$$
- **Limitation**: Jaccard similarity is strictly syntactic and discrete. Two papers addressing synonymous domains (e.g., "Deep Learning" vs. "Neural Networks") without overlapping tag assignments receive lower scores than their true conceptual affinity.
- **Academic Distinction**: The system explicitly reports scores as **"Potential Overlap"** rather than a plagiarism judgment or semantic duplicate detector.

### 2. MySQL Error 3823 & Trigger Enforcement
- **Constraint Consideration**: Standard SQL table check constraints (`CHECK (citing_p_id <> cited_p_id)`) were considered for preventing self-citations.
- **MySQL Limitation**: In earlier MySQL versions and specific storage configurations, subqueries or cross-referencing constraints in CHECK clauses encounter `Error 3823` or are not enforced during row updates.
- **Engineered Solution**: Enforced using `BEFORE INSERT` and `BEFORE UPDATE` database triggers (`prevent_self_citation` and `prevent_self_citation_update`), raising SQLSTATE `'45000'` with custom error text: `'A paper cannot cite itself'`.

### 3. Cycle Detection in Recursive CTEs
- **Limitation**: Unlike Oracle or PostgreSQL, MySQL does not provide native `CYCLE ... SET ... TO ... DEFAULT ...` syntax for recursive common table expressions.
- **Engineered Solution**: Implemented explicit cycle guards by maintaining a comma-delimited path accumulator `,p1,p2,p3,` and checking `path NOT LIKE CONCAT('%,', candidate_id, ',%')`. The delimiters ensure paper ID `1` does not falsely substring-match paper ID `11` or `21`.

### 4. Sample Dataset Size
- **Current Scope**: The initial seed dataset comprises 13 tables containing 99 rows across 5 researchers, 6 papers, 3 conferences, 6 topics, 8 keywords, 3 projects, and 4 datasets.
- **Performance Expectation**: Recursive CTEs and Jaccard joins run in sub-millisecond time. In high-volume production deployments (>100k papers), recursive CTEs require indexed adjacency matrices or graph extensions.

### 5. Authentication & Access Control
- **Scope**: Designed as an open academic discovery dashboard. User authentication, login workflows, and fine-grained role-based permissions (RBAC) are excluded from the current educational PBL scope.

