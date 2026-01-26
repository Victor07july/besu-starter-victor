"""
Script para fazer login e obter JWT token da API

USO:
    # Modo interativo (pergunta email/password)
    python login_user.py

    # Modo com argumentos
    python login_user.py --email user@example.com --password senha456

Configuração:
    - Ajuste API_BASE_URL se necessário
"""

import requests
import argparse
import sys
import json

# ===========================
# CONFIGURAÇÃO
# ===========================

# API Configuration
API_BASE_URL = "https://localhost/api/v1"  # Ou http://localhost:8000/api/v1 se local
VERIFY_SSL = False  # False para localhost com certificado self-signed

# ===========================
# FUNÇÕES
# ===========================

def print_section(title):
    """Imprime separador visual"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def login(email, password):
    """
    Faz login na API e retorna o JWT token
    
    Args:
        email: Email do usuário
        password: Senha do usuário
    
    Returns:
        dict: Dados do login (access_token, token_type, etc.) ou None
    """
    print_section("LOGIN")
    
    url = f"{API_BASE_URL}/auth/signin/"
    
    # Dados do login (form-data)
    data = {
        "username": email,  # API espera 'username' mas é o email
        "password": password
    }
    
    print(f"📧 Email: {email}")
    print(f"🔒 Password: {'*' * len(password)}")
    
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
            print(f"\n✅ Login bem-sucedido!")
            print(f"\n🔑 JWT Token:")
            print(f"   {token}")
            print(f"\n📋 Informações do token:")
            print(f"   Token Type: {result.get('token_type', 'bearer')}")
            if result.get('id'):
                print(f"   User ID: {result.get('id')}")
            
            # Salvar token em arquivo
            token_file = "jwt_token.txt"
            with open(token_file, 'w') as f:
                f.write(token)
            
            print(f"\n💾 Token salvo em: {token_file}")
            
            # Salvar dados completos em JSON
            json_file = "login_data.json"
            with open(json_file, 'w') as f:
                json.dump(result, f, indent=2)
            
            print(f"   Dados completos em: {json_file}")
            
            return result
        else:
            print(f"\n❌ Token não encontrado na resposta")
            print(f"   Resposta: {result}")
            return None
            
    except requests.exceptions.HTTPError as e:
        print(f"\n❌ Erro HTTP {e.response.status_code}")
        
        # Tentar parsear JSON da resposta
        try:
            error_detail = e.response.json()
            print(f"📋 Detalhes do erro:")
            print(f"   {error_detail}")
        except:
            print(f"📋 Resposta do servidor:")
            print(f"   {e.response.text}")
        
        if e.response.status_code == 401:
            print(f"\n💡 Email ou senha incorretos")
        elif e.response.status_code == 422:
            print(f"\n💡 Erro de validação dos dados enviados")
        
        return None
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Erro de conexão: {e}")
        print(f"💡 Verifique se a API está rodando em {API_BASE_URL}")
        return None


# ===========================
# FLUXO PRINCIPAL
# ===========================

def main():
    print("\n" + "🎯 "+"="*66 + " 🎯")
    print("            LOGIN NA API - OBTER JWT TOKEN")
    print("🎯 "+"="*66 + " 🎯")
    
    # Desabilitar avisos de SSL se não verificar certificado
    if not VERIFY_SSL:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        print("\n⚠️  Verificação SSL desabilitada (certificado self-signed)")
    
    # Parse argumentos
    parser = argparse.ArgumentParser(description='Fazer login na API e obter JWT token')
    parser.add_argument('--email', '-e', help='Email do usuário')
    parser.add_argument('--password', '-p', help='Password do usuário')
    args = parser.parse_args()
    
    # Obter credenciais (argumentos ou input interativo)
    if args.email and args.password:
        email = args.email
        password = args.password
    else:
        print("\n📝 Modo interativo - Digite suas credenciais:")
        email = input("   Email: ").strip()
        
        if not email:
            print("❌ Email não pode ser vazio")
            sys.exit(1)
        
        password = input("   Password: ").strip()
        
        if not password:
            print("❌ Password não pode ser vazio")
            sys.exit(1)
    
    # Fazer login
    result = login(email, password)
    
    if result and (result.get("access_token") or result.get("token")):
        print_section("✨ SUCESSO")
        print(f"🎉 Login realizado com sucesso!")
        print(f"\n💡 Como usar o token:")
        print(f"   1. Copie o token de jwt_token.txt")
        print(f"   2. Adicione no header: Authorization: Bearer <token>")
        print(f"   3. Ou use em scripts Python:")
        print(f"      headers = {{'Authorization': f'Bearer {{token}}'}}")
        print(f"\n📄 Exemplo de uso:")
        print(f"   curl -H 'Authorization: Bearer $(cat jwt_token.txt)' \\")
        print(f"        https://localhost/api/v1/besu/...")
        print("\n" + "="*70)
    else:
        print_section("❌ FALHA")
        print(f"Não foi possível fazer login com '{email}'")
        print(f"\n💡 Verifique:")
        print(f"   - Email e senha estão corretos")
        print(f"   - Usuário está registrado (use register_user.py)")
        print(f"   - API está rodando em {API_BASE_URL}")
        print("\n" + "="*70)
        sys.exit(1)


if __name__ == "__main__":
    main()
