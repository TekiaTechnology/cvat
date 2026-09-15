# Copyright (C) CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT

from unittest import mock

import requests
from django.test import SimpleTestCase

from cvat.apps.lambda_manager.views import LambdaGateway


class LambdaGatewayTest(SimpleTestCase):
    def setUp(self):
        self.func = mock.Mock(id="test-function", port=32768)
        self.payload = {"image": "encoded-image"}

    @mock.patch("cvat.apps.lambda_manager.views.os.path.exists", return_value=True)
    @mock.patch("cvat.apps.lambda_manager.views.make_requests_session")
    def test_direct_invocation_uses_function_container_network(self, session_factory, _exists):
        session = session_factory.return_value.__enter__.return_value
        reply = session.post.return_value
        reply.json.return_value = ["result"]

        response = LambdaGateway()._invoke_directly(self.func, self.payload)

        self.assertEqual(response, ["result"])
        session.post.assert_called_once_with(
            "http://nuclio-nuclio-test-function:8080",
            timeout=120,
            json=self.payload,
        )

    @mock.patch("cvat.apps.lambda_manager.views.os.path.exists", return_value=True)
    @mock.patch("cvat.apps.lambda_manager.views.make_requests_session")
    def test_direct_invocation_falls_back_to_published_port(self, session_factory, _exists):
        session = session_factory.return_value.__enter__.return_value
        reply = mock.Mock()
        reply.json.return_value = ["result"]
        session.post.side_effect = [requests.ConnectionError, reply]

        response = LambdaGateway()._invoke_directly(self.func, self.payload)

        self.assertEqual(response, ["result"])
        self.assertEqual(
            session.post.call_args_list,
            [
                mock.call(
                    "http://nuclio-nuclio-test-function:8080",
                    timeout=120,
                    json=self.payload,
                ),
                mock.call(
                    "http://host.docker.internal:32768",
                    timeout=120,
                    json=self.payload,
                ),
            ],
        )

    @mock.patch("cvat.apps.lambda_manager.views.os.path.exists", return_value=False)
    @mock.patch("cvat.apps.lambda_manager.views.make_requests_session")
    def test_direct_invocation_outside_docker_uses_localhost(self, session_factory, _exists):
        session = session_factory.return_value.__enter__.return_value
        session.post.return_value.json.return_value = ["result"]

        LambdaGateway()._invoke_directly(self.func, self.payload)

        session.post.assert_called_once_with(
            "http://localhost:32768",
            timeout=120,
            json=self.payload,
        )
