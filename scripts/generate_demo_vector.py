from pathlib import Path
import json

path = Path("sample_data/demo_vector.json")
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps({"features": [0.0] * 2381}, indent=2), encoding="utf-8")
print(path)
