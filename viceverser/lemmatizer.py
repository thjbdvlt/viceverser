"""lemmatisation du français avec hunspell pour spacy

a) s'il s'agit d'un mot simple, utiliser la fonction `stem` de hunspell pour trouver le lemme (arrivions -> arriver). si possible, trouver un lemme qui a la même catégorie grammaticale (ex. conseillons -> conseiller (verbe)), mais parfois le pos-tagging fait des erreurs, et alors il faudra trouver un lemme d'une autre catégorie grammaticale.
b) s'il s'agit d'un mot composé (avec un ou plusieurs trait(s) d'union(s)), découper le mots en ses différents composant et analyser comme en a) chacun de ces composants, puis les aggréger. par exemple: "auteur-compositeur" -> ["auteurice", "compositeurice"] -> "auteurice-compositeurice".
"""

import re
from hunspell import HunSpell
from spacy.lookups import Lookups
from informifier import Informitif
from typing import Union
from verbes_speciaux import verbes_speciaux


class HunspellLemmatizer:
    """lemmatise des documents en utilisant hunspell."""

    def __init__(self, nlp, fp_dic: str, fp_aff: str):
        """crée un objet pour lemmatiser une série de documents.

        nlp:  la pipeline spacy avec le modèle, vocab, etc.
        fp_dic:  fichier .dic pour hunspell (lexique).
        fp_aff:  fichier .aff pour hunspell (règles de flexions).

        les mots du lexique hunspell doivent avoir l'attribut `po:` (part-of-speech).

        pour initier le lemmatiser, j'instancie différents objets qui vont me servir pour la lemmatisation:
        - un objet `Lookups` dans lequel mettre des tables d'accessions rapides, pour éviter de répéter inutilement des opérations.
        - un objet `HunSpell` à partir d'un fichier .dic (qui définit un lexique de base) et .aff (qui définit des règles combinatoires de variations autour du lexique).
        - un objet `Informitif`, issu d'un petit module que j'ai écrit pour ça et qui sert à trouver l'infinitif d'un verbe à partir de l'une de ses formes conjuguée, et de déterminer à quelle sous-groupe il appartient (parmi les verbes du premier groupe). l'idée est de pouvoir, en rencontrant un nouveau verbe, donner à hunspell un modèle pour construire toutes les formes possibles que ce verbe peut prendre.
        """

        self.lookups = Lookups()
        self.hobj = HunSpell(fp_dic, fp_aff)
        self.inform = Informitif()
        self.nlp = nlp
        self.strings = nlp.vocab.strings
        pos_similarities = {
            "aux": ["verb"],
            "verb": ["aux"],
            "noun": ["verb", "aux"],
            "det": ["cconj", "sconj", "pron", "adp"],
            "pron": ["det", "cconj", "sconj", "adp"],
        }
        pos_default_priority = [
            "pron",
            "det",
            "cconj",
            "sconj",
            "aux",
            "verb",
            "noun",
        ]
        self.pos_priorities = self.list_pos_priorities(
            similarities=pos_similarities,
            default_priority=pos_default_priority,
        )
        for i in self.pos_priorities.keys():
            self.lookups.add_table(i, {})
        v = self.lookups.get_table("verb")
        s = self.strings
        for verb in verbes_speciaux:
            for form in verbes_speciaux[verb]:
                v.set(s[form], verb)

    def list_pos_priorities(
        self, similarities: dict, default_priority: list[str]
    ) -> None:
        """construit un dictionnaire de proximitié des pos tags.

        `similarities`:  un dictionnaire qui attribue, à chaque pos-tag une liste de pos-tags proches.
        `default_priority`:  une liste de priorités par défault qui sera utilisée pour compléter `similarities`.

        exemple:
            similarities={"verb": ["aux"], "cconj": ["sconj", "det"]}
            default_priority=["noun", "verb", "pron"]

        aucune des deux liste n'a besoin d'être exhaustive. elle sera complétée par les tags possibles (récupérée dans les labels du morphologizer).

        l'attribution des pos-tags n'est pas toujours très précise pour le français avec les modèles actuellement proposés par spacy. or, l'attribution d'un lemme dépend de son pos-tag (par exemple: sommes:noun->somme  sommes:verb->être). je fixe donc des règles qui disent:
        si `pos=noun`, alors regarder d'abord si un lemme est fixé pour ce mot en tant que nom. s'il n'y a aucun résultat, alors regarder si un lemme est fixé pour ce mot en tant que verbe, puis si ce n'est pas le cas, en tant qu'auxiliaire, etc., jusqu'à trouvé un mot ou jusqu'à avoir épuisé toutes les catégories grammaticalse, et donc tous les mots du lexique.
        chaque catégorie est proches de certaines catégorie, est éloignée d'autres. donc en cas d'erreur, un mot identifié à une certaine catégorie est plus ou moins susceptible d'appartenir en fait à certaines catégorie qu'à d'autres. typiquement, les `aux` sont toujours des `verb` en français, donc on peut imaginer un mot taggé par erreur comme `aux`: on a plus de chance de le trouver en fait dans les `verb` que dans les `det`. un autre cas: les modèles proposés par spacy pour le français ne reconnaissent pas les verbes à l'infinitif présent, qui seront toujours taggés comme `noun`. donc si un mot avec la catégorie `noun` n'existe pas, le mieux à faire est de regarder si le même mot avec la catégorie `verb`, lui, existe.

        1. récupère la liste des tags possibles (dans le morphologizer).
        2. complète la liste de priorité par défault avec les tags possibles manquants (placés à la fin).
        3. compléter le dictionnaire de similarités.
        4. ajouter au dictionnaire de similarités, pour chaque pos-tag, une entrée sous forme de tuple ("adp", tag), ex. ("adp", "noun"), qui sera utilisée pour la lemmatisation des mots composés, car les parties qui composent les mots composés sont généralement:
            - des adpositions (suffixes ou préfixes): socio-critique.
            - des mots de même nature que le mot composé (maison-bateau).
        """

        posstags = self.list_pos_tags()
        default_priority.extend([i for i in posstags if i not in default_priority])
        for tag in default_priority:
            if tag in similarities.keys():
                prio = similarities[tag]
                missing = [i for i in default_priority if i not in prio]
                prio.extend(missing)
            else:
                prio = default_priority
            prio.remove(tag)
            prio.insert(0, tag)
            similarities[("adp", tag)] = ["adp"] + [
                i for i in prio if i != "adp"
            ]
            similarities[tag] = prio
        return similarities

    def list_pos_tags(self) -> list[str]:
        """récupère la liste des part-of-speech tags du morphologizer."""

        re_pos = re.compile(r"POS=(\w+)")
        a = []
        labels = self.nlp.get_pipe("morphologizer").labels
        for l in labels:
            r = re_pos.search(l)
            if r:
                a.append(r.group(1).lower())
        return sorted(set(a))

    def rule_lemmatize(self, word: str, upos: str) -> str:
        """lemmatise un mot à l'aide de règles spécifiques à son POS.

        verb: reconstitue l'infinitif d'un verbe. ajoute ensuite le verbe dans le lexique d'hunspell avec des affixes (à partir d'un verbe du même groupe), afin qu'il déduise les variations possibles (conjugaison).

        noun+adj: enlève un éventuel "s" et "x" final.

        dans les autres cas, retourne simplement le mot lui-même, sans modification.
        """

        if upos == "verb":
            lemma, like = self.inform(word)
            self.hobj.add_with_affix(lemma, like)
            return lemma
        elif word[-1] in ("x", "s") and upos in ("noun", "adj"):
            return word[:-1]
        else:
            return word

    def find_lemma(self, word, norm, upos) -> str:
        """trouve le lemme d'un mot.

        plusieurs méthodes sont essayées successivement:
            1. première solution, la plus simple: si le mot est dans la table, alors retourne le lemme correspondant. (idéalement, il faudrait faire qqch avec le part-of-speech ici, même pour la table. typiquement pour sommes/somme.)
            2. si le mot n'est pas déjà dans la table, le chercher dans le dictionnaire hunspell. si un stemme est trouvé, l'utiliser comme lemme et ajouter la relation mot-lemme dans la table (pour ne pas avoir à appeler plusieurs fois des fonctions de hunspell sur des mots identiques).
            3. s'il s'agit d'un mot composé (autrice-compositrice), je décompose le mot et lemmatise chaque composant, avant de les réaggréger pour construire le lemme du mot composé: "autrice-compositrice" -> "auteurice-compositeurice".
            4. en fonction du part-of-speech, j'essaie de reconstruire le lemme à partir d'une série de règles plus ou moins simples.
            5. si aucune méthode au-dessus n'a fonctionné, le lemme est identique à token.norm_
        (docstring pas à jour!)
        """

        l = self.lookups.get_table(upos)

        x = l.get(norm)
        if x is not None:
            return x

        x = self.search_lemma_hunspell(word=word, upos=upos)
        if x is not None:
            l.set(norm, x)
            return x

        x = self.rule_lemmatize(word=word, upos=upos)
        l.set(norm, x)
        return x

    def find_lemma_composed(self, word, norm, upos):
        """trouve le lemme d'un mot composé."""

        l = self.lookups.get_table(upos)
        strings = self.strings

        x = l.get(norm)
        if x is not None:
            return x

        keyhaslemme = l.get(norm)
        if keyhaslemme is not None:
            return keyhaslemme

        subwords = [
            self.find_lemma(
                word=s,
                norm=strings[s],
                upos=("adp", upos),
            )
            for s in word.split("-")
            if s.strip() != ""
        ]
        lemme_ = "-".join(subwords)
        composednorm = strings[lemme_]
        x = l.get(composednorm)
        if x is not None:
            l.set(norm, x)
            return x
        else:
            l.set(norm, lemme_)
            l.set(composednorm, lemme_)
            return lemme_

    def search_lemma_hunspell(
        self, word: str, upos: str
    ) -> Union[tuple[str, str], None]:
        """cherche un lemme correspondant au mot dans un lexique hunspell.

        si un lemme avec la même catégorie grammaticale (part-of-speech tag) est trouvé, alors il est retourné. sinon, cherche dans l'ordre des upos les plus proches du upos du mot. (si le mot correspond à une entrée, un lemme sera de toute façon retourné, si possible avec la même catégorie grammaticale.)

        exemples
        --------

            1. `word=rire, upos=noun`
                -> ("rire", "noun")

            2. `word=rire, upos=verb`
                -> ("rire", "verb")

            3. `word=rire, upos=aux`
                -> ("rire", "verb")

            4. `word=t8âùèildv, upos=aux`
                -> None
        """

        ho = self.hobj

        if ho.spell(word) is False:
            return None

        d = {}
        x = ho.analyze(word)
        for lex_entry in x:
            attrs = lex_entry.decode().split()
            po_tags = [a[3:] for a in attrs if a[:3] == "po:"]
            stem = attrs[0][3:]
            for t in po_tags:
                d[t] = stem
        tagsprio = self.pos_priorities[upos]
        for t in tagsprio:
            if t in d:
                return d[t]
        return None

    def set_lemma(self, token) -> None:
        """détermine le lemme d'un token."""

        word = token.norm_
        norm = token.norm
        upos = token.pos_.lower()
        x = self.lookups.get_table(upos).get(norm)
        if x is not None:
            token.lemma_ = x
            return
        elif "-" in token.norm_:
            fn = self.find_lemma_composed
        else:
            fn = self.find_lemma
        token.lemma_ = fn(word=word, norm=norm, upos=upos)

    def __call__(self, doc):
        """attribue un lemme à chaque token d'un doc."""

        for token in doc:
            if token._.token_class == "mot":
                self.set_lemma(token)
        return doc
