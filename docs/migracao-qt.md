> Registro histórico dev2. Para execução, compatibilidade e validação atuais, consulte [candidata-rc1.md](candidata-rc1.md) e o README.

# Mainuan Instalador Flatpak — Qt 6, desenvolvimento dev2

Branch `port/qt6-mainuan`, pacote/comando `mainuan-flatpak-install-gui`, versão
`0.1.0~dev2`. O comando `flatpak-install-gui` entra na mesma aplicação Qt.
O pacote antigo em Bash foi substituído. Não há YAD, Zenity, tiger-shell-osd,
terminal externo, parsing da CLI, sudoers ou interface executada como root.

## Fluxo atual

Ao abrir um arquivo por argumento ou duplo clique, ele é carregado sem seletor.
A janela mostra aplicativo, ícone do tema quando disponível, origem discreta,
**Apenas seu usuário** (marcado inicialmente), **Todo o sistema** e os botões
**Instalar** e **Cancelar**. Sem arquivo, oferece **Escolher arquivo**; após uma
seleção não mostra botão para trocar o arquivo. Arquivo inválido mostra erro,
detalhes recolhidos e **Fechar**.

O clique em **Instalar** autoriza a resolução e instalação do aplicativo
identificado e de suas dependências necessárias, no destino escolhido e com a
origem informada. A resolução acontece internamente com **Preparando instalação…**.
As operações ficam em **Ver detalhes**, sem segunda confirmação rotineira.
Destino e cliques repetidos são bloqueados ao iniciar; o destino não muda como
resposta a um erro. A janela apresenta progresso e resultado, com **Abrir/Fechar**
no sucesso e **Tentar novamente/Fechar** em falhas ou cancelamento apropriados.
Os botões permanecem no rodapé, visíveis mesmo quando o corpo precisa rolar.

Antes do clique, um trabalhador consulta as instalações de usuário e sistema e
informa os destinos onde o aplicativo já existe. Se a referência exata já estiver
no destino selecionado, não reinstala: verifica a instalação e oferece abrir.
Se existir apenas outra cópia (outro destino, branch ou arquitetura), pede
confirmação antes de criar uma cópia adicional. Não muda a seleção do usuário.

## Confirmações excepcionais e identidade das origens

Uma origem nova exige **Adicionar e instalar / Cancelar**, com a mensagem:
“Para instalar este aplicativo, é necessário adicionar esta origem.”
Nome e endereço aparecem na confirmação curta; chave e informação de confiança
ficam nos detalhes. O RuntimeRepo é obtido e validado antes de adicionar origens,
para agrupar origens novas já conhecidas. Descritores compatíveis da mesma URL
são combinados. Uma origem descoberta depois exige consentimento antes da
mutação; propostas equivalentes já autorizadas na mesma operação não repetem
perguntas. Rejeitar interrompe como **cancelamento**, sem erro técnico.

A correspondência considera URL exata, verificação GPG, identidades primárias das
chaves quando fornecidas, CollectionID quando declarado, filtros, disponibilidade,
branch padrão quando declarado e demais propriedades de comportamento/prioridade.
OSTree/GPG lê as chaves fornecidas em repositório temporário descartável e lê as
chaves configuradas; não importa chaves no chaveiro pessoal para compará-las.
Não se usa o nome do remote para inferir identidade. Nomes iguais com URLs
diferentes não são correspondências; não há sobrescrita de origem.

Aliases cuja identidade e configuração pertinentes são idênticas são resolvidos
automaticamente. Provedores de dependência únicos também não geram pergunta.
Somente configurações compatíveis mas realmente distintas exigem escolha de
origem; nenhuma opção vem autorizada implicitamente. Configuração conflitante
(chave diferente, filtro, origem desativada, mudança durante a instalação etc.)
interrompe com mensagem compreensível, sem escolher outra origem silenciosamente.
Para chaves explicitamente fornecidas, a política é conservadora: o conjunto de
identidades primárias deve corresponder; rotação/configuração divergente exige
conferência externa. Sem chave no descritor, mantém a confiança já configurada.

Adicionar uma origem é uma alteração persistente autorizada. HTTPS protege o
transporte, não certifica a confiabilidade de uma origem. Origens autorizadas e
operações concluídas podem permanecer após cancelamento; não se promete rollback.

## Controles internos e arquitetura

- `metadata.py`: arquivo regular de até 1 MiB, parser estrito, bytes/campos
  imutáveis, URLs HTTPS e dados exibidos como texto simples. Não executa conteúdo.
  Ícones só vêm de nomes no tema local; URLs de ícone não são baixadas.
- `backend.py`: intenção de instalação, decisões sincronizadas, agrupamento de
  origens, prevenção de cópias involuntárias e callbacks protegidos.
- `flatpak_backend.py`: libflatpak/PyGObject e OSTree, trabalho fora da interface,
  resolução, Gio.Cancellable, progresso e verificação da referência instalada.
- `controller.py`: sinais/propriedades Qt, inspeção prévia sem rede/instalação,
  um trabalhador por vez e espera por `QThread.finished` ao fechar.
- `Main.qml`: janela decorada Qt Quick/Kirigami, destino por radio buttons,
  detalhes recolhidos, rodapé fixo, foco de teclado e tema claro/escuro.
- `demo.py`: estados fictícios; não importa nem cria o driver real.

`ready-pre-auth` e `ready` permanecem como pontos reais de veto. Ambos validam a
lista de operações, referência/branch/arquitetura e identidade/configuração das
origens. Instalação/atualização do aplicativo escolhido e seus runtimes são
permitidas pelo clique inicial. Outro aplicativo ou remoção não autorizada é
vetado; rebases e instalação automática de autenticadores não são implementados.
Mudanças de commits das dependências passam por nova validação interna, sem
confirmação rotineira da lista. A aplicação não usa `add_install_flatpakref`,
pois seu caminho interno pode criar remotes sem emitir a confirmação esperada;
usa adição explícita autorizada de origem e `Transaction.add_install`.

O sistema corresponde à instalação padrão do Flatpak. Runtimes já instalados no
sistema podem ser reutilizados na instalação de usuário, pelos mecanismos de
fontes de dependência da biblioteca, sem mudar o destino da operação.
Flatpak/Polkit cuidam da autorização; o programa é executado como usuário normal.

Progresso de uma operação aparece como **Etapa atual**, e a barra total fica
indeterminada. Sucesso/100% só após `run()` retornar com êxito e a referência ser
confirmada no destino/branch/arquitetura/origem esperados. Abrir usa
`Installation.launch`, com identidade verificada, sem shell.

Cancelar usa `Gio.Cancellable`, acorda decisões pendentes e aguarda o trabalhador.
Fechar pela decoração faz o mesmo antes de encerrar a janela. O HTTP do
RuntimeRepo usa HTTPS, limite de tamanho e timeout de I/O de 15 segundos; durante
essa leitura, o cancelamento pode aguardar o retorno/timeout da rede.

## Dependências, execução e pacote

Na VM Mainuan/Kubuntu 26.04:

```sh
sudo apt install python3 python3-gi python3-pyqt6 python3-pyqt6.qtqml \
  python3-pyqt6.qtquick gir1.2-flatpak-1.0 gir1.2-ostree-1.0 flatpak \
  qml6-module-qtquick qml6-module-qtquick-window qml6-module-qtquick-controls \
  qml6-module-qtquick-dialogs qml6-module-qtquick-layouts \
  qml6-module-qtqml-workerscript qml6-module-org-kde-kirigami
./mainuan-flatpak-install-gui
./mainuan-flatpak-install-gui "/caminho com espaços/aplicativo.flatpakref"
./mainuan-flatpak-install-gui --demo progress
./build.sh
```

Estados demonstrativos: `ready`, `remote`, `progress`, `success`, `error`,
`cancelled`. A demonstração é incapaz de instalar, adicionar origens ou abrir apps.

`./build.sh` constrói sem root e sem permissões 777:
`dist/mainuan-flatpak-install-gui_0.1.0~dev2_all.deb`. O pacote contém aplicação Qt,
wrappers, documentação/manuais e desktop com `%f`, para um arquivo por processo.
`Provides/Conflicts/Replaces: flatpak-install-gui` trata o pacote antigo. Não há
scripts que alterem preferências MIME pessoais. A construção não instala o pacote.

Os argumentos antigos `--remove`, `--override-appname`, `--fetch-dependencies` e
`--do-install` **não estão implementados**: saem com erro explícito. IDs/URLs da
CLI, vários arquivos, remotes privados com login, autenticadores, opções avançadas
desconhecidas e instalações de sistema personalizadas também não são suportados.
Nunca há encaminhamento silencioso para o Bash antigo.

## Testes e roteiro de VM

```sh
/usr/bin/python3 -m unittest discover -s tests -v
QT_QPA_PLATFORM=offscreen QT_QUICK_CONTROLS_STYLE=Basic /usr/bin/python3 tests/qml_flow.py
QT_QPA_PLATFORM=offscreen QT_QUICK_CONTROLS_STYLE=Basic /usr/bin/python3 tests/qml_flow.py --dark
/usr/bin/python3 tests/qml_smoke.py --dark
lintian --tag-display-limit 0 dist/mainuan-flatpak-install-gui_0.1.0~dev2_all.deb
```

Na VM, após snapshot, copiar o pacote e executar:

```sh
sudo apt install ./mainuan-flatpak-install-gui_0.1.0~dev2_all.deb
mainuan-flatpak-install-gui "/home/teste/Downloads/aplicativo com espaços.flatpakref"
```

1. Com origem configurada: abrir por duplo clique, conferir usuário selecionado e
   sistema visível; clicar Instalar uma vez. Não deve haver confirmação de lista
   ou de origem. Conferir `flatpak --user info APP_ID` e Abrir.
2. Sem origem: conferir nome/endereço e aceitar/rejeitar **Adicionar e instalar**.
   Testar RuntimeRepo distinto e origem descoberta depois. A rejeição deve cancelar
   sem instalar e sem apresentar erro técnico.
3. Repetir no sistema com Polkit ativo; aceitar, negar e cancelar autorização.
   Conferir `flatpak --system info APP_ID`; a aplicação não deve mudar o destino.
4. Aplicativo já instalado no mesmo destino: indicar existente, sem reinstalação.
   Somente no outro destino: informar e impedir cópia adicional sem confirmação.
5. Conferir colisão de nome/URL diferente, chave divergente, aliases idênticos e
   múltiplos provedores diferentes. Nenhuma substituição silenciosa é aceitável.
6. Cancelar na confirmação, durante download e pela decoração. Aguardar parada
   segura; conferir o que persistiu. Repetir clique não deve criar outra operação.
7. Sem arquivo: escolher um; depois não poder trocá-lo. Referência inválida:
   mensagem compreensível e Fechar. Testar rede indisponível e nova tentativa.
8. Claro/escuro, Wayland, 640×480, Tab/Shift+Tab/Espaço e leitor de tela; testar
   também escalas fracionárias e 200% no Plasma real.

Visual segue Welcome `qml/components/InstallDialog.qml` e `qml/Main.qml` (GPLv3).
Atribuições/licenças estão preservadas. API conferida na introspecção instalada
Flatpak 1.16.6/OSTree 2025.7. Ver [validação dev2](validacao-dev2.md) para os testes
executados e suas limitações; instalação integral e Polkit continuam para VM.
