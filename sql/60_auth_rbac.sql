-- Additive authentication, ownership, publication workflow, and audit schema.
-- Legacy papers without a PAPER_WORKFLOW row are treated as APPROVED.

USE research_collaboration_db;

CREATE TABLE IF NOT EXISTS APP_USER (
    user_id INT NOT NULL AUTO_INCREMENT,
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('STUDENT', 'TEACHER', 'ADMIN') NOT NULL DEFAULT 'STUDENT',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    researcher_id INT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id),
    UNIQUE KEY uq_app_user_email (email),
    KEY idx_app_user_role_active (role, is_active),
    CONSTRAINT fk_app_user_researcher FOREIGN KEY (researcher_id)
        REFERENCES RESEARCHER (r_id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS PAPER_OWNERSHIP (
    p_id INT NOT NULL,
    owner_user_id INT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (p_id),
    KEY idx_paper_ownership_owner (owner_user_id),
    CONSTRAINT fk_paper_ownership_paper FOREIGN KEY (p_id)
        REFERENCES PAPER (p_id) ON DELETE CASCADE,
    CONSTRAINT fk_paper_ownership_user FOREIGN KEY (owner_user_id)
        REFERENCES APP_USER (user_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS PROJECT_OWNERSHIP (
    project_id INT NOT NULL,
    owner_user_id INT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (project_id),
    KEY idx_project_ownership_owner (owner_user_id),
    CONSTRAINT fk_project_ownership_project FOREIGN KEY (project_id)
        REFERENCES PROJECT (project_id) ON DELETE CASCADE,
    CONSTRAINT fk_project_ownership_user FOREIGN KEY (owner_user_id)
        REFERENCES APP_USER (user_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS PAPER_WORKFLOW (
    p_id INT NOT NULL,
    status ENUM('PENDING', 'APPROVED', 'REJECTED', 'ARCHIVED') NOT NULL,
    submitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (p_id),
    KEY idx_paper_workflow_status_submitted (status, submitted_at),
    CONSTRAINT fk_paper_workflow_paper FOREIGN KEY (p_id)
        REFERENCES PAPER (p_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS PUBLICATION_REVIEW (
    review_id BIGINT NOT NULL AUTO_INCREMENT,
    p_id INT NOT NULL,
    reviewer_user_id INT NOT NULL,
    decision ENUM('APPROVED', 'REJECTED') NOT NULL,
    remarks TEXT NULL,
    reviewed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (review_id),
    KEY idx_publication_review_paper_time (p_id, reviewed_at),
    KEY idx_publication_review_reviewer (reviewer_user_id),
    CONSTRAINT fk_publication_review_paper FOREIGN KEY (p_id)
        REFERENCES PAPER (p_id) ON DELETE CASCADE,
    CONSTRAINT fk_publication_review_reviewer FOREIGN KEY (reviewer_user_id)
        REFERENCES APP_USER (user_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS AUDIT_LOG (
    audit_id BIGINT NOT NULL AUTO_INCREMENT,
    actor_user_id INT NULL,
    action VARCHAR(64) NOT NULL,
    entity_type VARCHAR(64) NOT NULL,
    entity_id BIGINT NULL,
    old_values JSON NULL,
    new_values JSON NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (audit_id),
    KEY idx_audit_log_action_time (action, created_at),
    KEY idx_audit_log_actor_time (actor_user_id, created_at),
    CONSTRAINT fk_audit_log_actor FOREIGN KEY (actor_user_id)
        REFERENCES APP_USER (user_id) ON DELETE SET NULL
) ENGINE=InnoDB;
