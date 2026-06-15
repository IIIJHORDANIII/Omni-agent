# Habilidade: Coding (Desenvolvimento de Elite)

Use esta habilidade quando for solicitado a escrever, refatorar ou implementar novas funcionalidades de código.

## Processo Obrigatório
1. **Análise de Contexto:** Leia os arquivos relacionados e entenda as dependências.
2. **Plano de Implementação:** Descreva o que será feito antes de escrever o código.
3. **Escrita Cirúrgica:** Faça alterações mínimas e necessárias, seguindo o padrão do projeto.
4. **Auto-Revisão:** Verifique se há erros de sintaxe ou lógica.
5. **Verificação:** Execute os testes se disponíveis.

## Tabela Anti-Racionalização
| Desculpa Comum | Resposta Obrigatória |
| :--- | :--- |
| "É uma mudança pequena, não precisa de teste." | "Toda mudança em produção exige validação ou teste unitário." |
| "Vou limpar o código depois." | "Código limpo se escreve na primeira passagem. Não acumule dívida técnica." |

## Sinais Vermelhos (Red Flags)
- Uso de `any` ou tipos genéricos onde tipos específicos são possíveis.
- Comentários que explicam "o que" o código faz em vez de "por que".
- Funções com mais de 50 linhas.

## Verificação Final
- O código compila?
- Segue os padrões PEP8/Airbnb/Google do projeto?
- A funcionalidade foi testada empiricamente?
