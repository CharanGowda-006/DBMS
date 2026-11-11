-- Phase 3: Similarity Building Blocks
-- Views: v_paper_topic_sim and v_paper_keyword_sim
-- Columns per contract:
--   v_paper_topic_sim:   p1_id, p2_id, shared_count, union_count, topic_jaccard
--   v_paper_keyword_sim: p1_id, p2_id, shared_count, union_count, keyword_jaccard
-- Rules: p1_id < p2_id, only shared_count > 0, separate views, NULLIF for union_count

USE research_collaboration_db;

CREATE OR REPLACE VIEW v_paper_topic_sim AS
WITH paper_topic_counts AS (
    SELECT p_id, COUNT(DISTINCT t_id) AS total_topics
    FROM HAS_TOPIC
    GROUP BY p_id
),
shared AS (
    SELECT
        ht1.p_id AS p1_id,
        ht2.p_id AS p2_id,
        COUNT(DISTINCT ht1.t_id) AS shared_count
    FROM HAS_TOPIC ht1
    JOIN HAS_TOPIC ht2 ON ht1.t_id = ht2.t_id AND ht1.p_id < ht2.p_id
    GROUP BY ht1.p_id, ht2.p_id
)
SELECT
    s.p1_id,
    s.p2_id,
    s.shared_count,
    (c1.total_topics + c2.total_topics - s.shared_count) AS union_count,
    ROUND(s.shared_count / NULLIF(c1.total_topics + c2.total_topics - s.shared_count, 0), 4) AS topic_jaccard
FROM shared s
JOIN paper_topic_counts c1 ON s.p1_id = c1.p_id
JOIN paper_topic_counts c2 ON s.p2_id = c2.p_id
WHERE s.shared_count > 0;

CREATE OR REPLACE VIEW v_paper_keyword_sim AS
WITH paper_keyword_counts AS (
    SELECT p_id, COUNT(DISTINCT key_id) AS total_keywords
    FROM HAS_KEYWORD
    GROUP BY p_id
),
shared AS (
    SELECT
        hk1.p_id AS p1_id,
        hk2.p_id AS p2_id,
        COUNT(DISTINCT hk1.key_id) AS shared_count
    FROM HAS_KEYWORD hk1
    JOIN HAS_KEYWORD hk2 ON hk1.key_id = hk2.key_id AND hk1.p_id < hk2.p_id
    GROUP BY hk1.p_id, hk2.p_id
)
SELECT
    s.p1_id,
    s.p2_id,
    s.shared_count,
    (c1.total_keywords + c2.total_keywords - s.shared_count) AS union_count,
    ROUND(s.shared_count / NULLIF(c1.total_keywords + c2.total_keywords - s.shared_count, 0), 4) AS keyword_jaccard
FROM shared s
JOIN paper_keyword_counts c1 ON s.p1_id = c1.p_id
JOIN paper_keyword_counts c2 ON s.p2_id = c2.p_id
WHERE s.shared_count > 0;
