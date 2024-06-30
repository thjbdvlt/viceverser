import pkgutil
import hunspell
import importlib
import os
from spacy.morphology import Morphology

_datapath = importlib.resources.files("viceverser").joinpath("data")

FP_DIC = os.path.join(_datapath, "st.dic")
FP_AFF = os.path.join(_datapath, "st.aff")
LOOKUP = {}

_sep = "\t"
_lookup = pkgutil.get_data(__name__, "data/lookup.tsv").decode()
for _line in _lookup.split("\n"):
    _line_splitted = _line.strip().split(_sep)
    if len(_line_splitted) == 2:
        k, v = _line_splitted
        d = {}
        for feature in v.split(Morphology.FEATURE_SEP):
            name, value = feature.split(Morphology.FIELD_SEP)
            d[name] = value
        LOOKUP[k] = d


def get_default_hobj():
    return hunspell.HunSpell(FP_DIC, FP_AFF)
