# Copyright (C) CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT

import tempfile
from pathlib import Path

import numpy as np
from datumaro.components.annotation import AnnotationType, Bbox, Polygon
from datumaro.components.dataset import Dataset
from datumaro.components.dataset_base import DatasetItem
from datumaro.components.media import Image

from cvat.apps.dataset_manager.formats.yolo import _convert_segmentations_to_bboxes


def test_segmentations_to_bboxes_preserves_annotation_metadata():
    annotations = _convert_segmentations_to_bboxes(
        [
            Polygon(
                [10, 20, 40, 15, 35, 50, 12, 45],
                id=11,
                label=2,
                attributes={"source": "sam"},
                group=7,
                z_order=3,
            ),
            Bbox(1, 2, 3, 4, id=12, label=1),
        ]
    )

    assert [annotation.type for annotation in annotations] == [
        AnnotationType.bbox,
        AnnotationType.bbox,
    ]
    assert annotations[0].get_bbox() == [10, 15, 30, 35]
    assert annotations[0].id == 11
    assert annotations[0].label == 2
    assert annotations[0].attributes == {"source": "sam"}
    assert annotations[0].group == 7
    assert annotations[0].z_order == 3
    assert annotations[1].get_bbox() == [1, 2, 3, 4]


def test_yolo_detection_export_writes_polygon_as_bbox():
    for format_name in ("yolo", "yolo_ultralytics_detection"):
        dataset = Dataset.from_iterable(
            [
                DatasetItem(
                    id="frame",
                    media=Image.from_numpy(data=np.zeros((100, 200, 3), dtype=np.uint8)),
                    annotations=[
                        Polygon([20, 10, 100, 10, 100, 50, 20, 50], label=0)
                    ],
                )
            ],
            categories=["object"],
        )
        dataset.put(
            dataset.get("frame").wrap(
                annotations=_convert_segmentations_to_bboxes(
                    dataset.get("frame").annotations
                )
            )
        )

        with tempfile.TemporaryDirectory() as output_dir:
            dataset.export(output_dir, format_name, save_media=False)
            annotation_lines = [
                line
                for path in Path(output_dir).rglob("*.txt")
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.startswith("0 ")
            ]

        assert annotation_lines == ["0 0.300000 0.300000 0.400000 0.400000"]
