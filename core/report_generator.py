from fpdf import FPDF
import datetime
import os

class ReportGenerator:
    def __init__(self, data_manager):
        self.data_manager = data_manager

    def generate_pdf(self, output_path, charts=None):
        """تولید گزارش PDF شامل آمار و نمودارها"""
        try:
            pdf = FPDF()
            pdf.add_page()
            
            # Header
            pdf.set_font("Arial", 'B', 20)
            pdf.cell(0, 10, "DataSense Analysis Report", ln=True, align='C')
            pdf.set_font("Arial", size=12)
            pdf.cell(0, 10, f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')
            pdf.ln(10)

            # Data Summary
            if self.data_manager.df is not None:
                pdf.set_font("Arial", 'B', 14)
                pdf.cell(0, 10, "Dataset Summary:", ln=True)
                pdf.set_font("Arial", size=10)
                
                summary = self.data_manager.df.describe().to_string()
                pdf.multi_cell(0, 5, summary)
                pdf.ln(10)

                # Columns info
                pdf.set_font("Arial", 'B', 14)
                pdf.cell(0, 10, "Columns Info:", ln=True)
                pdf.set_font("Arial", size=10)
                cols_info = "\n".join([f"- {col} ({self.data_manager.df[col].dtype})" for col in self.data_manager.df.columns])
                pdf.multi_cell(0, 5, cols_info)
            
            # Charts (if provided as file paths)
            if charts:
                for chart_path in charts:
                    if os.path.exists(chart_path):
                        pdf.add_page()
                        pdf.image(chart_path, x=10, y=20, w=190)
            
            pdf.output(output_path)
            return True, "Report generated successfully!"
        except Exception as e:
            return False, str(e)
