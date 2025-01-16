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
    "verb": ["aux", "adj", "noun"],
    "noun": ["adj", "verb"],
    "adj": ["noun", "verb"],
    "det": ["cconj", "sconj", "pron", "adp"],
    "pron": ["det", "cconj", "sconj", "adp"],
}
