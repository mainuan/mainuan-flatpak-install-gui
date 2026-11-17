# Integração MIME

O desktop instalado é `mainuan-flatpak-install-gui.desktop`, com suporte a
`application/vnd.flatpak.ref`, `%f` e caminhos com espaços. `NoDisplay=true`
oculta a entrada do menu; não impede a abertura por associação MIME. O pacote
atualiza o desktop database, sem escrever na home dos usuários.

## O suporte MIME não define o padrão

O fragmento `/usr/share/mainuan-flatpak-install-gui/mainuan-mimeapps.list`
deve ser mesclado pelo pacote de configuração/imagem Mainuan na seção
`[Default Applications]` de `/etc/xdg/kde-mimeapps.list` (Plasma) ou
`/etc/xdg/mimeapps.list` (geral), preservando outras entradas. Preferências
pessoais têm precedência. Este fragmento sozinho não é consultado
automaticamente pelo Dolphin.

## Escolher o instalador numa conta

Na conta normal (por exemplo, na VM de teste), para escolher explicitamente o
instalador:

```sh
xdg-mime default mainuan-flatpak-install-gui.desktop application/vnd.flatpak.ref
kbuildsycoca6 --noincremental
xdg-mime query default application/vnd.flatpak.ref
```

A consulta deve retornar `mainuan-flatpak-install-gui.desktop`. Scripts root
do pacote não alteram preferências pessoais nem executam caches da sessão do
usuário.
