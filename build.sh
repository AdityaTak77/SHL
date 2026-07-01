#!/usr/bin/env bash
# exit on error
set -o errexit

# 1. Build frontend React assets
cd frontend
npm install
npm run build
cd ..

# 2. Install python packages
pip install -r requirements.txt
