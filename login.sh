#!/bin/bash

cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD"
python3 src/login.py
