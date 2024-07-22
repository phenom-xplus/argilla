#  Copyright 2021-present, the Recognai S.L. team.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import uuid
from unittest.mock import MagicMock

import pytest
from argilla_server.enums import UserRole
from argilla_server.models import User
from argilla_server.telemetry import TelemetryClient
from fastapi import Request

mock_request = Request(scope={"type": "http", "headers": {}})


def test_disable_telemetry():
    telemetry_client = TelemetryClient(enable_telemetry=False)

    assert telemetry_client.enable_telemetry == False


__CRUD__ = ["create", "read", "update", "delete"]


@pytest.mark.asyncio
class TestSuiteTelemetry:
    async def test_track_user_login(self, test_telemetry: MagicMock):
        user = User(id=uuid.uuid4(), username="argilla")
        await test_telemetry.track_user_login(request=mock_request, user=user)

        test_telemetry.track_user_login.assert_called_once_with(request=mock_request, user=user)
        test_telemetry.track_data.assert_called()

    @pytest.mark.parametrize("is_oauth", [True, False])
    @pytest.mark.parametrize("username", ["argilla", "john"])
    @pytest.mark.parametrize("action", __CRUD__)
    async def test_user_crud(self, test_telemetry: MagicMock, username: str, is_oauth: bool, action: str):
        user = User(id=uuid.uuid4(), username=username, role=UserRole.owner)

        await test_telemetry.track_crud_user(action=action, user=user, is_oauth=is_oauth)

        test_telemetry.track_crud_user.assert_called_once_with(action=action, user=user, is_oauth=is_oauth)
        test_telemetry.track_data.assert_called()

    @pytest.mark.parametrize("is_oauth", [True, False])
    @pytest.mark.parametrize("username", ["argilla", "john"])
    @pytest.mark.parametrize("action", __CRUD__)
    async def track_crud_workspace(self, test_telemetry: MagicMock, username: str, is_oauth: bool, action: str):
        user = User(id=uuid.uuid4(), username=username, role=UserRole.owner)

        await test_telemetry.track_crud_user(action=action, user=user, is_oauth=is_oauth)

        test_telemetry.track_crud_user.assert_called_once_with(action=action, user=user, is_oauth=is_oauth)
        test_telemetry.track_data.assert_called()
