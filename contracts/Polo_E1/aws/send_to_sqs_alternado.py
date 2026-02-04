"""
Script para enviar dados alternando entre os 64 CSVs
Envia 1 linha de cada CSV em PARALELO (64 simultâneas)
Cada linha é repetida 10 vezes antes de passar para próxima
"""

import pandas as pd
import requests
import json
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

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

REQUEST_TIMEOUT = 60  # Aumentar para 60s
MAX_RETRIES = 3  # Tentar até 3 vezes se der timeout

# Lock para sincronizar prints
print_lock = Lock()


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
    """Envia 1 registro para o API Gateway com retry automático"""
    payload = {
        "records": [record],  # Apenas 1 registro
        "message_group": message_group
    }
    
    last_error = None
    
    # Tentar até MAX_RETRIES vezes
    for attempt in range(MAX_RETRIES):
        try:
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
            
        except requests.exceptions.Timeout as e:
            last_error = f"Timeout (tentativa {attempt+1}/{MAX_RETRIES})"
            if attempt < MAX_RETRIES - 1:
                time.sleep(2)  # Aguardar 2s antes de retry
                continue
            
        except Exception as e:
            last_error = str(e)
            break  # Outros erros não fazem retry
    
    # Se chegou aqui, todas as tentativas falharam
    with print_lock:
        print(f"❌ {description}: {last_error}")
    return False


def process_line_worker(df_info, line_index, repetition):
    """
    Worker que processa uma linha de um CSV específico
    Envia 1 repetição da linha
    """
    df = df_info['df']
    config = df_info['config']
    
    # Verificar se linha existe
    if line_index >= len(df):
        return None
    
    row = df.iloc[line_index]
    record = prepare_record(row)
    
    description = config['description']
    message_group = config['message_group']
    
    success = send_record_to_api(record, message_group, description)
    
    return {
        'df_info': df_info,
        'config': config,
        'success': success,
        'description': description,
        'line_index': line_index,
        'repetition': repetition
    }


def main():
    """Processa os 64 CSVs em PARALELO"""
    print("\n🚀 Enviando dados em PARALELO (64 workers simultâneos)")
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
    print(f"⚡ Iniciando processamento PARALELO com {len(CSV_FILES)} threads")
    print(f"{'='*60}\n")
    
    # Processar alternando entre os CSVs
    max_rows = max(len(d['df']) for d in dfs)
    start_time = time.time()
    total_requests = 0
    
    # Usar ThreadPoolExecutor para paralelização
    with ThreadPoolExecutor(max_workers=len(CSV_FILES)) as executor:
        
        for line_index in range(max_rows):
            line_start = time.time()
            
            # Para cada repetição (10x)
            for repetition in range(10):
                futures = []
                
                # Enviar 1 requisição de cada CSV em PARALELO
                for df_info in dfs:
                    if line_index < len(df_info['df']):
                        future = executor.submit(
                            process_line_worker,
                            df_info,
                            line_index,
                            repetition
                        )
                        futures.append(future)
                
                # Aguardar todas as 64 requisições completarem
                rep_start = time.time()
                completed = 0
                success_count = 0
                failed_vehicles = []
                
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        vehicle_num = result['config']['message_group'].split('_')[-1]  # Extrair número do grupo
                        if result['success']:
                            result['df_info']['sent'] += 1
                            success_count += 1
                        else:
                            result['df_info']['failed'] += 1
                            failed_vehicles.append(vehicle_num)
                        completed += 1
                        total_requests += 1
                
                # Log de TODAS as repetições
                rep_time = time.time() - rep_start
                with print_lock:
                    if failed_vehicles:
                        # Ordenar veículos que falharam
                        failed_vehicles.sort(key=int)
                        if len(failed_vehicles) <= 10:
                            # Mostrar todos
                            failed_str = f"V{','.join(failed_vehicles)}"
                        else:
                            # Mostrar primeiros 10 + contador
                            failed_str = f"V{','.join(failed_vehicles[:10])} (e mais {len(failed_vehicles)-10})"
                        print(f"⚡ Linha {line_index+1}/{max_rows} - Rep {repetition+1}/10: ✅ {success_count} OK | ❌ {len(failed_vehicles)} FALHAS [{failed_str}] - {rep_time:.1f}s")
                    else:
                        print(f"⚡ Linha {line_index+1}/{max_rows} - Rep {repetition+1}/10: ✅ {completed} carteiras OK - {rep_time:.1f}s")
            
            # Progresso a cada 10 linhas
            if (line_index + 1) % 10 == 0:
                elapsed = time.time() - start_time
                rate = total_requests / elapsed if elapsed > 0 else 0
                with print_lock:
                    print(f"\n📊 Progresso: {line_index+1}/{max_rows} linhas | {total_requests:,} requisições | {rate:.1f} req/s | {elapsed:.1f}s\n")
    
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
