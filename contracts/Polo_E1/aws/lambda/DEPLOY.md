# Deploy da Lambda Function

## Pré-requisitos

- AWS CLI instalado e configurado
- Python 3.9+
- Conta AWS com permissões adequadas

aws secretsmanager create-secret \
  --secret-id besu-contract-config \
  --secret-string '{
    "CONTRACT_ADDRESS": "0x42699A7612A82f1d9C36148af9C77354759b210b",
    "RPC_URL": "http://18.117.255.42:8545"
  }'

## Passo 1: Criar Layer com Dependências

```bash
# Criar diretório para o layer
mkdir -p lambda-layer/python

# Instalar dependências no diretório
pip install web3 -t lambda-layer/python/

# Criar arquivo ZIP
cd lambda-layer
zip -r web3-layer.zip python/
cd ..

# Upload do layer para AWS
aws lambda publish-layer-version \
  --layer-name web3-dependencies \
  --description "Web3.py and dependencies" \
  --zip-file fileb://lambda-layer/web3-layer.zip \
  --compatible-runtimes python3.9 python3.10 python3.11

# Anotar o LayerVersionArn retornado
```

## Passo 2: Preparar Código da Lambda

```bash
# Criar arquivo ZIP com o código
zip lambda_function.zip lambda_function.py

# Ou se tiver outros arquivos:
# zip -r lambda_function.zip lambda_function.py utils.py config.py
```

## Passo 3: Criar Lambda Function

```bash
# Obter ARN do role (criado no README_AWS_ARCHITECTURE.md)
ROLE_ARN=$(aws iam get-role --role-name BesuLambdaExecutionRole --query 'Role.Arn' --output text)

# Obter ARN do layer
LAYER_ARN=$(aws lambda list-layer-versions \
  --layer-name web3-dependencies \
  --query 'LayerVersions[0].LayerVersionArn' \
  --output text)

# Criar função Lambda
aws lambda create-function \
  --function-name E1PoloCalculator \
  --runtime python3.11 \
  --role $ROLE_ARN \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://lambda_function.zip \
  --timeout 300 \
  --memory-size 512 \
  --layers $LAYER_ARN \
  --environment Variables='{
    "LOG_LEVEL":"INFO"
  }'
```

## Passo 4: Atualizar ABI do Contrato

Após compilar o contrato Solidity, você precisa atualizar o `CONTRACT_ABI` no `lambda_function.py`:

```bash
# 1. Compilar contrato e obter ABI
# (veja instruções em ../deploy_contract.py)

# 2. Atualizar lambda_function.py com o ABI completo

# 3. Recriar ZIP
zip lambda_function.zip lambda_function.py

# 4. Atualizar código da Lambda
aws lambda update-function-code \
  --function-name E1PoloCalculator \
  --zip-file fileb://lambda_function.zip
```

## Passo 5: Testar Lambda

### Teste Direto (sem API Gateway)

```bash
# Criar arquivo de teste
cat > test_event.json << 'EOF'
{
  "distance_highway": 32.19,
  "distance_city": 22.28,
  "city_gasoline": 13.5,
  "road_gasoline": 15.7,
  "city_ethanol": 9.3,
  "road_ethanol": 10.9,
  "carbon_price_european": 89.08,
  "euro_price": 6.1708
}
EOF

# Invocar Lambda
aws lambda invoke \
  --function-name E1PoloCalculator \
  --payload file://test_event.json \
  --cli-binary-format raw-in-base64-out \
  response.json

# Ver resultado
cat response.json | jq .
```

### Teste via API Gateway

```bash
# Obter URL do API Gateway
API_URL="https://YOUR-API-ID.execute-api.REGION.amazonaws.com/prod/calculate-e1"

# Fazer requisição
curl -X POST $API_URL \
  -H "Content-Type: application/json" \
  -d '{
    "distance_highway": 32.19,
    "distance_city": 22.28,
    "city_gasoline": 13.5,
    "road_gasoline": 15.7,
    "city_ethanol": 9.3,
    "road_ethanol": 10.9,
    "carbon_price_european": 89.08,
    "euro_price": 6.1708
  }'
```

## Passo 6: Configurar Monitoring

```bash
# Criar CloudWatch Alarm para erros
aws cloudwatch put-metric-alarm \
  --alarm-name E1PoloCalculator-Errors \
  --alarm-description "Alert on Lambda errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=FunctionName,Value=E1PoloCalculator

# Criar alarm para duração
aws cloudwatch put-metric-alarm \
  --alarm-name E1PoloCalculator-Duration \
  --alarm-description "Alert on long execution times" \
  --metric-name Duration \
  --namespace AWS/Lambda \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 60000 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=FunctionName,Value=E1PoloCalculator
```

## Atualização da Lambda

Para atualizar o código:

```bash
# Atualizar apenas o código
zip lambda_function.zip lambda_function.py
aws lambda update-function-code \
  --function-name E1PoloCalculator \
  --zip-file fileb://lambda_function.zip

# Atualizar configuração (timeout, memória, etc)
aws lambda update-function-configuration \
  --function-name E1PoloCalculator \
  --timeout 300 \
  --memory-size 1024

# Atualizar variáveis de ambiente
aws lambda update-function-configuration \
  --function-name E1PoloCalculator \
  --environment Variables='{
    "LOG_LEVEL":"DEBUG",
    "CUSTOM_VAR":"value"
  }'
```

## Logs e Debugging

```bash
# Ver logs recentes
aws logs tail /aws/lambda/E1PoloCalculator --follow

# Ver logs de um período específico
aws logs filter-log-events \
  --log-group-name /aws/lambda/E1PoloCalculator \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --filter-pattern "ERROR"

# Ver métricas
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=E1PoloCalculator \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

## Troubleshooting

### Erro: "Unable to import module 'lambda_function'"

```bash
# Verificar se o arquivo está no root do ZIP
unzip -l lambda_function.zip

# Deve mostrar:
# lambda_function.py (no root)
```

### Erro: "No module named 'web3'"

```bash
# Verificar se o layer está anexado
aws lambda get-function --function-name E1PoloCalculator

# Recriar e anexar layer
```

### Timeout

```bash
# Aumentar timeout
aws lambda update-function-configuration \
  --function-name E1PoloCalculator \
  --timeout 900  # máximo: 15 minutos
```

### Erro de Memória

```bash
# Aumentar memória
aws lambda update-function-configuration \
  --function-name E1PoloCalculator \
  --memory-size 1024  # ou 2048, 3008
```

## Limpeza (Delete)

```bash
# Deletar função
aws lambda delete-function --function-name E1PoloCalculator

# Deletar layer
aws lambda delete-layer-version \
  --layer-name web3-dependencies \
  --version-number 1

# Deletar role
aws iam delete-role-policy \
  --role-name BesuLambdaExecutionRole \
  --policy-name BesuLambdaPolicy

aws iam delete-role --role-name BesuLambdaExecutionRole
```
