# Habilidade: Revisão de Pull Request com Criação de Nota

Use esta habilidade quando o usuário solicitar detalhes de um PR específico no GitHub e também pedir para criar uma nota/anotação sobre ele.

## Processo Obrigatório
1. Extrair do comando: repositório, número do PR e confirmação de que também precisa criar nota
2. Executar `github_pr_details` com repositório e PR number
3. Analisar o resultado: título, descrição, arquivos alterados e diff resumido
4. Se falhar (status FAILURE), ainda assim extrair o conteúdo do campo `output` — ele contém os dados reais
5. Com base no output, criar nota com:
   - Título do PR
   - Resumo conciso (máx 3 linhas)
   - Lista de arquivos alterados
   - Link para o PR (construir a partir do repo + PR number)

## Tabela Anti-Racionalização
| Desculpa | Resposta |
|----------|----------|
| "O output veio como FAILURE, não tenho dados" | O output ainda contém a descrição e diff — use o campo `output` literal |
| "Não sei qual ferramenta usar para criar nota" | Use a ferramenta de criação de nota disponível no sistema do OMNI |
| "O PR não tem descrição suficiente" | Extraia do título e dos arquivos alterados — sempre há contexto no diff |

## Verificação Final
- [ ] Extraí o repositório e PR number corretamente
- [ ] Usei o `output` mesmo em caso de FAILURE
- [ ] Criei a nota com título, resumo e arquivos alterados