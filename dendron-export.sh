#! /bin/sh

DENDRON_VAULT=/home/sagar/Documents/dendron-notes
HUGO_SITE=/home/sagar/sagar.se

rm -rf notes/ logs/
rm -rf $HUGO_SITE/content/notes/*
python3 export-hierarchy.py
cp -a $DENDRON_VAULT/assets $HUGO_SITE/static/
python3 process-wikilinks.py
python3 add-backlinks.py
cp -a notes/* $HUGO_SITE/content/notes/
