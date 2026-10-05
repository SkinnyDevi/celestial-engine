#!/usr/bin/env bash
set -e

# Get the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="$DIR/../.venv"

# Create the python venv if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating Python virtual environment for tests in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
    
    echo "Installing jsonschema..."
    "$VENV_DIR/bin/pip" install --quiet --upgrade pip
    "$VENV_DIR/bin/pip" install --quiet jsonschema
fi

# Run the python schema validator inside the venv
"$VENV_DIR/bin/python3" "$DIR/../validate_schema.py" "$1" "$2"
