lemmatisation du français avec [hunspell](http://hunspell.github.io/) pour [spacy](https://spacy.io/api).

ce module propose une manière alternative de réaliser la [lemmatisation]() dans une [pipeline]() spacy, en s'appuyant essentiellement sur HunSpell. l'idée est de tirer parti de la facilité avec laquelle HunSpell permet de d'adapter un lexique à un contexte linguistique spécifique, par exemple en ajoutant des mots ou en définissant des règles de flexions (par exemple pour l'écriture inclusive).

part-of-speech
--------------

ce module est fait pour être utilisé dans une pipeline spacy, et je l'ai écrit parce les modèles actuellement (avril 2024) proposés par spacy ne correspondaient pas à mes besoins. outre la difficulté qu'ils ont à lemmatiser des textes utilisant l'écriture inclusive et les mots composés, l'un des défauts de ces modèles est qu'ils sont parfois assez imprécis dans l'assignation des _part-of-speech tags_. les verbes à l'impératifs présents sont par exemple systématiquement taggés comme étant des noms. or, la lemmatisation dépend des _part-of-speech tags_: le lemme de `sommes (noun)` est "somme" tandis que le lemme de `sommes (verb)` est "être".
la pseudo-solution que je propose est la suivante: à chaque _pos tag_ est associé une liste d'autres tags ordonnés par proximité (et susceptibilité d'être confondus).

un exemple: admettons que dans la phrase "Parle vite!", le modèle considère que "Parle" est un nom. la fonction de lemmatisation va utiliser hunspell pour regarder si "parle" est une forme connue. comme c'est le cas, la fonction prends la liste de priorité pour le tag "nom". elle commence ainsi:

```python
["noun", "verb", "adj", "..."]
```

la fonction prend, dans l'ordre, chacun de ces tags et regarde si un lemme dans le lexique hunspell lui correspond. comme aucun lemme ne correspond à "parle (nom)", la fonction essaie avec "parle (verbe)" et il y a un résultat ("parler") qui devient donc le lemme du mot. pour que cela puisse fonctionner, il faut donc que le lexique (dans hunspell) attribue aux mots un (ou plusieurs) _part-of-speech_ via l'attribut `po:`.

mots composés
-------------

les lemmes des mots composés (_artistes-peintres_, _autrice-compositrice-interprète_) sont obtenus par la concaténation des lemmes de leurs composants: _artistes-peintres_ deviendra _artiste-peintres_, les deux mots _artistes_ et _peintres_ ayant été mis au singulier. si le lexique considère que _auteurice_ est le lemme de _autrice_, alors _autrice-compositrice_ deviendra _auteurice-compositeurice_.

| mot          | lemme          |
| --           | --             |
|autrices-compositrices|auteurices-compositeurices|

l'avantage de cette méthode est qu'elle ne nécessite pas de connaître à l'avance tous les mots composés possibles (virtuellement infinis). elle peut toutefois produire des résultats déconcertants (et intéressants):

| mot          | lemme          |
| --           | --             |
| peut-être    | pouvoir-être   |
| soi-disant   | soi-dire       |
| gratte-ciel  | gratter-ciel   |
| compte-rendu | compter-rendre |
| vis-à-vis    | voir-à-voir    |
| c'est-à-dire | ce être-à-dire |
| vice-versa   | vice-verser    |

rule lemmatizer
---------------

dans certains cas, le mot ne correspond à aucune forme répertoriée dans le lexique hunspell. pour ces cas, une fonction est définie qui construit le lemme par application de règles (_rule-based lemmatization_). celle proposée par défaut est relative au _part-of-speech tag_: s'il s'agit d'un adjectif ou d'un nom, j'enlève simplement les pluriels en `s` ou `x`, s'il s'agit d'un verbe, je considère d'un verbe du premier groupe car la quasi-totalité des _néo-verbes_ sont des verbes du premier groupe, et j'essaie de reconstruire l'infinitif du verbe à partir de sa forme (ce que je fais en utilisant un autre mini-module que j'ai écrit pour ça: [informifier](https://github.com/thjbdvlt/informifier)), dans tous les autres cas, le lemme est le mot inchangé.

morphologie
-----------

puisqu'une analyse avec hunspell est menée, autant utiliser également les toutes les informations morphologiques: elles sont placées dans l'attribut `Token._.viceverser`, sans transformation.

usage
-----

pour l'ajouter comme composant d'une _pipeline_:

```python
import spacy
import viceverser

@spacy.Language.factory("viceverser_lemmatizer")
def create_hunspell_lemmatizer(nlp, name="viceverser_lemmatizer"):
    fp_dic = "/chemin/vers/exemple/fr_xii.dic"
    fp_aff = "/chemin/vers/exemple/fr_xii.aff"
    return viceverser.Lemmatizer(
        nlp=nlp,
        fp_dic=paths.fp_dic,
        fp_aff=paths.fp_aff
    )

nlp = spacy.load("fr_core_news_lg")
nlp.add_pipe("viceverser_lemmatizer", after="morphologizer")
```

installation
------------

```bash
git clone https://github.com/thjbdvlt/viceverser viceverser
cd viceverser
pip install .
```

dependancies
------------

- spacy
- [pyhunspell](https://github.com/pyhunspell/pyhunspell)
- optionnelle: [informifier](https://github.com/thjbdvlt/informifier)
