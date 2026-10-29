import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Controls.ApplicationWindow {
    id: window
    visible: true
    width: 580
    height: 460
    minimumWidth: 360
    minimumHeight: 360
    title: "Mainuan Instalador Flatpak"
    property string phase: initialPhase
    property bool finished: ["success", "error", "cancelled"].indexOf(phase) >= 0

    Controls.ScrollView {
        anchors.fill: parent
        anchors.margins: 24
        contentWidth: availableWidth
        ColumnLayout {
            width: parent.width
            spacing: 16
            Controls.Label {
                text: "Prévia visual — nenhuma instalação será executada"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            RowLayout {
                spacing: 14
                Kirigami.Icon {
                    source: phase === "success" ? "dialog-ok-apply"
                          : phase === "error" ? "dialog-error" : "system-software-install"
                    Layout.preferredWidth: 52
                    Layout.preferredHeight: 52
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    Kirigami.Heading {
                        level: 3
                        text: (phase === "progress" ? "Instalando " : "") + appInfo.name
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                    Controls.Label {
                        text: phase === "success" ? "Instalação concluída com sucesso."
                            : phase === "error" ? (initialError || "Não foi possível concluir a instalação.")
                            : phase === "cancelled" ? "Instalação cancelada." : appInfo.id
                        textFormat: Text.PlainText
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }
            }
            Controls.Label {
                text: "Origem: " + appInfo.source
                textFormat: Text.PlainText
                wrapMode: Text.WrapAnywhere
                Layout.fillWidth: true
            }
            Controls.ProgressBar {
                visible: phase === "progress" || phase === "success"
                Layout.fillWidth: true
                from: 0
                to: 100
                value: phase === "success" ? 100 : 42
                Accessible.name: "Progresso da instalação"
            }
            Controls.Label {
                visible: phase === "progress" || phase === "success"
                text: phase === "success" ? "100%" : "42%"
                Layout.alignment: Qt.AlignRight
            }
            Controls.Label {
                visible: phase === "ready"
                text: "Boas-vindas! A confirmação das dependências e a instalação serão integradas na próxima etapa."
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            Controls.Button {
                visible: phase === "error"
                text: details.visible ? "Ocultar detalhes" : "Ver detalhes"
                onClicked: details.visible = !details.visible
            }
            Controls.Label {
                id: details
                visible: false
                text: initialError || "Erro simulado para revisão da interface."
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                Controls.Button {
                    visible: !finished
                    text: phase === "progress" ? "Simular conclusão" : "Simular instalação"
                    highlighted: true
                    onClicked: window.phase = phase === "progress" ? "success" : "progress"
                }
                Controls.Button {
                    visible: phase === "error" && !initialError
                    text: "Tentar novamente"
                    onClicked: window.phase = "progress"
                }
                Controls.Button {
                    text: "Fechar"
                    onClicked: window.close()
                }
            }
        }
    }
}
