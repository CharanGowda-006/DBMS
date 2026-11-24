import re
from difflib import SequenceMatcher

from .reference_parser import normalize_doi


def normalize_name(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def researcher_candidates(author, researchers):
    email = str(author.get("email") or "").strip().casefold()
    name = normalize_name(author.get("name"))
    exact_email = [
        row for row in researchers
        if email and str(row.get("email") or "").strip().casefold() == email
    ]
    if exact_email:
        return exact_email, "email"
    exact_name = [
        row for row in researchers
        if name and normalize_name(row.get("r_name")) == name
    ]
    return exact_name, "name" if exact_name else None


def match_references(references, papers):
    results = []
    for reference in references:
        doi = normalize_doi(reference.get("doi"))
        exact_doi = [
            paper for paper in papers
            if doi and normalize_doi(paper.get("doi")) == doi
        ]
        if exact_doi:
            results.append({
                **reference,
                "match_status": "Matched" if len(exact_doi) == 1 else "Ambiguous match",
                "candidate": exact_doi[0] if len(exact_doi) == 1 else None,
                "candidates": exact_doi if len(exact_doi) > 1 else [],
                "match_reason": "DOI",
            })
            continue
        title = normalize_name(reference.get("title"))
        exact_title = [
            paper for paper in papers
            if title and normalize_name(paper.get("p_title")) == title
            and (
                not reference.get("year")
                or int(paper.get("pub_year") or 0) == int(reference["year"])
            )
        ]
        if len(exact_title) == 1:
            results.append({
                **reference,
                "match_status": "Possible match",
                "candidate": exact_title[0],
                "match_reason": "Normalized title and year",
            })
            continue
        if len(exact_title) > 1:
            results.append({
                **reference,
                "match_status": "Ambiguous match",
                "candidate": None,
                "candidates": exact_title,
                "match_reason": "Duplicate normalized title and year",
            })
            continue
        best, ratio = None, 0.0
        near_matches = []
        if title:
            for paper in papers:
                paper_title = normalize_name(paper.get("p_title"))
                score = SequenceMatcher(None, title, paper_title).ratio()
                if score >= 0.88:
                    near_matches.append((score, paper))
                if score > ratio:
                    best, ratio = paper, score
        near_matches.sort(key=lambda result: result[0], reverse=True)
        if (
            len(near_matches) > 1
            and near_matches[0][0] - near_matches[1][0] < 0.03
        ):
            results.append({
                **reference,
                "match_status": "Ambiguous match",
                "candidate": None,
                "candidates": [paper for _, paper in near_matches],
                "match_reason": "Several similar titles",
            })
            continue
        results.append({
            **reference,
            "match_status": "Possible match" if ratio >= 0.88 else "Unmatched",
            "candidate": best if ratio >= 0.88 else None,
            "candidates": [],
            "match_reason": "Similar title" if ratio >= 0.88 else None,
        })
    return results


def exact_duplicate(title, year, doi, papers):
    normalized_title = normalize_name(title)
    normalized_doi = normalize_doi(doi)
    return [
        paper for paper in papers
        if (
            normalized_doi
            and normalize_doi(paper.get("doi")) == normalized_doi
        ) or (
            normalized_title
            and normalize_name(paper.get("p_title")) == normalized_title
            and int(paper.get("pub_year") or 0) == int(year or 0)
        )
    ]
