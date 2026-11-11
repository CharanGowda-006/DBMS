CREATE DATABASE research_collaboration_db;
USE research_collaboration_db;
SHOW DATABASES;

CREATE TABLE RESEARCHER(
	r_id int auto_increment,
    r_name varchar(150) NOT NULL,
    email varchar(255) NOT NULL unique,
    institution varchar(255),
    
    PRIMARY KEY(r_id)
)ENGINE=InnoDB;

CREATE TABLE CONFERENCE(
	c_id int auto_increment,
    c_name varchar(255) not null,
    c_year smallint unsigned not null,
    c_location varchar(255),
    primary key(c_id),
    
    CHECK(c_year>0)
)ENGINE=InnoDB;

CREATE TABLE PAPER(
	p_id int auto_increment,
    p_title varchar(500) not null,
    abstract TEXT,
    pub_year smallint unsigned not null,
    c_id INT,
    
    primary key(p_id),
    
    foreign key (c_id)
		references CONFERENCE(c_id)
        on delete set null
        on update cascade,
        
	check(pub_year>0)
)ENGINE=InnoDB;

CREATE TABLE TOPIC (
    t_id INT AUTO_INCREMENT,
    t_name VARCHAR(150) NOT NULL UNIQUE,

    PRIMARY KEY (t_id)
) ENGINE=InnoDB;

CREATE TABLE KEYWORD (
    key_id INT AUTO_INCREMENT,
    keyword VARCHAR(150) NOT NULL UNIQUE,

    PRIMARY KEY (key_id)
) ENGINE=InnoDB;


CREATE TABLE PROJECT (
    project_id INT AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    description TEXT,

    PRIMARY KEY (project_id)
) ENGINE=InnoDB;

CREATE TABLE DATASET (
    dataset_id INT AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    source VARCHAR(1000) NOT NULL,

    PRIMARY KEY (dataset_id)
) ENGINE=InnoDB;






