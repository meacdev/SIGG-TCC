CREATE OR REPLACE FUNCTION sigg_preservar_ata_reuniao() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'Atas de reunião são registros históricos imutáveis';
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS sigg_ata_reuniao_imutavel ON reuniao_orientacao;
CREATE TRIGGER sigg_ata_reuniao_imutavel
    BEFORE UPDATE OR DELETE ON reuniao_orientacao
    FOR EACH ROW EXECUTE FUNCTION sigg_preservar_ata_reuniao();
DROP TRIGGER IF EXISTS sigg_ata_reuniao_sem_truncate ON reuniao_orientacao;
CREATE TRIGGER sigg_ata_reuniao_sem_truncate
    BEFORE TRUNCATE ON reuniao_orientacao
    FOR EACH STATEMENT EXECUTE FUNCTION sigg_preservar_ata_reuniao();
