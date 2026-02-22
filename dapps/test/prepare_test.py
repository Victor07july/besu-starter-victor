#!/usr/bin/env python3
"""
Script auxiliar para copiar wallets e CSV para teste do SimpleCounter
"""

import shutil
from pathlib import Path

# Caminhos
MULTITHREAD_DIR = Path(__file__).parent / "multithread"
DAPPS_DIR = Path(__file__).parent

SOURCE_WALLETS = MULTITHREAD_DIR / "send" / "wallets_64_groups.json"
SOURCE_CSV = MULTITHREAD_DIR / "send" / "dados_gas.csv"

DEST_WALLETS = DAPPS_DIR / "wallets_64_groups.json"
DEST_CSV = DAPPS_DIR / "dados_gas.csv"

def main():
    print("📋 Preparando arquivos para teste do SimpleCounter...")
    
    # Copiar wallets
    if SOURCE_WALLETS.exists():
        shutil.copy(SOURCE_WALLETS, DEST_WALLETS)
        print(f"✅ Copiado: {SOURCE_WALLETS.name}")
    else:
        print(f"⚠️  Wallets não encontrado: {SOURCE_WALLETS}")
    
    # Copiar CSV
    if SOURCE_CSV.exists():
        shutil.copy(SOURCE_CSV, DEST_CSV)
        print(f"✅ Copiado: {SOURCE_CSV.name}")
    else:
        print(f"⚠️  CSV não encontrado: {SOURCE_CSV}")
    
    print("\n✨ Arquivos preparados!")
    print("\n📋 Próximos passos:")
    print("   1. Execute: python3 deploy_simple_counter.py")
    print("   2. Compile o Go: cd test_simple && go build")
    print("   3. Execute o teste: ./test_simple")

if __name__ == "__main__":
    main()
