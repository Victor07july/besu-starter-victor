# Arquitetura AWS - E1 Polo Blockchain

## Visão Geral da Arquitetura

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│   Script Local  │────────▶│   AWS Lambda    │────────▶│  Blockchain EC2 │
│   (read CSV)    │  HTTPS  │  (invoke smart  │   RPC   │   (Besu Node)   │
└─────────────────┘         │   contract)     │         └─────────────────┘
                            └─────────────────┘
                                    │
                                    ▼
                            ┌─────────────────┐
                            │   AWS Secrets   │
                            │   Manager       │
                            │ (Private Keys)  │
                            └─────────────────┘
```

## Componentes

1. **Script Local**: Lê CSV e envia dados para Lambda via API Gateway
2. **AWS Lambda**: Recebe dados e invoca contrato na blockchain
3. **Blockchain EC2**: Rede Besu rodando em instância EC2
4. **Secrets Manager**: Armazena chaves privadas de forma segura
5. **API Gateway**: Endpoint HTTP para invocar Lambda

---

## PASSO 1: Levantar Blockchain na AWS

### 1.1 Criar Instância EC2

```bash
# Tipo de instância recomendado: t3.medium ou t3.large
# AMI: Ubuntu 22.04 LTS
# Storage: 50GB SSD (mínimo)
# Security Group: Abrir portas 8545 (RPC), 30303 (P2P)
```

### 1.2 Instalar Besu na EC2

```bash
# Conectar via SSH
ssh -i sua-chave.pem ubuntu@<EC2-PUBLIC-IP>

# Instalar Java
sudo apt update
sudo apt install -y openjdk-17-jdk

# Instalar Besu
wget https://hyperledger.jfrog.io/hyperledger/besu-binaries/besu/23.10.0/besu-23.10.0.tar.gz
tar -xzf besu-23.10.0.tar.gz
sudo mv besu-23.10.0 /opt/besu

# Adicionar ao PATH
echo 'export PATH=$PATH:/opt/besu/bin' >> ~/.bashrc
source ~/.bashrc
```

### 1.3 Configurar Besu

```bash
# Criar diretório de dados
mkdir -p ~/besu-data

# Copiar configurações do seu projeto local
# Você pode usar scp para copiar seus arquivos de configuração
scp -i sua-chave.pem -r config/besu/* ubuntu@<EC2-PUBLIC-IP>:~/besu-config/
```

### 1.4 Iniciar Besu

```bash
# Criar script de inicialização
cat > ~/start-besu.sh << 'EOF'
#!/bin/bash
besu --data-path=~/besu-data \
  --genesis-file=~/besu-config/genesis.json \
  --rpc-http-enabled \
  --rpc-http-api=ETH,NET,WEB3,TXPOOL \
  --rpc-http-host=0.0.0.0 \
  --rpc-http-port=8545 \
  --rpc-http-cors-origins="*" \
  --host-allowlist="*" \
  --min-gas-price=0
EOF

chmod +x ~/start-besu.sh

# Iniciar Besu em background
nohup ~/start-besu.sh > besu.log 2>&1 &

# Verificar se está rodando
curl http://localhost:8545 -X POST -H "Content-Type: application/json" \
  --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
```

### 1.5 Configurar Security Group na AWS Console

- VPC → Security Groups → Seu Security Group
- Inbound Rules:
  - Tipo: Custom TCP
  - Porta: 8545
  - Origem: 0.0.0.0/0 (ou IP específico do Lambda/seu IP)
  - Descrição: Besu RPC

---

## PASSO 2: Configurar AWS Secrets Manager

### 2.1 Criar Secret para Chaves Privadas

```bash
# Via AWS CLI
aws secretsmanager create-secret \
  --name besu-blockchain-keys \
  --description "Private keys for Besu blockchain" \
  --secret-string '{
    "SENDER_ADDRESS": "0xfe3b557e8fb62b89f4916b721be55ceb828dbd73",
    "PRIVATE_KEY": "0x8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63"
  }'
```

### 2.2 Criar Secret para Endereço do Contrato

```bash
aws secretsmanager create-secret \
  --name besu-contract-config \
  --description "Smart contract addresses" \
  --secret-string '{
    "CONTRACT_ADDRESS": "0x0000000000000000000000000000000000000000",
    "RPC_URL": "http://<EC2-PUBLIC-IP>:8545"
  }'
```

---

## PASSO 3: Criar Lambda Function

### 3.1 Criar Role IAM para Lambda

```bash
# Criar política de permissões
cat > lambda-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:*:*:secret:besu-*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
EOF

# Criar role
aws iam create-role \
  --role-name BesuLambdaExecutionRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Anexar política
aws iam put-role-policy \
  --role-name BesuLambdaExecutionRole \
  --policy-name BesuLambdaPolicy \
  --policy-document file://lambda-policy.json
```

### 3.2 Criar Layer para Dependências

Veja instruções detalhadas em `aws/lambda/CREATE_LAYER.md`

### 3.3 Deploy da Lambda

Veja código em `aws/lambda/lambda_function.py` e instruções em `aws/lambda/DEPLOY.md`

---

## PASSO 4: Configurar API Gateway

### 4.1 Criar API REST

```bash
# Criar API
aws apigateway create-rest-api \
  --name "E1PoloBlockchainAPI" \
  --description "API for E1 Polo blockchain interactions"

# Anotar o API ID retornado
```

### 4.2 Criar Resource e Method

Via AWS Console:
1. API Gateway → APIs → E1PoloBlockchainAPI
2. Resources → Actions → Create Resource
   - Resource Name: `calculate-e1`
   - Resource Path: `/calculate-e1`
3. Actions → Create Method → POST
4. Integration type: Lambda Function
5. Lambda Function: selecionar sua função
6. Deploy API → New Stage → `prod`

### 4.3 Obter URL do Endpoint

```bash
# Formato: https://{api-id}.execute-api.{region}.amazonaws.com/{stage}/calculate-e1
# Exemplo: https://abc123def4.execute-api.us-east-1.amazonaws.com/prod/calculate-e1
```

---

## PASSO 5: Script Local para Enviar Dados

Veja código em `aws/send_to_lambda.py`

---

## Custos Estimados (AWS)

| Serviço | Tipo | Custo Estimado/Mês |
|---------|------|-------------------|
| EC2 | t3.medium (24/7) | ~$30 |
| Lambda | 1M requests, 512MB | ~$5 |
| API Gateway | 1M requests | ~$3.50 |
| Secrets Manager | 2 secrets | ~$0.80 |
| Storage (EBS) | 50GB | ~$5 |
| **TOTAL** | | **~$44/mês** |

### Como Reduzir Custos

1. **EC2**: Usar Spot Instances (~70% desconto)
2. **Lambda**: Reduzir memória se possível
3. **EC2**: Desligar quando não estiver usando
4. **Dados**: Processar em batch para reduzir chamadas

---

## Segurança

### Checklist de Segurança

- ✅ Chaves privadas no Secrets Manager (nunca no código)
- ✅ Security Group limitando acesso ao RPC
- ✅ API Gateway com autenticação (API Key ou IAM)
- ✅ Lambda com role IAM específico (least privilege)
- ✅ Logs habilitados (CloudWatch)
- ✅ VPC para Lambda e EC2 (opcional, mais seguro)
- ✅ HTTPS obrigatório no API Gateway

### Recomendações Adicionais

1. **API Key**: Adicionar API Key no API Gateway
2. **VPC**: Colocar Lambda e EC2 na mesma VPC
3. **Backup**: Backup regular dos dados da blockchain
4. **Monitoring**: CloudWatch Alarms para erros
5. **Rate Limiting**: Throttling no API Gateway

---

## Troubleshooting

### Lambda não consegue conectar ao Besu

```bash
# Verificar se Besu está rodando
ssh ubuntu@<EC2-IP>
curl http://localhost:8545 -X POST -H "Content-Type: application/json" \
  --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'

# Verificar Security Group
# Verificar se Lambda tem acesso à internet (NAT Gateway ou VPC endpoint)
```

### Erro de Gas

```bash
# Verificar saldo da conta
curl http://<EC2-IP>:8545 -X POST -H "Content-Type: application/json" \
  --data '{"jsonrpc":"2.0","method":"eth_getBalance","params":["0xSUACAONTA","latest"],"id":1}'
```

### Lambda Timeout

- Aumentar timeout da Lambda (default: 3s, máximo: 15 minutos)
- Processar dados em batch menor

---

## Próximos Passos

1. ✅ Seguir passos 1-5 acima
2. ✅ Deploy do contrato na blockchain EC2
3. ✅ Atualizar Secrets Manager com endereço do contrato
4. ✅ Testar com script local
5. ✅ Configurar monitoring e alertas
6. ✅ Documentar processo de backup/restore

---

## Recursos Úteis

- [Besu Documentation](https://besu.hyperledger.org/en/stable/)
- [AWS Lambda Python](https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html)
- [Web3.py Documentation](https://web3py.readthedocs.io/)
- [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/)
