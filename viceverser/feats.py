import viceverser.default
from spacy.morphology import Morphology
import hunspell

VALUE_SEP = Morphology.VALUE_SEP
FIELD_SEP = Morphology.FIELD_SEP
FEATURE_SEP = Morphology.FEATURE_SEP


def morph_to_feats(morph, lookup=viceverser.default.LOOKUP):
    """Convert a Hunspell analyses list into a dict.

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
    """Convert a dict into FEATS format.

    Args:
        lookup (dict)

    Returns (str)
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
    return d


class VunSpell(hunspell.HunSpell):
    """Un objet HunSpell avec quelques méthodes supplémentaires."""

    def __init__(self, dic=viceverser.default.FP_DIC, aff=viceverser.default.FP_AFF, *args, **kwargs):
        """Instancie un objet FrSpell.

        Args: tous les Args sont passés à hunspell.HunSpell()
        """

        super().__init__(dic, aff, *args, **kwargs)

    def todict(self, mot):
        """Retourne l'analyse d'un mot sous forme de list de dict.

        Args:
            mot (str)

        Returns (list[dict])
        """

        result = []
        for i in self.analyze(mot):
            d = {}
            s = i.decode().split()
            for attr in s:
                k = attr[:2]
                v = attr[3:]
                if k not in d:
                    d[k] = [v]
                else:
                    d[k].append(v)
            d = {k: sorted(v) for k, v in d.items()}
            result.append(d)
        return result

    def getpos(self, mot):
        """Retourne tous les part-of-speechs liés à un mot.

        Args:
            mot (str)

        Returns (dict[str:list])
        """

        d = {}
        analyses = [i for i in self.todict(mot) if 'po' in i]
        for i in analyses:
            pos = i.pop('po')
            for p in pos:
                if p not in d:
                    d[p] = [i]
                else:
                    d[p].append(i)
        return d
