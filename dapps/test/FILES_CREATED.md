# 📦 Arquivos Criados - Teste Simple Counter

## 📁 Estrutura Completa

```
dapps/
├── QUICKSTART.md                  # ⚡ Início rápido
├── README.md                      # 📖 Documentação completa
├── run_test.sh                    # 🚀 Script automático
├── prepare_test.py                # 📋 Prepara arquivos
├── deploy_simple_counter.py       # 📦 Deploy do contrato
├── .gitignore                     # 🚫 Arquivos ignorados
│
├── contracts/
│   └── SimpleCounter.sol          # 📄 Contrato simplificado
│
└── test_simple/
    ├── go.mod                     # 📦 Dependências Go
    └── send_simple.go             # 💻 Código de teste

# Gerados após execução:
├── simple_counter_deployment.json # 📍 Endereço do contrato
├── wallets_64_groups.json         # 💼 Carteiras (copiado)
├── dados_gas.csv                  # 📊 Dados CSV (copiado)
└── test_simple/
    ├── test_simple                # 🔨 Binário compilado
    └── results/
        ├── simple_results_Xworkers.csv    # 📈 Resultados detalhados
        └── simple_stats_Xworkers.csv      # 📊 Estatísticas agregadas
```

## 🎯 Propósito de Cada Arquivo

### 📘 Documentação
- **QUICKSTART.md**: Início rápido (3 passos)
- **README.md**: Documentação completa com detalhes técnicos

### 🔧 Scripts de Automação
- **run_test.sh**: Executa tudo automaticamente
- **prepare_test.py**: Copia wallets e CSV necessários
- **deploy_simple_counter.py**: Compila e faz deploy do contrato

### 💻 Código
- **contracts/SimpleCounter.sol**: Contrato minimalista (só contador)
- **test_simple/send_simple.go**: Código de teste adaptado

### 📦 Configuração
- **test_simple/go.mod**: Dependências do Go
- **.gitignore**: Arquivos a ignorar no git

## 🚀 Como Usar

### Opção 1: Automático (Recomendado)
```bash
cd /home/inmetro/besu-starter-victor/dapps
chmod +x run_test.sh
./run_test.sh
```

### Opção 2: Manual
```bash
cd /home/inmetro/besu-starter-victor/dapps

# 1. Preparar
python3 prepare_test.py

# 2. Deploy
python3 deploy_simple_counter.py

# 3. Compilar
cd test_simple
go mod tidy
go build -o test_simple send_simple.go

# 4. Executar
./test_simple
```

## 📊 Arquivos de Saída

Após executar o teste, serão gerados:

1. **simple_counter_deployment.json**
   - Endereço do contrato deployado
   - ABI do contrato
   - Gas usado no deploy

2. **test_simple/results/simple_results_Xworkers.csv**
   ```csv
   linha,worker_id,wallet_addr,tx_hash,block,gas_used,latency_ms,error
   1,1,0x...,0x...,1234567,45000,29842.15,
   ```

3. **test_simple/results/simple_stats_Xworkers.csv**
   ```csv
   worker_id,total_txs,successful_txs,failed_txs,duration_s,avg_latency_ms,min_latency_ms,max_latency_ms,throughput_tx_s
   1,100,100,0,3012.45,30124.50,24532.12,31245.78,0.03
   ```

## 🔄 Comparação com Teste Original

### Teste Original (CarbonCreditNFT)
- **Código:** `multithread/send/send_multithread.go`
- **Contrato:** CarbonCreditNFT_E1 (cálculos complexos)
- **Resultados:** `multithread/send/results/`

### Teste Novo (SimpleCounter)
- **Código:** `test_simple/send_simple.go`
- **Contrato:** SimpleCounter (apenas contador)
- **Resultados:** `test_simple/results/`

### Métricas para Comparar
1. **Latência Média**: Original ≈ 30s vs Novo = ?
2. **Throughput**: Original = 2.134 tx/s (64 workers) vs Novo = ?
3. **Taxa de Sucesso**: Original = 99.998% vs Novo = ?

## 📝 Checklist de Execução

- [ ] Arquivos copiados (`prepare_test.py`)
- [ ] Contrato deployado (`deploy_simple_counter.py`)
- [ ] Código compilado (`go build`)
- [ ] Teste executado (`./test_simple`)
- [ ] Resultados analisados (compare CSVs)
- [ ] Relatório para o chefe preparado

## 🎓 Para o Chefe

**Resumo para relatório:**

"Para isolar o impacto do algoritmo na latência, criei um contrato simplificado (SimpleCounter) que apenas incrementa um contador sequencial, sem executar cálculos de monetização.

**Setup:**
- Mesmo ambiente AWS
- Mesmas carteiras
- Mesmo conjunto de dados CSV
- Mesmo número de workers para comparação

**Resultado:**
- Latência Original: ~30s
- Latência SimpleCounter: [PREENCHER APÓS TESTE]
- Diferença: [CALCULAR]%

**Conclusão:**
[Se similar: Blockchain é o gargalo, não o algoritmo]
[Se muito menor: Algoritmo precisa otimização]"

---

**Total de Arquivos Criados:** 10  
**Linhas de Código:** ~1000+ (Go + Solidity + Python)  
**Tempo de Implementação:** 1 sessão  
**Status:** ✅ Pronto para uso
