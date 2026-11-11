# 5-Minute Demonstration Script & Screenshot Capture Guide

This guide provides a structured script for presenting the project during evaluation, along with an exact checklist of pages and SQL queries to capture for the report submission.

---

## 5-Minute Evaluation Presentation Script

### Minute 0:00 - 1:00 | Introduction & Database Architecture (Home Page)
- **Action**: Launch Streamlit app (`streamlit run app/Home.py`). Open the **Home** page.
- **Narrative**:
  > *"Good morning/afternoon. Today I present our Academic Research Collaboration & Discovery Portal. Our goal was to push core analytical computation directly into MySQL using views, triggers, and stored procedures, leaving the Streamlit UI as a clean presentation layer. On our landing page, we see our 13 relational tables and verified row counts across entities and many-to-many junction tables."*
- **Highlight**: Point out the 13 table counts matching the schema specification.

---

### Minute 1:00 - 2:00 | Analytical Overview & KPIs (Page 1: Overview)
- **Action**: Navigate to `1_Overview.py` in the sidebar.
- **Narrative**:
  > *"On the Overview page, six real-time KPI metrics summarize the repository: Papers, Researchers, Conferences, Topics, Projects, and Datasets. The analytical bar charts are powered entirely by database views (`v_papers_per_year`, `v_papers_per_conference`, `v_papers_per_topic`). Notice how `v_papers_per_conference` accounts for conferences with zero papers and handles papers without an assigned venue."*
- **Highlight**: Hover over the publication trends and topic distribution bars.

---

### Minute 2:00 - 3:00 | Unified Search & Deep Paper Inspection (Page 2: Search)
- **Action**: Navigate to `2_Search.py`. Enter `"Computer Vision"` in the search input box.
- **Narrative**:
  > *"Our unified search stored procedure (`sp_search`) scans publication titles, assigned topics, and keywords. Searching 'Computer Vision' simultaneously discovers matched papers, their author researchers, conferences, associated research projects, and benchmark datasets. Selecting a paper expands its full metadata, including author order, abstract, conference venue, topics, and keywords."*
- **Highlight**: Select Paper #1 to display the ordered authors and tags.

---

### Minute 3:00 - 4:00 | Collaboration Discovery & Jaccard Similarity (Page 3: Insights)
- **Action**: Navigate to `3_Insights.py`.
- **Narrative**:
  > *"The Insights module provides two key capabilities:*
  > *1. **Potential Collaborators**: Identifies researchers sharing 2 or more topics across their authored works. It highlights whether they have already co-authored papers or represent new cross-institutional opportunities.*
  > *2. **Publication Similarity**: Computes a weighted Jaccard score combining 40% topic overlap and 60% keyword overlap. Adjusting the slider filters candidate papers, with our disclaimer stating this represents potential overlap rather than plagiarism."*
- **Highlight**: Drag the similarity slider to 0.6 to isolate high-overlap pairs like (1, 5) and (3, 6).

---

### Minute 4:00 - 5:00 | Graph Citation Traversal & Data Integrity (Pages 4, 6 & 7)
- **Action**: Navigate to `4_Citations.py`. Select Paper #6, direction `forward`, depth `3`.
- **Narrative**:
  > *"Our recursive citation stored procedure (`sp_citations`) navigates multi-hop citation trees. Paper 6 cites Paper 2 and 3 at depth 1, and reaches Paper 1 at depth 2. An internal path accumulator prevents infinite recursion even in cyclic citation graphs.*
  > *Finally, our registration forms in Pages 6 and 7 enforce strict referential constraints, atomic multi-table transactions with rollback, and custom MySQL triggers blocking self-citations."*
- **Highlight**: Show the indented hierarchical citation view with traversal paths.

---

## Screenshot Capture Checklist for Final Report

Capture screenshots of the following pages and queries for your report document:

| # | Item to Capture | Page / Location | Recommended Input / State |
|---|---|---|---|
| **1** | Database Verification & Tables | `app/Home.py` | Full page showing row count table (13 tables, 99 total records) |
| **2** | Analytical Dashboard | `app/pages/1_Overview.py` | 6 KPI metric cards + 3 bar charts |
| **3** | Unified Cross-Entity Search | `app/pages/2_Search.py` | Search term: `"Computer Vision"`, showing grouped entity tables |
| **4** | Paper Metadata Inspector | `app/pages/2_Search.py` | Paper #1 expanded showing ordered authors and tags |
| **5** | Collaboration Discovery Table | `app/pages/3_Insights.py` (Tab 1) | Table showing 6 researcher pairs and co-author status |
| **6** | Jaccard Similarity & Expander | `app/pages/3_Insights.py` (Tab 2) | Slider set to `0.30`, expander open showing shared topics & keywords |
| **7** | Forward Citation Traversal | `app/pages/4_Citations.py` | Root: Paper #6, Direction: `Forward`, Depth: `3`, showing dashed hierarchy |
| **8** | Project Team & Shared Resources | `app/pages/5_Projects.py` | Tab 1 with Project #1 team, Tab 2 cross-project sharing |
| **9** | Self-Citation Error Message | `app/pages/7_Add_Paper.py` (Tab 2) | Selecting Paper #1 as both Citing and Cited, showing friendly error message |
| **10** | Workbench / SQL Verification | MySQL Workbench | Result of `SELECT * FROM v_paper_similarity LIMIT 5;` |
