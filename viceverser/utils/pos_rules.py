import re


def default_list(nlp):
    """Récupère la liste des upos possibles dans le morphologizer.

    Args:
        nlp: le modèle de langue chargé par spacy.

    Returns dict[str, list]: les upos associés aux autres upos par ordre de priorité.
    """

    from viceverser.francais import pos_priorities as pp

    postags = get_pos_tag_pipe(nlp=nlp, pipename="morphologizer")
    priorities = list_pos_priorities(
        postags=postags,
        similarities=pp.POS_SIMILARITIES,
        default_priority=pp.POS_DEFAULT_PRIORITY,
    )
    return priorities


def list_pos_priorities(
    postags, similarities: dict, default_priority: list[str]
) -> None:
    """Construit un dictionnaire de proximitié des pos tags.

    Args:
        similarities (dict):  un dictionnaire qui attribue, à chaque pos-tag une liste de pos-tags proches.
        default_priority (list):  une liste de priorités par défault qui sera utilisée pour compléter `similarities`.

    Returns (None)

    Exemple:
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

    default_priority.extend(
        [i for i in postags if i not in default_priority]
    )
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


def get_pos_tag_pipe(
    nlp, pipename: str = "morphologizer"
) -> list[str]:
    """Récupère la liste des part-of-speech tags d'un pipe component.

    Args:
        nlp: le modèle de langue chargé par spacy.
        pipename (str): le pipeline component dans lequel récupérer les tags (par défault: le morphologizer).

    Returns list[str]: la liste de part-of-speech tags.
    """

    re_pos = re.compile(r"POS=(\w+)")
    a = []
    labels = nlp.get_pipe(pipename).labels
    for l in labels:
        r = re_pos.search(l)
        if r:
            a.append(r.group(1).lower())
    return sorted(set(a))
