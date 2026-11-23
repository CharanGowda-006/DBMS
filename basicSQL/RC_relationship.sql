USE research_collaboration_db;

-- AUTHORS: Researcher <-> Paper (Many-to-Many)
CREATE TABLE AUTHORS (
    r_id INT,
    p_id INT,
    author_order INT NOT NULL,

    PRIMARY KEY (r_id, p_id),
    UNIQUE (p_id, author_order),

    FOREIGN KEY (r_id)
        REFERENCES RESEARCHER(r_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    FOREIGN KEY (p_id)
        REFERENCES PAPER(p_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CHECK (author_order > 0)
) ENGINE=InnoDB;


-- CITES: Paper <-> Paper (Recursive Many-to-Many)
CREATE TABLE CITES (

    citing_p_id INT,
    cited_p_id INT,

    PRIMARY KEY (citing_p_id, cited_p_id),

    FOREIGN KEY (citing_p_id)
        REFERENCES PAPER(p_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    FOREIGN KEY (cited_p_id)
        REFERENCES PAPER(p_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE

    -- CHECK (citing_p_id <> cited_p_id)
) ENGINE=InnoDB;

DELIMITER //

CREATE TRIGGER prevent_self_citation
BEFORE INSERT ON CITES
FOR EACH ROW
BEGIN
    IF NEW.citing_p_id = NEW.cited_p_id THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'A paper cannot cite itself';
    END IF;
END //

DELIMITER ;

DELIMITER //

CREATE TRIGGER prevent_self_citation_update
BEFORE UPDATE ON CITES
FOR EACH ROW
BEGIN
    IF NEW.citing_p_id = NEW.cited_p_id THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'A paper cannot cite itself';
    END IF;
END //

DELIMITER ;



-- HAS_TOPIC: Paper <-> Topic (Many-to-Many)
CREATE TABLE HAS_TOPIC (
    p_id INT,
    t_id INT,

    PRIMARY KEY (p_id, t_id),

    FOREIGN KEY (p_id)
        REFERENCES PAPER(p_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    FOREIGN KEY (t_id)
        REFERENCES TOPIC(t_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB;


-- HAS_KEYWORD: Paper <-> Keyword (Many-to-Many)
CREATE TABLE HAS_KEYWORD (
    p_id INT,
    key_id INT,

    PRIMARY KEY (p_id, key_id),

    FOREIGN KEY (p_id)
        REFERENCES PAPER(p_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    FOREIGN KEY (key_id)
        REFERENCES KEYWORD(key_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB;


--  WORKS_ON: Researcher <-> Project (Many-to-Many)
CREATE TABLE WORKS_ON (
    r_id INT,
    project_id INT,

    PRIMARY KEY (r_id, project_id),

    FOREIGN KEY (r_id)
        REFERENCES RESEARCHER(r_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    FOREIGN KEY (project_id)
        REFERENCES PROJECT(project_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB;


-- USES: Project <-> Dataset (Many-to-Many)
CREATE TABLE USES (
    project_id INT,
    dataset_id INT,

    PRIMARY KEY (project_id, dataset_id),

    FOREIGN KEY (project_id)
        REFERENCES PROJECT(project_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    FOREIGN KEY (dataset_id)
        REFERENCES DATASET(dataset_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB;