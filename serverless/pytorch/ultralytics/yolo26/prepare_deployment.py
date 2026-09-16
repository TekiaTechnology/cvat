# Copyright (C) CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT

import argparse
import json
from pathlib import Path

import yaml


def load_labels(data_yaml):
    with open(data_yaml, encoding="utf-8") as data_file:
        data = yaml.safe_load(data_file)

    names = data.get("names")
    if isinstance(names, list):
        labels = names
    elif isinstance(names, dict):
        indexed_names = {int(class_id): name for class_id, name in names.items()}
        expected_ids = list(range(len(indexed_names)))
        if sorted(indexed_names) != expected_ids:
            raise ValueError(f"Class IDs must be consecutive and start at 0: {sorted(indexed_names)}")
        labels = [indexed_names[class_id] for class_id in expected_ids]
    else:
        raise ValueError("data.yaml must contain 'names' as a list or ID-to-name mapping")

    if not labels or any(not isinstance(name, str) or not name.strip() for name in labels):
        raise ValueError("Every class in data.yaml must have a non-empty string name")

    if data.get("nc") is not None and int(data["nc"]) != len(labels):
        raise ValueError(f"data.yaml nc={data['nc']} but contains {len(labels)} class names")

    return labels


def prepare_function(function_yaml, data_yaml, display_name):
    labels = load_labels(data_yaml)

    with open(function_yaml, encoding="utf-8") as function_file:
        function = yaml.safe_load(function_file)

    function["metadata"]["annotations"]["name"] = display_name
    function["metadata"]["annotations"]["spec"] = json.dumps(
        [
            {"id": class_id, "name": name, "type": "rectangle"}
            for class_id, name in enumerate(labels)
        ]
    )

    with open(function_yaml, "w", encoding="utf-8", newline="\n") as function_file:
        yaml.safe_dump(function, function_file, sort_keys=False, allow_unicode=True)

    return labels


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--function-yaml", type=Path, required=True)
    parser.add_argument("--data-yaml", type=Path, required=True)
    parser.add_argument("--display-name", default="Custom YOLO26")
    args = parser.parse_args()

    labels = prepare_function(args.function_yaml, args.data_yaml, args.display_name)
    print(json.dumps(labels, ensure_ascii=False))


if __name__ == "__main__":
    main()
