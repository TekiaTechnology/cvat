# Copyright (C) CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT

import base64
import io
import json

import yaml
from PIL import Image

from model_handler import ModelHandler


def init_context(context):
    context.logger.info("Init context... 0%")

    with open("/opt/nuclio/data.yaml", encoding="utf-8") as data_file:
        data = yaml.safe_load(data_file)

    names = data["names"]
    if isinstance(names, list):
        labels = dict(enumerate(names))
    else:
        labels = {int(class_id): name for class_id, name in names.items()}

    context.user_data.model = ModelHandler(labels)
    context.logger.info("Init context...100%")


def handler(context, event):
    data = event.body
    image = Image.open(io.BytesIO(base64.b64decode(data["image"]))).convert("RGB")
    threshold = float(data.get("threshold", 0.25))
    results = context.user_data.model.infer(image, threshold)

    return context.Response(
        body=json.dumps(results),
        headers={},
        content_type="application/json",
        status_code=200,
    )
