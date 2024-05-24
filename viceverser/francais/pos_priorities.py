POS_DEFAULT_PRIORITY = [
    "pron",
    "det",
    "cconj",
    "sconj",
    "aux",
    "verb",
    "noun",
]

POS_SIMILARITIES = {
    "aux": ["verb"],
    "verb": ["aux"],
    "noun": ["verb", "aux", "adj"],
    "adj": ["noun"],
    "det": ["cconj", "sconj", "pron", "adp"],
    "pron": ["det", "cconj", "sconj", "adp"],
}
