import datetime
from fpdf import FPDF
import os

class ReportGenerator:
    """
    Industrial PDF Report Generator based on reference/example-data.pdf
    """
    
    @staticmethod
    def generate_report(filepath, part_info, xyz_data, lra_data, image_path=None):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("helvetica", "B", 16)
        
        # Header
        pdf.cell(0, 10, "BENDING PRODUCTION REPORT", ln=True, align='C')
        pdf.set_line_width(0.5)
        pdf.line(10, 20, 200, 20)
        pdf.ln(10)
        
        # Part Information
        pdf.set_font("helvetica", "B", 10)
        col_width = 45
        
        infos = [
            ("PART NUMBER:", part_info.get('part_no', '')),
            ("USERNAME:", part_info.get('username', '')),
            ("CUSTOMER:", part_info.get('customer', '')),
            ("REVISION:", part_info.get('revision', '')),
            ("TUBE OD (mm):", str(part_info.get('od', ''))),
            ("DATE:", datetime.datetime.now().strftime("%d.%m.%Y %H:%M")),
            ("MATERIAL:", part_info.get('material', '')),
            ("NET LENGTH:", f"{part_info.get('total_length', 0):.3f} mm")
        ]
        
        # Draw 2 columns of info
        for i in range(0, len(infos), 2):
            pdf.set_font("helvetica", "B", 9)
            pdf.cell(col_width, 7, infos[i][0])
            pdf.set_font("helvetica", "", 9)
            pdf.cell(col_width, 7, infos[i][1])
            
            if i+1 < len(infos):
                pdf.set_font("helvetica", "B", 9)
                pdf.cell(col_width, 7, infos[i+1][0])
                pdf.set_font("helvetica", "", 9)
                pdf.cell(col_width, 7, infos[i+1][1])
            pdf.ln(7)
            
        pdf.ln(5)
        
        # 3D Model Image
        if image_path and os.path.exists(image_path):
            pdf.set_font("helvetica", "B", 10)
            pdf.cell(0, 10, "3D MODEL VISUALIZATION", ln=True)
            pdf.image(image_path, x=10, w=180)
            pdf.ln(5)
            
        # XYZ Data Table
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(0, 10, "XYZ COORDINATE DATA", ln=True)
        pdf.set_font("helvetica", "B", 8)
        pdf.set_fill_color(240, 240, 240)
        
        headers = ["Point", "X (mm)", "Y (mm)", "Z (mm)", "CLR (mm)"]
        w = [15, 43, 43, 43, 43]
        for i, h in enumerate(headers):
            pdf.cell(w[i], 7, h, border=1, align='C', fill=True)
        pdf.ln()
        
        pdf.set_font("helvetica", "", 8)
        for i, pt in enumerate(xyz_data):
            # pt: [x, y, z, clr]
            pdf.cell(w[0], 6, str(i+1), border=1, align='C')
            pdf.cell(w[1], 6, f"{pt[0]:.3f}", border=1, align='C')
            pdf.cell(w[2], 6, f"{pt[1]:.3f}", border=1, align='C')
            pdf.cell(w[3], 6, f"{pt[2]:.3f}", border=1, align='C')
            pdf.cell(w[4], 6, f"{pt[3]:.3f}" if pt[3]>0 else "-", border=1, align='C')
            pdf.ln()
            
        pdf.ln(5)
        
        # LRA Data Table
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(0, 10, "LRA BENDING DATA", ln=True)
        pdf.set_font("helvetica", "B", 8)
        pdf.set_fill_color(240, 240, 240)
        
        lra_headers = ["Bend", "Length (mm)", "Arc (mm)", "Rotation (°)", "Angle (°)", "CLR (mm)"]
        lw = [15, 35, 35, 35, 35, 32]
        for i, h in enumerate(lra_headers):
            pdf.cell(lw[i], 7, h, border=1, align='C', fill=True)
        pdf.ln()
        
        pdf.set_font("helvetica", "", 8)
        for i, row in enumerate(lra_data):
            pdf.cell(lw[0], 6, str(i+1), border=1, align='C')
            pdf.cell(lw[1], 6, f"{row['L']:.3f}", border=1, align='C')
            pdf.cell(lw[2], 6, f"{row['Arc']:.3f}" if row['Arc']>0 else "0.000", border=1, align='C')
            pdf.cell(lw[3], 6, f"{row['R']:.3f}", border=1, align='C')
            pdf.cell(lw[4], 6, f"{row['A']:.3f}", border=1, align='C')
            pdf.cell(lw[5], 6, f"{row['CLR']:.3f}" if row['CLR']>0 else "-", border=1, align='C')
            pdf.ln()
            
        # Final Length
        last_l = lra_data[-1].get('L_final', 0) if lra_data else 0 # Need to handle final straight
        # Actually total length was in part_info
        
        pdf.output(filepath)
        return True
