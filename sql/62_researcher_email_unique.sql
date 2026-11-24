-- Add normalized, case-insensitive researcher email uniqueness.
-- This index is required to safely resolve concurrent researcher submissions.
-- Check for existing normalized duplicates before applying:
-- SELECT LOWER(TRIM(email)) AS normalized_email, COUNT(*) AS duplicate_count
-- FROM RESEARCHER GROUP BY LOWER(TRIM(email)) HAVING COUNT(*) > 1;
-- Resolve any reported duplicates manually before running this migration.

USE research_collaboration_db;

SET @researcher_email_index_exists = (
    SELECT COUNT(*)
    FROM information_schema.statistics
    WHERE table_schema = DATABASE()
      AND table_name = 'RESEARCHER'
      AND index_name = 'uq_researcher_normalized_email'
);
SET @researcher_email_index_sql = IF(
    @researcher_email_index_exists = 0,
    'CREATE UNIQUE INDEX uq_researcher_normalized_email ON RESEARCHER ((LOWER(TRIM(email))))',
    'SELECT 1'
);
PREPARE researcher_email_index_stmt FROM @researcher_email_index_sql;
EXECUTE researcher_email_index_stmt;
DEALLOCATE PREPARE researcher_email_index_stmt;
