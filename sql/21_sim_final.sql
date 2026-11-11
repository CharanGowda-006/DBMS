-- Phase 4: Combined Similarity View
-- View: v_paper_similarity
-- Weights chosen: w_t = 0.4 (topic weight), w_k = 0.6 (keyword weight)
-- Overlap bands:
--   score >= 0.6: "High potential overlap"
--   score >= 0.3: "Moderate potential overlap"
--   else:         "Low potential overlap"
-- Wording used: "potential overlap" only

USE research_collaboration_db;

CREATE OR REPLACE VIEW v_paper_similarity AS
WITH pairs AS (
    SELECT p1_id, p2_id FROM v_paper_topic_sim
    UNION
    SELECT p1_id, p2_id FROM v_paper_keyword_sim
)
SELECT
    pairs.p1_id,
    p1.p_title AS p1_title,
    pairs.p2_id,
    p2.p_title AS p2_title,
    COALESCE(ts.topic_jaccard, 0) AS topic_jaccard,
    COALESCE(ks.keyword_jaccard, 0) AS keyword_jaccard,
    ROUND(0.4 * COALESCE(ts.topic_jaccard, 0) + 0.6 * COALESCE(ks.keyword_jaccard, 0), 4) AS similarity_score,
    CASE
        WHEN (0.4 * COALESCE(ts.topic_jaccard, 0) + 0.6 * COALESCE(ks.keyword_jaccard, 0)) >= 0.6 THEN 'High potential overlap'
        WHEN (0.4 * COALESCE(ts.topic_jaccard, 0) + 0.6 * COALESCE(ks.keyword_jaccard, 0)) >= 0.3 THEN 'Moderate potential overlap'
        ELSE 'Low potential overlap'
    END AS overlap_band,
    (
        SELECT GROUP_CONCAT(t.t_name ORDER BY t.t_name SEPARATOR ', ')
        FROM HAS_TOPIC ht1
        JOIN HAS_TOPIC ht2 ON ht1.t_id = ht2.t_id
        JOIN TOPIC t ON ht1.t_id = t.t_id
        WHERE ht1.p_id = pairs.p1_id AND ht2.p_id = pairs.p2_id
    ) AS shared_topics,
    (
        SELECT GROUP_CONCAT(k.keyword ORDER BY k.keyword SEPARATOR ', ')
        FROM HAS_KEYWORD hk1
        JOIN HAS_KEYWORD hk2 ON hk1.key_id = hk2.key_id
        JOIN KEYWORD k ON hk1.key_id = k.key_id
        WHERE hk1.p_id = pairs.p1_id AND hk2.p_id = pairs.p2_id
    ) AS shared_keywords
FROM pairs
JOIN PAPER p1 ON pairs.p1_id = p1.p_id
JOIN PAPER p2 ON pairs.p2_id = p2.p_id
LEFT JOIN v_paper_topic_sim ts ON pairs.p1_id = ts.p1_id AND pairs.p2_id = ts.p2_id
LEFT JOIN v_paper_keyword_sim ks ON pairs.p1_id = ks.p1_id AND pairs.p2_id = ks.p2_id
ORDER BY similarity_score DESC, pairs.p1_id, pairs.p2_id;
