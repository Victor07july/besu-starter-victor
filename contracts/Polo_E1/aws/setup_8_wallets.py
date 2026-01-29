"""
Script para SETUP de 8 carteiras paralelas (2 existentes + 6 novas)
- Inclui 2 carteiras do genesis.json (group1 e group2)
- Cria 6 novas carteiras (group3 até group8)
- Transfere ETH da carteira mãe para as 6 novas
Objetivo: Preparar 8 carteiras paralelas para processamento simultâneo
"""

import json
from web3 import Web3
from eth_account import Account
import time
from pathlib import Path
import urllib3

# Desabilitar warnings SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configurações da Blockchain
BESU_URL = "https://ec2-18-117-255-42.us-east-2.compute.amazonaws.com/user/"
CHAIN_ID = 1337

# Carteira mãe (genesis.json - tem 90,000 ETH)
MOTHER_WALLET = {
    "address": "0xfe3B557E8Fb62b89F4916B721be55cEb828dBd73",
    "private_key": "0x8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63"
}

# Carteiras existentes (genesis.json)
EXISTING_WALLETS = {
    "vehicle_group_1": {
        "address": "0x627306090abaB3A6e1400e9345bC60c78a8BEf57",
        "private_key": "0xc87509a1c067bbde78beb793e6fa76530b6382a4c0241e5e4a9ec0a0f44dc0d3"
    },
    "vehicle_group_2": {
        "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
        "private_key": "0xae6ae8e5ccbfb04590405997ee2d52d2b330726137b875053c36d94e974d162f"
    }
}

# Quantidade de ETH a transferir para cada nova carteira (1 ETH é mais que suficiente)
ETH_AMOUNT = 10  # 10 ETH por carteira para margem de segurança
GAS_PRICE = 0  # Gas é gratuito (zeroBaseFee: true)
GAS_LIMIT = 21000  # Gas padrão para transferência simples

# Arquivo de saída
OUTPUT_FILE = Path(__file__).parent / "wallets_8_groups.json"


def create_new_wallets(count=6):
    """Gera 'count' novas carteiras"""
    print(f"🔐 Gerando {count} novas carteiras...")
    new_wallets = {}
    
    for i in range(3, 3 + count):  # group3 até group8
        account = Account.create()
        group_name = f"vehicle_group_{i}"
        new_wallets[group_name] = {
            "address": account.address,
            "private_key": account.key.hex()
        }
        print(f"  ✅ {group_name}: {account.address}")
    
    return new_wallets


def transfer_eth_to_wallets(w3, new_wallets):
    """Transfere ETH da carteira mãe para as novas carteiras"""
    print(f"\n💸 Transferindo {ETH_AMOUNT} ETH para cada carteira...")
    
    # Conta mãe (converter para checksum)
    mother_address = Web3.to_checksum_address(MOTHER_WALLET["address"])
    mother_account = w3.eth.account.from_key(MOTHER_WALLET["private_key"])
    nonce = w3.eth.get_transaction_count(mother_address)
    
    receipts = {}
    
    for group_name, wallet in new_wallets.items():
        print(f"\n  📤 {group_name} ({wallet['address']})...")
        
        # Construir transação (converter endereço destino para checksum)
        to_address = Web3.to_checksum_address(wallet['address'])
        transaction = {
            'nonce': nonce,
            'to': to_address,
            'value': w3.to_wei(ETH_AMOUNT, 'ether'),
            'gas': GAS_LIMIT,
            'gasPrice': GAS_PRICE,
            'chainId': CHAIN_ID
        }
        
        # Assinar transação
        signed_txn = w3.eth.account.sign_transaction(transaction, MOTHER_WALLET["private_key"])
        
        # Enviar transação
        try:
            tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            print(f"    🔗 Transação enviada: {tx_hash.hex()}")
            
            # Aguardar confirmação
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            print(f"    ✅ Confirmada no bloco {receipt['blockNumber']}")
            
            receipts[group_name] = {
                "tx_hash": tx_hash.hex(),
                "block": receipt['blockNumber'],
                "status": receipt['status']
            }
            
            # Incrementar nonce para próxima transação
            nonce += 1
            
            # Pequena pausa entre transações
            time.sleep(2)
            
        except Exception as e:
            print(f"    ❌ Erro: {e}")
            receipts[group_name] = {"error": str(e)}
    
    return receipts


def save_wallets(all_wallets):
    """Salva todas as 8 carteiras em JSON"""
    print(f"\n💾 Salvando carteiras em {OUTPUT_FILE}...")
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(all_wallets, f, indent=2)
    
    print(f"  ✅ Arquivo salvo: {OUTPUT_FILE}")


def verify_balances(w3, all_wallets):
    """Verifica o saldo de todas as carteiras"""
    print("\n🔍 Verificando saldos finais...")
    
    for group_name, wallet in all_wallets.items():
        address = Web3.to_checksum_address(wallet['address'])
        balance_wei = w3.eth.get_balance(address)
        balance_eth = w3.from_wei(balance_wei, 'ether')
        print(f"  {group_name}: {balance_eth} ETH")


def main():
    print("=" * 60)
    print("🚀 CRIAÇÃO DE 8 CARTEIRAS PARALELAS")
    print("=" * 60)
    
    # Conectar à blockchain
    print(f"\n🔗 Conectando à blockchain: {BESU_URL}")
    w3 = Web3(Web3.HTTPProvider(
        BESU_URL,
        request_kwargs={'verify': False}
    ))
    
    if not w3.is_connected():
        print("❌ Erro: Não foi possível conectar à blockchain")
        return
    
    print(f"  ✅ Conectado! Chain ID: {w3.eth.chain_id}")
    
    # Verificar saldo da carteira mãe (converter para checksum)
    mother_address = Web3.to_checksum_address(MOTHER_WALLET["address"])
    mother_balance = w3.from_wei(w3.eth.get_balance(mother_address), 'ether')
    print(f"  💰 Saldo carteira mãe: {mother_balance} ETH")
    
    required_eth = ETH_AMOUNT * 6
    if mother_balance < required_eth:
        print(f"❌ Erro: Saldo insuficiente (precisa de {required_eth} ETH)")
        return
    
    # Criar novas carteiras
    new_wallets = create_new_wallets(count=6)
    
    # Transferir ETH para as novas carteiras
    receipts = transfer_eth_to_wallets(w3, new_wallets)
    
    # Combinar carteiras existentes + novas
    all_wallets = {**EXISTING_WALLETS, **new_wallets}
    
    # Salvar arquivo JSON
    save_wallets(all_wallets)
    
    # Verificar saldos finais
    verify_balances(w3, all_wallets)
    
    print("\n" + "=" * 60)
    print("✅ PROCESSO CONCLUÍDO!")
    print("=" * 60)
    print(f"\n📁 Arquivo gerado: {OUTPUT_FILE}")
    print("\n📋 Próximos passos:")
    print("  1. Criar secrets na AWS usando 'create_aws_secrets_8_groups.py'")
    print("  2. Atualizar Lambda 'blockchain' com reserved concurrency = 8")
    print("  3. Executar 'send_to_sqs_alternado.py' para processar os 8 CSVs")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
