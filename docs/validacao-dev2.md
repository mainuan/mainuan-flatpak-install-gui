# Validação da simplificação — 0.1.0~dev2 — 29/10/2026

## Preservação e ambiente

Mantida a branch `port/qt6-mainuan` e todas as alterações locais da rodada anterior.
Nenhum AGENTS.md aplicável foi encontrado. Não houve reset, clean, commit, push,
tag, merge ou release. O pacote dev1 permanece em `dist/`.

Mesmo host Mainuan/Ubuntu resolute, sessão Wayland, Python 3.14.4,
Qt/PyQt6 6.10.2, libflatpak 1.16.6, PyGObject 3.56.2 e Kirigami 6.24.0.
Continuavam ausentes os módulos Python QML/Quick e as introspecções Flatpak/OSTree.
Os pacotes foram baixados e extraídos em `/tmp/mainuan-qt6-deps`, sem instalação.
Os nomes/versões vieram do apt configurado: `python3-pyqt6.qtqml`,
`python3-pyqt6.qtquick`, `gir1.2-flatpak-1.0` e `gir1.2-ostree-1.0` (2025.7).
A nova dependência OSTree está declarada no `.deb`.

Para repetir no host enquanto essa pasta temporária existir:

```sh
export PYTHONPATH=/tmp/mainuan-qt6-deps/python
export GI_TYPELIB_PATH=/tmp/mainuan-qt6-deps/root/usr/lib/x86_64-linux-gnu/girepository-1.0
/usr/bin/python3 -m unittest discover -s tests -v
QT_QPA_PLATFORM=offscreen QT_QUICK_CONTROLS_STYLE=Basic \
  /usr/bin/python3 tests/qml_flow.py --output test-artifacts/dev2-flow-light
QT_QPA_PLATFORM=offscreen QT_QUICK_CONTROLS_STYLE=Basic \
  /usr/bin/python3 tests/qml_flow.py --dark --output test-artifacts/dev2-flow-dark
QT_QPA_PLATFORM=wayland /usr/bin/python3 tests/qml_flow.py --dark \
  --output test-artifacts/dev2-wayland-flow
./mainuan-flatpak-install-gui --demo progress
```

O `sitecustomize.py` temporário apenas estende `PyQt6.__path__` para os módulos
extraídos. A aplicação instalada na VM não precisa dessas variáveis.

## Testes de backend/controlador/API

**41 testes passaram, sem pulos.** Incluem:

- Arquivo inválido, campos obrigatórios/duplicados, limites, bytes imutáveis,
  caminhos com espaços e títulos com caracteres especiais.
- Origem configurada inequívoca: nenhuma pergunta de origem ou dependências;
  um clique termina a instalação simulada, nos destinos usuário e sistema.
- Origem nova: consentimento precede qualquer adição. Rejeição cancela, não
  apresenta falha técnica e não instala. Origem principal e RuntimeRepo conhecidos
  são agrupados antes de qualquer adição. Propostas equivalentes não se repetem.
- URL diferente com mesmo nome não corresponde; chave/configuração conflitante,
  origem desativada/filtro e mudança entre os sinais de controle são vetadas.
  Aliases idênticos não criam pergunta. Configurações distintas exigem escolha.
- `ready-pre-auth`/`ready` continuam validando identidade, aplicativo e operações.
  Outro app ou remoção não autorizada é vetado. Não existe segunda confirmação
  rotineira de commits/dependências.
- Destino padrão usuário, consulta prévia de instalações existentes, não alterar
  escolha já feita e não criar cópia adicional sem confirmação.
- Cliques repetidos, sucesso/falha/cancelamento, cancelamento de decisão pendente,
  fechamento aguardando trabalhador, progresso por operação e abertura sem shell.

Os testes da API real usam **somente instalações temporárias**, emissão controlada
de sinais e chaves públicas do arquivo de teste do sistema
`/usr/share/keyrings/ubuntu-archive-keyring.gpg`. Nenhum chaveiro pessoal é alterado.
Não chamam `Transaction.run()` real nem instalam aplicativos. Os testes de sucesso,
rede e implantação são simulados; não equivalem a teste de instalação em VM.

## Interface executada e verificação visual

`qml_flow.py` passou em offscreen/Basic claro e escuro e em **Wayland/Breeze**,
sempre a **640×480**. O teste instancia uma aplicação Qt e a janela QML real,
usa backend simulado e percorre os caminhos:

1. Arquivo carregado antes da janela, sem seletor/botão para trocar arquivo.
2. Sem arquivo: abre o seletor gráfico e injeta uma seleção de arquivo de teste;
   depois esconde a entrada de seleção.
3. Dois radio buttons com os textos exatos, usuário marcado inicialmente.
   Tab/Shift+Tab/Espaço mudam o destino sem roubar foco.
4. Instalar por teclado segue direto a sucesso com origem configurada; clique
   repetido não duplica. Operações presentes nos detalhes, recolhidos por padrão.
5. Origem nova mostra **Adicionar e instalar**; cancelar não produz mutações.
6. Ambiguidade começa sem escolha autorizada; botão desabilitado até escolha
   explícita. Sucesso, erro, referência inválida e cancelamento na mesma janela.
7. Botões no rodapé dentro da área de 640×480, incluindo confirmações.

Capturas inspecionadas em `test-artifacts/dev2-flow-light`, `dev2-flow-dark` e
`dev2-wayland-flow`; estados demonstrativos em `dev2-wayland-dark`.
O modo demonstrativo também carregou os seis estados sem importar o backend real.
Capturas offscreen podem não desenhar ícones de tema; em Wayland foram exibidos.
O teste não substitui leitura humana com leitor de tela ou teste de escala real.

Na primeira tentativa Wayland, o seletor de fallback QML do Breeze gerou
`ButtonBackground.qml:19: control.parent` nulo. A inicialização passou a usar
`QApplication`, habilitando o seletor nativo do Plasma; a janela principal continua
Qt Quick/Kirigami. O fluxo Wayland passou após essa correção, sem erros QML.
Restaram diagnósticos de framework: `QSettings::value: Empty key passed` e
`KFileFilterCombo::setCurrentFilter: Could not find file filter`, sem impedir
abertura/seleção e sem erro de binding da aplicação. A aceitação do arquivo é
injetada pelo teste; testar seleção humana no Plasma continua no roteiro de VM.

## Pacote e limites

`./build.sh` executado sem root. Novo pacote:
`dist/mainuan-flatpak-install-gui_0.1.0~dev2_all.deb`.
Conteúdo/controle conferidos por `dpkg-deb`; Qt/Python, desktop `%f`, wrappers,
manuais e documentos incluídos. `desktop-file-validate` no desktop extraído e
`lintian --tag-display-limit 0` passaram após ajustes do changelog.
`apt-get -s install ./dist/mainuan-flatpak-install-gui_0.1.0~dev2_all.deb` resolveu
as quatro dependências ausentes e a aplicação, sem remoções. A aplicação extraída
do pacote abriu `--demo progress` em Wayland com o título correto e saiu com
código 0, sem importar o backend real. O portal avisou `App info not found` porque
o desktop não foi registrado por instalação; isso não impediu a demonstração.

Não houve instalação do pacote ou instalação/remoção de aplicativos reais no host.
Instalação completa, autenticação Polkit, abertura de app real, seleção humana de
arquivo, leitor de tela e escalas reais do Plasma seguem para VM. A resolução
real do KCalc descrita em `validacao-qt.md` pertence à rodada dev1 e não foi
repetida nesta rodada. Desinstalação e argumentos legados continuam pendentes,
com erro explícito. HTTP RuntimeRepo pode aguardar o timeout ao cancelar.
