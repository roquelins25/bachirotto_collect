CREATE TABLE IF NOT EXISTS tb_caixaBanco (
    tipo                   VARCHAR(1),
    historico              TEXT,
    numdoc                 VARCHAR(50),
    categoriafinanceira    VARCHAR(200),
    codcategoriafinanceira VARCHAR(20),
    lancamento             DATE,
    movimento              DATE,
    valor                  DECIMAL(15,2),
    valorcorrigido         DECIMAL(15,2),
    codbanco               VARCHAR(10),
    idemp                  INT,
    idcodcategoria         VARCHAR(20)
);
