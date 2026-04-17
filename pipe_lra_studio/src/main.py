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
                             QLineEdit, QFormLayout, QSlider, QSizePolicy, QStyledItemDelegate,
                             QGridLayout, QCheckBox)
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QColor, QFont, QIcon, QAction

from core.engine import BendingEngine
from core.report_generator import ReportGenerator
from visualizer.viewer import PipeViewer

class FullCellEditorDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        editor.setFrame(False)
        editor.setAlignment(Qt.AlignCenter)
        editor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        return editor

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)

class SquareViewport(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._content = None
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(320, 320)

    def set_content(self, widget):
        self._content = widget
        widget.setParent(self)
        self._update_content_geometry()

    def _update_content_geometry(self):
        if not self._content:
            return
        side = min(self.width(), self.height())
        x = (self.width() - side) // 2
        y = (self.height() - side) // 2
        self._content.setGeometry(x, y, side, side)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_content_geometry()

    def sizeHint(self):
        return QSize(520, 520)

    def minimumSizeHint(self):
        return QSize(320, 320)

class MainWindow(QMainWindow):
    ANIM_SLIDER_MAX = 1000

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
        self.anim_speed_levels = [1, 2, 4, 8]
        self.anim_speed_index = 0
        
        self._setup_style()
        self._setup_ui()
        self._setup_statusbar()
        self._update_dashboard()
        
    def _setup_style(self):
        # 🌙 Uniform Industrial Dark Theme
        self.setStyleSheet("""
            QMainWindow { background-color: #11111b; }
            QWidget { color: #cdd6f4; font-family: 'Inter', 'Segoe UI', sans-serif; font-size: 14px; }
            QFrame#heroBanner {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #131c2f, stop:0.5 #16243b, stop:1 #102033);
                border: 1px solid #273449;
                border-radius: 14px;
            }
            QLabel#appTitle { font-size: 24px; font-weight: 900; color: #f8fafc; letter-spacing: 1.4px; }
            QLabel#appSubtitle { font-size: 12px; color: #94e2d5; font-weight: 600; }
            QLabel#sectionHeader { font-size: 11px; font-weight: 700; color: #cdd6f4; }
            QLabel#fieldLabel { font-size: 11px; font-weight: 800; color: #7f849c; letter-spacing: 0.4px; }
            QLabel#metricValue { font-size: 22px; font-weight: 900; color: #f8fafc; }
            QLabel#metricCaption { font-size: 11px; font-weight: 700; color: #7f849c; text-transform: uppercase; }
            QFrame#metricCard {
                background-color: #151825;
                border: 1px solid #2a3144;
                border-radius: 10px;
            }

            QSplitter::handle { background-color: #313244; width: 6px; border-radius: 3px; }
            QSplitter::handle:hover { background-color: #89b4fa; }

            QGroupBox { 
                border: 1px solid #313244; border-radius: 10px; margin-top: 22px; 
                padding-top: 24px; padding-bottom: 10px; padding-left: 12px; padding-right: 12px;
                font-weight: 800; background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #171825, stop:1 #1f1f31);
            }
            QGroupBox::title { 
                subcontrol-origin: margin; subcontrol-position: top left; 
                left: 14px;
                top: -3px;
                padding: 6px 18px;
                min-width: 180px;
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #0f172a, stop:1 #162033);
                color: #f8fafc;
                border: 1px solid #334155;
                border-bottom: 2px solid #89b4fa;
                border-radius: 7px;
                font-size: 13px;
                font-weight: 900;
                letter-spacing: 0.8px;
            }

            QTableWidget { 
                background-color: #16161f; border: 1px solid #2a2a3e; border-radius: 8px;
                gridline-color: #313244; selection-background-color: #5e5f7a;
                selection-color: #f8fafc; outline: none; alternate-background-color: #181825;
            }
            QTableWidget::item { padding: 8px 6px; }
            QHeaderView::section {
                background-color: #12121c; color: #a6adc8; padding: 10px;
                border: none; border-bottom: 1px solid #313244; font-weight: 800; font-size: 12px;
            }
            QTableCornerButton::section {
                background-color: #12121c; border: none; border-bottom: 1px solid #313244; border-right: 1px solid #313244;
            }

            QPushButton { 
                background-color: #1e1e2e; border: 1px solid #2f3340; border-radius: 6px;
                padding: 10px 16px; font-weight: 800; color: #cdd6f4; text-transform: uppercase; font-size: 12px;
            }
            QPushButton:hover { background-color: #2f3340; border-color: #89b4fa; color: #ffffff; }
            QPushButton:pressed { background-color: #3f4258; }

            QCheckBox {
                spacing: 8px;
                color: #cdd6f4;
                font-weight: 700;
                padding: 10px 12px;
                border: 1px solid #2f3340;
                border-radius: 6px;
                background: #15171f;
            }
            QCheckBox:hover {
                border-color: #89b4fa;
                background: #1b1d29;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #475569;
                background: #0f172a;
            }
            QCheckBox::indicator:checked {
                background: #89b4fa;
                border: 1px solid #89b4fa;
            }

            QSlider::groove:horizontal {
                border: none;
                height: 10px;
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #23263a, stop:1 #313244);
                margin: 6px 0;
                border-radius: 5px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #74c7ec, stop:1 #89b4fa);
                border-radius: 5px;
            }
            QSlider::add-page:horizontal {
                background: #23263a;
                border-radius: 5px;
            }
            QSlider::handle:horizontal {
                background: #f8fafc;
                border: 2px solid #89b4fa;
                width: 20px;
                height: 20px;
                margin: -6px 0;
                border-radius: 10px;
            }
            QSlider::handle:horizontal:hover {
                border-color: #74c7ec;
            }

            QLineEdit, QDoubleSpinBox {
                padding: 10px 14px; border: 1px solid #2f3340; border-radius: 6px; background: #15171f; color: #cdd6f4; font-weight: 600; font-size: 13px;
            }
            QLineEdit:focus, QDoubleSpinBox:focus { border: 1px solid #89b4fa; }
        """)

    def _make_labeled_field(self, label_text, widget):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        label = QLabel(label_text)
        label.setObjectName("fieldLabel")
        layout.addWidget(label)
        layout.addWidget(widget)
        return container

    def _make_metric_card(self, value_text, caption_text):
        card = QFrame()
        card.setObjectName("metricCard")
        card.setMinimumHeight(78)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(2)

        value = QLabel(value_text)
        value.setObjectName("metricValue")
        caption = QLabel(caption_text)
        caption.setObjectName("metricCaption")

        layout.addWidget(value)
        layout.addWidget(caption)
        return card, value

    def _update_dashboard(self):
        point_count = len(self.points) if self.points else self.xyz_table.rowCount() if hasattr(self, "xyz_table") else 0
        segment_count = len(self.lra_data)
        total_length = f"{self.total_length:.1f} mm"

        if hasattr(self, "metric_points"):
            self.metric_points.setText(str(point_count))
        if hasattr(self, "metric_segments"):
            self.metric_segments.setText(str(segment_count))
        if hasattr(self, "metric_length"):
            self.metric_length.setText(total_length)

    def _setup_ui(self):
        central = QWidget(); self.setCentralWidget(central)
        layout = QVBoxLayout(central); layout.setContentsMargins(10, 10, 10, 10); layout.setSpacing(10)
        
        hero_banner = QFrame()
        hero_banner.setObjectName("heroBanner")
        hero_layout = QVBoxLayout(hero_banner)
        hero_layout.setContentsMargins(20, 18, 20, 18)
        hero_layout.setSpacing(4)

        title_label = QLabel("PIPE LRA STUDIO")
        title_label.setObjectName("appTitle")
        title_label.setAlignment(Qt.AlignCenter)
        subtitle_label = QLabel("XYZ verisini büküm hesaplarına, 3D doğrulamaya ve rapora dönüştür.")
        subtitle_label.setObjectName("appSubtitle")
        subtitle_label.setAlignment(Qt.AlignCenter)

        hero_layout.addWidget(title_label)
        hero_layout.addWidget(subtitle_label)
        layout.addWidget(hero_banner)

        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(10)
        points_card, self.metric_points = self._make_metric_card("0", "Loaded Points")
        segments_card, self.metric_segments = self._make_metric_card("0", "Computed Segments")
        length_card, self.metric_length = self._make_metric_card("0.0 mm", "Total Tube Length")
        for card in (points_card, segments_card, length_card):
            metrics_row.addWidget(card, 1)
        layout.addLayout(metrics_row)

        # --- 1. TOP: PROJECT METADATA ---
        info_grp = QGroupBox("PROJECT METADATA")
        info_grid = QGridLayout(info_grp); info_grid.setContentsMargins(8, 6, 8, 8); info_grid.setHorizontalSpacing(12); info_grid.setVerticalSpacing(10)
        
        self.in_part = QLineEdit(); self.in_part.setPlaceholderText("Part Number")
        self.in_cust = QLineEdit(); self.in_cust.setPlaceholderText("Customer Name")
        self.in_rev = QLineEdit(); self.in_rev.setPlaceholderText("Revision")
        self.in_mat = QLineEdit(); self.in_mat.setPlaceholderText("Material")
        info_fields = [
            ("Part Number", self.in_part, 0, 0),
            ("Customer Name", self.in_cust, 0, 1),
            ("Revision", self.in_rev, 1, 0),
            ("Material", self.in_mat, 1, 1),
        ]
        for label, widget, row, col in info_fields:
            info_grid.addWidget(self._make_labeled_field(label, widget), row, col)
        info_grid.setColumnStretch(0, 1)
        info_grid.setColumnStretch(1, 1)
        layout.addWidget(info_grp)
        
        # --- 2. MIDDLE: TECHNICAL PARAMETERS ---
        tech_grp = QGroupBox("TECHNICAL PARAMETERS")
        tech_h = QHBoxLayout(tech_grp); tech_h.setContentsMargins(8, 6, 8, 8); tech_h.setSpacing(12)
        
        self.spin_od = QDoubleSpinBox(); self.spin_od.setRange(1.0, 500.0); self.spin_od.setValue(40.0)
        self.spin_od.valueChanged.connect(lambda v: self.viewer.set_tube_properties(v))
        self.spin_od.setRange(1.0, 500.0)
        self.spin_od.setDecimals(2)
        self.spin_od.setButtonSymbols(QDoubleSpinBox.NoButtons)
        self.spin_od.setMinimumWidth(140)
        
        self.spin_clr = QDoubleSpinBox(); self.spin_clr.setRange(1.0, 1000.0); self.spin_clr.setValue(67.5)
        self.spin_clr.setDecimals(2)
        self.spin_clr.setButtonSymbols(QDoubleSpinBox.NoButtons)
        self.spin_clr.setMinimumWidth(140)
        
        self.chk_reverse_rot = QCheckBox("Rotate Reverse")
        self.chk_reverse_rot.setChecked(False)
        self.chk_reverse_rot.toggled.connect(self._toggle_rotation_reverse)
        self.chk_reverse_rot.setMinimumWidth(190)
        tech_h.addWidget(self._make_labeled_field("Outer Diameter", self.spin_od), 0)
        tech_h.addWidget(self._make_labeled_field("Global CLR", self.spin_clr), 0)
        tech_h.addStretch()
        tech_h.addWidget(self._make_labeled_field("Rotation Mode", self.chk_reverse_rot), 0)
        layout.addWidget(tech_grp)

        # --- 3. BOTTOM: TIGHT SPLIT (TABLES | RENDER) ---
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.setChildrenCollapsible(False)
        
        # LEFT: TABLES
        left_widget = QWidget()
        left_v = QVBoxLayout(left_widget); left_v.setContentsMargins(0,0,0,0); left_v.setSpacing(10)
        tabs_splitter = QSplitter(Qt.Vertical)
        tabs_splitter.setChildrenCollapsible(False)
        
        xyz_grp = QGroupBox("XYZ COORDINATES")
        xyz_v = QVBoxLayout(xyz_grp); xyz_v.setContentsMargins(6, 6, 6, 6); xyz_v.setSpacing(8)
        self.xyz_table = QTableWidget(0, 4)
        self.xyz_table.setAlternatingRowColors(True)
        self.xyz_table.setHorizontalHeaderLabels(["Seq", "X Coord", "Y Coord", "Z Coord"])
        xyz_header = self.xyz_table.horizontalHeader()
        xyz_header.setVisible(True)
        xyz_header.setFixedHeight(34)
        xyz_header.setMinimumHeight(34)
        xyz_header.setDefaultAlignment(Qt.AlignCenter)
        xyz_header.setSectionResizeMode(0, QHeaderView.Fixed)
        xyz_header.setSectionResizeMode(1, QHeaderView.Stretch)
        xyz_header.setSectionResizeMode(2, QHeaderView.Stretch)
        xyz_header.setSectionResizeMode(3, QHeaderView.Stretch)
        xyz_header.setStretchLastSection(True)
        xyz_header.setMinimumSectionSize(110)
        xyz_header.setDefaultSectionSize(150)
        self.xyz_table.setColumnWidth(0, 65)
        self.xyz_table.setColumnWidth(1, 150)
        self.xyz_table.setColumnWidth(2, 150)
        self.xyz_table.setColumnWidth(3, 150)
        self.xyz_table.verticalHeader().setVisible(False)
        self.xyz_table.verticalHeader().setDefaultSectionSize(44)
        self.xyz_table.setMinimumHeight(280)
        self.xyz_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.xyz_table.customContextMenuRequested.connect(self._show_context_menu)
        self.xyz_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.xyz_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.xyz_table.setItemDelegate(FullCellEditorDelegate(self.xyz_table))
        self.xyz_table.itemChanged.connect(self._center_table_item_text)
        
        xyz_v.addWidget(self.xyz_table)
        xyz_btn_box = QHBoxLayout(); xyz_btn_box.setSpacing(10)
        xyz_btn_box.setContentsMargins(0, 8, 0, 0)
        btn_import = QPushButton("IMPORT CSV", clicked=self._import_csv)
        btn_add = QPushButton("ADD POINT", clicked=self._add_row)
        btn_clear = QPushButton("CLEAR DATA", clicked=self._clear_table)
        for btn in (btn_import, btn_add, btn_clear):
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setMinimumHeight(42)
        xyz_btn_box.addWidget(btn_import)
        xyz_btn_box.addWidget(btn_add)
        xyz_btn_box.addWidget(btn_clear)
        xyz_v.addLayout(xyz_btn_box)
        tabs_splitter.addWidget(xyz_grp)
        
        lra_grp = QGroupBox("LRA BENDING DATA")
        lra_v = QVBoxLayout(lra_grp); lra_v.setContentsMargins(6, 6, 6, 6); lra_v.setSpacing(8)
        self.lra_table = QTableWidget(0, 6)
        self.lra_table.setAlternatingRowColors(True)
        self.lra_table.setHorizontalHeaderLabels(["Seq", "Len(L)", "Rot(R)", "Ang(A)", "Arc", "CLR"])
        lra_header = self.lra_table.horizontalHeader()
        lra_header.setVisible(True)
        lra_header.setFixedHeight(34)
        lra_header.setMinimumHeight(34)
        lra_header.setDefaultAlignment(Qt.AlignCenter)
        lra_header.setSectionResizeMode(0, QHeaderView.Fixed)
        lra_header.setSectionResizeMode(1, QHeaderView.Stretch)
        lra_header.setSectionResizeMode(2, QHeaderView.Stretch)
        lra_header.setSectionResizeMode(3, QHeaderView.Stretch)
        lra_header.setSectionResizeMode(4, QHeaderView.Stretch)
        lra_header.setSectionResizeMode(5, QHeaderView.Stretch)
        lra_header.setStretchLastSection(True)
        lra_header.setMinimumSectionSize(96)
        lra_header.setDefaultSectionSize(120)
        self.lra_table.setColumnWidth(0, 65)
        self.lra_table.setColumnWidth(1, 120)
        self.lra_table.setColumnWidth(2, 110)
        self.lra_table.setColumnWidth(3, 110)
        self.lra_table.setColumnWidth(4, 110)
        self.lra_table.setColumnWidth(5, 110)
        self.lra_table.verticalHeader().setVisible(False)
        self.lra_table.verticalHeader().setDefaultSectionSize(44)
        self.lra_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.lra_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.lra_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.lra_table.setItemDelegate(FullCellEditorDelegate(self.lra_table))
        self.lra_table.setMinimumHeight(250)
        lra_v.addWidget(self.lra_table)
        
        action_row = QHBoxLayout(); action_row.setSpacing(10)
        btn_calc = QPushButton("GENERATE LRA & 3D MODEL")
        btn_calc.clicked.connect(self._process_all)
        btn_report = QPushButton("EXPORT PDF REPORT")
        btn_report.clicked.connect(self._generate_report)
        for btn in (btn_calc, btn_report):
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setMinimumHeight(42)
        action_row.addWidget(btn_calc)
        action_row.addWidget(btn_report)
        lra_v.addLayout(action_row)
        tabs_splitter.addWidget(lra_grp)
        
        tabs_splitter.setStretchFactor(0, 1)
        tabs_splitter.setStretchFactor(1, 1)
        left_widget.setMinimumWidth(760)
        left_v.addWidget(tabs_splitter)
        main_splitter.addWidget(left_widget)

        # RIGHT: 3D RENDER
        viz_grp = QGroupBox("3D DIGITAL TWIN")
        viz_v = QVBoxLayout(viz_grp); viz_v.setContentsMargins(6, 6, 6, 6); viz_v.setSpacing(8)
        
        self.step_label = QLabel("SYSTEM IDLE - WAITING FOR GEOMETRY")
        self.step_label.setAlignment(Qt.AlignCenter)
        self.step_label.setStyleSheet("font-size: 13px; color: #11111b; font-weight: 800; background: #89b4fa; border-radius: 6px; padding: 10px 12px;")
        viz_v.addWidget(self.step_label)

        self.viewer = PipeViewer()
        self.viewer_host = SquareViewport()
        self.viewer_host.set_content(self.viewer)
        viz_v.addWidget(self.viewer_host, 1)
        
        sim_ctrl = QHBoxLayout(); sim_ctrl.setSpacing(6)
        self.btn_play = QPushButton("PLAY CNC"); self.btn_play.clicked.connect(self._anim_toggle)
        sim_ctrl.addWidget(self.btn_play)

        self.btn_speed = QPushButton("1x")
        self.btn_speed.clicked.connect(self._cycle_anim_speed)
        self.btn_speed.setMinimumWidth(64)
        sim_ctrl.addWidget(self.btn_speed)
        
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, self.ANIM_SLIDER_MAX); self.slider.setValue(0)
        self.slider.setPageStep(25); self.slider.setTracking(True)
        self.slider.setTickPosition(QSlider.NoTicks)
        self.slider.valueChanged.connect(self._slider_changed)
        sim_ctrl.addWidget(self.slider, 1)
        
        self.btn_stop = QPushButton("FULL RESET"); self.btn_stop.clicked.connect(self._anim_reset)
        sim_ctrl.addWidget(self.btn_stop)
        
        viz_v.addLayout(sim_ctrl)
        main_splitter.addWidget(viz_grp)
        
        # Distribute ratios: Tables larger than the 3D render area
        main_splitter.setStretchFactor(0, 5)
        main_splitter.setStretchFactor(1, 3)
        main_splitter.setSizes([1020, 640])
        
        layout.addWidget(main_splitter, 1)

    def _setup_statusbar(self):
        self.statusBar().setStyleSheet("background-color: #11111b; color: #a6adc8; font-weight: 600; padding: 4px;")
        self.statusBar().showMessage(" LRA Studio | Industrial Dynamic Mode Ready")

    # --- HANDLERS ---
    def _init_xyz_row(self, r):
        it_seq = QTableWidgetItem(str(r+1))
        it_seq.setTextAlignment(Qt.AlignCenter); it_seq.setFlags(it_seq.flags() & ~Qt.ItemIsEditable)
        it_seq.setForeground(QColor("#89b4fa")); it_seq.setFont(QFont("Arial", 9, QFont.Bold))
        self.xyz_table.setItem(r, 0, it_seq)
        for c in range(1, 4):
            item = QTableWidgetItem("")
            item.setTextAlignment(Qt.AlignCenter)
            self.xyz_table.setItem(r, c, item)

    def _center_table_item_text(self, item):
        if not item:
            return
        table = item.tableWidget()
        if table:
            table.blockSignals(True)
        item.setTextAlignment(Qt.AlignCenter)
        if table:
            table.blockSignals(False)

    def _toggle_rotation_reverse(self, checked):
        mode_text = "Reverse rotation enabled." if checked else "Reverse rotation disabled."
        self.statusBar().showMessage(mode_text, 3000)
        if self.xyz_table.rowCount() > 1:
            self._process_all()

    def _add_row(self):
        r = self.xyz_table.rowCount(); self.xyz_table.insertRow(r); self._init_xyz_row(r)
        self._update_dashboard()

    def _clear_table(self):
        if QMessageBox.question(self,"Clear","Delete all coordinates?",QMessageBox.Yes|QMessageBox.No)==QMessageBox.Yes:
            self.xyz_table.setRowCount(0)
            self.points = []
            self.lra_data = []
            self.total_length = 0.0
        self.lra_table.setRowCount(0)
        self.step_label.setText("SYSTEM IDLE - WAITING FOR GEOMETRY")
        self.slider.setValue(0)
        self.slider.setRange(0, self.ANIM_SLIDER_MAX)
        self.viewer.set_animation_mode(False)
        self._update_dashboard()

    def _show_context_menu(self, pos):
        m = QMenu(); a1 = QAction("Add Point", self); a1.triggered.connect(self._add_row)
        a2 = QAction("Delete Point", self); a2.triggered.connect(lambda: self.xyz_table.removeRow(self.xyz_table.currentRow()))
        m.addAction(a1); m.addAction(a2); m.exec(self.xyz_table.mapToGlobal(pos))

    def _process_all(self):
        pts = []
        for r in range(self.xyz_table.rowCount()):
            try:
                # Cols 1,2,3 are X,Y,Z
                itms = [self.xyz_table.item(r, c) for c in range(1, 4)]
                if not any(i and i.text().strip() for i in itms): continue
                pts.append([float(i.text().strip().replace(',','.')) for i in itms])
            except: continue
        if len(pts) < 2: return

        if self.chk_reverse_rot.isChecked():
            pts = [[x, y, -z] for x, y, z in pts]
        
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
                if j == 0: it.setForeground(QColor("#89b4fa")); it.setFont(QFont("Arial", 9, QFont.Bold))
                self.lra_table.setItem(i, j, it)
                
        self.viewer.calculate_full_geometry(pts, clrs)
        max_segments = len(self.lra_data)
        self.slider.setRange(0, self.ANIM_SLIDER_MAX)
        self.slider.setValue(self.ANIM_SLIDER_MAX)
        self.viewer.set_animation_mode(False)
        self.step_label.setText(f"TOTAL LENGTH: {self.total_length:.3f} mm | {max_segments} SEGMENTS COMPUTED")
        self._update_dashboard()

    def _anim_toggle(self):
        if not self.lra_data: return
        if self.anim_timer.isActive():
            self.anim_timer.stop(); self.btn_play.setText("RESUME CNC"); self.viewer.set_animation_mode(False)
        else:
            if self.slider.value() >= self.slider.maximum(): self.slider.setValue(0)
            self.viewer.set_animation_mode(True)
            self.anim_timer.start(self._anim_interval_ms()); self.btn_play.setText("PAUSE CNC")

    def _anim_reset(self):
        self.anim_timer.stop(); self.slider.setValue(0); self.btn_play.setText("PLAY CNC")
        self.viewer.set_animation_mode(False)
        self.viewer.show_progress(0.0)

    def _cycle_anim_speed(self):
        self.anim_speed_index = (self.anim_speed_index + 1) % len(self.anim_speed_levels)
        speed = self.anim_speed_levels[self.anim_speed_index]
        self.btn_speed.setText(f"{speed}x")
        self.statusBar().showMessage(f"Animation speed: {speed}x", 2000)
        if self.anim_timer.isActive():
            self.anim_timer.start(self._anim_interval_ms())

    def _anim_interval_ms(self):
        base_interval = 16
        speed = self.anim_speed_levels[self.anim_speed_index]
        return max(5, base_interval // speed)

    def _anim_tick(self):
        val = self.slider.value()
        if val >= self.slider.maximum():
            self.anim_timer.stop(); self.btn_play.setText("PLAY CNC"); self.viewer.set_animation_mode(False); return
        speed = self.anim_speed_levels[self.anim_speed_index]
        base_step = max(2, self.slider.maximum() // 260)
        step = base_step * speed
        self.slider.setValue(min(self.slider.maximum(), val + step))

    def _slider_changed(self, val):
        if not self.lra_data: return
        progress = val / self.slider.maximum() if self.slider.maximum() else 0.0
        self.viewer.show_progress(progress)

        markers = getattr(self.viewer, '_progress_markers', [])
        curr = -1
        for idx in range(len(self.lra_data)):
            marker_idx = min(len(markers) - 1, idx * 2 + 1) if markers else -1
            if marker_idx >= 0 and progress >= markers[marker_idx]:
                curr = idx
            else:
                break

        if 0 <= curr < len(self.lra_data):
            row = self.lra_data[curr]
            phase = "FORMING" if self.anim_timer.isActive() else "READY"
            self.step_label.setText(f"STEP {curr+1}/{len(self.lra_data)} | {phase} | FEED {row['L']:.1f} mm -> BEND {row['A']:.1f}°")
        elif val == 0:
            self.step_label.setText("SYSTEM IDLE / ORIGIN")
        elif progress >= 1.0:
            self.step_label.setText("CNC OPERATION COMPLETE")
        else:
            self.step_label.setText("MATERIAL FEED IN PROGRESS")

        for r in range(self.lra_table.rowCount()):
            bg = QColor("#313244") if r == curr else QColor("#181825")
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
                    if any(r): 
                        idx = self.xyz_table.rowCount()
                        self.xyz_table.insertRow(idx); self._init_xyz_row(idx)
                        for c, v in enumerate(r[:3]):
                            item = QTableWidgetItem(v.strip())
                            item.setTextAlignment(Qt.AlignCenter)
                            self.xyz_table.setItem(idx, c+1, item)
            self._update_dashboard()
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
