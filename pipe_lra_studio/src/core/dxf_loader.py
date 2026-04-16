import ezdxf
import numpy as np

class DXFProfileLoader:
    """
    DXF dosyasından 2B kesit (boru profili) verilerini okuyan sınıf.
    """
    
    @staticmethod
    def load_profile(dxf_path):
        """
        DXF dosyasındaki LWPOLYLINE veya CIRCLE objelerini okuyarak 
        bir nokta listesi (Vektör listesi) döndürür.
        """
        try:
            doc = ezdxf.readfile(dxf_path)
            msp = doc.modelspace()
            
            points = []
            
            # 1. Polylineları kontrol et
            polylines = msp.query('LWPOLYLINE')
            if polylines:
                # En az bir poligon varsa ilkinden noktaları al
                pline = polylines[0]
                points = [ (p[0], p[1]) for p in pline.get_points() ]
                # Kapalı değilse kapat
                if not pline.is_closed:
                    points.append(points[0])
            
            # 2. Polylines yoksa Çemberleri kontrol et
            else:
                circles = msp.query('CIRCLE')
                if circles:
                    circle = circles[0]
                    center = circle.dxf.center
                    radius = circle.dxf.radius
                    # Çemberi 32 noktalı bir poligona çevir
                    segments = 32
                    for i in range(segments + 1):
                        angle = 2 * np.pi * i / segments
                        x = center.x + radius * np.cos(angle)
                        y = center.y + radius * np.sin(angle)
                        points.append((x, y))
            
            if not points:
                # Varsayılan olarak 20mm çapında bir daire döndür
                radius = 10.0
                segments = 32
                points = []
                for i in range(segments + 1):
                    angle = 2 * np.pi * i / segments
                    points.append((radius * np.cos(angle), radius * np.sin(angle)))
            
            return np.array(points)

        except Exception as e:
            print(f"DXF yükleme hatası: {e}")
            # Hata durumunda varsayılan daire
            radius = 10.0
            segments = 32
            points = [(radius * np.cos(2*np.pi*i/segments), radius * np.sin(2*np.pi*i/segments)) for i in range(segments+1)]
            return np.array(points)
