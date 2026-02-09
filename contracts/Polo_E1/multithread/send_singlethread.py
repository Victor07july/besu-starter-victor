"""
Script para enviar dados do CSV para o contrato E1PoloCalculator na blockchain
"""

import pandas as pd
import json
from web3 import Web3
from pathlib import Path

# ======================================================================
# CONFIGURAÇÕES DA BLOCKCHAIN
# ======================================================================

# URL do nó RPC (rpcnode-user, sem autenticação)
RPC_URL = "http://localhost:8547"

# Conta que enviará as transações
SENDER_ADDRESS = "0xfe3b557e8fb62b89f4916b721be55ceb828dbd73"
PRIVATE_KEY = "0x8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63"

# Arquivo JSON com dados do deploy (ABI e endereço do contrato)
DEPLOYMENT_JSON = "deployment_result.json"

# ======================================================================
# FUNÇÃO PARA CONVERTER VALORES PARA O FORMATO DO CONTRATO
# ======================================================================

def prepare_vehicle_data(row):
    """
    Converte uma linha do DataFrame para o formato VehicleData do contrato
    
    Parâmetros esperados no contrato (multiplicados para precisão):
    - distanceHighway: km
    - distanceCity: km
    - cityGasoline: km/L * 1000
    - roadGasoline: km/L * 1000
    - cityEthanol: km/L * 1000
    - roadEthanol: km/L * 1000
    - carbonPriceEuropean: EUR * 100
    - euroPrice: BRL * 10000
    """
    
    return {
        'distanceHighway': int(row.get('distance_highway', 0)),
        'distanceCity': int(row.get('distance_city', 0)),
        'cityGasoline': int(row.get('city_gasoline', 13.5) * 1000),
        'roadGasoline': int(row.get('road_gasoline', 15.7) * 1000),
        'cityEthanol': int(row.get('city_ethanol', 9.3) * 1000),
        'roadEthanol': int(row.get('road_ethanol', 10.9) * 1000),
        'carbonPriceEuropean': int(row.get('Carbon_Price_European', 89.08) * 100),
        'euroPrice': int(row.get('Euro_price', 6.1708) * 10000)
    }

# ======================================================================
# FUNÇÃO PRINCIPAL
# ======================================================================

def main():
    print("=" * 70)
    print("ENVIANDO DADOS PARA O CONTRATO E1PoloCalculator")
    print("=" * 70)
    
    # 0. Carregar dados do deployment
    print("\n[0] Carregando dados do deployment...")
    deployment_file = Path(__file__).parent / DEPLOYMENT_JSON
    
    if not deployment_file.exists():
        print(f"❌ Erro: Arquivo não encontrado: {deployment_file}")
        print("   Execute o deploy primeiro com deploy_full_flow.py")
        return
    
    with open(deployment_file, 'r') as f:
        deployment_data = json.load(f)
    
    CONTRACT_ADDRESS = deployment_data.get('contract_address')
    CONTRACT_ABI = deployment_data.get('abi')
    
    if not CONTRACT_ADDRESS:
        print("❌ Erro: contract_address não encontrado no JSON")
        return
    
    if not CONTRACT_ABI:
        print("❌ Erro: abi não encontrada no JSON")
        return
    
    print(f"✅ Deployment carregado:")
    print(f"   Contract: {CONTRACT_ADDRESS}")
    print(f"   ABI: {len(CONTRACT_ABI)} funções")
    print(f"   Gas usado no deploy: {deployment_data.get('gas_used', 'N/A'):,}")
    
    # 1. Conectar à blockchain
    print("\n[1] Conectando à blockchain...")
    
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    
    # Adicionar middleware para redes PoA (QBFT/IBFT)
    from web3.middleware import ExtraDataToPOAMiddleware
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    
    if not w3.is_connected():
        print("❌ Erro: Não foi possível conectar à blockchain")
        print(f"   Verifique se o nó está rodando em {RPC_URL}")
        return
    
    print(f"✅ Conectado! Chain ID: {w3.eth.chain_id}")
    print(f"   Último bloco: {w3.eth.block_number}")
    
    # 2. Carregar o contrato
    print(f"\n[2] Carregando contrato em {CONTRACT_ADDRESS}...")
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(CONTRACT_ADDRESS),
        abi=CONTRACT_ABI
    )
    print("✅ Contrato carregado")
    
    # 3. Configurar conta
    print(f"\n[3] Configurando conta {SENDER_ADDRESS}...")
    account = w3.eth.account.from_key(PRIVATE_KEY)
    balance = w3.eth.get_balance(account.address)
    print(f"✅ Conta configurada")
    print(f"   Saldo: {w3.from_wei(balance, 'ether')} ETH")
    
    # 4. Ler dados do CSV
    print("\n[4] Lendo dados do CSV...")
    csv_path = Path(__file__).parent / "vehicle_data_1.csv"
    
    if not csv_path.exists():
        print(f"❌ Erro: Arquivo não encontrado: {csv_path}")
        return
    
    df = pd.read_csv(csv_path)
    print(f"✅ CSV carregado: {len(df)} linhas")
    
    # 6. Processar e enviar cada linha
    print(f"\n[5] Enviando dados para a blockchain...")
    print("-" * 70)
    
    results = []
    
    for idx, row in df.iterrows():
        print(f"\nProcessando linha {idx + 1}/{len(df)}...")
        
        try:
            # Preparar dados
            vehicle_data = prepare_vehicle_data(row)
            
            print(f"  → Distância rodovia: {vehicle_data['distanceHighway']} km")
            print(f"  → Distância cidade: {vehicle_data['distanceCity']} km")
            
            # Construir transação
            nonce = w3.eth.get_transaction_count(account.address)
            
            # Chamar função calculateAndRecordE1
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
            
            # Enviar transação (compatível com diferentes versões do web3.py)
            raw_tx = signed_tx.raw_transaction if hasattr(signed_tx, 'raw_transaction') else signed_tx.rawTransaction
            tx_hash = w3.eth.send_raw_transaction(raw_tx)
            print(f"  → TX enviada: {tx_hash.hex()}")
            
            # Aguardar confirmação
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt['status'] == 1:
                print(f"  ✅ Confirmada no bloco {receipt['blockNumber']}")
                
                # Processar eventos
                events = contract.events.E1Calculated().process_receipt(receipt)
                if events:
                    event = events[0]['args']
                    meta_co2 = event['metaCO2']
                    diff = event['diff']
                    e1_value = event['e1Value']
                    
                    print(f"  → Meta CO2: {meta_co2} g")
                    print(f"  → Diferença: {diff} g")
                    print(f"  → Valor E1: {e1_value / 1000000:.6f} BRL")
                    
                    results.append({
                        'linha': idx + 1,
                        'tx_hash': tx_hash.hex(),
                        'block': receipt['blockNumber'],
                        'gas_used': receipt['gasUsed'],
                        'meta_co2': meta_co2,
                        'diff': diff,
                        'e1_value': e1_value / 1000000
                    })
            else:
                print(f"  ❌ Transação falhou")
                
        except Exception as e:
            print(f"  ❌ Erro: {str(e)}")
            continue
    
    # 7. Resumo final
    print("\n" + "=" * 70)
    print("RESUMO")
    print("=" * 70)
    print(f"Total de linhas processadas: {len(results)}/{len(df)}")
    
    if results:
        df_results = pd.DataFrame(results)
        print(f"\nGas total usado: {df_results['gas_used'].sum()}")
        print(f"Valor E1 médio: {df_results['e1_value'].mean():.6f} BRL")
        print(f"Valor E1 total: {df_results['e1_value'].sum():.6f} BRL")
        
        # Salvar resultados
        output_file = Path(__file__).parent / "blockchain_results.csv"
        df_results.to_csv(output_file, index=False)
        print(f"\n✅ Resultados salvos em: {output_file}")

if __name__ == "__main__":
    main()
