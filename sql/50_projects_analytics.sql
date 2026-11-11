-- Phase 7: Project & Analytics Views
-- Views:
--   v_project_team
--   v_project_datasets
--   v_projects_shared
--   v_papers_per_conference
--   v_papers_per_year
--   v_papers_per_topic

USE research_collaboration_db;

-- 1. v_project_team: researchers working on each project
CREATE OR REPLACE VIEW v_project_team AS
SELECT
    p.project_id,
    p.name AS project_name,
    r.r_id,
    r.r_name,
    r.institution
FROM PROJECT p
JOIN WORKS_ON wo ON p.project_id = wo.project_id
JOIN RESEARCHER r ON wo.r_id = r.r_id
ORDER BY p.project_id, r.r_name;

-- 2. v_project_datasets: datasets used by each project
CREATE OR REPLACE VIEW v_project_datasets AS
SELECT
    p.project_id,
    p.name AS project_name,
    d.dataset_id,
    d.name AS dataset_name,
    d.source
FROM PROJECT p
JOIN USES u ON p.project_id = u.project_id
JOIN DATASET d ON u.dataset_id = d.dataset_id
ORDER BY p.project_id, d.name;

-- 3. v_projects_shared: project pairs sharing researchers or datasets
CREATE OR REPLACE VIEW v_projects_shared AS
WITH proj_researchers AS (
    SELECT
        w1.project_id AS p1_id,
        w2.project_id AS p2_id,
        COUNT(DISTINCT w1.r_id) AS shared_researcher_count
    FROM WORKS_ON w1
    JOIN WORKS_ON w2 ON w1.r_id = w2.r_id AND w1.project_id < w2.project_id
    GROUP BY w1.project_id, w2.project_id
),
proj_datasets AS (
    SELECT
        u1.project_id AS p1_id,
        u2.project_id AS p2_id,
        COUNT(DISTINCT u1.dataset_id) AS shared_dataset_count
    FROM USES u1
    JOIN USES u2 ON u1.dataset_id = u2.dataset_id AND u1.project_id < u2.project_id
    GROUP BY u1.project_id, u2.project_id
),
shared_pairs AS (
    SELECT p1_id, p2_id FROM proj_researchers
    UNION
    SELECT p1_id, p2_id FROM proj_datasets
)
SELECT
    sp.p1_id,
    pr1.name AS p1_name,
    sp.p2_id,
    pr2.name AS p2_name,
    COALESCE(pr.shared_researcher_count, 0) AS shared_researcher_count,
    COALESCE(pd.shared_dataset_count, 0) AS shared_dataset_count
FROM shared_pairs sp
JOIN PROJECT pr1 ON sp.p1_id = pr1.project_id
JOIN PROJECT pr2 ON sp.p2_id = pr2.project_id
LEFT JOIN proj_researchers pr ON sp.p1_id = pr.p1_id AND sp.p2_id = pr.p2_id
LEFT JOIN proj_datasets pd ON sp.p1_id = pd.p1_id AND sp.p2_id = pd.p2_id
WHERE COALESCE(pr.shared_researcher_count, 0) > 0 OR COALESCE(pd.shared_dataset_count, 0) > 0
ORDER BY sp.p1_id, sp.p2_id;

-- 4. v_papers_per_conference: papers per conference (includes 0 and No conference)
CREATE OR REPLACE VIEW v_papers_per_conference AS
SELECT
    c.c_id,
    c.c_name,
    COUNT(p.p_id) AS paper_count
FROM CONFERENCE c
LEFT JOIN PAPER p ON c.c_id = p.c_id
GROUP BY c.c_id, c.c_name
UNION ALL
SELECT
    NULL AS c_id,
    'No conference' AS c_name,
    COUNT(*) AS paper_count
FROM PAPER
WHERE c_id IS NULL
HAVING paper_count > 0;

-- 5. v_papers_per_year: papers published per year
CREATE OR REPLACE VIEW v_papers_per_year AS
SELECT
    pub_year,
    COUNT(*) AS paper_count
FROM PAPER
GROUP BY pub_year
ORDER BY pub_year;

-- 6. v_papers_per_topic: papers per topic (includes 0)
CREATE OR REPLACE VIEW v_papers_per_topic AS
SELECT
    t.t_id,
    t.t_name,
    COUNT(ht.p_id) AS paper_count
FROM TOPIC t
LEFT JOIN HAS_TOPIC ht ON t.t_id = ht.t_id
GROUP BY t.t_id, t.t_name
ORDER BY paper_count DESC, t.t_name;
