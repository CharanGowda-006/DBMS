use research_collaboration_db;

INSERT INTO RESEARCHER (r_id, r_name, email, institution)
VALUES
(1, 'Alice Johnson', 'alice@example.com', 'RV College of Engineering'),
(2, 'Bob Smith', 'bob@example.com', 'IISc Bangalore'),
(3, 'Charlie Brown', 'charlie@example.com', 'NITK Surathkal'),
(4, 'David Wilson', 'david@example.com', 'RV College of Engineering'),
(5, 'Emma Davis', 'emma@example.com', 'IIT Madras');

INSERT INTO CONFERENCE (c_id, c_name, c_year, c_location)
VALUES
(1, 'International Conference on Machine Learning', 2024, 'Vienna'),
(2, 'IEEE Conference on Computer Vision', 2025, 'Seattle'),
(3, 'International Conference on Data Science', 2025, 'Bangalore');

INSERT INTO PAPER (p_id, p_title, abstract, pub_year, c_id)
VALUES
(1, 'Deep Learning for Image Classification',
 'A study of deep neural networks for image classification.',
 2024, 1),

(2, 'Convolutional Neural Networks for Object Detection',
 'An investigation of CNN architectures for object detection.',
 2025, 2),

(3, 'Natural Language Processing Using Transformers',
 'A study of transformer architectures for NLP tasks.',
 2025, 3),

(4, 'Applications of Machine Learning in Healthcare',
 'Machine learning techniques applied to healthcare prediction.',
 2024, 1),

(5, 'Advanced Image Recognition Using Deep Learning',
 'An approach to image recognition using deep learning models.',
 2025, 2),

(6, 'Transformer-Based Text Classification',
 'Text classification using transformer-based architectures.',
 2025, 3);
 
 INSERT INTO KEYWORD (key_id, keyword)
VALUES
(1, 'CNN'),
(2, 'Transformers'),
(3, 'Image Classification'),
(4, 'Object Detection'),
(5, 'Text Classification'),
(6, 'Neural Networks'),
(7, 'Medical Prediction'),
(8, 'Feature Extraction');

INSERT INTO TOPIC (t_id, t_name)
VALUES
(1, 'Machine Learning'),
(2, 'Deep Learning'),
(3, 'Computer Vision'),
(4, 'Natural Language Processing'),
(5, 'Healthcare AI'),
(6, 'Data Science');

INSERT INTO PROJECT (project_id, name, description)
VALUES
(1, 'AI-Based Image Analysis',
 'Research project focused on image recognition and classification.'),

(2, 'Intelligent Healthcare System',
 'Research project focused on healthcare prediction using ML.'),

(3, 'NLP Research Platform',
 'Research project focused on transformer-based NLP applications.');
 
 INSERT INTO DATASET (dataset_id, name, source)
VALUES
(1, 'ImageNet', 'https://www.image-net.org/'),
(2, 'COCO Dataset', 'https://cocodataset.org/'),
(3, 'MIMIC-III', 'https://physionet.org/'),
(4, 'GLUE Benchmark', 'https://gluebenchmark.com/');


SELECT * FROM RESEARCHER;
SELECT * FROM CONFERENCE;
SELECT * FROM PAPER;
SELECT * FROM TOPIC;
SELECT * FROM KEYWORD;
SELECT * FROM PROJECT;
SELECT * FROM DATASET;