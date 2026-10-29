# Migração Qt — etapa 1

Destino: mainuan/mainuan-flatpak-install-gui.
Referência visual: mainuan/welcome, qml/components/InstallDialog.qml.
A interface nova é independente, em Qt 6 Quick e Kirigami, com entrada Python/PyQt6.

Esta etapa é uma prévia isolada. O instalador legado ainda é o instalado por build.sh.
Não distribuir o pacote legado como se fosse a migração concluída.

## Executar a prévia no Mainuan

Dependências: python3-pyqt6, python3-pyqt6.qtquick, qml6-module-qtquick,
qml6-module-qtquick-controls, qml6-module-qtquick-layouts,
qml6-module-org-kde-kirigami e suas dependências.

    python3 qt/main.py --demo progress
    python3 qt/main.py --demo success
    python3 qt/main.py --demo error
    python3 qt/main.py aplicativo.flatpakref
    python3 -m unittest discover -s tests -v

Os botões simulam estados e não executam Flatpak.
A leitura de referências é local, limitada a 64 KiB e não busca URLs.
HTTPS é requisito de entrada, não prova de confiança da origem.

## Próxima etapa obrigatória

Integrar libflatpak em trabalhador assíncrono. Resolver a transação e aguardar
confirmação antes da execução; apresentar origem, escopo e operações.
Solicitar consentimento para novos remotes. Não usar install -y para consultar
dependências. Usar GCancellable e sinais reais de progresso. Distinguir erros,
cancelamento e sucesso confirmado. Autenticação somente pelo mecanismo Flatpak/
Polkit, sem executar a interface como root. Instalação por usuário e sistema
devem ser explícitas. Preservar compatibilidade com o comando antigo.
Implementar remoção, abertura e detecção de instalações existentes.
Depois substituir empacotamento e launcher e adicionar CI de pacote.

## Validação pendente

Qt/Kirigami e libflatpak não estão disponíveis no ambiente inicial de trabalho.
Validar carregamento QML, claro/escuro, Wayland, escalas 100/125/150/200%,
teclado, 640×480 e transações reais em VM antes de uma versão instalável.
