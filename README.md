# Mainuan Instalador Flatpak

Versão **1.0**, preparada localmente para publicação, branch `port/qt6-mainuan`. Implementação Qt 6 Quick/QML, Kirigami e libflatpak via PyGObject.

Abre um arquivo `.flatpakref` local, mostra nome e resumo separados, permite
escolher **Apenas seu usuário** ou **Todo o sistema** e oferece **Instalar**.
O clique autoriza instalar e adicionar as origens necessárias declaradas pelo
arquivo/dependências, com validação de identidade, HTTPS e GPG. Origem, operações
e diagnóstico ficam em **Ver detalhes**, recolhido inicialmente.

Ao reabrir, consulta usuário e instalações de sistema. A referência exata no destino
selecionado oferece **Abrir / Desinstalar / Fechar**. Remoção pede confirmação,
preserva os dados pessoais e não remove origens nem limpa runtimes globalmente.
A janela compacta acompanha o conteúdo, com rolagem e escalonamento nativo do Qt.

## Executar

Execute na sessão gráfica como usuário normal. Flatpak e o agente Polkit cuidam
da autorização: senha depende da política efetiva, grupos, sessão e autorizações
mantidas. A interface não roda como root e não altera regras globais.

```sh
mainuan-flatpak-install-gui
mainuan-flatpak-install-gui "/caminho com espaços/aplicativo.flatpakref"
mainuan-flatpak-install-gui --scope system "/caminho/app.flatpakref"
mainuan-flatpak-install-gui --remove --scope user "/caminho/app.flatpakref"
mainuan-flatpak-install-gui --override-appname="Nome apresentado" "/caminho/app.flatpakref"
mainuan-flatpak-install-gui --demo progress
```

No checkout, os mesmos exemplos funcionam com `./mainuan-flatpak-install-gui`.
`--scope` aceita `user`, `system` e `system:ID`; remoção exige destino explícito.
`--override-appname` é texto simples e muda somente a apresentação. Identidade,
branch, arquitetura e destino das operações permanecem independentes do nome.
`--demo` é isolado: não cria worker/backend real nem instala, remove ou lança apps.

## Compatibilidade

`flatpak-install-gui` continua como comando de compatibilidade e encaminha os
argumentos à implementação Qt. O pacote fornece, conflita e substitui o pacote
legado `flatpak-install-gui`; não inclui YAD ou tiger-shell-osd.

O escopo do produto é abrir arquivos **.flatpakref locais** e instalar, reconhecer,
abrir e desinstalar o aplicativo correspondente. IDs ou URLs avulsos estão **fora
do escopo**, recebem erro claro e não constituem pendência da versão 1.0.
`--remove` exige arquivo e destino inequívocos. `--fetch-dependencies` e
`--do-install` eram auxiliares internos inseguros do Bash: foram descontinuados e
saem com erro claro, sem operação. Ver [inventário de chamadas](docs/candidata-rc1.md).
O alias preserva as formas públicas documentadas acima. O inventário histórico
registra formas antigas com ID avulso, sem ampliar o escopo atual do produto.

## Construção e testes

As dependências Debian estão em [packaging/control](packaging/control).
O build não precisa de root. A implementação instalada usa `/usr/share`, sem
checkout, PYTHONPATH de desenvolvimento ou dependências extraídas em `/tmp`.

```sh
./build.sh
/usr/bin/python3 -m unittest discover -s tests -v
QT_QPA_PLATFORM=offscreen QT_QUICK_CONTROLS_STYLE=Basic \
  /usr/bin/python3 tests/qml_flow.py --output test-artifacts/1.0-flow
QT_QPA_PLATFORM=offscreen QT_QUICK_CONTROLS_STYLE=Basic \
  /usr/bin/python3 tests/qml_presentation.py --output test-artifacts/1.0-presentation
lintian --tag-display-limit 0 'dist/mainuan-flatpak-install-gui_1.0_all.deb'
sha256sum 'dist/mainuan-flatpak-install-gui_1.0_all.deb'
```

Execute os testes com as dependências do pacote disponíveis. Os testes de transação
usam simulação e repositórios temporários: não instalam/removem apps reais. O teste
opcional `tests/package_smoke.py pacote.deb` usa `bwrap` para executar o pacote
extraído em namespace privado, sem instalar no host. Detalhes da execução local,
resultados e comparação com a RC1 estão em [versao-1.0.md](docs/versao-1.0.md).

## MIME e distribuição

O desktop real é `mainuan-flatpak-install-gui.desktop`, com suporte a
`application/vnd.flatpak.ref`, `%f` e caminhos com espaços. `NoDisplay=true` oculta
a entrada do menu; não impede a abertura por associação MIME. O pacote atualiza
o desktop database, sem escrever na home dos usuários.

Suporte MIME **não define o padrão**. O fragmento
`/usr/share/mainuan-flatpak-install-gui/mainuan-mimeapps.list` deve ser mesclado pelo
pacote de configuração/imagem Mainuan na seção `[Default Applications]` de
`/etc/xdg/kde-mimeapps.list` (Plasma) ou `/etc/xdg/mimeapps.list` (geral), preservando
outras entradas. Preferências pessoais têm precedência. Este fragmento sozinho
não é consultado automaticamente pelo Dolphin.

Na conta normal da VM, para escolher explicitamente o instalador:

```sh
xdg-mime default mainuan-flatpak-install-gui.desktop application/vnd.flatpak.ref
kbuildsycoca6 --noincremental
xdg-mime query default application/vnd.flatpak.ref
```

A consulta deve retornar `mainuan-flatpak-install-gui.desktop`. Scripts root do
pacote não alteram preferências pessoais nem executam caches da sessão do usuário.

## Licenças e atribuições

Origem histórica: Tiger-OperatingSystem/flatpak-install-gui, Natanael Barbosa
Santos / Tiger OS. Licença original MIT preservada em
[docs/LICENSE-original-MIT](docs/LICENSE-original-MIT); a branch Mainuan usa GPLv3
([LICENSE](LICENSE)). Estrutura visual e paleta adaptadas do Welcome Mainuan,
GPLv3, com atribuição em `qt/Main.qml` e `packaging/copyright`.
O usuário informou que testou novamente a RC1 em VM e que ela manteve o
comportamento esperado; visual e fluxo estão aprovados. A promoção para 1.0
preserva esse código e o QML. Os relatórios dev1–dev5 e da RC permanecem como
registros históricos. Consulte as [notas de lançamento](docs/notas-lancamento-1.0.md).
Nenhuma publicação é realizada pela preparação local desta versão.
