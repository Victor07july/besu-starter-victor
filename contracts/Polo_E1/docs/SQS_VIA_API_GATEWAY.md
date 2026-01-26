# Envio para SQS via API Gateway (SEM credenciais AWS locais)

Este guia mostra como enviar dados para SQS sem precisar configurar credenciais AWS no seu computador.

## 🎯 Arquitetura

```
send_to_sqs_via_api.py (HTTP, sem credenciais)
    ↓
API Gateway (público)
    ↓
Lambda "sqs-sender" (com IAM Role)
    ↓
SQS FIFO
    ↓
Lambda "blockchain" (2 instâncias paralelas)
    ↓
Blockchain
```

---

## 📋 Passo 1: Criar Lambda "sqs-sender"

### No Console AWS Lambda:

1. **Criar nova função:**
   - Console AWS → Lambda
   - Clique: **"Create function"**
   - **Function name:** `sqs-sender`
   - **Runtime:** Python 3.11
   - Clique: **"Create function"**

2. **Copiar código:**
   - Copie todo conteúdo de `/contracts/Polo_E1/aws/lambda/lambda_sqs_sender.py`
   - Cole no editor do Lambda
   - Clique: **"Deploy"**

3. **Configurar variável de ambiente:**
   - Aba **"Configuration"** → **"Environment variables"**
   - Clique: **"Edit"**
   - **Key:** `SQS_QUEUE_URL`
   - **Value:** `https://sqs.us-east-1.amazonaws.com/510805239628/polo-e1-queue.fifo`
   - Clique: **"Save"**

4. **Ajustar timeout:**
   - Aba **"Configuration"** → **"General configuration"** → **"Edit"**
   - **Timeout:** `30 seconds`
   - **Memory:** `256 MB`
   - Clique: **"Save"**

5. **Adicionar permissões SQS:**
   - Aba **"Configuration"** → **"Permissions"**
   - Clique no **Execution role**
   - **Add permissions** → **Attach policies**
   - Procure: `AWSLambdaSQSQueueExecutionRole`
   - Marque e clique: **"Add permissions"**

---

## 📋 Passo 2: Criar API Gateway para "sqs-sender"

### No Console API Gateway:

1. **Criar API:**
   - Console AWS → API Gateway
   - Clique: **"Create API"**
   - **REST API** (não private) → **"Build"**
   - **API name:** `sqs-sender-api`
   - Clique: **"Create API"**

2. **Criar método POST:**
   - Clique: **"Create Method"**
   - **Method type:** POST
   - **Integration type:** Lambda Function
   - **Lambda function:** `sqs-sender`
   - Clique: **"Create method"**

3. **Habilitar CORS:**
   - Selecione a API
   - **Actions** → **Enable CORS**
   - Deixe padrões marcados
   - Clique: **"Enable CORS"**

4. **Deploy API:**
   - **Actions** → **Deploy API**
   - **Deployment stage:** [New Stage]
   - **Stage name:** `default`
   - Clique: **"Deploy"**

5. **Copiar URL:**
   - Você verá: **Invoke URL**
   - Exemplo: `https://abc123.execute-api.us-east-1.amazonaws.com/default`
   - **URL completa:** `https://abc123.execute-api.us-east-1.amazonaws.com/default/sqs-sender`

https://r3zt1dfiej.execute-api.us-east-1.amazonaws.com/default/sqs-sender
---

## 📋 Passo 3: Atualizar Script Local

### Edite send_to_sqs_via_api.py:

Linha 11, substitua:
```python
API_GATEWAY_URL = "https://SEU_ID.execute-api.us-east-1.amazonaws.com/default/sqs-sender"
```

Por sua URL real copiada no passo anterior.

---

## 🚀 Como Usar

### Executar sem credenciais AWS:

```bash
cd /home/victor/besu-starter-victor/contracts/Polo_E1/aws
python3 send_to_sqs_via_api.py
```

✅ **Não precisa de `aws configure`!**

---

## 📊 Vantagens

- ✅ **Sem credenciais locais** (apenas HTTP)
- ✅ **Seguro** (IAM Role no Lambda)
- ✅ **Pronto para produção** (pode expor para frontend)
- ✅ **Batch processing** (10 registros por request)
- ✅ **Processamento paralelo** (2 Message Groups)

---

## 🔍 Monitorar

### CloudWatch Logs:

**Lambda sqs-sender:**
```bash
# Ver logs do Lambda que recebe do API Gateway
aws logs tail /aws/lambda/sqs-sender --follow
```

**Lambda blockchain:**
```bash
# Ver logs do Lambda que processa SQS
aws logs tail /aws/lambda/blockchain --follow
```

**SQS Console:**
- https://console.aws.amazon.com/sqs
- Veja mensagens em tempo real

---

## 💡 Próximos Passos

Depois de testar, você pode:
- Expor API Gateway para frontend web/mobile
- Adicionar autenticação (API Key, Cognito)
- Aumentar BATCH_SIZE para 50-100 registros
- Adicionar mais Message Groups (mais paralelismo)


curl --header "Content-Type: application/json" \
--request POST \
--data '
{
  "wallet": "0x4288201baC903F84648E81A07F793C9E7d893692",
  "vin": "JM1BM1V37F1238727",
  "usertank": "40"
}
' http://18.218.85.118/jwtserver/create/contract