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
    idcodrep              VARCHAR(50),

    -- FOREIGN KEYS

    CONSTRAINT fk_cliente
        FOREIGN KEY (idcodcli)
        REFERENCES tb_cliente(idcliente),

    CONSTRAINT fk_produto
        FOREIGN KEY (idcodpro)
        REFERENCES tb_produto(idprod),

    CONSTRAINT fk_operacao
        FOREIGN KEY (idcodop)
        REFERENCES tb_operacao(idop),

    CONSTRAINT fk_representante
        FOREIGN KEY (idcodrep)
        REFERENCES tb_representante(idrep)
);