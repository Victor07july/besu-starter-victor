"""
Script para replicar os 16 CSVs existentes e criar 48 novos (total: 64 CSVs)
Estratégia: Cópia cíclica dos 16 CSVs originais
- vehicle_data_1.csv  → vehicle_data_17.csv, vehicle_data_33.csv, vehicle_data_49.csv
- vehicle_data_2.csv  → vehicle_data_18.csv, vehicle_data_34.csv, vehicle_data_50.csv
- ...
- vehicle_data_16.csv → vehicle_data_32.csv, vehicle_data_48.csv, vehicle_data_64.csv
"""

import shutil
from pathlib import Path

def replicate_csvs_to_64():
    """Replica os 16 CSVs para chegar a 64 no total"""
    
    print("=" * 70)
    print("📋 REPLICAÇÃO DE CSVs: 16 → 64")
    print("=" * 70)
    
    # Diretório base
    data_dir = Path(__file__).parent
    
    # Verificar se os 16 CSVs originais existem
    print("\n🔍 Verificando CSVs originais (1-16)...")
    missing = []
    for i in range(1, 17):
        csv_file = data_dir / f"vehicle_data_{i}.csv"
        if not csv_file.exists():
            missing.append(i)
            print(f"  ❌ vehicle_data_{i}.csv - NÃO ENCONTRADO")
        else:
            print(f"  ✅ vehicle_data_{i}.csv - OK")
    
    if missing:
        print(f"\n❌ Erro: {len(missing)} arquivo(s) faltando: {missing}")
        print("   Execute este script apenas com os 16 CSVs originais presentes.")
        return
    
    # Replicar para criar 17-64 (48 novos arquivos)
    print("\n📄 Criando 48 novos CSVs (17-64)...")
    
    created_count = 0
    skipped_count = 0
    
    # Para cada novo CSV (17-64)
    for target_num in range(17, 65):
        # Determinar qual CSV original usar (ciclo 1-16)
        # 17 → 1, 18 → 2, ..., 32 → 16, 33 → 1, ...
        source_num = ((target_num - 1) % 16) + 1
        
        source_file = data_dir / f"vehicle_data_{source_num}.csv"
        target_file = data_dir / f"vehicle_data_{target_num}.csv"
        
        # Verificar se o arquivo destino já existe
        if target_file.exists():
            print(f"  ⏭️  vehicle_data_{target_num}.csv já existe (pulando)")
            skipped_count += 1
        else:
            # Copiar arquivo
            shutil.copy2(source_file, target_file)
            print(f"  ✅ vehicle_data_{target_num}.csv (copiado de vehicle_data_{source_num}.csv)")
            created_count += 1
    
    # Resumo
    print("\n" + "=" * 70)
    print("📊 RESUMO")
    print("=" * 70)
    print(f"  ✅ Arquivos criados: {created_count}")
    print(f"  ⏭️  Arquivos pulados: {skipped_count}")
    print(f"  📁 Total de CSVs: {16 + created_count} arquivos")
    print("\n" + "=" * 70)
    print("✅ REPLICAÇÃO CONCLUÍDA!")
    print("=" * 70)
    
    # Verificação final
    print("\n🔍 Verificação final (1-64):")
    total_files = 0
    for i in range(1, 65):
        csv_file = data_dir / f"vehicle_data_{i}.csv"
        if csv_file.exists():
            total_files += 1
    
    if total_files == 64:
        print(f"  ✅ Todos os 64 CSVs presentes!")
    else:
        print(f"  ⚠️  Apenas {total_files}/64 CSVs encontrados")
    
    print("\n📋 Próximos passos:")
    print("  1. Executar add_48_more_wallets.py (criar 48 novas carteiras)")
    print("  2. Executar create_aws_secrets_64_groups.py (criar 48 novos secrets)")
    print("  3. Atualizar Lambda com 64 grupos e concurrency = 64")
    print("  4. Executar send_to_sqs_alternado.py (atualizado para 64 CSVs)")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    replicate_csvs_to_64()
