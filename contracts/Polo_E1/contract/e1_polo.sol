// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title E1PoloCalculator
 * @dev Contrato para calcular créditos de carbono E1 baseado em dados de consumo de combustível
 */
contract E1PoloCalculator {
    
    // Constantes de emissão (multiplicadas por 1000 para precisão)
    uint256 constant EMISSAO_GASOLINA = 1720; // 1.720 kg CO2/L
    uint256 constant EMISSAO_ETANOL = 1510;   // 1.510 kg CO2/L
    
    // Estrutura para armazenar dados do veículo
    struct VehicleData {
        uint256 distanceHighway;      // Distância em rodovia (km)
        uint256 distanceCity;         // Distância em cidade (km)
        uint256 cityGasoline;         // Consumo gasolina cidade (km/L * 1000)
        uint256 roadGasoline;         // Consumo gasolina rodovia (km/L * 1000)
        uint256 cityEthanol;          // Consumo etanol cidade (km/L * 1000)
        uint256 roadEthanol;          // Consumo etanol rodovia (km/L * 1000)
        uint256 carbonPriceEuropean;  // Preço carbono europeu (EUR * 100)
        uint256 euroPrice;            // Preço do Euro em Reais (* 10000)
    }
    
    // Evento para registrar cálculos
    event E1Calculated(
        address indexed vehicle,
        uint256 metaCO2,
        uint256 diff,
        uint256 e1Value,
        uint256 timestamp
    );
    
    /**
     * @dev Calcula a meta de emissão de CO2 e o valor do crédito E1
     * @param data Dados do veículo
     * @return metaCO2 Meta de emissão em gramas de CO2
     * @return diff Diferença entre meta e emissão real em gramas
     * @return e1Value Valor do crédito E1 em reais (com 6 casas decimais)
     */
    function calculateE1(VehicleData memory data) 
        public 
        pure 
        returns (
            uint256 metaCO2,
            uint256 diff,
            uint256 e1Value
        ) 
    {
        // Cálculo parte 1 (rodovia)
        // parte_1 = dist_highway * (1/road_gasoline * EMISSAO_GASOLINA + 1/road_ethanol * EMISSAO_ETANOL) * 1000
        uint256 parte1Gas = 0;
        uint256 parte1Eth = 0;
        
        if (data.roadGasoline > 0) {
            // (1000000 / roadGasoline) * EMISSAO_GASOLINA * distanceHighway / 1000
            parte1Gas = (1000000 * EMISSAO_GASOLINA * data.distanceHighway) / data.roadGasoline / 1000;
        }
        
        if (data.roadEthanol > 0) {
            parte1Eth = (1000000 * EMISSAO_ETANOL * data.distanceHighway) / data.roadEthanol / 1000;
        }
        
        uint256 parte1 = parte1Gas + parte1Eth;
        
        // Cálculo parte 2 (cidade)
        uint256 parte2Gas = 0;
        uint256 parte2Eth = 0;
        
        if (data.cityGasoline > 0) {
            parte2Gas = (1000000 * EMISSAO_GASOLINA * data.distanceCity) / data.cityGasoline / 1000;
        }
        
        if (data.cityEthanol > 0) {
            parte2Eth = (1000000 * EMISSAO_ETANOL * data.distanceCity) / data.cityEthanol / 1000;
        }
        
        uint256 parte2 = parte2Gas + parte2Eth;
        
        // Meta de CO2 total
        metaCO2 = parte1 + parte2;
        
        // Diferença (Meta - Meta/2, conforme código Python modificado)
        diff = metaCO2 / 2;
        
        // Preço real = Carbon_Price_European * Euro_price
        // carbonPriceEuropean está em EUR * 100
        // euroPrice está em BRL * 10000
        // Resultado deve estar em BRL * 1000000 (6 casas decimais)
        uint256 realPrice = (data.carbonPriceEuropean * data.euroPrice * 100);
        
        // e1 = Diff * Real_price / 1_000_000
        // diff está em gramas
        // realPrice está em centavos * 1000000
        e1Value = (diff * realPrice) / 1000000000000;
        
        return (metaCO2, diff, e1Value);
    }
    
    /**
     * @dev Calcula e registra o E1 para um veículo
     * @param data Dados do veículo
     * @return e1Value Valor do crédito E1
     */
    function calculateAndRecordE1(VehicleData memory data) 
        public 
        returns (uint256 e1Value) 
    {
        (uint256 metaCO2, uint256 diff, uint256 e1Val) = calculateE1(data);
        
        emit E1Calculated(
            msg.sender,
            metaCO2,
            diff,
            e1Val,
            block.timestamp
        );
        
        return e1Val;
    }
    
    /**
     * @dev Função auxiliar para criar VehicleData com valores padrão do Polo
     * Valores padrão baseados no código Python
     */
    function createDefaultPoloData(
        uint256 distanceHighway,
        uint256 distanceCity
    ) 
        public 
        pure 
        returns (VehicleData memory) 
    {
        return VehicleData({
            distanceHighway: distanceHighway,
            distanceCity: distanceCity,
            cityGasoline: 13500,      // 13.5 km/L * 1000
            roadGasoline: 15700,      // 15.7 km/L * 1000
            cityEthanol: 9300,        // 9.3 km/L * 1000
            roadEthanol: 10900,       // 10.9 km/L * 1000
            carbonPriceEuropean: 8908, // 89.08 EUR * 100
            euroPrice: 61708          // 6.1708 BRL * 10000
        });
    }
    
    /**
     * @dev Calcula E1 com valores padrão do Polo
     */
    function calculateE1ForPolo(
        uint256 distanceHighway,
        uint256 distanceCity
    ) 
        public 
        pure 
        returns (
            uint256 metaCO2,
            uint256 diff,
            uint256 e1Value
        ) 
    {
        VehicleData memory data = createDefaultPoloData(distanceHighway, distanceCity);
        return calculateE1(data);
    }
}
