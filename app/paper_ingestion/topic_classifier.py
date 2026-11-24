import re
import unicodedata


_EXISTING_TOPIC_PHRASES = {
    "machine learning": (
        "machine learning",
        "supervised learning",
        "unsupervised learning",
        "predictive modeling",
        "predictive modelling",
        "classification model",
    ),
    "deep learning": (
        "deep learning",
        "neural network",
        "neural networks",
        "convolutional neural network",
        "transformer model",
    ),
    "computer vision": (
        "computer vision",
        "image recognition",
        "image classification",
        "object detection",
        "visual recognition",
    ),
    "natural language processing": (
        "natural language processing",
        "text mining",
        "text classification",
        "named entity recognition",
        "language model",
        "language models",
    ),
    "healthcare ai": (
        "healthcare ai",
        "medical ai",
        "clinical decision support",
        "medical imaging",
        "patient data",
    ),
    "data science": (
        "data science",
        "data analytics",
        "data analysis",
        "data mining",
        "statistical analysis",
        "data-driven",
    ),
}

_PROPOSED_TOPIC_PHRASES = {
    "Database Management Systems": (
        "database management system",
        "database management systems",
        "relational database",
        "relational databases",
        "relational data model",
        "sql database",
        "sql databases",
    ),
    "Citation Networks": (
        "citation network",
        "citation networks",
        "citation graph",
        "citation graphs",
        "scholarly citation network",
    ),
    "Entity Resolution": (
        "entity resolution",
        "record linkage",
        "identity resolution",
        "entity matching",
    ),
    "Research Information Systems": (
        "academic information system",
        "academic information systems",
        "research information system",
        "research information systems",
        "scholarly metadata",
        "academic research platform",
        "academic research platforms",
    ),
    "Metadata Management": (
        "metadata extraction",
        "metadata management",
        "metadata curation",
        "publication metadata",
    ),
}


def _normalize(value):
    value = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def _source_fields(title, abstract, keywords):
    return {
        "title": _normalize(title),
        "abstract": _normalize(abstract),
        "keywords": _normalize(" ".join(str(item) for item in (keywords or []))),
    }


def _phrase_matches(phrases, fields):
    matches = []
    for phrase in phrases:
        normalized = _normalize(phrase)
        if not normalized:
            continue
        pattern = rf"(?<![a-z0-9]){re.escape(normalized)}(?![a-z0-9])"
        found_in = [
            field_name for field_name, text in fields.items()
            if re.search(pattern, text)
        ]
        if found_in:
            matches.append({"phrase": phrase, "found_in": found_in})
    return matches


def classify_topics(title, keywords, topics, abstract=""):
    """Suggest existing topics and separately identify relevant new-topic candidates."""
    fields = _source_fields(title, abstract, keywords)
    existing = []
    for topic in topics:
        name = str(topic["t_name"]).strip()
        normalized = _normalize(name)
        aliases = _EXISTING_TOPIC_PHRASES.get(
            normalized,
            _PROPOSED_TOPIC_PHRASES.get(name, ()),
        )
        phrases = tuple(dict.fromkeys((name, *aliases)))
        matched = _phrase_matches(phrases, fields)
        if matched:
            existing.append({
                "t_id": int(topic["t_id"]),
                "t_name": name,
                "reason": "Matched research terms: "
                + ", ".join(item["phrase"] for item in matched),
                "matched_phrases": matched,
            })

    proposed = []
    existing_names = {_normalize(topic["t_name"]) for topic in topics}
    for name, phrases in _PROPOSED_TOPIC_PHRASES.items():
        if _normalize(name) in existing_names:
            continue
        matched = _phrase_matches(phrases, fields)
        if matched:
            proposed.append({
                "t_name": name,
                "reason": "Related terms found in "
                + ", ".join(dict.fromkeys(
                    field
                    for item in matched
                    for field in item["found_in"]
                ))
                + ": "
                + ", ".join(item["phrase"] for item in matched),
                "matched_phrases": matched,
            })
    return {"existing": existing, "proposed": proposed}


def suggest_topics(title, keywords, topics, abstract=""):
    """Backward-compatible helper returning only suggestions backed by TOPIC rows."""
    return classify_topics(title, keywords, topics, abstract)["existing"]
