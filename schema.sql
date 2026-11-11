-- MySQL dump 10.13  Distrib 8.0.41, for Win64 (x86_64)
--
-- Host: 127.0.0.1    Database: research_collaboration_db
-- ------------------------------------------------------
-- Server version	8.0.41

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `authors`
--

DROP TABLE IF EXISTS `authors`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `authors` (
  `r_id` int NOT NULL,
  `p_id` int NOT NULL,
  `author_order` int NOT NULL,
  PRIMARY KEY (`r_id`,`p_id`),
  UNIQUE KEY `p_id` (`p_id`,`author_order`),
  CONSTRAINT `authors_ibfk_1` FOREIGN KEY (`r_id`) REFERENCES `researcher` (`r_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `authors_ibfk_2` FOREIGN KEY (`p_id`) REFERENCES `paper` (`p_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `authors_chk_1` CHECK ((`author_order` > 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cites`
--

DROP TABLE IF EXISTS `cites`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cites` (
  `citing_p_id` int NOT NULL,
  `cited_p_id` int NOT NULL,
  PRIMARY KEY (`citing_p_id`,`cited_p_id`),
  KEY `cited_p_id` (`cited_p_id`),
  CONSTRAINT `cites_ibfk_1` FOREIGN KEY (`citing_p_id`) REFERENCES `paper` (`p_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `cites_ibfk_2` FOREIGN KEY (`cited_p_id`) REFERENCES `paper` (`p_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8mb4 */ ;
/*!50003 SET character_set_results = utf8mb4 */ ;
/*!50003 SET collation_connection  = utf8mb4_0900_ai_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
/*!50003 CREATE*/ /*!50017 DEFINER=`root`@`localhost`*/ /*!50003 TRIGGER `prevent_self_citation` BEFORE INSERT ON `cites` FOR EACH ROW BEGIN
    IF NEW.citing_p_id = NEW.cited_p_id THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'A paper cannot cite itself';
    END IF;
END */;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8mb4 */ ;
/*!50003 SET character_set_results = utf8mb4 */ ;
/*!50003 SET collation_connection  = utf8mb4_0900_ai_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
/*!50003 CREATE*/ /*!50017 DEFINER=`root`@`localhost`*/ /*!50003 TRIGGER `prevent_self_citation_update` BEFORE UPDATE ON `cites` FOR EACH ROW BEGIN
        IF NEW.citing_p_id = NEW.cited_p_id THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'A paper cannot cite itself';
        END IF;
    END */;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;

--
-- Table structure for table `conference`
--

DROP TABLE IF EXISTS `conference`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `conference` (
  `c_id` int NOT NULL AUTO_INCREMENT,
  `c_name` varchar(255) NOT NULL,
  `c_year` smallint unsigned NOT NULL,
  `c_location` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`c_id`),
  KEY `idx_conference_year` (`c_year`),
  CONSTRAINT `conference_chk_1` CHECK ((`c_year` > 0))
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `dataset`
--

DROP TABLE IF EXISTS `dataset`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dataset` (
  `dataset_id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `source` varchar(1000) NOT NULL,
  PRIMARY KEY (`dataset_id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `has_keyword`
--

DROP TABLE IF EXISTS `has_keyword`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `has_keyword` (
  `p_id` int NOT NULL,
  `key_id` int NOT NULL,
  PRIMARY KEY (`p_id`,`key_id`),
  KEY `idx_keyword_paper` (`key_id`,`p_id`),
  CONSTRAINT `has_keyword_ibfk_1` FOREIGN KEY (`p_id`) REFERENCES `paper` (`p_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `has_keyword_ibfk_2` FOREIGN KEY (`key_id`) REFERENCES `keyword` (`key_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `has_topic`
--

DROP TABLE IF EXISTS `has_topic`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `has_topic` (
  `p_id` int NOT NULL,
  `t_id` int NOT NULL,
  PRIMARY KEY (`p_id`,`t_id`),
  KEY `idx_topic_paper` (`t_id`,`p_id`),
  CONSTRAINT `has_topic_ibfk_1` FOREIGN KEY (`p_id`) REFERENCES `paper` (`p_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `has_topic_ibfk_2` FOREIGN KEY (`t_id`) REFERENCES `topic` (`t_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `keyword`
--

DROP TABLE IF EXISTS `keyword`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `keyword` (
  `key_id` int NOT NULL AUTO_INCREMENT,
  `keyword` varchar(150) NOT NULL,
  PRIMARY KEY (`key_id`),
  UNIQUE KEY `keyword` (`keyword`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `paper`
--

DROP TABLE IF EXISTS `paper`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `paper` (
  `p_id` int NOT NULL AUTO_INCREMENT,
  `p_title` varchar(500) NOT NULL,
  `abstract` text,
  `pub_year` smallint unsigned NOT NULL,
  `c_id` int DEFAULT NULL,
  PRIMARY KEY (`p_id`),
  KEY `c_id` (`c_id`),
  KEY `idx_publication_year` (`pub_year`),
  CONSTRAINT `paper_ibfk_1` FOREIGN KEY (`c_id`) REFERENCES `conference` (`c_id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `paper_chk_1` CHECK ((`pub_year` > 0))
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `project`
--

DROP TABLE IF EXISTS `project`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `project` (
  `project_id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `description` text,
  PRIMARY KEY (`project_id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `researcher`
--

DROP TABLE IF EXISTS `researcher`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `researcher` (
  `r_id` int NOT NULL AUTO_INCREMENT,
  `r_name` varchar(150) NOT NULL,
  `email` varchar(245) NOT NULL,
  `institution` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`r_id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `topic`
--

DROP TABLE IF EXISTS `topic`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `topic` (
  `t_id` int NOT NULL AUTO_INCREMENT,
  `t_name` varchar(150) NOT NULL,
  PRIMARY KEY (`t_id`),
  UNIQUE KEY `t_name` (`t_name`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `uses`
--

DROP TABLE IF EXISTS `uses`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `uses` (
  `project_id` int NOT NULL,
  `dataset_id` int NOT NULL,
  PRIMARY KEY (`project_id`,`dataset_id`),
  KEY `idx_dataset_project` (`dataset_id`,`project_id`),
  CONSTRAINT `uses_ibfk_1` FOREIGN KEY (`project_id`) REFERENCES `project` (`project_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `uses_ibfk_2` FOREIGN KEY (`dataset_id`) REFERENCES `dataset` (`dataset_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `works_on`
--

DROP TABLE IF EXISTS `works_on`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `works_on` (
  `r_id` int NOT NULL,
  `project_id` int NOT NULL,
  PRIMARY KEY (`r_id`,`project_id`),
  KEY `idx_project_researcher` (`project_id`,`r_id`),
  CONSTRAINT `works_on_ibfk_1` FOREIGN KEY (`r_id`) REFERENCES `researcher` (`r_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `works_on_ibfk_2` FOREIGN KEY (`project_id`) REFERENCES `project` (`project_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping routines for database 'research_collaboration_db'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-11-11 22:48:11
