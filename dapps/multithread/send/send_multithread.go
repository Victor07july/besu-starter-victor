package main

import (
	"context"
	"crypto/ecdsa"
	"crypto/tls"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"math/big"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/ethereum/go-ethereum"
	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/crypto"
	"github.com/ethereum/go-ethereum/ethclient"
	"github.com/ethereum/go-ethereum/rpc"
)

// ======================================================================
// CONFIGURAÇÕES DA BLOCKCHAIN
// ======================================================================

const (
	// URL do nó RPC (rpcnode-user, sem autenticação)
	RPCURL = "https://ec2-18-218-85-118.us-east-2.compute.amazonaws.com/user/"

	// Arquivo JSON com dados do deploy (ABI e endereço do contrato)
	DeploymentJSON = "deployment_result.json"

	// Arquivo JSON com as carteiras
	WalletsJSON = "wallets_64_groups.json"

	// Número de workers/carteiras em paralelo
	NumWorkers = 8

	// Número máximo de linhas a serem lidas do CSV (0 = sem limite)
	MaxRowsToRead = 1000

	// Timeout para aguardar confirmação de transações
	TxTimeout = 120 * time.Second
)

// ======================================================================
// ESTRUTURAS DE DADOS
// ======================================================================

// Wallet representa uma carteira com endereço e chave privada
type Wallet struct {
	Address    string `json:"address"`
	PrivateKey string `json:"private_key"`
}

// VehicleData representa os dados de um veículo no formato do contrato
type VehicleData struct {
	DistanceHighway     *big.Int
	DistanceCity        *big.Int
	CityGasoline        *big.Int
	RoadGasoline        *big.Int
	CityEthanol         *big.Int
	RoadEthanol         *big.Int
	CarbonPriceEuropean *big.Int
	EuroPrice           *big.Int
}

// DeploymentData armazena informações do deployment
type DeploymentData struct {
	ContractAddress string          `json:"contract_address"`
	ABI             json.RawMessage `json:"abi"`
	GasUsed         uint64          `json:"gas_used"`
}

// CSVRow representa uma linha do CSV
type CSVRow struct {
	DistanceHighway     float64
	DistanceCity        float64
	CityGasoline        float64
	RoadGasoline        float64
	CityEthanol         float64
	RoadEthanol         float64
	CarbonPriceEuropean float64
	EuroPrice           float64
}

// Job representa um trabalho a ser processado
type Job struct {
	Index int
	Row   CSVRow
}

// Result armazena o resultado de uma transação
type Result struct {
	Linha      int
	WorkerID   int
	WalletAddr string
	TxHash     string
	Block      uint64
	GasUsed    uint64
	MetaCO2    *big.Int
	Diff       *big.Int
	E1Value    float64
	Error      error

	// Métricas de tempo
	StartTime     time.Time
	TxSentTime    time.Time
	ConfirmedTime time.Time
	Latency       time.Duration // Tempo total (start até confirmação)
	TxLatency     time.Duration // Tempo de envio até confirmação
}

// WorkerStats armazena estatísticas de um worker
type WorkerStats struct {
	WorkerID      int
	TotalTxs      int
	SuccessfulTxs int
	FailedTxs     int
	TotalLatency  time.Duration
	AvgLatency    time.Duration
	MinLatency    time.Duration
	MaxLatency    time.Duration
	StartTime     time.Time
	EndTime       time.Time
	Duration      time.Duration
}

// ======================================================================
// FUNÇÕES AUXILIARES
// ======================================================================

// prepareVehicleData converte uma linha CSV para VehicleData
func prepareVehicleData(row CSVRow) VehicleData {
	// Valores padrão se não fornecidos
	if row.CityGasoline == 0 {
		row.CityGasoline = 13.5
	}
	if row.RoadGasoline == 0 {
		row.RoadGasoline = 15.7
	}
	if row.CityEthanol == 0 {
		row.CityEthanol = 9.3
	}
	if row.RoadEthanol == 0 {
		row.RoadEthanol = 10.9
	}
	if row.CarbonPriceEuropean == 0 {
		row.CarbonPriceEuropean = 89.08
	}
	if row.EuroPrice == 0 {
		row.EuroPrice = 6.1708
	}

	return VehicleData{
		DistanceHighway:     big.NewInt(int64(row.DistanceHighway)),
		DistanceCity:        big.NewInt(int64(row.DistanceCity)),
		CityGasoline:        big.NewInt(int64(row.CityGasoline * 1000)),
		RoadGasoline:        big.NewInt(int64(row.RoadGasoline * 1000)),
		CityEthanol:         big.NewInt(int64(row.CityEthanol * 1000)),
		RoadEthanol:         big.NewInt(int64(row.RoadEthanol * 1000)),
		CarbonPriceEuropean: big.NewInt(int64(row.CarbonPriceEuropean * 100)),
		EuroPrice:           big.NewInt(int64(row.EuroPrice * 10000)),
	}
}

// loadDeploymentData carrega os dados do deployment do JSON
func loadDeploymentData() (*DeploymentData, error) {
	dir, err := os.Getwd()
	if err != nil {
		return nil, err
	}

	filePath := filepath.Join(dir, DeploymentJSON)
	data, err := os.ReadFile(filePath)
	if err != nil {
		return nil, fmt.Errorf("arquivo não encontrado: %s\nExecute o deploy primeiro", filePath)
	}

	var deployment DeploymentData
	if err := json.Unmarshal(data, &deployment); err != nil {
		return nil, err
	}

	return &deployment, nil
}

// loadWallets carrega as carteiras do arquivo JSON
func loadWallets(numWallets int) ([]Wallet, error) {
	dir, err := os.Getwd()
	if err != nil {
		return nil, err
	}

	filePath := filepath.Join(dir, WalletsJSON)
	data, err := os.ReadFile(filePath)
	if err != nil {
		return nil, fmt.Errorf("arquivo não encontrado: %s", filePath)
	}

	var walletsMap map[string]Wallet
	if err := json.Unmarshal(data, &walletsMap); err != nil {
		return nil, err
	}

	// Converter mapa em slice e pegar apenas numWallets
	var wallets []Wallet
	for i := 1; i <= numWallets && i <= len(walletsMap); i++ {
		key := fmt.Sprintf("vehicle_group_%d", i)
		if wallet, ok := walletsMap[key]; ok {
			wallets = append(wallets, wallet)
		}
	}

	if len(wallets) < numWallets {
		return nil, fmt.Errorf("apenas %d carteiras disponíveis, mas %d foram solicitadas", len(wallets), numWallets)
	}

	return wallets, nil
}

// readCSV lê o arquivo CSV e retorna os dados
func readCSV(filename string) ([]CSVRow, error) {
	file, err := os.Open(filename)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	reader := csv.NewReader(file)

	// Ler cabeçalho
	header, err := reader.Read()
	if err != nil {
		return nil, err
	}

	// Criar mapa de colunas
	colMap := make(map[string]int)
	for i, col := range header {
		colMap[col] = i
	}

	var rows []CSVRow
	for {
		record, err := reader.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, err
		}

		row := CSVRow{}

		if idx, ok := colMap["distance_highway"]; ok {
			row.DistanceHighway, _ = strconv.ParseFloat(record[idx], 64)
		}
		if idx, ok := colMap["distance_city"]; ok {
			row.DistanceCity, _ = strconv.ParseFloat(record[idx], 64)
		}
		if idx, ok := colMap["city_gasoline"]; ok {
			row.CityGasoline, _ = strconv.ParseFloat(record[idx], 64)
		}
		if idx, ok := colMap["road_gasoline"]; ok {
			row.RoadGasoline, _ = strconv.ParseFloat(record[idx], 64)
		}
		if idx, ok := colMap["city_ethanol"]; ok {
			row.CityEthanol, _ = strconv.ParseFloat(record[idx], 64)
		}
		if idx, ok := colMap["road_ethanol"]; ok {
			row.RoadEthanol, _ = strconv.ParseFloat(record[idx], 64)
		}
		if idx, ok := colMap["Carbon_Price_European"]; ok {
			row.CarbonPriceEuropean, _ = strconv.ParseFloat(record[idx], 64)
		}
		if idx, ok := colMap["Euro_price"]; ok {
			row.EuroPrice, _ = strconv.ParseFloat(record[idx], 64)
		}

		rows = append(rows, row)
	}

	return rows, nil
}

// saveResults salva os resultados em um arquivo CSV
func saveResults(results []Result, filename string) error {
	file, err := os.Create(filename)
	if err != nil {
		return err
	}
	defer file.Close()

	writer := csv.NewWriter(file)
	defer writer.Flush()

	// Escrever cabeçalho
	header := []string{"linha", "worker_id", "wallet", "tx_hash", "block", "gas_used", "meta_co2", "diff", "e1_value", "latency_ms", "tx_latency_ms", "error"}
	if err := writer.Write(header); err != nil {
		return err
	}

	// Escrever dados
	for _, r := range results {
		errMsg := ""
		if r.Error != nil {
			errMsg = r.Error.Error()
		}

		metaCO2 := ""
		diff := ""
		if r.MetaCO2 != nil {
			metaCO2 = r.MetaCO2.String()
		}
		if r.Diff != nil {
			diff = r.Diff.String()
		}

		record := []string{
			strconv.Itoa(r.Linha),
			strconv.Itoa(r.WorkerID),
			r.WalletAddr,
			r.TxHash,
			strconv.FormatUint(r.Block, 10),
			strconv.FormatUint(r.GasUsed, 10),
			metaCO2,
			diff,
			fmt.Sprintf("%.6f", r.E1Value),
			fmt.Sprintf("%.2f", r.Latency.Seconds()*1000),
			fmt.Sprintf("%.2f", r.TxLatency.Seconds()*1000),
			errMsg,
		}
		if err := writer.Write(record); err != nil {
			return err
		}
	}

	return nil
}

// saveWorkerStats salva estatísticas dos workers
func saveWorkerStats(stats []WorkerStats, filename string) error {
	file, err := os.Create(filename)
	if err != nil {
		return err
	}
	defer file.Close()

	writer := csv.NewWriter(file)
	defer writer.Flush()

	// Escrever cabeçalho
	header := []string{"worker_id", "total_txs", "successful_txs", "failed_txs", "duration_s", "avg_latency_ms", "min_latency_ms", "max_latency_ms", "throughput_tx_s"}
	if err := writer.Write(header); err != nil {
		return err
	}

	// Escrever dados
	for _, s := range stats {
		throughput := 0.0
		if s.Duration.Seconds() > 0 {
			throughput = float64(s.SuccessfulTxs) / s.Duration.Seconds()
		}

		record := []string{
			strconv.Itoa(s.WorkerID),
			strconv.Itoa(s.TotalTxs),
			strconv.Itoa(s.SuccessfulTxs),
			strconv.Itoa(s.FailedTxs),
			fmt.Sprintf("%.2f", s.Duration.Seconds()),
			fmt.Sprintf("%.2f", s.AvgLatency.Seconds()*1000),
			fmt.Sprintf("%.2f", s.MinLatency.Seconds()*1000),
			fmt.Sprintf("%.2f", s.MaxLatency.Seconds()*1000),
			fmt.Sprintf("%.2f", throughput),
		}
		if err := writer.Write(record); err != nil {
			return err
		}
	}

	return nil
}

// waitForReceipt aguarda a confirmação de uma transação
func waitForReceipt(ctx context.Context, client *ethclient.Client, txHash common.Hash, timeout time.Duration) (*types.Receipt, error) {
	timeoutCtx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	ticker := time.NewTicker(1 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-timeoutCtx.Done():
			return nil, fmt.Errorf("timeout aguardando confirmação")
		case <-ticker.C:
			receipt, err := client.TransactionReceipt(ctx, txHash)
			if err == nil {
				return receipt, nil
			}
			if err != ethereum.NotFound {
				return nil, err
			}
		}
	}
}

// parseE1CalculatedEvent processa os logs para extrair o evento E1Calculated
func parseE1CalculatedEvent(contractABI abi.ABI, logs []*types.Log) (map[string]interface{}, error) {
	eventName := "E1Calculated"

	for _, vLog := range logs {
		event, err := contractABI.EventByID(vLog.Topics[0])
		if err != nil {
			continue
		}

		if event.Name == eventName {
			data := make(map[string]interface{})
			err := contractABI.UnpackIntoMap(data, eventName, vLog.Data)
			if err != nil {
				return nil, err
			}

			// Adicionar indexed topics
			for i, input := range event.Inputs {
				if input.Indexed && i+1 < len(vLog.Topics) {
					indexed, err := contractABI.Unpack(eventName, vLog.Topics[i+1].Bytes())
					if err == nil && len(indexed) > 0 {
						data[input.Name] = indexed[0]
					}
				}
			}

			return data, nil
		}
	}

	return nil, fmt.Errorf("evento não encontrado")
}

// ======================================================================
// WORKER
// ======================================================================

// dialWithInsecureTLS cria um cliente Ethereum com verificação TLS desabilitada
func dialWithInsecureTLS(url string) (*ethclient.Client, error) {
	httpClient := &http.Client{
		Transport: &http.Transport{
			TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
		},
	}

	rpcClient, err := rpc.DialHTTPWithClient(url, httpClient)
	if err != nil {
		return nil, err
	}

	return ethclient.NewClient(rpcClient), nil
}

// workerFullCSV processa TODAS as linhas do CSV (simula um dispositivo completo)
func workerFullCSV(
	workerID int,
	wallet Wallet,
	rows []CSVRow,
	results chan<- Result,
	wg *sync.WaitGroup,
	contractAddress common.Address,
	contractABI abi.ABI,
	chainID *big.Int,
	printMutex *sync.Mutex,
) {
	defer wg.Done()

	// Conectar à blockchain (cada worker tem sua própria conexão)
	client, err := dialWithInsecureTLS(RPCURL)
	if err != nil {
		log.Printf("❌ Worker %d: Erro ao conectar: %v\n", workerID, err)
		return
	}
	defer client.Close()

	// Carregar chave privada
	privateKeyStr := wallet.PrivateKey
	if strings.HasPrefix(privateKeyStr, "0x") {
		privateKeyStr = privateKeyStr[2:]
	}

	privateKey, err := crypto.HexToECDSA(privateKeyStr)
	if err != nil {
		log.Printf("❌ Worker %d: Erro ao carregar chave privada: %v\n", workerID, err)
		return
	}

	publicKey := privateKey.Public()
	publicKeyECDSA, ok := publicKey.(*ecdsa.PublicKey)
	if !ok {
		log.Printf("❌ Worker %d: Erro ao fazer cast da chave pública\n", workerID)
		return
	}

	fromAddress := crypto.PubkeyToAddress(*publicKeyECDSA)

	printMutex.Lock()
	fmt.Printf("🟢 Worker %d iniciado | Carteira: %s | Processará %d linhas\n", workerID, wallet.Address, len(rows))
	printMutex.Unlock()

	ctx := context.Background()
	workerStartTime := time.Now()

	// Processar TODAS as linhas
	for idx, row := range rows {
		job := Job{Index: idx, Row: row}
		startTime := time.Now() // Início da transação

		result := Result{
			Linha:      job.Index + 1,
			WorkerID:   workerID,
			WalletAddr: wallet.Address,
			StartTime:  startTime,
		}

		// Preparar dados
		vehicleData := prepareVehicleData(job.Row)

		// Obter nonce
		nonce, err := client.PendingNonceAt(ctx, fromAddress)
		if err != nil {
			result.Error = fmt.Errorf("erro ao obter nonce: %v", err)
			printMutex.Lock()
			fmt.Printf("[Worker %d] Linha %d - ❌ Erro ao obter nonce\n", workerID, job.Index+1)
			printMutex.Unlock()
			results <- result
			continue
		}

		// Obter gas price
		gasPrice, err := client.SuggestGasPrice(ctx)
		if err != nil {
			result.Error = fmt.Errorf("erro ao obter gas price: %v", err)
			printMutex.Lock()
			fmt.Printf("[Worker %d] Linha %d - ❌ Erro ao obter gas price\n", workerID, job.Index+1)
			printMutex.Unlock()
			results <- result
			continue
		}

		// Preparar dados da transação
		input, err := contractABI.Pack("calculateAndRecordE1", vehicleData)
		if err != nil {
			result.Error = fmt.Errorf("erro ao fazer pack dos dados: %v", err)
			printMutex.Lock()
			fmt.Printf("[Worker %d] Linha %d - ❌ Erro ao fazer pack\n", workerID, job.Index+1)
			printMutex.Unlock()
			results <- result
			continue
		}

		// Criar transação
		gasLimit := uint64(500000)
		tx := types.NewTransaction(nonce, contractAddress, big.NewInt(0), gasLimit, gasPrice, input)

		// Assinar transação
		signedTx, err := types.SignTx(tx, types.NewEIP155Signer(chainID), privateKey)
		if err != nil {
			result.Error = fmt.Errorf("erro ao assinar transação: %v", err)
			printMutex.Lock()
			fmt.Printf("[Worker %d] Linha %d - ❌ Erro ao assinar\n", workerID, job.Index+1)
			printMutex.Unlock()
			results <- result
			continue
		}

		// Enviar transação
		err = client.SendTransaction(ctx, signedTx)
		if err != nil {
			result.Error = fmt.Errorf("erro ao enviar transação: %v", err)
			result.Latency = time.Since(startTime)
			printMutex.Lock()
			fmt.Printf("[Worker %d] Linha %d - ❌ Erro ao enviar TX\n", workerID, job.Index+1)
			printMutex.Unlock()
			results <- result
			continue
		}

		result.TxHash = signedTx.Hash().Hex()
		result.TxSentTime = time.Now() // Marca quando TX foi enviada

		// Aguardar confirmação
		receipt, err := waitForReceipt(ctx, client, signedTx.Hash(), TxTimeout)
		if err != nil {
			result.Error = fmt.Errorf("erro ao aguardar confirmação: %v", err)
			result.Latency = time.Since(startTime)
			result.TxLatency = time.Since(result.TxSentTime)
			printMutex.Lock()
			fmt.Printf("[Worker %d] Linha %d - ❌ Timeout/erro na confirmação\n", workerID, job.Index+1)
			printMutex.Unlock()
			results <- result
			continue
		}

		result.ConfirmedTime = time.Now() // Marca confirmação
		result.Latency = time.Since(startTime)
		result.TxLatency = time.Since(result.TxSentTime)
		result.Block = receipt.BlockNumber.Uint64()
		result.GasUsed = receipt.GasUsed

		if receipt.Status == 1 {
			// Processar eventos
			event, err := parseE1CalculatedEvent(contractABI, receipt.Logs)
			if err == nil && event != nil {
				result.MetaCO2 = event["metaCO2"].(*big.Int)
				result.Diff = event["diff"].(*big.Int)

				e1ValueBigInt := event["e1Value"].(*big.Int)
				e1ValueFloat := new(big.Float).Quo(new(big.Float).SetInt(e1ValueBigInt), big.NewFloat(1000000))
				result.E1Value, _ = e1ValueFloat.Float64()

				// Print consolidado de sucesso
				printMutex.Lock()
				fmt.Printf("[Worker %d] Linha %3d ✅ Bloco %d | E1: %.6f BRL | Latência: %dms | TX: %s\n",
					workerID, job.Index+1, receipt.BlockNumber.Uint64(), result.E1Value,
					result.Latency.Milliseconds(), signedTx.Hash().Hex()[:10]+"...")
				printMutex.Unlock()
			} else {
				printMutex.Lock()
				fmt.Printf("[Worker %d] Linha %3d ✅ Bloco %d | Sem evento | Latência: %dms | TX: %s\n",
					workerID, job.Index+1, receipt.BlockNumber.Uint64(),
					result.Latency.Milliseconds(), signedTx.Hash().Hex()[:10]+"...")
				printMutex.Unlock()
			}
		} else {
			result.Error = fmt.Errorf("transação falhou")
			printMutex.Lock()
			fmt.Printf("[Worker %d] Linha %3d ❌ Transação falhou no bloco %d\n",
				workerID, job.Index+1, receipt.BlockNumber.Uint64())
			printMutex.Unlock()
		}

		results <- result
	}

	workerEndTime := time.Now()
	workerDuration := workerEndTime.Sub(workerStartTime)

	printMutex.Lock()
	fmt.Printf("🔴 Worker %d finalizado | %d transações | Duração: %s\n",
		workerID, len(rows), workerDuration.Round(time.Millisecond))
	printMutex.Unlock()
}

// ======================================================================
// FUNÇÃO PRINCIPAL
// ======================================================================

func main() {
	startTime := time.Now()

	fmt.Println(strings.Repeat("=", 70))
	fmt.Println("ENVIANDO DADOS PARA O CONTRATO E1PoloCalculator (MULTITHREAD)")
	fmt.Println(strings.Repeat("=", 70))
	fmt.Printf("Configuração: %d workers em paralelo\n", NumWorkers)

	// 0. Carregar dados do deployment
	fmt.Println("\n[0] Carregando dados do deployment...")
	deployment, err := loadDeploymentData()
	if err != nil {
		log.Fatalf("❌ Erro: %v", err)
	}

	if deployment.ContractAddress == "" {
		log.Fatal("❌ Erro: contract_address não encontrado no JSON")
	}

	fmt.Printf("✅ Deployment carregado:\n")
	fmt.Printf("   Contract: %s\n", deployment.ContractAddress)
	if deployment.GasUsed > 0 {
		fmt.Printf("   Gas usado no deploy: %d\n", deployment.GasUsed)
	}

	contractAddress := common.HexToAddress(deployment.ContractAddress)

	// Parse ABI
	contractABI, err := abi.JSON(strings.NewReader(string(deployment.ABI)))
	if err != nil {
		log.Fatalf("❌ Erro ao fazer parse da ABI: %v", err)
	}

	// 1. Carregar carteiras
	fmt.Printf("\n[1] Carregando %d carteiras...\n", NumWorkers)
	wallets, err := loadWallets(NumWorkers)
	if err != nil {
		log.Fatalf("❌ Erro ao carregar carteiras: %v", err)
	}

	fmt.Printf("✅ Carteiras carregadas:\n")
	for i, wallet := range wallets {
		fmt.Printf("   [%d] %s\n", i+1, wallet.Address)
	}

	// 2. Conectar à blockchain (apenas para verificar e obter chain ID)
	fmt.Println("\n[2] Conectando à blockchain...")
	client, err := dialWithInsecureTLS(RPCURL)
	if err != nil {
		log.Fatalf("❌ Erro: Não foi possível conectar à blockchain\n   Verifique se o nó está rodando em %s\n   Erro: %v", RPCURL, err)
	}

	ctx := context.Background()
	chainID, err := client.ChainID(ctx)
	if err != nil {
		log.Fatalf("❌ Erro ao obter Chain ID: %v", err)
	}

	blockNumber, err := client.BlockNumber(ctx)
	if err != nil {
		log.Fatalf("❌ Erro ao obter número do bloco: %v", err)
	}

	fmt.Printf("✅ Conectado! Chain ID: %s\n", chainID.String())
	fmt.Printf("   Último bloco: %d\n", blockNumber)

	client.Close()

	// 3. Ler dados do CSV
	fmt.Println("\n[3] Lendo dados do CSV...")

	dir, _ := os.Getwd()
	csvPath := filepath.Join(dir, "vehicle_data_1.csv")

	rows, err := readCSV(csvPath)
	if err != nil {
		log.Fatalf("❌ Erro ao ler CSV: %v", err)
	}

	// Limitar número de linhas se configurado
	if MaxRowsToRead > 0 && len(rows) > MaxRowsToRead {
		fmt.Printf("Limitando de %d para %d linhas conforme configuração\n", len(rows), MaxRowsToRead)
		rows = rows[:MaxRowsToRead]
	}

	fmt.Printf("✅ CSV carregado: %d linhas\n", len(rows))

	// 4. Iniciar processamento multithread
	fmt.Println("\n[4] Iniciando workers e enviando transações em paralelo...")
	fmt.Printf("📱 Simulando %d dispositivos enviando %d transações cada\n", NumWorkers, len(rows))
	fmt.Printf("📊 Total esperado: %d transações\n", NumWorkers*len(rows))
	fmt.Println(strings.Repeat("-", 70))

	// Criar canais (cada worker processa TODAS as linhas)
	totalTransactions := NumWorkers * len(rows)
	results := make(chan Result, totalTransactions)

	// WaitGroup para sincronização
	var wg sync.WaitGroup

	// Mutex para prints sincronizados
	var printMutex sync.Mutex

	// Iniciar workers (cada um processa todas as linhas)
	for i := 0; i < NumWorkers; i++ {
		wg.Add(1)
		go workerFullCSV(i+1, wallets[i], rows, results, &wg, contractAddress, contractABI, chainID, &printMutex)
	}

	// Aguardar conclusão dos workers
	go func() {
		wg.Wait()
		close(results)
	}()

	// Coletar resultados
	var allResults []Result
	successCount := 0
	errorCount := 0

	fmt.Println()
	for result := range results {
		allResults = append(allResults, result)
		if result.Error == nil {
			successCount++
		} else {
			errorCount++
		}

		// Progresso geral
		total := len(allResults)
		if total%100 == 0 {
			successRate := float64(successCount) / float64(total) * 100
			fmt.Printf("📊 Progresso: %d/%d | ✅ %d (%.1f%%) | ❌ %d\n",
				total, totalTransactions, successCount, successRate, errorCount)
		}
	}

	elapsed := time.Since(startTime)

	// Calcular estatísticas por worker
	workerStatsMap := make(map[int]*WorkerStats)
	for i := 1; i <= NumWorkers; i++ {
		workerStatsMap[i] = &WorkerStats{
			WorkerID:   i,
			MinLatency: time.Hour, // Valor alto inicial
			StartTime:  startTime,
		}
	}

	for _, r := range allResults {
		stats := workerStatsMap[r.WorkerID]
		stats.TotalTxs++

		if r.Error == nil {
			stats.SuccessfulTxs++
			stats.TotalLatency += r.Latency

			if r.Latency < stats.MinLatency {
				stats.MinLatency = r.Latency
			}
			if r.Latency > stats.MaxLatency {
				stats.MaxLatency = r.Latency
			}
		} else {
			stats.FailedTxs++
		}

		if r.ConfirmedTime.After(stats.EndTime) {
			stats.EndTime = r.ConfirmedTime
		}
	}

	// Calcular médias e durações
	var workerStatsList []WorkerStats
	for _, stats := range workerStatsMap {
		if stats.SuccessfulTxs > 0 {
			stats.AvgLatency = stats.TotalLatency / time.Duration(stats.SuccessfulTxs)
		}
		if stats.EndTime.IsZero() {
			stats.EndTime = time.Now()
		}
		stats.Duration = stats.EndTime.Sub(stats.StartTime)
		workerStatsList = append(workerStatsList, *stats)
	}

	// 5. Resumo final
	fmt.Println("\n" + strings.Repeat("=", 70))
	fmt.Println("RESUMO DA SIMULAÇÃO")
	fmt.Println(strings.Repeat("=", 70))
	fmt.Printf("Dispositivos simulados: %d\n", NumWorkers)
	fmt.Printf("Linhas por dispositivo: %d\n", len(rows))
	fmt.Printf("Total de transações: %d\n", len(allResults))
	fmt.Printf("\n✅ Sucessos: %d (%.2f%%)\n", successCount, float64(successCount)/float64(len(allResults))*100)
	fmt.Printf("❌ Erros: %d (%.2f%%)\n", errorCount, float64(errorCount)/float64(len(allResults))*100)
	fmt.Printf("⏱️  Tempo total: %s\n", elapsed.Round(time.Millisecond))

	if successCount > 0 {
		var totalGas uint64
		var totalE1Value float64
		var totalLatency time.Duration
		var minLatency = time.Hour
		var maxLatency time.Duration

		for _, r := range allResults {
			if r.Error == nil {
				totalGas += r.GasUsed
				totalE1Value += r.E1Value
				totalLatency += r.Latency

				if r.Latency < minLatency {
					minLatency = r.Latency
				}
				if r.Latency > maxLatency {
					maxLatency = r.Latency
				}
			}
		}

		avgGas := totalGas / uint64(successCount)
		avgE1Value := totalE1Value / float64(successCount)
		avgLatency := totalLatency / time.Duration(successCount)
		throughput := float64(successCount) / elapsed.Seconds()
		avgPerDevice := float64(successCount) / float64(NumWorkers)

		// Workload
		workload := len(rows) * NumWorkers

		fmt.Printf("\n📊 Estatísticas:\n")
		fmt.Printf("Gas médio por TX: %d\n", avgGas)
		fmt.Printf("Gas total usado: %d\n", totalGas)
		fmt.Printf("Valor E1 médio: %.6f BRL\n", avgE1Value)
		fmt.Printf("Valor E1 total: %.6f BRL\n", totalE1Value)

		fmt.Printf("\n⏱️  Latência:\n")
		fmt.Printf("Latência média: %s (%.2f ms)\n", avgLatency.Round(time.Millisecond), avgLatency.Seconds()*1000)
		fmt.Printf("Latência mínima: %s (%.2f ms)\n", minLatency.Round(time.Millisecond), minLatency.Seconds()*1000)
		fmt.Printf("Latência máxima: %s (%.2f ms)\n", maxLatency.Round(time.Millisecond), maxLatency.Seconds()*1000)

		fmt.Printf("\n⚡ Performance:\n")
		fmt.Printf("Workload total: %d transações (%d dispositivos × %d txs)\n", workload, NumWorkers, len(rows))
		fmt.Printf("Throughput total: %.2f tx/s\n", throughput)
		fmt.Printf("Média por dispositivo: %.1f transações\n", avgPerDevice)
		fmt.Printf("Tempo médio por dispositivo: %s\n", elapsed.Round(time.Millisecond))

		// Estatísticas por worker
		fmt.Printf("\n📈 Estatísticas por Worker:\n")
		fmt.Printf("%-10s | %-15s | %-15s | %-15s | %-12s\n",
			"Worker", "Sucesso", "Erro", "Taxa Sucesso", "Throughput")
		fmt.Println(strings.Repeat("-", 80))
		for _, stats := range workerStatsList {
			workerThroughput := 0.0
			successRate := 0.0
			if stats.Duration.Seconds() > 0 && stats.SuccessfulTxs > 0 {
				workerThroughput = float64(stats.SuccessfulTxs) / stats.Duration.Seconds()
			}
			if stats.TotalTxs > 0 {
				successRate = float64(stats.SuccessfulTxs) / float64(stats.TotalTxs) * 100
			}
			fmt.Printf("Worker %-3d | %6d / %-6d | %-6d         | %6.2f%%        | %6.2f tx/s\n",
				stats.WorkerID, stats.SuccessfulTxs, stats.TotalTxs, stats.FailedTxs,
				successRate, workerThroughput)
		}

		// Salvar resultados
		dir, _ := os.Getwd()
		outputFile := filepath.Join(dir, "blockchain_results_multithread.csv")
		if err := saveResults(allResults, outputFile); err != nil {
			log.Printf("❌ Erro ao salvar resultados: %v", err)
		} else {
			fmt.Printf("\n✅ Resultados salvos em: %s\n", outputFile)
		}

		// Salvar estatísticas dos workers
		statsFile := filepath.Join(dir, "worker_statistics.csv")
		if err := saveWorkerStats(workerStatsList, statsFile); err != nil {
			log.Printf("❌ Erro ao salvar estatísticas: %v", err)
		} else {
			fmt.Printf("✅ Estatísticas dos workers: %s\n", statsFile)
		}
	}
}
