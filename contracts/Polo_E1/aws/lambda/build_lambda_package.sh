#!/bin/bash

# Script para criar pacote Lambda com todas as dependências

echo "=== Criando pacote Lambda com Web3.py ==="

# Criar diretório temporário
rm -rf lambda_package
mkdir -p lambda_package

# Instalar dependências usando Docker para garantir compatibilidade com Lambda
docker run --rm \
  -v "$PWD":/var/task \
  public.ecr.aws/sam/build-python3.11 \
  bash -c "pip install web3 eth-account eth-hash[pycryptodome] -t /var/task/lambda_package/ && chown -R $(id -u):$(id -g) /var/task/lambda_package"

# Copiar lambda_function.py
cp lambda_function.py lambda_package/

# Criar arquivo .zip
cd lambda_package
zip -r ../lambda_deployment.zip . -x "*.pyc" "*__pycache__*"
cd ..

# Informações
echo ""
echo "=== Pacote criado: lambda_deployment.zip ==="
ls -lh lambda_deployment.zip
echo ""
echo "Agora faça upload deste arquivo no console Lambda:"
echo "1. Vá para a função Lambda no console AWS"
echo "2. Clique em 'Upload from' > '.zip file'"
echo "3. Selecione lambda_deployment.zip"
echo "4. Clique 'Save'"
