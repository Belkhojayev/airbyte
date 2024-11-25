#
# Copyright (c) 2024 Airbyte, Inc., all rights reserved.
#

from airbyte_cdk.sources import AbstractSource
from airbyte_cdk.sources.streams import Stream
from airbyte_cdk.sources.streams.http.requests_native_auth import TokenAuthenticator


from abc import ABC, abstractmethod
from typing import Any, Iterable, Mapping, MutableMapping, Optional, Union, List, Tuple
import json

import requests
from airbyte_cdk.sources.streams.http import HttpStream


# Basic full refresh stream
class SourceSplititNew(HttpStream, ABC):

    url_base = "https://reportingsystem-api.production.splitit.com/api/v1/reports/generate-report"
    http_method = "POST"

    def __init__(self, config: Mapping[str, Any], **kwargs) -> None:
        super().__init__(**kwargs)
        # self.merchant_id = config["merchant_id"]
        self.api_username = config["api_username"]
        self.api_password = config["api_password"]
        self.start_date = config["start_date"]
        self.end_date = config["end_date"]

    def _get_session_id(self) -> str:
        url = "https://id.production.splitit.com/connect/token"

        request_body = {
            'grant_type': 'client_credentials',
            'scope': 'dataretrieval.api reportingSystem.config.api reportingSystem.operation.api',
            'client_id': self.api_username,
            'client_secret': self.api_password
        }
        # 'api.v1 api.v2 api.v3 reportingSystem.fileoperations.api reports.api'
        response = requests.post(url, data=request_body)
        response.raise_for_status()
        return response.json()['access_token']

    @property
    @abstractmethod
    def report_code(self) -> str:
        """
        Override to define a report code.

        The value returned from this method is passed as parameter in request body. Possible values are:
        Finance.Reconciliation, Finance.OutstandingAmounts, Finance.NewPlans,
        Funding.MerchantFunding, Funding.CollectFromMerchant.

        :return: Report code
        """

    def next_page_token(self, response: requests.Response) -> Optional[Mapping[str, Any]]:

        return None

    def path(
            self,
            *,
            stream_state: Mapping[str, Any] = None,
            stream_slice: Mapping[str, Any] = None,
            next_page_token: Mapping[str, Any] = None,
    ) -> str:

        return ""

    def request_params(
            self,
            stream_state: Mapping[str, Any],
            stream_slice: Mapping[str, any] = None,
            next_page_token: Mapping[str, Any] = None
    ) -> MutableMapping[str, Any]:

        return {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'Authorization': f'Bearer {self._get_session_id()}'
                }

    def request_body_data(
            self,
            stream_state: Mapping[str, Any],
            stream_slice: Mapping[str, Any] = None,
            next_page_token: Mapping[str, Any] = None,
    ) -> Optional[Union[Mapping, str]]:

        payload = json.dumps({
            "ReportCode": self.report_code,
            "From": self.start_date,
            "To": self.end_date,
            "Format": "JSON",
            "SelectedColumns": [
                "Merchant_Name",
                "Plan_Number"
            ]
        })

        return payload

    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
            print("Response status:")
            print(response.status_code)
            try:
                print(response.json())
                # data_parsed = dict(response.json())["Data"]["DataResponse"]["Data"]["ReportItems"]
                # print(f'The number of report items for {self.report_code} is {len(data_parsed)}')
                #
                # for record in data_parsed:
                #     record["MerchantId"] = self.merchant_id
                # yield from data_parsed
                yield response.json()
            except (TypeError, KeyError):
                print(f'Request returned no data for {self.report_code}:')
                print(response.json())



class Reconciliation(SplititNewStream):
    report_code = "ReconciliationReport"


class OutstandingAmounts(SplititNewStream):
    report_code = "OutstandingAmountsReport"


class NewPlans(SplititNewStream):
    report_code = "NewPlansReport"
