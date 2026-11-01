# Registro histórico de validação — dev1 — 29/10/2026

Este registro descreve a primeira rodada. O fluxo atual e os testes da versão
dev2 estão em [validacao-dev2.md](validacao-dev2.md).

## Ambiente e inspeção

Diretório inicialmente limpo, branch `main` em `8d16e41`, remote `origin` apontando
para Tiger-OperatingSystem/flatpak-install-gui. Nenhum AGENTS.md aplicável foi
encontrado no repositório ou nos diretórios ancestrais. A branch preliminar foi
buscada do destino via HTTPS e aberta como `port/qt6-mainuan`, base `dd73ed2`.
Não houve reset, clean, descarte de alterações, commit, push, merge, tag ou release.

Host Mainuan 2026 LTS, Ubuntu resolute, sessão Wayland, usuário normal:
Python 3.14.4, PyQt6 6.10.2, Qt 6.10.2, libflatpak/Flatpak 1.16.6,
PyGObject 3.56.2 e Kirigami 6.24.0. `lintian` e ferramentas QML estão disponíveis.

Faltavam `python3-pyqt6.qtqml`, `python3-pyqt6.qtquick` e
`gir1.2-flatpak-1.0`. Os `.deb` da base Ubuntu configurada foram baixados com
`apt-get download` e extraídos **sem instalação** em `/tmp/mainuan-qt6-deps/root`.
`gir1.2-ostree-1.0` também foi extraído para a inspeção. Um `sitecustomize.py`
temporário estendeu `PyQt6.__path__`; `GI_TYPELIB_PATH` apontou para a pasta
extraída. Isso permitiu executar a aplicação e testes com as bibliotecas reais.
Nenhuma dependência foi instalada no host e o `.deb` produzido não foi instalado.

Para repetir a demonstração neste host enquanto a pasta temporária existir:

```sh
PYTHONPATH=/tmp/mainuan-qt6-deps/python ./mainuan-flatpak-install-gui --demo progress
```

Para repetir a suíte completa:

```sh
GI_TYPELIB_PATH=/tmp/mainuan-qt6-deps/root/usr/lib/x86_64-linux-gnu/girepository-1.0 \
PYTHONPATH=/tmp/mainuan-qt6-deps/python \
/usr/bin/python3 -m unittest discover -s tests -v
```

## Testes simulados e ABI

```sh
/usr/bin/python3 -m unittest discover -s tests -v
/usr/bin/python3 tests/qml_flow.py
```

Executados com as dependências temporárias: **25 testes unitários passaram**,
sem testes pulados. Cobrem validação/malformed, campos obrigatórios, duplicação,
limites, bytes imutáveis, caminhos com espaços, caracteres especiais, consentimento
antes de mutação, rejeição de remote principal e RuntimeRepo, escopos, inventário,
aplicativo existente, mudança de operações, falha de rede/operação/verificação,
negação de autorização/conflito, cancelamento e decisões pendentes, cliques
repetidos, fechamento aguardando QThread e isolamento demonstrativo.

O teste `test_flatpak_api.py` usa tipos/sinais reais de libflatpak, remotes em uma
instalação temporária e emissão controlada do sinal `ready-pre-auth`. Não chama
`Transaction.run()` nem instala aplicativos. Progresso e abertura são simulados;
a abertura confere argumentos reais de `Installation.launch` para usuário/sistema.

`qml_flow.py` carregou QML com o backend simulado, passou um caminho com espaços
e `#` via QUrl, verificou título literal `<b>Exemplo & 100%</b>` como PlainText,
escolheu usuário e percorreu preparação, confirmação acionada por teclado e
resultado. Conferiu o foco dos botões e uma única execução da transação.

## QML e verificações visuais

```sh
/usr/bin/python3 tests/qml_smoke.py --dark
QT_QPA_PLATFORM=offscreen QT_QUICK_CONTROLS_STYLE=Basic \
  /usr/bin/python3 tests/qml_smoke.py
QT_QPA_PLATFORM=offscreen QT_QUICK_CONTROLS_STYLE=Basic QT_SCALE_FACTOR=1.25 \
  /usr/bin/python3 tests/qml_smoke.py --dark
# Repetido com QT_SCALE_FACTOR=1.5 e 2.
```

Com dependências temporárias: seis estados (`ready`, `remote`, `progress`,
`success`, `error`, `cancelled`) carregados e capturados a 640×480 em Wayland
escuro a 100%, e offscreen claro a 100%/escuro a 125%, 150% e 200%. Nenhum erro de
importação, binding ou layout após as correções. O harness confere largura do
conteúdo e ausência de importação do driver real. Capturas ficam em
`test-artifacts/` (artefatos locais ignorados pelo Git).

A barra Breeze da versão disponível gerava erros de padding nulo; a aplicação
usa conteúdo/background próprios na ProgressBar com cores Kirigami. Resta um
diagnóstico do framework KDE em Wayland, `QSettings::value: Empty key passed`,
sem erro QML ou impedimento da execução. `qmllint` carrega os imports, mas avisa
sobre `backend`, uma context property Python conhecida somente em execução.

As capturas foram inspecionadas visualmente. Isso não substitui teste humano em
Plasma com escala fracionária real, leitor de tela, seletores nativos e Polkit.

## Resolução real, sem instalar aplicativos

Foi baixada a referência pública do KCalc de
`https://dl.flathub.org/repo/appstream/org.kde.kcalc.flatpakref`.
O parser leu `org.kde.kcalc`, branch `stable`, chave GPG de 2844 bytes e RuntimeRepo
`https://dl.flathub.org/repo/flathub.flatpakrepo`.

Um driver direcionado a `Installation.new_for_path()` em diretório temporário
executou a política real. O teste aceitou apenas o remote dentro dessa instalação
temporária e rejeitou a confirmação de instalação em `ready-pre-auth`.
A libflatpak resolveu duas operações: `org.kde.kcalc.Locale` e `org.kde.kcalc`,
ambas x86_64/stable; o runtime já disponível foi considerado pela biblioteca.
O resultado foi `cancelled`/`Aborted by user`; a lista final de referências
instaladas na instalação temporária continha **zero itens**. O diretório foi
removido pelo contexto temporário. Não houve alteração de remotes ou aplicativos
nas instalações reais de usuário/sistema do host.

Isso valida resolução real e veto antes da implantação. **Não valida instalação
completa, download/implantação integral, autorização Polkit ou abertura real.**
Esses passos ficam no roteiro de VM em `migracao-qt.md`.

## Pacote

`./build.sh` executado sem root; conteúdo/controle inspecionados com
`dpkg-deb -c` e `dpkg-deb -I`. Dependências conferidas no apt resolute.
`lintian --tag-display-limit 0 dist/*.deb` passou sem apontamentos após correções
de changelog, manuais, copyright e permissões. A validação desktop deve usar o
arquivo extraído com extensão `.desktop`, não o arquivo-fonte chamado `launcher`.
A simulação `apt-get -s install ./dist/mainuan-flatpak-install-gui_0.1.0~dev1_all.deb`
resolveu o pacote e as três dependências ausentes, sem remoções ou instalação real.
O `.desktop` extraído passou em `desktop-file-validate`. A entrada `main.py`
extraída do pacote também executou `--demo progress` em Wayland, abriu uma janela
com o título correto e encerrou com código 0 sem importar o backend real. Como
o pacote não foi instalado, o portal avisou que o app ID não tinha registro
local (`App info not found`); isso não impediu a janela demonstrativa.
Não há pós-instalação que altere associação MIME, dependências antigas, arquivos
com permissão 777 ou aplicação executável como root.

## Pendências

Instalação/desinstalação de apps no host: não executadas. Teste completo em VM,
Polkit, falhas reais de rede durante implantação e abertura real: pendentes.
Desinstalação e argumentos legados de override/auxiliares: não implementados;
falham explicitamente. Remotes privados com login, autenticadores, rebase e
opções avançadas desconhecidas: fora desta primeira versão. Cancelamento durante
HTTP RuntimeRepo pode aguardar I/O/timeout; operações já concluídas não revertem.
