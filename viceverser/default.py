import pkgutil
import importlib
import os

_datapath = importlib.resources.files('viceverser').joinpath('data')
FP_DIC = os.path.join(_datapath, "st.dic")
FP_AFF = os.path.join(_datapath, "st.dic")
LOOKUP = pkgutil.get_data(__name__, "data/lookup.tsv").decode()
