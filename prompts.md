# prompts.md · Prompts usados em Differentiated Problem Solving

A página 22 do desafio pede que os prompts fiquem registrados em um arquivo `prompts.md`. Este arquivo lista os pedidos feitos ao **Claude Code** (Anthropic) na parte de Differentiated Problem Solving do **Olho na Via**, na ordem em que aconteceram.

Os pedidos estão transcritos como foram enviados; só corrigi a digitação e abreviei os caminhos dos arquivos.

## Papel da IA

A IA foi usada como copiloto. A ideia do projeto, o documento-base e a escolha do problema vieram antes, no sumário executivo. A partir deles, pedi à IA que comparasse a proposta com o conteúdo das aulas e implementasse a análise no mesmo padrão dos notebooks da disciplina. Cada número do relatório é gerado pelo `app.py` e conferido por um segundo caminho (veja a seção Validações do [README](README.md)), e sei explicar cada etapa do cálculo.

## Análise da proposta, aplicação e relatório

> Analise os conteúdos de referência dados em aula que estão em `differentiated-problem-solving/referencias/` e analise para ver se faz sentido a proposta para a matéria de Differentiated Problem Solving. Após isso, implemente a aplicação em `app.ipynb` e `app.py` seguindo os mesmos conteúdos e padrões de código dados em aula, e então crie um relatório técnico em PDF (.pdf) contendo descrição do problema, modelo, análises de cálculo e interpretação dos resultados, siga a mesma identidade visual do sumário executivo.
>
> O conceito da atividade é: Aplicação de cálculo diferencial e integral (limites, derivadas e taxas de variação, e integrais para grandezas acumuladas) na resolução de problemas urbanos e sociais, utilizando Python ou GeoGebra para modelar e analisar soluções do desafio CitizenTech.
> E o objetivo é: Demonstrar proficiência no uso de limites, derivadas e integrais para modelar um fenômeno urbano real, analisar comportamentos extremos, taxas de variação e acumulações, subsidiando tecnicamente um protótipo CitizenTech.

**Resultado:**

- **Revisão da proposta.** A comparação com as aulas mostrou que o modelo do documento-base, A(t) = A₀e^(kt) com k = 0,10 por dia, não tinha dado real por trás. Ele foi trocado por modelos ajustados por mínimos quadrados aos pedidos de tapa-buraco do SP156, e o crescimento do dano ficou só como cenário (seção 1.1 do relatório). A escolha dos ônibus por cobertura, um problema de otimização combinatória, foi deixada para a disciplina de Python.
- **Dados.** Os microdados oficiais vieram do Portal de Dados Abertos da Prefeitura, e o `preparar_dados.py` gerou as três bases de `dados/`.
- **Análise.** O notebook e o script trazem as três análises (demanda, fila e espera).
- **Relatório.** O relatório técnico em PDF segue a identidade visual do sumário executivo.

## Qualidade do código

> Corrija os erros e warnings de linting do `app.py`.

> Corrija do `preparar_dados.py` também.

**Resultado:** os dois arquivos ficaram sem avisos do linter, com funções documentadas e nomes em português.

## Ajustes da entrega

> Irei excluir a pasta `differentiated-problem-solving/referencias/`, tire as citações dela em `prompts.md`.

> Remova a citação do `prompts.md`, irei excluir ele também. Esse arquivo só é pedido em outras matérias.

> Remova a citação do uso de inteligência artificial no relatório técnico.

> Tire também.

> Na entrega para o professor, eu posso remover o arquivo `preparar_dados.py`?

**Resultado:** a pasta de referências das aulas saiu da entrega, e o relatório e o notebook deixaram de citar o `prompts.md` da época. O `preparar_dados.py` foi mantido, porque é ele que mostra de onde vieram as bases de `dados/`.

## README, este arquivo e revisão

Depois, ao revisar as entregas contra o desafio, vi que a página 21 pede a Ficha da CitizenTech no início do README de todos os repositórios, e a página 22 pede o `prompts.md`. Por isso este arquivo voltou.

> Certo, agora gere um README.md e prompts.md para a matéria de differentiated-problem-solving. Além disso, faça a revisão dele de acordo com o PDF do desafio também, faça apontamentos caso houver e sugestões de melhoria para ficar um trabalho mais completinho.

**Resultado:**

- **README.** Tem a ficha, as três perguntas, os entregáveis, os oito gráficos com a leitura de cada um, as decisões para o protótipo, como rodar, a origem dos dados, as validações e as limitações.
- **Este arquivo.**
- **Revisão.** A lista de apontamentos sobre a entrega.
