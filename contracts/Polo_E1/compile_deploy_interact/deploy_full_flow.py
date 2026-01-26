"""
Script completo para fazer deploy de contrato Solidity via API
Fluxo completo automatizado:
1. Login na API (obter JWT token)
2. Compilar contrato e obter transaction object
3. Assinar transação localmente
4. Fazer deploy da transação assinada

USO:
    python deploy_full_flow.py

Configuração:
    - Ajuste as constantes abaixo conforme seu ambiente
    - Coloque o caminho do arquivo .sol
    - Configure deployer_address e private_key
"""

import requests
import json
from eth_account import Account
from pathlib import Path

# ===========================
# CONFIGURAÇÃO
# ===========================

# API Configuration
API_BASE_URL = "https://localhost/api/v1"  # Ou http://localhost:8000/api/v1 se local
VERIFY_SSL = False  # False para localhost com certificado self-signed

# JWT Token (OPCIONAL - se já tiver um token, cole aqui para pular o login)
# Deixe como None para fazer login automaticamente
JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoyLCJlbWFpbCI6InZpY3RvckBnbWFpbC5jb20iLCJleHAiOjE3Njg1ODU1MjAsImlhdCI6MTc2ODQxMjcyMC43NjgwODl9.ZRBxr4QNWX264YU5FbZRN0WsJf5Vf0V52Vg7y7SaAno"
# Credenciais de login (usado apenas se JWT_TOKEN for None)
USERNAME = "victor@gmail.com"
PASSWORD = "Teste@123"

# Contrato
CONTRACT_FILE_PATH = "/home/victor/besu-starter-victor/contracts/Polo_E1/contract/e1_polo.sol"  # Ajuste o caminho
CONSTRUCTOR_PARAMS = [42]  # Ajuste conforme seu contrato
GAS_LIMIT = 3000000

# Deployer (quem vai fazer o deploy)
DEPLOYER_ADDRESS = "0xfe3b557e8fb62b89f4916b721be55ceb828dbd73"
PRIVATE_KEY = "0x8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63"

# ===========================
# FUNÇÕES
# ===========================

def print_section(title):
    """Imprime separador visual"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def login(username, password):
    """
    Faz login na API e retorna o JWT token
    
    Returns:
        str: JWT token ou None se falhar
    """
    print_section("1. LOGIN")
    
    url = f"{API_BASE_URL}/auth/signin/"
    
    # Dados do login (form-data)
    data = {
        "username": username,
        "password": password
    }
    
    print(f"🔑 Fazendo login com usuário: {username}")
    
    try:
        response = requests.post(
            url,
            data=data,
            verify=VERIFY_SSL
        )
        response.raise_for_status()
        
        result = response.json()
        
        # API pode retornar 'token' ou 'access_token'
        token = result.get("access_token") or result.get("token")
        
        if token:
            print(f"✅ Login bem-sucedido!")
            print(f"   Token: {token[:50]}...")
            return token
        else:
            print("❌ Token não encontrado na resposta")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro ao fazer login: {e}")
        if hasattr(e.response, 'text'):
            print(f"   Resposta: {e.response.text}")
        return None


def compile_contract(token, contract_path, deployer_address, constructor_params, gas_limit):
    """
    Compila o contrato e retorna o transaction object pronto para assinar
    
    Returns:
        dict: Dados da compilação (abi, bytecode, transaction) ou None
    """
    print_section("2. COMPILAR CONTRATO")
    
    url = f"{API_BASE_URL}/besu/compile-contract/"
    
    # Ler arquivo do contrato
    contract_file = Path(contract_path)
    if not contract_file.exists():
        print(f"❌ Arquivo não encontrado: {contract_path}")
        return None
    
    print(f"📄 Compilando: {contract_file.name}")
    print(f"   Deployer: {deployer_address}")
    print(f"   Constructor params: {constructor_params}")
    print(f"   Gas limit: {gas_limit:,}")
    
    # Headers com token
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # Form-data
    files = {
        "contract_file": (contract_file.name, open(contract_path, "rb"), "text/plain")
    }
    
    data = {
        "deployer_address": deployer_address,
        "constructor_params": json.dumps(constructor_params),
        "gas_limit": gas_limit
    }
    
    try:
        response = requests.post(
            url,
            headers=headers,
            files=files,
            data=data,
            verify=VERIFY_SSL
        )
        response.raise_for_status()
        
        result = response.json()
        
        if result.get("success"):
            print("✅ Compilação bem-sucedida!")
            print(f"   ABI: {len(result.get('abi', []))} funções")
            print(f"   Bytecode: {len(result.get('bytecode', ''))} caracteres")
            
            if result.get("transaction"):
                tx = result["transaction"]
                print(f"\n📋 Transaction preparada:")
                print(f"   From: {tx.get('from')}")
                print(f"   Nonce: {tx.get('nonce')}")
                print(f"   Gas: {tx.get('gas'):,}")
                print(f"   Gas Price: {tx.get('gasPrice')} wei")
                print(f"   Chain ID: {tx.get('chainId')}")
                
            return result
        else:
            print(f"❌ Erro na compilação: {result.get('error_message')}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro ao compilar: {e}")
        if hasattr(e.response, 'text'):
            print(f"   Resposta: {e.response.text}")
        return None


def sign_transaction(transaction, private_key):
    """
    Assina a transação localmente usando a chave privada
    
    Returns:
        str: Transação assinada em hex ou None
    """
    print_section("3. ASSINAR TRANSAÇÃO")
    
    print(f"🔐 Assinando transação localmente...")
    
    try:
        # Criar account
        if not private_key.startswith('0x'):
            private_key = '0x' + private_key
        
        account = Account.from_key(private_key)
        print(f"   Account: {account.address}")
        
        # Assinar
        signed = account.sign_transaction(transaction)
        signed_tx_hex = signed.raw_transaction.hex()
        
        print(f"✅ Transação assinada!")
        print(f"   Hash previsto: {signed.hash.hex()}")
        print(f"   Signed TX: {signed_tx_hex[:50]}...")
        
        return signed_tx_hex
        
    except Exception as e:
        print(f"❌ Erro ao assinar: {e}")
        return None


def deploy_signed_transaction(token, signed_transaction):
    """
    Envia a transação assinada para a API fazer o deploy
    
    Returns:
        dict: Resultado do deploy ou None
    """
    print_section("4. DEPLOY")
    
    url = f"{API_BASE_URL}/besu/deploy-signed/"
    
    print(f"🚀 Enviando transação assinada para deploy...")
    
    # Headers
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Body
    body = {
        "signed_transaction": signed_transaction
    }
    
    try:
        response = requests.post(
            url,
            headers=headers,
            json=body,
            verify=VERIFY_SSL
        )
        response.raise_for_status()
        
        result = response.json()
        
        if result.get("success"):
            print("✅ Deploy bem-sucedido!")
            print(f"\n📍 Contract Address: {result.get('contract_address')}")
            print(f"🔗 Transaction Hash: {result.get('transaction_hash')}")
            print(f"⛽ Gas usado: {result.get('gas_used'):,}")
            
            return result
        else:
            print(f"❌ Erro no deploy: {result.get('error_message')}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro ao fazer deploy: {e}")
        if hasattr(e.response, 'text'):
            print(f"   Resposta: {e.response.text}")
        return None


# ===========================
# FLUXO PRINCIPAL
# ===========================

def main():
    print("\n" + "🎯 "+"="*66 + " 🎯")
    print("     DEPLOY AUTOMATIZADO DE CONTRATO SOLIDITY VIA API")
    print("🎯 "+"="*66 + " 🎯")
    
    # Desabilitar avisos de SSL se não verificar certificado
    if not VERIFY_SSL:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        print("\n⚠️  Verificação SSL desabilitada (certificado self-signed)")
    
    # Etapa 1: Obter Token
    if JWT_TOKEN:
        print_section("1. USANDO TOKEN PRÉ-CONFIGURADO")
        token = JWT_TOKEN
        print(f"✅ Token configurado manualmente")
        print(f"   Token: {token[:50]}...")
    else:
        # Fazer login para obter token
        token = login(USERNAME, PASSWORD)
        if not token:
            print("\n❌ Falha no login. Abortando.")
            return
    
    # Etapa 2: Compilar
    compilation_result = compile_contract(
        token=token,
        contract_path=CONTRACT_FILE_PATH,
        deployer_address=DEPLOYER_ADDRESS,
        constructor_params=CONSTRUCTOR_PARAMS,
        gas_limit=GAS_LIMIT
    )
    
    if not compilation_result or not compilation_result.get("transaction"):
        print("\n❌ Falha na compilação. Abortando.")
        return
    
    transaction = compilation_result["transaction"]
    
    # Etapa 3: Assinar
    signed_tx = sign_transaction(transaction, PRIVATE_KEY)
    if not signed_tx:
        print("\n❌ Falha ao assinar transação. Abortando.")
        return
    
    # Etapa 4: Deploy
    deploy_result = deploy_signed_transaction(token, signed_tx)
    if not deploy_result:
        print("\n❌ Falha no deploy. Abortando.")
        return
    
    # Sucesso!
    print_section("✨ SUCESSO")
    print(f"🎉 Contrato deployado com sucesso!")
    print(f"\n📋 Resumo:")
    print(f"   Contract Address: {deploy_result.get('contract_address')}")
    print(f"   Transaction Hash: {deploy_result.get('transaction_hash')}")
    print(f"   Gas usado: {deploy_result.get('gas_used'):,}")
    print(f"   ABI salva em: compilation_result.json")
    
    # Salvar dados para uso posterior
    output_data = {
        "contract_address": deploy_result.get('contract_address'),
        "transaction_hash": deploy_result.get('transaction_hash'),
        "gas_used": deploy_result.get('gas_used'),
        "abi": compilation_result.get('abi'),
        "bytecode": compilation_result.get('bytecode')
    }
    
    with open('deployment_result.json', 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"   Dados salvos em: deployment_result.json")
    print("\n" + "="*70)


if __name__ == "__main__":
    main()
