#!/bin/bash

name=spell-fr.vim
tmpdir=/tmp/${name}

if ! [ -d viceverser/data ];then
    mkdir viceverser/data
fi

git clone https://github.com/thjbdvlt/${name} ${tmpdir}
cp ${tmpdir}/morph/* ${tmpdir}/feats/* viceverser/data/

rm ${tmpdir} -rf
