import csv
import io

class CsvReportService:

    @staticmethod
    def generate_csv(headers: list, rows: list) -> io.BytesIO:
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers and data rows
        writer.writerow(headers)
        for row in rows:
            writer.writerow(row)

        mem = io.BytesIO()
        # Prepend UTF-8 BOM so Excel decodes rupee symbol (₹) correctly
        mem.write(b'\xef\xbb\xbf')
        mem.write(output.getvalue().encode("utf-8"))
        mem.seek(0)
        return mem
