import re


def test_openapi_matches_all_api_operations_and_references(app, client):
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    spec = response.json
    assert spec["openapi"] == "3.1.0"
    operations = set()
    for rule in app.url_map.iter_rules():
        if not rule.rule.startswith("/api/v1/"):
            continue
        path = re.sub(r"<int:(\w+)>", r"{\1}", rule.rule)
        for method in rule.methods - {"HEAD", "OPTIONS"}:
            operations.add((path, method.lower()))
    documented = {(path, method) for path, methods in spec["paths"].items() for method in methods}
    assert operations == documented

    def check_refs(value):
        if isinstance(value, dict):
            if "$ref" in value:
                target = spec
                for component in value["$ref"].removeprefix("#/").split("/"):
                    target = target[component]
                assert target
            for item in value.values():
                check_refs(item)
        elif isinstance(value, list):
            for item in value:
                check_refs(item)

    check_refs(spec)
