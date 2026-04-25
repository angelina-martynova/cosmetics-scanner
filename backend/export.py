import io
import unicodedata
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
import sys
import traceback

class ScanExporter:
    def __init__(self):
        self._register_fonts()

    def _register_fonts(self):
        """Регистрация шрифтов с поддержкой кириллицы"""
        try:
            try:
                pdfmetrics.getFont('Arial')
                print("Шрифт Arial вже зареєстрований")
                return
            except:
                pass

            font_paths = []

            # Windows
            if sys.platform == 'win32':
                windows_fonts = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts')
                font_paths = [
                    os.path.join(windows_fonts, 'arial.ttf'),
                    os.path.join(windows_fonts, 'Arial.ttf'),
                    os.path.join(windows_fonts, 'ARIAL.TTF')
                ]
            else:
                # Linux / Mac
                font_paths = [
                    '/usr/share/fonts/truetype/msttcorefonts/arial.ttf',
                    '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
                    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                    '/System/Library/Fonts/Arial.ttf',
                    '/Library/Fonts/Arial.ttf'
                ]

            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont('Arial', font_path))
                        print(f"Шрифт Arial зареєстрований з: {font_path}")

                        # Bold вариант
                        bold_path = font_path.replace('.ttf', 'bd.ttf').replace('.TTF', 'bd.TTF')
                        if os.path.exists(bold_path):
                            pdfmetrics.registerFont(TTFont('Arial-Bold', bold_path))
                            print("Шрифт Arial-Bold зареєстрований")
                        return
                    except Exception as e:
                        print(f"Не вдалося зареєструвати {font_path}: {e}")
                        continue

            # Fallback
            print("Використовуємо стандартний шрифт Helvetica")
        except Exception as e:
            print(f"Помилка реєстрації шрифтів: {e}")

    def normalize_text(self, text):
        if not text:
            return ""
        text = str(text).strip()
        text = unicodedata.normalize('NFKC', text)
        replacements = {
            '—': '-', '«': '"', '»': '"', '„': '"', '…': '...'
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    def create_pdf_bytes(self, scan_data, user_email, lang='uk'):
        """Создать PDF с учётом языка"""
        try:
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=0.7*inch,
                leftMargin=0.7*inch,
                topMargin=0.7*inch,
                bottomMargin=0.7*inch
            )
            story = []

            # Шрифты
            styles = getSampleStyleSheet()
            available_fonts = []
            for font_name in ['Arial', 'Helvetica', 'Times-Roman']:
                try:
                    pdfmetrics.getFont(font_name)
                    available_fonts.append(font_name)
                except:
                    pass
            font_name = available_fonts[0] if available_fonts else 'Helvetica'
            bold_font_name = f"{font_name}-Bold" if f"{font_name}-Bold" in available_fonts else font_name

            # Заголовок
            title_text = "ЗВІТ ПО СКАНУВАННЮ КОСМЕТИКИ" if lang == 'uk' else "COSMETICS SCAN REPORT"
            title_style = ParagraphStyle(
                'Title', parent=styles['Title'],
                fontSize=16, textColor=colors.HexColor('#330036'),
                spaceAfter=20, alignment=TA_CENTER, fontName=bold_font_name
            )
            story.append(Paragraph(title_text, title_style))
            story.append(Spacer(1, 15))

            normal_style = ParagraphStyle(
                'Normal', parent=styles['Normal'],
                fontSize=11, textColor=colors.black,
                spaceAfter=8, fontName=font_name, alignment=TA_LEFT
            )

            # Дата
            created_at = scan_data.get('created_at', '')
            formatted_date = "Невідома дата" if lang == 'uk' else "Unknown date"
            if created_at:
                try:
                    if '.' in created_at:
                        created_at = created_at.split('.')[0]
                    if 'Z' in created_at:
                        created_at = created_at.replace('Z', '')
                    for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                        try:
                            dt = datetime.strptime(created_at, fmt)
                            formatted_date = dt.strftime('%d.%m.%Y %H:%M')
                            break
                        except:
                            continue
                except:
                    formatted_date = created_at[:19] if len(created_at) > 19 else created_at

            # Таблица информации
            labels = {
                'id': "ID сканування:" if lang == 'uk' else "Scan ID:",
                'date': "Дата сканування:" if lang == 'uk' else "Scan date:",
                'type': "Тип введення:" if lang == 'uk' else "Input type:",
                'method': "Метод введення:" if lang == 'uk' else "Input method:",
                'status': "Статус безпеки:" if lang == 'uk' else "Safety status:",
                'count': "Кількість інгредієнтів:" if lang == 'uk' else "Ingredients count:",
                'user': "Користувач:" if lang == 'uk' else "User:"
            }
            info_data = [
                [labels['id'], str(scan_data.get('id', 'N/A'))],
                [labels['date'], formatted_date],
                [labels['type'], self._get_type_text(scan_data.get('input_type', ''), lang)],
                [labels['method'], self._get_method_text(scan_data.get('input_method', ''), lang)],
                [labels['status'], self._get_safety_status_text(scan_data.get('safety_status', 'safe'), lang)],
                [labels['count'], str(scan_data.get('ingredients_count', 0))],
                [labels['user'], user_email]
            ]

            info_table = Table(info_data, colWidths=[130, 340])
            info_table.setStyle(TableStyle([
                ('FONTNAME', (0,0), (-1,-1), font_name),
                ('FONTSIZE', (0,0), (-1,-1), 11),
                ('BOTTOMPADDING', (0,0), (-1,-1), 8),
                ('TOPPADDING', (0,0), (-1,-1), 8),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('ALIGN', (0,0), (0,-1), 'RIGHT'),
                ('ALIGN', (1,0), (1,-1), 'LEFT'),
                ('FONTNAME', (0,0), (0,-1), bold_font_name),
            ]))
            story.append(info_table)
            story.append(Spacer(1, 20))

            # Оригинальный текст
            original_text = scan_data.get('original_text')
            if original_text:
                heading_style = ParagraphStyle(
                    'Heading', parent=normal_style,
                    fontSize=12, fontName=bold_font_name,
                    spaceAfter=10, spaceBefore=15
                )
                orig_title = "Оригінальний текст:" if lang == 'uk' else "Original text:"
                story.append(Paragraph(orig_title, heading_style))
                story.append(Spacer(1, 8))

                text_style = ParagraphStyle(
                    'Text', parent=normal_style,
                    fontSize=10, leading=12,
                    fontName=font_name, alignment=TA_JUSTIFY
                )
                text = str(original_text)[:1500]
                for line in text.split('\n'):
                    line = line.strip()
                    if line:
                        story.append(Paragraph(self.normalize_text(line), text_style))
                        story.append(Spacer(1, 4))
                story.append(Spacer(1, 20))

            # Ингредиенты
            ingredients = scan_data.get('ingredients_detailed') or scan_data.get('ingredients', [])
            if ingredients:
                ing_title = f"Знайдені інгредієнти ({len(ingredients)}):" if lang == 'uk' else f"Found ingredients ({len(ingredients)}):"
                story.append(Paragraph(ing_title, heading_style))
                story.append(Spacer(1, 8))

                list_style = ParagraphStyle(
                    'List', parent=normal_style,
                    fontSize=10, leftIndent=20,
                    firstLineIndent=-20, spaceAfter=4
                )
                for i, ing in enumerate(ingredients[:30], 1):
                    if isinstance(ing, dict):
                        name = ing.get('name', '')
                        risk = ing.get('risk_level', 'unknown')
                        risk_text = self._get_risk_text(risk, lang)
                        story.append(Paragraph(f"{i}. {name} ({risk_text})", list_style))
                if len(ingredients) > 30:
                    more = f"... та ще {len(ingredients)-30} інгредієнтів" if lang == 'uk' else f"... and {len(ingredients)-30} more ingredients"
                    story.append(Paragraph(more, normal_style))
                story.append(Spacer(1, 20))

            # Рекомендации
            rec_title = "Рекомендації та висновки:" if lang == 'uk' else "Recommendations & Conclusions:"
            rec_heading_style = ParagraphStyle(
                'RecHeading', parent=normal_style,
                fontSize=13, fontName=bold_font_name,
                textColor=colors.HexColor('#2A002D'),
                spaceAfter=12, spaceBefore=20
            )
            story.append(Paragraph(rec_title, rec_heading_style))
            story.append(Spacer(1, 10))

            safety_status = scan_data.get('safety_status', 'safe')
            recommendations = self._get_recommendations(safety_status, lang)
            rec_style = ParagraphStyle(
                'Recommendation', parent=normal_style,
                leftIndent=20, firstLineIndent=-20,
                spaceAfter=8
            )
            for rec in recommendations:
                story.append(Paragraph(f"• {self.normalize_text(rec)}", rec_style))
            story.append(Spacer(1, 30))

            # Футер
            footer_style = ParagraphStyle(
                'Footer', parent=normal_style,
                fontSize=9, textColor=colors.grey,
                spaceAfter=6, alignment=TA_CENTER
            )
            footer1 = f"Звіт створено: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}" if lang == 'uk' else f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            footer2 = "Згенеровано за допомогою Skipley - сканера косметичних інгредієнтів" if lang == 'uk' else "Generated by Skipley - Cosmetic Ingredient Scanner"
            story.append(Paragraph(footer1, footer_style))
            story.append(Paragraph(footer2, footer_style))

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
        """Запасной PDF при ошибке"""
        try:
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            styles = getSampleStyleSheet()
            story = [
                Paragraph("ПОМИЛКА ПРИ СТВОРЕННІ ЗВІТУ", styles['Title']),
                Spacer(1, 20),
                Paragraph(f"Помилка: {error_message}", styles['Normal']),
                Spacer(1, 20),
                Paragraph("Будь ласка, спробуйте ще раз або зверніться до адміністратора.", styles['Normal'])
            ]
            doc.build(story)
            return buffer.getvalue()
        except:
            return b''

    # ---------- Вспомогательные методы с языком ----------
    def _get_type_text(self, type_code, lang):
        if lang == 'uk':
            return {'manual': 'Текст', 'camera': 'Фото'}.get(type_code, 'Невідомий тип')
        return {'manual': 'Text', 'camera': 'Photo'}.get(type_code, 'Unknown type')

    def _get_method_text(self, method_code, lang):
        if lang == 'uk':
            return {'text': 'Ручний ввід', 'device': 'З пристрою', 'camera': 'Камера'}.get(method_code, 'Невідомий метод')
        return {'text': 'Manual input', 'device': 'From device', 'camera': 'Camera'}.get(method_code, 'Unknown method')

    def _get_safety_status_text(self, status, lang):
        if lang == 'uk':
            return {
                'danger': 'Високий ризик', 'high': 'Високий ризик',
                'warning': 'Середній ризик', 'medium': 'Середній ризик',
                'safe': 'Безпечно', 'low': 'Низький ризик'
            }.get(status, 'Невідомий статус')
        return {
            'danger': 'High risk', 'high': 'High risk',
            'warning': 'Medium risk', 'medium': 'Medium risk',
            'safe': 'Safe', 'low': 'Low risk'
        }.get(status, 'Unknown status')

    def _get_risk_text(self, risk_level, lang):
        if lang == 'uk':
            return {
                'high': 'Високий', 'danger': 'Високий',
                'medium': 'Середній', 'warning': 'Середній',
                'low': 'Низький', 'safe': 'Безпечний', 'unknown': 'Невідомий'
            }.get(risk_level, 'Невідомий')
        return {
            'high': 'High', 'danger': 'High',
            'medium': 'Medium', 'warning': 'Medium',
            'low': 'Low', 'safe': 'Safe', 'unknown': 'Unknown'
        }.get(risk_level, 'Unknown')

    def _get_recommendations(self, safety_status, lang):
        if safety_status in ['danger', 'high']:
            if lang == 'uk':
                return [
                    "Продукт містить інгредієнти високого ризику.",
                    "Рекомендуємо уникати регулярного використання.",
                    "Розгляньте альтернативні продукти без небезпечних компонентів.",
                    "Консультуйтеся з дерматологом при виникненні подразнень."
                ]
            return [
                "Product contains high-risk ingredients.",
                "Avoid regular use of this product.",
                "Consider alternative products without hazardous components.",
                "Consult a dermatologist if irritation occurs."
            ]
        elif safety_status in ['warning', 'medium']:
            if lang == 'uk':
                return [
                    "Продукт містить інгредієнти середнього ризику.",
                    "Використовуйте продукт з обережністю та спостерігайте за реакцією шкіри.",
                    "Не використовуйте продукт на пошкодженій шкірі.",
                    "При тривалому використанні робіть перерви."
                ]
            return [
                "Product contains moderate-risk ingredients.",
                "Use with caution and monitor skin reaction.",
                "Do not apply to damaged skin.",
                "Take breaks during prolonged use."
            ]
        else:
            if lang == 'uk':
                return [
                    "Продукт відносно безпечний для використання.",
                    "Дотримуйтесь інструкцій використання від виробника.",
                    "Проводьте тест на алергію перед першим використанням.",
                    "Зберігайте продукт відповідно до вказівок виробника."
                ]
            return [
                "Product is relatively safe to use.",
                "Follow the manufacturer's instructions.",
                "Perform an allergy test before first use.",
                "Store the product as recommended."
            ]