CREATE TABLE IF NOT EXISTS tb_produto (
    codigo       INT,
    referencia   VARCHAR(255),
    descricao    VARCHAR(255),
    unidade      VARCHAR(20),
    ativo        BOOLEAN,
    tipo         INT,
    codcat       VARCHAR(100),
    catdesc      VARCHAR(100),
    xtipo        VARCHAR(50),
    idemp        INT,
    idprod        VARCHAR(20) NOT NULL PRIMARY KEY
);