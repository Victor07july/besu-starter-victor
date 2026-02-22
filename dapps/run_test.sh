#!/bin/bash

# Script de execução completa do teste Simple Counter

echo "======================================================================"
echo "TESTE DE PERFORMANCE - SIMPLE COUNTER"
echo "======================================================================"
echo ""

cd "$(dirname "$0")"

# Passo 1: Preparar arquivos
echo "📋 Passo 1: Preparando arquivos necessários..."
python3 prepare_test.py
if [ $? -ne 0 ]; then
    echo "❌ Erro ao preparar arquivos"
    exit 1
fi
echo ""

# Passo 2: Deploy do contrato
echo "📦 Passo 2: Fazendo deploy do Simple Counter..."
python3 deploy_simple_counter.py
if [ $? -ne 0 ]; then
    echo "❌ Erro ao fazer deploy"
    exit 1
fi
echo ""

# Passo 3: Compilar Go
echo "🔨 Passo 3: Compilando código Go..."
cd test_simple
go mod tidy
go build -o test_simple send_simple.go
if [ $? -ne 0 ]; then
    echo "❌ Erro ao compilar"
    exit 1
fi
echo ""

# Passo 4: Executar teste
echo "🚀 Passo 4: Executando teste de performance..."
echo "⚠️  Isso pode levar algum tempo..."
echo ""
./test_simple

echo ""
echo "======================================================================"
echo "✅ TESTE CONCLUÍDO!"
echo "======================================================================"
echo ""
echo "📊 Resultados salvos em: test_simple/results/"
echo ""
echo "Para comparar com o teste original:"
echo "  - Verifique a latência média"
echo "  - Compare o throughput"
echo "  - Analise os CSVs gerados"
echo ""
