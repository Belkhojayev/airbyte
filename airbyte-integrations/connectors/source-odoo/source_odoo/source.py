import json
from datetime import datetime
import traceback
from typing import Dict, Generator, Mapping, Any, Tuple, List

from airbyte_cdk.logger import AirbyteLogger
from airbyte_cdk.sources import AbstractSource
from airbyte_cdk.sources.streams import Stream

from .streams import (
    SaleOrder, PurchaseOrder, AccountsBankStatement, AccountPayment,
    AccountMove, ResPartner, AccountMoveLine, AccountAnalyticTag
)


class SourceOdoo(AbstractSource):

    def check_connection(self, logger: AirbyteLogger, config: Mapping[str, Any]) -> Tuple[bool, Any]:
        logger.info("Checking access ...")
        try:
            odoo_stream = SaleOrder(config=config)
            client = odoo_stream.get_client()
            return True, None
        except Exception as e:
            return False, f"An exception occurred: {str(e)}"

    def streams(self, config: Mapping[str, Any]) -> List[Stream]:

        return [
            SaleOrder(config=config),
            # PurchaseOrder(config=config),
            # AccountsBankStatement(config=config),
            # AccountPayment(config=config),
            AccountMove(config=config),
            ResPartner(config=config),
            AccountMoveLine(config=config),
            AccountAnalyticTag(config=config),
        ]
