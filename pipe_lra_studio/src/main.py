import sys
import os
import numpy as np
import csv

# Add project roots
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QFileDialog, QLabel, QSplitter, 
                             QMessageBox, QHeaderView, QGroupBox, QMenu,
                             QFrame, QStatusBar, QAbstractItemView, QDoubleSpinBox,
                             QLineEdit, QFormLayout, QSlider)
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QColor, QFont, QIcon, QAction

from core.engine import BendingEngine
from core.report_generator import ReportGenerator
from visualizer.viewer import PipeViewer

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pipe LRA Studio v2.7 - Professional Edition")
        self.resize(1600, 1000)
        
        # State
        self.points = []
        self.clrs = []
        self.lra_data = []
        self.total_length = 0.0
        self.anim_timer = QTimer()
        self.anim_timer.timeout.connect(self._anim_tick)
        
        self._setup_style()
        self._setup_ui()
        self._setup_statusbar()
        
    def _setup_style(self):
        # Professional Industrial Light Theme
        self.setStyleSheet("""
            QMainWindow { background-color: #f8f9fa; }
            QWidget { color: #343a40; font-family: 'Inter', 'Segoe UI', sans-serif; font-size: 13px; }
            
            QGroupBox { 
                border: 1px solid #dee2e6; border-radius: 12px; margin-top: 20px; 
                padding-top: 30px; font-weight: 800; color: #1e293b; background: white;
            }
            QGroupBox::title { 
                subcontrol-origin: margin; subcontrol-position: top center; 
                padding: 0 15px; background: white; font-size: 15px; color: #1e66f5;
            }

            QTableWidget { 
                background-color: white; border: 1px solid #dee2e6; border-radius: 6px;
                gridline-color: #f1f3f5; selection-background-color: #e9ecef;
                selection-color: #1e66f5; outline: none;
            }
            QHeaderView::section {
                background-color: #f8f9fa; color: #495057; padding: 10px;
                border: none; border-bottom: 2px solid #dee2e6; font-weight: 700;
            }

            QPushButton { 
                background-color: #ffffff; border: 1px solid #ced4da; border-radius: 8px;
                padding: 10px 18px; font-weight: 600; color: #4c4f69;
            }
            QPushButton:hover { background-color: #f1f3f5; border-color: #1e66f5; }
            QPushButton:pressed { background-color: #e9ecef; }
            
            QPushButton#btn_run { background-color: #1e66f5; color: white; border: none; font-size: 14px; }
            QPushButton#btn_run:hover { background-color: #1d4ed8; }

            QPushButton#btn_flip { 
                background-color: #585b70; color: white; border: none; 
                font-size: 10px; padding: 4px 8px; border-radius: 4px;
                font-weight: 700;
            }
            QPushButton#btn_flip:hover { background-color: #45475a; }

            QPushButton#btn_report { background-color: #212529; color: white; border: none; }
            QPushButton#btn_report:hover { background-color: #343a40; }

            QPushButton#btn_play { background-color: #198754; color: white; border: none; min-width: 150px; }
            QPushButton#btn_play:hover { background-color: #157347; }
            
            QPushButton#btn_stop { background-color: #dc3545; color: white; border: none; min-width: 140px; }
            QPushButton#btn_stop:hover { background-color: #bb2d3b; }

            /* Premium Slider Styling */
            QSlider::groove:horizontal { border: 1px solid #dce0e8; height: 10px; background: #f1f3f5; margin: 2px 0; border-radius: 5px; }
            QSlider::sub-page:horizontal { background: #1e66f5; border-radius: 5px; }
            QSlider::handle:horizontal { background: white; border: 2px solid #1e66f5; width: 20px; height: 20px; margin: -6px 0; border-radius: 10px; }

            QLineEdit, QDoubleSpinBox {
                padding: 8px; border: 1px solid #dee2e6; border-radius: 6px; background: #ffffff;
            }
        """)

    def _setup_ui(self):
        central = QWidget(); self.setCentralWidget(central)
        layout = QVBoxLayout(central); layout.setContentsMargins(20, 10, 20, 20); layout.setSpacing(15)
        
        # --- 1. TOP: PROJECT AND TECHNICAL ---
        top_row = QHBoxLayout(); top_row.setSpacing(20)
        
        info_grp = QGroupBox("Project Metadata")
        info_f = QFormLayout(info_grp); info_f.setLabelAlignment(Qt.AlignRight); info_f.setVerticalSpacing(10)
        self.in_part = QLineEdit(""); info_f.addRow("Part No:", self.in_part)
        self.in_cust = QLineEdit(""); info_f.addRow("Customer:", self.in_cust)
        self.in_rev = QLineEdit(""); info_f.addRow("Revision:", self.in_rev)
        self.in_mat = QLineEdit(""); info_f.addRow("Material:", self.in_mat)
        top_row.addWidget(info_grp, 1)
        
        tech_grp = QGroupBox("Technical Parameters")
        tech_f = QFormLayout(tech_grp); tech_f.setLabelAlignment(Qt.AlignRight); tech_f.setVerticalSpacing(10)
        
        od_h = QHBoxLayout()
        self.spin_od = QDoubleSpinBox(); self.spin_od.setRange(1.0, 500.0); self.spin_od.setValue(40.0)
        self.spin_od.valueChanged.connect(lambda v: self.viewer.set_tube_properties(v))
        self.btn_flip = QPushButton("MIRROR / REVERSE ROTATION"); self.btn_flip.setObjectName("btn_flip")
        self.btn_flip.clicked.connect(self._flip_z_coords)
        od_h.addWidget(self.spin_od); od_h.addWidget(self.btn_flip)
        tech_f.addRow("Outside Diameter (OD):", od_h)
        
        self.spin_clr = QDoubleSpinBox(); self.spin_clr.setRange(1.0, 1000.0); self.spin_clr.setValue(67.5)
        tech_f.addRow("Global Bending Radius:", self.spin_clr)
        
        tool_btns = QHBoxLayout()
        tool_btns.addWidget(QPushButton("Import CSV", clicked=self._import_csv))
        btn_report = QPushButton("Generate PDF Report"); btn_report.setObjectName("btn_report"); btn_report.clicked.connect(self._generate_report)
        tool_btns.addWidget(btn_report)
        tech_f.addRow(tool_btns)
        top_row.addWidget(tech_grp, 1)
        layout.addLayout(top_row)

        # --- 2. MIDDLE: DATA TABLES ---
        mid_splitter = QSplitter(Qt.Horizontal)
        
        xyz_grp = QGroupBox("Coordinate Definitions (XYZ)")
        xyz_v = QVBoxLayout(xyz_grp)
        self.xyz_table = QTableWidget(10, 3)
        self.xyz_table.setHorizontalHeaderLabels(["X Coord", "Y Coord", "Z Coord"])
        self.xyz_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.xyz_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.xyz_table.customContextMenuRequested.connect(self._show_context_menu)
        for r in range(10): 
            for c in range(3): self.xyz_table.setItem(r, c, QTableWidgetItem(""))
        
        xyz_v.addWidget(self.xyz_table)
        xyz_btn_box = QHBoxLayout()
        xyz_btn_box.addWidget(QPushButton("Add New Point", clicked=self._add_row))
        xyz_btn_box.addWidget(QPushButton("Clear Data", clicked=self._clear_table))
        xyz_v.addLayout(xyz_btn_box)
        mid_splitter.addWidget(xyz_grp)
        
        lra_grp = QGroupBox("Bending Output (LRA)")
        lra_v = QVBoxLayout(lra_grp)
        self.lra_table = QTableWidget(0, 6)
        self.lra_table.setHorizontalHeaderLabels(["Seq", "Length (L)", "Rotation (R)", "Angle (A)", "Arc", "CLR"])
        self.lra_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.lra_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        lra_v.addWidget(self.lra_table)
        
        btn_calc = QPushButton("GENERATE 3D MODEL & DATA"); btn_calc.setObjectName("btn_run"); btn_calc.setFixedHeight(45)
        btn_calc.clicked.connect(self._process_all); lra_v.addWidget(btn_calc)
        mid_splitter.addWidget(lra_grp)
        layout.addWidget(mid_splitter, 1)

        # --- 3. BOTTOM: SIMULATION ---
        viz_grp = QGroupBox("Simulation Control Center")
        viz_v = QVBoxLayout(viz_grp); viz_v.setContentsMargins(15, 15, 15, 15); viz_v.setSpacing(12)
        
        self.step_label = QLabel("INITIALIZE CALCULATION TO START SIMULATION"); self.step_label.setAlignment(Qt.AlignCenter)
        self.step_label.setStyleSheet("font-size: 13px; color: #1e66f5; font-weight: 800; background: #f0f4ff; border-top: 1px solid #dbeafe; padding: 6px;")
        viz_v.addWidget(self.step_label)

        self.viewer = PipeViewer()
        viz_v.addWidget(self.viewer, 1)
        
        sim_ctrl = QHBoxLayout(); sim_ctrl.setSpacing(25)
        self.btn_play = QPushButton("▶ PLAY SIMULATION"); self.btn_play.setObjectName("btn_play"); self.btn_play.clicked.connect(self._anim_toggle)
        sim_ctrl.addWidget(self.btn_play)
        
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100); self.slider.setValue(0)
        self.slider.setPageStep(1) # Fix jumping to end
        self.slider.setTracking(True)
        self.slider.setTickPosition(QSlider.TicksBelow); self.slider.setTickInterval(1)
        self.slider.valueChanged.connect(self._slider_changed)
        sim_ctrl.addWidget(self.slider, 2)
        
        self.btn_stop = QPushButton("⏹ RESET VIEW"); self.btn_stop.setObjectName("btn_stop"); self.btn_stop.clicked.connect(self._anim_reset)
        sim_ctrl.addWidget(self.btn_stop)
        
        viz_v.addLayout(sim_ctrl)
        layout.addWidget(viz_grp, 2)

    def _setup_statusbar(self):
        self.statusBar().showMessage("Pipe LRA Studio v2.7 Professional | Imperial/Metric Engine Ready")

    # --- HANDLERS ---
    def _flip_z_coords(self):
        flipped = False
        for r in range(self.xyz_table.rowCount()):
            it = self.xyz_table.item(r, 2)
            if it and it.text().strip():
                try:
                    val = float(it.text().strip().replace(',','.'))
                    if val != 0: it.setText(str(-val)); flipped = True
                except: continue
        if flipped: 
            self.statusBar().showMessage("Z-Axis Flipped (Mirror Applied).", 3000)
            self._process_all()

    def _add_row(self):
        r = self.xyz_table.rowCount(); self.xyz_table.insertRow(r)
        for c in range(3): self.xyz_table.setItem(r, c, QTableWidgetItem(""))

    def _clear_table(self):
        if QMessageBox.question(self,"Clear","Delete all coordinates?",QMessageBox.Yes|QMessageBox.No)==QMessageBox.Yes:
            self.xyz_table.setRowCount(0); self._add_row()

    def _show_context_menu(self, pos):
        m = QMenu(); a1 = QAction("Add Point", self); a1.triggered.connect(self._add_row)
        a2 = QAction("Delete Point", self); a2.triggered.connect(lambda: self.xyz_table.removeRow(self.xyz_table.currentRow()))
        m.addAction(a1); m.addAction(a2); m.exec(self.xyz_table.mapToGlobal(pos))

    def _process_all(self):
        pts = []
        for r in range(self.xyz_table.rowCount()):
            try:
                itms = [self.xyz_table.item(r, c) for c in range(3)]
                if not any(i and i.text().strip() for i in itms): continue
                pts.append([float(i.text().strip().replace(',','.')) for i in itms])
            except: continue
        if len(pts) < 2: return
        
        g_clr = self.spin_clr.value()
        self.points, clrs = pts, [g_clr] * (len(pts)-2)
        try:
            self.lra_data, warns, self.total_length = BendingEngine.calculate_lra(pts, clrs)
        except Exception as e:
            QMessageBox.critical(self, "Calc Error", str(e)); return
            
        self.lra_table.setRowCount(len(self.lra_data))
        for i, row in enumerate(self.lra_data):
            v = [str(i+1), f"{row['L']:.3f}", f"{row['R']:.3f}", f"{row['A']:.3f}", f"{row['Arc']:.3f}", f"{row['CLR']:.3f}"]
            for j, val in enumerate(v):
                it = QTableWidgetItem(val); it.setTextAlignment(Qt.AlignCenter)
                if j==0: it.setForeground(QColor("#1e66f5")); it.setFont(QFont("Arial", 9, QFont.Bold))
                self.lra_table.setItem(i, j, it)
                
        self.viewer.calculate_full_geometry(pts, clrs)
        max_segments = len(self.lra_data)
        self.slider.setRange(0, max_segments)
        self.slider.setValue(max_segments)
        self.step_label.setText(f"TOTAL LENGTH: {self.total_length:.3f} mm | {max_segments} SEGMENTS COMPUTED")

    def _anim_toggle(self):
        if not self.lra_data: return
        if self.anim_timer.isActive():
            self.anim_timer.stop(); self.btn_play.setText("▶ RESUME SIMULATION")
        else:
            if self.slider.value() >= self.slider.maximum(): self.slider.setValue(0)
            self.anim_timer.start(800); self.btn_play.setText("⏸ PAUSE SIMULATION")

    def _anim_reset(self):
        self.anim_timer.stop(); self.slider.setValue(0); self.btn_play.setText("▶ PLAY SIMULATION")
        self.viewer.show_slice(0)

    def _anim_tick(self):
        val = self.slider.value()
        if val >= self.slider.maximum(): self.anim_timer.stop(); self.btn_play.setText("▶ PLAY SIMULATION"); return
        self.slider.setValue(val + 1)

    def _slider_changed(self, val):
        if not self.lra_data: return
        miles = getattr(self.viewer, '_milestones', [])
        m_idx = min(len(miles)-1, val * 2 - 1)
        if val == 0: self.viewer.show_slice(0)
        else: self.viewer.show_slice(miles[m_idx] + 1)
        
        curr = val - 1
        if 0 <= curr < len(self.lra_data):
            row = self.lra_data[curr]
            self.step_label.setText(f"STEP {val}/{len(self.lra_data)}: FEED {row['L']:.1f} mm -> BEND {row['A']:.1f}°")
        elif val == 0: self.step_label.setText("SIMULATION ORIGIN")
        else: self.step_label.setText("SIMULATION COMPLETE")

        for r in range(self.lra_table.rowCount()):
            bg = QColor("#e9ecef") if r == curr else QColor("white")
            for c in range(6): 
                it = self.lra_table.item(r, c)
                if it: it.setBackground(bg)

    def _import_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open CSV", "", "CSV Files (*.csv)")
        if not path: return
        try:
            with open(path, 'r') as f:
                reader = csv.reader(f); rows = list(reader)
                start = 0
                try: float(rows[0][0].replace(',','.'))
                except: start = 1
                self.xyz_table.setRowCount(0)
                for r in rows[start:]:
                    if any(r): idx = self.xyz_table.rowCount(); self.xyz_table.insertRow(idx); [self.xyz_table.setItem(idx,c,QTableWidgetItem(v.strip())) for c,v in enumerate(r[:3])]
            self._process_all() 
        except: pass

    def _generate_report(self):
        if not self.lra_data: return
        tmp_img = "/tmp/report_v27.png"
        self.viewer.take_screenshot(tmp_img)
        p_info = {'part_no': self.in_part.text(), 'customer': self.in_cust.text(), 'revision': self.in_rev.text(),
                  'od': self.spin_od.value(), 'username': os.getlogin(), 'total_length': self.total_length, 'material': self.in_mat.text()}
        xyz_rep = []
        g_clr = self.spin_clr.value()
        for i, p in enumerate(self.points): clr = g_clr if (0 < i < len(self.points)-1) else 0.0; xyz_rep.append(p + [clr])
        path, _ = QFileDialog.getSaveFileName(self, "Save Analysis", "", "PDF (*.pdf)")
        if path:
            try:
                ReportGenerator.generate_report(path, p_info, xyz_rep, self.lra_data, tmp_img)
                QMessageBox.information(self, "Export OK", f"PDF path:\n{path}")
                if os.path.exists(tmp_img): os.remove(tmp_img)
            except Exception as e: QMessageBox.critical(self, "Error", f"Report failed: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv); app.setStyle("Fusion")
    w = MainWindow(); w.show(); sys.exit(app.exec())
