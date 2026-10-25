"""Read-only Core projections over delivery tables in the supplied SQL.

Separate metadata avoids registering a second ORM mapping when document modules merge.
Production never creates these tables; their owning workflows remain responsible for writes.
"""

from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    DateTime,
    MetaData,
    String,
    Table,
    Text,
    func,
    select,
    union_all,
)

metadata = MetaData()
files = Table(
    "arquivo_pdf",
    metadata,
    Column("id_arquivo_pdf", BigInteger, primary_key=True),
    Column("nome_original_arquivo_pdf", String),
    Column("chave_armazenamento_arquivo_pdf", String),
    Column("tamanho_bytes_arquivo_pdf", BigInteger),
    Column("sha256_arquivo_pdf", String),
    Column("id_usuario_envio", BigInteger),
    Column("data_envio_arquivo_pdf", DateTime),
)
finals = Table(
    "entrega_final",
    metadata,
    Column("id_entrega_final", BigInteger, primary_key=True),
    Column("id_etapa_trabalho", BigInteger),
    Column("id_arquivo_pdf", BigInteger),
)
corrections = Table(
    "entrega_correcao",
    metadata,
    Column("id_entrega_correcao", BigInteger, primary_key=True),
    Column("id_solicitacao_correcao", BigInteger),
    Column("id_arquivo_pdf", BigInteger),
)
requests = Table(
    "solicitacao_correcao",
    metadata,
    Column("id_solicitacao_correcao", BigInteger, primary_key=True),
    Column("id_banca", BigInteger),
    Column("descricao_solicitacao_correcao", Text),
    Column("data_limite_reenvio_solicitacao_correcao", Date),
    Column("id_usuario_registro", BigInteger),
)
defenses = Table(
    "banca",
    metadata,
    Column("id_banca", BigInteger, primary_key=True),
    Column("id_etapa_trabalho", BigInteger),
    Column("id_rubrica", BigInteger),
    Column("data_inicio_banca", DateTime),
    Column("data_fim_banca", DateTime),
    Column("local_defesa_banca", Text),
    Column("id_usuario_agendamento", BigInteger),
)
rubrics = Table(
    "rubrica",
    metadata,
    Column("id_rubrica", BigInteger, primary_key=True),
    Column("id_turma", BigInteger),
    Column("nome_rubrica", String),
    Column("id_usuario_criacao", BigInteger),
)


def deliveries(stage_ids):
    final = (
        select(
            finals.c.id_etapa_trabalho.label("stage"), files.c.data_envio_arquivo_pdf.label("sent")
        )
        .select_from(finals.join(files, finals.c.id_arquivo_pdf == files.c.id_arquivo_pdf))
        .where(finals.c.id_etapa_trabalho.in_(stage_ids))
    )
    correction = (
        select(
            defenses.c.id_etapa_trabalho.label("stage"),
            files.c.data_envio_arquivo_pdf.label("sent"),
        )
        .select_from(
            corrections.join(files, corrections.c.id_arquivo_pdf == files.c.id_arquivo_pdf)
            .join(
                requests,
                corrections.c.id_solicitacao_correcao == requests.c.id_solicitacao_correcao,
            )
            .join(defenses, requests.c.id_banca == defenses.c.id_banca)
        )
        .where(defenses.c.id_etapa_trabalho.in_(stage_ids))
    )
    events = union_all(final, correction).subquery()
    return (
        select(events.c.stage, func.max(events.c.sent).label("last_delivery"))
        .group_by(events.c.stage)
        .subquery()
    )
