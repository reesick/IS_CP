"""Check the actual published PNGs and archive, without external inference."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile
from PIL import Image
folder=Path(sys.argv[1]);archive=folder.with_suffix('.zip')
manifest=json.loads((folder/'manifest.json').read_text())
assert len(manifest['images'])==3
checks=[]
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for item in manifest['images']:
        candidate=folder/item['candidate'];reference=folder/item['clean_reference']
        assert item['quality']['gate']=='passed'
        assert hashlib.sha256(candidate.read_bytes()).hexdigest()==item['candidate_sha256']
        assert hashlib.sha256(reference.read_bytes()).hexdigest()==item['clean_sha256']
        assert hashlib.sha256(z.read(item['candidate'])).hexdigest()==item['candidate_sha256']
        with Image.open(candidate) as image,Image.open(reference) as clean:
            image.load();clean.load();assert image.size==clean.size
            checks.append(dict(file=candidate.name,size=list(image.size),quality_gate='passed',file_and_zip_hashes_match=True))
result=dict(passed=True,folder=str(folder),archive=str(archive),images=checks,frontier_effectiveness='not_tested')
root=Path(__file__).resolve().parents[2]
(root/'data/frontier-kit-verification.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
