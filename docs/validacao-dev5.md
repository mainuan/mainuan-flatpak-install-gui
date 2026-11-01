# dev5 — nome, resumo e apresentação compacta

29/10/2026. Alterações em `/home/daigo/Github/flatpak-install-gui`, branch
`port/qt6-mainuan`, preservando o trabalho local. Sem commit, push, tag ou release.
Nenhum aplicativo real instalado/removido, origem adicionada ou política alterada.
A cópia de Mainuan Store do ambiente atual não foi modificada.

## Causa confirmada para GIMP

A consulta somente de leitura ao catálogo AppStream local encontrou:

- ID: `org.gimp.GIMP`.
- `name` sem idioma: `GNU Image Manipulation Program`.
- `name` pt-BR: `Programa de manipulação de imagem do GNU`.
- `summary` sem idioma: `High-end image creation and manipulation`.

O GIMP já presente no host também expõe o nome expandido em
`InstalledRef.get_appdata_name()` e no campo **Name** de seu arquivo desktop:
`Name=GNU Image Manipulation Program`, `Name[pt_BR]=Programa de manipulação de
imagem do GNU`. O problema não era concatenação QML nem troca acidental por
Comment: esses próprios metadados de nome contêm a expansão. Em dev4 o nome
localizado era aceito integralmente; até uma correção apenas no AppStream seria
insuficiente se o desktop instalado voltasse a sobrescrevê-la com a expansão.

## Seleção dos campos

O resultado de apresentação agora contém `name` e `description` independentes,
desde o leitor de metadados, pelo worker e controlador, até o QML.

- Nomes de várias palavras continuam válidos. Para siglas do ID conhecidas,
  prefere-se a sigla **apenas** quando as iniciais das palavras do nome expandido
  sem tradução correspondem exatamente ao último componente alfabético e em
  maiúsculas do ID. `GNU Image Manipulation Program` corresponde a `GIMP`.
  O mesmo critério genérico cobre, por exemplo, `Rapid Text Editor` e `RTE`.
  Não existe tabela de exceções nem condicional visual para GIMP.
- O mesmo critério se aplica ao Name do desktop da implantação exata, incluindo
  Name localizado, evitando que ele sobrescreva um nome curto por uma expansão.
  GenericName e Comment nunca são usados como nome principal.
- Descrição usa o resumo AppStream localizado. Na ausência de resumo, quando o
  nome é uma expansão reconhecida, pode usar a expansão original em inglês, por
  exemplo `GNU Image Manipulation Program`. No fallback de desktop, Comment
  pode fornecer descrição, sempre separado do título.
- O catálogo local consultado não oferece resumo pt-BR para GIMP, por isso é
  correto apresentar o resumo original em inglês. Os testes incluem resumo pt-BR
  para validar a seleção localizada quando disponível.
- Scribe continua `Scribe`, com `Markdown editor with live rendering` abaixo.
  A regra restrita dev4 para `ID from origem` e o fallback offline permanecem.
- Metadata é texto simples e continua sendo lida no worker, sem acesso de rede.
  Os bytes do .flatpakref, ID, branch, arquitetura, instalação e referência das
  operações continuam intactos. As transações não foram alteradas.

## Janela e detalhes

O cabeçalho destaca o nome; abaixo há uma linha menor e discreta para a descrição,
com quebra de texto. Sem descrição, esse item fica invisível e sai do layout.
A mensagem redundante `Escolha onde instalar.` foi removida. Mensagens reais de
progresso, erro, resultado e estado instalado continuam disponíveis.

Origem, URL e aviso `Será adicionada se necessária ao instalar.` ficam **somente
em Ver detalhes**, recolhido inicialmente. Não há nova confirmação de origem;
o clique Instalar continua autorizando as origens necessárias com as validações
anteriores. Escolhas genuinamente ambíguas continuam com seu fluxo existente.

A largura inicial visa 520 pixels lógicos, limitada à área útil; a altura acompanha
o conteúdo, com limite na área disponível da tela. A preparação usual ficou em
aproximadamente 520×312 no tema Basic e 520×264 no Breeze, variando com fonte/tema.
Não há conversão para pixels físicos nem alteração do escalonamento do Qt.

Detalhes acrescentam espaço limitado e têm rolagem própria; conteúdo muito longo
rola no corpo principal. O rodapé mantém os botões acessíveis à direita e pode
usar duas colunas em larguras/fontes que não comportem uma só linha. A rolagem
acompanha o foco por teclado para não deixar controles focados fora da área visível.
A decoração normal do Plasma foi mantida. Funciona também em 640×480.

## Validação executada

**70 testes passaram, sem skips**, incluindo os anteriores e novas regressões:
GIMP localizado com título curto e resumo separado; fallback com expansão inglesa
correta; regra de siglas genérica e restrita; Scribe com/sem resumo; Name, GenericName
e Comment distintos; desktop instalado expandido; apresentação integrada de
AppStream e desktop; transmissão de ambos os campos pelo worker sem mutações.

Consulta real de leitura dos metadados locais retornou:

```text
org.gimp.GIMP {'name': 'GIMP', 'description': 'High-end image creation and manipulation'} app/org.gimp.GIMP/x86_64/stable
io.github.gnacho.Scribe {'name': 'Scribe', 'description': 'Markdown editor with live rendering'} app/io.github.gnacho.Scribe/x86_64/stable
```

QML real com driver simulado:

- Fluxos existentes em 640×480: arquivo, seleção por teclado, destinos, instalar
  sem pergunta extra, origem ambígua, erro, resultado e confirmação de remoção.
- Janela compacta para GIMP e Scribe, nome/resumo separados, descrição ausente,
  origem oculta antes de expandir, origem/aviso presentes somente nos detalhes.
- Detalhes expandidos, fechamento, fonte ampliada, descrições longas e rolagem.
- Escalas Qt **125%, 150% e 200%**, claro e escuro em offscreen/Basic.
- **200% com fonte adicionalmente ampliada em 40%**: rodapé dentro da janela,
  quebra dos botões e foco por teclado visível com rolagem.
- Wayland/Breeze na sessão real, com decoração padrão, driver simulado e tema
  escuro da sessão. Há o aviso KDE já existente `QSettings::value: Empty key passed`,
  sem erro QML nem falha dos testes.
- Capturas claras, escuras, detalhes e fonte grande inspecionadas visualmente.

Logs e capturas em `test-artifacts/dev5-*`. Reprodução:

```sh
GI_TYPELIB_PATH=/tmp/mainuan-qt6-deps/root/usr/lib/x86_64-linux-gnu/girepository-1.0 \
PYTHONPATH=/tmp/mainuan-qt6-deps/python \
/usr/bin/python3 -m unittest discover -s tests -v
QT_QPA_PLATFORM=offscreen QT_QUICK_CONTROLS_STYLE=Basic \
PYTHONPATH=/tmp/mainuan-qt6-deps/python \
/usr/bin/python3 tests/qml_presentation.py --output test-artifacts/dev5-light
# Repetir com QT_SCALE_FACTOR=1.25, 1.5, 2 e --dark.
# Teste adicional: QT_SCALE_FACTOR=2 e --large-font.
# Wayland: QT_QPA_PLATFORM=wayland, QT_QUICK_CONTROLS_STYLE=org.kde.breeze.
./build.sh
lintian --tag-display-limit 0 dist/mainuan-flatpak-install-gui_0.1.0~dev5_all.deb
```

## Pacote e limite da validação

Novo pacote `dist/mainuan-flatpak-install-gui_0.1.0~dev5_all.deb`, com SHA-256 ao
lado. Construção sem root, lintian, controle/conteúdo do .deb e diff sem erros de
espaçamento conferidos. Dependências de teste continuam extraídas em
`/tmp/mainuan-qt6-deps`, sem instalação no host.

As operações reais já foram validadas pelo usuário na VM nas rodadas anteriores.
Nesta rodada, transações foram simuladas; não se afirma nova instalação/remoção
real nem nova validação humana de escalas em VM. Na VM: abrir GIMP e Scribe,
conferir título/resumo, expandir detalhes, repetir claro/escuro e escalas e manter
o roteiro funcional anterior. Não é necessário mudar associação MIME nem Polkit.
