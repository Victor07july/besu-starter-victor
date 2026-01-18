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
            "anonymous": False,
            "inputs": [
                {
                    "indexed": True,
                    "internalType": "address",
                    "name": "vehicle",
                    "type": "address"
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "metaCO2",
                    "type": "uint256"
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "diff",
                    "type": "uint256"
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "e1Value",
                    "type": "uint256"
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "timestamp",
                    "type": "uint256"
                }
            ],
            "name": "E1Calculated",
            "type": "event"
        },
        {
            "inputs": [
                {
                    "components": [
                        {
                            "internalType": "uint256",
                            "name": "distanceHighway",
                            "type": "uint256"
                        },
                        {
                            "internalType": "uint256",
                            "name": "distanceCity",
                            "type": "uint256"
                        },
                        {
                            "internalType": "uint256",
                            "name": "cityGasoline",
                            "type": "uint256"
                        },
                        {
                            "internalType": "uint256",
                            "name": "roadGasoline",
                            "type": "uint256"
                        },
                        {
                            "internalType": "uint256",
                            "name": "cityEthanol",
                            "type": "uint256"
                        },
                        {
                            "internalType": "uint256",
                            "name": "roadEthanol",
                            "type": "uint256"
                        },
                        {
                            "internalType": "uint256",
                            "name": "carbonPriceEuropean",
                            "type": "uint256"
                        },
                        {
                            "internalType": "uint256",
                            "name": "euroPrice",
                            "type": "uint256"
                        }
                    ],
                    "internalType": "struct E1PoloCalculator.VehicleData",
                    "name": "data",
                    "type": "tuple"
                }
            ],
            "name": "calculateAndRecordE1",
            "outputs": [
                {
                    "internalType": "uint256",
                    "name": "e1Value",
                    "type": "uint256"
                }
            ],
            "stateMutability": "nonpayable",
            "type": "function"
        },
        {
            "inputs": [
                {
                    "components": [
                        {
                            "internalType": "uint256",
                            "name": "distanceHighway",
                            "type": "uint256"
                        },
                        {
                            "internalType": "uint256",
                            "name": "distanceCity",
                            "type": "uint256"
                        },
                        {
                            "internalType": "uint256",
                            "name": "cityGasoline",
                            "type": "uint256"
                        },
                        {
                            "internalType": "uint256",
                            "name": "roadGasoline",
                            "type": "uint256"
                        },
                        {
                            "internalType": "uint256",
                            "name": "cityEthanol",
                            "type": "uint256"
                        },
                        {
                            "internalType": "uint256",
                            "name": "roadEthanol",
                            "type": "uint256"
                        },
                        {
                            "internalType": "uint256",
                            "name": "carbonPriceEuropean",
                            "type": "uint256"
                        },
                        {
                            "internalType": "uint256",
                            "name": "euroPrice",
                            "type": "uint256"
                        }
                    ],
                    "internalType": "struct E1PoloCalculator.VehicleData",
                    "name": "data",
                    "type": "tuple"
                }
            ],
            "name": "calculateE1",
            "outputs": [
                {
                    "internalType": "uint256",
                    "name": "metaCO2",
                    "type": "uint256"
                },
                {
                    "internalType": "uint256",
                    "name": "diff",
                    "type": "uint256"
                },
                {
                    "internalType": "uint256",
                    "name": "e1Value",
                    "type": "uint256"
                }
            ],
            "stateMutability": "pure",
            "type": "function"
        },
        {
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "distanceHighway",
                    "type": "uint256"
                },
                {
                    "internalType": "uint256",
                    "name": "distanceCity",
                    "type": "uint256"
                }
            ],
            "name": "calculateE1ForPolo",
            "outputs": [
                {
                    "internalType": "uint256",
                    "name": "metaCO2",
                    "type": "uint256"
                },
                {
                    "internalType": "uint256",
                    "name": "diff",
                    "type": "uint256"
                },
                {
                    "internalType": "uint256",
                    "name": "e1Value",
                    "type": "uint256"
                }
            ],
            "stateMutability": "pure",
            "type": "function"
        },
        {
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "distanceHighway",
                    "type": "uint256"
                },
                {
                    "internalType": "uint256",
                    "name": "distanceCity",
                    "type": "uint256"
                }
            ],
            "name": "createDefaultPoloData",
            "outputs": [
                {
                    "components": [
                        {
                            "internalType": "uint256",
                            "name": "distanceHighway",
                            "type": "uint256"
                        },
                        {
                            "internalType": "uint256",
                            "name": "distanceCity",
                            "type": "uint256"
                        },
                        {
                            "internalType": "uint256",
                            "name": "cityGasoline",
                            "type": "uint256"
                        },
                        {
                            "internalType": "uint256",
                            "name": "roadGasoline",
                            "type": "uint256"
                        },
                        {
                            "internalType": "uint256",
                            "name": "cityEthanol",
                            "type": "uint256"
                        },
                        {
                            "internalType": "uint256",
                            "name": "roadEthanol",
                            "type": "uint256"
                        },
                        {
                            "internalType": "uint256",
                            "name": "carbonPriceEuropean",
                            "type": "uint256"
                        },
                        {
                            "internalType": "uint256",
                            "name": "euroPrice",
                            "type": "uint256"
                        }
                    ],
                    "internalType": "struct E1PoloCalculator.VehicleData",
                    "name": "",
                    "type": "tuple"
                }
            ],
            "stateMutability": "pure",
            "type": "function"
        }
    ]
# Cole aqui o BYTECODE que você recebeu do /compile-contract/
BYTECODE = "608060405234801561001057600080fd5b506108c1806100206000396000f3fe608060405234801561001057600080fd5b506004361061004b5760003560e01c8062a7aa2e146100505780630188fabd146100825780635252d8f9146100b4578063d047f141146100e4575b600080fd5b61006a600480360381019061006591906104f2565b610114565b6040516100799392919061064f565b60405180910390f35b61009c6004803603810190610097919061051c565b6102df565b6040516100ab9392919061064f565b60405180910390f35b6100ce60048036038101906100c991906104f2565b610308565b6040516100db9190610634565b60405180910390f35b6100fe60048036038101906100f9919061051c565b61037c565b60405161010b9190610618565b60405180910390f35b600080600080600090506000808660600151111561016b576103e8866060015187600001516106b8620f424061014a9190610783565b6101549190610783565b61015e9190610752565b6101689190610752565b91505b60008660a0015111156101b7576103e88660a0015187600001516105e6620f42406101969190610783565b6101a09190610783565b6101aa9190610752565b6101b49190610752565b90505b600081836101c591906106fc565b9050600080600089604001511115610216576103e889604001518a602001516106b8620f42406101f59190610783565b6101ff9190610783565b6102099190610752565b6102139190610752565b91505b600089608001511115610262576103e889608001518a602001516105e6620f42406102419190610783565b61024b9190610783565b6102559190610752565b61025f9190610752565b90505b6000818361027091906106fc565b9050808461027e91906106fc565b985060028961028d9190610752565b9750600060648b60e001518c60c001516102a79190610783565b6102b19190610783565b905064e8d4a51000818a6102c59190610783565b6102cf9190610752565b9750505050505050509193909250565b6000806000806102ef868661037c565b90506102fa81610114565b935093509350509250925092565b60008060008061031785610114565b9250925092503373ffffffffffffffffffffffffffffffffffffffff167ff5cce48855fc1a944955e62310888f11a15587e4ad6bdec82395deda160cf8ed848484426040516103699493929190610686565b60405180910390a2809350505050919050565b6103846103d2565b6040518061010001604052808481526020018381526020016134bc8152602001613d5481526020016124548152602001612a9481526020016122cc815260200161f10c815250905092915050565b60405180610100016040528060008152602001600081526020016000815260200160008152602001600081526020016000815260200160008152602001600081525090565b6000610100828403121561042a57600080fd5b6104356101006106cb565b90506000610445848285016104dd565b6000830152506020610459848285016104dd565b602083015250604061046d848285016104dd565b6040830152506060610481848285016104dd565b6060830152506080610495848285016104dd565b60808301525060a06104a9848285016104dd565b60a08301525060c06104bd848285016104dd565b60c08301525060e06104d1848285016104dd565b60e08301525092915050565b6000813590506104ec81610874565b92915050565b6000610100828403121561050557600080fd5b600061051384828501610417565b91505092915050565b6000806040838503121561052f57600080fd5b600061053d858286016104dd565b925050602061054e858286016104dd565b9150509250929050565b6101008201600082015161056f60008501826105fa565b50602082015161058260208501826105fa565b50604082015161059560408501826105fa565b5060608201516105a860608501826105fa565b5060808201516105bb60808501826105fa565b5060a08201516105ce60a08501826105fa565b5060c08201516105e160c08501826105fa565b5060e08201516105f460e08501826105fa565b50505050565b610603816107dd565b82525050565b610612816107dd565b82525050565b60006101008201905061062e6000830184610558565b92915050565b60006020820190506106496000830184610609565b92915050565b60006060820190506106646000830186610609565b6106716020830185610609565b61067e6040830184610609565b949350505050565b600060808201905061069b6000830187610609565b6106a86020830186610609565b6106b56040830185610609565b6106c26060830184610609565b95945050505050565b6000604051905081810181811067ffffffffffffffff821117156106f2576106f1610845565b5b8060405250919050565b6000610707826107dd565b9150610712836107dd565b9250827fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff03821115610747576107466107e7565b5b828201905092915050565b600061075d826107dd565b9150610768836107dd565b92508261077857610777610816565b5b828204905092915050565b600061078e826107dd565b9150610799836107dd565b9250817fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff04831182151516156107d2576107d16107e7565b5b828202905092915050565b6000819050919050565b7f4e487b7100000000000000000000000000000000000000000000000000000000600052601160045260246000fd5b7f4e487b7100000000000000000000000000000000000000000000000000000000600052601260045260246000fd5b7f4e487b7100000000000000000000000000000000000000000000000000000000600052604160045260246000fd5b61087d816107dd565b811461088857600080fd5b5056fea26469706673582212201200067352e603c5c1b451bf9c78c3ae11e7de4945c5ae9167e7c330d69b900564736f6c63430008000033"

# Parâmetros do construtor (ajuste conforme seu contrato)
# Para SimpleStorage que recebe _initialValue:
CONSTRUCTOR_PARAMS = [42]  # Valor inicial = 42

# Configurações de gas
GAS_LIMIT = 300  # 3 milhões (ajuste se necessário)

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


    # Essa parte que a rota deveria retornar
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
