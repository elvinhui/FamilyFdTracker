import boto3
from boto3.dynamodb.conditions import Key
import os
import uuid
from typing import List, Dict, Any

class DynamoDBHandler:
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb', region_name=os.getenv('AWS_REGION', 'ap-southeast-1'))
        self.table_name = os.getenv('DYNAMODB_TABLE', 'FamilyFixedDeposits')
        self.table = self.dynamodb.Table(self.table_name)

    def mask_account(self, account_str: str) -> str:
        if not account_str:
            return ""
        if len(account_str) <= 4:
            return account_str
        return "*" * 4 + account_str[-4:]

    def add_deposit(self, bank_code: str, account_full: str, principal: float, interest_rate: float, maturity_date: str) -> str:
        deposit_id = str(uuid.uuid4())
        account_tail = self.mask_account(account_full)
        
        item = {
            'deposit_id': deposit_id,
            'status': 'ACTIVE',
            'bank_code': bank_code,
            'account_tail': account_tail,
            'principal_amount': str(principal), # store as string/decimal for dynamodb compatibility usually, but can be Decimal
            'interest_rate': str(interest_rate),
            'maturity_date': maturity_date
        }
        
        self.table.put_item(Item=item)
        return deposit_id

    def get_all_active_deposits(self) -> List[Dict[str, Any]]:
        response = self.table.scan(
            FilterExpression=Key('status').eq('ACTIVE')
        )
        return response.get('Items', [])

    def get_deposits_by_maturity_date(self, target_date: str) -> List[Dict[str, Any]]:
        response = self.table.query(
            IndexName='MaturityDateIndex',
            KeyConditionExpression=Key('status').eq('ACTIVE') & Key('maturity_date').eq(target_date)
        )
        return response.get('Items', [])

    def update_status(self, deposit_id: str, current_status: str, new_status: str):
        # DynamoDB requires the full primary key (Partition + Sort) to update/delete
        # Since status is the sort key, changing status actually means creating a new item and deleting the old one
        response = self.table.get_item(
            Key={
                'deposit_id': deposit_id,
                'status': current_status
            }
        )
        if 'Item' in response:
            item = response['Item']
            # Delete old
            self.table.delete_item(
                Key={
                    'deposit_id': deposit_id,
                    'status': current_status
                }
            )
            # Add new
            item['status'] = new_status
            self.table.put_item(Item=item)
            return True
        return False
