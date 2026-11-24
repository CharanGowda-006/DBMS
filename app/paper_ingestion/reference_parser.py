import re
import unicodedata


_REFERENCE_HEADING = re.compile(
    r"(?im)^\s*(?:\d{0,2}\s*[.)]?\s*)?"
    r"(?:references|bibliography)\b\s*:?\s*(.*)$"
)
_NEXT_HEADING = re.compile(
    r"(?im)^\s*(?:appendix|acknowledg(?:e)?ments|author biographies)\b"
)
_DOI = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.IGNORECASE)
_YEAR = re.compile(r"\b(18\d{2}|19\d{2}|20\d{2}|2100)\b")
_ENTRY_START = re.compile(
    r"^\s*(?:\[\s*(\d+)\s*\]|(\d{1,3})[.)])\s*"
)
_QUOTED_TITLE = re.compile(
    r"""(?:["“‘?])(.{8,}?)(?:["”’?])""",
    re.IGNORECASE,
)


def normalize_doi(value):
    if not value:
        return None
    match = _DOI.search(str(value).replace("https://doi.org/", ""))
    if not match:
        match = _DOI.search(str(value).replace("http://dx.doi.org/", ""))
    return match.group(0).rstrip(".,;:") if match else None


def parse_references(text, max_references=250):
    heading = _REFERENCE_HEADING.search(text or "")
    if not heading:
        return []
    section = (text or "")[heading.end():]
    if heading.group(1).strip():
        section = heading.group(1).strip() + "\n" + section
    next_heading = _NEXT_HEADING.search(section)
    if next_heading:
        section = section[:next_heading.start()]

    entries = []
    current = []
    for line in section.splitlines():
        if line.strip() == "\f":
            continue
        line = re.sub(r"\s+", " ", line).strip()
        if not line:
            continue
        if _ENTRY_START.match(line):
            if current:
                entries.append(" ".join(current))
            current = [line]
        elif current:
            if current[-1].endswith("-") and line[:1].islower():
                current[-1] = current[-1][:-1] + line
            else:
                current.append(line)
        elif len(line) > 40:
            current = [line]
    if current:
        entries.append(" ".join(current))

    results = []
    for raw in entries[:max_references]:
        marker = _ENTRY_START.match(raw)
        number = (
            int(marker.group(1) or marker.group(2))
            if marker else None
        )
        body = _ENTRY_START.sub("", raw, count=1)
        doi = normalize_doi(body)
        year_match = _YEAR.search(body)
        title_part = body
        quoted_title = _QUOTED_TITLE.search(body)
        if quoted_title:
            title_part = quoted_title.group(1).strip(" .,:;")
        else:
            if doi:
                title_part = title_part[:_DOI.search(title_part).start()]
            if year_match:
                title_part = (
                    title_part[:year_match.start()]
                    + title_part[year_match.end():]
                )
            title_part = re.sub(r"^[^,]{1,100},\s*", "", title_part).strip(" .,:;")
        title_part = unicodedata.normalize("NFKC", title_part).replace("\u00ad", "-")
        results.append({
            "raw": raw,
            "number": number,
            "title": title_part or None,
            "year": int(year_match.group(0)) if year_match else None,
            "doi": doi,
        })
    return results
