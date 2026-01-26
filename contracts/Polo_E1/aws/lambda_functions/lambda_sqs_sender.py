"""
Lambda intermediário: Recebe do API Gateway e envia para SQS
Permite envio sem credenciais AWS locais
"""

import json
import boto3
import os
from datetime import datetime

# Cliente SQS
sqs = boto3.client('sqs', region_name='us-east-1')
SQS_QUEUE_URL = os.environ.get('SQS_QUEUE_URL', 'https://sqs.us-east-1.amazonaws.com/510805239628/polo-e1-queue.fifo')


def lambda_handler(event, context):
    """
    Recebe dados via API Gateway e envia para SQS FIFO
    
    Expected payload:
    {
        "records": [lista de registros],
        "message_group": "vehicle_group_1" ou "vehicle_group_2"
    }
    """
    
    try:
        # Parse body
        if 'body' in event:
            body = json.loads(event['body'])
        else:
            body = event
            
        records = body.get('records', [])
        message_group = body.get('message_group', 'vehicle_group_1')
        
        if not records:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'No records provided'})
            }
        
        # Enviar cada registro para SQS
        sent_count = 0
        failed_count = 0
        
        for idx, record in enumerate(records):
            try:
                # Preparar mensagem
                message_body = json.dumps({
                    'record': record,
                    'timestamp': datetime.now().isoformat()
                })
                
                # Enviar para SQS FIFO
                response = sqs.send_message(
                    QueueUrl=SQS_QUEUE_URL,
                    MessageBody=message_body,
                    MessageGroupId=message_group,
                    MessageDeduplicationId=f"{message_group}-{datetime.now().timestamp()}-{idx}"
                )
                
                sent_count += 1
                
            except Exception as e:
                print(f"❌ Erro ao enviar registro {idx}: {str(e)}")
                failed_count += 1
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Mensagens enviadas para SQS',
                'sent': sent_count,
                'failed': failed_count,
                'message_group': message_group
            })
        }
        
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
