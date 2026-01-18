"""
Script para assinar transação de deploy localmente
Gera a transação assinada em formato hexadecimal para enviar via Postman

USO:
1. Cole aqui o ABI e BYTECODE do contrato compilado
2. Rode o script: python sign_transaction.py
3. Copie a transação assinada que será exibida
4. Cole no Postman na rota POST /api/v1/besu/deploy-signed/
"""

import json
from web3 import Web3
from eth_account import Account

# ===========================
# CONFIGURAÇÃO
# ===========================

# RPC do Besu
BESU_RPC_URL = "http://localhost:8547"

# Sua chave privada (NUNCA compartilhe!)
PRIVATE_KEY = "8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63"

# Cole aqui o ABI que você recebeu do /compile-contract/
ABI = [
    {
        "inputs": [],
        "name": "favoriteInt",
        "outputs": [
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "uint256",
                "name": "_favoriteNumber",
                "type": "uint256"
            }
        ],
        "name": "store",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

# Cole aqui o BYTECODE que você recebeu do /compile-contract/
BYTECODE = "608060405234801561001057600080fd5b50610133806100206000396000f3fe6080604052348015600f57600080fd5b506004361060325760003560e01c80636057361d146037578063b9da175614604f575b600080fd5b604d60048036038101906049919060af565b6069565b005b60556073565b6040516060919060e4565b60405180910390f35b8060008190555050565b60005481565b600080fd5b6000819050919050565b608f81607e565b8114609957600080fd5b50565b60008135905060a9816088565b92915050565b60006020828403121560c25760c16079565b5b600060ce84828501609c565b91505092915050565b60de81607e565b82525050565b600060208201905060f7600083018460d7565b9291505056fea2646970667358221220a967bda5cf845c8c5de7331a3a879c8b72fd6c71190ae122a40ec7a725ccb87364736f6c63430008130033"

# Parâmetros do construtor (ajuste conforme seu contrato)
# Para SimpleStorage que recebe _initialValue:
CONSTRUCTOR_PARAMS = [42]  # Valor inicial = 42

# Configurações de gas
GAS_LIMIT = 3000000  # 3 milhões (ajuste se necessário)

# ===========================
# SCRIPT
# ===========================

def main():
    print("=" * 70)
    print("GERADOR DE TRANSAÇÃO ASSINADA PARA DEPLOY")
    print("=" * 70)
    
    # Conectar ao Besu
    print(f"\nConectando ao Besu em {BESU_RPC_URL}...")
    w3 = Web3(Web3.HTTPProvider(BESU_RPC_URL))
    
    if not w3.is_connected():
        print("Não foi possível conectar ao Besu!")
        print("   Verifique se o Besu está rodando e a URL está correta.")
        return
    
    print(f"✅ Conectado! Chain ID: {w3.eth.chain_id}")
    
    # Criar conta
    if not PRIVATE_KEY.startswith('0x'):
        private_key = '0x' + PRIVATE_KEY
    else:
        private_key = PRIVATE_KEY
    
    account = Account.from_key(private_key)
    deployer_address = account.address
    
    print(f"\n👤 Deployer: {deployer_address}")
    
    # Verificar saldo
    balance = w3.eth.get_balance(deployer_address)
    balance_eth = w3.from_wei(balance, 'ether')
    print(f"Saldo: {balance_eth} ETH")
    
    if balance == 0:
        print("ATENÇÃO: Saldo zero! A transação pode falhar.")
    
    # Adicionar 0x ao bytecode se não tiver
    if not BYTECODE.startswith('0x'):
        bytecode = '0x' + BYTECODE
    else:
        bytecode = BYTECODE
    
    # Criar contrato para encodar o construtor
    print(f"\nPreparando dados da transação...")
    contract = w3.eth.contract(abi=ABI, bytecode=bytecode)
    
    # Encodar dados do construtor
    if CONSTRUCTOR_PARAMS:
        print(f"   Parâmetros do construtor: {CONSTRUCTOR_PARAMS}")
        data = contract.constructor(*CONSTRUCTOR_PARAMS).data_in_transaction
    else:
        print("   Sem parâmetros no construtor")
        data = bytecode
    
    # Obter informações da rede
    nonce = w3.eth.get_transaction_count(deployer_address)
    gas_price = w3.eth.gas_price
    chain_id = w3.eth.chain_id
    
    print(f"\n📋 Informações da transação:")
    print(f"   Nonce: {nonce}")
    print(f"   Gas Limit: {GAS_LIMIT:,}")
    print(f"   Gas Price: {w3.from_wei(gas_price, 'gwei')} Gwei")
    print(f"   Chain ID: {chain_id}")
    
    # Estimar custo
    estimated_cost_wei = GAS_LIMIT * gas_price
    estimated_cost_eth = w3.from_wei(estimated_cost_wei, 'ether')
    print(f"   Custo estimado (máximo): {estimated_cost_eth} ETH")
    
    # Montar transação
    transaction = {
        'from': deployer_address,
        'nonce': nonce,
        'gas': GAS_LIMIT,
        'gasPrice': gas_price,
        'data': data,
        'chainId': chain_id,
        'value': 0  # Deploy não envia ETH
    }
    
    # Assinar transação
    print(f"\n Assinando transação localmente...")
    signed = account.sign_transaction(transaction)
    signed_tx_hex = signed.raw_transaction.hex()
    
    # Hash previsto
    tx_hash = signed.hash.hex()
    
    print(f"Transação assinada com sucesso!")
    print(f"   Hash (previsto): {tx_hash}")
    
    # ===========================
    # RESULTADO PARA COPIAR
    # ===========================
    print("\n" + "=" * 70)
    print("COPIE OS DADOS ABAIXO PARA O POSTMAN")
    print("=" * 70)
    
    print("\n URL:")
    print("POST http://localhost:8000/api/v1/besu/deploy-signed/")
    
    print("\n Headers:")
    print("Authorization: Bearer SEU_TOKEN_JWT")
    print("Content-Type: application/json")
    
    print("\n Body (raw JSON):")
    body = {
        "signed_transaction": signed_tx_hex
    }
    print(json.dumps(body, indent=2))
    
    print("\n" + "=" * 70)
    print("APENAS A TRANSAÇÃO ASSINADA (para copiar facilmente):")
    print("=" * 70)
    print(signed_tx_hex)
    
    # Salvar em arquivo também
    output_data = {
        "signed_transaction": signed_tx_hex,
        "transaction_hash_preview": tx_hash,
        "deployer_address": deployer_address,
        "nonce": nonce,
        "gas_limit": GAS_LIMIT,
        "gas_price": gas_price,
        "chain_id": chain_id,
        "constructor_params": CONSTRUCTOR_PARAMS
    }
    
    output_file = "signed_transaction.json"
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n Dados também salvos em: {output_file}")
    
    print("\n" + "=" * 70)
    print("PRONTO! Use a transação assinada no Postman")
    print("=" * 70)
    print("\n Lembre-se: Sua chave privada NUNCA foi enviada pela rede!")
    print("   Você está enviando apenas a transação JÁ ASSINADA.\n")


if __name__ == "__main__":
    main()
