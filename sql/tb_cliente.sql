CREATE TABLE IF NOT EXISTS tb_cliente (
    codigo       INT,
    razao        VARCHAR(255),
    nome         VARCHAR(255),
    cnpjcpf      VARCHAR(20),
    ativo        BOOLEAN,
    codvendedor  INT,
    cidade       VARCHAR(100),
    cep          VARCHAR(10),
    uf           VARCHAR(2),
    datacadastro DATE,
    idemp        INT,
    idcliente    VARCHAR(20) NOT NULL PRIMARY KEY
);
