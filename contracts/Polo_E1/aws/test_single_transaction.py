"""
Script de TESTE para enviar UMA ÚNICA transação
Testa a conexão: CSV → API Gateway → SQS → Lambda → Blockchain
"""

import requests
import json
import time

# Configuração
API_GATEWAY_URL = "https://r3zt1dfiej.execute-api.us-east-1.amazonaws.com/default"
TEST_MESSAGE_GROUP = "vehicle_group_1"  # Qual carteira usar (1-64)

# Dados de teste (1 registro fictício)
TEST_RECORD = {
    "distance_highway": 100,
    "distance_city": 50,
    "city_gasoline": 13.5,
    "road_gasoline": 15.7,
    "city_ethanol": 9.3,
    "road_ethanol": 10.9,
    "city_gnv": 15.1,
    "road_gnv": 16.8,
    "co2_per_liter": 2.31,
    "co2_per_liter_ethanol": 2.15,
    "co2_per_m3_gnv": 2.74
}


def test_connection():
    """Envia 1 transação de teste e monitora resultado"""
    
    print("=" * 70)
    print("🧪 TESTE DE CONEXÃO - Uma Única Transação")
    print("=" * 70)
    print(f"📍 API Gateway: {API_GATEWAY_URL}")
    print(f"👛 Carteira: {TEST_MESSAGE_GROUP}")
    print(f"📊 Dados: {json.dumps(TEST_RECORD, indent=2)}\n")
    
    # Preparar payload
    payload = {
        "records": [TEST_RECORD],
        "message_group": TEST_MESSAGE_GROUP
    }
    
    print("📤 Enviando para API Gateway...")
    start_time = time.time()
    
    try:
        response = requests.post(
            API_GATEWAY_URL,
            json=payload,
            timeout=30
        )
        
        elapsed = time.time() - start_time
        
        # Verificar resposta
        response.raise_for_status()
        result = response.json()
        
        print(f"✅ API Gateway respondeu em {elapsed:.2f}s")
        print(f"📨 Response: {json.dumps(result, indent=2)}\n")
        
        # Parsear body (Lambda retorna body como string JSON)
        if 'body' in result:
            body = json.loads(result['body'])
            sent_count = body.get('sent', 0)
            
            if sent_count > 0:
                print("=" * 70)
                print("✅ MENSAGEM ENVIADA PARA O SQS COM SUCESSO!")
                print("=" * 70)
                print(f"📬 {sent_count} mensagem(ns) na fila SQS")
                print(f"🔄 Lambda processará em breve...")
                print("\n💡 Para monitorar o processamento, execute:")
                print("   aws logs tail /aws/lambda/blockchain --follow")
                print("=" * 70)
            else:
                print("⚠️ Nenhuma mensagem enviada. Verifique os logs.")
        else:
            print("⚠️ Resposta inesperada da API Gateway")
        
    except requests.exceptions.Timeout:
        print("❌ TIMEOUT: API Gateway não respondeu em 30 segundos")
        print("   Verifique se o Lambda está configurado corretamente")
        
    except requests.exceptions.HTTPError as e:
        print(f"❌ ERRO HTTP: {e}")
        print(f"   Response: {response.text}")
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
    
    print()


def check_queue_status():
    """Verifica status da fila SQS (requer AWS CLI configurado)"""
    import subprocess
    
    print("\n📊 Verificando status da fila SQS...")
    
    try:
        result = subprocess.run([
            'aws', 'sqs', 'get-queue-attributes',
            '--queue-url', 'https://sqs.us-east-1.amazonaws.com/510805239628/polo-e1-queue.fifo',
            '--attribute-names', 'ApproximateNumberOfMessages,ApproximateNumberOfMessagesNotVisible'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            attrs = data.get('Attributes', {})
            waiting = attrs.get('ApproximateNumberOfMessages', 'N/A')
            processing = attrs.get('ApproximateNumberOfMessagesNotVisible', 'N/A')
            
            print(f"   🟡 Aguardando: {waiting} mensagens")
            print(f"   🔵 Processando: {processing} mensagens\n")
        else:
            print("   ⚠️ Não foi possível verificar SQS (AWS CLI não configurado?)\n")
    
    except Exception as e:
        print(f"   ⚠️ Erro ao verificar SQS: {e}\n")


def main():
    """Executa teste completo"""
    test_connection()
    
    # Opcional: verificar fila
    try:
        check_queue_status()
    except:
        pass
    
    print("🏁 Teste concluído!\n")


if __name__ == "__main__":
    main()
