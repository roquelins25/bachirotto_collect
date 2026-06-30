CREATE TABLE IF NOT EXISTS tb_categoriaFinanceira (
    codigo       INT,
    descricao    VARCHAR(255),
    tipo         VARCHAR(10),
    grupo        VARCHAR(100),
    idemp        INT,
    idcodfin     VARCHAR(20) NOT NULL PRIMARY KEY
);
