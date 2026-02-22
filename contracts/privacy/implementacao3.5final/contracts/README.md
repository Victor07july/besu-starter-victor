# 🔒 E1RegistryGPS - Contrato com Privacidade Diferencial

Contrato Solidity para registro de viagens com coordenadas GPS protegidas por Privacidade Diferencial, integrando monetização de emissões de carbono.

---

## 📋 Histórico de Otimizações

### Versão Otimizada (Atual)
**Data:** 2026-02-15

**Mantido:**
- ✅ Cálculo de monetização E1 (função principal)
- ✅ Armazenamento de coordenadas GPS protegidas
- ✅ Registro de viagens
- ✅ Sistema de pagamentos

**Removido para otimização:**
- ❌ Função `_calculateGPSDistance()` - Cálculo Haversine de distância
- ❌ Campo `gpsDistance` no struct `TripGPSData`
- ❌ Função `getTripGPS()` - Retorno isolado de coordenadas
- ❌ Emissão de `startLat/startLon` em eventos

**Justificativa:**
O cálculo de distância GPS não estava sendo usado na monetização E1. As coordenadas eram armazenadas apenas para auditoria futura, mas não impactavam a recompensa.

---

## 🗂️ Funcionalidades Removidas (Referência Futura)

### 1. Cálculo de Distância GPS (Haversine Simplificado)

```solidity
/**
 * @dev Calcula distância entre dois pontos GPS usando Haversine simplificado
 * @return Distância em km × 1e6
 */
function _calculateGPSDistance(
    GPSLocation memory start,
    GPSLocation memory end
) internal pure returns (uint256) {
    // Diferenças em graus (já × 1e6)
    int256 dLat = end.latitude - start.latitude;
    int256 dLon = end.longitude - start.longitude;

    // Conversão aproximada: 1° ≈ 111 km
    uint256 absLat = dLat >= 0 ? uint256(dLat) : uint256(-dLat);
    uint256 absLon = dLon >= 0 ? uint256(dLon) : uint256(-dLon);

    uint256 latKm = (absLat * 111) / 1e6;
    uint256 lonKm = (absLon * 111) / 1e6;

    // Distância euclidiana aproximada
    uint256 maxKm = latKm > lonKm ? latKm : lonKm;
    uint256 minKm = latKm <= lonKm ? latKm : lonKm;
    uint256 distKm = maxKm + (minKm / 2);

    return distKm * 1e6; // km × 1e6
}
```

**Uso:** Auditoria, validação de coerência entre `gpsDistance` e `totalDistance`

---

### 2. Função getTripGPS (Consulta Isolada)

```solidity
/**
 * @dev Retorna apenas as coordenadas GPS de uma viagem
 * Útil para análise geográfica sem expor todos os dados
 */
function getTripGPS(
    uint256 _tripId
)
    external
    view
    returns (
        GPSLocation memory startLocation,
        GPSLocation memory endLocation,
        uint256 gpsDistance
    )
{
    TripGPSData memory trip = trips[_tripId];
    return (trip.startLocation, trip.endLocation, trip.gpsDistance);
}
```

**Uso:** Análise geográfica agregada, estudos de mobilidade

---

### 3. Campo gpsDistance no Struct

```solidity
struct TripGPSData {
    // ... outros campos
    uint256 gpsDistance; // Distância calculada por GPS (km × 1e6)
}
```

**Uso:** Comparação com `totalDistance` para detectar inconsistências

---

## 💡 Sugestões de Implementação: GPS no Cálculo de E1

### Cenário 1: Bônus por Viagens Curtas (Incentivo a Mobilidade Local)

**Conceito:** Viagens mais curtas recebem bônus adicional para incentivar deslocamentos locais.

```solidity
function _calculateE1WithDistanceBonus(
    TripGPSParams memory params
) internal pure returns (uint256 metaCO2, int256 diff, int256 valorE1) {
    // Cálculo padrão de E1
    (metaCO2, diff, valorE1) = _calculateE1(params);
    
    // Calcular distância GPS
    uint256 gpsDistance = _calculateGPSDistance(
        params.startLocation,
        params.endLocation
    );
    
    // Aplicar bônus: viagens < 10km recebem 20% extra
    if (gpsDistance < 10 * 1e6 && valorE1 > 0) {
        int256 bonus = (valorE1 * 20) / 100;
        valorE1 += bonus;
    }
    
    return (metaCO2, diff, valorE1);
}
```

**Parâmetros ajustáveis:**
- Distância limite para bônus (10km)
- Percentual de bônus (20%)
- Escalonamento (10-20km = 10%, <10km = 20%)

---

### Cenário 2: Fator Regional (Zonas Geográficas com Incentivos Diferentes)

**Conceito:** Áreas urbanas vs rurais têm multiplicadores diferentes.

```solidity
// Definir zonas geográficas (exemplo: Natal/RN)
struct GeoZone {
    int256 latMin;
    int256 latMax;
    int256 lonMin;
    int256 lonMax;
    uint256 multiplier; // × 100 (ex: 120 = 1.20x)
    string name;
}

mapping(uint256 => GeoZone) public geoZones;
uint256 public zoneCount;

function _calculateE1WithRegionalFactor(
    TripGPSParams memory params
) internal view returns (uint256 metaCO2, int256 diff, int256 valorE1) {
    (metaCO2, diff, valorE1) = _calculateE1(params);
    
    // Verificar se o ponto inicial está em zona especial
    uint256 multiplier = 100; // Default: 1.0x
    
    for (uint256 i = 0; i < zoneCount; i++) {
        GeoZone memory zone = geoZones[i];
        
        if (params.startLocation.latitude >= zone.latMin &&
            params.startLocation.latitude <= zone.latMax &&
            params.startLocation.longitude >= zone.lonMin &&
            params.startLocation.longitude <= zone.lonMax) {
            multiplier = zone.multiplier;
            break;
        }
    }
    
    // Aplicar multiplicador regional
    if (multiplier != 100 && valorE1 > 0) {
        valorE1 = (valorE1 * int256(multiplier)) / 100;
    }
    
    return (metaCO2, diff, valorE1);
}

// Função administrativa para adicionar zonas
function addGeoZone(
    int256 _latMin,
    int256 _latMax,
    int256 _lonMin,
    int256 _lonMax,
    uint256 _multiplier,
    string memory _name
) external onlyOwner {
    geoZones[zoneCount++] = GeoZone({
        latMin: _latMin,
        latMax: _latMax,
        lonMin: _lonMin,
        lonMax: _lonMax,
        multiplier: _multiplier,
        name: _name
    });
}
```

**Exemplo de uso:**
```javascript
// Natal centro urbano: 1.3x (incentivo à descarbonização urbana)
await contract.addGeoZone(
  -5850000,  // -5.85°
  -5790000,  // -5.79°
  -35210000, // -35.21°
  -35180000, // -35.18°
  130,       // 1.3x
  "Natal Centro"
);

// Zona rural: 0.8x (menor incentivo)
await contract.addGeoZone(
  -5900000,
  -5850000,
  -35300000,
  -35250000,
  80,
  "Zona Rural"
);
```

---

### Cenário 3: Penalidade por Deslocamento Excessivo vs Emissão Reportada

**Conceito:** Se a distância GPS for muito diferente da distância reportada, aplicar penalidade.

```solidity
function _calculateE1WithCoherenceCheck(
    TripGPSParams memory params
) internal pure returns (uint256 metaCO2, int256 diff, int256 valorE1) {
    (metaCO2, diff, valorE1) = _calculateE1(params);
    
    uint256 gpsDistance = _calculateGPSDistance(
        params.startLocation,
        params.endLocation
    );
    
    uint256 reportedDistance = params.highwayDistance + params.cityDistance;
    
    // Calcular diferença percentual
    uint256 diffPct;
    if (reportedDistance > gpsDistance) {
        diffPct = ((reportedDistance - gpsDistance) * 100) / reportedDistance;
    } else {
        diffPct = ((gpsDistance - reportedDistance) * 100) / gpsDistance;
    }
    
    // Se divergência > 20%, aplicar penalidade de 50%
    if (diffPct > 20 && valorE1 > 0) {
        valorE1 = valorE1 / 2;
    }
    // Se divergência > 50%, zerar recompensa
    else if (diffPct > 50) {
        valorE1 = 0;
    }
    
    return (metaCO2, diff, valorE1);
}
```

**Observação:** Esta abordagem pode conflitar com a privacidade diferencial, pois o ruído aplicado às coordenadas pode causar divergências legítimas.

---

### Cenário 4: Multiplicador Baseado em Densidade de Viagens (Heatmap)

**Conceito:** Áreas com muitas viagens recebem bônus maior (gamificação).

```solidity
// Dividir mapa em grid de células (ex: 0.01° × 0.01°)
mapping(int256 => mapping(int256 => uint256)) public tripCountByCell;

function _getCellKey(int256 lat, int256 lon) internal pure returns (int256, int256) {
    // Arredondar para célula de 0.01° (× 1e6 = 10000)
    int256 cellLat = (lat / 10000) * 10000;
    int256 cellLon = (lon / 10000) * 10000;
    return (cellLat, cellLon);
}

function _calculateE1WithHeatmapBonus(
    TripGPSParams memory params
) internal returns (uint256 metaCO2, int256 diff, int256 valorE1) {
    (metaCO2, diff, valorE1) = _calculateE1(params);
    
    // Obter célula do ponto inicial
    (int256 cellLat, int256 cellLon) = _getCellKey(
        params.startLocation.latitude,
        params.startLocation.longitude
    );
    
    // Incrementar contador dessa célula
    tripCountByCell[cellLat][cellLon]++;
    
    uint256 cellTrips = tripCountByCell[cellLat][cellLon];
    
    // Aplicar bônus baseado em densidade
    // 1-10 viagens: sem bônus
    // 11-50 viagens: +10%
    // 51-100 viagens: +20%
    // 100+ viagens: +30%
    if (cellTrips > 100 && valorE1 > 0) {
        valorE1 = (valorE1 * 130) / 100;
    } else if (cellTrips > 50) {
        valorE1 = (valorE1 * 120) / 100;
    } else if (cellTrips > 10) {
        valorE1 = (valorE1 * 110) / 100;
    }
    
    return (metaCO2, diff, valorE1);
}
```

---

### Cenário 5: Integração com Oráculo Externo (Dados de Tráfego/Poluição)

**Conceito:** Consultar oráculo externo para obter índice de poluição na região.

```solidity
interface IPollutionOracle {
    function getPollutionIndex(int256 lat, int256 lon) external view returns (uint256);
}

IPollutionOracle public pollutionOracle;

function _calculateE1WithPollutionFactor(
    TripGPSParams memory params
) internal view returns (uint256 metaCO2, int256 diff, int256 valorE1) {
    (metaCO2, diff, valorE1) = _calculateE1(params);
    
    // Obter índice de poluição da região (0-100)
    uint256 pollutionIndex = pollutionOracle.getPollutionIndex(
        params.startLocation.latitude,
        params.startLocation.longitude
    );
    
    // Áreas mais poluídas recebem incentivo maior
    // Poluição 80-100: +50%
    // Poluição 60-79: +30%
    // Poluição 40-59: +15%
    // Poluição 0-39: sem bônus
    if (pollutionIndex >= 80 && valorE1 > 0) {
        valorE1 = (valorE1 * 150) / 100;
    } else if (pollutionIndex >= 60) {
        valorE1 = (valorE1 * 130) / 100;
    } else if (pollutionIndex >= 40) {
        valorE1 = (valorE1 * 115) / 100;
    }
    
    return (metaCO2, diff, valorE1);
}

function setPollutionOracle(address _oracle) external onlyOwner {
    pollutionOracle = IPollutionOracle(_oracle);
}
```

---

## 🎯 Recomendação de Implementação

**Sugestão principal:** **Cenário 2 (Fator Regional)** + **Cenário 1 (Bônus por Viagens Curtas)**

**Justificativa:**
1. ✅ **Simples de implementar** - Não requer oráculos externos
2. ✅ **Compatível com DP** - Zonas grandes (0.1° × 0.1°) não quebram privacidade
3. ✅ **Gamificação efetiva** - Incentiva comportamentos específicos
4. ✅ **Gas eficiente** - Poucas operações adicionais
5. ✅ **Configurável** - Owner pode ajustar zonas e bônus

**Possível combinação:**
```solidity
function _calculateE1WithGPS(
    TripGPSParams memory params
) internal view returns (uint256 metaCO2, int256 diff, int256 valorE1) {
    // Cálculo base
    (metaCO2, diff, valorE1) = _calculateE1(params);
    
    if (valorE1 <= 0) return (metaCO2, diff, valorE1);
    
    // 1. Aplicar fator regional
    uint256 multiplier = _getRegionalMultiplier(params.startLocation);
    valorE1 = (valorE1 * int256(multiplier)) / 100;
    
    // 2. Aplicar bônus por viagem curta
    uint256 gpsDistance = _calculateGPSDistance(
        params.startLocation,
        params.endLocation
    );
    
    if (gpsDistance < 10 * 1e6) {
        int256 bonus = (valorE1 * 20) / 100;
        valorE1 += bonus;
    }
    
    return (metaCO2, diff, valorE1);
}
```

---

## 📊 Impacto do GPS na Privacidade

**Importante:** Ao usar GPS no cálculo de E1, considere:

### ⚠️ Riscos:
1. **Ataques de inferência:** Se bônus for muito específico, pode revelar localização
2. **Correlação temporal:** Múltiplas viagens podem triangular posição exata
3. **Zonas pequenas:** Células < 0.05° podem quebrar privacidade diferencial

### ✅ Mitigações:
1. **Zonas amplas:** Usar células grandes (0.1° - 0.5° = 11-55 km)
2. **Bônus escalonados:** Evitar saltos abruptos nas recompensas
3. **Randomização adicional:** Aplicar ruído ao próprio multiplicador
4. **Agregação temporal:** Calcular bônus apenas após N viagens na região

---

## 🔧 Próximos Passos

1. ✅ Decidir qual(is) cenário(s) implementar
2. ✅ Adicionar funções ao contrato
3. ✅ Testar com dados reais protegidos por DP
4. ✅ Ajustar parâmetros (distâncias, multiplicadores, thresholds)
5. ✅ Deploy e monitoramento

---

## 📚 Referências

- **Privacidade Diferencial:** Dwork & Roth (2014)
- **Geo-privacy:** Andrés et al. (2013) - "Geo-Indistinguishability"
- **Smart Contracts & Location:** Zyskind et al. (2015)

---

**Atualizado:** 2026-02-15  
**Versão:** Otimizada  
**Autor:** Victor
