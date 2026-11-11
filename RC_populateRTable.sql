
USE research_collaboration_db;

-- ==========================================
-- 1. AUTHORS: Researcher <-> Paper
-- ==========================================

INSERT INTO AUTHORS (r_id, p_id, author_order)
VALUES
(1, 1, 1),
(2, 1, 2),
(2, 2, 1),
(3, 2, 2),
(3, 3, 1),
(4, 4, 1),
(1, 5, 1),
(5, 5, 2),
(2, 6, 1),
(5, 6, 2);


-- ==========================================
-- 2. CITES: Paper <-> Paper
-- ==========================================

INSERT INTO CITES (citing_p_id, cited_p_id)
VALUES
(2, 1),
(5, 1),
(5, 2),
(6, 3),
(6, 2);


-- ==========================================
-- 3. HAS_TOPIC: Paper <-> Topic
-- ==========================================

INSERT INTO HAS_TOPIC (p_id, t_id)
VALUES
(1, 1), (1, 2), (1, 3),
(2, 1), (2, 2), (2, 3),
(3, 1), (3, 4),
(4, 1), (4, 5), (4, 6),
(5, 1), (5, 2), (5, 3),
(6, 1), (6, 4);


-- ==========================================
-- 4. HAS_KEYWORD: Paper <-> Keyword
-- ==========================================

INSERT INTO HAS_KEYWORD (p_id, key_id)
VALUES
(1, 1), (1, 3), (1, 6), (1, 8),
(2, 1), (2, 4), (2, 6), (2, 8),
(3, 2), (3, 5), (3, 6),
(4, 6), (4, 7), (4, 8),
(5, 1), (5, 3), (5, 6), (5, 8),
(6, 2), (6, 5), (6, 6);


-- ==========================================
-- 5. WORKS_ON: Researcher <-> Project
-- ==========================================

INSERT INTO WORKS_ON (r_id, project_id)
VALUES
(1, 1),
(2, 1),
(3, 1),
(4, 2),
(1, 2),
(3, 3),
(5, 3),
(2, 3);


-- ==========================================
-- 6. USES: Project <-> Dataset
-- ==========================================

INSERT INTO USES (project_id, dataset_id)
VALUES
(1, 1),
(1, 2),
(2, 3),
(3, 4);


-- ==========================================
-- 7. VERIFY RECORD COUNTS
-- ==========================================

SELECT 'AUTHORS' AS table_name, COUNT(*) AS total FROM AUTHORS
UNION ALL
SELECT 'CITES', COUNT(*) FROM CITES
UNION ALL
SELECT 'HAS_TOPIC', COUNT(*) FROM HAS_TOPIC
UNION ALL
SELECT 'HAS_KEYWORD', COUNT(*) FROM HAS_KEYWORD
UNION ALL
SELECT 'WORKS_ON', COUNT(*) FROM WORKS_ON
UNION ALL
SELECT 'USES', COUNT(*) FROM USES;


-- ==========================================
-- 8. TEST RELATIONSHIPS: RESEARCHER + PAPER
-- ==========================================

SELECT
    r.r_name,
    p.p_title,
    a.author_order
FROM RESEARCHER r
JOIN AUTHORS a
    ON r.r_id = a.r_id
JOIN PAPER p
    ON a.p_id = p.p_id
ORDER BY p.p_id, a.author_order;
