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
-- Dumping data for table `authors`
--

LOCK TABLES `authors` WRITE;
/*!40000 ALTER TABLE `authors` DISABLE KEYS */;
INSERT INTO `authors` VALUES (1,1,1),(2,1,2),(2,2,1),(3,2,2),(3,3,1),(4,4,1),(1,5,1),(5,5,2),(2,6,1),(5,6,2);
/*!40000 ALTER TABLE `authors` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping data for table `cites`
--

LOCK TABLES `cites` WRITE;
/*!40000 ALTER TABLE `cites` DISABLE KEYS */;
INSERT INTO `cites` VALUES (2,1),(5,1),(5,2),(6,2),(6,3);
/*!40000 ALTER TABLE `cites` ENABLE KEYS */;
UNLOCK TABLES;
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
-- Dumping data for table `conference`
--

LOCK TABLES `conference` WRITE;
/*!40000 ALTER TABLE `conference` DISABLE KEYS */;
INSERT INTO `conference` VALUES (1,'International Conference on Machine Learning',2024,'Vienna'),(2,'IEEE Conference on Computer Vision',2025,'Seattle'),(3,'International Conference on Data Science',2025,'Bangalore');
/*!40000 ALTER TABLE `conference` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping data for table `dataset`
--

LOCK TABLES `dataset` WRITE;
/*!40000 ALTER TABLE `dataset` DISABLE KEYS */;
INSERT INTO `dataset` VALUES (1,'ImageNet','https://www.image-net.org/'),(2,'COCO Dataset','https://cocodataset.org/'),(3,'MIMIC-III','https://physionet.org/'),(4,'GLUE Benchmark','https://gluebenchmark.com/');
/*!40000 ALTER TABLE `dataset` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping data for table `has_keyword`
--

LOCK TABLES `has_keyword` WRITE;
/*!40000 ALTER TABLE `has_keyword` DISABLE KEYS */;
INSERT INTO `has_keyword` VALUES (1,1),(1,3),(1,6),(1,8),(2,1),(2,4),(2,6),(2,8),(3,2),(3,5),(3,6),(4,6),(4,7),(4,8),(5,1),(5,3),(5,6),(5,8),(6,2),(6,5),(6,6);
/*!40000 ALTER TABLE `has_keyword` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping data for table `has_topic`
--

LOCK TABLES `has_topic` WRITE;
/*!40000 ALTER TABLE `has_topic` DISABLE KEYS */;
INSERT INTO `has_topic` VALUES (1,1),(1,2),(1,3),(2,1),(2,2),(2,3),(3,1),(3,4),(4,1),(4,5),(4,6),(5,1),(5,2),(5,3),(6,1),(6,4);
/*!40000 ALTER TABLE `has_topic` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping data for table `keyword`
--

LOCK TABLES `keyword` WRITE;
/*!40000 ALTER TABLE `keyword` DISABLE KEYS */;
INSERT INTO `keyword` VALUES (1,'CNN'),(8,'Feature Extraction'),(3,'Image Classification'),(7,'Medical Prediction'),(6,'Neural Networks'),(4,'Object Detection'),(5,'Text Classification'),(2,'Transformers');
/*!40000 ALTER TABLE `keyword` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping data for table `paper`
--

LOCK TABLES `paper` WRITE;
/*!40000 ALTER TABLE `paper` DISABLE KEYS */;
INSERT INTO `paper` VALUES (1,'Deep Learning for Image Classification','A study of deep neural networks for image classification.',2024,1),(2,'Convolutional Neural Networks for Object Detection','An investigation of CNN architectures for object detection.',2025,2),(3,'Natural Language Processing Using Transformers','A study of transformer architectures for NLP tasks.',2025,3),(4,'Applications of Machine Learning in Healthcare','Machine learning techniques applied to healthcare prediction.',2024,1),(5,'Advanced Image Recognition Using Deep Learning','An approach to image recognition using deep learning models.',2025,2),(6,'Transformer-Based Text Classification','Text classification using transformer-based architectures.',2025,3);
/*!40000 ALTER TABLE `paper` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping data for table `project`
--

LOCK TABLES `project` WRITE;
/*!40000 ALTER TABLE `project` DISABLE KEYS */;
INSERT INTO `project` VALUES (1,'AI-Based Image Analysis','Research project focused on image recognition and classification.'),(2,'Intelligent Healthcare System','Research project focused on healthcare prediction using ML.'),(3,'NLP Research Platform','Research project focused on transformer-based NLP applications.');
/*!40000 ALTER TABLE `project` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping data for table `researcher`
--

LOCK TABLES `researcher` WRITE;
/*!40000 ALTER TABLE `researcher` DISABLE KEYS */;
INSERT INTO `researcher` VALUES (1,'Alice Johnson','alice@example.com','RV College of Engineering'),(2,'Bob Smith','bob@example.com','IISc Bangalore'),(3,'Charlie Brown','charlie@example.com','NITK Surathkal'),(4,'David Wilson','david@example.com','RV College of Engineering'),(5,'Emma Davis','emma@example.com','IIT Madras');
/*!40000 ALTER TABLE `researcher` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping data for table `topic`
--

LOCK TABLES `topic` WRITE;
/*!40000 ALTER TABLE `topic` DISABLE KEYS */;
INSERT INTO `topic` VALUES (3,'Computer Vision'),(6,'Data Science'),(2,'Deep Learning'),(5,'Healthcare AI'),(1,'Machine Learning'),(4,'Natural Language Processing');
/*!40000 ALTER TABLE `topic` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping data for table `uses`
--

LOCK TABLES `uses` WRITE;
/*!40000 ALTER TABLE `uses` DISABLE KEYS */;
INSERT INTO `uses` VALUES (1,1),(1,2),(2,3),(3,4);
/*!40000 ALTER TABLE `uses` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping data for table `works_on`
--

LOCK TABLES `works_on` WRITE;
/*!40000 ALTER TABLE `works_on` DISABLE KEYS */;
INSERT INTO `works_on` VALUES (1,1),(1,2),(2,1),(2,3),(3,1),(3,3),(4,2),(5,3);
/*!40000 ALTER TABLE `works_on` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-11-11 22:48:32
