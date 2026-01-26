"""
Script para tornar um usuário ADMIN no banco de dados PostgreSQL

USO:
    # Modo interativo (pergunta o email)
    python make_admin.py

    # Modo com argumentos
    python make_admin.py --email victor@gmail.com

Requisitos:
    pip install psycopg2-binary

Configuração:
    - Por padrão conecta em localhost:5432
    - Usuário: postgres / Senha: postgres / Database: dev
"""

import psycopg2
import argparse
import sys

# ===========================
# CONFIGURAÇÃO
# ===========================

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "postgres",
    "password": "postgres",
    "database": "dev"
}

# ===========================
# FUNÇÕES
# ===========================

def print_section(title):
    """Imprime separador visual"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def connect_db():
    """Conecta ao banco de dados PostgreSQL"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except psycopg2.Error as e:
        print(f"❌ Erro ao conectar ao banco de dados: {e}")
        print(f"\n💡 Verifique:")
        print(f"   - PostgreSQL está rodando em {DB_CONFIG['host']}:{DB_CONFIG['port']}")
        print(f"   - Container auth-db está ativo: docker ps | grep auth-db")
        print(f"   - Credenciais estão corretas")
        return None


def list_users(conn):
    """Lista todos os usuários do banco"""
    try:
        cur = conn.cursor()
        cur.execute('SELECT id, email, is_admin FROM "user" ORDER BY id;')
        users = cur.fetchall()
        cur.close()
        
        if users:
            print("\n📋 Usuários cadastrados:")
            print(f"{'ID':<5} {'EMAIL':<40} {'ADMIN':<10}")
            print("-" * 70)
            for user in users:
                user_id, email, is_admin = user
                admin_status = "✅ Sim" if is_admin else "❌ Não"
                print(f"{user_id:<5} {email:<40} {admin_status:<10}")
        else:
            print("\n⚠️  Nenhum usuário encontrado no banco")
        
        return users
        
    except psycopg2.Error as e:
        print(f"❌ Erro ao listar usuários: {e}")
        return []


def make_admin(conn, email):
    """Torna um usuário admin pelo email"""
    try:
        cur = conn.cursor()
        
        # Verificar se usuário existe
        cur.execute('SELECT id, email, is_admin FROM "user" WHERE email = %s;', (email,))
        user = cur.fetchone()
        
        if not user:
            print(f"\n❌ Usuário com email '{email}' não encontrado")
            cur.close()
            return False
        
        user_id, user_email, is_admin = user
        
        if is_admin:
            print(f"\n⚠️  Usuário '{email}' já é admin")
            cur.close()
            return True
        
        # Tornar admin
        cur.execute('UPDATE "user" SET is_admin = true WHERE email = %s;', (email,))
        conn.commit()
        
        print(f"\n✅ Usuário '{email}' agora é ADMIN!")
        print(f"   ID: {user_id}")
        
        cur.close()
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Erro ao atualizar usuário: {e}")
        conn.rollback()
        return False


def verify_admin(conn, email):
    """Verifica se usuário é admin"""
    try:
        cur = conn.cursor()
        cur.execute('SELECT id, email, is_admin FROM "user" WHERE email = %s;', (email,))
        user = cur.fetchone()
        cur.close()
        
        if user:
            user_id, user_email, is_admin = user
            print(f"\n📋 Status atual:")
            print(f"   ID: {user_id}")
            print(f"   Email: {user_email}")
            print(f"   Is Admin: {'✅ Sim' if is_admin else '❌ Não'}")
            return is_admin
        
        return False
        
    except psycopg2.Error as e:
        print(f"❌ Erro ao verificar usuário: {e}")
        return False


# ===========================
# FLUXO PRINCIPAL
# ===========================

def main():
    print("\n" + "🎯 "+"="*66 + " 🎯")
    print("         TORNAR USUÁRIO ADMIN NO BANCO DE DADOS")
    print("🎯 "+"="*66 + " 🎯")
    
    # Parse argumentos
    parser = argparse.ArgumentParser(description='Tornar usuário admin no PostgreSQL')
    parser.add_argument('--email', '-e', help='Email do usuário')
    parser.add_argument('--list', '-l', action='store_true', help='Apenas listar usuários')
    args = parser.parse_args()
    
    # Conectar ao banco
    print_section("CONECTANDO AO BANCO DE DADOS")
    print(f"🔌 Conectando em {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}...")
    
    conn = connect_db()
    if not conn:
        sys.exit(1)
    
    print(f"✅ Conectado com sucesso!")
    
    # Listar usuários
    print_section("USUÁRIOS CADASTRADOS")
    users = list_users(conn)
    
    if not users:
        print("\n💡 Registre um usuário primeiro com register_user.py")
        conn.close()
        sys.exit(0)
    
    # Se for apenas para listar, sair
    if args.list:
        conn.close()
        sys.exit(0)
    
    # Obter email (argumento ou input)
    print_section("TORNAR ADMIN")
    
    if args.email:
        email = args.email
    else:
        email = input("\n📧 Digite o email do usuário para tornar admin: ").strip()
        
        if not email:
            print("❌ Email não pode ser vazio")
            conn.close()
            sys.exit(1)
    
    print(f"\n🔄 Processando usuário: {email}")
    
    # Tornar admin
    success = make_admin(conn, email)
    
    if success:
        # Verificar
        verify_admin(conn, email)
        
        print_section("✨ SUCESSO")
        print(f"🎉 Usuário '{email}' agora tem permissões de ADMIN!")
        print(f"\n💡 Agora você pode:")
        print(f"   1. Fazer login com este usuário")
        print(f"   2. Obter JWT token com login_user.py")
        print(f"   3. Fazer deploy de contratos via API")
        print("\n" + "="*70)
    else:
        print_section("❌ FALHA")
        print(f"Não foi possível tornar '{email}' admin")
        print(f"\n💡 Verifique o email e tente novamente")
        print("\n" + "="*70)
    
    conn.close()


if __name__ == "__main__":
    main()
