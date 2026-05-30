import os
import sys
import signal
import subprocess

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QPlainTextEdit, QPushButton, QGraphicsView, QGraphicsScene,
    QLineEdit, QLabel, QCheckBox, QMenuBar, QMenu, QAction, QToolBar,
    QFileDialog, QMessageBox, QStatusBar, QSizePolicy
)

from PyQt5.QtGui  import QIcon, QDesktopServices, QSyntaxHighlighter, QFont, QTextCharFormat, QColor, QPixmap, QPainter, QTextCursor
from PyQt5.QtCore import QDir, QFileInfo, QFile, QTextStream, QProcess, QRegularExpression, Qt, QUrl, QRegularExpressionMatchIterator, QSize
from PyQt5.QtSvg  import QSvgRenderer

import abc_gui_editor.about as about
import abc_gui_editor.modules.configure as configure 
from abc_gui_editor.modules.resources import resource_path

from abc_gui_editor.modules.wabout    import show_about_window
from abc_gui_editor.desktop import create_desktop_file, create_desktop_directory, create_desktop_menu
from abc_gui_editor.mimetype import ensure_mime_type


# ---------- Path to config file ----------
CONFIG_PATH = os.path.join( os.path.expanduser("~"),
                            ".config", 
                            about.__package__, 
                            "config.json" )

DEFAULT_CONTENT={   
    "toolbar_configure": "Configure",
    "toolbar_configure_tooltip": "Open the configure Json file of program GUI",
    "toolbar_about": "About",
    "toolbar_about_tooltip": "About the program",
    "toolbar_coffee": "Coffee",
    "toolbar_coffee_tooltip": "Buy me a coffee (TrucomanX)",
    "window_width": 1024,
    "window_height": 800,
    "tabwidget_editor": "Editor",
    "plaintextedit_font": "DejaVu Sans Mono",
    "plaintextedit_fontsize": 14,
    "pushbutton_generate": "Generate image",
    "pushbutton_play": "Play",
    "tabwidget_configuration": "Configuration",
    "str_filepath": "filepath",
    "checkbox_delete_dir": "Enable auto delete of work filepath",
    "menu_file": "Fi&le",
    "menu_save_abc": "&Save as abc file",
    "menu_open_abc": "&Open abc file",
    "menu_save_data": "Save &data files",
    "menu_about": "About",
    "toolbar_save_abc": "Save as abc file",
    "toolbar_open_abc": "Open abc file",
    "toolbar_save_data": "Save data files",
    "msg_error_writing": "ERROR writing the file:",
    "msgbox_abc_file": "ABC file",
    "msgbox_save_success": "The document has been saved.",
    "msgbox_save_error": "ERROR: The document has NOT been saved.",
    "msgbox_open_success": "The document has been loaded.",
    "msgbox_open_error": "ERROR loading file.",
    "msgbox_png_file": "PNG file",
    "msgbox_save_data_success": "The document has been saved.",
    "msgbox_save_data_error": "The document has not been saved."
}

configure.verify_default_config(CONFIG_PATH,default_content=DEFAULT_CONTENT)

CONFIG=configure.load_config(CONFIG_PATH)

# ---------------------------------------



class Highlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
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
            r"\bnone\b", r"\bperc\b", r"\bup\b", r"\bdown\b",
            r"\bDmajor\b", r"\bDminor\b", r"\bDmaj\b", r"\bDmin\b",
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

    def highlightBlock(self, text: str):
        # Regras normais (palavras-chave, símbolos, comentários de linha, etc.)
        for rule in self.highlightingRules:
            matchIterator = rule['pattern'].globalMatch(text)
            while matchIterator.hasNext():
                match = matchIterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), rule['format'])
        
        # Multi-line comments (se necessário)
        self.setCurrentBlockState(0)
        
        startIndex = 0
        if self.previousBlockState() != 1:
            # Usa Python str.find com regex
            match = self.commentStartExpression.match(text, startIndex)
            startIndex = match.capturedStart() if match.hasMatch() else -1

        while startIndex >= 0:
            match = self.commentEndExpression.match(text, startIndex)
            endIndex = match.capturedStart()
            commentLength = 0
            
            if endIndex == -1:
                self.setCurrentBlockState(1)
                commentLength = len(text) - startIndex
            else:
                commentLength = endIndex - startIndex + match.capturedLength()
            
            self.setFormat(startIndex, commentLength, self.multiLineCommentFormat)
            
            # Próxima ocorrência
            match = self.commentStartExpression.match(text, startIndex + commentLength)
            startIndex = match.capturedStart() if match.hasMatch() else -1



class MainWindow(QMainWindow):
    def __init__(self, input_file):
        super().__init__()

        self.setWindowTitle(about.__program_name__)
        self.resize(CONFIG["window_width"], CONFIG["window_height"])
        
        ## Icon
        # Get base directory for icons
        self.icon_path = resource_path("icons", "logo.svg")
        self.setWindowIcon(QIcon(self.icon_path)) 
        
        
        
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
        
        if os.path.isfile(input_file) and input_file.lower().endswith(".abc"):
            self.load_abc_file(input_file)
        
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
        self.tabWidget.addTab(  tab_editor, 
                                QIcon(resource_path("icons", "if_compose_1055085.svg")), 
                                CONFIG["tabwidget_editor"] )
        
        editor_layout = QHBoxLayout(tab_editor)
        
        left_layout = QVBoxLayout()
        
        # PlainTextEdit
        self.plainTextEdit_editor = QPlainTextEdit()
        font = QFont(CONFIG["plaintextedit_font"], CONFIG["plaintextedit_fontsize"] )
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
        self.pushButton_generate = QPushButton(CONFIG["pushbutton_generate"])
        self.pushButton_generate.setIcon(QIcon(resource_path("icons", "if_polaroids_1055003.svg")))
        self.pushButton_generate.setIconSize(QSize(32, 32))
        self.pushButton_generate.clicked.connect(self.on_pushButton_generate_clicked)
        left_layout.addWidget(self.pushButton_generate)
        
        # GraphicsView
        self.graphicsView = QGraphicsView()
        self.graphicsView.setScene(self.scene)
        left_layout.addWidget(self.graphicsView)
        
        # Play button
        self.pushButton_play = QPushButton(CONFIG["pushbutton_play"])
        self.pushButton_play.setIcon(QIcon(resource_path("icons", "edit-add.svg")))
        self.pushButton_play.setIconSize(QSize(32, 32))
        self.pushButton_play.clicked.connect(self.on_pushButton_play_clicked)
        left_layout.addWidget(self.pushButton_play)
        
        editor_layout.addLayout(left_layout)
        
        # === Tab 2: Configuration ===
        tab_config = QWidget()
        self.tabWidget.addTab(  tab_config, 
                                QIcon(resource_path("icons", "if_tools_1054957.svg")), 
                                CONFIG["tabwidget_configuration"])
        
        config_layout = QVBoxLayout(tab_config)
        grid = QGridLayout()
        
        str_filepath = CONFIG["str_filepath"]
        # abcm2ps
        grid.addWidget(QLabel(f"abcm2ps {str_filepath}:"), 0, 0)
        self.lineEdit_abcm2ps = QLineEdit("abcm2ps")
        grid.addWidget(self.lineEdit_abcm2ps, 0, 1)
        
        # abc2midi
        grid.addWidget(QLabel(f"abc2midi {str_filepath}:"), 1, 0)
        self.lineEdit_abc2midi = QLineEdit("abc2midi")
        grid.addWidget(self.lineEdit_abc2midi, 1, 1)
        
        # inkscape
        grid.addWidget(QLabel(f"inkscape {str_filepath}:"), 2, 0)
        self.lineEdit_inkscape = QLineEdit("inkscape")
        grid.addWidget(self.lineEdit_inkscape, 2, 1)
        
        # workdir
        grid.addWidget(QLabel(f"work {str_filepath}:"), 4, 0)
        self.lineEdit_workdir = QLineEdit("temporal_abc-gui-editor_path")
        grid.addWidget(self.lineEdit_workdir, 4, 1)
        
        # player
        grid.addWidget(QLabel(f"player {str_filepath}:"), 3, 0)
        self.lineEdit_player = QLineEdit("totem")
        grid.addWidget(self.lineEdit_player, 3, 1)
        
        # checkbox
        self.checkBoxEnableDeleteDir = QCheckBox(CONFIG["checkbox_delete_dir"])
        self.checkBoxEnableDeleteDir.setChecked(True)
        grid.addWidget(self.checkBoxEnableDeleteDir, 5, 1)
        
        config_layout.addLayout(grid)
        
        # Menus
        self.create_menus()
        
        # Toolbar
        self.create_toolbar()
        
        # Status Bar
        self.status_bar = QStatusBar()      # ← melhor nome
        self.setStatusBar(self.status_bar)
        
        # Connect cursor change
        self.plainTextEdit_editor.cursorPositionChanged.connect(self.on_plainTextEdit_editor_cursorPositionChanged)

    def create_menus(self):
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu(CONFIG["menu_file"])
        
        # save_action
        save_action = QAction(  QIcon(resource_path("icons", "Gnome-media-flash.png")), 
                                CONFIG["menu_save_abc"], 
                                self)
        save_action.triggered.connect(self.on_actionSave_as_abc_file_triggered)
        file_menu.addAction(save_action)
        
        # open_action
        open_action = QAction(  QIcon(resource_path("icons", "folder-saved-search.svg")), 
                                CONFIG["menu_open_abc"], 
                                self)
        open_action.triggered.connect(self.on_actionOpen_abc_file_triggered)
        file_menu.addAction(open_action)
        
        # save_data_action
        save_data_action = QAction( QIcon(resource_path("icons", "svg.svg")), 
                                    CONFIG["menu_save_data"], 
                                    self)
        save_data_action.triggered.connect(self.on_actionSave_data_files_triggered)
        file_menu.addAction(save_data_action)
        
        # help_menu
        help_menu = menubar.addMenu("Help")
        about_action = QAction( QIcon(resource_path("icons", "Information_icon.svg")), 
                                CONFIG["menu_about"], 
                                self)
        about_action.triggered.connect(self.open_about)
        help_menu.addAction(about_action)

    def create_toolbar(self):       
        self.toolbar = self.addToolBar("Main")
        self.toolbar.setIconSize(QSize(48, 48))
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        
        save_action = QAction(  QIcon(resource_path("icons", "Gnome-media-flash.png")), 
                                CONFIG["toolbar_save_abc"], 
                                self)
        save_action.triggered.connect(self.on_actionSave_as_abc_file_triggered)
        self.toolbar.addAction(save_action)
        
        open_action = QAction(  QIcon(resource_path("icons", "folder-saved-search.svg")), 
                                CONFIG["toolbar_open_abc"], 
                                self)
        open_action.triggered.connect(self.on_actionOpen_abc_file_triggered)
        self.toolbar.addAction(open_action)
        
        save_data_action = QAction( QIcon(resource_path("icons", "svg.svg")), 
                                    CONFIG["toolbar_save_data"], 
                                    self)
        save_data_action.triggered.connect(self.on_actionSave_data_files_triggered)
        self.toolbar.addAction(save_data_action)

        # Adicionar o espaçador
        self.toolbar_spacer = QWidget()
        self.toolbar_spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.toolbar.addWidget(self.toolbar_spacer)
        
        #
        self.configure_action = QAction(QIcon(resource_path("icons", "text-configure.svg")),
                                        CONFIG["toolbar_configure"], 
                                        self)
        self.configure_action.setToolTip(CONFIG["toolbar_configure_tooltip"])
        self.configure_action.triggered.connect(self.open_configure_editor)
        self.toolbar.addAction(self.configure_action)
        
        #
        self.about_action = QAction(QIcon(resource_path("icons", "Information_icon.svg")),
                                    CONFIG["toolbar_about"], 
                                    self)
        self.about_action.setToolTip(CONFIG["toolbar_about_tooltip"])
        self.about_action.triggered.connect(self.open_about)
        self.toolbar.addAction(self.about_action)
        
        # Coffee
        self.coffee_action = QAction(   QIcon(resource_path("icons", "emote-love.png")),
                                        CONFIG["toolbar_coffee"], 
                                        self)
        self.coffee_action.setToolTip(CONFIG["toolbar_coffee_tooltip"])
        self.coffee_action.triggered.connect(self.on_coffee_action_click)
        self.toolbar.addAction(self.coffee_action)

        # Conectar ao sinal de mudança de orientação
        self.toolbar.orientationChanged.connect(self.on_update_spacer_policy)
        self.on_update_spacer_policy()

    def on_update_spacer_policy(self):
        """Atualiza a política do espaçador baseado na orientação da toolbar"""
        if self.toolbar.orientation() == Qt.Horizontal:
            # Horizontal: expande na largura
            self.toolbar_spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        else:
            # Vertical: expande na altura
            self.toolbar_spacer.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

    def _open_file_in_text_editor(self, filepath):
        if os.name == 'nt':  # Windows
            os.startfile(filepath)
        elif os.name == 'posix':  # Linux/macOS
            subprocess.run(['xdg-open', filepath])
    
    def open_url_usage_editor(self):
        QDesktopServices.openUrl(QUrl(CONFIG_GPT["usage"]))
        
    def open_configure_editor(self):
        self._open_file_in_text_editor(CONFIG_PATH)

    def open_about(self):
        data={
            "version": about.__version__,
            "package": about.__package__,
            "program_name": about.__program_name__,
            "author": about.__author__,
            "email": about.__email__,
            "description": about.__description__,
            "url_source": about.__url_source__,
            "url_doc": about.__url_doc__,
            "url_funding": about.__url_funding__,
            "url_bugs": about.__url_bugs__
        }
        show_about_window(data,self.icon_path)

    def on_coffee_action_click(self):
        QDesktopServices.openUrl(QUrl("https://ko-fi.com/trucomanx"))
        
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
            self.status_bar.showMessage(abcfile, 10000)
        else:
            self.status_bar.showMessage(CONFIG["msg_error_writing"]+ " " + abcfile, 10000)
            return False
        
        if self.creating_svg_file(abcfile, svgfile):
            self.creating_png_file(svgfile, pngfile, 150)
            
            self.scene.clear()
            pixmap = QPixmap(pngfile)
            self.scene.addPixmap(pixmap)
            self.graphicsView.setScene(self.scene)
            self.graphicsView.show()
            self.status_bar.showMessage(svgfile, 10000)
        else:
            self.status_bar.showMessage(CONFIG["msg_error_writing"]+ " " + svgfile, 10000)
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
            QMessageBox.information(self, 
                                    CONFIG["msgbox_abc_file"], 
                                    CONFIG["msgbox_save_success"])
        else:
            QMessageBox.warning(self, 
                                CONFIG["msgbox_abc_file"], 
                                CONFIG["msgbox_save_error"])

    def load_abc_file(self, abcfile):
        if not abcfile:
            return None
            
            
        code = self.loading_abc_file(abcfile)
        if code is not None:
            self.plainTextEdit_editor.setPlainText(code)
            
        return code
        
    def on_actionOpen_abc_file_triggered(self):
        abcfile, _ = QFileDialog.getOpenFileName(self, "Open ABC file", "", "ABC Files (*.abc *.ABC *.txt)")
        
        code = self.load_abc_file(abcfile)
        
        if code is not None:
            QMessageBox.information(self, 
                                    CONFIG["msgbox_abc_file"], 
                                    CONFIG["msgbox_open_success"])
        else:
            QMessageBox.warning(self, 
                                CONFIG["msgbox_abc_file"], 
                                CONFIG["msgbox_open_error"])

    def on_actionSave_data_files_triggered(self):
        pngfile, _ = QFileDialog.getSaveFileName(self, "Save PNG File", "", "PNG files (*.png *.PNG)")
        if not pngfile:
            return
        abccode = self.plainTextEdit_editor.toPlainText()
        absoluteworkdir = QFileInfo(pngfile).absoluteDir().absolutePath()
        StrBaseName = QFileInfo(pngfile).baseName()
        results = self.creating_datafiles_in_dir(abccode, absoluteworkdir, StrBaseName)
        if results:
            QMessageBox.information(self, 
                                    CONFIG["msgbox_png_file"], 
                                    CONFIG["msgbox_save_data_success"])
        else:
            QMessageBox.warning(self, 
                                CONFIG["msgbox_png_file"], 
                                CONFIG["msgbox_save_data_error"])

def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    ensure_mime_type("abc", "application/x-abc", "ABC notation file")
    extras="MimeType=application/x-abc;"
    
    create_desktop_directory()    
    create_desktop_menu()
    create_desktop_file(os.path.join("~",".local","share","applications"), 
                        program_name=about.__program_name__,
                        extras=extras)
    
    for n in range(len(sys.argv)):
        if sys.argv[n] == "--autostart":
            create_desktop_directory(overwrite = True)
            create_desktop_menu(overwrite = True)
            create_desktop_file(os.path.join("~",".config","autostart"), 
                                overwrite=True, 
                                program_name=about.__program_name__,
                                extras=extras)
            return
        if sys.argv[n] == "--applications":
            create_desktop_directory(overwrite = True)
            create_desktop_menu(overwrite = True)
            create_desktop_file(os.path.join("~",".local","share","applications"), 
                                overwrite=True, 
                                program_name=about.__program_name__,
                                extras=extras)
            return
    
    filepath=""
    if len(sys.argv)>1:
        filepath=sys.argv[1]
        
    app = QApplication(sys.argv)
    app.setApplicationName(about.__package__) 
    
    window = MainWindow(filepath)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
