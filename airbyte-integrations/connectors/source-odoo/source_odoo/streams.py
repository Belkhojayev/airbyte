from abc import ABC, abstractmethod
from typing import Any, Mapping, List, Iterable
from datetime import datetime, timedelta

from airbyte_cdk.sources.streams.core import Stream, IncrementalMixin
from airbyte_cdk.models import AirbyteStream, SyncMode
import erppeek


class OdooStream(Stream, ABC):

    primary_key = None

    def __init__(self, config: Mapping[str, Any], **kwargs) -> None:
        self.SERVER = config["SERVER"]
        self.DATABASE = config["DATABASE"]
        self.USERNAME = config["USERNAME"]
        self.PASSWORD = config["PASSWORD"]
        self.chunk_size = config["chunk_size"]
        self.end_date = config["end_date"]

    @property
    @abstractmethod
    def model_name(self) -> str:
        """
        Override to define a Odoo model name.

        The value returned from this method is the model to read from Odoo. Possible models are:
        sale.order, purchase.order, account.bank.statement, account.payment

        :return: Model name
        """

    @property
    @abstractmethod
    def fields(self) -> List[str]:
        """
        Override to define a Odoo model fields.

        The value returned from this method is the list of fields to read from the model.

        :return: fields
        """

    @property
    def search_conditions(self) -> List[tuple]:
        """
        Override to define a Odoo model search conditions.

        The value returned from this method is the list of search conditions to filter ids.
        Default return value is empty list which means there are no conditions. Override if
        model has search conditions. For example: search_conditions = [('some_field', '=', 'some_value')]
        """
        return []

    def get_client(self) -> erppeek.Client:
        client = erppeek.Client(
            self.SERVER, self.DATABASE, self.USERNAME, self.PASSWORD
        )

        return client

    def get_records(self, search_conditions: List[tuple]) -> List[dict]:
        client = self.get_client()
        model = client.model(self.model_name)
        print('=== SEARCH STARTED ===', datetime.now())
        all_ids = model.search(search_conditions)
        print('=== SEARCH ENDED ===', datetime.now())
        print(f'=== {len(all_ids)} records will be read ===')
        # all_ids = all_ids[:10]  # to test
        records = []
        ids_parts = [all_ids[i:i + self.chunk_size] for i in range(0, len(all_ids), self.chunk_size)]
        number_of_iterations = len(ids_parts)
        print(f'=== {number_of_iterations} iterations ===')
        for i, ids_part in enumerate(ids_parts):
            records_part = model.read(ids_part, self.fields)
            if not records_part:
                records_part = []
            records.extend(records_part)
            print(f'=== Records read in chunk #{i + 1}: {len(records_part)}, total: {len(records)} ===')

        return records

    def read_records(
            self,
            sync_mode: SyncMode,
            cursor_field: List[str] = None,
            stream_slice: Mapping[str, Any] = None,
            stream_state: Mapping[str, Any] = None,
    ) -> Iterable[Mapping[str, Any]]:
        records = self.get_records(self.search_conditions)

        yield from records


class OdooIncrementalStream(OdooStream, IncrementalMixin, ABC):

    _cursor_value = datetime.min.isoformat()

    @property
    def state(self) -> Mapping[str, Any]:
        return {self.cursor_field: self._cursor_value}

    @state.setter
    def state(self, value: Mapping[str, Any]):
        self._cursor_value = value[self.cursor_field]

    def read_records(
            self,
            sync_mode: SyncMode,
            cursor_field: List[str] = None,
            stream_slice: Mapping[str, Any] = None,
            stream_state: Mapping[str, Any] = None,
    ) -> Iterable[Mapping[str, Any]]:
        if sync_mode == SyncMode.full_refresh:
            for record in super().read_records(sync_mode, cursor_field, stream_slice, stream_state):
                yield record
        else:
            last_write_date = self.state[self.cursor_field] if self.cursor_field in self.state else datetime.min.isoformat()
            incremental_search_conditions = self.search_conditions + [(self.cursor_field, '>', last_write_date)]
            print(f'=== Search condition: {incremental_search_conditions[1:]} ===')
            records = self.get_records(incremental_search_conditions)

            last_write_date = datetime.fromisoformat(last_write_date)
            for record in records:
                last_write_date = max(last_write_date, datetime.fromisoformat(record[self.cursor_field]))
                yield record

            if records:
                last_write_date += timedelta(seconds=1)
            self.state = {self.cursor_field: last_write_date.isoformat()}


class SaleOrder(OdooIncrementalStream):

    model_name = 'sale.order'
    fields = [
        'id', 'display_name', 'partner_id', 'invoice_ids',
        'order_line',  'hubspot_id', 'create_date', 'write_date'
    ]
    cursor_field = 'write_date'


class PurchaseOrder(OdooIncrementalStream):

    model_name = 'purchase.order'
    fields = ['id', 'display_name', 'partner_id', 'order_line', 'amount_total', 'create_date', 'write_date']
    cursor_field = 'write_date'


class AccountsBankStatement(OdooIncrementalStream):

    model_name = 'account.bank.statement'
    fields = ['id', 'balance_end', 'balance_end_real', 'balance_start', 'company_id', 'date',
              'foreign_currency_balance_end_real', 'foreign_currency_balance_start',
              'foreign_currency_journal_id', 'is_valid_balance_start', 'journal_id', 'create_date', 'write_date']
    cursor_field = 'write_date'


class AccountPayment(OdooIncrementalStream):

    model_name = 'account.payment'
    fields = ['id', 'display_name', 'payment_method_id', 'payment_type',
              'company_id', 'amount_total', 'create_date', 'write_date']
    cursor_field = 'write_date'


class AccountMove(OdooIncrementalStream):

    model_name = 'account.move'
    fields = ['move_type', 'name', 'date', 'partner_id', 'partner_vat', 'invoice_date',
              'invoice_date_due', 'company_id', 'amount_untaxed_signed','amount_total_signed',
              'sale_order_id', 'sale_order_name','hubspot_deals', 'state', 'payment_state',
              'invoice_line_ids', 'create_date', 'write_date']
    cursor_field = 'write_date'
    search_conditions = [('state', '=', 'posted')]


class ResPartner(OdooIncrementalStream):

    model_name = 'res.partner'
    fields = ['id', 'name', 'hubspot_id', 'create_date', 'write_date', 'email','email2','email_formatted','email_normalized']
    cursor_field = 'write_date'

    @property
    def search_conditions(self) -> List[tuple]:
        client = self.get_client()
        account_model = client.model('account.move')
        account_ids = account_model.search([('state', '=', 'posted')])
        # account_ids = account_ids[:1000]  # to test
        account_records = account_model.read(account_ids, ['partner_id'])

        partner_ids = [record['partner_id'][0] for record in account_records if type(record['partner_id']) != bool]
        search_conditions_ = [('id', 'in', partner_ids)]

        return search_conditions_


class AccountMoveLine(OdooIncrementalStream):

    model_name = 'account.move.line'
    fields = ['id', 'move_id', 'product_id', 'quantity', 'price_unit',
              'create_date', 'write_date', 'price_subtotal', 'analytic_tag_ids']
    cursor_field = 'write_date'

    @property
    def search_conditions(self) -> List[tuple]:
        client = self.get_client()
        account_model = client.model('account.move')
        move_ids = account_model.search([('state', '=', 'posted')])
        # move_ids = move_ids[:1000]   # to test
        search_conditions_ = [('move_id', 'in', move_ids)]
        if self.end_date is not None and self.end_date != '':
            search_conditions_.append((self.cursor_field, '<=', self.end_date))

        return search_conditions_


class AccountAnalyticTag(OdooIncrementalStream):

    model_name = 'account.analytic.tag'
    fields = ['id', 'name', 'display_name', 'active',  'active_analytic_distribution', 'analytic_distribution_ids',
              'color', 'company_id', 'create_uid', 'write_uid', 'create_date', 'write_date']
    cursor_field = 'write_date'
