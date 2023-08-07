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

import argilla
import pytest
from argilla.server.apis.v0.models.commons.model import ScoreRange
from argilla.server.apis.v0.models.text_classification import (
    TextClassificationQuery,
    TextClassificationRecord,
)
from argilla.server.apis.v0.models.token_classification import TokenClassificationQuery
from argilla.server.commons.models import TaskType
from argilla.server.daos.backend import GenericElasticEngineBackend
from argilla.server.daos.backend.search.query_builder import EsQueryBuilder
from argilla.server.daos.models.datasets import BaseDatasetDB
from argilla.server.daos.records import DatasetRecordsDAO
from argilla.server.schemas.datasets import Dataset
from argilla.server.services.metrics import MetricsService, ServicePythonMetric
from argilla.server.services.search.model import ServiceSortConfig
from argilla.server.services.search.service import SearchRecordsService


@pytest.fixture
def backend():
    return GenericElasticEngineBackend.get_instance()


@pytest.fixture
def dao(backend: GenericElasticEngineBackend):
    return DatasetRecordsDAO.get_instance(es=backend)


@pytest.fixture
def metrics(dao: DatasetRecordsDAO):
    return MetricsService.get_instance(dao=dao)


@pytest.fixture
def service(dao: DatasetRecordsDAO, metrics: MetricsService):
    return SearchRecordsService.get_instance(dao=dao, metrics=metrics)


def test_query_builder_with_query_range(backend: GenericElasticEngineBackend):
    es_query = EsQueryBuilder().map_2_es_query(
        schema=None,
        query=TextClassificationQuery(score=ScoreRange(range_from=10)),
    )
    assert es_query == {
        "query": {
            "bool": {
                "filter": {
                    "bool": {
                        "minimum_should_match": 1,
                        "should": [{"range": {"score": {"gte": 10.0}}}],
                    }
                },
                "must": {"match_all": {}},
            }
        }
    }


def test_query_builder_with_nested(mocked_client, dao, backend: GenericElasticEngineBackend):
    argilla.init()
    dataset = BaseDatasetDB(
        name="test_query_builder_with_nested", workspace=argilla.get_workspace(), task=TaskType.token_classification
    )
    argilla.delete(dataset.name)
    argilla.log(
        name=dataset.name,
        records=argilla.TokenClassificationRecord(
            text="Michael is a professor at Harvard",
            tokens=["Michael", "is", "a", "professor", "at", "Harvard"],
            prediction=[("NAME", 0, 7, 0.9), ("LOC", 26, 33, 0.12)],
        ),
    )

    es_query = EsQueryBuilder().map_2_es_query(
        schema=dao._es.get_schema(dataset.id),
        query=TokenClassificationQuery(
            advanced_query_dsl=True,
            query_text="metrics.predicted.mentions:(label:NAME AND score:[* TO 0.1])",
        ),
    )

    assert es_query == {
        "query": {
            "bool": {
                "filter": {"bool": {"must": {"match_all": {}}}},
                "must": {
                    "nested": {
                        "path": "metrics.predicted.mentions",
                        "query": {
                            "bool": {
                                "must": [
                                    {"term": {"metrics.predicted.mentions.label": {"value": "NAME"}}},
                                    {"range": {"metrics.predicted.mentions.score": {"lte": "0.1"}}},
                                ]
                            }
                        },
                    }
                },
            }
        }
    }


def test_failing_metrics(service, mocked_client):
    argilla.init()

    dataset = BaseDatasetDB(
        name="test_failing_metrics",
        workspace=argilla.get_workspace(),
        task=TaskType.text_classification,
    )

    argilla.delete(dataset.name)
    argilla.log(argilla.TextClassificationRecord(text="This is a text, yeah!"), name=dataset.name)
    results = service.search(
        dataset=dataset,
        query=TextClassificationQuery(),
        sort_config=ServiceSortConfig(),
        metrics=[ServicePythonMetric(id="missing-metric", name="Missing metric")],
        size=0,
        record_type=TextClassificationRecord,
    )

    assert results.dict() == {
        "metrics": {"missing-metric": {}},
        "records": [],
        "total": 1,
    }