# Mainuan Instalador Flatpak 1.0

Versão final preparada localmente para publicação. Estas são as notas propostas;
a preparação não cria tag nem publica release.

O Mainuan Instalador Flatpak oferece uma interface Qt 6/Kirigami para abrir
arquivos `.flatpakref` e gerenciar o aplicativo correspondente:

- Integração com a abertura de `.flatpakref` pelo gerenciador de arquivos.
- Instalação apenas para o usuário ou para todo o sistema.
- Nome amigável e resumo separados em uma janela compacta, com detalhes recolhidos.
- Reconhecimento da referência instalada ao reabrir o arquivo.
- Abertura e desinstalação da cópia selecionada, com confirmação antes de remover.
- Preservação dos dados pessoais na remoção, sem remover origens ou fazer limpeza
  global de runtimes.
- Autorização das origens necessárias pelo clique em Instalar, mantendo validações
  de URL, identidade e assinatura; cancelamento cooperativo e diagnóstico em detalhes.

A interface executa sem privilégios elevados. A autorização de operações de
sistema respeita a política efetiva do Flatpak/Polkit; não se força uma nova senha
nem se alteram regras globais.

O usuário informou que a RC1 foi testada novamente em VM e manteve o comportamento
esperado. O visual e o fluxo foram aprovados. A versão 1.0 preserva o código
funcional e o QML aprovados, com promoção de versão e atualização documental.

## Entrada e argumentos públicos

A entrada suportada é **um arquivo .flatpakref local por janela**. IDs e URLs
avulsos estão fora do escopo do produto e são rejeitados com erro claro; não são
pendências de lançamento.

```sh
mainuan-flatpak-install-gui "/caminho/app.flatpakref"
mainuan-flatpak-install-gui --scope system "/caminho/app.flatpakref"
mainuan-flatpak-install-gui --remove --scope user "/caminho/app.flatpakref"
mainuan-flatpak-install-gui --override-appname="Nome apresentado" "/caminho/app.flatpakref"
mainuan-flatpak-install-gui --demo progress
```

Sem arquivo, abre um seletor gráfico. `--scope` aceita `user`, `system` ou
`system:ID`. Remoção exige destino explícito e mantém confirmação gráfica.
`--override-appname` altera somente texto de apresentação, nunca identidade.
`--demo` é isolado, sem operações reais. `--help` descreve a CLI.
O comando `flatpak-install-gui` continua como alias. Os helpers internos antigos
`--fetch-dependencies` e `--do-install` foram descontinuados com erro explícito.

## Instalação e integração

Anexo proposto para a release: `mainuan-flatpak-install-gui_1.0_all.deb`, acompanhado
de seu arquivo SHA-256. O pacote declara as dependências Qt/Kirigami/libflatpak e
substitui o pacote legado, sem YAD ou tiger-shell-osd.

O registro de suporte MIME não define sozinho o aplicativo padrão. A distribuição
pode integrar o fragmento `mainuan-mimeapps.list`; as preferências pessoais têm
precedência. Para definir e verificar na conta gráfica:

```sh
xdg-mime default mainuan-flatpak-install-gui.desktop application/vnd.flatpak.ref
xdg-mime query default application/vnd.flatpak.ref
```

Atribuições Mainuan Welcome/GPLv3 e a licença MIT histórica do projeto de origem
foram preservadas. Resultados da validação e comparação do pacote com a RC1:
[versao-1.0.md](versao-1.0.md).
