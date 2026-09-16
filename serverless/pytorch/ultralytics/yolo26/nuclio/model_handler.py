# Copyright (C) CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT

import numpy as np
from ultralytics import YOLO


class ModelHandler:
    def __init__(self, labels):
        self.labels = labels
        self.model = YOLO("/opt/nuclio/model.pt", task="detect")

        if len(self.model.names) != len(self.labels):
            raise ValueError(
                "The model and data.yaml have different class counts: "
                f"{len(self.model.names)} != {len(self.labels)}"
            )

    def infer(self, image, threshold):
        prediction = self.model.predict(
            source=np.asarray(image),
            conf=threshold,
            device="cpu",
            verbose=False,
        )[0]

        results = []
        for box in prediction.boxes:
            class_id = int(box.cls.item())
            results.append(
                {
                    "confidence": str(float(box.conf.item())),
                    "label": self.labels[class_id],
                    "points": [float(value) for value in box.xyxy[0].tolist()],
                    "type": "rectangle",
                }
            )

        return results
