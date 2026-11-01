# Mainuan Instalador Flatpak — candidata 1.0~rc1

29/10/2026. Branch `port/qt6-mainuan`, checkout
`/home/daigo/Github/flatpak-install-gui`. Versão preparada para validação final;
não é uma publicação de 1.0. Não houve commit, push, merge, tag ou release.
Nenhum AGENTS.md aplicável foi encontrado no checkout ou seus ancestrais.
`git status` mostrou o trabalho Qt local, incluindo arquivos novos ainda não
rastreados; ele foi preservado. Não houve reset, troca de branch ou limpeza.

## Base aprovada e revisão final

O usuário aprovou a apresentação dev5 e validou na VM instalação, detecção após
reabertura, abertura e remoção. Cada rodada usa uma **VM nova clonada da imagem
original**. Nenhuma conclusão desta revisão é atribuída a resíduos de versões
anteriores. A validação automatizada local não substitui nova rodada real da RC.

O QML aprovado não foi alterado nesta revisão. SHA-256 de `qt/Main.qml`, igual antes
e depois: `cc802e2b463a32ec58dc00afbabd5847343e64fbc87a5803ecf069283397537b`.

Foram corrigidos problemas concretos:

1. Depois de uma operação retornar, o cancelamento podia já ter sido solicitado
   antes do anúncio de sucesso. Há agora verificação cooperativa antes de emitir
   sucesso de instalação, abertura, remoção ou consulta inicial, incluindo após
   a conferência da implantação. Cancelamento tardio não vira falso sucesso.
2. Um veto de identidade nos callbacks cancela a transação. Antes, se libflatpak
   devolvesse CANCELLED, esse cancelamento podia mascarar o conflito original.
   A classificação agora usa a causa original e preserva a mensagem de erro.
3. O fechamento normal já aguardava o worker, mas saída do event loop ou falha
   ao carregar QML não passavam necessariamente pelo mesmo caminho. O finally de
   main cancela e aguarda o QThread cooperativamente, antes de destruir o QML.
   Não há terminate, kill de transação ou trabalhador abandonado.
4. O destino CLI era aplicado depois de iniciar a consulta. Agora o destino
   inicial acompanha a inspeção desde a criação do worker; `system:default` é
   normalizado para `system`, evitando divergência entre detecção e operação.
5. A mensagem de rejeição dos helpers Bash ainda dizia, incorretamente, que
   remove e override não existiam. Foi corrigida, e IDs avulsos recebem erro
   direto orientando o uso de arquivo local. Demo rejeita combinações de destino,
   arquivo, remoção ou override, inclusive override vazio, e não cria worker ao
   tentar trocar destino. Nenhuma dessas mudanças altera o fluxo gráfico normal.
6. O launcher instalado passou a apontar exclusivamente para
   `/usr/share/mainuan-flatpak-install-gui/qt/main.py`, sem sondar um checkout ao
   lado do executável. O launcher do checkout mantém a conveniência de execução
   local. Ambos os nomes públicos entram no mesmo código Qt.

## Garantias conferidas nos caminhos ativos

- Inspeção faz consultas, não adiciona origens nem instala. Só Instalar inicia a
  política/transação; a confirmação gráfica autoriza remover a referência exata.
- Usuário usa `Installation.new_user`; sistema padrão, `new_system`; sistema
  nomeado, `new_system_with_id`. Falha não seleciona usuário silenciosamente.
- Instalação/verificação usam ID, arquitetura padrão Flatpak, branch e instalação.
  Detecção enumera cópias/branches e atualiza caches. Erro de consulta é erro,
  não “ausente”. Abrir/remover usam a identidade selecionada e caminho conferido.
- Remoção usa `Transaction.add_uninstall` da referência selecionada, sem
  delete-data, remoção de remote ou limpeza global de runtimes; dependências,
  relacionados e prune ficam desabilitados. Sucesso exige NOT_INSTALLED no destino.
- Falha de operação, autenticação negada, falha de verificação e cancelamento não
  anunciam sucesso. Alterações já concluídas podem permanecer após cancelamento.
- Autorizações de origem continuam vinculadas ao aplicativo e descritores
  validados; URLs HTTPS e GPG/identidade são conferidos novamente nos callbacks.
  Não se desativa TLS/GPG nem se substitui origem existente silenciosamente.
- Nome/resumo/override continuam independentes da identidade. Nome e descrição
  são texto simples. Metadados opcionais são locais e assíncronos; não bloqueiam
  a interface ou exigem rede para mostrar o aplicativo.
- A interface permanece sem privilégios elevados. Não foram criadas regras
  Polkit, sudoers ou diálogos próprios de senha.

## Argumentos e consumidores legados

Inventário do Bash em `git show HEAD:flatpak-install-gui`:

| Forma | Estado na RC |
| --- | --- |
| `flatpak-install-gui arquivo.flatpakref` | Alias preservado, mesmos argumentos da aplicação Qt |
| `--override-appname=Nome` ou `--override-appname Nome` | Implementado, inclusive espaços e caracteres de marcação literais; só apresentação |
| `--remove` | Implementado com arquivo local, `--scope user/system/system:ID` e confirmação gráfica |
| ID ou URL avulso para instalar/remover | Não suportado; erro claro, sem adivinhar origem, branch ou destino |
| `--fetch-dependencies` | Helper interno descontinuado; erro 2 antes de importar Qt/backend |
| `--do-install` | Helper interno descontinuado; erro 2 antes de importar Qt/backend |
| Múltiplos arquivos | Rejeitados; desktop recebe um arquivo via `%f` |

Os helpers antigos executavam `flatpak install -y` para sondar dependências,
criavam arquivos laterais e interrompiam processos por PID. Não foram reproduzidos.
O Bash também tinha variáveis/funções internas para seu progresso; não eram API
pública. Opções desconhecidas são rejeitadas pelo parser.

Busca nos projetos locais em `/home/daigo/Github`, incluindo `mainuan-store`,
`welcome`, `skel`, `atualizadorderecursos` e `alerta-atualizacao`, não encontrou
chamadas ativas externas a `flatpak-install-gui` fora deste instalador. Os hits da
Store atual são documentação de referência/arquitetura; seu código ativo não
invoca o executável. A arquitetura prevê libflatpak, mas isso não certifica uma
integração real da Store nesta revisão.

O código histórico consultado em `/tmp/mainuan-old/flatpak_controller.dart`
(linhas 61/75), também descrito em `mainuan-store/docs/references.md`, chamava:

```text
flatpak-install-gui --override-appname="Nome" ID
flatpak-install-gui --override-appname="Nome" --remove ID
```

Essas formas históricas com ID **não são compatíveis**. Um consumidor que ainda
as use precisa fornecer o .flatpakref local e, para remoção, destino explícito.
Não foram modificados outros projetos nem se anuncia compatibilidade total com
consumidores externos ou repositórios não disponíveis localmente.

## Pacote e execução instalada

Artefato: `dist/mainuan-flatpak-install-gui_1.0~rc1_all.deb`, SHA-256 no arquivo
`.deb.sha256` ao lado. Arquitetura `all`: o pacote contém Python/QML/shell e
metadados, sem binários nativos próprios. Os módulos Qt/GI nativos são dependências
Debian, não cópias distribuídas dentro do pacote.

Controle: `Provides/Conflicts/Replaces: flatpak-install-gui`. Pacote/comando
principal `mainuan-flatpak-install-gui`; desktop ID
`mainuan-flatpak-install-gui.desktop`; nome visível **Mainuan Instalador Flatpak**.
Atribuições GPLv3/Mainuan Welcome e licença MIT histórica foram preservadas.
Referências Tiger existem como créditos/registros históricos, não caminhos ativos.
Nenhum Bash antigo, YAD, tiger-shell-osd, cache de testes ou dependência extraída
foi incorporado à implementação ativa.

Os wrappers são 0755; código, QML, desktop e documentação são 0644; maintainer
scripts são 0755. O build usa `--root-owner-group`. O pacote depende de Qt 6,
Kirigami, PyGObject, libflatpak >=1.16, OSTree, flatpak e desktop-file-utils.
Os testes do pacote inspecionam permissões, caminhos ativos e desktop.

`dpkg --compare-versions` confirmou:
`0.1.0~dev5 < 1.0~rc1 < 1.0`.

O teste `tests/package_smoke.py` extrai o .deb e usa `bwrap` com rede isolada e
host somente de leitura. Ele monta os arquivos nos caminhos `/usr/bin` e
`/usr/share` de um namespace privado, executa os dois launchers (`--help` e erro
claro de helper descontinuado) e abre o main/QML instalado em demo, encerrado por
timer de teste, com código 0. Nenhum backend real é importado no demo.

O teste remove PYTHONPATH/GI_TYPELIB_PATH/caminhos QML de desenvolvimento do
ambiente e executa fora do checkout. As dependências Qt ausentes no host são
sobrepostas no namespace em seus caminhos normais de sistema a partir de .debs
extraídos; isso não é instalação no host e não vira requisito do pacote. Em uma
VM com `apt install pacote.deb`, as dependências vêm dos pacotes declarados.
`tempfile` ainda é usado legitimamente para conferir chaves em repo temporário;
não é dependência de artefatos de desenvolvimento em /tmp.

## MIME e Polkit

Instalar o pacote registra suporte a `application/vnd.flatpak.ref` e atualiza o
desktop database. Isso não define automaticamente o aplicativo padrão.
O fragmento `/usr/share/mainuan-flatpak-install-gui/mainuan-mimeapps.list` deve ser
mesclado pelo pacote de configuração da distribuição em
`/etc/xdg/kde-mimeapps.list` ou `/etc/xdg/mimeapps.list`, preservando outras entradas.
Preferências pessoais têm precedência. Não há escrita em homes por scripts root.

Na conta normal da VM:

```sh
xdg-mime default mainuan-flatpak-install-gui.desktop application/vnd.flatpak.ref
kbuildsycoca6 --noincremental
xdg-mime query default application/vnd.flatpak.ref
xdg-mime query filetype "/caminho com espaços/app.flatpakref"
```

Esperado: `mainuan-flatpak-install-gui.desktop` e `application/vnd.flatpak.ref`.
O teste MIME automatizado usa XDG temporário, comprova precedência pessoal,
reconsulta após definir o padrão e lança um gravador de argumentos pelo desktop
com caminho contendo espaços e `#`. Não muda a associação pessoal do host.

Senha depende da política efetiva Polkit, grupos, estado local/ativo da sessão e
autorizações mantidas. A regra do host para Flatpak pode autorizar sessões locais
ativas do grupo sudo sem senha; isso não prova a decisão de uma VM diferente.
Conferir regras, `id`, sessão e logs se necessário. Não forçar senha ou alterar
política global para uniformizar o comportamento.

## Testes e limites

**82 testes automatizados passaram sem skips**, incluindo os 70 de dev5 e as novas
regressões de cancelamento tardio, causa original de callback, encerramento do
worker em decisão pendente, destino inicial, alias de sistema padrão, isolamento
demo, texto/identidade do override e mensagens precisas para CLI descontinuada.
Os testes da API real usam instalações temporárias; instalação/remoção reais de
aplicativos são simuladas.

QML aprovado revalidado em offscreen/Basic claro, Wayland/Breeze escuro e 200% com
fonte aumentada em 40%: teclado, instalação simplificada, seleção ambígua, erro,
remoção confirmada, nome/resumo, detalhes e acessibilidade dos botões. O override
com `<b>`, `&` e texto `$()` permanece literal no cabeçalho/confirmador, sem alterar
ID/branch. A rodada dev5 já validou a matriz 125/150/200% claro/escuro; a QML está
idêntica. Permanecem os avisos KDE de QSettings/filtro nativo, sem erro QML.

Lintian, inspeção de conteúdo/controle do pacote, resolução simulada pelo apt,
ordenação Debian, smoke do pacote extraído e `git diff --check` executados.
Logs/capturas ficam em `test-artifacts/rc1-*` e `test-artifacts/rc1-validation`.
Nenhum pacote foi instalado no host.

Limitações reais: um arquivo local por janela; IDs/URLs avulsos, autenticadores e
rebase automático não suportados; origem inválida/sem chave/conflitante é bloqueada;
propostas tardias sem descritor autorizado são recusadas. Metadados opcionais podem
estar ausentes, usando fallback; siglas não são uma regra universal de marcas.
Cancelamento pode aguardar I/O/timeout da consulta de RuntimeRepo e não desfaz
operações concluídas. Não se promete rollback completo. Leitor de tela, seleção
humana de arquivos e autenticação efetiva devem ser confirmados na VM.

## Roteiro de validação final em VM nova

1. Clonar novamente a imagem original. Instalar a RC com
   `sudo apt install ./mainuan-flatpak-install-gui_1.0~rc1_all.deb`. Conferir versão
   e dependências; definir/reconsultar MIME na conta gráfica, se necessário.
2. Dar duplo clique no .flatpakref, inclusive caminho com espaços. Conferir nome
   curto/resumo, aparência aprovada e origem dentro dos detalhes recolhidos.
3. Escolher **Apenas seu usuário** e **Instalar**: sem confirmação extra de origem.
   Conferir detalhes e `flatpak --user list --app` para ID/arquitetura/branch.
4. Fechar, reabrir o mesmo arquivo: **Já instalado**, **Abrir**, **Desinstalar** e
   **Fechar**. Abrir o app correto, então remover com confirmação. Conferir ausência
   da referência no usuário e dados pessoais/origens preservados; Instalar reaparece.
5. Repetir em **Todo o sistema**, conferindo `flatpak --system list --app` e eventual
   Polkit segundo a política da VM. Com as duas cópias presentes, alternar destino
   e comprovar que Abrir/Desinstalar afetam apenas a cópia selecionada.
6. Conferir cancelamento e fechamento durante operação, erro/autenticação negada,
   GIMP e Scribe, claro/escuro, detalhes expandidos e escala. Testar o comando de
   compatibilidade e override literal. Não atribuir falhas a resíduos de outra
   versão: esta rodada começa de uma VM nova.

A candidata ainda depende desta validação final; nenhuma versão final foi publicada.
