import boto3
import os

def create_table():
    # Configure AWS locally if needed, but preferably use AWS CLI or environment variables
    # For local dev without env vars set perfectly, you might need to supply region.
    # We will rely on boto3 finding credentials from environment variables or ~/.aws/credentials
    dynamodb = boto3.resource('dynamodb', region_name=os.getenv('AWS_REGION', 'ap-southeast-1'))
    table_name = os.getenv('DYNAMODB_TABLE', 'FamilyFixedDeposits')

    print(f"Creating DynamoDB table: {table_name}")
    try:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'deposit_id',
                    'KeyType': 'HASH'  # Partition key
                },
                {
                    'AttributeName': 'status',
                    'KeyType': 'RANGE'  # Sort key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'deposit_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'status',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'maturity_date',
                    'AttributeType': 'S'
                }
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'MaturityDateIndex',
                    'KeySchema': [
                        {
                            'AttributeName': 'status',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'maturity_date',
                            'KeyType': 'RANGE'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )

        print("Waiting for table to be created...")
        table.wait_until_exists()
        print(f"Table {table_name} created successfully!")
    except Exception as e:
        print(f"Error creating table: {e}")

if __name__ == "__main__":
    create_table()
