# Atualizar AWS para 64 Grupos Paralelos

Guia rápido para atualizar a infraestrutura AWS e processar os 64 CSVs.

---

## ✅ Pré-requisitos

Antes de começar, certifique-se que você já executou:

1. ✅ `replicate_csvs_to_64.py` - 64 CSVs criados na pasta `data/`
2. ✅ `add_48_more_wallets.py` - 48 novas carteiras criadas (group17-64)
3. ✅ `wallets_64_groups.json` gerado com todas as 64 carteiras

---

## 📋 Passo 1: Criar 48 Novos Secrets AWS

Execute o script para criar os secrets das novas carteiras (group17-64):

```bash
cd /home/victor/besu-starter-victor/contracts/Polo_E1/aws
python create_aws_secrets_64_groups.py
```

**O que acontece:**
- Atualiza secrets existentes (group1-16)
- Cria 48 novos secrets (group17-64)
- Cada secret contém: `SENDER_ADDRESS` e `PRIVATE_KEY`

**Tempo estimado:** ~1-2 minutos

---

## 🔧 Passo 2: Atualizar Código do Lambda

### 2.1. Copiar o código atualizado

```bash
cat /home/victor/besu-starter-victor/contracts/Polo_E1/aws/lambda_functions/lambda_function_sqs.py
```

### 2.2. No AWS Lambda Console

1. Acesse: https://console.aws.amazon.com/lambda/
2. **Região:** us-east-1
3. Abra a função **`blockchain`**
4. Aba **"Code"**
5. Selecione todo o código e **substitua** pelo código copiado
6. **Verifique:** O dicionário `MESSAGE_GROUP_TO_SECRET` deve ter **64 entradas** (vehicle_group_1 até vehicle_group_64)
7. Clique em **"Deploy"**

**Tempo estimado:** ~2 minutos

---

## ⚙️ Passo 3: Atualizar Reserved Concurrency

### 3.1. No AWS Lambda Console

1. Na função **`blockchain`**
2. Aba **"Configuration"** → **"Concurrency"**
3. Clique em **"Edit"**
4. Marque **"Reserve concurrency"**
5. Valor: **`64`**
6. Clique em **"Save"**

**O que isso faz:**
- Garante que 64 instâncias Lambda podem rodar simultaneamente
- Cada instância processa 1 Message Group (1 carteira = 1 CSV)

**Tempo estimado:** ~1 minuto

---

## 📤 Passo 4: Executar o Envio dos 64 CSVs

Agora execute o script para enviar os dados:

```bash
cd /home/victor/besu-starter-victor/contracts/Polo_E1/aws
python send_to_sqs_alternado.py
```

**O que acontece:**
- Carrega os 64 CSVs
- Envia alternando entre os 64 grupos (round-robin)
- SQS distribui para as 64 carteiras em paralelo
- Lambda processa 64 mensagens simultaneamente

**Tempo estimado:** ~10-12 minutos (tempo do CSV maior)

---

## 🔍 Passo 5: Monitorar o Processamento

### Ver logs em tempo real:

```bash
aws logs tail /aws/lambda/blockchain --follow
```

### Verificar fila SQS:

```bash
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/SEU_ACCOUNT_ID/polo-e1-queue.fifo \
  --attribute-names ApproximateNumberOfMessages,ApproximateNumberOfMessagesNotVisible
```

### No AWS Console:

- **SQS:** https://console.aws.amazon.com/sqs/
  - `ApproximateNumberOfMessages` → mensagens aguardando
  - `ApproximateNumberOfMessagesNotVisible` → sendo processadas
  - Quando ambos = 0, processamento concluído!

- **CloudWatch:** https://console.aws.amazon.com/cloudwatch/
  - Lambda invocations
  - Erros
  - Duração média

---

## ✅ Checklist Rápido

- [ ] 64 CSVs existem na pasta `data/`
- [ ] wallets_64_groups.json gerado
- [ ] 64 secrets criados no AWS Secrets Manager
- [ ] Lambda código atualizado e deployado
- [ ] Lambda reserved concurrency = 64
- [ ] Script send_to_sqs_alternado.py executado
- [ ] Monitoramento ativo (logs/SQS)
- [ ] Processamento concluído (SQS = 0 mensagens)

---

## ⏱️ Resumo de Tempo

| Etapa | Tempo |
|-------|-------|
| Criar secrets AWS | ~1-2 min |
| Atualizar Lambda código | ~2 min |
| Atualizar concurrency | ~1 min |
| **Executar processamento** | **~10-12 min** |
| **TOTAL** | **~14-17 min** |

---

## 🚨 Troubleshooting

### Lambda Throttling

**Erro:** `Rate exceeded`

**Solução:** 
- Verifique reserved concurrency = 64
- Aguarde 1 minuto e tente novamente

### Secret não encontrado

**Erro:** `ResourceNotFoundException: Secrets Manager can't find the specified secret`

**Solução:**
```bash
# Verificar secrets
aws secretsmanager list-secrets --region us-east-1 | grep besu-blockchain

# Criar secrets faltando
python create_aws_secrets_64_groups.py
```

### Mensagens paradas no SQS

**Causa:** Lambda não está consumindo

**Solução:**
- Verificar se Lambda está ativo
- Verificar logs: `aws logs tail /aws/lambda/blockchain --since 5m`
- Verificar se evento SQS está configurado no Lambda

---

## 📊 Resultado Final

Após conclusão:

- ✅ 64 carteiras processaram seus CSVs em paralelo
- ✅ Tempo total: ~10-12 minutos
- ✅ Todas as transações confirmadas na blockchain
- ✅ SQS zerado (0 mensagens)

🎉 **Processamento paralelo com 64 carteiras concluído!**
