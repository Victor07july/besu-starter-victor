package main

import (
	"context"
	"crypto/ecdsa"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"math/big"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/ethereum/go-ethereum"
	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/crypto"
	"github.com/ethereum/go-ethereum/ethclient"
)

// ======================================================================
// CONFIGURAÇÕES DA BLOCKCHAIN
// ======================================================================

const (
	// URL do nó RPC (rpcnode-user, sem autenticação)
	RPCURL = "http://localhost:8547"

	// Conta que enviará as transações
	SenderAddress = "0xfe3b557e8fb62b89f4916b721be55ceb828dbd73"
	PrivateKey    = "8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63"

	// Arquivo JSON com dados do deploy (ABI e endereço do contrato)
	DeploymentJSON = "deployment_result.json"
)

// ======================================================================
// ESTRUTURAS DE DADOS
// ======================================================================

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

// Result armazena o resultado de uma transação
type Result struct {
	Linha   int
	TxHash  string
	Block   uint64
	GasUsed uint64
	MetaCO2 *big.Int
	Diff    *big.Int
	E1Value float64
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
	header := []string{"linha", "tx_hash", "block", "gas_used", "meta_co2", "diff", "e1_value"}
	if err := writer.Write(header); err != nil {
		return err
	}

	// Escrever dados
	for _, r := range results {
		record := []string{
			strconv.Itoa(r.Linha),
			r.TxHash,
			strconv.FormatUint(r.Block, 10),
			strconv.FormatUint(r.GasUsed, 10),
			r.MetaCO2.String(),
			r.Diff.String(),
			fmt.Sprintf("%.6f", r.E1Value),
		}
		if err := writer.Write(record); err != nil {
			return err
		}
	}

	return nil
}

// ======================================================================
// FUNÇÃO PRINCIPAL
// ======================================================================

func main() {
	fmt.Println(strings.Repeat("=", 70))
	fmt.Println("ENVIANDO DADOS PARA O CONTRATO E1PoloCalculator")
	fmt.Println(strings.Repeat("=", 70))

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

	// 1. Conectar à blockchain
	fmt.Println("\n[1] Conectando à blockchain...")
	client, err := ethclient.Dial(RPCURL)
	if err != nil {
		log.Fatalf("❌ Erro: Não foi possível conectar à blockchain\n   Verifique se o nó está rodando em %s\n   Erro: %v", RPCURL, err)
	}
	defer client.Close()

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

	// 2. Carregar o contrato
	fmt.Printf("\n[2] Carregando contrato em %s...\n", deployment.ContractAddress)

	contractAddress := common.HexToAddress(deployment.ContractAddress)

	// Parse ABI
	contractABI, err := abi.JSON(strings.NewReader(string(deployment.ABI)))
	if err != nil {
		log.Fatalf("❌ Erro ao fazer parse da ABI: %v", err)
	}

	fmt.Println("✅ Contrato carregado")

	// 3. Configurar conta
	fmt.Printf("\n[3] Configurando conta %s...\n", SenderAddress)

	privateKey, err := crypto.HexToECDSA(PrivateKey)
	if err != nil {
		log.Fatalf("❌ Erro ao carregar chave privada: %v", err)
	}

	publicKey := privateKey.Public()
	publicKeyECDSA, ok := publicKey.(*ecdsa.PublicKey)
	if !ok {
		log.Fatal("❌ Erro ao fazer cast da chave pública")
	}

	fromAddress := crypto.PubkeyToAddress(*publicKeyECDSA)

	balance, err := client.BalanceAt(ctx, fromAddress, nil)
	if err != nil {
		log.Fatalf("❌ Erro ao obter saldo: %v", err)
	}

	fmt.Println("✅ Conta configurada")
	balanceEth := new(big.Float).Quo(new(big.Float).SetInt(balance), big.NewFloat(1e18))
	fmt.Printf("   Saldo: %s ETH\n", balanceEth.Text('f', 18))

	// 4. Ler dados do CSV
	fmt.Println("\n[4] Lendo dados do CSV...")

	dir, _ := os.Getwd()
	csvPath := filepath.Join(dir, "vehicle_data_1.csv")

	rows, err := readCSV(csvPath)
	if err != nil {
		log.Fatalf("❌ Erro ao ler CSV: %v", err)
	}

	fmt.Printf("✅ CSV carregado: %d linhas\n", len(rows))

	// 5. Processar e enviar cada linha
	fmt.Println("\n[5] Enviando dados para a blockchain...")
	fmt.Println(strings.Repeat("-", 70))

	var results []Result

	for idx, row := range rows {
		fmt.Printf("\nProcessando linha %d/%d...\n", idx+1, len(rows))

		// Preparar dados
		vehicleData := prepareVehicleData(row)

		fmt.Printf("  → Distância rodovia: %s km\n", vehicleData.DistanceHighway.String())
		fmt.Printf("  → Distância cidade: %s km\n", vehicleData.DistanceCity.String())

		// Obter nonce
		nonce, err := client.PendingNonceAt(ctx, fromAddress)
		if err != nil {
			fmt.Printf("  ❌ Erro ao obter nonce: %v\n", err)
			continue
		}

		// Obter gas price
		gasPrice, err := client.SuggestGasPrice(ctx)
		if err != nil {
			fmt.Printf("  ❌ Erro ao obter gas price: %v\n", err)
			continue
		}

		// Preparar dados da transação
		input, err := contractABI.Pack("calculateAndRecordE1", vehicleData)
		if err != nil {
			fmt.Printf("  ❌ Erro ao fazer pack dos dados: %v\n", err)
			continue
		}

		// Criar transação
		gasLimit := uint64(500000)
		tx := types.NewTransaction(nonce, contractAddress, big.NewInt(0), gasLimit, gasPrice, input)

		// Assinar transação
		signedTx, err := types.SignTx(tx, types.NewEIP155Signer(chainID), privateKey)
		if err != nil {
			fmt.Printf("  ❌ Erro ao assinar transação: %v\n", err)
			continue
		}

		// Enviar transação
		err = client.SendTransaction(ctx, signedTx)
		if err != nil {
			fmt.Printf("  ❌ Erro ao enviar transação: %v\n", err)
			continue
		}

		fmt.Printf("  → TX enviada: %s\n", signedTx.Hash().Hex())

		// Aguardar confirmação
		receipt, err := waitForReceipt(ctx, client, signedTx.Hash(), 120*time.Second)
		if err != nil {
			fmt.Printf("  ❌ Erro ao aguardar confirmação: %v\n", err)
			continue
		}

		if receipt.Status == 1 {
			fmt.Printf("  ✅ Confirmada no bloco %d\n", receipt.BlockNumber.Uint64())

			// Processar eventos
			event, err := parseE1CalculatedEvent(contractABI, receipt.Logs)
			if err == nil && event != nil {
				fmt.Printf("  → Meta CO2: %s g\n", event["metaCO2"])
				fmt.Printf("  → Diferença: %s g\n", event["diff"])

				e1ValueBigInt := event["e1Value"].(*big.Int)
				e1ValueFloat := new(big.Float).Quo(new(big.Float).SetInt(e1ValueBigInt), big.NewFloat(1000000))
				e1Value, _ := e1ValueFloat.Float64()

				fmt.Printf("  → Valor E1: %.6f BRL\n", e1Value)

				results = append(results, Result{
					Linha:   idx + 1,
					TxHash:  signedTx.Hash().Hex(),
					Block:   receipt.BlockNumber.Uint64(),
					GasUsed: receipt.GasUsed,
					MetaCO2: event["metaCO2"].(*big.Int),
					Diff:    event["diff"].(*big.Int),
					E1Value: e1Value,
				})
			}
		} else {
			fmt.Println("  ❌ Transação falhou")
		}
	}

	// 6. Resumo final
	fmt.Println("\n" + strings.Repeat("=", 70))
	fmt.Println("RESUMO")
	fmt.Println(strings.Repeat("=", 70))
	fmt.Printf("Total de linhas processadas: %d/%d\n", len(results), len(rows))

	if len(results) > 0 {
		var totalGas uint64
		var totalE1Value float64

		for _, r := range results {
			totalGas += r.GasUsed
			totalE1Value += r.E1Value
		}

		avgE1Value := totalE1Value / float64(len(results))

		fmt.Printf("\nGas total usado: %d\n", totalGas)
		fmt.Printf("Valor E1 médio: %.6f BRL\n", avgE1Value)
		fmt.Printf("Valor E1 total: %.6f BRL\n", totalE1Value)

		// Salvar resultados
		outputFile := filepath.Join(dir, "blockchain_results.csv")
		if err := saveResults(results, outputFile); err != nil {
			log.Printf("❌ Erro ao salvar resultados: %v", err)
		} else {
			fmt.Printf("\n✅ Resultados salvos em: %s\n", outputFile)
		}
	}
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
