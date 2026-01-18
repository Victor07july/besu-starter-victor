import boto3
import json
from datetime import datetime

timestream = boto3.client('timestream-write')

DATABASE_NAME = 'app_gabriel'
TABLE_NAME = 'dados_app'

def lambda_handler(event, context):
    try:
        print("==== Início da execução da Lambda ====")

        if 'body' in event:
            data = json.loads(event['body'])
            print("Evento recebido via API Gateway (event['body'])")
        else:
            data = event
            print("Evento recebido diretamente")

        print(f"Quantidade de itens recebidos: {len(data)}")

        records = []

        for idx, item in enumerate(data):
            print(f"\n-- Processando item {idx+1} --")

            timestamp_str = item["timestamp"]
            timestamp_epoch_ms = str(int(datetime.fromisoformat(timestamp_str.replace("Z", "+00:00")).timestamp() * 1000))
            print(f"Timestamp convertido para epoch ms: {timestamp_epoch_ms}")

            vin = item["uservehicle"]["vin"]
            device_id = item["device_id"]
            signature = item["uservehicle"]["userdata"]["signature"]

            base_dimensions = [
                {"Name": "vin", "Value": vin, "DimensionValueType": "VARCHAR"},
                {"Name": "device_id", "Value": device_id, "DimensionValueType": "VARCHAR"},
                {"Name": "signature", "Value": signature[:100], "DimensionValueType": "VARCHAR"}
            ]

            measures = {
                "total_tanque_litros": float(item["total_tanque_litros"]),
                "total_abastecido_litros": float(item["total_abastecido_litros"]),
                "percentual_abastecido": float(item["percentual_abastecido"]),
                "latitude": float(item["latitude"]),
                "longitude": float(item["longitude"]),
                "media_movel_nivel_combustivel_antes": float(item["media_movel_nivel_combustivel_antes"]),
                "media_movel_nivel_combustivel": float(item["media_movel_nivel_combustivel"]),
                "diferenca_percentual_detectada": float(item["diferenca_percentual_detectada"])
            }

            for key, value in measures.items():
                record = {
                    'Dimensions': base_dimensions,
                    'MeasureName': key,
                    'MeasureValue': str(value),
                    'MeasureValueType': 'DOUBLE',
                    'Time': timestamp_epoch_ms,
                    'TimeUnit': 'MILLISECONDS'
                }
                records.append(record)

            records.append({
                'Dimensions': base_dimensions,
                'MeasureName': 'imagem_hash',
                'MeasureValue': item["imagem_hash"],
                'MeasureValueType': 'VARCHAR',
                'Time': timestamp_epoch_ms,
                'TimeUnit': 'MILLISECONDS'
            })

            for entry in item["uservehicle"]["userdata"]["userdata"]:
                pid = entry["pid"]
                obddata = entry["obddata"]
                title = obddata["title"]
                unit = obddata["unit"]
                response_str = obddata["response"]

                if response_str.strip() != "":
                    try:
                        response_value = float(response_str)

                        obd_dimensions = base_dimensions + [
                            {"Name": "pid", "Value": pid, "DimensionValueType": "VARCHAR"},
                            {"Name": "obd_title", "Value": title, "DimensionValueType": "VARCHAR"},
                            {"Name": "obd_unit", "Value": unit, "DimensionValueType": "VARCHAR"}
                        ]

                        obd_record = {
                            'Dimensions': obd_dimensions,
                            'MeasureName': 'obd_response',
                            'MeasureValue': str(response_value),
                            'MeasureValueType': 'DOUBLE',
                            'Time': timestamp_epoch_ms,
                            'TimeUnit': 'MILLISECONDS'
                        }
                        records.append(obd_record)
                    except ValueError:
                        print(f"⚠️ Valor inválido para float em PID {pid}: '{response_str}', ignorando este registro.")
                else:
                    print(f"⚠️ Campo 'response' vazio para PID {pid}, ignorando este registro.")
            print(f"Item {idx+1} processado. Registros preparados até agora: {len(records)}")

        print(f"Total de registros a serem enviados: {len(records)}")
        print("Enviando para o Timestream...")

        BATCH_SIZE = 100
        for i in range(0, len(records), BATCH_SIZE):
            batch = records[i:i+BATCH_SIZE]
            response = timestream.write_records(
                DatabaseName=DATABASE_NAME,
                TableName=TABLE_NAME,
                Records=batch
            )
            print(f"Lote enviado: registros {i+1} a {i+len(batch)}")

        print("✅ Todos os dados enviados com sucesso ao Timestream.")
        print(f"Última resposta da AWS: {response}")

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Dados enviados com sucesso!', 'response': str(response)})
        }

    except Exception as e:
        print("❌ Erro durante a execução da Lambda")
        print(f"Detalhes do erro: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
