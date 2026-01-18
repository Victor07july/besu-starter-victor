"""
AWS Lambda Function para invocar contrato E1PoloCalculator
"""

import json
import boto3
import os
from web3 import Web3
from botocore.exceptions import ClientError

# Cliente para Secrets Manager
secrets_client = boto3.client('secretsmanager')

# ABI do contrato (será preenchido após compilação)
CONTRACT_ABI = [
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "uint256", "name": "distanceHighway", "type": "uint256"},
                    {"internalType": "uint256", "name": "distanceCity", "type": "uint256"},
                    {"internalType": "uint256", "name": "cityGasoline", "type": "uint256"},
                    {"internalType": "uint256", "name": "roadGasoline", "type": "uint256"},
                    {"internalType": "uint256", "name": "cityEthanol", "type": "uint256"},
                    {"internalType": "uint256", "name": "roadEthanol", "type": "uint256"},
                    {"internalType": "uint256", "name": "carbonPriceEuropean", "type": "uint256"},
                    {"internalType": "uint256", "name": "euroPrice", "type": "uint256"}
                ],
                "internalType": "struct E1PoloCalculator.VehicleData",
                "name": "data",
                "type": "tuple"
            }
        ],
        "name": "calculateAndRecordE1",
        "outputs": [
            {"internalType": "uint256", "name": "e1Value", "type": "uint256"}
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "vehicle", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "metaCO2", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "diff", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "e1Value", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"}
        ],
        "name": "E1Calculated",
        "type": "event"
    }
]


def get_secret(secret_name):
    """Recupera secret do AWS Secrets Manager"""
    try:
        response = secrets_client.get_secret_value(SecretId=secret_name)
        return json.loads(response['SecretString'])
    except ClientError as e:
        print(f"Erro ao recuperar secret {secret_name}: {str(e)}")
        raise e


def prepare_vehicle_data(row):
    """
    Converte dados do CSV para o formato do contrato
    """
    return (
        int(row.get('distance_highway', 0)),
        int(row.get('distance_city', 0)),
        int(row.get('city_gasoline', 13.5) * 1000),
        int(row.get('road_gasoline', 15.7) * 1000),
        int(row.get('city_ethanol', 9.3) * 1000),
        int(row.get('road_ethanol', 10.9) * 1000),
        int(row.get('carbon_price_european', 89.08) * 100),
        int(row.get('euro_price', 6.1708) * 10000)
    )


def invoke_smart_contract(w3, contract, account, vehicle_data):
    """
    Invoca o smart contract para calcular E1
    """
    try:
        # Construir transação
        nonce = w3.eth.get_transaction_count(account.address)
        
        tx = contract.functions.calculateAndRecordE1(
            vehicle_data
        ).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': 500000,
            'gasPrice': w3.eth.gas_price
        })
        
        # Assinar transação
        signed_tx = account.sign_transaction(tx)
        
        # Enviar transação
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        print(f"Transação enviada: {tx_hash.hex()}")
        
        # Aguardar confirmação
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        if receipt['status'] == 1:
            print(f"Transação confirmada no bloco {receipt['blockNumber']}")
            
            # Processar eventos
            events = contract.events.E1Calculated().process_receipt(receipt)
            if events:
                event = events[0]['args']
                return {
                    'success': True,
                    'tx_hash': tx_hash.hex(),
                    'block_number': receipt['blockNumber'],
                    'gas_used': receipt['gasUsed'],
                    'meta_co2': event['metaCO2'],
                    'diff': event['diff'],
                    'e1_value': event['e1Value'] / 1000000,  # Converter para BRL
                    'timestamp': event['timestamp']
                }
        else:
            return {
                'success': False,
                'error': 'Transaction failed',
                'tx_hash': tx_hash.hex()
            }
            
    except Exception as e:
        print(f"Erro ao invocar contrato: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def lambda_handler(event, context):
    """
    Handler principal da Lambda
    """
    try:
        print("=== Lambda E1 Polo Calculator Iniciada ===")
        print(f"Event: {json.dumps(event)}")
        
        # Parse do body se vier do API Gateway
        if 'body' in event:
            if isinstance(event['body'], str):
                body = json.loads(event['body'])
            else:
                body = event['body']
        else:
            body = event
        
        # Recuperar configurações do Secrets Manager
        print("Recuperando secrets...")
        blockchain_keys = get_secret('besu-blockchain-keys')
        contract_config = get_secret('besu-contract-config')
        
        RPC_URL = contract_config['RPC_URL']
        CONTRACT_ADDRESS = contract_config['CONTRACT_ADDRESS']
        SENDER_ADDRESS = blockchain_keys['SENDER_ADDRESS']
        PRIVATE_KEY = blockchain_keys['PRIVATE_KEY']
        
        print(f"RPC URL: {RPC_URL}")
        print(f"Contract: {CONTRACT_ADDRESS}")
        print(f"Sender: {SENDER_ADDRESS}")
        
        # Conectar à blockchain
        print("Conectando à blockchain...")
        # Desabilitar verificação SSL para certificados self-signed
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        w3 = Web3(Web3.HTTPProvider(
            RPC_URL,
            request_kwargs={'verify': False}
        ))
        
        if not w3.is_connected():
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Failed to connect to blockchain',
                    'rpc_url': RPC_URL
                })
            }
        
        print(f"Conectado! Chain ID: {w3.eth.chain_id}")
        
        # Carregar contrato
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACT_ADDRESS),
            abi=CONTRACT_ABI
        )
        
        # Configurar conta
        account = w3.eth.account.from_key(PRIVATE_KEY)
        
        # Verificar se é um lote ou item único
        if isinstance(body, list):
            records = body
        else:
            records = [body]
        
        print(f"Processando {len(records)} registro(s)...")
        
        results = []
        
        for idx, record in enumerate(records):
            print(f"\nProcessando registro {idx + 1}/{len(records)}...")
            
            try:
                # Preparar dados
                vehicle_data = prepare_vehicle_data(record)
                
                print(f"  Distância rodovia: {vehicle_data[0]} km")
                print(f"  Distância cidade: {vehicle_data[1]} km")
                
                # Invocar contrato
                result = invoke_smart_contract(w3, contract, account, vehicle_data)
                
                if result['success']:
                    print(f"  ✅ E1 calculado: {result['e1_value']:.6f} BRL")
                    results.append(result)
                else:
                    print(f"  ❌ Erro: {result['error']}")
                    results.append(result)
                    
            except Exception as e:
                print(f"  ❌ Erro ao processar registro: {str(e)}")
                results.append({
                    'success': False,
                    'error': str(e),
                    'record_index': idx
                })
        
        # Calcular estatísticas
        successful = [r for r in results if r.get('success')]
        failed = [r for r in results if not r.get('success')]
        
        total_gas = sum(r.get('gas_used', 0) for r in successful)
        total_e1 = sum(r.get('e1_value', 0) for r in successful)
        
        response = {
            'statusCode': 200 if len(failed) == 0 else 207,  # 207 = Multi-Status
            'body': json.dumps({
                'message': 'Processing completed',
                'summary': {
                    'total_records': len(records),
                    'successful': len(successful),
                    'failed': len(failed),
                    'total_gas_used': total_gas,
                    'total_e1_value': total_e1
                },
                'results': results
            })
        }
        
        print(f"\n=== Processamento Concluído ===")
        print(f"Sucesso: {len(successful)}/{len(records)}")
        print(f"Total E1: {total_e1:.6f} BRL")
        
        return response
        
    except Exception as e:
        print(f"❌ Erro fatal: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'type': type(e).__name__
            })
        }
