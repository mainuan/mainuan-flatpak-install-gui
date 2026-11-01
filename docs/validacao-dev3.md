# Desenvolvimento dev3 — 29/10/2026

## Local de trabalho e preservação

A cópia indicada inicialmente, `/home/daigo/Github/mainuan-flatpak-install-gui`,
estava limpa na branch `main`, com o Bash antigo. A branch `port/qt6-mainuan`
e as alterações locais Qt estavam em `/home/daigo/Github/flatpak-install-gui`.
Foi nesta última que o trabalho continuou. Nenhum reset, checkout, commit, push,
tag, release, instalação ou remoção de aplicativo real foi executado.
Os documentos dev1/dev2 são registros históricos; este documento descreve dev3.

## Diagnóstico dos seis relatos

1. **Dolphin/Discover:** o desktop Qt já declarava `MimeType=application/vnd.flatpak.ref;`,
   `Exec=mainuan-flatpak-install-gui %f`, `TryExec` correspondente e `NoDisplay=true`.
   `%f` recebe um caminho individual, inclusive com espaços; não se deve envolvê-lo
   em shell. `NoDisplay` oculta a entrada dos menus, sem retirar suporte MIME.
   Faltavam scripts de atualização do desktop database e uma proposta de padrão
   da distribuição. No host, só o desktop Flatpak do Discover está instalado e
   `xdg-mime query default application/vnd.flatpak.ref` retorna
   `org.kde.discover.desktop`. MIME real de fixture `.flatpakref`, inclusive com
   espaços e `#`: `application/vnd.flatpak.ref`. Não recebemos o arquivo nem o
   estado de associações da VM, portanto a causa exata lá depende dessa coleta.
2. **Origem:** `Installer.remote_consent()` emitia `confirmRemote`, bloqueando o
   worker até “Adicionar e instalar”. Agora o clique Instalar autoriza as origens
   do arquivo e RuntimeRepo validado. Nada é adicionado durante a inspeção.
   A tela avisa discretamente que a origem será adicionada se necessária. URLs
   HTTPS, chave GPG válida, assinatura habilitada e identidade são exigidas.
   Chaves/configurações são conferidas novamente em ready-pre-auth/ready.
   Propostas tardias precisam estar vinculadas ao aplicativo e a descritor já
   autorizado; URL desconhecida, conflito ou chave ausente interrompem o fluxo.
   Origens efetivamente adicionadas são registradas nos detalhes. Nenhum remote
   existente é substituído e nomes em conflito não são contornados silenciosamente.
3. **Nome:** o parser usava Title/ID, sem resolução AppStream. Não usava Comment
   diretamente. Sem o arquivo real não é possível afirmar qual campo continha a
   descrição técnica. Agora usa nome localizado AppStream da referência exata
   instalada ou do cache local da origem, depois Title, depois ID. Não faz rede
   nem refresh de AppStream ao abrir; leitura limitada e assíncrona. Falha desses
   metadados opcionais mantém Title/ID, sem impedir abertura. Texto é simples.
   `--override-appname` só muda apresentação; identidade vem do arquivo imutável.
4. **Destino/senha:** o código anterior já encaminhava user/system para
   `Installation.new_user/new_system`. Testes verificam encaminhamento e ausência
   de fallback; foram adicionadas instalações de sistema nomeadas. A conferência
   pós-instalação usa a mesma instalação, ID, arquitetura, branch e origem.
   No host existe `/usr/share/polkit-1/rules.d/org.freedesktop.Flatpak.rules`, que
   retorna YES para instalar/remover/modificar origens quando a sessão é local,
   ativa e pertence a `sudo`; esta conta pertence a `sudo`. Isso comprova uma
   política capaz de dispensar senha neste host, não a decisão histórica da VM.
   A política padrão XML também permite autorização mantida (`auth_admin_keep`).
   Não se alterou regra Polkit, sudoers nem se elevou a interface. Coletar na VM
   regras efetivas, grupos, sessão e logs antes de atribuir a causa a cache,
   política ou destino. `/etc/polkit-1/rules.d` do host não foi acessível sem root.
5. **Reabertura:** a inspeção anterior apenas preenchia `existingNotice`; não
   populava `installed` nem mudava os botões. A consulta assíncrona agora enumera
   usuário e todas as instalações de sistema, descarta caches, distingue branches
   e arquitetura e habilita Já instalado/Abrir/Desinstalar para a cópia exata.
   Outras branches/destinos aparecem no aviso, sem habilitar remoção arbitrária.
   Falhas de consulta são erros. Há nova consulta após instalar/remover/trocar
   destino. Campos ausentes usam branch master e arquitetura padrão libflatpak.
6. **Remoção:** não existia no port Qt; `--remove` era rejeitado. Agora há confirmação
   curta com nome/destino, transação libflatpak cancelável e `add_uninstall` da
   referência exata. Desabilita dependências, relacionados e prune; não solicita
   delete-data, remove origens ou limpa runtimes. Verifica NOT_INSTALLED na mesma
   instalação antes de sucesso. Erro/cancelamento/autorização negada não são sucesso.

## MIME: suporte não significa padrão

O pacote atualiza `/usr/share/applications/mimeinfo.cache` via
`update-desktop-database` em configure/remove. Não fornece um novo tipo MIME:
Flatpak já fornece o XML e os glob patterns; não há motivo para regravar sua base.
KDE observa mudanças no diretório applications; na sessão de teste pode-se executar
`kbuildsycoca6 --noincremental` como o usuário para reconstruir seu cache.
Não executar kbuildsycoca nem escrever na home de usuários em maintainer scripts root.

O pacote inclui `/usr/share/mainuan-flatpak-install-gui/mainuan-mimeapps.list`.
É um **fragmento de integração**, não um arquivo automaticamente consultado pelo
Dolphin. O pacote de configuração/imagem Mainuan deve mesclar a entrada
`application/vnd.flatpak.ref=mainuan-flatpak-install-gui.desktop;` na seção
`[Default Applications]` de `/etc/xdg/kde-mimeapps.list` (Plasma), ou
`/etc/xdg/mimeapps.list` para o padrão geral, preservando as outras entradas.
Não se assume propriedade de arquivos globais pertencentes a outro pacote.
Preferências em XDG_CONFIG_HOME e no kdedefaults pessoal têm precedência.
Instalar este .deb sozinho registra suporte; o padrão da distribuição depende
explicitamente dessa integração. A preferência individual é definida na VM abaixo.

Na **conta normal da VM**, depois de instalar o pacote:

```sh
xdg-mime default mainuan-flatpak-install-gui.desktop application/vnd.flatpak.ref
kbuildsycoca6 --noincremental
xdg-mime query default application/vnd.flatpak.ref
xdg-mime query filetype "/caminho com espaços/aplicativo.flatpakref"
gio mime application/vnd.flatpak.ref
```

A primeira consulta deve retornar `mainuan-flatpak-install-gui.desktop`; a segunda,
`application/vnd.flatpak.ref`. Conferir também o duplo clique real no Dolphin.
O host não teve a associação pessoal modificada. O teste isolado reproduz a
entrada da distribuição, comprova a precedência pessoal, executa o mesmo comando
xdg-mime default, consulta o resultado e lança o desktop via Gio com um gravador
de argumentos inofensivo, preservando um único argumento com espaços e `#`.

## Testes locais e reprodução

55 testes unitários/API/regressão passaram, sem skips. Cobrem parser, nomes,
AppStream ID/branch, destinos sem fallback, ambas as cópias, outra branch,
reabertura, erro de consulta, override só visual, origem após o clique sem pergunta,
conflitos, callback tardio limitado, GPG real em repo temporário, lançamento
exato, remoção exata e verificação de ausência, preservação de dados, falha,
cancelamento e autorização negada. A API real usa apenas repositórios temporários;
`Transaction.run` de instalação/remoção é simulado. Nenhum aplicativo real é alterado.

As dependências GI Flatpak/OSTree e módulos QtQuick/QtQml ausentes no host foram
reutilizados de .debs **extraídos**, sem apt install, em `/tmp/mainuan-qt6-deps`:

```sh
GI_TYPELIB_PATH=/tmp/mainuan-qt6-deps/root/usr/lib/x86_64-linux-gnu/girepository-1.0 \
PYTHONPATH=/tmp/mainuan-qt6-deps/python \
/usr/bin/python3 -m unittest discover -s tests -v
QT_QPA_PLATFORM=offscreen QT_QUICK_CONTROLS_STYLE=Basic \
PYTHONPATH=/tmp/mainuan-qt6-deps/python \
/usr/bin/python3 tests/qml_flow.py --output test-artifacts/dev3-flow-light
# Repetir com --dark; em uma sessão Wayland, QT_QPA_PLATFORM=wayland.
```

QML real com driver simulado passou em offscreen/Basic claro e escuro,
Wayland/Basic claro e Wayland/Breeze com a paleta escura da sessão. Capturas em
`test-artifacts/dev3-*`, 640×480, incluindo origem nova sem pergunta, sucesso,
confirmação de remoção e retorno a Instalar. Capturas claro/escuro inspecionadas.
Breeze acompanha a configuração KDE e pode ignorar a paleta injetada pelo teste;
a combinação Wayland/Basic usa a paleta clara determinística. Há dois avisos do
seletor KDE (`QSettings Empty key` e filtro), sem erros QML nem falha do fluxo.

## Pacote verificado

`./build.sh` gerou `dist/mainuan-flatpak-install-gui_0.1.0~dev3_all.deb` sem root.
`lintian --tag-display-limit 0` passou sem diagnósticos; `dpkg-deb -I/-c`
confirmou versão, dependências, scripts de cache, desktop, fragmento MIME e código.
`apt-get -s install ./dist/mainuan-flatpak-install-gui_0.1.0~dev3_all.deb`
resolveu o pacote e quatro dependências ausentes, sem remoções. `git diff --check`
passou. Logs dos testes em `test-artifacts/dev3-validation`.

## Roteiro curto para VM

1. Instalar `mainuan-flatpak-install-gui_0.1.0~dev3_all.deb` com apt; executar os
   comandos MIME acima na conta gráfica, conferir Exec/MimeType/NoDisplay do
   desktop em `/usr/share/applications` e abrir arquivo com espaços no Dolphin.
2. Escolher **Apenas seu usuário**, clicar **Instalar**. Conferir origem antes do
   clique, ausência de confirmação extra, detalhes e `flatpak --user list --app`.
3. Fechar e reabrir o mesmo arquivo: **Já instalado**, Abrir, Desinstalar, Fechar.
   Abrir; confirmar o aplicativo correto. Criar dado pessoal no app de teste.
4. **Desinstalar**, conferir nome/destino na confirmação e confirmar. Verificar
   ausência da referência apenas no usuário, dados preservados e botão Instalar.
5. Repetir em **Todo o sistema**, consultando `flatpak --system list --app`.
   Coletar autenticação sem exigir nova senha em todo clique. Testar usuário
   comum sem autorização, negar autenticação e cancelar a operação.
6. Manter as duas cópias e alternar destino: Abrir/Desinstalar devem afetar
   somente a seleção; repetir com branch distinta e instalação nomeada.
   CLI equivalente, ainda com confirmação gráfica:
   `mainuan-flatpak-install-gui --remove --scope system "/caminho/app.flatpakref"`.
   Instalação nomeada: `--scope system:ID`. Para outra branch, fornecer um
   `.flatpakref` com a branch exata; não escolher referências por título.
7. Conferir conflito de origem/chave, cancelamento, erro de rede, consulta negada,
   tema claro/escuro e Wayland com interação humana.

Coleta Polkit na VM: `id`, `loginctl show-session "$XDG_SESSION_ID" -p Active -p Remote`,
`pkaction --action-id org.freedesktop.Flatpak.app-install --verbose`, regras
`/usr/share/polkit-1/rules.d` e `/etc/polkit-1/rules.d` e logs
`journalctl -b -u polkit -u flatpak-system-helper`. A leitura de regras protegidas
pode exigir administrador. Não adicionar regras para forçar ou dispensar senha.

Instalação completa, execução de app real, dados reais e autenticação efetiva
continuam **pendentes da VM**. Os testes locais não comprovam esses efeitos.

Referência de API usada na auditoria:
https://docs.flatpak.org/en/latest/libflatpak-api-reference.html
