import QtQuick
import QtQuick.Controls
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Commons as Commons
import qs.Ui
import "Homelab.js" as Homelab

// Bar icon that shows whether the homelab answers, with a per-host panel.
// Each check is one short TCP connection per host, made by probe.sh; no data
// is sent and nothing is written to disk. Host names and addresses come from
// shell.json and are validated in Homelab.js before they reach the script's
// arguments; every Text here is PlainText.
Panel {
  id: root
  moduleName: "tobias.homelab"
  ipcTarget: "tobias.homelab"

  readonly property var hosts: Homelab.normalizeHosts(setting("hosts", []))
  readonly property bool backgroundRefresh: setting("backgroundRefresh", true) !== false
  readonly property int refreshSec: Math.max(15, Math.min(3600, parseInt(setting("refreshIntervalSec", 60), 10) || 60))
  property var results: ({})
  property double checkedAt: 0
  readonly property int slowMs: Math.max(20, Math.min(3000, parseInt(setting("slowMs", 250), 10) || 250))
  readonly property var counts: Homelab.summary(hosts, results, slowMs)
  // Every host down at once almost always means the lab is off or this
  // machine is off the tailnet, so that reads as "away", not as an alarm.
  readonly property bool unreachable: counts.known > 0 && counts.down === counts.known
  readonly property bool degraded: counts.down > 0 && !unreachable
  readonly property bool warned: counts.warn > 0 && !degraded

  // Green and yellow are not shell colour roles, so they are read from the
  // active theme's colors.toml; red follows the shell's urgent colour.
  property var themePalette: Homelab.palette("", { green: "#5df0a8", yellow: "#e8d98a", red: "" })
  readonly property color okColor: themePalette.green
  readonly property color warnColor: themePalette.yellow
  readonly property color downColor: themePalette.red !== "" ? themePalette.red : urgent

  function levelColor(level, fallback) {
    return level === "ok" ? okColor : level === "warn" ? warnColor : level === "down" ? downColor : fallback
  }

  readonly property color foreground: bar ? bar.foreground : Color.foreground
  readonly property color urgent: bar ? bar.urgent : Color.urgent
  readonly property color dim: Qt.darker(foreground, 1.55)
  readonly property string fontFamily: bar ? bar.fontFamily : Style.font.family
  readonly property string scriptPath: Qt.resolvedUrl("probe.sh").toString().replace(/^file:\/\//, "")
  readonly property string checkedText: checkedAt > 0
    ? new Date(checkedAt).toLocaleTimeString(Qt.locale(Commons.I18n.formatLocale), "HH:mm")
    : ""

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  function open() {
    reload()
    root.controller.show()
  }

  function reload() {
    if (probeProc.running || root.hosts.length === 0) return
    var command = ["bash", root.scriptPath]
    for (var i = 0; i < root.hosts.length; i++) command.push(root.hosts[i].target)
    probeProc.command = command
    probeProc.running = true
  }

  function copy(text) {
    Quickshell.execDetached(["wl-copy", "--", text])
  }

  onHostsChanged: {
    root.results = ({})
    root.checkedAt = 0
    if (root.backgroundRefresh || root.opened) reload()
  }

  FileView {
    id: paletteFile
    path: Color.currentThemePath + "/colors.toml"
    watchChanges: false
    printErrors: false
    onLoaded: root.themePalette = Homelab.palette(text(), { green: "#5df0a8", yellow: "#e8d98a", red: "" })
  }

  // A theme switch replaces the theme directory; the shell's own palette
  // changing is the cue to read the new file.
  Connections {
    target: Color
    function onBackgroundChanged() { paletteFile.reload() }
    function onForegroundChanged() { paletteFile.reload() }
    function onAccentChanged() { paletteFile.reload() }
  }

  Commons.Translations { id: strings; directory: Qt.resolvedUrl("i18n") }

  Timer {
    interval: root.refreshSec * 1000
    running: root.hosts.length > 0 && (root.backgroundRefresh || root.opened)
    repeat: true
    triggeredOnStart: true
    onTriggered: root.reload()
  }

  Process {
    id: probeProc
    property string output: ""
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: probeProc.output = text
    }
    onExited: function(exitCode) {
      var text = probeProc.output
      probeProc.output = ""
      if (exitCode !== 0) return
      root.results = Homelab.parseResults(text, root.hosts)
      root.checkedAt = Date.now()
    }
  }

  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: "󰒍" // nf-md-server_network (U+F048D)
    foreground: root.degraded ? root.downColor
      : root.warned ? root.warnColor
      : (root.counts.known === 0 || root.unreachable ? Qt.darker(root.barForeground, 1.55) : root.barForeground)
    // Counts only: the tooltip is an Omarchy-owned text sink, so no host
    // names or addresses go into it.
    tooltipText: root.counts.known > 0
      ? strings.t("tooltip.counts").arg(Commons.I18n.formatNumber(root.counts.up)).arg(Commons.I18n.formatNumber(root.counts.total))
      : strings.t("tooltip.unknown")
    onPressed: function(buttonCode) { root.toggle() }
  }

  KeyboardPanel {
    id: panel
    anchorItem: button
    owner: root
    bar: root.bar
    open: root.opened
    focusTarget: keyCatcher
    contentWidth: panel.fittedContentWidth(Style.space(360))
    contentHeight: panel.fittedContentHeight(column.implicitHeight, Style.space(560))

    PanelKeyCatcher {
      id: keyCatcher
      anchors.fill: parent
      onCloseRequested: root.close()
      onTabRequested: function(direction) { root.switchPanel(direction) }

      Flickable {
        id: flick
        anchors.fill: parent
        contentWidth: width
        contentHeight: column.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        flickableDirection: Flickable.VerticalFlick
        interactive: contentHeight > height
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

        Column {
          id: column
          width: flick.width
          spacing: Style.space(4)

          Item {
            width: parent.width
            height: Math.max(title.implicitHeight, refresh.height)

            Text {
              id: title
              anchors.verticalCenter: parent.verticalCenter
              textFormat: Text.PlainText
              text: strings.t("title")
              color: root.foreground
              font.family: root.fontFamily
              font.pixelSize: Style.font.body
              font.bold: true
            }

            PanelActionButton {
              id: refresh
              anchors.right: parent.right
              anchors.verticalCenter: parent.verticalCenter
              iconText: "󰑐" // nf-md-refresh (U+F0450)
              tooltipText: strings.t("refresh")
              foreground: root.dim
              hoverColor: root.foreground
              fontFamily: root.fontFamily
              enabled: !probeProc.running
              onClicked: root.reload()
            }
          }

          Text {
            width: parent.width
            wrapMode: Text.WordWrap
            textFormat: Text.PlainText
            text: {
              if (root.hosts.length === 0) return strings.t("summary.none")
              if (root.counts.known === 0) return strings.t("summary.checking")
              if (root.unreachable) return strings.t("summary.unreachable").arg(root.checkedText)
              return strings.t("summary.checked")
                .arg(Commons.I18n.formatNumber(root.counts.up))
                .arg(Commons.I18n.formatNumber(root.counts.total))
                .arg(root.checkedText)
            }
            color: root.degraded ? root.downColor : root.warned ? root.warnColor : root.dim
            font.family: root.fontFamily
            font.pixelSize: Style.font.caption
          }

          Item { width: 1; height: Style.space(4) }

          Repeater {
            model: root.hosts

            delegate: Item {
              id: rowItem
              required property var modelData
              readonly property var result: root.results[modelData.target] || null
              readonly property string level: Homelab.level(result, root.slowMs)
              readonly property color levelColor: root.levelColor(level, root.dim)

              width: column.width
              height: nameText.implicitHeight + Style.space(6)

              Rectangle {
                anchors.fill: parent
                radius: Style.space(4)
                color: root.foreground
                opacity: rowMouse.containsMouse ? 0.08 : 0
              }

              Rectangle {
                id: dot
                x: Style.space(4)
                width: Style.space(8)
                height: width
                radius: width / 2
                anchors.verticalCenter: parent.verticalCenter
                color: rowItem.levelColor
                opacity: rowItem.result ? 1 : 0.3
              }

              Text {
                id: nameText
                anchors.left: dot.right
                anchors.leftMargin: Style.space(8)
                anchors.verticalCenter: parent.verticalCenter
                width: Style.space(110)
                elide: Text.ElideRight
                textFormat: Text.PlainText
                text: rowItem.modelData.name
                color: root.foreground
                font.family: root.fontFamily
                font.pixelSize: Style.font.body
              }

              Text {
                anchors.left: nameText.right
                anchors.leftMargin: Style.space(8)
                anchors.right: stateText.left
                anchors.rightMargin: Style.space(8)
                anchors.verticalCenter: parent.verticalCenter
                elide: Text.ElideRight
                textFormat: Text.PlainText
                text: rowItem.modelData.target
                color: root.dim
                font.family: root.fontFamily
                font.pixelSize: Style.font.caption
              }

              Text {
                id: stateText
                anchors.right: parent.right
                anchors.rightMargin: Style.space(4)
                anchors.verticalCenter: parent.verticalCenter
                textFormat: Text.PlainText
                text: !rowItem.result ? strings.t("row.pending")
                  : rowItem.result.state === "up" ? strings.t("row.ms").arg(Commons.I18n.formatNumber(rowItem.result.ms))
                  : rowItem.result.state === "partial" ? strings.t("row.partial")
                  : strings.t("row.down")
                color: rowItem.levelColor
                font.family: root.fontFamily
                font.pixelSize: Style.font.caption
              }

              // Click a row to copy its address.
              MouseArea {
                id: rowMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.copy(rowItem.modelData.host)
              }
            }
          }
        }
      }
    }
  }
}
