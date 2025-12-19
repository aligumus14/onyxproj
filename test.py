import json
doc = json.load(open("./json_docs/INV-2025-000001.json", "r", encoding="utf-8"))
print(doc["doc_id"], doc["grand_total"], len(doc["lines"]))
print([x for x in doc["lines"] if "Dana Kıyma" in x["name"]])