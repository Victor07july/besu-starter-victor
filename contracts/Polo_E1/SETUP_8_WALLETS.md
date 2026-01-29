# Setup de 8 Carteiras Paralelas - Passo a Passo

## 📋 Objetivo
Configurar 8 carteiras paralelas para processar 3400 registros de forma simultânea, reduzindo o tempo de processamento de ~2h50min para ~21 minutos.

---

## ✅ Pré-requisitos

- Blockchain Besu rodando (Docker)
- AWS CLI configurado (`aws configure` ou `aws login`)
- Python 3.8+ com bibliotecas: `web3`, `boto3`, `pandas`, `requests`
- 8 arquivos CSV na pasta `/contracts/Polo_E1/data/` (vehicle_data_1.csv até vehicle_data_8.csv)

---

## 🚀 Passo 1: Criar 6 Novas Carteiras e Transferir ETH

**Objetivo:** Gerar 6 novas carteiras (group3 até group8) e transferir 10 ETH da carteira mãe para cada uma.

**Nota:** Você JÁ TEM 2 carteiras (group1 e group2 do genesis.json), este script cria as 6 faltantes para chegar a 8 no total.

```bash
cd /home/victor/besu-starter-victor/contracts/Polo_E1/aws
python setup_8_wallets.py
```

**O que acontece:**
- ✅ Gera **6 novos** pares de endereço/chave privada (group3-8)
- ✅ Transfere 10 ETH da carteira mãe (0xfe3b5...) para cada uma das **6 novas**
- ✅ Salva arquivo `wallets_8_groups.json` com **todas as 8 carteiras** (2 existentes + 6 novas)

**Tempo estimado:** ~2 minutos (6 transações)

**Verificação:**
- Arquivo `wallets_8_groups.json` criado na pasta `aws/` com 8 carteiras
- Saldos de 10 ETH confirmados para cada uma das 6 novas carteiras

---

## ☁️ Passo 2: Criar Secrets no AWS Secrets Manager

**Objetivo:** Criar ou atualizar 8 secrets na AWS (região us-east-1) com as credenciais das 8 carteiras.

**Situação:**
- ✅ **group1 e group2**: JÁ EXISTEM (serão atualizados com os dados atuais do genesis.json)
- 🆕 **group3 até group8**: NOVOS (serão criados)

### Opção A: Automaticamente via Script (Recomendado)

```bash
python create_aws_secrets_8_groups.py
```

**O que acontece:**
- ✅ Lê o arquivo `wallets_8_groups.json`
- 🔄 **Atualiza** 2 secrets existentes (group1 e group2)
- 🆕 **Cria** 6 novos secrets (group3 até group8)
- ✅ Cada secret contém: `SENDER_ADDRESS` e `PRIVATE_KEY` (uppercase)

**Tempo estimado:** ~30 segundos

---

### Opção B: Manualmente via AWS Console

**1. Abrir o Arquivo JSON Local:**
```bash
cat wallets_8_groups.json
```
Copie o conteúdo (você vai precisar dos endereços e chaves privadas).

**2. Acessar AWS Secrets Manager:**
- Faça login na [AWS Console](https://console.aws.amazon.com/)
- Vá para **Secrets Manager** (buscar na barra superior)
- **Região:** Selecione **US East (N. Virginia) us-east-1** (canto superior direito)

**3A. Atualizar Secrets Existentes (group1 e group2):**

Para group1 e group2 (se quiser usar as carteiras do genesis.json):

1. Clicar no secret **`besu-blockchain-keys-group1`** (ou group2)

2. Clicar em **"Retrieve secret value"** → **"Edit"**

3. **Plaintext:** Atualizar com:
   ```json
   {
     "SENDER_ADDRESS": "0x627306090abaB3A6e1400e9345bC60c78a8BEf57",
     "PRIVATE_KEY": "0xc87509a1c067bbde78beb793e6fa76530b6382a4c0241e5e4a9ec0a0f44dc0d3"
   }
   ```
   (Para group2, usar o endereço e chave correspondentes do JSON)

4. Clicar em **"Save"**

**Repetir para group2!**

---

**3B. Criar Novos Secrets (group3 até group8):**

Para cada grupo novo (3 até 8):

1. Clicar em **"Store a new secret"**

2. **Secret type:** Selecionar **"Other type of secret"**

3. **Key/value pairs:**
   - Clicar em **"Plaintext"** (tab no topo)
   - Colar JSON no formato:
   ```json
   {
     "SENDER_ADDRESS": "0xENDERECO_DO_GRUPO_X",
     "PRIVATE_KEY": "0xCHAVE_PRIVADA_DO_GRUPO_X"
   }
   ```
   ⚠️ **Importante:** Use UPPERCASE (`SENDER_ADDRESS` e `PRIVATE_KEY`)

4. **Encryption key:** Deixar `aws/secretsmanager` (padrão)

5. Clicar em **"Next"**

6. **Secret name:** Digitar exatamente:
   - `besu-blockchain-keys-group3`
   - `besu-blockchain-keys-group4`
   - ... até `besu-blockchain-keys-group8`

7. **Description** (opcional): `Blockchain keys for vehicle_group_X`

8. Clicar em **"Next"**

9. **Rotation:** Deixar desabilitado

10. Clicar em **"Next"**

11. **Review:** Verificar tudo e clicar em **"Store"**

**Repetir para os 6 novos grupos (3 até 8)!**

**Tempo estimado:** ~5 minutos

---

**Verificação AWS Console:**
- AWS Console → Secrets Manager → Região: us-east-1
- Verificar que existem 8 secrets: `besu-blockchain-keys-group1` até `group8`

---

## 🔧 Passo 3: Atualizar Lambda "blockchain" na AWS

### 3.1 Atualizar Código do Lambda

**No AWS Console:**
1. Lambda → Functions → `blockchain`
2. Aba **Code** → Clicar no arquivo `lambda_function.py`
3. **Copiar todo o conteúdo** do arquivo local:
   ```
   /contracts/Polo_E1/aws/lambda_functions/lambda_function_sqs.py
   ```
4. **Colar** no editor da AWS (substituir tudo)
5. Clicar em **Deploy**
6. Aguardar ~10 segundos até aparecer "Changes deployed successfully"

**Mudança crítica:** O dicionário `MESSAGE_GROUP_TO_SECRET` agora tem 8 grupos.

### 3.2 Configurar Reserved Concurrency

**No AWS Console:**
1. Lambda → Functions → `blockchain`
2. Aba **Configuration** → Menu lateral **Concurrency**
3. Clicar em **Edit**
4. Marcar **Reserve concurrency**
5. Digitar: **8**
6. Clicar em **Save**

**O que isso faz:** Permite que 8 instâncias da Lambda rodem simultaneamente (1 por Message Group).

**Tempo estimado:** ~2 minutos

---

## 🚀 Passo 4: Processar os 8 CSVs

**Objetivo:** Enviar todos os registros dos 8 CSVs para o SQS FIFO, que dispara as 8 Lambdas em paralelo.

```bash
cd /home/victor/besu-starter-victor/contracts/Polo_E1/aws
python send_to_sqs_alternado.py
```

**O que acontece:**
- ✅ Lê os 8 CSVs da pasta `../data/`
- ✅ Envia registros alternando entre os grupos (1 de cada vez, round-robin)
- ✅ API Gateway → Lambda "sqs-sender" → SQS FIFO → 8 Lambdas "blockchain" paralelas

**Tempo estimado:** 
- Envio: ~5-10 minutos (depende da velocidade da rede)
- Processamento: ~21 minutos (8 Lambdas processando simultaneamente)

**Verificação em tempo real (CloudWatch Logs):**
```bash
# Monitorar logs da Lambda "blockchain"
aws logs tail /aws/lambda/blockchain --since 5m --region us-east-1 --follow
```

Você verá logs de 8 execuções paralelas com diferentes `RequestId`.

---

## 📊 Passo 5: Verificar Resultados

### 5.1 Verificar CloudWatch Logs

```bash
aws logs tail /aws/lambda/blockchain --since 10m --region us-east-1
```

**Procure por:**
- ✅ "Message Group: vehicle_group_X" (X de 1 até 8)
- ✅ "Transação confirmada no bloco XXXX"
- ✅ "E1 calculado: 0.XXXXXX BRL" (valores diferentes de 0)
- ✅ Múltiplos `RequestId` diferentes (prova de execução paralela)

### 5.2 Verificar SQS (Opcional)

**AWS Console:**
- SQS → Queues → `polo-e1-queue.fifo`
- Aba **Monitoring** → Verificar gráfico de mensagens processadas

### 5.3 Estatísticas Finais

No final da execução do `send_to_sqs_alternado.py`, você verá:
```
Veículo 1:
  ✅ Enviados: XXX
  ❌ Falhas: 0
...
Veículo 8:
  ✅ Enviados: XXX
  ❌ Falhas: 0

Total:
  ✅ Enviados: 3400
  ❌ Falhas: 0
  ⏱️  Tempo: XXX segundos
```

---

## 🔍 Troubleshooting

### ❌ Erro: "insufficient funds"
**Causa:** Carteira nova não recebeu ETH  
**Solução:** Re-executar `setup_8_wallets.py`

### ❌ Erro: "AccessDenied" ao criar secrets
**Causa:** AWS CLI não configurado  
**Solução:** Executar `aws configure` ou `aws login`

### ❌ Erro: "KeyError: 'vehicle_group_X'"
**Causa:** Lambda não atualizado com 8 grupos  
**Solução:** Re-fazer Passo 3.1 (atualizar código da Lambda)

### ❌ Lambda só processa 2 simultâneas (não 8)
**Causa:** Reserved concurrency não configurado  
**Solução:** Re-fazer Passo 3.2 (configurar concurrency = 8)

### ❌ Distâncias aparecem como 0 km
**Causa:** Bug no código da Lambda (já corrigido)  
**Solução:** Verificar que o código tem `record_data = message_body.get('record', {})` na linha 233

---

## 📈 Resultados Esperados

| Métrica | Valor |
|---------|-------|
| **CSVs processados** | 8 |
| **Total de registros** | 3400 |
| **Lambdas paralelas** | 8 |
| **Tempo de processamento** | ~21 minutos |
| **Speedup vs serial** | ~8x mais rápido |
| **Custos AWS** | ~$0.50 (Lambda + Secrets + SQS) |

---

## ✅ Checklist Final

- [ ] Passo 1: `wallets_8_groups.json` criado com 8 carteiras
- [ ] Passo 2: 8 secrets criados no AWS Secrets Manager
- [ ] Passo 3.1: Lambda "blockchain" atualizado com código novo
- [ ] Passo 3.2: Reserved concurrency = 8 configurado
- [ ] Passo 4: Script `send_to_sqs_alternado.py` executado
- [ ] Passo 5: CloudWatch logs mostrando 8 grupos processando
- [ ] Resultado: 3400 registros processados com sucesso

---

## 🎉 Próximos Passos (Opcional)

**Para escalar para 64 carteiras:**
1. Modificar `setup_8_wallets.py` para gerar **62 novas carteiras** (você já tem 2, faltam 62)
2. Atualizar `MESSAGE_GROUP_TO_SECRET` para 64 grupos
3. Configurar reserved concurrency = 64
4. Dividir dados em 64 CSVs (~53 registros cada)

**Tempo estimado com 64 carteiras:** ~2.7 minutos (vs 2h50min original)

---

## 📞 Suporte

Problemas? Verificar:
1. Logs do CloudWatch (`/aws/lambda/blockchain`)
2. Saldos das carteiras na blockchain
3. Status dos secrets no AWS Console
4. Configuração de concurrency da Lambda


curl --header "Content-Type: application/json" \
--request POST \
--data '
{
  "wallet": "0x4288201baC903F84648E81A07F793C9E7d893692",
  "vin": "JM1BM1V37F1238727",
  "usertank": "40"
}
' http://181.77.231.104/jwt/create/contract