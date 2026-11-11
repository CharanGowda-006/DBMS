-- Phase 1: Database Verification Script
-- Target Database: research_collaboration_db

USE research_collaboration_db;

-- 1. SHOW TABLES: confirm all 13 tables exist
SHOW TABLES;

-- 2. Row counts for all 13 tables
SELECT 'RESEARCHER' AS table_name, COUNT(*) AS row_count FROM RESEARCHER
UNION ALL
SELECT 'CONFERENCE', COUNT(*) FROM CONFERENCE
UNION ALL
SELECT 'PAPER', COUNT(*) FROM PAPER
UNION ALL
SELECT 'TOPIC', COUNT(*) FROM TOPIC
UNION ALL
SELECT 'KEYWORD', COUNT(*) FROM KEYWORD
UNION ALL
SELECT 'PROJECT', COUNT(*) FROM PROJECT
UNION ALL
SELECT 'DATASET', COUNT(*) FROM DATASET
UNION ALL
SELECT 'AUTHORS', COUNT(*) FROM AUTHORS
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

-- 3. Run RESEARCHER-AUTHORS-PAPER join (r_name, p_title, author_order)
SELECT
    r.r_name,
    p.p_title,
    a.author_order
FROM RESEARCHER r
JOIN AUTHORS a ON r.r_id = a.r_id
JOIN PAPER p ON a.p_id = p.p_id
ORDER BY p.p_id, a.author_order
LIMIT 20;

-- 4. Trigger test inside transaction with ROLLBACK
-- (a) INSERT self-citation: must be rejected with SQLSTATE '45000' ('A paper cannot cite itself')
START TRANSACTION;
-- The following statement should fail:
-- INSERT INTO CITES (citing_p_id, cited_p_id) VALUES (1, 1);
ROLLBACK;

-- (b) UPDATE self-citation: must be rejected with SQLSTATE '45000' ('A paper cannot cite itself')
START TRANSACTION;
-- The following statement should fail:
-- UPDATE CITES SET cited_p_id = citing_p_id WHERE citing_p_id = 2 AND cited_p_id = 1;
ROLLBACK;

-- Verify CITES count remains exactly 5
SELECT COUNT(*) AS cites_count_after_tests FROM CITES;

