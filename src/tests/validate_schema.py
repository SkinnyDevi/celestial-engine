#!/usr/bin/env python3
import sys
import json

try:
    import jsonschema
except ImportError:
    print("Warning: 'jsonschema' python package not installed. Skipping strict schema validation.")
    print("To enable this test, run: pip3 install jsonschema")
    sys.exit(0) # Return 0 so we don't break the build for developers missing the package

if len(sys.argv) < 3:
    print(f"Usage: {sys.argv[0]} <schema_file.json> <data_file.json>")
    sys.exit(1)

schema_path = sys.argv[1]
data_path = sys.argv[2]

try:
    with open(schema_path, 'r') as f:
        schema = json.load(f)
    
    with open(data_path, 'r') as f:
        data = json.load(f)
        
    jsonschema.validate(instance=data, schema=schema)
    print(f"SUCCESS: '{data_path}' perfectly matches the schema in '{schema_path}'!")
    sys.exit(0)

except jsonschema.exceptions.ValidationError as e:
    print(f"\n[!] JSON SCHEMA VALIDATION FAILED in {data_path}")
    print(f"Error Path: {' -> '.join([str(p) for p in e.absolute_path])}")
    print(f"Message: {e.message}\n")
    sys.exit(1)

except Exception as e:
    print(f"Error reading JSON files: {e}")
    sys.exit(1)
