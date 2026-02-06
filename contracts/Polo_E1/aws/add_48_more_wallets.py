"""
Script para ADICIONAR 48 carteiras adicionais (group17 até group64)
- Lê o arquivo wallets_16_groups.json existente (preserva groups 1-16)
- Cria 48 novas carteiras (group17 até group64)
- Transfere ETH da carteira mãe para as 48 novas
- Salva wallets_64_groups.json com todas as 64 carteiras
Objetivo: Escalar de 16 para 64 carteiras paralelas
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
BESU_URL = "https://ec2-18-218-85-118.us-east-2.compute.amazonaws.com/user/"
CHAIN_ID = 1337

# Carteira mãe (genesis.json)
MOTHER_WALLET = {
    "address": "0xfe3B557E8Fb62b89F4916B721be55cEb828dBd73",
    "private_key": "0x8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63"
}

# Quantidade de ETH a transferir para cada nova carteira
ETH_AMOUNT = 10  # 10 ETH por carteira
GAS_PRICE = 0  # Gas é gratuito (zeroBaseFee: true)
GAS_LIMIT = 21000  # Gas padrão para transferência simples

# Arquivos
INPUT_FILE = Path(__file__).parent / "wallets_16_groups.json"
OUTPUT_FILE = Path(__file__).parent / "wallets_64_groups.json"


def load_existing_wallets():
    """Carrega as 16 carteiras existentes do arquivo JSON"""
    print(f"📂 Carregando carteiras existentes de {INPUT_FILE}...")
    
    if not INPUT_FILE.exists():
        print(f"❌ Erro: Arquivo {INPUT_FILE} não encontrado!")
        print("   Execute primeiro o script add_8_more_wallets.py")
        return None
    
    with open(INPUT_FILE, 'r') as f:
        wallets = json.load(f)
    
    print(f"  ✅ Carregadas {len(wallets)} carteiras existentes (groups 1-16)")
    return wallets


def create_new_wallets(count=48):
    """Gera 'count' novas carteiras (group17 até group64)"""
    print(f"\n🔐 Gerando {count} novas carteiras...")
    new_wallets = {}
    
    for i in range(17, 17 + count):  # group17 até group64
        account = Account.create()
        group_name = f"vehicle_group_{i}"
        new_wallets[group_name] = {
            "address": account.address,
            "private_key": account.key.hex()
        }
        if i <= 20 or i % 10 == 0:  # Mostrar primeiros e múltiplos de 10
            print(f"  ✅ {group_name}: {account.address}")
    
    if count > 20:
        print(f"  ... ({count - 20} carteiras adicionais geradas)")
    
    return new_wallets


def transfer_eth_to_wallets(w3, new_wallets):
    """Transfere ETH da carteira mãe para as novas carteiras"""
    print(f"\n💸 Transferindo {ETH_AMOUNT} ETH para cada nova carteira...")
    print(f"   Total: {len(new_wallets)} transações")
    
    # Conta mãe (converter para checksum)
    mother_address = Web3.to_checksum_address(MOTHER_WALLET["address"])
    mother_account = w3.eth.account.from_key(MOTHER_WALLET["private_key"])
    nonce = w3.eth.get_transaction_count(mother_address)
    
    receipts = {}
    success_count = 0
    
    # Ordenar por número do grupo
    sorted_wallets = sorted(new_wallets.items(), key=lambda x: int(x[0].split('_')[-1]))
    
    for idx, (group_name, wallet) in enumerate(sorted_wallets, 1):
        group_num = int(group_name.split('_')[-1])
        
        # Mostrar progresso a cada 10 transações
        if idx == 1 or idx % 10 == 0 or idx == len(sorted_wallets):
            print(f"\n  [{idx}/{len(sorted_wallets)}] {group_name} ({wallet['address'][:10]}...)...")
        
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
            
            # Aguardar confirmação
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if idx == 1 or idx % 10 == 0 or idx == len(sorted_wallets):
                print(f"    ✅ Confirmada no bloco {receipt['blockNumber']}")
            
            receipts[group_name] = {
                "tx_hash": tx_hash.hex(),
                "block": receipt['blockNumber'],
                "status": receipt['status']
            }
            
            success_count += 1
            
            # Incrementar nonce para próxima transação
            nonce += 1
            
            # Pequena pausa entre transações
            time.sleep(1)
            
        except Exception as e:
            print(f"    ❌ Erro: {e}")
            receipts[group_name] = {"error": str(e)}
    
    print(f"\n  ✅ {success_count}/{len(sorted_wallets)} transações confirmadas")
    return receipts


def save_wallets(all_wallets):
    """Salva todas as 64 carteiras em JSON"""
    print(f"\n💾 Salvando carteiras em {OUTPUT_FILE}...")
    
    # Ordenar por número do grupo (vehicle_group_1, vehicle_group_2, ...)
    sorted_wallets = dict(sorted(all_wallets.items(), key=lambda x: int(x[0].split('_')[-1])))
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(sorted_wallets, f, indent=2)
    
    print(f"  ✅ Arquivo salvo: {OUTPUT_FILE}")


def verify_balances(w3, all_wallets):
    """Verifica o saldo de todas as carteiras (amostra)"""
    print("\n🔍 Verificando saldos (amostra)...")
    
    # Verificar primeiras 5, últimas 5, e algumas do meio
    sample_groups = []
    sorted_keys = sorted(all_wallets.keys(), key=lambda x: int(x.split('_')[-1]))
    
    # Primeiras 3
    sample_groups.extend(sorted_keys[:3])
    # Algumas do meio (group 16, 32, 48)
    for g in ['vehicle_group_16', 'vehicle_group_32', 'vehicle_group_48']:
        if g in all_wallets:
            sample_groups.append(g)
    # Últimas 3
    sample_groups.extend(sorted_keys[-3:])
    
    for group_name in sample_groups:
        wallet = all_wallets[group_name]
        address = Web3.to_checksum_address(wallet['address'])
        balance_wei = w3.eth.get_balance(address)
        balance_eth = w3.from_wei(balance_wei, 'ether')
        print(f"  {group_name}: {balance_eth} ETH")


def main():
    print("=" * 70)
    print("🚀 ADIÇÃO DE 48 CARTEIRAS ADICIONAIS (TOTAL: 64 CARTEIRAS)")
    print("=" * 70)
    
    # Carregar carteiras existentes
    existing_wallets = load_existing_wallets()
    if existing_wallets is None:
        return
    
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
    
    required_eth = ETH_AMOUNT * 48
    if mother_balance < required_eth:
        print(f"❌ Erro: Saldo insuficiente (precisa de {required_eth} ETH)")
        return
    
    print(f"  ✅ Saldo suficiente para criar 48 carteiras ({required_eth} ETH necessários)")
    
    # Criar novas carteiras (group17-64)
    new_wallets = create_new_wallets(count=48)
    
    # Transferir ETH para as novas carteiras
    receipts = transfer_eth_to_wallets(w3, new_wallets)
    
    # Combinar carteiras existentes (1-16) + novas (17-64)
    all_wallets = {**existing_wallets, **new_wallets}
    
    # Salvar arquivo JSON
    save_wallets(all_wallets)
    
    # Verificar saldos (amostra)
    verify_balances(w3, all_wallets)
    
    print("\n" + "=" * 70)
    print("✅ PROCESSO CONCLUÍDO!")
    print("=" * 70)
    print(f"\n📁 Arquivo gerado: {OUTPUT_FILE}")
    print(f"\n📊 Resumo:")
    print(f"  • Carteiras existentes (preservadas): 16")
    print(f"  • Carteiras criadas: 48")
    print(f"  • Total de carteiras: 64")
    print(f"  • ETH transferido: {ETH_AMOUNT * 48} ETH")
    print("\n📋 Próximos passos:")
    print("  1. Criar 48 novos secrets na AWS (group17-64) usando script atualizado")
    print("  2. Atualizar Lambda 'blockchain' com reserved concurrency = 64")
    print("  3. Atualizar código do Lambda com 64 grupos")
    print("  4. Executar script atualizado para processar os 64 CSVs")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
