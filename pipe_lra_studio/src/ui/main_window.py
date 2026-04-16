import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QFileDialog, QLabel, QSplitter)
from PySide6.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pipe LRA Studio")
        self.resize(1200, 800)
        
        # Ana Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Splitter (Sol: Veri, Sağ: 3B)
        self.splitter = QSplitter(Qt.Horizontal)
        
        # --- SOL PANEL: Veri ve Giriş ---
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        
        self.left_layout.addWidget(QLabel("XYZ Koordinatları"))
        self.table = QTableWidget(10, 3)
        self.table.setHorizontalHeaderLabels(["X", "Y", "Z"])
        self.left_layout.addWidget(self.table)
        
        self.btn_calculate = QPushButton("LRA Hesapla")
        self.left_layout.addWidget(self.btn_calculate)
        
        self.btn_load_dxf = QPushButton("Profil DXF Yükle")
        self.left_layout.addWidget(self.btn_load_dxf)
        
        # LRA Sonuç Tablosu
        self.left_layout.addWidget(QLabel("LRA Sonuçları"))
        self.result_table = QTableWidget(0, 3)
        self.result_table.setHorizontalHeaderLabels(["L (Boy)", "R (Rot)", "A (Açı)"])
        self.left_layout.addWidget(self.result_table)
        
        self.splitter.addWidget(self.left_panel)
        
        # --- SAĞ PANEL: 3B Görselleştirme ---
        self.right_panel = QWidget()
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.addWidget(QLabel("3B Görselleştirme"))
        
        # Buraya PyVista entegre edilecek
        self.visualizer_placeholder = QWidget()
        self.visualizer_placeholder.setStyleSheet("background-color: black;")
        self.right_layout.addWidget(self.visualizer_placeholder)
        
        # Animasyon kontrolleri
        anim_controls = QHBoxLayout()
        self.btn_play = QPushButton("Play")
        self.btn_pause = QPushButton("Pause")
        self.btn_stop = QPushButton("Stop")
        anim_controls.addWidget(self.btn_play)
        anim_controls.addWidget(self.btn_pause)
        anim_controls.addWidget(self.btn_stop)
        self.right_layout.addLayout(anim_controls)
        
        self.splitter.addWidget(self.right_panel)
        
        main_layout.addWidget(self.splitter)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
