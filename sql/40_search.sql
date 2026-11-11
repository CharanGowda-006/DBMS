-- Phase 6: Unified Search Procedure
-- Procedure: sp_search(IN term VARCHAR(100))
-- Output: (result_type, ref_id, label, detail)
-- Rules:
--   Match t_name, keyword, p_title with LIKE CONCAT('%', term, '%')
--   UNION ALL across paper, researcher, conference, project, dataset
--   DISTINCT within each type
--   Blank or whitespace term returns empty set

USE research_collaboration_db;

DROP PROCEDURE IF EXISTS sp_search;

DELIMITER $$

CREATE PROCEDURE sp_search(IN term VARCHAR(100))
BEGIN
    DECLARE clean_term VARCHAR(100);
    SET clean_term = TRIM(term);

    IF clean_term IS NULL OR clean_term = '' THEN
        -- Blank or whitespace returns 0 rows
        SELECT CAST(NULL AS CHAR(20)) AS result_type,
               CAST(NULL AS SIGNED) AS ref_id,
               CAST(NULL AS CHAR(500)) AS label,
               CAST(NULL AS CHAR(500)) AS detail
        WHERE 1 = 0;
    ELSE
        WITH matched_papers AS (
            SELECT
                m.p_id,
                m.p_title,
                m.c_id,
                GROUP_CONCAT(DISTINCT m.match_reason ORDER BY m.match_reason SEPARATOR ', ') AS match_detail
            FROM (
                SELECT p.p_id, p.p_title, p.c_id, 'matched via title' AS match_reason
                FROM PAPER p
                WHERE p.p_title LIKE CONCAT('%', clean_term, '%')
                UNION ALL
                SELECT p.p_id, p.p_title, p.c_id, 'matched via topic' AS match_reason
                FROM PAPER p
                JOIN HAS_TOPIC ht ON p.p_id = ht.p_id
                JOIN TOPIC t ON ht.t_id = t.t_id
                WHERE t.t_name LIKE CONCAT('%', clean_term, '%')
                UNION ALL
                SELECT p.p_id, p.p_title, p.c_id, 'matched via keyword' AS match_reason
                FROM PAPER p
                JOIN HAS_KEYWORD hk ON p.p_id = hk.p_id
                JOIN KEYWORD k ON hk.key_id = k.key_id
                WHERE k.keyword LIKE CONCAT('%', clean_term, '%')
            ) m
            GROUP BY m.p_id, m.p_title, m.c_id
        ),
        matched_researchers AS (
            SELECT DISTINCT r.r_id, r.r_name, r.institution
            FROM matched_papers mp
            JOIN AUTHORS a ON mp.p_id = a.p_id
            JOIN RESEARCHER r ON a.r_id = r.r_id
        ),
        matched_projects AS (
            SELECT DISTINCT pr.project_id, pr.name
            FROM matched_researchers mr
            JOIN WORKS_ON wo ON mr.r_id = wo.r_id
            JOIN PROJECT pr ON wo.project_id = pr.project_id
        )
        SELECT 'paper' AS result_type, mp.p_id AS ref_id, mp.p_title AS label, mp.match_detail AS detail
        FROM matched_papers mp
        UNION ALL
        SELECT 'researcher' AS result_type, mr.r_id AS ref_id, mr.r_name AS label, CONCAT('Author of matched paper; ', COALESCE(mr.institution, '')) AS detail
        FROM matched_researchers mr
        UNION ALL
        SELECT DISTINCT 'conference' AS result_type, c.c_id AS ref_id, c.c_name AS label, CONCAT(c.c_year, ', ', COALESCE(c.c_location, '')) AS detail
        FROM matched_papers mp
        JOIN CONFERENCE c ON mp.c_id = c.c_id
        WHERE mp.c_id IS NOT NULL
        UNION ALL
        SELECT 'project' AS result_type, mpj.project_id AS ref_id, mpj.name AS label, 'related via researcher' AS detail
        FROM matched_projects mpj
        UNION ALL
        SELECT DISTINCT 'dataset' AS result_type, d.dataset_id AS ref_id, d.name AS label, 'related via project' AS detail
        FROM matched_projects mpj
        JOIN USES u ON mpj.project_id = u.project_id
        JOIN DATASET d ON u.dataset_id = d.dataset_id;
    END IF;
END $$

DELIMITER ;
