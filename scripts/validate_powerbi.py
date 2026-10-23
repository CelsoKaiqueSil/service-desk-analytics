"""Validate PBIP/PBIR JSON against the official Microsoft schemas (not a DAX runtime)."""
import json
import hashlib
import os
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urlparse
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT7
from jsonschema import Draft7Validator

ROOT = Path(__file__).resolve().parents[1] / 'powerbi'


def retrieve(uri):
    parsed = urlparse(uri)
    if parsed.scheme != 'https' or parsed.netloc != 'developer.microsoft.com':
        raise ValueError('Only official Microsoft schemas are allowed')
    cache = os.getenv('POWERBI_SCHEMA_CACHE')
    path = Path(cache) / (hashlib.sha256(uri.encode()).hexdigest()+'.json') if cache else None
    if path and path.exists():
        contents = json.loads(path.read_text(encoding='utf-8-sig'))
    else:
        with urlopen(uri, timeout=30) as response:
            contents = json.load(response)
    return Resource.from_contents(contents, default_specification=DRAFT7)


registry = Registry(retrieve=retrieve)
count = 0
for path in ROOT.rglob('*.json'):
    data = json.loads(path.read_text(encoding='utf-8'))
    if '$schema' not in data:
        continue
    uri = data['$schema']
    schema = retrieve(uri).contents
    schema['$id'] = uri
    Draft7Validator(schema, registry=registry).validate(data)
    count += 1
assert count >= 12, 'Missing report, page or visual definitions'
print(f'{count} PBIR JSON files validated; Desktop/DAX runtime validation remains pending')
