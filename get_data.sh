#!/bin/bash

name=spell-fr.vim

set -e

git clone https://github.com/thjbdvlt/${name} ${name}
cp ${name}/morph/* ${name}/feats/* viceverser/data/

rm ${name} -rf
