from viceverser.francais.verbes_speciaux import verbes_speciaux

exc = {"verb": []}
for verb in verbes_speciaux:
    for form in verbes_speciaux[verb]:
        exc["verb"][form] = verb
