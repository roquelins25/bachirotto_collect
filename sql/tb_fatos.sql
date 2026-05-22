CREATE TABLE IF NOT EXISTS tb_fatos (
    
    numero                VARCHAR(20),
    data                  DATE,
    emissao               DATE,
    situacao              VARCHAR(50),
    codvendedor           VARCHAR(20),

    totalprodutos         DECIMAL(10,2),
    totalPedido           DECIMAL(10,2),

    cliente_codigo        VARCHAR(20),

    itens_codigoproduto   VARCHAR(20),
    itens_codigooperacao  VARCHAR(20),

    itens_qtd             DECIMAL(10,2),
    itens_unitario        DECIMAL(10,2),
    itens_total           DECIMAL(10,2),

    idEmp                 INT,

    idcodcli              VARCHAR(50),
    idcodpro              VARCHAR(50),
    idcodop               VARCHAR(50),
    idcodrep              VARCHAR(50)
);