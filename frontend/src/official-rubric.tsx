import { useEffect, useState } from 'react';
import { api, ApiError } from './api';
import { Notice } from './components';

export type Descriptors = { exemplar: string; competente: string; necessita_trabalho: string };
export type Concept = { chave: keyof Descriptors; nome: string; minimo: string; maximo: string };
type OfficialCriterion = {
  nome: string;
  descricao: string;
  peso: string;
  descritores: Descriptors;
};
type OfficialRubricData = {
  nome: string;
  aprovacao_minima: string;
  tempo_apresentacao: { tcc1: number; tcc2: number };
  conceitos: Concept[];
  componentes: { chave: string; nome: string; pontos: string; criterios: OfficialCriterion[] }[];
};

export const decimal = (value: string | number) =>
  Number(value).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 2 });

export const conceptBand = (concept: Concept) =>
  `${concept.nome}: notas de ${decimal(concept.minimo)} a ${decimal(concept.maximo)}`;

/** UC08 (somente leitura): a rubrica oficial da disciplina é fixa e não parametrizável. */
export function OfficialRubric({ onSessionEnded }: { onSessionEnded: (message: string) => void }) {
  const [rubric, setRubric] = useState<OfficialRubricData>();
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    api
      .request<OfficialRubricData>('/rubrica-oficial', { signal: controller.signal }, true)
      .then(({ body }) => {
        if (!controller.signal.aborted) setRubric(body.data);
      })
      .catch((cause) => {
        if (controller.signal.aborted) return;
        if (cause instanceof ApiError && cause.status === 401) onSessionEnded(cause.message);
        else setError('Não foi possível carregar a rubrica oficial.');
      });
    return () => controller.abort();
  }, []);

  if (error) return <Notice message={error} />;
  if (!rubric) return <p role="status">Carregando a rubrica oficial…</p>;
  return (
    <div className="official-rubric">
      <h3>{rubric.nome}</h3>
      <p>
        Rubrica fixa da disciplina, aplicada automaticamente a todas as bancas. Em cada critério, o
        avaliador marca um conceito e atribui a nota dentro da faixa correspondente. A nota
        ponderada é nota × peso ÷ 10, e a nota do avaliador é a soma das ponderadas (0 a 10). A
        média final é a média das notas do orientador e dos dois avaliadores. Média maior ou igual a{' '}
        {decimal(rubric.aprovacao_minima)} aprova.
      </p>
      <p>
        Tempo regimental de apresentação: TCC 1, {rubric.tempo_apresentacao.tcc1} min; TCC 2,{' '}
        {rubric.tempo_apresentacao.tcc2} min.
      </p>
      <ul className="concept-bands">
        {rubric.conceitos.map((concept) => (
          <li key={concept.chave}>{conceptBand(concept)}</li>
        ))}
      </ul>
      {rubric.componentes.map((component) => (
        <section key={component.chave}>
          <h4>
            {component.nome} ({decimal(component.pontos)} pontos)
          </h4>
          <div className="rubric-table-wrap">
            <table className="rubric-table">
              <thead>
                <tr>
                  <th scope="col">Critério</th>
                  {rubric.conceitos.map((concept) => (
                    <th scope="col" key={concept.chave}>
                      {concept.nome}
                      <small>
                        {decimal(concept.minimo)} a {decimal(concept.maximo)}
                      </small>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {component.criterios.map((criterion) => (
                  <tr key={criterion.nome}>
                    <th scope="row">
                      {criterion.nome}
                      {criterion.descricao && <small>{criterion.descricao}</small>}
                      <small>Peso {decimal(criterion.peso)}</small>
                    </th>
                    {rubric.conceitos.map((concept) => (
                      <td key={concept.chave}>{criterion.descritores[concept.chave]}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ))}
    </div>
  );
}
