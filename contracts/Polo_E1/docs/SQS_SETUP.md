# Configuração AWS SQS FIFO para Processamento Paralelo

## 🎯 Objetivo

Processar 2 CSVs simultaneamente usando SQS FIFO com Message Groups, evitando conflito de nonce.

---

## 📋 Passo 1: Criar Fila SQS FIFO

### No Console AWS:

1. **Acesse SQS:**
   - Console AWS → SQS
   - Região: **us-east-1**

2. **Criar Fila:**
   - Clique: **"Create queue"**
   - **Type:** FIFO
   - **Name:** `polo-e1-queue.fifo`
   - **Content-based deduplication:** ❌ Desabilitado
   - **Visibility timeout:** `180 seconds` (3 minutos)
   - **Message retention period:** `4 days`
   - **Delivery delay:** `0 seconds`
   - **Receive message wait time:** `0 seconds`
   - Clique: **"Create queue"**

3. **Copiar URL:**
   - Copie a **Queue URL**
   - Exemplo: `https://sqs.us-east-1.amazonaws.com/123456789012/polo-e1-queue.fifo`

   https://sqs.us-east-1.amazonaws.com/510805239628/polo-e1-queue.fifo

---

## 📋 Passo 2: Usar Contas do Genesis

Para evitar conflito de nonce, cada Message Group usa uma conta diferente.

### Contas do genesis.json (já têm saldo):

**Conta 1 (vehicle_group_1):**
- Address: `0x627306090abaB3A6e1400e9345bC60c78a8BEf57`
- Private Key: `0xc87509a1c067bbde78beb793e6fa76530b6382a4c0241e5e4a9ec0a0f44dc0d3`

**Conta 2 (vehicle_group_2):**
- Address: `0xf17f52151EbEF6C7334FAD080c5704D77216b732`
- Private Key: `0xae6ae8e5ccbfb04590405997ee2d52d2b330726137b875053c36d94e974d162f`

✅ Ambas já possuem saldo suficiente (90000 ETH). Não precisa transferir fundos!

---

## 📋 Passo 3: Criar Secrets Manager

### No Console AWS:

1. **Acesse Secrets Manager:**
   - Console AWS → Secrets Manager
   - Região: **us-east-1** (mesma do Lambda)
   - Clique: **"Store a new secret"**

---

### **Criar Secret 1: besu-blockchain-keys-group1**

2. **Secret type:**
   - Selecione: **"Other type of secret"**

3. **Key/value pairs:**
   - Clique: **"Plaintext"** (aba superior)
   - Apague tudo e cole:
   ```json
   {
     "address": "0x627306090abaB3A6e1400e9345bC60c78a8BEf57",
     "private_key": "0xc87509a1c067bbde78beb793e6fa76530b6382a4c0241e5e4a9ec0a0f44dc0d3"
   }
   ```
   - Clique: **"Next"**

4. **Secret name:**
   - Secret name: `besu-blockchain-keys-group1`
   - Description: `Conta blockchain para vehicle_group_1 (genesis.json)`
   - Clique: **"Next"**

5. **Configure rotation:**
   - Deixe: **"Disable automatic rotation"**
   - Clique: **"Next"**

6. **Review:**
   - Revise as informações
   - Clique: **"Store"**

---

### **Criar Secret 2: besu-blockchain-keys-group2**

7. **Repita os passos 1-6 com os dados:**
   - **Plaintext:**
   ```json
   {
     "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
     "private_key": "0xae6ae8e5ccbfb04590405997ee2d52d2b330726137b875053c36d94e974d162f"
   }
   ```
   - **Secret name:** `besu-blockchain-keys-group2`
   - **Description:** `Conta blockchain para vehicle_group_2 (genesis.json)`

---

### ✅ Resultado:

Você terá 3 secrets no total:
- `besu-blockchain-keys` (antigo, pode manter como backup)
- `besu-blockchain-keys-group1` ✨ (novo)
- `besu-blockchain-keys-group2` ✨ (novo)

---

## 📋 Passo 4: Atualizar Permissões IAM (FAZER PRIMEIRO!)

### Lambda precisa de permissão para SQS:

1. **Acesse IAM Role do Lambda:**
   - Console AWS → Lambda
   - Função: **blockchain**
   - Aba **"Configuration"** → **"Permissions"**
   - Clique no **Execution role** (abre IAM em nova aba)

2. **Adicionar Policy:**
   - Clique: **"Add permissions"** → **"Attach policies"**
   - Procure: `AWSLambdaSQSQueueExecutionRole`
   - Marque a checkbox
   - Clique: **"Add permissions"**

✅ **Importante:** Aguarde 30 segundos para permissões propagarem!

---

## 📋 Passo 5: Configurar Lambda Trigger (SQS)

### No Console Lambda:

1. **Acesse a função Lambda:**
   - Console AWS → Lambda
   - Função: **blockchain**

2. **PRIMEIRO: Ajustar Timeout (FAZER ANTES DO TRIGGER!):**
   - Aba **"Configuration"** → **"General configuration"**
   - Clique: **"Edit"**
   - **Timeout:** `2 minutes 30 seconds` (150 segundos) ⚠️ DEVE SER MENOR QUE 180s
   - **Memory:** `512 MB`
   - Clique: **"Save"**

3. **Aguarde 10 segundos**, depois adicionar Trigger:
   - Volte para a aba **"Configuration"** → **"Triggers"**
   - Clique: **"Add trigger"**
   - **Source:** SQS
   - **SQS queue:** `polo-e1-queue.fifo`
   - **Batch size:** `1` (1 mensagem por invocação)
   - **Enabled:** ✅ Sim
   - Clique: **"Add"**

4. **Configurar Concorrência:**
   - Aba **"Configuration"** → **"Concurrency"**
   - **Reserved concurrency:** `2` (máximo 2 Lambdas simultâneas)
   - Clique: **"Save"**

---

## 📋 Passo 6: Atualizar Código do Lambda

### Substituir código atual por lambda_function_sqs.py:

1. **Acesse a função Lambda:**
   - Console AWS → Lambda
   - Função: **blockchain**
   - Aba **"Code"**

2. **Substituir código:**
   - Apague todo o conteúdo de `lambda_function.py`
   - Copie o conteúdo de `/contracts/Polo_E1/aws/lambda/lambda_function_sqs.py`
   - Cole no editor do Lambda
   - Clique: **"Deploy"**

---

## 📋 Passo 7: Atualizar Scripts Locais

### send_to_sqs.py:

Atualizar linha 13:
```python
SQS_QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/SUA_CONTA/polo-e1-queue.fifo"
```

Substituir `SUA_CONTA` pelo número da sua conta AWS.

---

## 🚀 Como Usar

### 1. Enviar dados para SQS:

```bash
cd /home/victor/besu-starter-victor/contracts/Polo_E1/aws
python3 send_to_sqs.py
```

### 2. Monitorar processamento:

```bash
# CloudWatch Logs
aws logs tail /aws/lambda/blockchain --follow

# SQS Console
# Veja mensagens sendo processadas em tempo real
```

---

## 🔍 Como Funciona

### Fluxo:

```
send_to_sqs.py
    ↓
vehicle_data_1.csv → SQS (Group 1) → Lambda 1 (0x6273...) → Blockchain
vehicle_data_2.csv → SQS (Group 2) → Lambda 2 (0xf17f...) → Blockchain
```

### Vantagens:

- ✅ **2 Lambdas simultâneas** (uma por Message Group)
- ✅ **Sem conflito de nonce** (cada Lambda usa conta diferente)
- ✅ **Ordem garantida** dentro de cada grupo
- ✅ **Retry automático** se falhar
- ✅ **Contas do genesis** (já com saldo, sem transferências)
- ✅ **Persistência** (mensagens não se perdem)

---

## ⚙️ Parâmetros Importantes

### Batch Size: 1
- Cada Lambda processa **1 mensagem** por vez
- Evita timeout (cada transação demora ~2-3 segundos)

### Message Groups: 2
- `vehicle_group_1`, `vehicle_group_2`
- AWS garante ordem dentro de cada grupo
- Grupos diferentes = processamento paralelo

### Visibility Timeout: 180s
- Tempo que mensagem fica "invisível" após ser lida
- Se Lambda falhar, mensagem volta para fila após 180s

### Reserved Concurrency: 2
- Máximo de 2 Lambdas executando ao mesmo tempo
- Previne custos inesperados

---

## 📊 Estimativa de Tempo

Com 2 CSVs de ~1700 registros cada (~3400 registros total):

- **Sem SQS (serial):** ~3400 registros × 3s = **2h50min**
- **Com SQS (paralelo):** ~1700 registros × 3s = **1h25min** (2x mais rápido!)

---

## 🐛 Troubleshooting

### Mensagens não estão sendo processadas:
- Verifique se Lambda Trigger está habilitado
- Confira permissões IAM
- Veja CloudWatch Logs

### Erro de nonce:
- Certifique-se de usar contas diferentes para cada grupo
- Verifique secrets no Secrets Manager

### Lambda timeout:
- Aumente timeout para 3 minutos
- Reduza batch_size para 1

---

## 💡 Próximos Passos

Após configurar tudo, basta rodar:

```bash
python3 send_to_sqs.py
```

E acompanhar o processamento em tempo real! 🚀
