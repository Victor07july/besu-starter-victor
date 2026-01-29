# Setup de 16 Carteiras Paralelas - Passo a Passo

## 📋 Objetivo
Configurar 16 carteiras paralelas para processar os registros de forma simultânea, reduzindo o tempo de processamento de ~2h50min (serial) para ~10-11 minutos (16 paralelos).

---

## ✅ Pré-requisitos

- Blockchain Besu rodando (Docker)
- AWS CLI configurado (`aws configure` ou `aws login`)
- Python 3.8+ com bibliotecas: `web3`, `boto3`, `pandas`, `requests`
- 16 arquivos CSV na pasta `/contracts/Polo_E1/data/` (vehicle_data_1.csv até vehicle_data_16.csv)
- **Já ter executado o setup de 8 carteiras anteriormente** (wallets_8_groups.json deve existir)

---

## 🚀 Passo 1: Adicionar Mais 8 Carteiras (group9-16)

**Objetivo:** Gerar 8 novas carteiras adicionais (group9 até group16) e transferir 10 ETH da carteira mãe para cada uma, PRESERVANDO as 8 carteiras existentes (group1-8).

```bash
cd /home/victor/besu-starter-victor/contracts/Polo_E1/aws
python add_8_more_wallets.py
```

**O que acontece:**
- ✅ Lê o arquivo `wallets_8_groups.json` existente (preserva groups 1-8)
- ✅ Gera **8 novos** pares de endereço/chave privada (group9-16)
- ✅ Transfere 10 ETH da carteira mãe para cada uma das **8 novas**
- ✅ Salva arquivo `wallets_16_groups.json` com **todas as 16 carteiras** (8 existentes + 8 novas)

**Tempo estimado:** ~2-3 minutos (8 transações)

**Verificação:**
- Arquivo `wallets_16_groups.json` criado na pasta `aws/` com 16 carteiras
- Saldos de 10 ETH confirmados para cada uma das 8 novas carteiras (group9-16)
- Carteiras existentes (group1-8) mantidas intactas

---

## ☁️ Passo 2: Criar Secrets no AWS Secrets Manager

**Objetivo:** Criar 8 novos secrets na AWS (região us-east-1) com as credenciais das novas carteiras (group9-16).

**Situação:**
- ✅ **group1 até group8**: JÁ EXISTEM (não serão alterados)
- 🆕 **group9 até group16**: NOVOS (serão criados)

### Opção A: Automaticamente via Script (Recomendado)

```bash
python create_aws_secrets_16_groups.py
```

**O que acontece:**
- ✅ Lê o arquivo `wallets_16_groups.json`
- 🔄 **Atualiza** 8 secrets existentes (group1 até group8) - apenas confirma os dados
- 🆕 **Cria** 8 novos secrets (group9 até group16)
- ✅ Cada secret contém: `SENDER_ADDRESS` e `PRIVATE_KEY` (uppercase)

**Tempo estimado:** ~1 minuto

---

### Opção B: Manualmente via AWS Console (Apenas para group9-16)

**1. Abrir o Arquivo JSON Local:**
```bash
cat wallets_16_groups.json
```
Copie os dados dos groups 9-16 (você vai precisar dos endereços e chaves privadas).

**2. Acessar AWS Secrets Manager:**
- Faça login na [AWS Console](https://console.aws.amazon.com/)
- Vá para **Secrets Manager** (buscar na barra superior)
- **Região:** Selecione **US East (N. Virginia) us-east-1** (canto superior direito)

**3. Criar Secrets Novos (group9 até group16):**

Para cada grupo de 9 a 16, repetir:

1. Clicar em **"Store a new secret"**

2. **Secret type:** Selecionar **"Other type of secret"**

3. **Key/value pairs:**
   - Clicar em **"Plaintext"**
   - Colar o JSON (adaptar para cada grupo):
   ```json
   {
     "SENDER_ADDRESS": "0x...",
     "PRIVATE_KEY": "0x..."
   }
   ```
   (Copiar do `wallets_16_groups.json` o endereço e chave do respectivo grupo)

4. Clicar em **"Next"**

5. **Secret name:** `besu-blockchain-keys-group9` (ou group10, group11, etc.)

6. **Description:** `Blockchain keys for vehicle_group_9`

7. Clicar em **"Next"** → **"Next"** → **"Store"**

**Repetir para todos os grupos 9 até 16!** (8 secrets no total)

**Tempo estimado manual:** ~10-15 minutos

---

## 🔧 Passo 3: Atualizar Lambda Function

**Objetivo:** Atualizar o código do Lambda `blockchain` para suportar 16 grupos paralelos e aumentar o reserved concurrency.

### 3A. Atualizar Código do Lambda

**1. Abrir o arquivo local atualizado:**
```bash
cat /home/victor/besu-starter-victor/contracts/Polo_E1/aws/lambda_functions/lambda_function_sqs.py
```

**2. No AWS Lambda Console:**
- Acessar [AWS Lambda Console](https://console.aws.amazon.com/lambda/)
- **Região:** us-east-1
- Abrir a função **`blockchain`**
- Aba **"Code"**
- Substituir TODO o código com o conteúdo do arquivo local
- **⚠️ IMPORTANTE:** Verificar que o dicionário `MESSAGE_GROUP_TO_SECRET` tem **16 entradas** (vehicle_group_1 até vehicle_group_16)
- Clicar em **"Deploy"**

**Tempo estimado:** ~2 minutos

---

### 3B. Atualizar Reserved Concurrency

**Objetivo:** Aumentar de 8 para 16 instâncias Lambda simultâneas.

**1. No AWS Lambda Console:**
- Abrir a função **`blockchain`**
- Aba **"Configuration"** → **"Concurrency"**
- Clicar em **"Edit"**

**2. Reserved Concurrency:**
- Marcar **"Reserve concurrency"**
- Valor: **`16`**
- Clicar em **"Save"**

**Verificação:**
- Concurrency = 16 na aba Configuration

**Tempo estimado:** ~1 minuto

---

## 📤 Passo 4: Processar os 16 CSVs

**Objetivo:** Enviar os dados dos 16 CSVs para o SQS via API Gateway, distribuindo entre os 16 grupos.

```bash
cd /home/victor/besu-starter-victor/contracts/Polo_E1/aws
python send_to_sqs_alternado.py
```

**O que acontece:**
- ✅ Lê 16 arquivos CSV (vehicle_data_1.csv até vehicle_data_16.csv)
- ✅ Envia 1 registro de cada CSV por vez (round-robin)
- ✅ Cada CSV é associado a um Message Group (vehicle_group_1 até vehicle_group_16)
- ✅ Lambda processa 16 mensagens simultaneamente (uma por grupo)
- ✅ Cada Lambda usa sua carteira correspondente (group1 usa secret group1, etc.)

**Tempo estimado:** ~10-15 minutos para processar todos os registros (depende do total de dados)

**Monitoramento:**
```bash
# Ver logs em tempo real
aws logs tail /aws/lambda/blockchain --follow

# Verificar métricas SQS
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/SEU_ACCOUNT_ID/polo-e1-queue.fifo \
  --attribute-names All
```

---

## ✅ Passo 5: Verificar Resultados

### 5.1 Verificar Saldos das Carteiras

```bash
# Via blockchain
curl -k https://ec2-18-117-255-42.us-east-2.compute.amazonaws.com/user/ \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "eth_getBalance",
    "params": ["0x...", "latest"],
    "id": 1
  }'
```

### 5.2 Verificar Logs Lambda

```bash
# Ver últimos logs
aws logs tail /aws/lambda/blockchain --since 10m

# Buscar erros
aws logs tail /aws/lambda/blockchain --filter-pattern "ERROR"
```

### 5.3 Verificar Fila SQS

- Acessar [SQS Console](https://console.aws.amazon.com/sqs/)
- Abrir `polo-e1-queue.fifo`
- **Messages Available:** Deve ser 0 quando concluir
- **Messages In Flight:** Número de mensagens sendo processadas

---

## 📊 Resultados Esperados

### Tempo de Processamento

Com 16 carteiras paralelas:

| Cenário | Tempo Estimado |
|---------|----------------|
| **Serial (1 carteira)** | ~2h50min |
| **8 paralelas** | ~21 minutos |
| **16 paralelas** | ~10-11 minutos |

### Estrutura de Arquivos

```
contracts/Polo_E1/
├── data/
│   ├── vehicle_data_1.csv
│   ├── vehicle_data_2.csv
│   ├── ...
│   └── vehicle_data_16.csv
│
├── aws/
│   ├── add_8_more_wallets.py           # Script para adicionar 8 carteiras
│   ├── create_aws_secrets_16_groups.py # Script para criar secrets
│   ├── wallets_8_groups.json           # 8 carteiras originais (preservado)
│   ├── wallets_16_groups.json          # 16 carteiras (8 + 8 novas)
│   ├── send_to_sqs_alternado.py        # Script para enviar dados (atualizado)
│   └── lambda_functions/
│       └── lambda_function_sqs.py      # Código Lambda (atualizado)
```

### AWS Secrets Manager

16 secrets criados:
- `besu-blockchain-keys-group1` (90k ETH - genesis)
- `besu-blockchain-keys-group2` (90k ETH - genesis)
- `besu-blockchain-keys-group3` (10 ETH - criada no setup 8 wallets)
- `besu-blockchain-keys-group4` (10 ETH - criada no setup 8 wallets)
- `besu-blockchain-keys-group5` (10 ETH - criada no setup 8 wallets)
- `besu-blockchain-keys-group6` (10 ETH - criada no setup 8 wallets)
- `besu-blockchain-keys-group7` (10 ETH - criada no setup 8 wallets)
- `besu-blockchain-keys-group8` (10 ETH - criada no setup 8 wallets)
- `besu-blockchain-keys-group9` (10 ETH - nova)
- `besu-blockchain-keys-group10` (10 ETH - nova)
- `besu-blockchain-keys-group11` (10 ETH - nova)
- `besu-blockchain-keys-group12` (10 ETH - nova)
- `besu-blockchain-keys-group13` (10 ETH - nova)
- `besu-blockchain-keys-group14` (10 ETH - nova)
- `besu-blockchain-keys-group15` (10 ETH - nova)
- `besu-blockchain-keys-group16` (10 ETH - nova)

### Lambda Configuration

- **Reserved Concurrency:** 16 (permite 16 instâncias simultâneas)
- **Timeout:** 150 segundos
- **Memory:** 512 MB
- **Runtime:** Python 3.14

---

## 🔍 Troubleshooting

### Erro: "wallets_8_groups.json not found"

**Causa:** Arquivo base não existe.

**Solução:**
```bash
# Verificar se existe
ls -la /home/victor/besu-starter-victor/contracts/Polo_E1/aws/wallets_8_groups.json

# Se não existir, execute primeiro o setup de 8 wallets
cd /home/victor/besu-starter-victor/contracts/Polo_E1/aws
python setup_8_wallets.py
```

---

### Erro: "Insufficient funds"

**Causa:** Carteira mãe sem saldo suficiente.

**Solução:**
```bash
# Verificar saldo da carteira mãe (0xfe3B557E8Fb62b89F4916B721be55cEb828dBd73)
# Deve ter pelo menos 80 ETH (8 carteiras × 10 ETH)
```

---

### Erro: "Secret already exists" (group1-8)

**Causa:** Secrets já existem de setup anterior.

**Solução:** Normal! O script atualiza automaticamente. Se quiser criar manualmente apenas group9-16, use a opção manual do Passo 2B.

---

### Lambda Timeout

**Causa:** Transação blockchain demorando muito.

**Solução:**
- Verificar Besu rodando: `docker ps | grep besu`
- Aumentar timeout Lambda: Configuration → General configuration → Timeout → 180 segundos

---

### SQS Messages não processando

**Causas possíveis:**
1. Lambda sem reserved concurrency = 16
2. Lambda código não atualizado (ainda com 8 grupos)
3. Secrets não criados (group9-16 faltando)

**Solução:**
```bash
# Verificar concurrency
aws lambda get-function-concurrency --function-name blockchain

# Verificar secrets
aws secretsmanager list-secrets --region us-east-1 | grep besu-blockchain

# Verificar mensagens na fila
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/SEU_ACCOUNT_ID/polo-e1-queue.fifo \
  --attribute-names ApproximateNumberOfMessages
```

---

## 🎯 Checklist Completo

### Antes de Começar
- [ ] Besu rodando (Docker)
- [ ] AWS CLI configurado
- [ ] Python 3.8+ com bibliotecas instaladas
- [ ] 16 CSVs na pasta `data/`
- [ ] **wallets_8_groups.json existe** (setup de 8 wallets já executado)

### Passo 1: Criar Carteiras
- [ ] Executar `add_8_more_wallets.py`
- [ ] Arquivo `wallets_16_groups.json` criado
- [ ] 8 transações confirmadas (group9-16)
- [ ] Saldos verificados (10 ETH cada)

### Passo 2: AWS Secrets
- [ ] Executar `create_aws_secrets_16_groups.py` OU criar manualmente
- [ ] 16 secrets no total (8 existentes + 8 novos)
- [ ] Secrets group9-16 criados com sucesso

### Passo 3: Lambda
- [ ] Código Lambda atualizado (16 grupos)
- [ ] Código deployado no AWS Console
- [ ] Reserved concurrency = 16

### Passo 4: Processar
- [ ] Executar `send_to_sqs_alternado.py`
- [ ] 16 CSVs carregados sem erro
- [ ] Mensagens enviadas ao SQS

### Passo 5: Verificar
- [ ] Logs Lambda sem erros críticos
- [ ] SQS "Messages Available" = 0
- [ ] Transações confirmadas na blockchain

---

## 🚀 Próximos Passos (Opcional)

### Escalar para 32 ou 64 Grupos

Se precisar de mais paralelização:

1. **Dividir CSVs:** Criar mais arquivos (vehicle_data_17.csv, etc.)
2. **Criar carteiras:** Adaptar script para criar mais wallets
3. **Lambda concurrency:** Aumentar para 32 ou 64
4. **Secrets:** Criar mais secrets (group17+)
5. **Atualizar código:** Expandir dicionário MESSAGE_GROUP_TO_SECRET

**Tempo estimado com 32 grupos:** ~5-6 minutos  
**Tempo estimado com 64 grupos:** ~3-4 minutos

---

## 📝 Notas Importantes

1. **Carteiras são aleatórias:** Cada execução de `add_8_more_wallets.py` gera novas carteiras. Faça backup do `wallets_16_groups.json`!

2. **Gas gratuito:** Blockchain Besu com `zeroBaseFee: true`, então 10 ETH é apenas margem de segurança.

3. **SQS FIFO:** Garante ordem dentro de cada Message Group, mas grupos processam em paralelo.

4. **Lambda Concurrency:** Reserved concurrency garante 16 instâncias dedicadas (não compete com outros Lambdas).

5. **CSV Header:** Todos os CSVs devem ter a linha de cabeçalho: `vehicle_id,model,fuel_type,start_time,end_time,start_lat,start_lon,end_lat,end_lon,distance,distance_city,distance_highway,CO2,NOx,PMx`

---

## 📞 Suporte

Em caso de dúvidas:
- Verificar logs: `aws logs tail /aws/lambda/blockchain --follow`
- Verificar saldos: Script Python com Web3.py
- Consultar CloudWatch Metrics para Lambda e SQS

---

**✅ Setup Completo! Processamento paralelo com 16 carteiras configurado.**
