# Pizzaria Jablonsk — Medidas DAX para Power BI

Copie cada medida em **Modelagem → Nova Medida**.  
Tabela base sugerida: `fato_pedidos` (salvo indicação contrária).

---

## RELACIONAMENTOS RECOMENDADOS

```
fato_pedidos[pedido_id]        → status_historico[pedido_id]     (1:N)
fato_pedidos[cliente_id]       → dim_clientes[cliente_id]        (N:1)
fato_pedidos[cupom_id]         → dim_cupons[cupom_id]            (N:1)
itens_pedido_detalhado[pedido_id] → fato_pedidos[pedido_id]      (N:1)
bridge_itens_sabores[item_pedido_id] → itens_pedido_detalhado[item_id] (N:1)
avaliacoes[pedido_id]          → fato_pedidos[pedido_id]         (1:1)
```

---

## 1. KPIs PRINCIPAIS (cartões)

```dax
-- Faturamento Total
Faturamento Total =
CALCULATE(
    SUMX(fato_pedidos, fato_pedidos[total]),
    fato_pedidos[status] = "entregue"
)

-- Ticket Médio
Ticket Médio =
CALCULATE(
    AVERAGEX(fato_pedidos, fato_pedidos[total]),
    fato_pedidos[status] = "entregue"
)

-- Total de Pedidos
Total Pedidos =
COUNTROWS(fato_pedidos)

-- Pedidos Entregues
Pedidos Entregues =
CALCULATE(COUNTROWS(fato_pedidos), fato_pedidos[status] = "entregue")

-- Taxa de Cancelamento (%)
Taxa Cancelamento % =
DIVIDE(
    CALCULATE(COUNTROWS(fato_pedidos), fato_pedidos[status] = "cancelado"),
    COUNTROWS(fato_pedidos),
    0
) * 100

-- Total de Clientes
Total Clientes =
DISTINCTCOUNT(fato_pedidos[cliente_id])

-- Clientes que compraram mais de 1x (recorrentes)
Clientes Recorrentes =
COUNTROWS(
    FILTER(
        SUMMARIZE(fato_pedidos, fato_pedidos[cliente_id], "qtd", COUNTROWS(fato_pedidos)),
        [qtd] > 1
    )
)

-- Taxa de Retenção (%)
Taxa Retenção % =
DIVIDE([Clientes Recorrentes], [Total Clientes], 0) * 100
```

---

## 2. FATURAMENTO E TENDÊNCIA

```dax
-- Faturamento Mês Anterior
Faturamento Mês Anterior =
CALCULATE(
    [Faturamento Total],
    DATEADD(fato_pedidos[data], -1, MONTH)
)

-- Variação MoM (%)
Variação MoM % =
DIVIDE(
    [Faturamento Total] - [Faturamento Mês Anterior],
    [Faturamento Mês Anterior],
    0
) * 100

-- Faturamento Acumulado no Ano (YTD)
Faturamento YTD =
CALCULATE(
    [Faturamento Total],
    DATESYTD(fato_pedidos[data])
)

-- Média Móvel 3 meses
Média Móvel 3M =
AVERAGEX(
    DATESINPERIOD(fato_pedidos[data], LASTDATE(fato_pedidos[data]), -3, MONTH),
    [Faturamento Total]
)
```

---

## 3. NPS E AVALIAÇÕES

```dax
-- Nota Média
Nota Média =
AVERAGE(avaliacoes[nota])

-- % Promotores (nota 4 ou 5)
% Promotores =
DIVIDE(
    CALCULATE(COUNTROWS(avaliacoes), avaliacoes[nota] >= 4),
    COUNTROWS(avaliacoes),
    0
) * 100

-- % Detratores (nota 1 ou 2)
% Detratores =
DIVIDE(
    CALCULATE(COUNTROWS(avaliacoes), avaliacoes[nota] <= 2),
    COUNTROWS(avaliacoes),
    0
) * 100

-- NPS Score
NPS Score =
[% Promotores] - [% Detratores]

-- Total Avaliações
Total Avaliações =
COUNTROWS(avaliacoes)

-- % Pedidos com Avaliação
% Avaliados =
DIVIDE([Total Avaliações], [Pedidos Entregues], 0) * 100
```

---

## 4. ANÁLISE DE PRODUTOS

```dax
-- Receita por Sabor (usar em tabela/gráfico com bridge_itens_sabores[sabor])
Receita por Sabor =
SUMX(
    RELATEDTABLE(bridge_itens_sabores),
    RELATED(itens_pedido_detalhado[subtotal]) /
    COUNTROWS(RELATEDTABLE(bridge_itens_sabores))
)

-- Ranking de Sabores por Receita
Ranking Sabor =
RANKX(
    ALL(bridge_itens_sabores[sabor]),
    [Receita por Sabor],
    ,
    DESC,
    DENSE
)

-- % do Faturamento por Sabor
% Fat por Sabor =
DIVIDE(
    [Receita por Sabor],
    CALCULATE([Receita por Sabor], ALL(bridge_itens_sabores[sabor])),
    0
) * 100

-- Pizzas Doces vs Salgadas
Receita Categoria =
CALCULATE(
    [Faturamento Total],
    RELATEDTABLE(bridge_itens_sabores)
)
```

---

## 5. SLA E OPERACIONAL

```dax
-- Tempo Médio Total do Pedido (minutos) — via status_historico
SLA Médio Total (min) =
CALCULATE(
    AVERAGE(fato_pedidos[min_ciclo_total]),
    fato_pedidos[status] = "entregue",
    NOT ISBLANK(fato_pedidos[min_ciclo_total])
)

-- Tempo Médio de Produção
SLA Produção (min) =
CALCULATE(
    AVERAGE(fato_pedidos[min_tempo_producao]),
    NOT ISBLANK(fato_pedidos[min_tempo_producao])
)

-- Tempo Médio de Entrega
SLA Entrega (min) =
CALCULATE(
    AVERAGE(fato_pedidos[min_tempo_entrega]),
    NOT ISBLANK(fato_pedidos[min_tempo_entrega])
)

-- % Pedidos dentro do SLA (menos de 60 min ciclo total)
% Dentro do SLA =
DIVIDE(
    CALCULATE(
        COUNTROWS(fato_pedidos),
        fato_pedidos[min_ciclo_total] <= 60,
        fato_pedidos[status] = "entregue"
    ),
    [Pedidos Entregues],
    0
) * 100
```

---

## 6. CLIENTES E LTV

```dax
-- LTV Médio por Cliente
LTV Médio =
DIVIDE([Faturamento Total], [Total Clientes], 0)

-- Pedidos por Cliente (frequência)
Frequência Média =
DIVIDE([Pedidos Entregues], [Total Clientes], 0)

-- Receita Top 10 Clientes
Receita Top 10 Clientes =
CALCULATE(
    [Faturamento Total],
    TOPN(10,
        SUMMARIZE(fato_pedidos, fato_pedidos[cliente_id]),
        [Faturamento Total],
        DESC
    )
)
```

---

## 7. CUPONS

```dax
-- % Pedidos com Cupom
% Pedidos com Cupom =
DIVIDE(
    CALCULATE(COUNTROWS(fato_pedidos), NOT ISBLANK(fato_pedidos[cupom_id])),
    COUNTROWS(fato_pedidos),
    0
) * 100

-- Desconto Total Concedido
Desconto Total =
SUM(fato_pedidos[desconto])

-- Impacto do Desconto no Faturamento (%)
% Impacto Desconto =
DIVIDE([Desconto Total], [Desconto Total] + [Faturamento Total], 0) * 100
```

---

## 8. FORMA DE PAGAMENTO

```dax
-- % Pix
% Pix =
DIVIDE(
    CALCULATE(COUNTROWS(fato_pedidos), fato_pedidos[forma_pagamento] = "pix"),
    COUNTROWS(fato_pedidos),
    0
) * 100

-- Ticket Médio por Forma (usar em visual com forma_pagamento no eixo)
Ticket por Forma =
CALCULATE([Ticket Médio])
```

---

## SUGESTÃO DE DASHBOARD (3 páginas)

### Página 1 — Visão Executiva
| Visual | Campos |
|---|---|
| 4 cartões KPI | Faturamento Total, Ticket Médio, Taxa Cancelamento %, NPS Score |
| Gráfico de linhas | Faturamento Total por `ano_mes` + linha Média Móvel 3M |
| Gráfico de barras | Faturamento por `dia_semana_nome` |
| Gráfico de pizza | Total Pedidos por `forma_pagamento` |
| Cartão | Variação MoM % |

### Página 2 — Produtos & Operação
| Visual | Campos |
|---|---|
| Gráfico de barras horizontais | Receita por Sabor (Top 10) |
| Tabela | Sabor, Ranking Sabor, % Fat por Sabor, vezes_pedido |
| Gráfico de barras empilhadas | Pedidos por `hora_pedido` |
| Mapa de calor (Matrix) | Linhas: `dia_semana_nome` · Colunas: `hora_pedido` · Valores: Total Pedidos |
| Cartões | SLA Médio Total, SLA Produção, SLA Entrega, % Dentro do SLA |

### Página 3 — Clientes & NPS
| Visual | Campos |
|---|---|
| Gráfico de barras | LTV por cliente (Top 10) |
| Gráfico de barras | Distribuição de notas (1–5) com medida % Promotores/Detratores |
| Cartões | NPS Score, Nota Média, % Avaliados, Taxa Retenção % |
| Tabela | cliente, total_pedidos, LTV, ticket_medio, ultimo_pedido |
| Gráfico rosca | % Pedidos com Cupom vs Sem Cupom |
