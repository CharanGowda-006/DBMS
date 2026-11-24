import re
import unicodedata

from .reference_parser import normalize_doi, parse_references


_EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
_YEAR = re.compile(r"\b(18\d{2}|19\d{2}|20\d{2}|2100)\b")
_SECTION = re.compile(
    r"(?i)^\s*(?:(?:\d+(?:\.\d+)*|[ivxlc]+)[.)]?\s+)?"
    r"(?:introduction|background|related work|literature review|"
    r"problem formulation|methodology|methods|materials and methods|"
    r"proposed method|approach|experiments|results|discussion|"
    r"conclusion|conclusions|future work|acknowledg(?:e)?ments)\b"
    r"\s*[:.]?\s*$"
)
_ABSTRACT_LINE = re.compile(
    r"(?i)^\s*abstract\b\s*(?:[—–:\-\u00ad\u037e]\s*)?(.*)$"
)
_KEYWORDS_LINE = re.compile(
    r"(?i)^\s*(?:index\s+terms?|author\s+keywords?|keywords?)"
    r"\s*(?:[—–:\-\u00ad\u037e]\s*)?(.*)$"
)
_DOI = re.compile(
    r"(?:doi\s*:\s*|https?://(?:dx\.)?doi\.org/)?"
    r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b",
    re.IGNORECASE,
)
_AFFILIATION = re.compile(
    r"\b(university|universit[eé]|institute|college|department|laboratory|"
    r"school of|research center|research centre|faculty of|corresponding author|"
    r"affiliation)\b",
    re.IGNORECASE,
)
_TITLE_NOISE = re.compile(
    r"(?i)^(?:"
    r"synthetic\s+(?:test|sample|demo)\b.*|"
    r"(?:test|sample|demo)\s+(?:document|paper|file)\b.*|"
    r"generated\s+(?:test|sample|document)\b.*|"
    r"copyright\b.*|©.*|published by\b.*|"
    r"proceedings of\b.*|ieee\b.*|acm\b.*|"
    r"vol(?:ume)?\.?\s*\d+.*|"
    r"page\s+\d+(?:\s+of\s+\d+)?"
    r")$"
)
_NAME_TOKEN = re.compile(
    r"^(?:[A-Z]\.?|[A-Z][A-Za-z'’.-]*|"
    r"(?:de|del|van|von|da|di|la|le|bin|al))$"
)
_PERSON_SPLIT = re.compile(r"\s*(?:;|&)\s*", re.IGNORECASE)


def _clean(value):
    value = unicodedata.normalize("NFKC", value or "")
    value = value.replace("\u00ad", "-")
    return re.sub(r"\s+", " ", value).strip(" \t\r\n:;-")


def _normalized_lines(text):
    pages = (text or "").replace("\r", "").split("\f")
    edge_lines = {}
    for page in pages:
        lines = [_clean(line) for line in page.splitlines()]
        meaningful = [line for line in lines if line]
        for line in meaningful[:3] + meaningful[-3:]:
            normalized = line.casefold()
            if normalized.isdigit() or len(normalized) > 160:
                continue
            edge_lines[normalized] = edge_lines.get(normalized, 0) + 1

    output = []
    for page in pages:
        lines = [_clean(line) for line in page.splitlines()]
        meaningful_indices = [i for i, line in enumerate(lines) if line]
        edge_indices = set(meaningful_indices[:3] + meaningful_indices[-3:])
        for index, line in enumerate(lines):
            if not line:
                output.append("")
                continue
            if (
                line.isdigit()
                or (
                    index in edge_indices
                    and edge_lines.get(line.casefold(), 0) > 1
                )
            ):
                continue
            output.append(line)
    return output


def _is_title_noise(line):
    return bool(
        _TITLE_NOISE.match(line)
        or _EMAIL.search(line)
        or _AFFILIATION.search(line)
        or _YEAR.search(line)
        or len(line) < 8
        or len(line) > 240
        or re.fullmatch(r"[\W\d_]+", line)
        or re.match(r"(?i)^(abstract|index terms?|keywords?)\b", line)
    )


def _split_author_line(line):
    line = _EMAIL.sub("", line)
    line = re.sub(r"[\d*†‡§]+", " ", line)
    line = _PERSON_SPLIT.sub("|", line)
    line = re.sub(r"\s+\band\b\s+", "|", line, flags=re.IGNORECASE)
    if "|" not in line and "," in line:
        # IEEE author lists commonly use comma-separated full names.
        line = re.sub(r",\s*(?=[A-Z][A-Za-z'.-]*\s)", "|", line)
    candidates = []
    for part in line.split("|"):
        candidate = _clean(part.strip(" ,"))
        candidate = re.sub(r"\s+", " ", candidate)
        words = candidate.replace(",", " ").split()
        if not (2 <= len(words) <= 6):
            continue
        if all(_NAME_TOKEN.fullmatch(word.strip(".,'’")) for word in words):
            candidates.append(candidate)
    return candidates


def _extract_title_and_authors(header, pdf_title):
    meaningful = [
        (index, line) for index, line in enumerate(header)
        if not _is_title_noise(line)
    ]
    title = ""
    author_start = None
    for position, (index, line) in enumerate(meaningful):
        if position == 0:
            title = line
            continue
        candidates = _split_author_line(line)
        next_meaningful = meaningful[position + 1:position + 2]
        if (
            candidates
            and next_meaningful
            and len(_split_author_line(next_meaningful[0][1])) >= 2
        ):
            candidates = []
        following_lines = header[index + 1:]
        has_author_context = any(
            _EMAIL.search(item) or _AFFILIATION.search(item)
            for item in following_lines
        )
        has_initial = any(
            re.search(r"\b[A-Z]\.\s*[A-Z]", candidate)
            for candidate in candidates
        )
        if len(candidates) >= 2 and (
            "," in line
            or ";" in line
            or "&" in line
            or (re.search(r"\band\b", line, re.I) and (
                has_author_context or has_initial
            ))
        ):
            author_start = index
            break
        if len(candidates) == 1 and has_author_context:
            author_start = index
            break
        # A non-name line after the first line is usually a wrapped title line.
        if not candidates and len(title) < 280:
            title = _clean(f"{title} {line}")

    if author_start is not None:
        authors = []
        for index, line in meaningful:
            if index < author_start:
                continue
            candidates = _split_author_line(line)
            if (
                candidates
                and not _EMAIL.search(line)
                and not _AFFILIATION.search(line)
            ):
                authors.extend(candidates)
    else:
        authors = []

    if not title and pdf_title:
        candidate = _clean(pdf_title)
        if not _is_title_noise(candidate):
            title = candidate

    unique_authors = []
    seen = set()
    for name in authors:
        key = re.sub(r"[^a-z]+", "", name.casefold())
        if key and key not in seen:
            seen.add(key)
            unique_authors.append(name)
    return title, unique_authors


def _header_lines(lines):
    for index, line in enumerate(lines):
        match = _ABSTRACT_LINE.match(line)
        if match:
            return lines[:index], index, match.group(1).strip()
        if _SECTION.match(line):
            return lines[:index], None, ""
    return lines[:min(40, len(lines))], None, ""


def _extract_abstract(lines, heading_index, inline_content):
    if heading_index is None:
        return ""
    content = [inline_content] if inline_content else []
    for line in lines[heading_index + 1:]:
        if _KEYWORDS_LINE.match(line) or _SECTION.match(line):
            break
        if _ABSTRACT_LINE.match(line):
            break
        content.append(line)
    return _clean(" ".join(item for item in content if item))


def _extract_keywords(lines):
    for index, line in enumerate(lines):
        match = _KEYWORDS_LINE.match(line)
        if not match:
            continue
        keyword_lines = [match.group(1)] if match.group(1) else []
        for continuation in lines[index + 1:]:
            if _SECTION.match(continuation) or _ABSTRACT_LINE.match(continuation):
                break
            keyword_lines.append(continuation)
        value = _clean(" ".join(keyword_lines))
        items = re.split(r"\s*[,;]\s*", value)
        return list(dict.fromkeys(
            _clean(item).rstrip(".") for item in items if _clean(item)
        ))
    return []


def extract_metadata(text, pdf_metadata=None):
    pdf_metadata = pdf_metadata or {}
    lines = _normalized_lines(text)
    header, abstract_index, inline_abstract = _header_lines(lines)
    title, author_names = _extract_title_and_authors(
        header, pdf_metadata.get("title", "")
    )
    header_emails = list(dict.fromkeys(
        email.casefold() for line in header for email in _EMAIL.findall(line)
    ))
    authors = [
        {
            "name": name,
            "email": header_emails[index] if index < len(header_emails) else "",
            "institution": "",
        }
        for index, name in enumerate(author_names)
    ]
    abstract = _extract_abstract(lines, abstract_index, inline_abstract)
    keywords = _extract_keywords(lines)
    doi_match = _DOI.search(text or "")
    doi = normalize_doi(doi_match.group(0)) if doi_match else None

    first_page = (text or "").split("\f", 1)[0]
    reference_heading = re.search(
        r"(?im)^\s*(?:\d{0,2}\s*[.)]?\s*)?(?:references|bibliography)\b",
        first_page,
    )
    if reference_heading:
        first_page = first_page[:reference_heading.start()]
    early_text = "\n".join(_normalized_lines(first_page)[:60])
    year_match = _YEAR.search(early_text)
    year = int(year_match.group(0)) if year_match else None
    venue = next(
        (
            line for line in _normalized_lines(first_page)[:30]
            if re.search(r"\b(proceedings|conference|symposium|workshop|"
                         r"journal|transactions|IEEE|ACM)\b", line, re.I)
            and not _TITLE_NOISE.match(line)
        ),
        "",
    )
    if venue == title:
        venue = ""
    return {
        "title": title,
        "authors": authors,
        "abstract": abstract,
        "year": year,
        "venue": venue,
        "doi": doi,
        "keywords": keywords,
        "references": parse_references(text or ""),
    }
