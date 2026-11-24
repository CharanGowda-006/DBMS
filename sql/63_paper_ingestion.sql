-- Additive storage for reviewed Smart Paper Import metadata and private PDF uploads.
-- Existing publication, workflow, and seed records are not modified.

USE research_collaboration_db;

CREATE TABLE IF NOT EXISTS PAPER_INGESTION (
    p_id INT NOT NULL,
    doi VARCHAR(255) NULL,
    original_filename VARCHAR(255) NOT NULL,
    storage_key CHAR(36) NOT NULL,
    sha256 CHAR(64) NOT NULL,
    file_size INT UNSIGNED NOT NULL,
    parser_version VARCHAR(32) NOT NULL,
    extracted_metadata JSON NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (p_id),
    UNIQUE KEY uq_paper_ingestion_doi (doi),
    UNIQUE KEY uq_paper_ingestion_storage_key (storage_key),
    CONSTRAINT fk_paper_ingestion_paper FOREIGN KEY (p_id)
        REFERENCES PAPER (p_id) ON DELETE CASCADE
) ENGINE=InnoDB;
