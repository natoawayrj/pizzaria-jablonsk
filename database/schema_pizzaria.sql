-- =============================================================================
-- PIZZARIA JABLONSK — Schema do Banco de Dados
-- =============================================================================
-- Versão    : 2.0 (refactor para portfólio de dados)
-- Banco     : MySQL 8.0+ / MariaDB 10.6+
-- Charset   : utf8mb4 (suporte completo a Unicode e emojis)
-- Collation : utf8mb4_unicode_ci
-- Autor     : Renato Batista
--
-- FILOSOFIA DE DESIGN:
--   - Timestamps em TODAS as tabelas (auditoria e analytics)
--   - Soft delete com flag `ativo` (nunca deletar dados históricos)
--   - Preço salvo como snapshot no item do pedido (proteção contra retroatividade)
--   - ENUM para campos categóricos (garante integridade sem tabela auxiliar)
--   - INT UNSIGNED em PKs (sem IDs negativos, dobra o range)
--   - Índices em todas as FKs e colunas de filtro frequente
--   - Star Schema implementado via VIEWs sobre as tabelas operacionais
-- =============================================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE DATABASE IF NOT EXISTS pizzaria
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE pizzaria;


-- =============================================================================
-- TABELAS OPERACIONAIS
-- =============================================================================

-- -----------------------------------------------------------------------------
-- admin_usuarios: Usuários do painel administrativo
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admin_usuarios (
    id           INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    nome         VARCHAR(100)    NOT NULL,
    email        VARCHAR(150)    NOT NULL,
    senha_hash   VARCHAR(255)    NOT NULL,
    perfil       ENUM('super_admin', 'gerente', 'atendente') NOT NULL DEFAULT 'atendente',
    ativo        TINYINT(1)      NOT NULL DEFAULT 1,
    ultimo_acesso DATETIME       NULL,
    created_at   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_admin_email (email),
    KEY idx_admin_ativo (ativo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Usuários com acesso ao painel administrativo';


-- -----------------------------------------------------------------------------
-- clientes: Clientes cadastrados no sistema
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS clientes (
    id              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    nome            VARCHAR(100)    NOT NULL,
    email           VARCHAR(150)    NOT NULL,
    senha_hash      VARCHAR(255)    NOT NULL,
    telefone        VARCHAR(20)     NULL,
    data_nascimento DATE            NULL                    COMMENT 'Para analytics de faixa etária',
    ativo           TINYINT(1)      NOT NULL DEFAULT 1,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_cliente_email (email),
    KEY idx_cliente_ativo (ativo),
    KEY idx_cliente_created (created_at)    COMMENT 'Análise de aquisição por período'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Clientes cadastrados no app';


-- -----------------------------------------------------------------------------
-- enderecos: Endereços de entrega dos clientes (1 cliente, N endereços)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS enderecos (
    id           INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    cliente_id   INT UNSIGNED    NOT NULL,
    logradouro   VARCHAR(150)    NOT NULL,
    numero       VARCHAR(20)     NOT NULL,
    complemento  VARCHAR(100)    NULL,
    bairro       VARCHAR(80)     NOT NULL,
    cidade       VARCHAR(80)     NOT NULL DEFAULT 'Niterói',
    estado       CHAR(2)         NOT NULL DEFAULT 'RJ',
    cep          VARCHAR(9)      NOT NULL,
    principal    TINYINT(1)      NOT NULL DEFAULT 0            COMMENT '1 = endereço padrão do cliente',
    created_at   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY idx_endereco_cliente (cliente_id),
    CONSTRAINT fk_endereco_cliente
        FOREIGN KEY (cliente_id) REFERENCES clientes (id)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Endereços de entrega dos clientes';


-- -----------------------------------------------------------------------------
-- categorias: Categorias de sabores e produtos (ex: Tradicionais, Doces, Bebidas)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS categorias (
    id         INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    nome       VARCHAR(60)     NOT NULL,
    tipo       ENUM('pizza', 'produto') NOT NULL             COMMENT 'Distingue categoria de sabor vs produto avulso',
    ativo      TINYINT(1)      NOT NULL DEFAULT 1,
    created_at DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY idx_categoria_tipo (tipo),
    KEY idx_categoria_ativo (ativo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Categorias de sabores e produtos';


-- -----------------------------------------------------------------------------
-- massas: Tipos de massa disponíveis (lookup table)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS massas (
    id              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    nome            VARCHAR(60)     NOT NULL,
    descricao       VARCHAR(200)    NULL,
    preco_adicional DECIMAL(8,2)    NOT NULL DEFAULT 0.00,
    ativo           TINYINT(1)      NOT NULL DEFAULT 1,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Tipos de massa disponíveis';


-- -----------------------------------------------------------------------------
-- bordas: Tipos de borda disponíveis (lookup table)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bordas (
    id              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    nome            VARCHAR(60)     NOT NULL,
    descricao       VARCHAR(200)    NULL,
    preco_adicional DECIMAL(8,2)    NOT NULL DEFAULT 0.00,
    ativo           TINYINT(1)      NOT NULL DEFAULT 1,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Tipos de borda disponíveis';


-- -----------------------------------------------------------------------------
-- sabores: Sabores de pizza disponíveis no cardápio
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sabores (
    id           INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    nome         VARCHAR(80)     NOT NULL,
    descricao    VARCHAR(300)    NULL,
    categoria_id INT UNSIGNED    NOT NULL,
    preco_base   DECIMAL(8,2)    NOT NULL                    COMMENT 'Preço base de uma pizza inteira deste sabor',
    disponivel   TINYINT(1)      NOT NULL DEFAULT 1,
    imagem_url   VARCHAR(255)    NULL,
    created_at   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY idx_sabor_categoria (categoria_id),
    KEY idx_sabor_disponivel (disponivel),
    CONSTRAINT fk_sabor_categoria
        FOREIGN KEY (categoria_id) REFERENCES categorias (id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Sabores de pizza do cardápio';


-- -----------------------------------------------------------------------------
-- produtos: Produtos avulsos (bebidas, sobremesas, porções)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS produtos (
    id           INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    nome         VARCHAR(80)     NOT NULL,
    descricao    VARCHAR(300)    NULL,
    categoria_id INT UNSIGNED    NOT NULL,
    preco        DECIMAL(8,2)    NOT NULL,
    estoque      INT             NOT NULL DEFAULT 0           COMMENT 'NULL = estoque ilimitado',
    disponivel   TINYINT(1)      NOT NULL DEFAULT 1,
    imagem_url   VARCHAR(255)    NULL,
    created_at   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY idx_produto_categoria (categoria_id),
    KEY idx_produto_disponivel (disponivel),
    CONSTRAINT fk_produto_categoria
        FOREIGN KEY (categoria_id) REFERENCES categorias (id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Produtos avulsos: bebidas, sobremesas, porções';


-- -----------------------------------------------------------------------------
-- cupons: Cupons de desconto
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cupons (
    id              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    codigo          VARCHAR(30)     NOT NULL,
    tipo            ENUM('percentual', 'fixo') NOT NULL       COMMENT 'percentual = % sobre total; fixo = R$ fixo',
    valor           DECIMAL(8,2)    NOT NULL,
    valor_minimo    DECIMAL(8,2)    NOT NULL DEFAULT 0.00     COMMENT 'Valor mínimo do pedido para usar o cupom',
    validade        DATE            NULL,
    usos_maximos    INT             NULL                       COMMENT 'NULL = uso ilimitado',
    usos_realizados INT             NOT NULL DEFAULT 0,
    ativo           TINYINT(1)      NOT NULL DEFAULT 1,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_cupom_codigo (codigo),
    KEY idx_cupom_ativo (ativo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Cupons de desconto para análise de conversão e impacto no ticket médio';


-- -----------------------------------------------------------------------------
-- pedidos: Tabela central — cada pedido realizado
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pedidos (
    id                  INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    cliente_id          INT UNSIGNED    NOT NULL,
    endereco_id         INT UNSIGNED    NOT NULL,
    cupom_id            INT UNSIGNED    NULL,

    -- Status e timestamps individuais (CRÍTICO para analytics de SLA)
    status              ENUM(
                            'aguardando_pagamento',
                            'recebido',
                            'em_producao',
                            'saiu_para_entrega',
                            'entregue',
                            'cancelado'
                        ) NOT NULL DEFAULT 'recebido',
    recebido_em         DATETIME        NULL,
    em_producao_em      DATETIME        NULL,
    saiu_entrega_em     DATETIME        NULL,
    entregue_em         DATETIME        NULL,
    cancelado_em        DATETIME        NULL,

    -- Financeiro
    subtotal            DECIMAL(10,2)   NOT NULL               COMMENT 'Total dos itens sem desconto',
    desconto            DECIMAL(10,2)   NOT NULL DEFAULT 0.00  COMMENT 'Valor total descontado pelo cupom',
    total               DECIMAL(10,2)   NOT NULL               COMMENT 'subtotal - desconto',
    forma_pagamento     ENUM('dinheiro', 'cartao_credito', 'cartao_debito', 'pix', 'pendente')
                                        NOT NULL DEFAULT 'pendente',
    troco_para          DECIMAL(10,2)   NULL                   COMMENT 'Preenchido quando forma_pagamento = dinheiro',

    -- Informações adicionais
    observacao          TEXT            NULL,
    cancelamento_motivo TEXT            NULL,

    created_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY idx_pedido_cliente    (cliente_id),
    KEY idx_pedido_endereco   (endereco_id),
    KEY idx_pedido_cupom      (cupom_id),
    KEY idx_pedido_status     (status),
    KEY idx_pedido_created    (created_at)                     COMMENT 'Análise temporal: dia/semana/mês',
    KEY idx_pedido_entregue   (entregue_em),
    KEY idx_pedido_pagamento  (forma_pagamento),

    CONSTRAINT fk_pedido_cliente
        FOREIGN KEY (cliente_id) REFERENCES clientes (id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_pedido_endereco
        FOREIGN KEY (endereco_id) REFERENCES enderecos (id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_pedido_cupom
        FOREIGN KEY (cupom_id) REFERENCES cupons (id)
        ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Tabela central de pedidos — fato principal do sistema';


-- -----------------------------------------------------------------------------
-- itens_pedido: Cada linha de um pedido (pizza ou produto)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS itens_pedido (
    id              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    pedido_id       INT UNSIGNED    NOT NULL,
    tipo            ENUM('pizza', 'produto') NOT NULL,

    -- Referências ao cardápio (NULLable: pizza não tem produto_id; produto não tem massa/borda)
    massa_id        INT UNSIGNED    NULL,
    borda_id        INT UNSIGNED    NULL,
    produto_id      INT UNSIGNED    NULL,

    quantidade      TINYINT UNSIGNED NOT NULL DEFAULT 1,

    -- SNAPSHOT de preço: nunca referenciar preço atual da tabela
    preco_unitario  DECIMAL(8,2)    NOT NULL               COMMENT 'Preço no momento do pedido (imutável)',
    subtotal        DECIMAL(10,2)   NOT NULL               COMMENT 'preco_unitario * quantidade',
    observacao      VARCHAR(300)    NULL,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY idx_item_pedido  (pedido_id),
    KEY idx_item_produto (produto_id),
    KEY idx_item_massa   (massa_id),
    KEY idx_item_borda   (borda_id),

    CONSTRAINT fk_item_pedido
        FOREIGN KEY (pedido_id) REFERENCES pedidos (id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_item_massa
        FOREIGN KEY (massa_id) REFERENCES massas (id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_item_borda
        FOREIGN KEY (borda_id) REFERENCES bordas (id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_item_produto
        FOREIGN KEY (produto_id) REFERENCES produtos (id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Itens individuais de cada pedido com snapshot de preço';


-- -----------------------------------------------------------------------------
-- itens_pedido_sabores: Sabores de cada pizza (até 3 sabores por pizza)
-- Modelo: cada pizza pode ter até 3 sabores em posições 1, 2 e 3
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS itens_pedido_sabores (
    id             INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    item_pedido_id INT UNSIGNED    NOT NULL,
    sabor_id       INT UNSIGNED    NOT NULL,
    posicao        TINYINT UNSIGNED NOT NULL               COMMENT 'Posição do sabor na pizza: 1, 2 ou 3',

    PRIMARY KEY (id),
    UNIQUE KEY uq_item_posicao (item_pedido_id, posicao)   COMMENT 'Cada posição única por item',
    KEY idx_ips_item   (item_pedido_id),
    KEY idx_ips_sabor  (sabor_id)                          COMMENT 'Analytics: sabores mais pedidos',

    CONSTRAINT fk_ips_item
        FOREIGN KEY (item_pedido_id) REFERENCES itens_pedido (id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_ips_sabor
        FOREIGN KEY (sabor_id) REFERENCES sabores (id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Associação N:N entre itens de pedido e sabores (até 3 por pizza)';


-- -----------------------------------------------------------------------------
-- avaliacoes: Avaliação do cliente após entrega (NPS e satisfação por produto)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS avaliacoes (
    id          INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    pedido_id   INT UNSIGNED    NOT NULL,
    cliente_id  INT UNSIGNED    NOT NULL,
    nota        TINYINT UNSIGNED NOT NULL                  COMMENT 'Nota de 1 a 5',
    comentario  TEXT            NULL,
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_avaliacao_pedido (pedido_id)             COMMENT '1 avaliação por pedido',
    KEY idx_avaliacao_cliente (cliente_id),
    KEY idx_avaliacao_nota    (nota)                       COMMENT 'Filtro por nota (ex: notas < 3)',

    CONSTRAINT chk_avaliacao_nota CHECK (nota BETWEEN 1 AND 5),
    CONSTRAINT fk_avaliacao_pedido
        FOREIGN KEY (pedido_id) REFERENCES pedidos (id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_avaliacao_cliente
        FOREIGN KEY (cliente_id) REFERENCES clientes (id)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Avaliações pós-entrega — base para análise de NPS e satisfação';


-- -----------------------------------------------------------------------------
-- status_historico: Log de todas as mudanças de status de pedidos
-- Essencial para análise de SLA e detecção de gargalos no processo
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS status_historico (
    id              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    pedido_id       INT UNSIGNED    NOT NULL,
    status_anterior ENUM(
                        'aguardando_pagamento', 'recebido', 'em_producao',
                        'saiu_para_entrega', 'entregue', 'cancelado'
                    ) NULL                                 COMMENT 'NULL na primeira transição',
    status_novo     ENUM(
                        'aguardando_pagamento', 'recebido', 'em_producao',
                        'saiu_para_entrega', 'entregue', 'cancelado'
                    ) NOT NULL,
    admin_id        INT UNSIGNED    NULL                   COMMENT 'NULL se mudança foi automática',
    observacao      VARCHAR(300)    NULL,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY idx_hist_pedido (pedido_id),
    KEY idx_hist_admin  (admin_id),
    KEY idx_hist_status (status_novo),

    CONSTRAINT fk_hist_pedido
        FOREIGN KEY (pedido_id) REFERENCES pedidos (id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_hist_admin
        FOREIGN KEY (admin_id) REFERENCES admin_usuarios (id)
        ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Auditoria de mudanças de status — base para análise de tempo por etapa e SLA';


-- =============================================================================
-- SEED DATA — Tabelas de lookup (valores fixos de operação)
-- =============================================================================

INSERT INTO categorias (nome, tipo) VALUES
    ('Tradicionais',     'pizza'),
    ('Especiais',        'pizza'),
    ('Doces',            'pizza'),
    ('Bebidas',          'produto'),
    ('Sobremesas',       'produto'),
    ('Porções',          'produto');

INSERT INTO massas (nome, descricao, preco_adicional) VALUES
    ('Fina',        'Massa crocante e levinha',                      0.00),
    ('Tradicional', 'Massa clássica no estilo italiano',             0.00),
    ('Grossa',      'Massa alta e macia, estilo americano',          3.00),
    ('Integral',    'Massa integral com farinha de trigo integral',  5.00);

INSERT INTO bordas (nome, descricao, preco_adicional) VALUES
    ('Sem borda',         'Sem recheio na borda',                    0.00),
    ('Catupiry',          'Borda recheada com Catupiry cremoso',     6.00),
    ('Cheddar',           'Borda recheada com cheddar derretido',    6.00),
    ('Chocolate',         'Borda recheada com chocolate ao leite',   6.00),
    ('Cream Cheese',      'Borda recheada com cream cheese',         7.00);

-- Admin padrão para setup inicial (senha deve ser trocada em produção)
-- Senha: 'admin123' — substituir por hash bcrypt em produção
INSERT INTO admin_usuarios (nome, email, senha_hash, perfil) VALUES
    ('Administrador', 'admin@pizzariajablonsk.com.br',
     '$2b$12$placeholder_hash_troque_em_producao', 'super_admin');


-- -----------------------------------------------------------------------------
-- sabores: Cardápio de sabores de pizza
-- -----------------------------------------------------------------------------
INSERT INTO sabores (nome, descricao, categoria_id, preco_base, disponivel) VALUES
    -- Tradicionais (cat 1)
    ('Margherita',              'Molho de tomate, mussarela fresca e manjericão',          1, 39.90, 1),
    ('Calabresa',               'Calabresa fatiada, cebola, azeitona e mussarela',         1, 42.90, 1),
    ('Portuguesa',              'Presunto, ovo, cebola, azeitona e pimentão',              1, 44.90, 1),
    ('Mussarela',               'Mussarela especial, orégano e molho de tomate',           1, 38.90, 1),
    ('Frango com Catupiry',     'Frango desfiado temperado com Catupiry cremoso',           1, 46.90, 1),
    ('Napolitana',              'Tomate fresco, mussarela, manjericão e alho',             1, 41.90, 1),
    -- Especiais (cat 2)
    ('Quatro Queijos',          'Mussarela, parmesão, gorgonzola e provolone',             2, 54.90, 1),
    ('Pepperoni',               'Generosa camada de pepperoni com mussarela especial',     2, 52.90, 1),
    ('Carne Seca',              'Carne seca desfiada, catupiry e cebola caramelizada',     2, 56.90, 1),
    ('Camarão',                 'Camarão salteado, catupiry e requeijão',                  2, 64.90, 1),
    ('Costela BBQ',             'Costela desfiada, molho barbecue e cebola crispy',        2, 58.90, 1),
    -- Doces (cat 3)
    ('Chocolate com Morango',   'Chocolate ao leite derretido com morangos frescos',       3, 48.90, 1),
    ('Nutella com Banana',      'Nutella generosa com bananas caramelizadas',              3, 52.90, 1),
    ('Prestígio',               'Chocolate com coco ralado e leite condensado',            3, 46.90, 1),
    ('Romeu e Julieta',         'Requeijão cremoso com goiabada',                          3, 44.90, 1);


-- -----------------------------------------------------------------------------
-- produtos: Bebidas, sobremesas e porções
-- -----------------------------------------------------------------------------
INSERT INTO produtos (nome, descricao, categoria_id, preco, estoque, disponivel) VALUES
    -- Bebidas (cat 4)
    ('Coca-Cola 2L',            'Refrigerante Coca-Cola 2 litros',                4, 12.00, 999, 1),
    ('Coca-Cola Lata 350ml',    'Refrigerante Coca-Cola lata gelada',              4,  6.00, 999, 1),
    ('Guaraná Antarctica 2L',   'Refrigerante Guaraná Antarctica 2 litros',        4, 10.00, 999, 1),
    ('Água Mineral 500ml',      'Água mineral sem gás',                            4,  4.00, 999, 1),
    ('Suco de Laranja 500ml',   'Suco natural de laranja',                         4,  9.00,  50, 1),
    -- Sobremesas (cat 5)
    ('Petit Gateau',            'Bolinho de chocolate quente com sorvete',         5, 18.00,  20, 1),
    ('Brownie com Sorvete',     'Brownie caseiro com sorvete de baunilha',         5, 16.00,  20, 1),
    -- Porções (cat 6)
    ('Batata Frita Grande',     'Batata frita crocante, porção grande',            6, 22.00, 999, 1),
    ('Frango Frito',            'Pedaços de frango empanado e frito',              6, 28.00, 999, 1);


-- -----------------------------------------------------------------------------
-- cupons: Cupons de desconto iniciais
-- -----------------------------------------------------------------------------
INSERT INTO cupons (codigo, tipo, valor, valor_minimo, validade, usos_maximos, ativo) VALUES
    ('BEMVINDO10',   'percentual', 10.00,   0.00, DATE_ADD(CURDATE(), INTERVAL 180 DAY), 200, 1),
    ('FIDELIDADE15', 'percentual', 15.00,  80.00, DATE_ADD(CURDATE(), INTERVAL 180 DAY), 150, 1),
    ('PROMO20',      'fixo',       20.00, 100.00, DATE_ADD(CURDATE(), INTERVAL 180 DAY), 100, 1),
    ('ANIVERSARIO',  'percentual', 20.00,   0.00, DATE_ADD(CURDATE(), INTERVAL 180 DAY),  50, 1),
    ('PRIMEIRA5',    'fixo',        5.00,  40.00, DATE_ADD(CURDATE(), INTERVAL 180 DAY), 500, 1);


-- =============================================================================
-- STAR SCHEMA — Views para camada analítica
-- =============================================================================
-- Estas views transformam o modelo operacional em star schema
-- sem necessidade de ETL separado. Conectar diretamente via SQLAlchemy.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- dim_clientes: Dimensão de clientes com atributos analíticos
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW dim_clientes AS
SELECT
    c.id                                                    AS cliente_id,
    c.nome,
    c.email,
    c.telefone,
    c.data_nascimento,
    TIMESTAMPDIFF(YEAR, c.data_nascimento, CURDATE())       AS idade,
    CASE
        WHEN TIMESTAMPDIFF(YEAR, c.data_nascimento, CURDATE()) < 25  THEN '18-24'
        WHEN TIMESTAMPDIFF(YEAR, c.data_nascimento, CURDATE()) < 35  THEN '25-34'
        WHEN TIMESTAMPDIFF(YEAR, c.data_nascimento, CURDATE()) < 45  THEN '35-44'
        WHEN TIMESTAMPDIFF(YEAR, c.data_nascimento, CURDATE()) < 55  THEN '45-54'
        ELSE '55+'
    END                                                     AS faixa_etaria,
    c.ativo,
    c.created_at                                            AS cadastrado_em,
    DATE_FORMAT(c.created_at, '%Y-%m')                      AS mes_cadastro,
    YEAR(c.created_at)                                      AS ano_cadastro
FROM clientes c;


-- -----------------------------------------------------------------------------
-- dim_produtos: Dimensão unificada de sabores e produtos avulsos
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW dim_produtos AS
SELECT
    CONCAT('sabor_', s.id)  AS produto_key,       -- chave surrogate única
    'pizza'                 AS tipo_produto,
    s.id                    AS produto_id,
    s.nome,
    s.descricao,
    cat.nome                AS categoria,
    s.preco_base            AS preco,
    s.disponivel,
    s.created_at
FROM sabores s
JOIN categorias cat ON s.categoria_id = cat.id

UNION ALL

SELECT
    CONCAT('produto_', p.id) AS produto_key,
    'avulso'                 AS tipo_produto,
    p.id                     AS produto_id,
    p.nome,
    p.descricao,
    cat.nome                 AS categoria,
    p.preco,
    p.disponivel,
    p.created_at
FROM produtos p
JOIN categorias cat ON p.categoria_id = cat.id;


-- -----------------------------------------------------------------------------
-- fato_pedidos: Tabela fato com todas as métricas calculadas por pedido
-- Esta é a view central para o Power BI e análises no Jupyter
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW fato_pedidos AS
SELECT
    -- Chaves
    p.id                                                AS pedido_id,
    p.cliente_id,
    p.endereco_id,
    p.cupom_id,

    -- Dimensão temporal
    p.created_at                                        AS data_pedido,
    DATE(p.created_at)                                  AS data,
    DATE_FORMAT(p.created_at, '%Y-%m')                  AS ano_mes,
    YEAR(p.created_at)                                  AS ano,
    MONTH(p.created_at)                                 AS mes,
    WEEK(p.created_at, 1)                               AS semana_iso,
    DAYOFWEEK(p.created_at)                             AS dia_semana_num,  -- 1=Dom, 7=Sáb
    DAYNAME(p.created_at)                               AS dia_semana_nome,
    HOUR(p.created_at)                                  AS hora_pedido,

    -- Métricas financeiras
    p.subtotal,
    p.desconto,
    p.total,
    p.forma_pagamento,
    p.troco_para,
    CASE WHEN p.cupom_id IS NOT NULL THEN 1 ELSE 0 END  AS usou_cupom,

    -- Status
    p.status,
    CASE WHEN p.status = 'cancelado' THEN 1 ELSE 0 END  AS foi_cancelado,
    CASE WHEN p.status = 'entregue'  THEN 1 ELSE 0 END  AS foi_entregue,

    -- Avaliação
    av.nota                                             AS nota_avaliacao,
    CASE
        WHEN av.nota >= 4  THEN 'promotor'
        WHEN av.nota = 3   THEN 'neutro'
        WHEN av.nota <= 2  THEN 'detrator'
        ELSE 'sem_avaliacao'
    END                                                 AS nps_categoria,

    -- Métricas de SLA (em minutos) — análise de eficiência operacional
    TIMESTAMPDIFF(MINUTE, p.recebido_em, p.em_producao_em)      AS min_espera_producao,
    TIMESTAMPDIFF(MINUTE, p.em_producao_em, p.saiu_entrega_em)  AS min_tempo_producao,
    TIMESTAMPDIFF(MINUTE, p.saiu_entrega_em, p.entregue_em)     AS min_tempo_entrega,
    TIMESTAMPDIFF(MINUTE, p.recebido_em, p.entregue_em)         AS min_ciclo_total,

    -- Timestamps individuais de status
    p.recebido_em,
    p.em_producao_em,
    p.saiu_entrega_em,
    p.entregue_em,
    p.cancelado_em,

    -- Quantidade de itens no pedido
    (SELECT COUNT(*) FROM itens_pedido ip WHERE ip.pedido_id = p.id) AS qtd_itens

FROM pedidos p
LEFT JOIN avaliacoes av ON av.pedido_id = p.id;


SET FOREIGN_KEY_CHECKS = 1;

-- =============================================================================
-- FIM DO SCHEMA
-- =============================================================================
-- Próximos passos:
--   1. Executar este script: mysql -u root -p pizzaria < schema_pizzaria.sql
--   2. Rodar o script Faker (faker_seed.py) para popular 6 meses de dados
--   3. Conectar via SQLAlchemy: create_engine('mysql+pymysql://user:pass@host/pizzaria')
--   4. Jupyter Notebook com queries analíticas usando as views de star schema
-- =============================================================================
