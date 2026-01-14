"""
Script para registrar um novo usuário na API

USO:
    # Modo interativo (pergunta email/password)
    python register_user.py

    # Modo com argumentos
    python register_user.py --email user@example.com --password senha456

Configuração:
    - Ajuste API_BASE_URL se necessário
    
IMPORTANTE:
    - O username deve ser um EMAIL válido (ex: victor@gmail.com)
"""

import requests
import argparse
import sys

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


def register_user(email, password):
    """
    Registra um novo usuário na API
    
    Args:
        email: Email do usuário (formato: user@domain.com)
        password: Senha do usuário
    
    Returns:
        bool: True se sucesso, False se falhar
    """
    print_section("REGISTRAR NOVO USUÁRIO")
    
    # Validar formato de email básico
    if '@' not in email or '.' not in email.split('@')[1]:
        print(f"❌ Email inválido: {email}")
        print(f"💡 Use formato: usuario@dominio.com")
        return False
    
    url = f"{API_BASE_URL}/auth/signup/"
    
    # Dados do registro (form-data)
    data = {
        "username": email,  # API espera 'username' mas deve ser email
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
        
        print(f"\n✅ Usuário registrado com sucesso!")
        print(f"\n📋 Dados do usuário:")
        print(f"   Username: {result.get('username')}")
        print(f"   ID: {result.get('id')}")
        print(f"   Is Admin: {result.get('is_admin', False)}")
        print(f"   Created at: {result.get('created_at')}")
        
        # Mostrar e salvar token se disponível (API pode retornar 'token' ou 'access_token')
        token = result.get('access_token') or result.get('token')
        
        if token:
            print(f"\n🔑 JWT Token:")
            print(f"   {token}")
            
            # Salvar token em arquivo
            token_file = "jwt_token.txt"
            with open(token_file, 'w') as f:
                f.write(token)
            
            print(f"\n💾 Token salvo em: {token_file}")
            
            # Salvar dados completos em JSON
            json_file = "register_data.json"
            with open(json_file, 'w') as f:
                import json as json_module
                json_module.dump(result, f, indent=2)
            
            print(f"   Dados completos em: {json_file}")
        
        return True
            
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
        
        if e.response.status_code == 400:
            print(f"\n💡 Possíveis causas:")
            print(f"   - Usuário já existe no banco de dados")
            print(f"   - Username ou password inválidos (muito curtos, caracteres inválidos)")
        elif e.response.status_code == 422:
            print(f"\n💡 Erro de validação dos dados enviados")
        
        return False
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Erro de conexão: {e}")
        print(f"💡 Verifique se a API está rodando em {API_BASE_URL}")
        return False


# ===========================
# FLUXO PRINCIPAL
# ===========================

def main():
    print("\n" + "🎯 "+"="*66 + " 🎯")
    print("            REGISTRAR NOVO USUÁRIO NA API")
    print("🎯 "+"="*66 + " 🎯")
    
    # Desabilitar avisos de SSL se não verificar certificado
    if not VERIFY_SSL:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        print("\n⚠️  Verificação SSL desabilitada (certificado self-signed)")
    
    # Parse argumentos
    parser = argparse.ArgumentParser(description='Registrar novo usuário na API')
    parser.add_argument('--email', '-e', help='Email do novo usuário (ex: user@example.com)')
    parser.add_argument('--password', '-p', help='Password do novo usuário')
    args = parser.parse_args()
    
    # Obter credenciais (argumentos ou input interativo)
    if args.email and args.password:
        email = args.email
        password = args.password
    else:
        print("\n📝 Modo interativo - Digite as credenciais:")
        print("⚠️  IMPORTANTE: O username deve ser um EMAIL válido")
        email = input("   Email (ex: victor@gmail.com): ").strip()
        
        if not email:
            print("❌ Email não pode ser vazio")
            sys.exit(1)
        
        password = input("   Password: ").strip()
        
        if not password:
            print("❌ Password não pode ser vazio")
            sys.exit(1)
    
    # Registrar usuário
    success = register_user(email, password)
    
    if success:
        print_section("✨ SUCESSO")
        print(f"🎉 Usuário '{email}' criado com sucesso!")
        print(f"\n💡 Próximos passos:")
        print(f"   1. O token JWT já foi gerado e salvo em jwt_token.txt")
        print(f"   2. Use o token para acessar endpoints protegidos")
        print(f"   3. Ou faça login depois com: python login_user.py -e {email}")
        print("\n" + "="*70)
    else:
        print_section("❌ FALHA")
        print(f"Não foi possível criar o usuário '{email}'")
        print(f"\n💡 Dicas:")
        print(f"   - Tente outro email: python register_user.py -e user@example.com -p senha123")
        print(f"   - Verifique se a API está rodando em {API_BASE_URL}")
        print(f"   - Use modo interativo: python register_user.py")
        print("\n" + "="*70)


if __name__ == "__main__":
    main()
