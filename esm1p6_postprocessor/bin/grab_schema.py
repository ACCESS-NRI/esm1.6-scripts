from sys import argv
import json
from json_ref_dict import materialize, RefDict

# Get the schema as a json
SCHEMA_URL = "https://raw.githubusercontent.com/ACCESS-NRI/schema/refs/heads/main/au.org.access-nri/model/output/file-metadata/2-1-0/2-1-0.json"
schema = materialize(RefDict(SCHEMA_URL))

dest_file = argv[1]

with open(dest_file, 'w') as f:
    json.dump(schema, f)
