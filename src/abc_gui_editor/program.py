import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QPlainTextEdit, QPushButton, QGraphicsView, QGraphicsScene,
    QLineEdit, QLabel, QCheckBox, QMenuBar, QMenu, QAction, QToolBar,
    QFileDialog, QMessageBox, QStatusBar
)
from PyQt5.QtGui import QIcon, QFont, QTextCharFormat, QColor, QPixmap, QPainter
from PyQt5.QtCore import QDir, QFileInfo, QFile, QTextStream, QProcess, QRegularExpression, Qt, QRegularExpressionMatchIterator, QSize
from PyQt5.QtSvg import QSvgRenderer


class Highlighter:
    def __init__(self, parent=None):
        self.parent = parent  # QTextDocument
        self.highlightingRules = []
        
        # keyword tipo1 - darkMagenta
        keywordFormat1 = QTextCharFormat()
        keywordFormat1.setForeground(Qt.darkMagenta)
        keywordFormat1.setFontWeight(QFont.Bold)
        
        keywordPatterns1 = [
            r"\bclef\b", r"\bstem\b", r"\bname\b",
            r"\bsname\b", r"\bstafflines\b"
        ]
        for pattern in keywordPatterns1:
            rule = {'pattern': QRegularExpression(pattern), 'format': keywordFormat1}
            self.highlightingRules.append(rule)
        
        # keyword tipo2 - darkGreen
        keywordFormat2 = QTextCharFormat()
        keywordFormat2.setForeground(Qt.darkGreen)
        keywordFormat2.setFontWeight(QFont.Bold)
        
        keywordPatterns2 = [
            r"\bnone\b", r"\bperc\b",
            r"\bup\b", r"\bdown\b",
            r"\bDmajor\b", r"\bDminor\b",
            r"\bDmaj\b", r"\bDmin\b",
            r"\bAeolian\b", r"\bPhrygian\b", r"\bLocrian\b",
            r"\bDorian\b", r"\bMixolydian\b", r"\bIonian\b"
        ]
        for pattern in keywordPatterns2:
            rule = {'pattern': QRegularExpression(pattern), 'format': keywordFormat2}
            self.highlightingRules.append(rule)
        
        # symbols - blue
        keywordFormat3 = QTextCharFormat()
        keywordFormat3.setForeground(Qt.blue)
        keywordFormat3.setFontWeight(QFont.Bold)
        
        keywordPatterns3 = [
            r":", r"\|", r"\|\]", r"\>", r"\(", r"\)", r"\_", r"\^", r"\'",
            r"\.", r"\~", r"\{", r"\}", r"\[", r"\]"
        ]
        for pattern in keywordPatterns3:
            rule = {'pattern': QRegularExpression(pattern), 'format': keywordFormat3}
            self.highlightingRules.append(rule)
        
        # Class format (not heavily used in ABC)
        classFormat = QTextCharFormat()
        classFormat.setFontWeight(QFont.Bold)
        classFormat.setForeground(Qt.darkMagenta)
        rule = {'pattern': QRegularExpression(r"\bQ[A-Za-z]+\b"), 'format': classFormat}
        self.highlightingRules.append(rule)
        
        # Quotation
        quotationFormat = QTextCharFormat()
        quotationFormat.setForeground(Qt.green)
        rule = {'pattern': QRegularExpression(r'(?<!\\)(["\'])(.+?)(?<!\\)\1'), 'format': quotationFormat}
        self.highlightingRules.append(rule)
        
        # Function
        functionFormat = QTextCharFormat()
        functionFormat.setFontItalic(True)
        functionFormat.setForeground(Qt.blue)
        rule = {'pattern': QRegularExpression(r"\b[A-Za-z0-9_]+(?=\()"), 'format': functionFormat}
        self.highlightingRules.append(rule)
        
        # Single line comment %
        singleLineCommentFormat = QTextCharFormat()
        singleLineCommentFormat.setForeground(Qt.gray)
        rule = {'pattern': QRegularExpression(r"%[^\n]*"), 'format': singleLineCommentFormat}
        self.highlightingRules.append(rule)
        
        # Multi-line comment (though ABC uses % mostly)
        self.multiLineCommentFormat = QTextCharFormat()
        self.multiLineCommentFormat.setForeground(Qt.lightGray)
        self.commentStartExpression = QRegularExpression(r"/\*")
        self.commentEndExpression = QRegularExpression(r"\*/")

    def highlightBlock(self, text):
        for rule in self.highlightingRules:
            matchIterator = rule['pattern'].globalMatch(text)
            while matchIterator.hasNext():
                match = matchIterator.next()
                self.parent.setFormat(match.capturedStart(), match.capturedLength(), rule['format'])
        
        self.parent.setCurrentBlockState(0)
        
        startIndex = 0
        if self.parent.previousBlockState() != 1:
            startIndex = text.indexOf(self.commentStartExpression)
        
        while startIndex >= 0:
            match = self.commentEndExpression.match(text, startIndex)
            endIndex = match.capturedStart()
            commentLength = 0
            if endIndex == -1:
                self.parent.setCurrentBlockState(1)
                commentLength = len(text) - startIndex
            else:
                commentLength = endIndex - startIndex + match.capturedLength()
            
            self.parent.setFormat(startIndex, commentLength, self.multiLineCommentFormat)
            startIndex = text.indexOf(self.commentStartExpression, startIndex + commentLength)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ABC GUI Editor")
        self.resize(1250, 700)
        self.setMinimumSize(800, 700)
        
        self.highlighter = None
        self.scene = QGraphicsScene(self)
        self.ColorCurrentLine = QColor(230, 230, 230)
        self.oldcursor = None
        
        self.setup_ui()
        self.highlighter = Highlighter(self.plainTextEdit_editor.document())
        
        # Default paths
        self.lineEdit_abcm2ps.setText("abcm2ps")
        self.lineEdit_inkscape.setText("inkscape")
        self.lineEdit_abc2midi.setText("abc2midi")
        self.lineEdit_player.setText("totem")
        self.lineEdit_workdir.setText("temporal_abc-gui-editor_path")
        
    def setup_ui(self):
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        
        # Tab Widget
        self.tabWidget = QTabWidget()
        self.tabWidget.setIconSize(QSize(32, 32))
        main_layout.addWidget(self.tabWidget)
        
        # === Tab 1: Editor ===
        tab_editor = QWidget()
        self.tabWidget.addTab(tab_editor, QIcon("icons/if_compose_1055085.png"), "Editor")
        
        editor_layout = QHBoxLayout(tab_editor)
        
        left_layout = QVBoxLayout()
        
        # PlainTextEdit
        self.plainTextEdit_editor = QPlainTextEdit()
        font = QFont("DejaVu Sans Mono", 14)
        self.plainTextEdit_editor.setFont(font)
        self.plainTextEdit_editor.setPlainText(
            "X: 1 % start of header\n"
            "K: C stafflines=1 % scale: C major\n"
            "M: 2/4 %meter - compasso\n"
            "Q:1/4=80\n"
            'V:1 clef=perc stem=up %name="Pauta com clave de fá"   sname="Pauta com clave de fá"\n'
            '[V:1] |:!>!B3/2 B/2 B1 B1| B3/2 B/2 B1 B1 | B2 B2| B2 z2:|'
        )
        left_layout.addWidget(self.plainTextEdit_editor)
        
        # Generate button
        self.pushButton_generate = QPushButton("Generate image")
        self.pushButton_generate.setIcon(QIcon("icons/if_polaroids_1055003.png"))
        self.pushButton_generate.setIconSize(QSize(32, 32))
        self.pushButton_generate.clicked.connect(self.on_pushButton_generate_clicked)
        left_layout.addWidget(self.pushButton_generate)
        
        # GraphicsView
        self.graphicsView = QGraphicsView()
        self.graphicsView.setScene(self.scene)
        left_layout.addWidget(self.graphicsView)
        
        # Play button
        self.pushButton_play = QPushButton("Play")
        self.pushButton_play.setIcon(QIcon("icons/edit-add.png"))
        self.pushButton_play.setIconSize(QSize(32, 32))
        self.pushButton_play.clicked.connect(self.on_pushButton_play_clicked)
        left_layout.addWidget(self.pushButton_play)
        
        editor_layout.addLayout(left_layout)
        
        # === Tab 2: Configuration ===
        tab_config = QWidget()
        self.tabWidget.addTab(tab_config, QIcon("icons/if_tools_1054957.png"), "Configuration")
        
        config_layout = QVBoxLayout(tab_config)
        grid = QGridLayout()
        
        # abcm2ps
        grid.addWidget(QLabel("abcm2ps filepath:"), 0, 0)
        self.lineEdit_abcm2ps = QLineEdit("abcm2ps")
        grid.addWidget(self.lineEdit_abcm2ps, 0, 1)
        
        # abc2midi
        grid.addWidget(QLabel("abc2midi filepath:"), 1, 0)
        self.lineEdit_abc2midi = QLineEdit("abc2midi")
        grid.addWidget(self.lineEdit_abc2midi, 1, 1)
        
        # inkscape
        grid.addWidget(QLabel("inkscape filepath:"), 2, 0)
        self.lineEdit_inkscape = QLineEdit("inkscape")
        grid.addWidget(self.lineEdit_inkscape, 2, 1)
        
        # workdir
        grid.addWidget(QLabel("work filepath"), 4, 0)
        self.lineEdit_workdir = QLineEdit("temporal_abc-gui-editor_path")
        grid.addWidget(self.lineEdit_workdir, 4, 1)
        
        # player
        grid.addWidget(QLabel("player filepath"), 3, 0)
        self.lineEdit_player = QLineEdit("totem")
        grid.addWidget(self.lineEdit_player, 3, 1)
        
        # checkbox
        self.checkBoxEnableDeleteDir = QCheckBox("Enable auto delete of work filepath")
        self.checkBoxEnableDeleteDir.setChecked(True)
        grid.addWidget(self.checkBoxEnableDeleteDir, 5, 1)
        
        config_layout.addLayout(grid)
        
        # Menus
        self.create_menus()
        
        # Toolbar
        self.create_toolbar()
        
        # Status Bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        
        # Connect cursor change
        self.plainTextEdit_editor.cursorPositionChanged.connect(self.on_plainTextEdit_editor_cursorPositionChanged)

    def create_menus(self):
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("Fi&le")
        
        save_action = QAction(QIcon("icons/Gnome-media-flash.png"), "&Save as abc file", self)
        save_action.triggered.connect(self.on_actionSave_as_abc_file_triggered)
        file_menu.addAction(save_action)
        
        open_action = QAction(QIcon("icons/folder-saved-search.png"), "&Open abc file", self)
        open_action.triggered.connect(self.on_actionOpen_abc_file_triggered)
        file_menu.addAction(open_action)
        
        save_data_action = QAction(QIcon("icons/svg.png"), "Save &data files", self)
        save_data_action.triggered.connect(self.on_actionSave_data_files_triggered)
        file_menu.addAction(save_data_action)
        
        help_menu = menubar.addMenu("Help")
        about_action = QAction(QIcon("icons/Information_icon.png"), "About", self)
        about_action.triggered.connect(self.on_actionAbout_triggered)
        help_menu.addAction(about_action)

    def create_toolbar(self):
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(48, 48))
        self.addToolBar(toolbar)
        
        save_action = QAction(QIcon("icons/Gnome-media-flash.png"), "Save as abc file", self)
        save_action.triggered.connect(self.on_actionSave_as_abc_file_triggered)
        toolbar.addAction(save_action)
        
        open_action = QAction(QIcon("icons/folder-saved-search.png"), "Open abc file", self)
        open_action.triggered.connect(self.on_actionOpen_abc_file_triggered)
        toolbar.addAction(open_action)
        
        save_data_action = QAction(QIcon("icons/svg.png"), "Save data files", self)
        save_data_action.triggered.connect(self.on_actionSave_data_files_triggered)
        toolbar.addAction(save_data_action)

    # === Helper methods ===
    def creating_abc_file(self, abcfilepath, code):
        file = QFile(abcfilepath)
        file.remove()
        
        if not file.open(QFile.WriteOnly | QFile.Text):
            return False
        
        out = QTextStream(file)
        out << code
        file.close()
        return True

    def loading_abc_file(self, abcfilepath):
        file = QFile(abcfilepath)
        if not file.open(QFile.ReadOnly | QFile.Text):
            return None
        in_stream = QTextStream(file)
        code = in_stream.readAll()
        file.close()
        return code

    def creating_svg_file(self, abcfilepath, svgfilepath):
        abcm2ps = self.lineEdit_abcm2ps.text()
        
        QFile(svgfilepath).remove()
        
        outputFolder = QFileInfo(abcfilepath).absolutePath()
        generatedSvg = QDir(outputFolder).filePath("Out.svg")
        
        arguments = [abcfilepath, "-g", "-O", generatedSvg]
        
        process = QProcess()
        process.start(abcm2ps, arguments)
        
        if not process.waitForFinished(30000):
            print("Error executing abcm2ps")
            return False
        
        finalSvg = QDir(outputFolder).filePath("Out001.svg")
        if QFile.exists(finalSvg):
            return QFile.rename(finalSvg, svgfilepath)
        return False

    def creating_png_file(self, svgfilepath, pngfilepath, dpi=150):
        QFile(pngfilepath).remove()
        
        inkscape = self.lineEdit_inkscape.text()
        DPI_str = str(dpi)
        
        process = QProcess()
        
        # First try (newer inkscape)
        arguments1 = ["--batch-process", "--export-type=png", f"--export-filename={pngfilepath}", f"--export-dpi={DPI_str}", svgfilepath]
        process.start(inkscape, arguments1)
        
        if not process.waitForFinished(30000):
            # Second try (older)
            arguments2 = ["--without-gui", f"--export-png={pngfilepath}", f"--export-dpi={DPI_str}", svgfilepath]
            process.start(inkscape, arguments2)
            if not process.waitForFinished(30000):
                return False
        return True

    def creating_datafiles_in_dir(self, abccode, absoluteworkdir, StrBaseName):
        abcfile = QDir(absoluteworkdir).filePath(StrBaseName + ".abc")
        svgfile = QDir(absoluteworkdir).filePath(StrBaseName + ".svg")
        pngfile = QDir(absoluteworkdir).filePath(StrBaseName + ".png")
        
        QDir().mkpath(absoluteworkdir)
        
        if self.creating_abc_file(abcfile, abccode):
            self.statusBar.showMessage(abcfile, 10000)
        else:
            self.statusBar.showMessage("ERROR writing the file: " + abcfile, 10000)
            return False
        
        if self.creating_svg_file(abcfile, svgfile):
            self.creating_png_file(svgfile, pngfile, 150)
            
            self.scene.clear()
            pixmap = QPixmap(pngfile)
            self.scene.addPixmap(pixmap)
            self.graphicsView.setScene(self.scene)
            self.graphicsView.show()
            self.statusBar.showMessage(svgfile, 10000)
        else:
            self.statusBar.showMessage("ERROR writing the file: " + svgfile, 10000)
            return False
        
        return True

    def on_pushButton_generate_clicked(self):
        abccode = self.plainTextEdit_editor.toPlainText()
        workdir = self.lineEdit_workdir.text()
        absoluteworkdir = QDir(workdir).absolutePath()
        
        dir_ = QDir(absoluteworkdir)
        if self.checkBoxEnableDeleteDir.isChecked():
            dir_.removeRecursively()
        
        StrBaseName = "temporalfileName"
        self.creating_datafiles_in_dir(abccode, absoluteworkdir, StrBaseName)
        
        if self.checkBoxEnableDeleteDir.isChecked():
            dir_.removeRecursively()

    def creating_midi_file(self, abcfilepath, midifilepath):
        QFile(midifilepath).remove()
        abc2midi = self.lineEdit_abc2midi.text()
        
        arguments = [abcfilepath, "-v", "1", "-o", midifilepath]
        process = QProcess()
        process.start(abc2midi, arguments)
        process.waitForFinished()
        return True

    def play_midi_file(self, midifilepath):
        player = self.lineEdit_player.text()
        arguments = [midifilepath]
        process = QProcess()
        process.start(player, arguments)
        process.waitForFinished()

    def on_pushButton_play_clicked(self):
        abccode = self.plainTextEdit_editor.toPlainText()
        workdir = self.lineEdit_workdir.text()
        basename = QDir(workdir).filePath("fileName")
        
        abcfile = basename + ".abc"
        midfile = basename + ".mid"
        
        dir_ = QDir(workdir)
        if self.checkBoxEnableDeleteDir.isChecked():
            dir_.removeRecursively()
        QDir().mkpath(workdir)
        
        self.creating_abc_file(abcfile, abccode)
        self.creating_midi_file(abcfile, midfile)
        self.play_midi_file(midfile)
        
        if self.checkBoxEnableDeleteDir.isChecked():
            dir_.removeRecursively()

    def on_plainTextEdit_editor_cursorPositionChanged(self):
        # Simple current line highlight
        cursor = self.plainTextEdit_editor.textCursor()
        fmt = QTextCharFormat()
        fmt.setBackground(self.ColorCurrentLine)
        
        cursor.select(QTextCursor.LineUnderCursor)
        cursor.setCharFormat(fmt)
        
        # Reset previous (basic implementation)
        if self.oldcursor:
            fmt.setBackground(Qt.white)
            self.oldcursor.setCharFormat(fmt)
        
        self.oldcursor = self.plainTextEdit_editor.textCursor()
        self.oldcursor.select(QTextCursor.LineUnderCursor)

    def on_actionSave_as_abc_file_triggered(self):
        abcfile, _ = QFileDialog.getSaveFileName(self, "Save File", "", "ABC files (*.abc *.ABC *.txt)")
        if not abcfile:
            return
        abccode = self.plainTextEdit_editor.toPlainText()
        if self.creating_abc_file(abcfile, abccode):
            QMessageBox.information(self, "ABC file", "The document has been saved.")
        else:
            QMessageBox.warning(self, "ABC file", "ERROR: The document has NOT been saved.")

    def on_actionOpen_abc_file_triggered(self):
        abcfile, _ = QFileDialog.getOpenFileName(self, "Open ABC file", "", "ABC Files (*.abc *.ABC *.txt)")
        if not abcfile:
            return
        code = self.loading_abc_file(abcfile)
        if code is not None:
            self.plainTextEdit_editor.setPlainText(code)
            QMessageBox.information(self, "ABC file", "The document has been loaded.")
        else:
            QMessageBox.warning(self, "ABC file", "ERROR loading file.")

    def on_actionSave_data_files_triggered(self):
        pngfile, _ = QFileDialog.getSaveFileName(self, "Save PNG File", "", "PNG files (*.png *.PNG)")
        if not pngfile:
            return
        abccode = self.plainTextEdit_editor.toPlainText()
        absoluteworkdir = QFileInfo(pngfile).absoluteDir().absolutePath()
        StrBaseName = QFileInfo(pngfile).baseName()
        results = self.creating_datafiles_in_dir(abccode, absoluteworkdir, StrBaseName)
        if results:
            QMessageBox.information(self, "PNG file", "The document has been saved.")
        else:
            QMessageBox.warning(self, "PNG file", "The document has not been saved.")

    def on_actionAbout_triggered(self):
        text = (
            "<b>Program:</b> ABC GUI Editor<br>"
            "<b>Version:</b> 1.0<br>"
            "<b>Homepage:</b> <a href=\"https://github.com\">https://github.com</a><br>"
            "<b>Summary:</b> GUI to work with abc notation<br>"
            "<b>Description:</b> A graphic user interface program to work with abc notation"
        )
        QMessageBox.about(self, "ABC Gui Editor", text)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
