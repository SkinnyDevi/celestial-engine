#!/usr/bin/env bash
set -e

# Get the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="$DIR/.venv"

# Create the python venv if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating Python virtual environment for data import in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
    
    echo "Installing packages..."
    "$VENV_DIR/bin/pip" install --quiet --upgrade pip
    "$VENV_DIR/bin/pip" install --quiet jsonschema
    "$VENV_DIR/bin/pip" install --quiet astroquery
    "$VENV_DIR/bin/pip" install --quiet astropy
fi

"$VENV_DIR/bin/python3" "$DIR/import_data.py"
