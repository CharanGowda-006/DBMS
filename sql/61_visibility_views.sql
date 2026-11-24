-- Public discovery objects include approved papers only.
-- A missing workflow row means a historical paper and remains APPROVED.

USE research_collaboration_db;

CREATE OR REPLACE VIEW v_collaborators AS
WITH researcher_topics AS (
    SELECT DISTINCT a.r_id, ht.t_id, t.t_name
    FROM AUTHORS a
    JOIN PAPER p ON p.p_id = a.p_id
    LEFT JOIN PAPER_WORKFLOW w ON w.p_id = p.p_id
    JOIN HAS_TOPIC ht ON ht.p_id = p.p_id
    JOIN TOPIC t ON t.t_id = ht.t_id
    WHERE COALESCE(w.status, 'APPROVED') = 'APPROVED'
),
coauthors AS (
    SELECT DISTINCT a1.r_id AS r1_id, a2.r_id AS r2_id
    FROM AUTHORS a1
    JOIN AUTHORS a2 ON a1.p_id = a2.p_id AND a1.r_id < a2.r_id
    JOIN PAPER p ON p.p_id = a1.p_id
    LEFT JOIN PAPER_WORKFLOW w ON w.p_id = p.p_id
    WHERE COALESCE(w.status, 'APPROVED') = 'APPROVED'
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
JOIN researcher_topics rt2 ON rt1.t_id = rt2.t_id AND rt1.r_id < rt2.r_id
JOIN RESEARCHER r1 ON rt1.r_id = r1.r_id
JOIN RESEARCHER r2 ON rt2.r_id = r2.r_id
LEFT JOIN coauthors ca ON rt1.r_id = ca.r1_id AND rt2.r_id = ca.r2_id
GROUP BY r1.r_id, r1.r_name, r2.r_id, r2.r_name, ca.r1_id
HAVING shared_topic_count >= 2;

CREATE OR REPLACE VIEW v_paper_topic_sim AS
WITH paper_topic_counts AS (
    SELECT ht.p_id, COUNT(DISTINCT ht.t_id) AS total_topics
    FROM HAS_TOPIC ht
    JOIN PAPER p ON p.p_id = ht.p_id
    LEFT JOIN PAPER_WORKFLOW w ON w.p_id = p.p_id
    WHERE COALESCE(w.status, 'APPROVED') = 'APPROVED'
    GROUP BY ht.p_id
),
shared AS (
    SELECT ht1.p_id AS p1_id, ht2.p_id AS p2_id,
           COUNT(DISTINCT ht1.t_id) AS shared_count
    FROM HAS_TOPIC ht1
    JOIN HAS_TOPIC ht2 ON ht1.t_id = ht2.t_id AND ht1.p_id < ht2.p_id
    JOIN PAPER p1 ON p1.p_id = ht1.p_id
    JOIN PAPER p2 ON p2.p_id = ht2.p_id
    LEFT JOIN PAPER_WORKFLOW w1 ON w1.p_id = p1.p_id
    LEFT JOIN PAPER_WORKFLOW w2 ON w2.p_id = p2.p_id
    WHERE COALESCE(w1.status, 'APPROVED') = 'APPROVED'
      AND COALESCE(w2.status, 'APPROVED') = 'APPROVED'
    GROUP BY ht1.p_id, ht2.p_id
)
SELECT s.p1_id, s.p2_id, s.shared_count,
       c1.total_topics + c2.total_topics - s.shared_count AS union_count,
       ROUND(s.shared_count / NULLIF(c1.total_topics + c2.total_topics - s.shared_count, 0), 4) AS topic_jaccard
FROM shared s
JOIN paper_topic_counts c1 ON c1.p_id = s.p1_id
JOIN paper_topic_counts c2 ON c2.p_id = s.p2_id
WHERE s.shared_count > 0;

CREATE OR REPLACE VIEW v_paper_keyword_sim AS
WITH paper_keyword_counts AS (
    SELECT hk.p_id, COUNT(DISTINCT hk.key_id) AS total_keywords
    FROM HAS_KEYWORD hk
    JOIN PAPER p ON p.p_id = hk.p_id
    LEFT JOIN PAPER_WORKFLOW w ON w.p_id = p.p_id
    WHERE COALESCE(w.status, 'APPROVED') = 'APPROVED'
    GROUP BY hk.p_id
),
shared AS (
    SELECT hk1.p_id AS p1_id, hk2.p_id AS p2_id,
           COUNT(DISTINCT hk1.key_id) AS shared_count
    FROM HAS_KEYWORD hk1
    JOIN HAS_KEYWORD hk2 ON hk1.key_id = hk2.key_id AND hk1.p_id < hk2.p_id
    JOIN PAPER p1 ON p1.p_id = hk1.p_id
    JOIN PAPER p2 ON p2.p_id = hk2.p_id
    LEFT JOIN PAPER_WORKFLOW w1 ON w1.p_id = p1.p_id
    LEFT JOIN PAPER_WORKFLOW w2 ON w2.p_id = p2.p_id
    WHERE COALESCE(w1.status, 'APPROVED') = 'APPROVED'
      AND COALESCE(w2.status, 'APPROVED') = 'APPROVED'
    GROUP BY hk1.p_id, hk2.p_id
)
SELECT s.p1_id, s.p2_id, s.shared_count,
       c1.total_keywords + c2.total_keywords - s.shared_count AS union_count,
       ROUND(s.shared_count / NULLIF(c1.total_keywords + c2.total_keywords - s.shared_count, 0), 4) AS keyword_jaccard
FROM shared s
JOIN paper_keyword_counts c1 ON c1.p_id = s.p1_id
JOIN paper_keyword_counts c2 ON c2.p_id = s.p2_id
WHERE s.shared_count > 0;

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
        WHEN 0.4 * COALESCE(ts.topic_jaccard, 0) + 0.6 * COALESCE(ks.keyword_jaccard, 0) >= 0.6 THEN 'High potential overlap'
        WHEN 0.4 * COALESCE(ts.topic_jaccard, 0) + 0.6 * COALESCE(ks.keyword_jaccard, 0) >= 0.3 THEN 'Moderate potential overlap'
        ELSE 'Low potential overlap'
    END AS overlap_band,
    (SELECT GROUP_CONCAT(t.t_name ORDER BY t.t_name SEPARATOR ', ')
     FROM HAS_TOPIC ht1 JOIN HAS_TOPIC ht2 ON ht1.t_id = ht2.t_id
     JOIN TOPIC t ON t.t_id = ht1.t_id
     WHERE ht1.p_id = pairs.p1_id AND ht2.p_id = pairs.p2_id) AS shared_topics,
    (SELECT GROUP_CONCAT(k.keyword ORDER BY k.keyword SEPARATOR ', ')
     FROM HAS_KEYWORD hk1 JOIN HAS_KEYWORD hk2 ON hk1.key_id = hk2.key_id
     JOIN KEYWORD k ON k.key_id = hk1.key_id
     WHERE hk1.p_id = pairs.p1_id AND hk2.p_id = pairs.p2_id) AS shared_keywords
FROM pairs
JOIN PAPER p1 ON p1.p_id = pairs.p1_id
JOIN PAPER p2 ON p2.p_id = pairs.p2_id
LEFT JOIN v_paper_topic_sim ts ON ts.p1_id = pairs.p1_id AND ts.p2_id = pairs.p2_id
LEFT JOIN v_paper_keyword_sim ks ON ks.p1_id = pairs.p1_id AND ks.p2_id = pairs.p2_id;

CREATE OR REPLACE VIEW v_papers_per_conference AS
SELECT c.c_id, c.c_name,
       SUM(CASE WHEN p.p_id IS NOT NULL
                     AND COALESCE(w.status, 'APPROVED') = 'APPROVED'
                THEN 1 ELSE 0 END) AS paper_count
FROM CONFERENCE c
LEFT JOIN PAPER p ON p.c_id = c.c_id
LEFT JOIN PAPER_WORKFLOW w ON w.p_id = p.p_id
GROUP BY c.c_id, c.c_name
UNION ALL
SELECT NULL, 'No conference', COUNT(*)
FROM PAPER p
LEFT JOIN PAPER_WORKFLOW w ON w.p_id = p.p_id
WHERE p.c_id IS NULL AND COALESCE(w.status, 'APPROVED') = 'APPROVED'
HAVING COUNT(*) > 0;

CREATE OR REPLACE VIEW v_papers_per_year AS
SELECT p.pub_year, COUNT(*) AS paper_count
FROM PAPER p
LEFT JOIN PAPER_WORKFLOW w ON w.p_id = p.p_id
WHERE COALESCE(w.status, 'APPROVED') = 'APPROVED'
GROUP BY p.pub_year;

CREATE OR REPLACE VIEW v_papers_per_topic AS
SELECT t.t_id, t.t_name,
       SUM(CASE WHEN p.p_id IS NOT NULL
                     AND COALESCE(w.status, 'APPROVED') = 'APPROVED'
                THEN 1 ELSE 0 END) AS paper_count
FROM TOPIC t
LEFT JOIN HAS_TOPIC ht ON ht.t_id = t.t_id
LEFT JOIN PAPER p ON p.p_id = ht.p_id
LEFT JOIN PAPER_WORKFLOW w ON w.p_id = p.p_id
GROUP BY t.t_id, t.t_name;

DROP PROCEDURE IF EXISTS sp_search;
DELIMITER $$
CREATE PROCEDURE sp_search(IN term VARCHAR(100))
BEGIN
    DECLARE clean_term VARCHAR(100);
    SET clean_term = TRIM(term);
    IF clean_term IS NULL OR clean_term = '' THEN
        SELECT CAST(NULL AS CHAR(20)) AS result_type,
               CAST(NULL AS SIGNED) AS ref_id,
               CAST(NULL AS CHAR(500)) AS label,
               CAST(NULL AS CHAR(500)) AS detail
        WHERE 1 = 0;
    ELSE
        WITH matched_papers AS (
            SELECT m.p_id, m.p_title, m.c_id,
                   GROUP_CONCAT(DISTINCT m.match_reason ORDER BY m.match_reason SEPARATOR ', ') AS match_detail
            FROM (
                SELECT p.p_id, p.p_title, p.c_id, 'matched via title' AS match_reason
                FROM PAPER p LEFT JOIN PAPER_WORKFLOW w ON w.p_id = p.p_id
                WHERE COALESCE(w.status, 'APPROVED') = 'APPROVED'
                  AND p.p_title LIKE CONCAT('%', clean_term, '%')
                UNION ALL
                SELECT p.p_id, p.p_title, p.c_id, 'matched via topic'
                FROM PAPER p LEFT JOIN PAPER_WORKFLOW w ON w.p_id = p.p_id
                JOIN HAS_TOPIC ht ON ht.p_id = p.p_id
                JOIN TOPIC t ON t.t_id = ht.t_id
                WHERE COALESCE(w.status, 'APPROVED') = 'APPROVED'
                  AND t.t_name LIKE CONCAT('%', clean_term, '%')
                UNION ALL
                SELECT p.p_id, p.p_title, p.c_id, 'matched via keyword'
                FROM PAPER p LEFT JOIN PAPER_WORKFLOW w ON w.p_id = p.p_id
                JOIN HAS_KEYWORD hk ON hk.p_id = p.p_id
                JOIN KEYWORD k ON k.key_id = hk.key_id
                WHERE COALESCE(w.status, 'APPROVED') = 'APPROVED'
                  AND k.keyword LIKE CONCAT('%', clean_term, '%')
            ) m
            GROUP BY m.p_id, m.p_title, m.c_id
        ),
        matched_researchers AS (
            SELECT DISTINCT r.r_id, r.r_name, r.institution
            FROM matched_papers mp
            JOIN AUTHORS a ON a.p_id = mp.p_id
            JOIN RESEARCHER r ON r.r_id = a.r_id
        ),
        matched_projects AS (
            SELECT DISTINCT pr.project_id, pr.name
            FROM matched_researchers mr
            JOIN WORKS_ON wo ON wo.r_id = mr.r_id
            JOIN PROJECT pr ON pr.project_id = wo.project_id
        )
        SELECT 'paper' AS result_type, mp.p_id AS ref_id,
               mp.p_title AS label, mp.match_detail AS detail
        FROM matched_papers mp
        UNION ALL
        SELECT 'researcher', mr.r_id, mr.r_name,
               CONCAT('Author of matched paper; ', COALESCE(mr.institution, ''))
        FROM matched_researchers mr
        UNION ALL
        SELECT DISTINCT 'conference', c.c_id, c.c_name,
               CONCAT(c.c_year, ', ', COALESCE(c.c_location, ''))
        FROM matched_papers mp JOIN CONFERENCE c ON c.c_id = mp.c_id
        WHERE mp.c_id IS NOT NULL
        UNION ALL
        SELECT 'project', mpj.project_id, mpj.name, 'related via researcher'
        FROM matched_projects mpj
        UNION ALL
        SELECT DISTINCT 'dataset', d.dataset_id, d.name, 'related via project'
        FROM matched_projects mpj
        JOIN USES u ON u.project_id = mpj.project_id
        JOIN DATASET d ON d.dataset_id = u.dataset_id;
    END IF;
END $$
DELIMITER ;

DROP PROCEDURE IF EXISTS sp_citations;
DELIMITER $$
CREATE PROCEDURE sp_citations(
    IN start_p_id INT,
    IN direction VARCHAR(7),
    IN max_depth INT
)
BEGIN
    DECLARE eff_max_depth INT;
    DECLARE dir VARCHAR(7);
    SET dir = LOWER(TRIM(direction));
    IF dir NOT IN ('forward', 'reverse') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid direction: must be forward or reverse';
    END IF;
    SET eff_max_depth = IF(max_depth IS NULL OR max_depth <= 0, 5, max_depth);

    IF dir = 'forward' THEN
        WITH RECURSIVE citation_tree AS (
            SELECT 1 AS depth, c.cited_p_id AS p_id,
                   CONCAT(',', start_p_id, ',', c.cited_p_id, ',') AS path
            FROM CITES c
            JOIN PAPER src ON src.p_id = c.citing_p_id
            LEFT JOIN PAPER_WORKFLOW sw ON sw.p_id = src.p_id
            JOIN PAPER target ON target.p_id = c.cited_p_id
            LEFT JOIN PAPER_WORKFLOW tw ON tw.p_id = target.p_id
            WHERE c.citing_p_id = start_p_id
              AND COALESCE(sw.status, 'APPROVED') = 'APPROVED'
              AND COALESCE(tw.status, 'APPROVED') = 'APPROVED'
            UNION ALL
            SELECT ct.depth + 1, c.cited_p_id, CONCAT(ct.path, c.cited_p_id, ',')
            FROM citation_tree ct
            JOIN CITES c ON c.citing_p_id = ct.p_id
            JOIN PAPER p ON p.p_id = c.cited_p_id
            LEFT JOIN PAPER_WORKFLOW w ON w.p_id = p.p_id
            WHERE ct.depth < eff_max_depth
              AND ct.path NOT LIKE CONCAT('%,', c.cited_p_id, ',%')
              AND COALESCE(w.status, 'APPROVED') = 'APPROVED'
        )
        SELECT ct.depth, ct.p_id, p.p_title, ct.path
        FROM citation_tree ct JOIN PAPER p ON p.p_id = ct.p_id
        ORDER BY ct.depth, ct.p_id;
    ELSE
        WITH RECURSIVE citation_tree AS (
            SELECT 1 AS depth, c.citing_p_id AS p_id,
                   CONCAT(',', start_p_id, ',', c.citing_p_id, ',') AS path
            FROM CITES c
            JOIN PAPER src ON src.p_id = c.cited_p_id
            LEFT JOIN PAPER_WORKFLOW sw ON sw.p_id = src.p_id
            JOIN PAPER target ON target.p_id = c.citing_p_id
            LEFT JOIN PAPER_WORKFLOW tw ON tw.p_id = target.p_id
            WHERE c.cited_p_id = start_p_id
              AND COALESCE(sw.status, 'APPROVED') = 'APPROVED'
              AND COALESCE(tw.status, 'APPROVED') = 'APPROVED'
            UNION ALL
            SELECT ct.depth + 1, c.citing_p_id, CONCAT(ct.path, c.citing_p_id, ',')
            FROM citation_tree ct
            JOIN CITES c ON c.cited_p_id = ct.p_id
            JOIN PAPER p ON p.p_id = c.citing_p_id
            LEFT JOIN PAPER_WORKFLOW w ON w.p_id = p.p_id
            WHERE ct.depth < eff_max_depth
              AND ct.path NOT LIKE CONCAT('%,', c.citing_p_id, ',%')
              AND COALESCE(w.status, 'APPROVED') = 'APPROVED'
        )
        SELECT ct.depth, ct.p_id, p.p_title, ct.path
        FROM citation_tree ct JOIN PAPER p ON p.p_id = ct.p_id
        ORDER BY ct.depth, ct.p_id;
    END IF;
END $$
DELIMITER ;
