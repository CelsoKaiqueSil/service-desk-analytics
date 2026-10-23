# Seguranca e dados publicos

Esta e uma demonstracao sintetica, nao um conector de producao homologado.
Nao inclua segredos, dumps, nomes de clientes, contatos ou arquivos operacionais.

- Configuracao externa em variaveis de ambiente; .env nunca entra no Git.
- Exemplos e exports versionados usam apenas a entrada sintetica deste repositorio.
- Capturas privadas nao devem ser publicadas, mesmo com alguns campos borrados.
- Execute `python scripts/check_publication.py` antes de enviar; o scanner e limitado
  e nao substitui revisao humana do conteudo e do historico.
- Se um segredo for publicado, revogue/rotacione primeiro e depois trate o historico;
  apagar somente da ultima revisao nao remove o vazamento.
- A allowlist de API e a trava de arquivo nao substituem privilegios minimos no ambiente.

Relate falhas sem anexar credenciais ou dados pessoais. Para detalhes sensiveis,
use o canal privado de seguranca do GitHub quando disponivel, nao uma issue publica.
