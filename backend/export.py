import io
import unicodedata
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable)
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.lib.units import inch, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os, sys, traceback

class ScanExporter:
    def __init__(self):
        self._register_fonts()

    def _register_fonts(self):
        try:
            try:
                pdfmetrics.getFont('Arial')
                print("Шрифт Arial вже зареєстрований")
                return
            except:
                pass
            font_paths = []
            if sys.platform == 'win32':
                windows_fonts = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts')
                font_paths = [os.path.join(windows_fonts, 'arial.ttf'), os.path.join(windows_fonts, 'Arial.ttf'), os.path.join(windows_fonts, 'ARIAL.TTF')]
            else:
                font_paths = ['/usr/share/fonts/truetype/msttcorefonts/arial.ttf', '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/System/Library/Fonts/Arial.ttf', '/Library/Fonts/Arial.ttf']
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont('Arial', font_path))
                        bold_path = font_path.replace('.ttf', 'bd.ttf').replace('.TTF', 'bd.TTF')
                        if os.path.exists(bold_path): pdfmetrics.registerFont(TTFont('Arial-Bold', bold_path))
                        return
                    except: continue
            print("Використовуємо стандартний шрифт Helvetica")
        except Exception as e: print(f"Помилка реєстрації шрифтів: {e}")

    def normalize_text(self, text):
        if not text: return ""
        text = str(text).strip()
        text = unicodedata.normalize('NFKC', text)
        replacements = {'—': '-', '«': '"', '»': '"', '„': '"', '…': '...'}
        for old, new in replacements.items(): text = text.replace(old, new)
        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        return text

    def create_pdf_bytes(self, scan_data, user_email, lang='uk'):
        try:
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=15*mm, leftMargin=15*mm, topMargin=12*mm, bottomMargin=12*mm)
            story = []

            styles = getSampleStyleSheet()
            available = []
            for f in ['Arial','Helvetica','Times-Roman']:
                try:
                    pdfmetrics.getFont(f)
                    available.append(f)
                except: pass
            font_name = available[0] if available else 'Helvetica'
            bold_font_name = f"{font_name}-Bold" if f"{font_name}-Bold" in available else font_name
            TEXT_COLOR = colors.HexColor('#1A1816')
            MUTED_COLOR = colors.HexColor('#4D4640')

            # ─── ШАПКА ───
            created_at = scan_data.get('created_at', '')
            formatted_date = "—"
            if created_at:
                try:
                    if '.' in created_at: created_at = created_at.split('.')[0]
                    if 'Z' in created_at: created_at = created_at.replace('Z', '')
                    for fmt in ['%Y-%m-%dT%H:%M:%S','%Y-%m-%d %H:%M:%S','%Y-%m-%d']:
                        try:
                            dt = datetime.strptime(created_at, fmt)
                            formatted_date = dt.strftime('%d.%m.%Y %H:%M')
                            break
                        except: continue
                except: formatted_date = created_at[:19] if len(created_at) > 19 else created_at

            input_method = scan_data.get('input_method') or 'text'
            safety_status = scan_data.get('safety_status') or 'safe'

            header_left = Paragraph(
                f'<font size="18"><b>Skipley</b></font><br/>'
                f'<font size="8" color="{MUTED_COLOR}">'
                f'{self._get_method_text(input_method, lang)} &nbsp;·&nbsp; {formatted_date}'
                f'</font>',
                ParagraphStyle('HLeft', fontName=font_name, textColor=TEXT_COLOR, alignment=TA_LEFT, leading=22)
            )
            header_right = Paragraph(
                f'<font size="9" color="{MUTED_COLOR}">{ "Статус" if lang == "uk" else "Status" }</font><br/>'
                f'<font size="11"><b>{self._get_safety_status_text(safety_status, lang)}</b></font>',
                ParagraphStyle('HRight', fontName=font_name, textColor=TEXT_COLOR, alignment=TA_RIGHT, leading=16)
            )

            header_table = Table([[header_left, header_right]], colWidths=[doc.width*0.7, doc.width*0.3])
            header_table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'), ('LEFTPADDING',(0,0),(-1,-1),0), ('RIGHTPADDING',(0,0),(-1,-1),0)]))
            story.append(header_table)
            story.append(Spacer(1, 4*mm))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#E0DCD5')))
            story.append(Spacer(1, 8*mm))

            # ─── ОРИГИНАЛЬНЫЙ ТЕКСТ ───
            heading_style = ParagraphStyle('H2', fontName=bold_font_name, fontSize=11, textColor=TEXT_COLOR, spaceAfter=3*mm)
            original_text = scan_data.get('original_text')
            if original_text:
                story.append(Paragraph("Оригінальний текст" if lang=='uk' else "Original text", heading_style))
                text_style = ParagraphStyle('Orig', fontName=font_name, fontSize=8, leading=10, textColor=TEXT_COLOR, alignment=TA_JUSTIFY)
                for line in str(original_text)[:2000].split('\n'):
                    line = line.strip()
                    if line:
                        story.append(Paragraph(self.normalize_text(line), text_style))
                        story.append(Spacer(1,2))
                story.append(Spacer(1,8*mm))

            # ─── ИНГРЕДИЕНТЫ (простая таблица) ───
            ingredients = scan_data.get('ingredients_detailed') or scan_data.get('ingredients', [])
            if ingredients:
                story.append(Paragraph(f"Знайдені інгредієнти ({len(ingredients)})" if lang=='uk' else f"Found ingredients ({len(ingredients)})", heading_style))
                story.append(Spacer(1,3*mm))

                table_data = []
                if lang=='uk':
                    table_data.append(['№', 'Назва інгредієнта', 'Ризик', 'Опис'])
                else:
                    table_data.append(['#', 'Ingredient name', 'Risk', 'Description'])

                cell = ParagraphStyle('Cell', fontName=font_name, fontSize=9, textColor=TEXT_COLOR, leading=12)
                bold_cell = ParagraphStyle('BoldCell', fontName=bold_font_name, fontSize=9, textColor=TEXT_COLOR, leading=12)
                num_style = ParagraphStyle('Num', fontName=font_name, fontSize=9, textColor=TEXT_COLOR, leading=12)

                for i, ing in enumerate(ingredients[:30], 1):
                    if isinstance(ing, dict):
                        name = self.normalize_text(ing.get('name','—'))
                        risk = ing.get('risk_level','unknown')
                        risk_text = self._get_risk_text(risk, lang)
                        desc = ing.get('description','') if lang=='uk' else ing.get('description_en','')
                        desc = (desc[:120]+'...') if len(desc)>120 else desc
                        desc = self.normalize_text(desc)

                        table_data.append([
                            Paragraph(str(i), num_style),
                            Paragraph(name, cell),
                            Paragraph(f'<b>{risk_text}</b>', bold_cell),
                            Paragraph(desc, cell)
                        ])

                available_width = doc.width
                col_widths = [8*mm, available_width*0.35, available_width*0.15, available_width*0.5 - 8*mm]

                ing_table = Table(table_data, colWidths=col_widths, repeatRows=1)
                table_style = TableStyle([
                    ('FONTNAME',(0,0),(-1,-1), font_name),
                    ('FONTSIZE',(0,0),(-1,-1),9),
                    ('TEXTCOLOR',(0,0),(-1,-1), TEXT_COLOR),
                    ('BOTTOMPADDING',(0,0),(-1,-1),4),
                    ('TOPPADDING',(0,0),(-1,-1),4),
                    ('BACKGROUND',(0,0),(-1,0), colors.HexColor('#F5F5F5')),
                    ('LINEBELOW',(0,0),(-1,0),0.5, colors.HexColor('#CCCCCC')),
                    ('VALIGN',(0,0),(-1,-1),'TOP'),
                    ('ALIGN',(0,0),(0,-1),'CENTER'),
                ])
                ing_table.setStyle(table_style)
                story.append(ing_table)
                story.append(Spacer(1,10*mm))

            # ─── РЕКОМЕНДАЦИИ ───
            rec_title = "Рекомендації" if lang=='uk' else "Recommendations"
            story.append(Paragraph(rec_title, heading_style))
            recommendations = self._get_recommendations(safety_status, lang)
            rec_style = ParagraphStyle('Rec', fontName=font_name, fontSize=10, textColor=TEXT_COLOR, leftIndent=8*mm, firstLineIndent=-8*mm, spaceAfter=4)
            for rec in recommendations:
                story.append(Paragraph(f"• {self.normalize_text(rec)}", rec_style))
            story.append(Spacer(1,12*mm))

            # ─── ФУТЕР ───
            footer_style = ParagraphStyle('Footer', fontName=font_name, fontSize=8, textColor=MUTED_COLOR, alignment=TA_CENTER)
            footer_text = f"Звіт створено: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')} | Skipley — Cosmetics Ingredient Scanner"
            if lang!='uk': footer_text = f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Skipley — Cosmetics Ingredient Scanner"
            story.append(Paragraph(footer_text, footer_style))

            doc.build(story)
            pdf_bytes = buffer.getvalue()
            buffer.close()
            print(f"PDF створено, розмір: {len(pdf_bytes)} байт")
            return pdf_bytes

        except Exception as e:
            print(f"Помилка створення PDF: {e}")
            traceback.print_exc()
            return self._create_error_pdf(str(e))

    def _create_error_pdf(self, error_message):
        try:
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            styles = getSampleStyleSheet()
            story = [Paragraph("ПОМИЛКА ПРИ СТВОРЕННІ ЗВІТУ", styles['Title']), Spacer(1,20),
                     Paragraph(f"Помилка: {error_message}", styles['Normal']), Spacer(1,20),
                     Paragraph("Будь ласка, спробуйте ще раз або зверніться до адміністратора.", styles['Normal'])]
            doc.build(story)
            return buffer.getvalue()
        except: return b''

    # вспомогательные методы (остались прежние)
    def _get_method_text(self, method_code, lang):
        if lang=='uk':
            return {'text':'Ручний ввід','device':'З пристрою','camera':'Камера','gallery':'Галерея'}.get(method_code, method_code or '—')
        return {'text':'Manual input','device':'From device','camera':'Camera','gallery':'Gallery'}.get(method_code, method_code or '—')

    def _get_safety_status_text(self, status, lang):
        mapping = {'danger':('Високий ризик','High risk'),'high':('Високий ризик','High risk'),'warning':('Середній ризик','Medium risk'),'medium':('Середній ризик','Medium risk'),'safe':('Безпечно','Safe'),'low':('Низький ризик','Low risk')}
        return mapping.get(status, (status.capitalize(),status.capitalize()))[0 if lang=='uk' else 1]

    def _get_risk_text(self, risk_level, lang):
        mapping = {'high':('Високий','High'),'danger':('Високий','High'),'medium':('Середній','Medium'),'warning':('Середній','Medium'),'low':('Низький','Low'),'safe':('Безпечний','Safe'),'unknown':('Невідомий','Unknown')}
        return mapping.get(risk_level, (risk_level,risk_level))[0 if lang=='uk' else 1]

    def _get_recommendations(self, safety_status, lang):
        if safety_status in ['danger','high']:
            if lang=='uk': return ["Продукт містить інгредієнти високого ризику.","Рекомендуємо уникати регулярного використання.","Розгляньте альтернативні продукти без небезпечних компонентів.","Консультуйтеся з дерматологом при виникненні подразнень."]
            return ["Product contains high-risk ingredients.","Avoid regular use.","Consider alternative products without hazardous components.","Consult a dermatologist if irritation occurs."]
        elif safety_status in ['warning','medium']:
            if lang=='uk': return ["Продукт містить інгредієнти середнього ризику.","Використовуйте з обережністю.","Не використовуйте на пошкодженій шкірі.","При тривалому використанні робіть перерви."]
            return ["Product contains moderate-risk ingredients.","Use with caution.","Do not apply to damaged skin.","Take breaks during prolonged use."]
        else:
            if lang=='uk': return ["Продукт відносно безпечний.","Дотримуйтесь інструкцій виробника.","Проводьте тест на алергію перед першим використанням.","Зберігайте продукт відповідно до вказівок."]
            return ["Product is relatively safe.","Follow manufacturer's instructions.","Perform an allergy test before first use.","Store as recommended."]