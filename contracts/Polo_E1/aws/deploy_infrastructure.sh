#!/bin/bash

###############################################################################
# Script de Deploy Completo da Infraestrutura AWS
# E1 Polo Calculator Blockchain
###############################################################################

set -e  # Exit on error

echo "=========================================="
echo "E1 POLO CALCULATOR - AWS INFRASTRUCTURE"
echo "=========================================="
echo ""

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Função para mensagens
info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Verificar AWS CLI
if ! command -v aws &> /dev/null; then
    error "AWS CLI não encontrado. Instale: https://aws.amazon.com/cli/"
fi

# Verificar configuração AWS
if ! aws sts get-caller-identity &> /dev/null; then
    error "AWS CLI não configurado. Execute: aws configure"
fi

info "Conta AWS: $(aws sts get-caller-identity --query Account --output text)"
info "Região: $(aws configure get region)"
echo ""

# Variáveis configuráveis
read -p "Digite a região AWS (default: us-east-1): " AWS_REGION
AWS_REGION=${AWS_REGION:-us-east-1}

read -p "Digite o endereço público da EC2 do Besu: " EC2_IP
if [ -z "$EC2_IP" ]; then
    error "Endereço EC2 é obrigatório!"
fi

read -p "Digite o endereço da conta blockchain: " SENDER_ADDRESS
if [ -z "$SENDER_ADDRESS" ]; then
    error "Endereço da conta é obrigatório!"
fi

read -sp "Digite a chave privada da conta: " PRIVATE_KEY
echo ""
if [ -z "$PRIVATE_KEY" ]; then
    error "Chave privada é obrigatória!"
fi

# Configurar região
export AWS_DEFAULT_REGION=$AWS_REGION

echo ""
info "========== PASSO 1: Criando Secrets Manager =========="

# Criar secret para chaves blockchain
info "Criando secret: besu-blockchain-keys..."
aws secretsmanager create-secret \
    --name besu-blockchain-keys \
    --description "Private keys for Besu blockchain" \
    --secret-string "{
        \"SENDER_ADDRESS\": \"$SENDER_ADDRESS\",
        \"PRIVATE_KEY\": \"$PRIVATE_KEY\"
    }" 2>/dev/null || warn "Secret já existe, atualizando..."

aws secretsmanager update-secret \
    --secret-id besu-blockchain-keys \
    --secret-string "{
        \"SENDER_ADDRESS\": \"$SENDER_ADDRESS\",
        \"PRIVATE_KEY\": \"$PRIVATE_KEY\"
    }" 2>/dev/null

info "✓ Secret besu-blockchain-keys criado/atualizado"

# Criar secret para configuração do contrato
info "Criando secret: besu-contract-config..."
aws secretsmanager create-secret \
    --name besu-contract-config \
    --description "Smart contract addresses" \
    --secret-string "{
        \"CONTRACT_ADDRESS\": \"0x0000000000000000000000000000000000000000\",
        \"RPC_URL\": \"http://$EC2_IP:8545\"
    }" 2>/dev/null || warn "Secret já existe, atualizando..."

aws secretsmanager update-secret \
    --secret-id besu-contract-config \
    --secret-string "{
        \"CONTRACT_ADDRESS\": \"0x0000000000000000000000000000000000000000\",
        \"RPC_URL\": \"http://$EC2_IP:8545\"
    }" 2>/dev/null

info "✓ Secret besu-contract-config criado/atualizado"

echo ""
info "========== PASSO 2: Criando IAM Role para Lambda =========="

# Criar trust policy
cat > /tmp/lambda-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "lambda.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF

# Criar role
info "Criando role: BesuLambdaExecutionRole..."
aws iam create-role \
    --role-name BesuLambdaExecutionRole \
    --assume-role-policy-document file:///tmp/lambda-trust-policy.json \
    2>/dev/null || warn "Role já existe"

# Criar policy
cat > /tmp/lambda-policy.json << 'EOF'
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

info "Anexando política à role..."
aws iam put-role-policy \
    --role-name BesuLambdaExecutionRole \
    --policy-name BesuLambdaPolicy \
    --policy-document file:///tmp/lambda-policy.json

info "✓ IAM Role configurado"

# Aguardar role ser propagado
info "Aguardando propagação do IAM (10s)..."
sleep 10

echo ""
info "========== PASSO 3: Criando Lambda Layer =========="

# Criar layer com dependências
info "Criando layer com Web3.py..."
LAYER_DIR="/tmp/lambda-layer"
mkdir -p $LAYER_DIR/python

pip install web3 -t $LAYER_DIR/python/ -q

cd $LAYER_DIR
zip -r web3-layer.zip python/ > /dev/null
cd - > /dev/null

LAYER_ARN=$(aws lambda publish-layer-version \
    --layer-name web3-dependencies \
    --description "Web3.py and dependencies" \
    --zip-file fileb://$LAYER_DIR/web3-layer.zip \
    --compatible-runtimes python3.11 \
    --query 'LayerVersionArn' \
    --output text)

info "✓ Layer criado: $LAYER_ARN"

echo ""
info "========== PASSO 4: Criando Lambda Function =========="

# Criar ZIP com código da Lambda
info "Preparando código da Lambda..."
cd lambda
zip lambda_function.zip lambda_function.py > /dev/null
cd ..

# Obter ARN do role
ROLE_ARN=$(aws iam get-role --role-name BesuLambdaExecutionRole --query 'Role.Arn' --output text)

info "Criando função Lambda: E1PoloCalculator..."
aws lambda create-function \
    --function-name E1PoloCalculator \
    --runtime python3.11 \
    --role $ROLE_ARN \
    --handler lambda_function.lambda_handler \
    --zip-file fileb://lambda/lambda_function.zip \
    --timeout 300 \
    --memory-size 512 \
    --layers $LAYER_ARN \
    --environment Variables='{
        "LOG_LEVEL":"INFO"
    }' \
    2>/dev/null || {
        warn "Lambda já existe, atualizando..."
        aws lambda update-function-code \
            --function-name E1PoloCalculator \
            --zip-file fileb://lambda/lambda_function.zip > /dev/null
    }

info "✓ Lambda Function criada/atualizada"

echo ""
info "========== PASSO 5: Criando API Gateway =========="

# Criar API REST
info "Criando API Gateway..."
API_ID=$(aws apigateway create-rest-api \
    --name "E1PoloBlockchainAPI" \
    --description "API for E1 Polo blockchain interactions" \
    --query 'id' \
    --output text 2>/dev/null || {
        # Se já existe, pegar o ID
        aws apigateway get-rest-apis \
            --query "items[?name=='E1PoloBlockchainAPI'].id" \
            --output text | head -n1
    })

info "API ID: $API_ID"

# Obter root resource ID
ROOT_ID=$(aws apigateway get-resources \
    --rest-api-id $API_ID \
    --query 'items[?path==`/`].id' \
    --output text)

# Criar resource /calculate-e1
info "Criando resource /calculate-e1..."
RESOURCE_ID=$(aws apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $ROOT_ID \
    --path-part "calculate-e1" \
    --query 'id' \
    --output text 2>/dev/null || {
        aws apigateway get-resources \
            --rest-api-id $API_ID \
            --query "items[?pathPart=='calculate-e1'].id" \
            --output text
    })

# Criar método POST
info "Criando método POST..."
aws apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $RESOURCE_ID \
    --http-method POST \
    --authorization-type "NONE" 2>/dev/null || warn "Método já existe"

# Integração com Lambda
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
LAMBDA_ARN="arn:aws:lambda:$AWS_REGION:$ACCOUNT_ID:function:E1PoloCalculator"

info "Configurando integração com Lambda..."
aws apigateway put-integration \
    --rest-api-id $API_ID \
    --resource-id $RESOURCE_ID \
    --http-method POST \
    --type AWS_PROXY \
    --integration-http-method POST \
    --uri "arn:aws:apigateway:$AWS_REGION:lambda:path/2015-03-31/functions/$LAMBDA_ARN/invocations" 2>/dev/null || warn "Integração já existe"

# Dar permissão ao API Gateway para invocar Lambda
info "Configurando permissões..."
aws lambda add-permission \
    --function-name E1PoloCalculator \
    --statement-id apigateway-invoke \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:$AWS_REGION:$ACCOUNT_ID:$API_ID/*/*" \
    2>/dev/null || warn "Permissão já existe"

# Deploy da API
info "Fazendo deploy da API..."
aws apigateway create-deployment \
    --rest-api-id $API_ID \
    --stage-name prod > /dev/null

info "✓ API Gateway configurado"

echo ""
echo "=========================================="
echo "          DEPLOY CONCLUÍDO!"
echo "=========================================="
echo ""
echo -e "${GREEN}URLs e Informações:${NC}"
echo ""
echo "API Gateway URL:"
echo "  https://$API_ID.execute-api.$AWS_REGION.amazonaws.com/prod/calculate-e1"
echo ""
echo "Lambda Function:"
echo "  Nome: E1PoloCalculator"
echo "  ARN: $LAMBDA_ARN"
echo ""
echo "Secrets Manager:"
echo "  - besu-blockchain-keys"
echo "  - besu-contract-config"
echo ""
echo -e "${YELLOW}PRÓXIMOS PASSOS:${NC}"
echo ""
echo "1. Faça deploy do contrato Solidity na blockchain EC2"
echo ""
echo "2. Atualize o endereço do contrato no Secrets Manager:"
echo "   aws secretsmanager update-secret \\"
echo "     --secret-id besu-contract-config \\"
echo "     --secret-string '{\"CONTRACT_ADDRESS\":\"0xSEU_CONTRATO\",\"RPC_URL\":\"http://$EC2_IP:8545\"}'"
echo ""
echo "3. Configure send_to_lambda.py com a URL da API:"
echo "   API_GATEWAY_URL = \"https://$API_ID.execute-api.$AWS_REGION.amazonaws.com/prod/calculate-e1\""
echo ""
echo "4. Execute o script para enviar dados:"
echo "   python aws/send_to_lambda.py"
echo ""
echo "5. Monitore os logs:"
echo "   aws logs tail /aws/lambda/E1PoloCalculator --follow"
echo ""
echo "=========================================="
