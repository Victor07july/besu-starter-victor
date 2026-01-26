# Configuração de Rede: Lambda → EC2 Blockchain

## Arquitetura Atual (Simples - Via Internet Pública)

```
┌────────────────────┐       Internet        ┌────────────────────┐
│  AWS Lambda        │───────────────────────▶│  AWS EC2 (Besu)   │
│  (Função Python)   │    HTTP (porta 8545)  │  IP Público        │
│  Web3.py           │                        │  Security Group    │
└────────────────────┘                        └────────────────────┘
```

## ⚙️ Configuração Passo a Passo

### PASSO 1: Configurar EC2 para aceitar conexões externas

#### 1.1 Conectar na EC2 via SSH
```bash
ssh -i sua-chave.pem ubuntu@ec2-XX-XXX-XX-XX.compute-1.amazonaws.com
```

#### 1.2 Verificar configuração do Besu
```bash
# Ver se Besu está rodando
ps aux | grep besu

# Ver configuração atual
cat ~/start-besu.sh
```

#### 1.3 Garantir que RPC aceita conexões externas
Editar script de inicialização:
```bash
nano ~/start-besu.sh
```

Conteúdo deve ter:
```bash
#!/bin/bash
besu --data-path=~/besu-data \
  --genesis-file=~/besu-config/genesis.json \
  --rpc-http-enabled \
  --rpc-http-api=ETH,NET,WEB3,TXPOOL \
  --rpc-http-host=0.0.0.0 \          # ← Aceita de qualquer IP
  --rpc-http-port=8545 \
  --rpc-http-cors-origins="*" \
  --host-allowlist="*" \              # ← Permite qualquer host
  --min-gas-price=0
```

#### 1.4 Reiniciar Besu
```bash
# Parar Besu
pkill -f besu

# Iniciar novamente
nohup ~/start-besu.sh > besu.log 2>&1 &

# Verificar se está rodando
tail -f besu.log
```

#### 1.5 Testar localmente na EC2
```bash
curl -X POST http://localhost:8545 \
  -H "Content-Type: application/json" \
  --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
```

### PASSO 2: Configurar Security Group da EC2

Via AWS Console:
1. EC2 → Instances → Selecionar sua instância
2. Security → Security groups → Clicar no security group
3. Inbound rules → Edit inbound rules
4. Add rule:
   - **Type**: Custom TCP
   - **Port range**: 8545
   - **Source**: 0.0.0.0/0 (ou IP específico)
   - **Description**: Besu RPC for Lambda

Ou via CLI:
```bash
# Obter Security Group ID
SG_ID=$(aws ec2 describe-instances \
  --instance-ids i-XXXXXXXX \
  --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' \
  --output text)

# Adicionar regra
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 8545 \
  --cidr 0.0.0.0/0
```

### PASSO 3: Obter URL de Conexão

#### Opção A: IP Público da EC2
```bash
# Via AWS Console: EC2 → Instance → Public IPv4 address
# Exemplo: 54.123.45.67

RPC_URL="http://54.123.45.67:8545"
```

#### Opção B: DNS Público da EC2
```bash
# Via AWS Console: EC2 → Instance → Public IPv4 DNS
# Exemplo: ec2-54-123-45-67.us-east-1.compute.amazonaws.com

RPC_URL="http://ec2-54-123-45-67.us-east-1.compute.amazonaws.com:8545"
```

#### Opção C: Elastic IP (Recomendado)
```bash
# Alocar Elastic IP
aws ec2 allocate-address --domain vpc

# Associar à instância
aws ec2 associate-address \
  --instance-id i-XXXXXXXX \
  --allocation-id eipalloc-XXXXXXXX

# Usar o Elastic IP
RPC_URL="http://52.123.45.67:8545"
```

### PASSO 4: Testar de Fora da EC2

Da sua máquina local:
```bash
# Substituir pelo seu IP/DNS da EC2
curl -X POST http://SEU-EC2-IP:8545 \
  -H "Content-Type: application/json" \
  --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
```

Resposta esperada:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": "0x123"
}
```

### PASSO 5: Atualizar Secrets Manager

```bash
# Atualizar com a URL correta
aws secretsmanager update-secret \
  --secret-id besu-contract-config \
  --secret-string '{
    "CONTRACT_ADDRESS": "0xSEU_CONTRATO_AQUI",
    "RPC_URL": "http://SEU-EC2-IP:8545"
  }'

# Verificar
aws secretsmanager get-secret-value \
  --secret-id besu-contract-config \
  --query SecretString \
  --output text | jq .
```

### PASSO 6: Testar Lambda

```bash
# Invocar Lambda diretamente
aws lambda invoke \
  --function-name E1PoloCalculator \
  --payload '{
    "distance_highway": 32.19,
    "distance_city": 22.28
  }' \
  --cli-binary-format raw-in-base64-out \
  response.json

# Ver resposta
cat response.json | jq .
```

## 🔒 Segurança Avançada

### Restringir acesso apenas da Lambda

#### 1. Lambda com IP Fixo (usando NAT Gateway)

```bash
# 1. Criar VPC e Subnet para Lambda
# 2. Criar NAT Gateway
# 3. Configurar Lambda na VPC
# 4. Obter IP do NAT Gateway
# 5. Restringir Security Group da EC2 apenas para esse IP
```

#### 2. VPC Peering (mesma conta AWS)

```
Lambda VPC ←→ Peering ←→ EC2 VPC
```

Configurar:
```bash
# 1. Criar VPC Peering Connection
aws ec2 create-vpc-peering-connection \
  --vpc-id vpc-lambda \
  --peer-vpc-id vpc-ec2

# 2. Aceitar peering
# 3. Atualizar route tables
# 4. Usar IP privado no RPC_URL
```

#### 3. VPN Site-to-Site (contas diferentes)

Para AWS em contas completamente diferentes.

## 🔍 Troubleshooting

### Lambda não conecta na EC2

**Problema 1: Security Group**
```bash
# Verificar regras
aws ec2 describe-security-groups --group-ids sg-XXXXX
```

**Problema 2: Besu não está escutando em 0.0.0.0**
```bash
# Na EC2, verificar
sudo netstat -tlnp | grep 8545

# Deve mostrar:
# 0.0.0.0:8545 (não 127.0.0.1:8545)
```

**Problema 3: Firewall do SO**
```bash
# Verificar firewall (Ubuntu)
sudo ufw status

# Se ativo, liberar porta
sudo ufw allow 8545/tcp
```

**Problema 4: Lambda sem acesso à internet**
- Lambda precisa estar em subnet pública OU
- Ter NAT Gateway configurado

### Testar conectividade da Lambda

Criar Lambda de teste:
```python
import json
import urllib.request

def lambda_handler(event, context):
    url = "http://SEU-EC2-IP:8545"
    data = {
        "jsonrpc": "2.0",
        "method": "eth_blockNumber",
        "params": [],
        "id": 1
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode(),
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read())
            return {
                'statusCode': 200,
                'body': json.dumps(result)
            }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
```

## 📊 Monitoramento

### CloudWatch Logs da Lambda
```bash
# Ver logs em tempo real
aws logs tail /aws/lambda/E1PoloCalculator --follow
```

### Logs do Besu na EC2
```bash
# Na EC2
tail -f ~/besu.log
```

## 💰 Custos

| Item | Custo |
|------|-------|
| EC2 t3.medium | ~$30/mês |
| Elastic IP (se usar) | Grátis (se associado) |
| Data Transfer OUT | $0.09/GB |
| Lambda invocations | Incluído no Lambda pricing |

**Nota**: Data transfer entre Lambda e EC2 na mesma região é grátis!

## ✅ Checklist Final

- [ ] Besu rodando com `--rpc-http-host=0.0.0.0`
- [ ] Security Group com porta 8545 aberta
- [ ] Teste de curl da sua máquina funciona
- [ ] Secrets Manager atualizado com RPC_URL correto
- [ ] Lambda tem permissão para acessar Secrets Manager
- [ ] Lambda consegue acessar a internet (NAT ou subnet pública)
- [ ] Contrato deployado na blockchain
- [ ] CONTRACT_ADDRESS atualizado no Secrets Manager
