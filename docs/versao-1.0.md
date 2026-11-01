# Mainuan Instalador Flatpak 1.0 — preparação local

29/10/2026. Branch `port/qt6-mainuan`, checkout
`/home/daigo/Github/flatpak-install-gui`. Versão final preparada localmente para
publicação, sem commit, push, merge, tag ou publicação de release.

## Aprovação e escopo

O usuário informou que a RC1 foi testada novamente em VM e manteve o comportamento
esperado. O visual e o fluxo estão aprovados. Este registro reproduz a aprovação
recebida; não acrescenta aplicativos, cenários, contagens ou resultados de VM.

O escopo aprovado é abrir arquivos **.flatpakref locais**, instalar, reconhecer,
abrir e desinstalar o aplicativo correspondente. IDs e URLs avulsos são fora do
escopo e recebem erro claro, não constituindo pendência da versão 1.0.
Os argumentos públicos estão documentados no README, manuais e
[notas de lançamento](notas-lancamento-1.0.md): arquivo opcional/seletor,
`--scope`, `--remove`, `--override-appname`, `--demo`, `--help` e o alias
`flatpak-install-gui`. Helpers internos Bash continuam descontinuados.

## Alterações da promoção

- `packaging/control` e manuais promovidos de `1.0~rc1` para `1.0`.
- Entrada 1.0 adicionada ao changelog, preservando as entradas anteriores.
- User-Agent de consulta de RuntimeRepo atualizado de versão `1.0-rc1` para `1.0`.
  Essa é a única diferença em um arquivo Python do pacote, exclusivamente metadado.
- README atualizado para versão final local e escopo aprovado.
- Notas de lançamento e este relatório adicionados.
- Ignore ampliado para impedir inclusão acidental de .deb, SHA de pacote e
  configuração local `.vscode/`; os arquivos existentes foram preservados no disco.

Nenhuma funcionalidade, refatoração ou mudança visual foi acrescentada. O QML,
launchers, política de origens, transações, detecção, abertura, remoção e
cancelamento permanecem os aprovados na RC1. Relatórios históricos dev1–dev5,
migração e RC1 foram preservados byte a byte no pacote.

## Artefatos e validação

- Pacote: `dist/mainuan-flatpak-install-gui_1.0_all.deb`.
- SHA: `dist/mainuan-flatpak-install-gui_1.0_all.deb.sha256`.
- Versão interna 1.0, arquitetura all, dependências preservadas.
- `dpkg --compare-versions '1.0~rc1' lt '1.0'` confirmou a ordenação.
- **82 testes passaram, sem skips**, incluindo destinos, referência exata,
  consulta, nomes/resumos, origem, autenticação negada simulada, remoção com dados
  preservados, cancelamento, fechamento do worker, demo, CLI e registro MIME.
- Lintian e `git diff --check` passaram. Controle e conteúdo do pacote inspecionados.
- O smoke do pacote extraído executou os launchers nos caminhos instalados e o
  QML demo em namespace bwrap, sem PYTHONPATH/GI_TYPELIB_PATH de desenvolvimento,
  sem rede e sem importar backend no demo. Dependências Qt ausentes foram
  sobrepostas apenas no namespace, em caminhos normais do sistema.

Comparação do .deb final com `mainuan-flatpak-install-gui_1.0~rc1_all.deb`:

- Todos os arquivos funcionais são idênticos, exceto a string de versão no
  User-Agent de `qt/flatpak_backend.py` descrita acima; comparação normalizada
  dessa única string confirma que o restante do arquivo é idêntico.
- `Main.qml` idêntico, SHA-256
  `cc802e2b463a32ec58dc00afbabd5847343e64fbc87a5803ecf069283397537b`.
- Sem adição/remoção de arquivos ativos, mudança de dependências ou permissões.
- Demais diferenças restritas a README, changelog, manuais, novos documentos e
  campo Version do controle Debian. Timestamps do build não são código funcional.

Logs locais em `test-artifacts/1.0-validation`, incluindo diferenças por arquivo.
Não houve instalação do pacote ou instalação/remoção de aplicativos reais no host.
A suíte automatizada usa simulação/instalações temporárias; a aprovação dos efeitos
reais em VM é a informada pelo usuário para a RC1, não uma execução adicional aqui.

A execução instalada não usa caminhos do checkout, PYTHONPATH de desenvolvimento
ou artefatos de /tmp. Uso transitório de tempfile para conferir chaves é parte
normal do backend, não uma dependência de ambiente de desenvolvimento.

## Publicação preparada

O .deb e o SHA são anexos propostos da release, **não** arquivos de código a
versionar. `dist/`, `test-artifacts/`, caches Python, .deb e seus SHA estão ignorados.
A configuração local `.vscode/` também permanece fora da lista de commit.
Nenhum pacote/cache foi adicionado ao índice Git. Atribuições/licenças preservadas.

Notas propostas: `docs/notas-lancamento-1.0.md`. Nenhum bloqueio concreto encontrado
para esta preparação local. A publicação permanece uma ação futura, não executada.

Arquivos locais prontos para revisão/commit (incluem o trabalho acumulado das
rodadas anteriores, ainda sem commit):

```text
.gitignore
README.md
build.sh
docs/LICENSE-original-MIT
docs/candidata-rc1.md
docs/migracao-qt.md
docs/notas-lancamento-1.0.md
docs/validacao-dev2.md
docs/validacao-dev3.md
docs/validacao-dev4.md
docs/validacao-dev5.md
docs/validacao-qt.md
docs/versao-1.0.md
flatpak-install-gui
launcher
mainuan-flatpak-install-gui
packaging/changelog
packaging/control
packaging/copyright
packaging/flatpak-install-gui.1
packaging/mainuan-flatpak-install-gui
packaging/mainuan-flatpak-install-gui.1
packaging/mainuan-mimeapps.list
packaging/postinst
packaging/postrm
qt/Main.qml
qt/backend.py
qt/controller.py
qt/demo.py
qt/flatpak_backend.py
qt/main.py
qt/metadata.py
tests/package_smoke.py
tests/qml_flow.py
tests/qml_presentation.py
tests/qml_smoke.py
tests/test_arguments.py
tests/test_backend.py
tests/test_controller.py
tests/test_dev3.py
tests/test_flatpak_api.py
tests/test_metadata.py
tests/test_names.py
tests/test_presentation.py
tests/test_rc1.py
```
