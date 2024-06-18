import viceverser.default
from spacy.morphology import Morphology

VALUE_SEP = Morphology.VALUE_SEP
FIELD_SEP = Morphology.FIELD_SEP
FEATURE_SEP = Morphology.FEATURE_SEP


def morph_to_feats(morph, lookup=viceverser.default.LOOKUP):
    """Convert a flag like `is:sg` to feats like `Number=Sing`.

    Args:
        morph (str):  the morphological analysis as provided by hunspell.
        lookup (dict):  a lookup table to translate to feats. each values must be a dict itself:

        Example:
            {"is:ipre": {"Tense": "Pres", "Mood": "Ind"}}

    Returns (str):  morphological analysis in FEATS format.
    """

    d = {"is": set()}
    for i in morph.split():
        if i.startswith("is:"):
            if i in lookup:
                for k, v in lookup[i].items():
                    if k in d:
                        d[k].add(v)
                    else:
                        d[k] = {v}
            else:
                d["is"].add(i[3:])

    if len(d["is"]) == 0:
        d.pop("is")

    for k, v in d.items():
        d[k] = sorted(v)

    feats = []
    for k in sorted(d.keys()):
        feats.append(FIELD_SEP.join((k, VALUE_SEP.join(d[k]))))
    return FEATURE_SEP.join(feats)


def morph_to_dict(morph, lookup=viceverser.default.LOOKUP):
    d = {"is": set()}
    for i in morph.split():
        if i.startswith("is:"):
            if i in lookup:
                for k, v in lookup[i].items():
                    if k in d:
                        d[k].add(v)
                    else:
                        d[k] = {v}
            else:
                d["is"].add(i[3:])

    if len(d["is"]) == 0:
        d.pop("is")

    for k, v in d.items():
        d[k] = sorted(v)
    return d
