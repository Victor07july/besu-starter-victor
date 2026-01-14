# E1 Polo - Cálculo de Créditos de Carbono na Blockchain

Este projeto calcula créditos de carbono E1 baseado em dados de consumo de combustível e registra os resultados na blockchain Besu.

## Arquivos

- **contract/e1_polo.sol**: Contrato Solidity com a lógica de cálculo
- **E1PoloTeste_sumo.py**: Script Python original de análise
- **deploy_contract.py**: Script para fazer deploy do contrato
- **send_to_blockchain.py**: Script para enviar dados do CSV para a blockchain
- **vehicle_data_1.csv**: Dados de entrada

## Instalação

```bash
# Criar ambiente virtual (opcional)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r requirements.txt
```

## Uso

### 1. Fazer Deploy do Contrato

Primeiro, edite `deploy_contract.py` e configure:
- `RPC_URL`: URL do seu nó Besu
- `SENDER_ADDRESS`: Endereço da sua conta
- `PRIVATE_KEY`: Chave privada da sua conta

Depois execute:

```bash
python deploy_contract.py
```

Anote o endereço do contrato que será exibido.

### 2. Enviar Dados para a Blockchain

Edite `send_to_blockchain.py` e configure:
- `CONTRACT_ADDRESS`: Endereço do contrato (do passo anterior)
- `CONTRACT_ABI`: ABI do contrato (copie de deployment_info.json)
- `SENDER_ADDRESS`: Endereço da sua conta
- `PRIVATE_KEY`: Chave privada da sua conta

Execute:

```bash
python send_to_blockchain.py
```

O script irá:
1. Ler os dados do CSV
2. Para cada linha, enviar uma transação para o contrato
3. Calcular o valor E1
4. Salvar os resultados em `blockchain_results.csv`

## Estrutura de Dados

### VehicleData (Contrato)

- `distanceHighway`: Distância em rodovia (km)
- `distanceCity`: Distância em cidade (km)
- `cityGasoline`: Consumo de gasolina em cidade (km/L × 1000)
- `roadGasoline`: Consumo de gasolina em rodovia (km/L × 1000)
- `cityEthanol`: Consumo de etanol em cidade (km/L × 1000)
- `roadEthanol`: Consumo de etanol em rodovia (km/L × 1000)
- `carbonPriceEuropean`: Preço do carbono europeu (EUR × 100)
- `euroPrice`: Preço do Euro em Reais (BRL × 10000)

### Retorno

- `metaCO2`: Meta de emissão em gramas de CO2
- `diff`: Diferença entre meta e emissão real em gramas
- `e1Value`: Valor do crédito E1 em reais (com 6 casas decimais)

## Fórmulas

### Emissões Parte 1 (Rodovia)

```
parte1 = distance_highway × (
    (1 / road_gasoline) × EMISSAO_GASOLINA +
    (1 / road_ethanol) × EMISSAO_ETANOL
) × 1000
```

### Emissões Parte 2 (Cidade)

```
parte2 = distance_city × (
    (1 / city_gasoline) × EMISSAO_GASOLINA +
    (1 / city_ethanol) × EMISSAO_ETANOL
) × 1000
```

### Meta e Valor E1

```
Meta_CO2 = parte1 + parte2
Diff = Meta_CO2 / 2
Real_price = Carbon_Price_European × Euro_price
E1 = Diff × Real_price / 1_000_000
```

## Constantes

- `EMISSAO_GASOLINA`: 1.720 kg CO2/L
- `EMISSAO_ETANOL`: 1.510 kg CO2/L

## Eventos

O contrato emite eventos `E1Calculated` com:
- `vehicle`: Endereço que enviou a transação
- `metaCO2`: Meta de emissão calculada
- `diff`: Diferença calculada
- `e1Value`: Valor do crédito E1
- `timestamp`: Timestamp do bloco
