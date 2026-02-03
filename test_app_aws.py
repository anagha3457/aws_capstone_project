import os
import boto3
from moto import mock_aws

# -------------------------------------------------
# Mock AWS Credentials (must exist before boto3)
# -------------------------------------------------
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
os.environ['AWS_SECURITY_TOKEN'] = 'testing'
os.environ['AWS_SESSION_TOKEN'] = 'testing'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

# -------------------------------------------------
# Start Moto Mock
# -------------------------------------------------
mock = mock_aws()
mock.start()

# Import your Flask app AFTER mock starts
from aws_app import app
import aws_app


def setup_infrastructure():
    print(">>> Creating Mock AWS Infrastructure...")

    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    sns = boto3.client('sns', region_name='us-east-1')

    # -------------------------------------------------
    # DynamoDB Tables (MATCH YOUR APP EXACTLY)
    # -------------------------------------------------

    # Users table (PK: user_id)
    dynamodb.create_table(
        TableName='Users',
        KeySchema=[{'AttributeName': 'user_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'user_id', 'AttributeType': 'S'}],
        ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
    )

    # AdminUsers table (PK: username)
    dynamodb.create_table(
        TableName='AdminUsers',
        KeySchema=[{'AttributeName': 'username', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'username', 'AttributeType': 'S'}],
        ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
    )

    # Campaigns table (PK: campaign_id)
    dynamodb.create_table(
        TableName='Campaigns',
        KeySchema=[{'AttributeName': 'campaign_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'campaign_id', 'AttributeType': 'S'}],
        ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
    )

    # UserActivity table (PK: user_id)
    dynamodb.create_table(
        TableName='UserActivity',
        KeySchema=[{'AttributeName': 'user_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'user_id', 'AttributeType': 'S'}],
        ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
    )

    # UserCampaigns table (PK: user_id)
    dynamodb.create_table(
        TableName='UserCampaigns',
        KeySchema=[{'AttributeName': 'user_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'user_id', 'AttributeType': 'S'}],
        ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
    )

    # Products table (PK: product_id)
    dynamodb.create_table(
        TableName='Products',
        KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
        ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
    )

    # -------------------------------------------------
    # SNS Topic
    # -------------------------------------------------
    response = sns.create_topic(Name='campaign_topic')
    aws_app.SNS_TOPIC_ARN = response['TopicArn']

    print(f">>> SNS Topic Created: {aws_app.SNS_TOPIC_ARN}")
    print(">>> Mock AWS Environment Ready.")


# -------------------------------------------------
# Run Flask App
# -------------------------------------------------
if __name__ == '__main__':
    try:
        setup_infrastructure()
        print("\n>>> Starting Flask Server at http://localhost:5000")
        print(">>> Press CTRL+C to stop (mock data will reset)")
        app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
    finally:
        mock.stop()
