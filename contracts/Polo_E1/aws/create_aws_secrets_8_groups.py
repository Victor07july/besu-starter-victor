"""
Script para criar 8 Secrets no AWS Secrets Manager
Lê o arquivo wallets_8_groups.json e cria/atualiza os secrets
"""

import json
import boto3
from pathlib import Path
from botocore.exceptions import ClientError

# Cliente AWS Secrets Manager
secrets_client = boto3.client('secretsmanager', region_name='us-east-1')

# Arquivo de entrada
WALLETS_FILE = Path(__file__).parent / "wallets_8_groups.json"


def load_wallets():
    """Carrega carteiras do arquivo JSON"""
    print(f"📂 Carregando carteiras de {WALLETS_FILE}...")
    
    if not WALLETS_FILE.exists():
        print(f"❌ Erro: Arquivo não encontrado: {WALLETS_FILE}")
        print("   Execute 'create_8_wallets.py' primeiro!")
        return None
    
    with open(WALLETS_FILE, 'r') as f:
        wallets = json.load(f)
    
    print(f"  ✅ {len(wallets)} carteiras carregadas")
    return wallets


def create_or_update_secret(secret_name, wallet_data):
    """Cria ou atualiza um secret no AWS Secrets Manager"""
    
    # Preparar dados do secret (chaves em UPPERCASE conforme Lambda espera)
    secret_value = {
        "SENDER_ADDRESS": wallet_data["address"],
        "PRIVATE_KEY": wallet_data["private_key"]
    }
    
    try:
        # Tentar criar novo secret
        response = secrets_client.create_secret(
            Name=secret_name,
            Description=f"Blockchain keys for {secret_name}",
            SecretString=json.dumps(secret_value)
        )
        print(f"  ✅ Criado: {secret_name}")
        return response
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceExistsException':
            # Secret já existe, atualizar
            response = secrets_client.update_secret(
                SecretId=secret_name,
                SecretString=json.dumps(secret_value)
            )
            print(f"  🔄 Atualizado: {secret_name}")
            return response
        else:
            print(f"  ❌ Erro ao criar {secret_name}: {e}")
            return None


def main():
    print("=" * 60)
    print("☁️  CRIAÇÃO DE SECRETS NO AWS SECRETS MANAGER")
    print("=" * 60)
    
    # Carregar carteiras
    wallets = load_wallets()
    if not wallets:
        return
    
    print(f"\n🔐 Criando/atualizando secrets na AWS (região: us-east-1)...")
    
    success_count = 0
    failed_count = 0
    
    # Criar secret para cada carteira
    for group_name, wallet_data in wallets.items():
        # Nome do secret: besu-blockchain-keys-group1, group2, etc.
        group_number = group_name.split('_')[-1]  # Extrai o número
        secret_name = f"besu-blockchain-keys-group{group_number}"
        
        print(f"\n📝 {secret_name} ({wallet_data['address']})...")
        
        result = create_or_update_secret(secret_name, wallet_data)
        
        if result:
            success_count += 1
        else:
            failed_count += 1
    
    # Resumo
    print("\n" + "=" * 60)
    print("📊 RESUMO")
    print("=" * 60)
    print(f"  ✅ Sucesso: {success_count}")
    print(f"  ❌ Falhas: {failed_count}")
    
    if success_count == len(wallets):
        print("\n✅ TODOS OS SECRETS CRIADOS COM SUCESSO!")
        print("\n📋 Próximos passos:")
        print("  1. Atualizar Lambda 'blockchain' para reconhecer os 8 grupos")
        print("  2. Configurar Lambda reserved concurrency = 8")
        print("  3. Executar send_to_sqs_alternado.py")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
