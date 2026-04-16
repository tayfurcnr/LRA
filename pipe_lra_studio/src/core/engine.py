import numpy as np

class BendingEngine:
    """
    XYZ koordinatlarını LRA (Length, Rotation, Angle) formatına dönüştüren motor.
    """
    
    @staticmethod
    def calculate_lra(points, bend_radius=0.0):
        """
        XYZ noktalarını LRA formatına dönüştürür.
        bend_radius: Tek bir float veya her büküm için ayrı float içeren bir liste.
        """
        points = np.array(points, dtype=float)
        # Filter consecutive duplicates to avoid division by zero (NaN)
        filtered = [points[0]]
        for i in range(1, len(points)):
            if np.linalg.norm(points[i] - points[i-1]) > 1e-6:
                filtered.append(points[i])
        points = np.array(filtered)
        
        if len(points) < 2:
            return [], [], 0.0

        # Vektörleri oluştur
        vectors = np.diff(points, axis=0)
        
        # Büküm açılarını hesapla
        angles = []
        for i in range(len(vectors) - 1):
            v1 = vectors[i]
            v2 = vectors[i+1]
            mag1 = np.linalg.norm(v1)
            mag2 = np.linalg.norm(v2)
            
            cos_theta = np.dot(v1, v2) / (mag1 * mag2)
            cos_theta = np.clip(cos_theta, -1.0, 1.0)
            bend_angle_rad = np.arccos(cos_theta)
            angles.append(np.degrees(bend_angle_rad))
            
        # Tanjant (Yay payı) hesapla - Her büküm için ayrı CLR olabilir
        tangents = [0.0] * len(angles)
        clrs = []
        for i, bend_angle in enumerate(angles):
            if isinstance(bend_radius, list):
                r = bend_radius[i] if i < len(bend_radius) else bend_radius[-1]
            else:
                r = bend_radius
            
            bend_angle_rad = np.radians(bend_angle)
            t = r * np.tan(bend_angle_rad / 2) if r > 0 else 0
            tangents[i] = t
            clrs.append(r)

        # Tanjantları kısıtla ve Uyarıları Topla
        warnings = []
        for i in range(len(vectors)):
            dist = np.linalg.norm(vectors[i])
            t_prev = tangents[i-1] if i > 0 else 0
            t_curr = tangents[i] if i < len(tangents) else 0
            
            if t_prev + t_curr > dist * 0.99:
                warnings.append(f"Segment {i+1} çok kısa! Bükümler iç içe geçiyor. Radius değerleri otomatik küçültüldü.")
                scale = (dist * 0.98) / (t_prev + t_curr)
                if i > 0: tangents[i-1] *= scale
                if i < len(tangents): tangents[i] *= scale
                
                # CLR'leri güncelle
                if i > 0:
                    ang_rad = np.radians(angles[i-1])
                    if ang_rad > 0: clrs[i-1] = tangents[i-1] / np.tan(ang_rad / 2)
                if i < len(clrs):
                    ang_rad = np.radians(angles[i])
                    if ang_rad > 0: clrs[i] = tangents[i] / np.tan(ang_rad / 2)

        # İkinci geçiş: Rotasyonları hesapla (büküm düzlemi bazlı)
        plane_normals = []
        for i in range(len(vectors) - 1):
            v1 = vectors[i]
            v2 = vectors[i+1]
            n = np.cross(v1, v2)
            norm_val = np.linalg.norm(n)
            if norm_val < 1e-9:
                n = plane_normals[-1] if plane_normals else np.array([0., 0., 1.])
            else:
                n = n / norm_val
            plane_normals.append(n)
        
        rotations = [0.0] * len(plane_normals)
        for i in range(1, len(plane_normals)):
            cos_rot = np.dot(plane_normals[i-1], plane_normals[i])
            cos_rot = np.clip(cos_rot, -1.0, 1.0)
            rot_rad = np.arccos(cos_rot)
            cross_n = np.cross(plane_normals[i-1], plane_normals[i])
            if np.dot(vectors[i], cross_n) < 0:
                rot_rad = -rot_rad
            rotations[i] = np.degrees(rot_rad)
        
        # Üçüncü geçiş: L, R, A, Arc, CLR birleştir
        lra_results = []
        for i in range(len(vectors)):
            v = vectors[i]
            mag = np.linalg.norm(v)
            
            t_prev = tangents[i-1] if i > 0 else 0.0
            t_curr = tangents[i] if i < len(vectors)-1 else 0.0
            l_val = mag - t_prev - t_curr
            
            bend_angle = angles[i] if i < len(vectors)-1 else 0.0
            rotation = rotations[i] if i < len(plane_normals) else 0.0
            r_val = clrs[i] if i < len(clrs) else 0.0
            
            arc_length = 0.0
            if bend_angle > 0 and r_val > 0:
                arc_length = r_val * np.radians(bend_angle)
                
            lra_results.append({
                'L': l_val,
                'R': rotation,
                'A': bend_angle,
                'Arc': arc_length,
                'CLR': r_val if i < len(vectors)-1 else 0.0
            })
            
        total_length = sum(r['L'] + r['Arc'] for r in lra_results)
        return lra_results, warnings, total_length

# Test Amaçlı
if __name__ == "__main__":
    test_points = [
        [0, 0, 0],
        [100, 0, 0],
        [100, 100, 0],
        [100, 100, 100]
    ]
    results = BendingEngine.calculate_lra(test_points, bend_radius=[20.0, 40.0])
    for i, res in enumerate(results):
        print(f"Seg {i+1}: L={res['L']:.2f}, R={res['R']:.2f}, A={res['A']:.2f}, CLR={res['CLR']:.2f}")
