import numpy as np

import vtk
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import vtkmodules.vtkRenderingOpenGL2

class SolidWorksInteractorStyle(vtk.vtkInteractorStyleTrackballCamera):
    def __init__(self, renderer, render_window, parent=None):
        super().__init__()
        self._renderer = renderer
        self._render_window = render_window
        self.SetMotionFactor(6.0)
        self.SetDefaultRenderer(renderer)

        self.AddObserver("MiddleButtonPressEvent", self._on_middle_button_press)
        self.AddObserver("MiddleButtonReleaseEvent", self._on_middle_button_release)
        self.AddObserver("RightButtonPressEvent", self._on_right_button_press)
        self.AddObserver("RightButtonReleaseEvent", self._on_right_button_release)
        self.AddObserver("MouseWheelForwardEvent", self._on_mouse_wheel_forward)
        self.AddObserver("MouseWheelBackwardEvent", self._on_mouse_wheel_backward)

    def _on_middle_button_press(self, obj, event):
        interactor = self.GetInteractor()
        self.FindPokedRenderer(interactor.GetEventPosition()[0], interactor.GetEventPosition()[1])
        if interactor.GetShiftKey():
            self.StartPan()
        else:
            self.StartRotate()

    def _on_middle_button_release(self, obj, event):
        state = self.GetState()
        if state == vtk.VTKIS_PAN:
            self.EndPan()
        elif state == vtk.VTKIS_ROTATE:
            self.EndRotate()

    def _on_right_button_press(self, obj, event):
        interactor = self.GetInteractor()
        self.FindPokedRenderer(interactor.GetEventPosition()[0], interactor.GetEventPosition()[1])
        self.StartDolly()

    def _on_right_button_release(self, obj, event):
        if self.GetState() == vtk.VTKIS_DOLLY:
            self.EndDolly()

    def _on_mouse_wheel_forward(self, obj, event):
        self._dolly(1.15)

    def _on_mouse_wheel_backward(self, obj, event):
        self._dolly(0.87)

    def _dolly(self, factor):
        renderer = self.GetCurrentRenderer() or self._renderer
        if not renderer:
            return
        camera = renderer.GetActiveCamera()
        if camera.GetParallelProjection():
            camera.SetParallelScale(camera.GetParallelScale() / factor)
        else:
            camera.Dolly(factor)
            renderer.ResetCameraClippingRange()
        self._render_window.Render()

class PipeViewer(QWidget):
    """
    Geometrik Doğrulama ve Dondurulmuş Çerçeve (v17) motoru.
    - Orantılı Tanjant Ölçekleme (Kısa segment desteği)
    - Frozen Frames (T, N, B dondurma)
    - Sıfır-Burulma PTF
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tube_radius = 20.0
        self.ovality_factor = 0.08
        self.ring_sides = 28
        self.animation_ring_sides = 28
        self.sample_step = 3.5
        self._animating = False

        # Dondurulmuş Geometri Verileri
        self._full_path = None
        self._full_normals = None
        self._full_binormals = None
        self._full_deform = None
        self._milestones = []
        self._progress_markers = []

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0); self.layout.setSpacing(0)
        self._setup_camera_toolbar(self.layout)

        self.vtk_widget = QVTKRenderWindowInteractor(self)
        self.layout.addWidget(self.vtk_widget, 1)

        self.renderer = vtk.vtkRenderer()
        self.renderer.SetBackground(0.04, 0.04, 0.06)
        self.renderer.SetBackground2(0.1, 0.1, 0.15)
        self.renderer.GradientBackgroundOn()
        self.vtk_widget.GetRenderWindow().AddRenderer(self.renderer)
        self.vtk_widget.GetRenderWindow().SetMultiSamples(0)
        self.interactor_style = SolidWorksInteractorStyle(self.renderer, self.vtk_widget.GetRenderWindow())
        self.vtk_widget.SetInteractorStyle(self.interactor_style)

        axes = vtk.vtkAxesActor()
        self.axes_widget = vtk.vtkOrientationMarkerWidget()
        self.axes_widget.SetOrientationMarker(axes); self.axes_widget.SetInteractor(self.vtk_widget)
        self.axes_widget.SetViewport(0.0, 0.0, 0.15, 0.15); self.axes_widget.EnabledOn(); self.axes_widget.InteractiveOff()

        self._tube_actor = None
        self.vtk_widget.Initialize(); self.vtk_widget.Start()

    def _setup_camera_toolbar(self, parent_layout):
        container = QWidget(); container.setStyleSheet("background-color: #1e1e2e; border: 1px solid #313244; border-radius: 8px;")
        layout = QHBoxLayout(container); layout.setContentsMargins(10, 5, 10, 5); layout.setSpacing(8)
        
        # Camera Views
        views = [("Iso", self.set_view_iso), ("Front", self.set_view_front), ("Top", self.set_view_top), ("Side", self.set_view_right)]
        for name, cb in views:
            btn = QPushButton(name); btn.setMinimumWidth(60)
            btn.setStyleSheet("QPushButton { background-color: #313244; border: 1px solid #45475a; padding: 6px; font-size: 11px; font-weight: bold; border-radius: 6px; color: #cdd6f4; } QPushButton:hover { background-color: #45475a; border-color: #89b4fa; }")
            btn.clicked.connect(cb); layout.addWidget(btn)
        
        layout.addSpacing(15); separator = QFrame(); separator.setFrameShape(QFrame.VLine); separator.setStyleSheet("color: #45475a;"); layout.addWidget(separator); layout.addSpacing(15)

        # Zoom Controls
        zooms = [("Zoom +", self.zoom_in), ("Zoom -", self.zoom_out), ("Fit", self.zoom_fit)]
        for name, cb in zooms:
            btn = QPushButton(name); btn.setMinimumWidth(50)
            btn.setStyleSheet("QPushButton { background-color: #313244; border: 1px solid #45475a; padding: 6px; font-weight: bold; border-radius: 6px; color: #cdd6f4; } QPushButton:hover { background-color: #45475a; border-color: #a6e3a1; color: white; }")
            btn.clicked.connect(cb); layout.addWidget(btn)
            
        layout.addStretch(); parent_layout.addWidget(container)

    def zoom_in(self): self.renderer.GetActiveCamera().Zoom(1.2); self.vtk_widget.GetRenderWindow().Render()
    def zoom_out(self): self.renderer.GetActiveCamera().Zoom(0.8); self.vtk_widget.GetRenderWindow().Render()
    def zoom_fit(self): self.renderer.ResetCamera(); self.vtk_widget.GetRenderWindow().Render()

    def _reset_camera_orientation(self, pos, up, parallel=True):
        cam = self.renderer.GetActiveCamera()
        cam.SetPosition(pos)
        cam.SetFocalPoint(0, 0, 0)
        cam.SetViewUp(up)
        cam.SetParallelProjection(parallel) # CAD style orthographic
        self.renderer.ResetCamera()
        self.vtk_widget.GetRenderWindow().Render()

    def set_view_iso(self): self._reset_camera_orientation([2000, -2000, 2000], [0, 0, 1], parallel=False) # Perspective for ISO
    def set_view_front(self): self._reset_camera_orientation([0, -3000, 0], [0, 0, 1])
    def set_view_back(self): self._reset_camera_orientation([0, 3000, 0], [0, 0, 1])
    def set_view_top(self): self._reset_camera_orientation([0, 0, 3000], [0, 1, 0])
    def set_view_bottom(self): self._reset_camera_orientation([0, 0, -3000], [0, -1, 0])
    def set_view_left(self): self._reset_camera_orientation([-3000, 0, 0], [0, 0, 1])
    def set_view_right(self): self._reset_camera_orientation([3000, 0, 0], [0, 0, 1])

    def set_tube_properties(self, od):
        self.tube_radius = float(od) / 2.0

    def set_animation_mode(self, active):
        self._animating = bool(active)

    def calculate_full_geometry(self, points, clr_list=None):
        """Tüm geometriyi bir kez hesaplar. Tanjant çakışmalarını orantılı ölçekler."""
        if len(points) < 2: return
        pts = np.array(points, dtype=float)
        
        # Filtreleme: Aynı olan ardışık noktaları temizle (NaN hatasını önler)
        filtered = [pts[0]]
        for i in range(1, len(pts)):
            if np.linalg.norm(pts[i] - pts[i-1]) > 1e-6:
                filtered.append(pts[i])
        pts = np.array(filtered)
        if len(pts) < 2: return
        
        num_pts = len(pts)
        clrs = list(clr_list) if clr_list else []
        
        # 1. Ham Tanjant Hesaplama (Corner Analysis)
        num_corners = len(pts) - 2
        raw_tangents = np.zeros(max(0, num_corners))
        for i in range(1, len(pts)-1):
            v_in, v_out = pts[i-1]-pts[i], pts[i+1]-pts[i]
            m_in, m_out = np.linalg.norm(v_in), np.linalg.norm(v_out)
            if m_in < 1e-6 or m_out < 1e-6: continue
            dot = np.clip(np.dot(v_in/m_in, v_out/m_out), -1.0, 1.0)
            if abs(dot) > 0.9999: continue
            angle = np.arccos(dot)
            clr = clrs[i-1] if i-1 < len(clrs) else 0.0
            # KRİTİK FİX: Tanjant boyu (T), büküm açısının (bend_angle) yarısının tanjantıdır.
            # İç açı (angle) değil, dış açı (pi - angle) kullanılmalıdır.
            bend_angle = np.pi - angle
            raw_tangents[i-1] = clr * np.tan(bend_angle / 2.0)

        # 2. Orantılı Ölçekleme (Kısa segmentlerde çakışmayı önle)
        adj_t = raw_tangents.copy()
        for i in range(len(pts) - 1):
            seg_len = np.linalg.norm(pts[i+1] - pts[i])
            t_start = adj_t[i-1] if i > 0 else 0.0
            t_end = adj_t[i] if i < len(adj_t) else 0.0
            if t_start + t_end > seg_len * 0.99:
                scale = (seg_len * 0.98) / (t_start + t_end)
                if i > 0: adj_t[i-1] *= scale
                if i < len(adj_t): adj_t[i] *= scale

        # 3. Path İnşası
        path_list = []; def_list = []; milestones = []
        milestones.append(0) # Start P0

        def add_subdivided(p_start, p_end):
            d = np.linalg.norm(p_end - p_start)
            if d < 1e-6: return
            n = int(np.ceil(d / self.sample_step))
            sk = 1 if path_list else 0
            for k in range(sk, n + 1):
                path_list.append(p_start + (p_end - p_start)*(k/n))
                def_list.append(0.0)

        for i in range(1, len(pts)-1):
            v1_u = (pts[i-1]-pts[i])/np.linalg.norm(pts[i-1]-pts[i])
            v2_u = (pts[i+1]-pts[i])/np.linalg.norm(pts[i+1]-pts[i])
            t_dist = adj_t[i-1]
            if t_dist > 0.1:
                p_en, p_ex = pts[i] + v1_u*t_dist, pts[i] + v2_u*t_dist
                add_subdivided(path_list[-1] if path_list else pts[0], p_en)
                milestones.append(len(path_list)-1) # Feed End
                
                # Arc
                ang_in = np.arccos(np.clip(np.dot(v1_u, v2_u), -1.0, 1.0))
                bend_ang = np.pi - ang_in
                bend_radius = t_dist / np.tan(bend_ang / 2.0)
                bisector = v1_u + v2_u
                bisector_norm = np.linalg.norm(bisector)
                if bisector_norm < 1e-9:
                    add_subdivided(path_list[-1] if path_list else pts[0], pts[i])
                    milestones.append(len(path_list)-1); milestones.append(len(path_list)-1)
                    continue
                center_dist = bend_radius / np.sin(ang_in / 2.0)
                center = pts[i] + (bisector / bisector_norm) * center_dist
                r_in, r_out = p_en-center, p_ex-center
                axis = np.cross(r_in, r_out); axis /= np.linalg.norm(axis)
                w = np.cross(axis, r_in)
                arc_steps = max(16, int(np.ceil(abs(bend_ang * bend_radius) / self.sample_step)))
                for j in range(1, arc_steps+1):
                    phi = (j/arc_steps)*bend_ang
                    path_list.append(center + r_in*np.cos(phi) + w*np.sin(phi))
                    # Hassasiyet: Eğer büküm açısı 10 dereceden küçükse deformasyon yapma (Görsel netlik için)
                    d_val = np.sin(np.pi*(j/arc_steps)) if np.degrees(bend_ang) > 10.0 else 0.0
                    def_list.append(d_val)
                milestones.append(len(path_list)-1) # Bend End
            else:
                add_subdivided(path_list[-1] if path_list else pts[0], pts[i])
                milestones.append(len(path_list)-1); milestones.append(len(path_list)-1)
        
        add_subdivided(path_list[-1] if path_list else pts[0], pts[-1]); milestones.append(len(path_list)-1)
        
        path = np.array(path_list); deform = np.array(def_list)
        n_pts = len(path)
        
        # 4. Frozen Frames (T, N, B dondurma)
        normals = np.zeros((n_pts, 3)); binormals = np.zeros((n_pts, 3))
        
        t0 = (path[1]-path[0])/np.linalg.norm(path[1]-path[0])
        up = np.array([0,0,1]) if abs(t0[2]) < 0.9 else np.array([0,1,0])
        n0 = np.cross(up, t0); n0 /= np.linalg.norm(n0); b0 = np.cross(t0, n0)
        normals[0], binormals[0] = n0, b0
        
        for i in range(1, n_pts):
            t_curr = (path[i]-path[i-1])/np.linalg.norm(path[i]-path[i-1])
            t_prev = t0 if i==1 else (path[i-1]-path[i-2])/np.linalg.norm(path[i-1]-path[i-2])
            
            rot_axis = np.cross(t_prev, t_curr)
            if np.linalg.norm(rot_axis) > 1e-10:
                rot_axis /= np.linalg.norm(rot_axis)
                angle = np.arccos(np.clip(np.dot(t_prev, t_curr), -1.0, 1.0))
                # Rodrigues rotation matrix
                x,y,z = rot_axis; c, s = np.cos(angle), np.sin(angle); C = 1-c
                R = np.array([[c+x*x*C, x*y*C-z*s, x*z*C+y*s], [y*x*C+z*s, c+y*y*C, y*z*C-x*s], [z*x*C-y*s, z*y*C+x*s, c+z*z*C]])
                n_new = R @ normals[i-1]; b_new = R @ binormals[i-1]
            else:
                n_new, b_new = normals[i-1], binormals[i-1]
            
            # Re-orthogonalize to t_curr to avoid drift
            n_new = n_new - np.dot(n_new, t_curr)*t_curr; n_new /= np.linalg.norm(n_new)
            b_new = np.cross(t_curr, n_new)
            normals[i], binormals[i] = n_new, b_new

        self._full_path = path; self._full_normals = normals; self._full_binormals = binormals
        self._full_deform = deform; self._milestones = milestones
        if len(path) > 1:
            self._progress_markers = [m / (len(path) - 1) for m in milestones]
        else:
            self._progress_markers = [0.0]
        self.show_slice(len(path))
        self.set_view_iso() # Varsayılan olarak izometrikten aç ve ortala

    def show_progress(self, progress):
        if self._full_path is None or len(self._full_path) < 2:
            return
        clamped = max(0.0, min(float(progress), 1.0))
        max_idx = len(self._full_path) - 1
        end_pos = max(1.0, clamped * max_idx)
        self.show_slice(end_pos + 1.0)

    def show_slice(self, end_idx):
        if self._full_path is None: return
        end_pos = max(1.0, min(float(end_idx), float(len(self._full_path))))
        full_idx = int(np.floor(end_pos))
        frac = end_pos - full_idx
        idx = max(2, min(full_idx, len(self._full_path)))
        
        m_pts = vtk.vtkPoints(); m_polys = vtk.vtkCellArray()
        ring_sides = self.animation_ring_sides if self._animating else self.ring_sides
        theta = np.linspace(0, 2*np.pi, ring_sides, endpoint=False)
        
        for i in range(idx):
            p, n_v, b_v, d_v = self._full_path[i], self._full_normals[i], self._full_binormals[i], self._full_deform[i]
            f_n, f_b = 1.0 + (self.ovality_factor*0.5*d_v), 1.0 - (self.ovality_factor*d_v)
            for ang in theta:
                m_pts.InsertNextPoint(p + self.tube_radius * (f_n*np.cos(ang)*n_v + f_b*np.sin(ang)*b_v))
            if i > 0:
                r0, r1 = (i-1)*ring_sides, i*ring_sides
                for s in range(ring_sides):
                    s_next = (s + 1) % ring_sides
                    poly = vtk.vtkQuad()
                    poly.GetPointIds().SetId(0, r0+s); poly.GetPointIds().SetId(1, r1+s)
                    poly.GetPointIds().SetId(2, r1+s_next); poly.GetPointIds().SetId(3, r0+s_next)
                    m_polys.InsertNextCell(poly)

        if frac > 1e-6 and idx < len(self._full_path):
            p0, p1 = self._full_path[idx-1], self._full_path[idx]
            n0, n1 = self._full_normals[idx-1], self._full_normals[idx]
            b0, b1 = self._full_binormals[idx-1], self._full_binormals[idx]
            d0, d1 = self._full_deform[idx-1], self._full_deform[idx]

            p = p0 + (p1 - p0) * frac
            n_v = n0 + (n1 - n0) * frac
            b_v = b0 + (b1 - b0) * frac
            d_v = d0 + (d1 - d0) * frac

            n_norm = np.linalg.norm(n_v)
            b_norm = np.linalg.norm(b_v)
            if n_norm > 1e-9:
                n_v = n_v / n_norm
            if b_norm > 1e-9:
                b_v = b_v / b_norm

            f_n, f_b = 1.0 + (self.ovality_factor*0.5*d_v), 1.0 - (self.ovality_factor*d_v)
            for ang in theta:
                m_pts.InsertNextPoint(p + self.tube_radius * (f_n*np.cos(ang)*n_v + f_b*np.sin(ang)*b_v))

            r0 = (idx - 1) * ring_sides
            r1 = idx * ring_sides
            for s in range(ring_sides):
                s_next = (s + 1) % ring_sides
                poly = vtk.vtkQuad()
                poly.GetPointIds().SetId(0, r0+s); poly.GetPointIds().SetId(1, r1+s)
                poly.GetPointIds().SetId(2, r1+s_next); poly.GetPointIds().SetId(3, r0+s_next)
                m_polys.InsertNextCell(poly)
            idx += 1

        # Caps
        for r_idx, rev in [(0, False), (idx-1, True)]:
            cap = vtk.vtkPolygon(); cap.GetPointIds().SetNumberOfIds(ring_sides)
            base = r_idx * ring_sides
            for s in range(ring_sides):
                cap.GetPointIds().SetId(s, base + (ring_sides-1-s if rev else s))
            m_polys.InsertNextCell(cap)

        pd = vtk.vtkPolyData(); pd.SetPoints(m_pts); pd.SetPolys(m_polys)
        normals = vtk.vtkPolyDataNormals(); normals.SetInputData(pd); normals.SplittingOff(); normals.Update()
        
        mapper = vtk.vtkPolyDataMapper(); mapper.SetInputData(normals.GetOutput())
        actor = vtk.vtkActor(); actor.SetMapper(mapper)
        pr = actor.GetProperty(); pr.SetColor(0.65, 0.7, 0.75); pr.SetInterpolationToPhong()
        pr.SetSpecular(0.15); pr.SetSpecularPower(12); pr.SetAmbient(0.32); pr.SetDiffuse(0.68)
        
        if self._tube_actor: self.renderer.RemoveActor(self._tube_actor)
        self._tube_actor = actor; self.renderer.AddActor(actor)
        self.vtk_widget.GetRenderWindow().Render()

    def take_screenshot(self, filepath):
        """Mevcut 3D görüntüyü dosyaya kaydeder (Rapor için)."""
        w2i = vtk.vtkWindowToImageFilter()
        w2i.SetInput(self.vtk_widget.GetRenderWindow())
        w2i.SetInputBufferTypeToRGB()
        w2i.ReadFrontBufferOff()
        w2i.Update()
        
        writer = vtk.vtkPNGWriter()
        writer.SetFileName(filepath)
        writer.SetInputConnection(w2i.GetOutputPort())
        writer.Write()

    def update_view(self, points): pass
    def sweep_profile(self, points, clr_list=None): self.calculate_full_geometry(points, clr_list)
