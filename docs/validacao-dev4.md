# dev4 — nome de apresentação, 29/10/2026

Trabalho na branch `port/qt6-mainuan` da cópia
`/home/daigo/Github/flatpak-install-gui`, preservando as alterações locais.
Sem commit, push, tag, release ou instalação/remoção de aplicativos reais no host.
Os fluxos funcionais validados na VM pelo usuário continuam como base dev3.
Esta mudança se limita à obtenção/apresentação do nome e sua atualização.

## Causa rastreada

O arquivo público atual de Scribe foi consultado em
https://dl.flathub.org/repo/appstream/io.github.gnacho.Scribe.flatpakref .
Campos retornados:

```ini
Name=io.github.gnacho.Scribe
Title=io.github.gnacho.Scribe from flathub
Branch=stable
SuggestRemoteName=flathub
```

A cadeia dev3 era `parse_reference → Reference.title → Controller.view.name →
Main.qml installationTitle`. A QML apenas acrescenta “Instalando ” durante o
progresso; não concatena origem ao nome. O texto técnico vem de Title quando a
resolução AppStream não encontra nome ou falha; não vem de Comment/Description.

A auditoria encontrou outra causa concreta no leitor AppStream: ele carregava o
catálogo completo e descartava qualquer XML descomprimido acima de 32 MiB.
O catálogo real disponível neste host tem cerca de 49 MiB e contém o componente
`io.github.gnacho.Scribe`, `<name>Scribe</name>`, bundle da branch stable. Logo, o
leitor antigo descartava este catálogo apesar de o nome estar disponível.
Não temos a captura do cache da VM para comprovar seu tamanho lá. O Title público
coincide exatamente com o texto relatado; a falha de limite foi reproduzida aqui.

## Correção

- `Reference.title` e os bytes do arquivo continuam intactos. `display_name` é uma
  propriedade separada, usada desde a primeira apresentação, antes do worker.
- Prioridade: nome AppStream localizado da referência instalada exata; seu XML
  comprimido local via `load_appdata`; cache AppStream da origem correspondente;
  Title amigável; último componente do ID preservando a capitalização.
- Title igual ao ID ou **exatamente** `ID conhecido from origem` (origem como um
  único identificador) é técnico. Nenhum corte genérico na palavra “from”.
  `Letters from Home`, `Scribe from flathub` e outros títulos legítimos permanecem
  inteiros. Não há tabela de exceções ou tratamento específico para Scribe.
- `io.github.gnacho.Scribe → Scribe` é um fallback de apresentação, **não** uma
  regra universal para descobrir marcas ou nomes comerciais. AppStream e Title
  amigável têm prioridade e mantêm espaços e capitalização próprios.
- AppStream agora é processado por componentes, liberando os já examinados,
  sem manter o catálogo inteiro em memória. Limite de leitura descomprimida:
  128 MiB, com rejeição de DTD/entidades e verificação cooperativa de cancelamento.
  Mantém correspondência de ID e bundle/arquitetura/branch quando informado.
- Todas as consultas são locais, no worker Qt. Não há rede nem refresh do catálogo
  na aplicação; metadados ausentes, corrompidos ou indisponíveis preservam fallback
  e não impedem operações offline. A consulta HTTP acima foi apenas diagnóstico
  durante o desenvolvimento, não foi adicionada ao aplicativo.
- Após instalar, a atualização de inventário também consulta novamente o nome nos
  metadados instalados. Cabeçalho, progresso, resultado e confirmação de remoção
  consomem o mesmo `view.name`. `--override-appname` continua só visual.
- Origem permanece no campo separado; ID completo fica nos detalhes. ID,
  referência, branch, arquitetura, origem e destino usados pelas operações não
  recebem o nome de apresentação. Nenhuma mudança nas transações de instalar,
  lançar ou remover, políticas de origem, MIME, destino ou Polkit.

## Verificações executadas

**62 testes passaram, sem skips**, incluindo os 55 anteriores e sete regressões:
caso exato relatado; Title amigável e “from” legítimo; AppStream com espaços e
capitalização; catálogo comprimido com mais de 32 MiB; falha/offline; XML dos
metadados instalados; nome antes/depois de instalar e ao reabrir, referência exata
preservada para abrir e confirmar remoção. Testes de transação continuam simulados.

Consulta real somente de leitura ao cache local do host retornou:

```text
Fallback: Scribe
AppStream local real: Scribe
Identidade: app/io.github.gnacho.Scribe/x86_64/stable
```

QML real com backend simulado passou em claro e escuro (offscreen/Basic) e
Wayland/Breeze. O caso Scribe verifica o cabeçalho “Scribe”, progresso “Instalando
Scribe”, resultado “Scribe” e confirmação “Desinstalar Scribe”. Capturas de pronto,
progresso, sucesso e remoção em `test-artifacts/dev4-*`; claro e Wayland escuro
inspecionados visualmente. Os fluxos anteriores de seleção, destino, instalação,
origens ambíguas, erro e remoção também passaram. Permanecem dois avisos do seletor
KDE já presentes em dev3, sem erro QML nem falha de teste.

Comandos de reprodução (dependências extraídas, sem instalar no host):

```sh
GI_TYPELIB_PATH=/tmp/mainuan-qt6-deps/root/usr/lib/x86_64-linux-gnu/girepository-1.0 \
PYTHONPATH=/tmp/mainuan-qt6-deps/python \
/usr/bin/python3 -m unittest discover -s tests -v
QT_QPA_PLATFORM=offscreen QT_QUICK_CONTROLS_STYLE=Basic \
PYTHONPATH=/tmp/mainuan-qt6-deps/python \
/usr/bin/python3 tests/qml_flow.py --output test-artifacts/dev4-light
# Repetir com --dark; Wayland: QT_QPA_PLATFORM=wayland,
# QT_QUICK_CONTROLS_STYLE=org.kde.breeze, em sessão Wayland.
./build.sh
lintian --tag-display-limit 0 dist/mainuan-flatpak-install-gui_0.1.0~dev4_all.deb
```

Logs em `test-artifacts/dev4-validation`. Pacote:
`dist/mainuan-flatpak-install-gui_0.1.0~dev4_all.deb`, com SHA-256 ao lado.
Lintian, conteúdo/controle do .deb e `git diff --check` verificados.

Na VM, repetir com o mesmo arquivo de Scribe: abrir antes da instalação e também
offline, conferir “Scribe” e origem separada; instalar, conferir resultado, fechar
e reabrir, abrir o aplicativo e conferir “Desinstalar Scribe” antes de confirmar.
O usuário já validou os efeitos reais em dev3; não se afirma nova execução real
em VM para dev4. Nenhum aplicativo foi instalado ou removido do host.

API local inspecionada e documentação consultada para o XML instalado comprimido:
https://docs.flatpak.org/en/latest/libflatpak-api-reference.html#flatpak-installed-ref-load-appdata
