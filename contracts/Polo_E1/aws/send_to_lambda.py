"""
Script para enviar dados do CSV para o Lambda via API Gateway
"""

import pandas as pd
import requests
import json
import time

# URL do API Gateway
API_GATEWAY_URL = "https://9ckkg86575.execute-api.us-east-1.amazonaws.com/default/blockchain"

# Arquivo CSV
CSV_FILE = "vehicle_data_1.csv"

# Tamanho do lote (reduzido para evitar timeout do API Gateway)
BATCH_SIZE = 1


def prepare_record(row):
    """Prepara um registro do CSV para enviar ao Lambda"""
    return {
        "distance_highway": int(row['distance_highway']),
        "distance_city": int(row['distance_city']),
        # Valores padrão do Polo (podem ser sobrescritos se existirem no CSV)
        "city_gasoline": float(row.get('city_gasoline', 13.5)),
        "road_gasoline": float(row.get('road_gasoline', 15.7)),
        "city_ethanol": float(row.get('city_ethanol', 9.3)),
        "road_ethanol": float(row.get('road_ethanol', 10.9)),
        "carbon_price_european": float(row.get('carbon_price_european', 89.08)),
        "euro_price": float(row.get('euro_price', 6.1708))
    }


def send_to_lambda(batch):
    """Envia um lote de registros para o Lambda"""
    try:
        print(f"  Enviando lote com {len(batch)} registros...")
        
        response = requests.post(
            API_GATEWAY_URL,
            json=batch,
            headers={'Content-Type': 'application/json'},
            timeout=300  # 5 minutos
        )
        
        response.raise_for_status()
        
        # Parse response
        if isinstance(response.json(), str):
            result = json.loads(response.json())
        else:
            result = response.json()
        
        return result
        
    except requests.exceptions.Timeout:
        print("  ❌ Timeout ao aguardar resposta do Lambda")
        return {"error": "timeout"}
    except requests.exceptions.RequestException as e:
        print(f"  ❌ Erro na requisição: {str(e)}")
        return {"error": str(e)}
    except json.JSONDecodeError as e:
        print(f"  ❌ Erro ao parsear resposta: {str(e)}")
        return {"error": f"JSON parse error: {str(e)}"}


def main():
    print("=" * 70)
    print("📤 ENVIO DE DADOS PARA LAMBDA")
    print("=" * 70)
    
    # Ler CSV
    print(f"\n📂 Lendo arquivo: {CSV_FILE}...")
    try:
        df = pd.read_csv(CSV_FILE)
    except FileNotFoundError:
        print(f"❌ Arquivo não encontrado: {CSV_FILE}")
        print("\nCertifique-se de estar no diretório correto:")
        print("  cd /home/victor/besu-starter-victor/contracts/Polo_E1")
        return
    
    total_records = len(df)
    print(f"✅ {total_records} registros encontrados")
    
    # Preparar dados
    records = [prepare_record(row) for _, row in df.iterrows()]
    
    # Dividir em lotes
    batches = [records[i:i + BATCH_SIZE] for i in range(0, len(records), BATCH_SIZE)]
    total_batches = len(batches)
    
    print(f"\n📦 Dividindo em {total_batches} lotes de até {BATCH_SIZE} registros cada")
    print(f"🔗 API Gateway: {API_GATEWAY_URL}")
    
    # Confirmar antes de enviar
    print("\n" + "=" * 70)
    response = input("Deseja prosseguir com o envio? (s/n): ")
    
    if response.lower() != 's':
        print("\n⏭️ Operação cancelada.")
        return
    
    # Processar lotes
    print("\n" + "=" * 70)
    print("🚀 PROCESSANDO LOTES")
    print("=" * 70)
    
    all_results = []
    successful_batches = 0
    failed_batches = 0
    total_e1 = 0
    total_gas = 0
    
    for idx, batch in enumerate(batches, 1):
        print(f"\n[Lote {idx}/{total_batches}]")
        
        result = send_to_lambda(batch)
        
        if 'error' in result:
            print(f"  ❌ Erro no lote")
            failed_batches += 1
        else:
            # Parse do body se vier como string
            if 'body' in result:
                body = json.loads(result['body']) if isinstance(result['body'], str) else result['body']
            else:
                body = result
            
            if 'summary' in body:
                summary = body['summary']
                print(f"  ✅ Sucesso: {summary['successful']}/{summary['total_records']}")
                print(f"     Gas usado: {summary['total_gas_used']:,}")
                print(f"     E1 total: {summary['total_e1_value']:.6f} BRL")
                
                successful_batches += 1
                total_e1 += summary['total_e1_value']
                total_gas += summary['total_gas_used']
            else:
                print(f"  ⚠️ Resposta inesperada: {body}")
        
        all_results.append(result)
        
        # Aguardar um pouco entre lotes para não sobrecarregar
        if idx < total_batches:
            time.sleep(1)
    
    # Resumo final
    print("\n" + "=" * 70)
    print("📊 RESUMO FINAL")
    print("=" * 70)
    print(f"Total de registros processados: {total_records}")
    print(f"Lotes bem-sucedidos: {successful_batches}/{total_batches}")
    print(f"Lotes com erro: {failed_batches}/{total_batches}")
    print(f"Total E1 calculado: {total_e1:.6f} BRL")
    print(f"Gas total usado: {total_gas:,}")
    
    # Salvar resultados
    output_file = "lambda_results.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n💾 Resultados salvos em: {output_file}")
    
    print("\n" + "=" * 70)
    print("✨ PROCESSAMENTO CONCLUÍDO!")
    print("=" * 70)


if __name__ == "__main__":
    main()
