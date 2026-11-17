<div align="center">

<img src="https://raw.githubusercontent.com/mainuan/.github/main/profile/assets/mainuan-logo.svg" width="96" alt="Logotipo do Mainuan">

# Mainuan Instalador Flatpak

Instala, abre e remove o aplicativo descrito num arquivo `.flatpakref` local, com um clique.

[![CI](https://github.com/mainuan/mainuan-flatpak-install-gui/actions/workflows/ci.yml/badge.svg)](https://github.com/mainuan/mainuan-flatpak-install-gui/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/mainuan/mainuan-flatpak-install-gui)](https://github.com/mainuan/mainuan-flatpak-install-gui/releases/latest)
[![Licença](https://img.shields.io/github/license/mainuan/mainuan-flatpak-install-gui)](LICENSE)
![Plataforma](https://img.shields.io/badge/Kubuntu%2026.04%20%7C%20Plasma%206.6-0079c1)

**Português** · [English](README.en.md)

</div>

---

## O que é

O Mainuan Instalador Flatpak é o programa que abre quando se clica num arquivo
`.flatpakref` no Dolphin. Ele mostra o nome e o resumo do aplicativo, deixa
escolher entre **Apenas seu usuário** e **Todo o sistema** e instala com o
botão **Instalar**. Origem, operações e diagnóstico ficam em **Ver detalhes**,
recolhido no início.

A interface é Qt 6 Quick/QML com Kirigami, escrita em Python (PyQt6), e usa a
libflatpak pelo PyGObject. Ela **não roda como root**: o Flatpak e o agente
Polkit da sessão cuidam da autorização, e a senha depende da política em vigor.
O programa não altera regras globais.

## Funcionalidades

- Abre um arquivo `.flatpakref` local por janela, inclusive por associação MIME (`application/vnd.flatpak.ref`) e com caminhos com espaços.
- Instala para o usuário ou para todo o sistema; o clique em **Instalar** autoriza adicionar as origens que o arquivo e as dependências declaram.
- Valida antes de instalar:
  - URLs só em HTTPS, sem credenciais nem fragmento;
  - origem com verificação GPG ativa e chave fornecida; uma origem já existente com URL, coleção ou chave diferente interrompe a operação;
  - arquivo `.flatpakref` de até 1 MiB.
- Ao reabrir, consulta as instalações de usuário e de sistema; se a referência exata já está no destino escolhido, oferece **Abrir**, **Desinstalar** e **Fechar**.
- Remoção com confirmação, que preserva os dados pessoais e não remove origens nem faz limpeza global de runtimes.
- Cancelamento das operações em andamento.
- Janela compacta, com rolagem e escala nativa do Qt.
- Interface traduzida em 33 idiomas, que segue o idioma do KDE Plasma.

IDs e URLs avulsos estão fora do escopo e são recusados com uma mensagem clara.

## Instalação

O instalador já vem na ISO do Mainuan Linux, associado aos arquivos `.flatpakref`.

Em outro sistema Kubuntu/Ubuntu 26.04, baixe o `.deb` e o `SHA256SUMS` da
[última release](https://github.com/mainuan/mainuan-flatpak-install-gui/releases/latest),
confira e instale:

```bash
sha256sum --check --ignore-missing SHA256SUMS
sudo apt install ./mainuan-flatpak-install-gui_1.1_all.deb
```

O pacote fornece, conflita e substitui o pacote legado `flatpak-install-gui` e
não inclui YAD nem tiger-shell-osd.

## Uso

Dê dois cliques num `.flatpakref` ou execute, na sessão gráfica e como usuário comum:

```sh
mainuan-flatpak-install-gui "/caminho com espaços/aplicativo.flatpakref"
mainuan-flatpak-install-gui --scope system "/caminho/app.flatpakref"
mainuan-flatpak-install-gui --remove --scope user "/caminho/app.flatpakref"
mainuan-flatpak-install-gui --override-appname="Nome apresentado" "/caminho/app.flatpakref"
mainuan-flatpak-install-gui --demo progress
```

| Opção | Efeito |
|---|---|
| `REFERÊNCIA` | arquivo `.flatpakref` local |
| `--scope user\|system\|system:ID` | destino da operação; obrigatório com `--remove` |
| `--remove` | remove a referência exata, com confirmação gráfica |
| `--override-appname NOME` | texto simples exibido como nome; não muda identidade, branch, arquitetura nem destino |
| `--demo [ready\|remote\|progress\|success\|error\|cancelled]` | demonstração visual isolada: não instala, não remove e não abre aplicativos |
| `-h`, `--help` | ajuda |

`flatpak-install-gui` continua como comando de compatibilidade e repassa os
argumentos. Os antigos auxiliares internos do Bash `--fetch-dependencies` e
`--do-install` foram descontinuados e saem com erro, sem executar nada
([inventário de chamadas](docs/candidata-rc1.md)). Página de manual:
`man mainuan-flatpak-install-gui`.

A entrada `.desktop` tem `NoDisplay=true`: fica fora do menu, mas atende à
associação MIME. O pacote não define o aplicativo padrão; o fragmento
`mainuan-mimeapps.list` é mesclado pela imagem do Mainuan. Detalhes em
[docs/integracao-mime.md](docs/integracao-mime.md).

## Informações técnicas

| Item | Valor |
|---|---|
| Linguagem | Python 3 e QML |
| Toolkit | Qt 6 Quick (PyQt6) e Kirigami |
| Flatpak | libflatpak ≥ 1.16 via PyGObject (`gir1.2-flatpak-1.0`) |
| Base | Kubuntu 26.04 LTS, KDE Plasma 6.6 |
| Pacote | `mainuan-flatpak-install-gui`, `Architecture: all` |
| Privilégios | nenhum; autorização pelo Flatpak/Polkit |
| Arquitetura do sistema | amd64 |
| Arquivos instalados | `/usr/bin/mainuan-flatpak-install-gui`, `/usr/bin/flatpak-install-gui`, `/usr/share/mainuan-flatpak-install-gui/` |

## Compilação e testes

```bash
git clone https://github.com/mainuan/mainuan-flatpak-install-gui.git
cd mainuan-flatpak-install-gui
sudo apt build-dep ./
dpkg-buildpackage -us -uc -b      # executa também python3 -m unittest discover -s tests -v
```

O build não precisa de root; a versão vem de `debian/changelog`. Os testes de
transação usam simulação e repositórios temporários e não instalam nem removem
aplicativos reais.

Além do build, o [CI](.github/workflows/ci.yml) executa:

```bash
po/i18n.sh check-pot
po/i18n.sh validate
QT_QUICK_CONTROLS_STYLE=Basic python3 tests/qml_flow.py --output artifacts/flow
QT_QUICK_CONTROLS_STYLE=Basic python3 tests/qml_presentation.py --output artifacts/presentation
```

e confere a **reprodutibilidade**: compila o pacote duas vezes, em caminhos
diferentes, e exige `.deb` idênticos byte a byte. Depois vêm `lintian`,
`SHA256SUMS`, instalação, reinstalação e remoção num Ubuntu 26.04 limpo e um
teste de fumaça que valida o `.desktop`, o `--help` em inglês e português e
abre a janela real em modo de demonstração. A release só é publicada por uma
tag `v*`.

O teste opcional `tests/package_smoke.py <pacote.deb>` executa o pacote
extraído num namespace privado (`bwrap`), sem instalá-lo no sistema. Histórico
da validação: [docs/versao-1.0.md](docs/versao-1.0.md).

## Traduções

Catálogo gettext único para Python e QML (domínio
`mainuan-flatpak-install-gui`, textos-fonte em inglês), em 33 idiomas listados
em `po/LINGUAS`; o `.desktop` é traduzido com `msgfmt --desktop`. Como
contribuir: [docs/i18n/README.md](docs/i18n/README.md).

## Contribuição

Relate problemas em [Issues](https://github.com/mainuan/mainuan-flatpak-install-gui/issues)
e envie mudanças por pull request para `main`. O
[CI](https://github.com/mainuan/mainuan-flatpak-install-gui/actions/workflows/ci.yml)
precisa estar verde.

## Créditos

- Daigo ([@daigoasuka](https://github.com/daigoasuka)): migração para Qt 6/Kirigami e versão 1.0.
- Rafael Ruscher ([@ruscher](https://github.com/ruscher)): internacionalização, empacotamento Debian e CI.

Origem: **flatpak-install-gui** do Tiger OS (Tiger-OperatingSystem), de
Natanael Barbosa Santos, sob licença MIT, preservada em
[docs/LICENSE-original-MIT](docs/LICENSE-original-MIT). Estrutura visual e
paleta adaptadas do Welcome Mainuan (GPLv3), com atribuição em `qt/Main.qml`.
Notas da versão 1.0: [docs/notas-lancamento-1.0.md](docs/notas-lancamento-1.0.md).

## Licença

[GPL-3.0](LICENSE) (versão 3). O código de origem mantém a licença MIT original
([docs/LICENSE-original-MIT](docs/LICENSE-original-MIT)).
