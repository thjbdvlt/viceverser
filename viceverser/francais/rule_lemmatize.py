import informifier


def rule_lemmatize(word: str, upos: str) -> str:
    """lemmatise un mot à l'aide de règles spécifiques à son POS.

    - verb: reconstitue l'infinitif d'un verbe.
    - noun+adj: enlève un éventuel "s" et "x" final.
    dans les autres cas, retourne simplement le mot lui-même, sans modification.
    """

    if upos in ("verb", "aux"):
        lemma, _ = inform(word)
        return lemma
    elif word[-1] in ("x", "s") and upos in ("noun", "adj"):
        return word[:-1]
    else:
        return word
