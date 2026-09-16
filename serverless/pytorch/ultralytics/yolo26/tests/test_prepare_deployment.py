# Copyright (C) CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT

import json

import pytest
import yaml

from serverless.pytorch.ultralytics.yolo26.prepare_deployment import (
    load_labels,
    prepare_function,
)


@pytest.mark.parametrize(
    ("names", "expected"),
    [
        (["shrimp", "fish"], ["shrimp", "fish"]),
        ({0: "shrimp", 1: "fish"}, ["shrimp", "fish"]),
    ],
)
def test_load_labels_supports_list_and_mapping(tmp_path, names, expected):
    data_yaml = tmp_path / "data.yaml"
    data_yaml.write_text(yaml.safe_dump({"nc": 2, "names": names}), encoding="utf-8")

    assert load_labels(data_yaml) == expected


def test_prepare_function_updates_cvat_spec(tmp_path):
    function_yaml = tmp_path / "function.yaml"
    function_yaml.write_text(
        yaml.safe_dump(
            {
                "metadata": {
                    "annotations": {"name": "Old name", "type": "detector", "spec": "[]"}
                }
            }
        ),
        encoding="utf-8",
    )
    data_yaml = tmp_path / "data.yaml"
    data_yaml.write_text(yaml.safe_dump({"names": ["shrimp"]}), encoding="utf-8")

    prepare_function(function_yaml, data_yaml, "Shrimp detector")

    function = yaml.safe_load(function_yaml.read_text(encoding="utf-8"))
    assert function["metadata"]["annotations"]["name"] == "Shrimp detector"
    assert json.loads(function["metadata"]["annotations"]["spec"]) == [
        {"id": 0, "name": "shrimp", "type": "rectangle"}
    ]
