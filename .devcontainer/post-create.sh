#!/bin/bash
set -e

# Existing setup
apt-get update && apt-get install -y git-crypt
pip3 install --user -r requirements.txt

pipx install rust-just
