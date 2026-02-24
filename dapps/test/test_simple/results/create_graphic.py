import pandas as pd
import matplotlib.pyplot as plt
import os

# Criar pasta para imagens
output_dir = 'images'
os.makedirs(output_dir, exist_ok=True)

# Carregar o arquivo
df = pd.read_csv('comparison_summary.csv')

# =============================================================================
# 1. GRÁFICO DE THROUGHPUT
# =============================================================================
plt.figure(figsize=(12, 7))
plt.plot(df['num_workers'], df['throughput_real_tx_s'], marker='o', linestyle='-', 
         color='b', linewidth=2.5, markersize=10)
plt.title('Throughput vs Número de Workers', fontsize=16, fontweight='bold')
plt.xlabel('Número de Workers', fontsize=12)
plt.ylabel('Throughput (tx/s)', fontsize=12)
plt.grid(True, linestyle='--', alpha=0.7)
plt.xticks(df['num_workers'])

# Adicionar valores em cada ponto
for idx, row in df.iterrows():
    plt.text(row['num_workers'], row['throughput_real_tx_s'] + 0.5, 
             f"{row['throughput_real_tx_s']:.2f}", ha='center', va='bottom', fontweight='bold')

plt.tight_layout()
plt.savefig(f'{output_dir}/throughput.png', dpi=300, bbox_inches='tight')
print(f"✓ Gráfico salvo: {output_dir}/throughput.png")
plt.close()

# =============================================================================
# 2. GRÁFICO DE TRANSAÇÕES QUE FALHARAM
# =============================================================================
plt.figure(figsize=(12, 7))
bars = plt.bar(df['num_workers'], df['failed_txs'], color='red', alpha=0.7, edgecolor='darkred', linewidth=1.5)
plt.title('Transações Falhadas vs Número de Workers', fontsize=16, fontweight='bold')
plt.xlabel('Número de Workers', fontsize=12)
plt.ylabel('Número de Transações Falhadas', fontsize=12)
plt.grid(True, axis='y', linestyle='--', alpha=0.7)
plt.xticks(df['num_workers'])

# Adicionar valores no topo das barras
for i, (idx, row) in enumerate(df.iterrows()):
    plt.text(row['num_workers'], row['failed_txs'] + max(df['failed_txs']) * 0.02, 
             f"{int(row['failed_txs'])}", ha='center', va='bottom', fontweight='bold')

plt.tight_layout()
plt.savefig(f'{output_dir}/failed_transactions.png', dpi=300, bbox_inches='tight')
print(f"✓ Gráfico salvo: {output_dir}/failed_transactions.png")
plt.close()

# =============================================================================
# 3. GRÁFICO DE WORKERS QUE FALHARAM
# =============================================================================
fig, ax1 = plt.subplots(figsize=(12, 7))

# Calcular workers que falharam
df['failed_workers'] = df['workers_expected'] - df['workers_completed']

# Gráfico de barras: workers completados vs falhados
x_pos = range(len(df['num_workers']))
width = 0.35

bars1 = ax1.bar([x - width/2 for x in x_pos], df['workers_completed'], width, 
                label='Workers Completados', color='green', alpha=0.7)
bars2 = ax1.bar([x + width/2 for x in x_pos], df['failed_workers'], width, 
                label='Workers Falhados', color='red', alpha=0.7)

ax1.set_xlabel('Número de Workers', fontsize=12)
ax1.set_ylabel('Número de Workers', fontsize=12)
ax1.set_title('Workers Completados vs Falhados', fontsize=16, fontweight='bold')
ax1.set_xticks(x_pos)
ax1.set_xticklabels(df['num_workers'])
ax1.legend(loc='upper left', fontsize=11)
ax1.grid(True, axis='y', linestyle='--', alpha=0.7)

# Adicionar linha de taxa de completude (eixo secundário)
ax2 = ax1.twinx()
ax2.plot(x_pos, df['completion_rate_pct'], marker='D', linestyle=':', 
         color='blue', linewidth=2, markersize=8, label='Taxa de Completude (%)')
ax2.set_ylabel('Taxa de Completude (%)', fontsize=12, color='blue')
ax2.tick_params(axis='y', labelcolor='blue')
ax2.set_ylim([0, 110])
ax2.legend(loc='upper right', fontsize=11)

# Adicionar valores nas barras de workers falhados
for i, (idx, row) in enumerate(df.iterrows()):
    if row['failed_workers'] > 0:
        ax1.text(i + width/2, row['failed_workers'] + max(df['workers_expected']) * 0.01, 
                 f"{int(row['failed_workers'])}", ha='center', va='bottom', 
                 fontweight='bold', color='darkred')

plt.tight_layout()
plt.savefig(f'{output_dir}/failed_workers.png', dpi=300, bbox_inches='tight')
print(f"✓ Gráfico salvo: {output_dir}/failed_workers.png")
plt.close()

# =============================================================================
# 4. GRÁFICO DE LATÊNCIA MÉDIA
# =============================================================================
plt.figure(figsize=(12, 7))
plt.plot(df['num_workers'], df['avg_latency_ms'], marker='o', linestyle='-', 
         color='orange', linewidth=2.5, markersize=10, label='Latência Média')
plt.plot(df['num_workers'], df['p95_latency_ms'], marker='^', linestyle='--', 
         color='red', linewidth=2, markersize=8, label='P95')
plt.plot(df['num_workers'], df['p99_latency_ms'], marker='v', linestyle=':', 
         color='darkred', linewidth=2, markersize=8, label='P99')
plt.title('Latência vs Número de Workers', fontsize=16, fontweight='bold')
plt.xlabel('Número de Workers', fontsize=12)
plt.ylabel('Latência (ms)', fontsize=12)
plt.grid(True, linestyle='--', alpha=0.7)
plt.xticks(df['num_workers'])
plt.legend(fontsize=11)

# Adicionar valores na linha de latência média
for idx, row in df.iterrows():
    plt.text(row['num_workers'], row['avg_latency_ms'], 
             f"{row['avg_latency_ms']:.0f}", ha='center', va='bottom', 
             fontweight='bold', fontsize=9, color='orange')

plt.tight_layout()
plt.savefig(f'{output_dir}/latency.png', dpi=300, bbox_inches='tight')
print(f"✓ Gráfico salvo: {output_dir}/latency.png")
plt.close()

print(f"\n✅ Todos os gráficos foram salvos na pasta '{output_dir}/'")
