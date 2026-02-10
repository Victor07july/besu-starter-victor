aws logs filter-log-events \
  --log-group-name /aws/lambda/blockchain \
  --filter-pattern "ERROR" \
  --start-time $(($(date +%s -d "6 hours ago") * 1000))

  aws logs filter-log-events \
  --log-group-name /aws/lambda/blockchain \
  --filter-pattern "?ERROR ?Exception ?Traceback" \
  --start-time $(($(date +%s -d "6 hours ago") * 1000)) \
  | jq -r '.events[] | "\(.timestamp | todate) | \(.message)"'

  aws logs filter-log-events \
  --log-group-name /aws/lambda/blockchain \
  --filter-pattern "Falha ao conectar" \
  --start-time $(($(date +%s -d "1 hour ago") * 1000)) \
  | jq -r '.events[] | .message'

  aws logs tail /aws/lambda/blockchain --since 1h \
  | grep -i -A 5 -B 2 "falha\|erro\|error\|exception\|failed"



  aws logs filter-log-events \
  --log-group-name /aws/lambda/blockchain \
  --filter-pattern "ERROR" \
  --start-time $(($(date +%s -d "6 hours ago") * 1000)) \
  | jq -r '.events[].message' \
  | grep -oE "(timeout|connection|failed|exception|error).*" \
  | sort | uniq -c | sort -rn


  aws logs filter-log-events \
  --log-group-name /aws/lambda/blockchain \
  --filter-pattern "Sucesso: 0/" \
  --start-time $(($(date +%s -d "1 hour ago") * 1000)) \
  | jq -r '.events[] | "\(.timestamp | todate)\n\(.message)\n---"'

  aws logs filter-log-events \
  --log-group-name /aws/lambda/blockchain \
  --filter-pattern "ERROR" \
  --start-time $(($(date +%s -d "1 hour ago") * 1000)) \
  | jq -r '.events[] | select(.message | contains("RequestId")) | .message'

  tempo real

  aws logs tail /aws/lambda/blockchain --follow \
  | grep --color=always -i "erro\|error\|falha\|exception\|failed"

  aws logs tail /aws/lambda/blockchain --follow \
  | grep "❌"

  # Ver últimos 10 erros com timestamp formatado
aws logs filter-log-events \
  --log-group-name /aws/lambda/blockchain \
  --filter-pattern "?ERROR ?Exception ?\"❌\"" \
  --start-time $(($(date +%s -d "1 hour ago") * 1000)) \
  --max-items 10 \
  | jq -r '.events[] | 
    "\u001b[31m[\(.timestamp | todate)]\u001b[0m\n\(.message)\n" + ("-" * 70)'

    # Salvar todos os erros em arquivo
aws logs filter-log-events \
  --log-group-name /aws/lambda/blockchain \
  --filter-pattern "ERROR" \
  --start-time $(($(date +%s -d "24 hours ago") * 1000)) \
  > errors_last_24h.json

# Ver de forma legível
cat errors_last_24h.json | jq -r '.events[] | .message' | less