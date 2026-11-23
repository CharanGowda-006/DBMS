USE research_collaboration_db;

-- Topic-based paper search
CREATE INDEX idx_topic_paper
ON HAS_TOPIC(t_id, p_id);

-- Keyword-based paper search
CREATE INDEX idx_keyword_paper
ON HAS_KEYWORD(key_id, p_id);

-- Reverse citation lookup
CREATE INDEX idx_cited_paper
ON CITES(cited_p_id, citing_p_id);

-- Find researchers working on a project
CREATE INDEX idx_project_researcher
ON WORKS_ON(project_id, r_id);

-- Find projects using a dataset
CREATE INDEX idx_dataset_project
ON USES(dataset_id, project_id);

-- Search papers by publication year
CREATE INDEX idx_publication_year
ON PAPER(pub_year);

-- Search conferences by year
CREATE INDEX idx_conference_year
ON CONFERENCE(c_year);

SHOW tables;
SELECT
    TABLE_NAME,
    COLUMN_NAME,
    CONSTRAINT_NAME,
    REFERENCED_TABLE_NAME,
    REFERENCED_COLUMN_NAME
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'research_collaboration_db'
AND REFERENCED_TABLE_NAME IS NOT NULL
ORDER BY TABLE_NAME;