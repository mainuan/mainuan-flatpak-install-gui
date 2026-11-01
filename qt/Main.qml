// Visual reference: Mainuan Welcome, qml/components/InstallDialog.qml (GPL-3.0).
import QtQuick
import QtQuick.Window
import QtQuick.Controls as Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Controls.ApplicationWindow {
    id: window
    objectName: "installerWindow"
    visible: true
    width: Math.max(minimumWidth, Math.min(520, Screen.desktopAvailableWidth - 40))
    height: Math.min(Math.max(260, column.implicitHeight + 40 + actionFooter.implicitHeight),
                     Math.max(260, Screen.desktopAvailableHeight - 80))
    minimumWidth: 360
    minimumHeight: 240
    title: "Mainuan Instalador Flatpak"
    readonly property var state: backend.view
    readonly property string phase: state.phase
    readonly property bool finished: ["success", "error", "cancelled"].indexOf(phase) >= 0
    readonly property bool confirming: ["confirmRemove", "chooseRemote", "confirmDuplicate"].indexOf(phase) >= 0
    readonly property bool dark: Kirigami.Theme.backgroundColor.hslLightness < 0.5
    readonly property color accent: Kirigami.Theme.highlightColor
    readonly property color surface: dark ? "#242a33" : "#ffffff"
    readonly property color elevated: dark ? "#2d3440" : "#f7f8fa"
    readonly property color borderTone: dark ? "#3d4653" : "#d6dbe3"
    readonly property color textTone: dark ? "#f1f4f8" : "#20252d"
    readonly property color muted: dark ? "#aeb8c8" : "#657080"
    readonly property color successTone: dark ? "#7fdda5" : "#258b4b"
    readonly property color errorTone: dark ? "#ff8f87" : "#c0392b"
    palette.window: surface
    palette.windowText: textTone
    palette.text: textTone
    palette.buttonText: textTone
    palette.button: elevated
    palette.base: elevated
    palette.highlight: accent
    property bool showDetails: false
    property string focusedPhase: ""
    property int selectedOrigin: -1
    background: Rectangle { color: window.surface }
    // Keep keyboard focus visible when content must scroll (large fonts/scales).
    onActiveFocusItemChanged: Qt.callLater(function() {
        var item = window.activeFocusItem;
        var ancestor = item;
        while (ancestor && ancestor !== column) ancestor = ancestor.parent;
        if (!item || ancestor !== column || !body.contentItem) return;
        var flick = body.contentItem;
        var top = item.mapToItem(column, 0, 0).y;
        var target = flick.contentY;
        if (top < target) target = top;
        else if (top + item.height > target + flick.height) target = top + item.height - flick.height;
        flick.contentY = Math.max(0, Math.min(target, flick.contentHeight - flick.height));
    })
    onClosing: (event) => { event.accepted = backend.requestClose() }
    Connections {
        target: backend
        function onSafeToClose() { window.close() }
        function onChanged() {
            if (window.phase === window.focusedPhase) return;
            window.focusedPhase = window.phase;
            if (window.phase === "chooseRemote") { window.selectedOrigin = -1; remoteChoice.forceActiveFocus(); }
            else if (window.phase === "confirmRemove") removeConfirmation.forceActiveFocus();
            else if (window.confirming) confirmButton.forceActiveFocus();
            else if (window.phase === "ready") installButton.forceActiveFocus();
            else if (window.finished) closeButton.forceActiveFocus();
        }
    }
    FileDialog {
        id: picker
        objectName: "filePicker"
        title: "Escolher arquivo Flatpak"
        nameFilters: ["Referência Flatpak (*.flatpakref)"]
        fileMode: FileDialog.OpenFile
        onAccepted: backend.loadUrl(selectedFile)
    }
    Controls.ScrollView {
        id: body
        objectName: "bodyScroll"
        anchors.fill: parent
        anchors.margins: 20
        contentWidth: availableWidth
        contentHeight: column.implicitHeight
        clip: true
        Keys.onEscapePressed: window.close()
        ColumnLayout {
            id: column
            objectName: "bodyColumn"
            width: body.availableWidth
            spacing: 12
            Controls.Label {
                Layout.fillWidth: true
                visible: window.state.demo
                text: "DEMONSTRAÇÃO — nenhuma alteração será executada"
                textFormat: Text.PlainText
                wrapMode: Text.Wrap
                color: window.accent
                font.bold: true
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: 14
                Item {
                    Layout.preferredWidth: 52
                    Layout.preferredHeight: 52
                    Layout.alignment: Qt.AlignTop
                    Rectangle {
                        anchors.fill: parent
                        radius: 26
                        property color tone: window.phase === "success" ? window.successTone
                                             : window.phase === "error" ? window.errorTone : window.accent
                        color: Qt.rgba(tone.r, tone.g, tone.b, window.dark ? 0.20 : 0.12)
                    }
                    Kirigami.Icon {
                        objectName: "applicationIcon"
                        anchors.centerIn: parent
                        width: 32; height: 32
                        source: window.phase === "success" ? "dialog-ok-apply"
                              : window.phase === "error" ? "dialog-error"
                              : window.phase === "cancelled" ? "dialog-cancel" : window.state.iconName
                        fallback: "system-software-install"
                        Accessible.ignored: true
                    }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    Kirigami.Heading {
                        objectName: "installationTitle"
                        Layout.fillWidth: true
                        level: 3
                        font.bold: true
                        font.pointSize: window.font.pointSize + 3
                        text: (window.phase === "installing" ? "Instalando " : "") + window.state.name
                        textFormat: Text.PlainText
                        wrapMode: Text.WrapAnywhere
                        color: window.textTone
                    }
                    Controls.Label {
                        objectName: "applicationDescription"
                        Layout.fillWidth: true
                        visible: text.length > 0
                        text: window.state.description
                        textFormat: Text.PlainText
                        wrapMode: Text.Wrap
                        color: window.muted
                        font.pointSize: Math.max(8, window.font.pointSize - 1)
                    }
                    Controls.Label {
                        objectName: "installationMessage"
                        Layout.fillWidth: true
                        visible: text.length > 0
                        text: window.state.message
                        textFormat: Text.PlainText
                        wrapMode: Text.Wrap
                        color: window.muted
                        Accessible.role: Accessible.StaticText
                    }
                }
            }
            Controls.Label {
                objectName: "existingInstallation"
                Layout.fillWidth: true
                visible: window.state.existingNotice.length > 0
                text: window.state.existingNotice
                textFormat: Text.PlainText
                wrapMode: Text.Wrap
                color: window.muted
            }
            Controls.Button {
                objectName: "chooseFileButton"
                visible: !window.state.hasFile && !window.state.demo
                text: "Escolher arquivo"
                icon.name: "document-open"
                onClicked: picker.open()
            }
            ColumnLayout {
                objectName: "destinationOptions"
                Layout.fillWidth: true
                spacing: 4
                visible: window.state.source.length > 0
                enabled: !window.state.busy && !window.state.demo
                Controls.ButtonGroup { id: destinations }
                Controls.RadioButton {
                    id: userDestination
                    objectName: "userDestination"
                    text: "Apenas seu usuário"
                    checked: window.state.scope === "user"
                    Controls.ButtonGroup.group: destinations
                    onClicked: backend.selectDestination("user")
                }
                Controls.RadioButton {
                    id: systemDestination
                    objectName: "systemDestination"
                    text: "Todo o sistema"
                    checked: window.state.scope === "system"
                    Controls.ButtonGroup.group: destinations
                    onClicked: backend.selectDestination("system")
                }
            }
            Controls.ComboBox {
                objectName: "additionalSystemInstallation"
                visible: window.state.systemScopes.length > 0
                enabled: !window.state.busy && !window.state.demo
                model: window.state.systemScopes
                textRole: "label"
                displayText: "Outra instalação de sistema: " + currentText
                onActivated: (index) => backend.selectDestination(window.state.systemScopes[index].scope)
            }
            Controls.Label {
                Layout.fillWidth: true
                visible: window.finished && window.state.source.length > 0
                text: "Destino: " + (window.state.scope === "user" ? "Apenas seu usuário" : "Todo o sistema")
                color: window.muted
            }
            Controls.Label {
                objectName: "originNotice"
                Layout.fillWidth: true
                visible: window.confirming
                text: window.state.notice
                textFormat: Text.PlainText
                wrapMode: Text.WrapAnywhere
                color: window.textTone
            }
            Controls.ComboBox {
                id: remoteChoice
                objectName: "ambiguousOriginChoice"
                Layout.fillWidth: true
                visible: window.phase === "chooseRemote"
                model: window.state.choices
                currentIndex: window.selectedOrigin
                displayText: window.selectedOrigin < 0 ? "Selecione uma das origens" : textAt(window.selectedOrigin)
                onActivated: (index) => { window.selectedOrigin = index }
                Accessible.name: "Origem do aplicativo ou dependência"
            }
            ColumnLayout {
                Layout.fillWidth: true
                visible: (!window.confirming && window.state.busy) || window.phase === "success"
                         || (window.state.demo && window.phase === "progress")
                Controls.ProgressBar {
                    id: totalProgress
                    objectName: "installationProgress"
                    Layout.fillWidth: true
                    from: 0; to: 100
                    indeterminate: window.phase !== "success"
                    value: window.phase === "success" ? 100 : 0
                    background: Rectangle { implicitHeight: 6; radius: 3; color: window.borderTone }
                    contentItem: Item {
                        implicitHeight: 6
                        implicitWidth: 200
                        clip: true
                        Rectangle {
                            width: totalProgress.indeterminate ? parent.width / 3 : parent.width * totalProgress.position
                            height: parent.height
                            radius: 3
                            color: window.accent
                            property real motion: 0
                            x: totalProgress.indeterminate ? motion : 0
                            NumberAnimation on motion {
                                running: totalProgress.indeterminate && totalProgress.visible
                                from: -totalProgress.width / 3; to: totalProgress.width
                                duration: 1400; loops: Animation.Infinite
                            }
                        }
                    }
                    Accessible.name: "Progresso total da instalação"
                    Accessible.description: indeterminate ? "Em andamento" : "Concluído"
                }
                Controls.Label {
                    Layout.alignment: Qt.AlignRight
                    visible: window.phase === "success" || window.state.percent >= 0
                    text: window.phase === "success" ? "100%" : "Etapa atual: " + window.state.percent + "%"
                    color: window.muted
                }
            }
            Controls.Button {
                objectName: "detailsToggle"
                visible: window.state.hasFile
                flat: true
                text: window.showDetails ? "Ocultar detalhes" : "Ver detalhes"
                icon.name: window.showDetails ? "arrow-up" : "arrow-down"
                onClicked: window.showDetails = !window.showDetails
            }
            Rectangle {
                objectName: "detailsPanel"
                Layout.fillWidth: true
                Layout.preferredHeight: 160
                visible: window.showDetails
                radius: 8
                color: window.elevated
                border.color: window.borderTone
                Controls.ScrollView {
                    id: technicalScroll
                    anchors.fill: parent
                    anchors.margins: 8
                    contentWidth: availableWidth
                    TextEdit {
                        objectName: "installationSource"
                        width: technicalScroll.availableWidth
                        readOnly: true
                        selectByMouse: true
                        textFormat: TextEdit.PlainText
                        text: "Origem: " + window.state.source
                              + "\nSerá adicionada se necessária ao instalar."
                              + "\n" + window.state.id + "\n" + window.state.runtimeRepo + "\n" + window.state.details
                              + "\n" + window.state.operations + "\n" + window.state.inventory
                              + "\n" + window.state.operation + "\n" + window.state.operationStatus
                              + "\nCancelar solicita uma parada segura. Alterações concluídas podem permanecer."
                        wrapMode: Text.WrapAnywhere
                        font.family: "monospace"
                        color: window.textTone
                        Accessible.name: "Detalhes técnicos da instalação"
                    }
                }
            }
            Flow {
                visible: window.state.demo
                Layout.fillWidth: true
                spacing: 4
                Repeater {
                    model: ["ready", "remote", "progress", "success", "error", "cancelled"]
                    Controls.Button {
                        required property string modelData
                        text: ({ready: "Preparação", remote: "Origem", progress: "Progresso",
                                success: "Sucesso", error: "Erro", cancelled: "Cancelado"})[modelData]
                        onClicked: backend.simulate(modelData)
                        Accessible.name: "Simular estado " + text
                    }
                }
            }
        }
    }
    footer: Item {
        id: actionFooter
        implicitHeight: actions.implicitHeight + 32
        GridLayout {
            id: actions
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: 16
            width: Math.min(parent.width - 32, implicitWidth)
            columns: parent.width - 32 >= installButton.implicitWidth + closeButton.implicitWidth + 180 ? 6 : 2
            columnSpacing: 8
            rowSpacing: 8
            Controls.Button {
                id: installButton
                objectName: "installButton"
                visible: window.state.source.length > 0 && !window.state.started && !window.finished
                         || (!window.state.busy && ["error", "cancelled"].indexOf(window.phase) >= 0 && window.state.source.length > 0)
                enabled: !window.state.busy && !window.state.demo
                text: window.finished ? "Tentar novamente" : "Instalar"
                highlighted: true
                onClicked: backend.install()
            }
            Controls.Button {
                id: confirmButton
                objectName: "confirmButton"
                visible: window.confirming && window.phase !== "confirmRemove"
                enabled: window.state.token > 0 && !window.state.demo && (window.phase !== "chooseRemote" || window.selectedOrigin >= 0)
                text: window.phase === "confirmDuplicate" ? "Instalar outra cópia" : "Continuar"
                highlighted: true
                onClicked: backend.respond(true, window.selectedOrigin)
            }
            Controls.Button {
                objectName: "removeButton"
                visible: !!window.state.installed.ref && !window.confirming
                enabled: !window.state.busy && !window.state.demo
                text: "Desinstalar"
                onClicked: backend.requestRemove()
            }
            Controls.Button {
                id: removeConfirmation
                objectName: "confirmRemoveButton"
                visible: window.phase === "confirmRemove"
                text: "Desinstalar"
                enabled: !window.state.busy && !window.state.demo
                onClicked: backend.confirmRemove()
            }
            Controls.Button {
                objectName: "openButton"
                visible: window.phase === "success" && (window.state.demo || !!window.state.installed.ref)
                enabled: !window.state.demo && !window.state.busy
                text: "Abrir"
                icon.name: "system-run"
                highlighted: true
                onClicked: backend.launch()
            }
            Controls.Button {
                id: closeButton
                objectName: "closeButton"
                text: window.finished || window.phase === "ready" || !window.state.hasFile ? "Fechar" : "Cancelar"
                enabled: window.phase !== "cancelling"
                onClicked: {
                    if (window.phase === "confirmRemove") backend.selectDestination(window.state.scope);
                    else if (window.confirming) backend.respond(false, 0);
                    else if (window.state.busy) backend.cancel();
                    else window.close();
                }
            }
        }
    }
}
