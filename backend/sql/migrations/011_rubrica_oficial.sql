-- Official (fixed) TCC rubric: components, concept descriptors and the marked concept per grade.
ALTER TABLE criterio_rubrica ADD COLUMN IF NOT EXISTS componente_criterio_rubrica VARCHAR(20);
ALTER TABLE criterio_rubrica ADD COLUMN IF NOT EXISTS descritores_criterio_rubrica JSONB;
ALTER TABLE criterio_rubrica
    ADD CONSTRAINT ck_criterio_rubrica_componente
        CHECK (componente_criterio_rubrica IS NULL
            OR componente_criterio_rubrica IN ('parte_escrita', 'parte_oral')) NOT VALID;

ALTER TABLE nota_criterio ADD COLUMN IF NOT EXISTS conceito_nota_criterio VARCHAR(20);
ALTER TABLE nota_criterio
    ADD CONSTRAINT ck_nota_criterio_conceito
        CHECK (conceito_nota_criterio IS NULL
            OR conceito_nota_criterio IN ('exemplar', 'competente', 'necessita_trabalho')) NOT VALID,
    ADD CONSTRAINT ck_nota_criterio_maximo CHECK (valor_nota_criterio <= 10) NOT VALID;
