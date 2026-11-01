#!/bin/bash
git submodule update --init --recursive
rm -rf ./venv
source bash-scripts/helpers.sh
setup_virtual_env
