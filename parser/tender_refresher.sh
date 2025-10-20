#!/bin/bash

#error showing
set -e

. ../venv/bin/activate

echo "Virtual env has been started ..."


echo "Starting data extractor ...."


#acxtually executing
python ./parser.py


echo "extraction completed"