import viceverser.default
from spacy.morphology import Morphology

VALUE_SEP = Morphology.VALUE_SEP
FIELD_SEP = Morphology.FIELD_SEP
FEATURE_SEP = Morphology.FEATURE_SEP


def morph_to_feats(morph, lookup=viceverser.default.LOOKUP):
    """Convert a flag like `is:sg` to feats like `Number=Sing`.

    Args:
        morph (str):  the morphological analysis as provided by hunspell.
        lookup (dict):  a lookup table to translate to feats.

    Returns (str):  morphological analysis in FEATS format.
    """

    x = []
    is_ = []
    for i in morph.split():
        if i.startswith('is:'):
            tag = i[3:]
            if tag in lookup:
                x.append(lookup[tag])
            else:
                is_.append(tag)
    is_ = FIELD_SEP.join('is', VALUE_SEP.join(is_))
    x.extend(is_)
    return FEATURE_SEP.join(x)
