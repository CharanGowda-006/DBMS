-- Phase 5: Citation Traversal Procedure
-- Procedure: sp_citations(IN start_p_id INT, IN direction VARCHAR(7), IN max_depth INT)
-- Output: depth, p_id, p_title, path
-- Cycle guard: comma-delimited path (e.g. ,1,3,4,) to prevent 1 matching 11
-- Direction: 'forward' (papers cited by start_p_id), 'reverse' (papers citing start_p_id)
-- Default max_depth: 5 if NULL or <= 0

USE research_collaboration_db;

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
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Invalid direction: must be forward or reverse';
    END IF;

    SET eff_max_depth = IF(max_depth IS NULL OR max_depth <= 0, 5, max_depth);

    IF dir = 'forward' THEN
        -- Papers cited by start_p_id (outgoing citations)
        WITH RECURSIVE citation_tree AS (
            -- Base case: depth 1
            SELECT
                1 AS depth,
                c.cited_p_id AS p_id,
                CONCAT(',', start_p_id, ',', c.cited_p_id, ',') AS path
            FROM CITES c
            WHERE c.citing_p_id = start_p_id

            UNION ALL

            -- Recursive step
            SELECT
                ct.depth + 1 AS depth,
                c.cited_p_id AS p_id,
                CONCAT(ct.path, c.cited_p_id, ',') AS path
            FROM citation_tree ct
            JOIN CITES c ON c.citing_p_id = ct.p_id
            WHERE ct.depth < eff_max_depth
              AND ct.path NOT LIKE CONCAT('%,', c.cited_p_id, ',%')
        )
        SELECT
            ct.depth,
            ct.p_id,
            p.p_title,
            ct.path
        FROM citation_tree ct
        JOIN PAPER p ON ct.p_id = p.p_id
        ORDER BY ct.depth, ct.p_id;

    ELSE
        -- Papers citing start_p_id (incoming / reverse citations)
        WITH RECURSIVE citation_tree AS (
            -- Base case: depth 1
            SELECT
                1 AS depth,
                c.citing_p_id AS p_id,
                CONCAT(',', start_p_id, ',', c.citing_p_id, ',') AS path
            FROM CITES c
            WHERE c.cited_p_id = start_p_id

            UNION ALL

            -- Recursive step
            SELECT
                ct.depth + 1 AS depth,
                c.citing_p_id AS p_id,
                CONCAT(ct.path, c.citing_p_id, ',') AS path
            FROM citation_tree ct
            JOIN CITES c ON c.cited_p_id = ct.p_id
            WHERE ct.depth < eff_max_depth
              AND ct.path NOT LIKE CONCAT('%,', c.citing_p_id, ',%')
        )
        SELECT
            ct.depth,
            ct.p_id,
            p.p_title,
            ct.path
        FROM citation_tree ct
        JOIN PAPER p ON ct.p_id = p.p_id
        ORDER BY ct.depth, ct.p_id;

    END IF;
END $$

DELIMITER ;

