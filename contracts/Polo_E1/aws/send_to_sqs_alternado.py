"""
Script para enviar dados alternando entre os 64 CSVs
Envia 1 linha do CSV1, depois 1 do CSV2, ..., até CSV64, e repete
"""

import pandas as pd
import requests
import json
import time
from pathlib import Path

# Configuração API Gateway
API_GATEWAY_URL = "https://r3zt1dfiej.execute-api.us-east-1.amazonaws.com/default"

# Gerar lista de 64 CSVs dinamicamente
CSV_FILES = []
for i in range(1, 65):
    CSV_FILES.append({
        "file": f"../data/vehicle_data_{i}.csv",
        "message_group": f"vehicle_group_{i}",
        "description": f"Veículo {i}"
    })

REQUEST_TIMEOUT = 30


def prepare_record(row):
    """Prepara um registro do CSV"""
    return {
        "distance_highway": int(row['distance_highway']),
        "distance_city": int(row['distance_city']),
        "city_gasoline": float(row.get('city_gasoline', 13.5)),
        "road_gasoline": float(row.get('road_gasoline', 15.7)),
        "city_ethanol": float(row.get('city_ethanol', 9.3)),
        "road_ethanol": float(row.get('road_ethanol', 10.9)),
        "city_gnv": float(row.get('city_gnv', 15.1)),
        "road_gnv": float(row.get('road_gnv', 16.8)),
        "co2_per_liter": float(row.get('co2_per_liter', 2.31)),
        "co2_per_liter_ethanol": float(row.get('co2_per_liter_ethanol', 2.15)),
        "co2_per_m3_gnv": float(row.get('co2_per_m3_gnv', 2.74))
    }


def send_record_to_api(record, message_group, description):
    """Envia 1 registro para o API Gateway"""
    try:
        payload = {
            "records": [record],  # Apenas 1 registro
            "message_group": message_group
        }
        
        response = requests.post(
            API_GATEWAY_URL,
            json=payload,
            timeout=REQUEST_TIMEOUT
        )
        
        response.raise_for_status()
        result = response.json()
        
        # Lambda retorna body como string JSON
        if 'body' in result:
            body = json.loads(result['body'])
            sent_count = body.get('sent', 0)
        else:
            sent_count = result.get('sent', 0)
        
        return sent_count > 0
        
    except Exception as e:
        print(f"❌ {description}: Erro - {str(e)}")
        return False


def main():
    """Processa os 64 CSVs alternando linha por linha"""
    print("\n🚀 Enviando dados alternados (1 linha de cada CSV por vez)")
    print(f"📍 API Gateway: {API_GATEWAY_URL}")
    print(f"🔢 Total de grupos: {len(CSV_FILES)}\n")
    
    # Carregar os 64 CSVs
    base_path = Path(__file__).parent
    dfs = []
    
    for csv_config in CSV_FILES:
        csv_path = base_path / csv_config["file"]
        if not csv_path.exists():
            print(f"❌ Arquivo não encontrado: {csv_path}")
            return
        
        df = pd.read_csv(csv_path)
        dfs.append({
            'df': df,
            'config': csv_config,
            'sent': 0,
            'failed': 0
        })
        # Mostrar apenas primeiros 5 e últimos 5
        if len(dfs) <= 5 or len(dfs) > len(CSV_FILES) - 5:
            print(f"📄 {csv_config['description']}: {len(df)} registros")
        elif len(dfs) == 6:
            print(f"   ... ({len(CSV_FILES) - 10} CSVs adicionais)")
    
    print(f"\n{'='*60}")
    
    # Processar alternando entre os CSVs
    max_rows = max(len(d['df']) for d in dfs)
    start_time = time.time()
    
    for i in range(max_rows):
        # Processar 1 linha de cada CSV
        for df_info in dfs:
            df = df_info['df']
            config = df_info['config']
            
            # Pular se este CSV já acabou
            if i >= len(df):
                continue
            
            row = df.iloc[i]
            record = prepare_record(row)
            
            description = config['description']
            message_group = config['message_group']
            
            # REPETIR 10 VEZES a mesma linha
            for repetition in range(10):
                success = send_record_to_api(record, message_group, description)
                
                if success:
                    df_info['sent'] += 1
                    if repetition == 0 or repetition == 9:  # Mostrar apenas primeira e última repetição
                        print(f"✅ {description}: registro {i+1}/{len(df)} (rep {repetition+1}/10)")
                else:
                    df_info['failed'] += 1
                    print(f"❌ {description}: falha no registro {i+1}/{len(df)} (rep {repetition+1}/10)")
                
                # Pequena pausa entre envios
                time.sleep(0.1)
        
        # Mostrar progresso a cada 10 linhas
        if (i + 1) % 10 == 0:
            elapsed = time.time() - start_time
            print(f"\n📊 Progresso: {i+1}/{max_rows} linhas processadas ({elapsed:.1f}s)\n")
    
    # Resumo final
    elapsed_time = time.time() - start_time
    total_sent = sum(d['sent'] for d in dfs)
    total_failed = sum(d['failed'] for d in dfs)
    
    print(f"\n{'='*60}")
    print(f"🎉 Processamento concluído!")
    print(f"{'='*60}")
    
    # Mostrar resumo apenas dos primeiros 3 e últimos 3
    for idx, df_info in enumerate(dfs):
        config = df_info['config']
        if idx < 3 or idx >= len(dfs) - 3:
            print(f"{config['description']}:")
            print(f"  ✅ Enviados: {df_info['sent']}")
            print(f"  ❌ Falhas: {df_info['failed']}")
        elif idx == 3:
            print(f"   ... ({len(dfs) - 6} grupos adicionais)")
    
    print(f"\nTotal:")
    print(f"  ✅ Enviados: {total_sent}")
    print(f"  ❌ Falhas: {total_failed}")
    print(f"  ⏱️  Tempo: {elapsed_time:.2f} segundos")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
