-- Phase 2: Collaboration Discovery View
-- View: v_collaborators
-- Contract: r1_id, r1_name, r2_id, r2_name, shared_topic_count, shared_topics, already_coauthored
-- Rules: r1_id < r2_id, at least 2 distinct shared topics

USE research_collaboration_db;

CREATE OR REPLACE VIEW v_collaborators AS
WITH researcher_topics AS (
    SELECT DISTINCT
        a.r_id,
        ht.t_id,
        t.t_name
    FROM AUTHORS a
    JOIN HAS_TOPIC ht ON a.p_id = ht.p_id
    JOIN TOPIC t ON ht.t_id = t.t_id
),
coauthors AS (
    SELECT DISTINCT
        a1.r_id AS r1_id,
        a2.r_id AS r2_id
    FROM AUTHORS a1
    JOIN AUTHORS a2 ON a1.p_id = a2.p_id AND a1.r_id < a2.r_id
)
SELECT
    r1.r_id AS r1_id,
    r1.r_name AS r1_name,
    r2.r_id AS r2_id,
    r2.r_name AS r2_name,
    COUNT(DISTINCT rt1.t_id) AS shared_topic_count,
    GROUP_CONCAT(DISTINCT rt1.t_name ORDER BY rt1.t_name SEPARATOR ', ') AS shared_topics,
    CASE WHEN ca.r1_id IS NOT NULL THEN 1 ELSE 0 END AS already_coauthored
FROM researcher_topics rt1
JOIN researcher_topics rt2 
    ON rt1.t_id = rt2.t_id 
    AND rt1.r_id < rt2.r_id
JOIN RESEARCHER r1 ON rt1.r_id = r1.r_id
JOIN RESEARCHER r2 ON rt2.r_id = r2.r_id
LEFT JOIN coauthors ca ON rt1.r_id = ca.r1_id AND rt2.r_id = ca.r2_id
GROUP BY r1.r_id, r1.r_name, r2.r_id, r2.r_name, ca.r1_id
HAVING shared_topic_count >= 2
ORDER BY shared_topic_count DESC, r1.r_id, r2.r_id;

