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

class ScanExporter:
    def __init__(self):
        # Попробуем зарегистрировать Arial для поддержки кириллицы
        self._register_fonts()
    
    def _register_fonts(self):
        """Попытаться зарегистрировать шрифты, поддерживающие кириллицу"""
        try:
            # Проверяем, не зарегистрирован ли уже Arial
            try:
                pdfmetrics.getFont('Arial')
                print("✅ Шрифт Arial уже зарегистрирован")
                return
            except:
                pass
            
            # Список возможных путей к шрифтам Arial
            font_paths = []
            
            # Для Windows
            if sys.platform == 'win32':
                windows_fonts = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts')
                font_paths.extend([
                    os.path.join(windows_fonts, 'arial.ttf'),
                    os.path.join(windows_fonts, 'arial.ttf'),
                    os.path.join(windows_fonts, 'Arial.ttf'),
                    os.path.join(windows_fonts, 'ARIAL.TTF')
                ])
            
            # Для Linux/Mac
            else:
                font_paths.extend([
                    '/usr/share/fonts/truetype/msttcorefonts/arial.ttf',
                    '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
                    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                    '/System/Library/Fonts/Arial.ttf',
                    '/Library/Fonts/Arial.ttf'
                ])
            
            # Пробуем найти и зарегистрировать шрифт
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont('Arial', font_path))
                        print(f"✅ Шрифт Arial зарегистрирован из: {font_path}")
                        
                        # Пробуем также зарегистрировать жирную версию
                        bold_path = font_path.replace('.ttf', 'bd.ttf').replace('.TTF', 'bd.TTF')
                        if os.path.exists(bold_path):
                            pdfmetrics.registerFont(TTFont('Arial-Bold', bold_path))
                            print(f"✅ Шрифт Arial-Bold зарегистрирован")
                        
                        return
                    except Exception as e:
                        print(f"⚠️ Не удалось зарегистрировать шрифт {font_path}: {e}")
                        continue
            
            # Если не нашли Arial, попробуем DejaVu Sans
            try:
                # DejaVu Sans обычно есть в Linux
                pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
                print("✅ Используем DejaVuSans как альтернативу")
            except:
                # В последнюю очередь используем Helvetica (должен поддерживать кириллицу в PDF)
                print("ℹ️ Используем стандартный шрифт Helvetica")
                
        except Exception as e:
            print(f"⚠️ Ошибка при регистрации шрифтов: {e}")
    
    def normalize_text(self, text):
        """Нормализация текста для корректного отображения"""
        if not text:
            return ""
        
        # Преобразуем в строку и чистим
        text = str(text).strip()
        
        # Убираем нестандартные символы
        text = unicodedata.normalize('NFKC', text)
        
        # Заменяем специфические символы на ASCII-эквиваленты
        replacements = {
            '—': '-',
            '«': '"',
            '»': '"',
            '„': '"',
            '…': '...',
            'ё': 'е',
            'Ё': 'Е'
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        return text
    
    def create_pdf_bytes(self, scan_data, user_email):
        """Создать PDF отчет по сканированию и вернуть bytes"""
        try:
            print(f"📝 Создание PDF для скана {scan_data.get('id')}")
            
            # Создаем буфер в памяти
            buffer = io.BytesIO()
            
            # Создаем документ в памяти
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=0.7*inch,
                leftMargin=0.7*inch,
                topMargin=0.7*inch,
                bottomMargin=0.7*inch
            )
            
            # Собираем содержимое документа
            story = []
            
            # Создаем стили с безопасными шрифтами
            styles = getSampleStyleSheet()
            
            # Проверяем, какие шрифты доступны
            available_fonts = []
            for font_name in ['Arial', 'Helvetica', 'Times-Roman']:
                try:
                    pdfmetrics.getFont(font_name)
                    available_fonts.append(font_name)
                except:
                    pass
            
            # Используем первый доступный шрифт
            font_name = available_fonts[0] if available_fonts else 'Helvetica'
            bold_font_name = f"{font_name}-Bold" if f"{font_name}-Bold" in available_fonts else font_name
            
            print(f"   Используем шрифт: {font_name}")
            
            # Стиль заголовка
            title_style = ParagraphStyle(
                'Title',
                parent=styles['Title'],
                fontSize=16,
                textColor=colors.HexColor('#330036'),
                spaceAfter=20,
                alignment=TA_CENTER,
                fontName=bold_font_name
            )
            
            # Заголовок
            title = Paragraph("ЗВІТ ПО СКАНУВАННЮ КОСМЕТИКИ", title_style)
            story.append(title)
            story.append(Spacer(1, 15))
            
            # Основной стиль текста
            normal_style = ParagraphStyle(
                'Normal',
                parent=styles['Normal'],
                fontSize=11,
                textColor=colors.black,
                spaceAfter=8,
                fontName=font_name,
                alignment=TA_LEFT
            )
            
            # Дата сканирования
            created_at = scan_data.get('created_at', '')
            formatted_date = "Невідома дата"
            
            if created_at:
                try:
                    # Убираем микросекунды и Z если есть
                    if '.' in created_at:
                        created_at = created_at.split('.')[0]
                    if 'Z' in created_at:
                        created_at = created_at.replace('Z', '')
                    
                    # Пробуем разные форматы
                    for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                        try:
                            dt = datetime.strptime(created_at, fmt)
                            formatted_date = dt.strftime('%d.%m.%Y %H:%M')
                            break
                        except:
                            continue
                except:
                    formatted_date = created_at[:19] if len(created_at) > 19 else created_at
            
            # Основная информация в таблице для лучшего форматирования
            info_data = [
                ["ID сканування:", str(scan_data.get('id', 'Н/Д'))],
                ["Дата сканування:", formatted_date],
                ["Тип введення:", self._get_type_text(scan_data.get('input_type', ''))],
                ["Метод введення:", self._get_method_text(scan_data.get('input_method', ''))],
                ["Статус безпеки:", self._get_safety_status_text(scan_data.get('safety_status', 'safe'))],
                ["Кількість інгредієнтів:", str(scan_data.get('ingredients_count', 0))],
                ["Користувач:", user_email]
            ]
            
            # Создаем таблицу
            info_table = Table(info_data, colWidths=[120, 350])
            info_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), bold_font_name),
            ]))
            
            story.append(info_table)
            story.append(Spacer(1, 20))
            
            # Раздел: Оригінальний текст
            original_text = scan_data.get('original_text')
            if original_text:
                # Заголовок раздела
                heading_style = ParagraphStyle(
                    'Heading',
                    parent=normal_style,
                    fontSize=12,
                    fontName=bold_font_name,
                    spaceAfter=10,
                    spaceBefore=15
                )
                
                story.append(Paragraph("Оригінальний текст:", heading_style))
                story.append(Spacer(1, 8))
                
                # Текст
                text_style = ParagraphStyle(
                    'Text',
                    parent=normal_style,
                    fontSize=10,
                    leading=12,
                    alignment=TA_JUSTIFY,
                    fontName=font_name
                )
                
                text = str(original_text)
                # Ограничиваем длину
                if len(text) > 1500:
                    text = text[:1500] + "..."
                
                # Разбиваем на строки для лучшего отображения
                lines = []
                for line in text.split('\n'):
                    line = line.strip()
                    if line:
                        lines.append(line)
                
                # Добавляем первые 20 строк
                for line in lines[:20]:
                    story.append(Paragraph(self.normalize_text(line), text_style))
                    story.append(Spacer(1, 4))
                
                if len(lines) > 20:
                    story.append(Paragraph("...", normal_style))
                
                story.append(Spacer(1, 20))
            
            # Раздел: Знайдені інгредієнти
            ingredients = scan_data.get('ingredients_detailed') or scan_data.get('ingredients', [])
            if ingredients:
                # Заголовок раздела
                heading_style = ParagraphStyle(
                    'Heading',
                    parent=normal_style,
                    fontSize=12,
                    fontName=bold_font_name,
                    spaceAfter=10,
                    spaceBefore=15
                )
                
                story.append(Paragraph(f"Знайдені інгредієнти ({len(ingredients)}):", heading_style))
                story.append(Spacer(1, 8))
                
                # Стиль для списка
                list_style = ParagraphStyle(
                    'List',
                    parent=normal_style,
                    fontSize=10,
                    leftIndent=20,
                    firstLineIndent=-20,
                    spaceAfter=4
                )
                
                # Добавляем ингредиенты
                for i, ing in enumerate(ingredients[:30], 1):
                    if isinstance(ing, dict):
                        name = ing.get('name', '')
                        risk = ing.get('risk_level', 'unknown')
                        
                        if name:
                            risk_text = self._get_risk_text(risk)
                            # Простое форматирование без HTML тегов
                            ingredient_text = f"{i}. {name} ({risk_text})"
                            story.append(Paragraph(self.normalize_text(ingredient_text), list_style))
                
                if len(ingredients) > 30:
                    story.append(Paragraph(f"... та ще {len(ingredients) - 30} інгредієнтів", normal_style))
                
                story.append(Spacer(1, 20))
            
            # Раздел: Рекомендации
            rec_heading_style = ParagraphStyle(
                'RecHeading',
                parent=normal_style,
                fontSize=13,
                fontName=bold_font_name,
                textColor=colors.HexColor('#2A002D'),
                spaceAfter=12,
                spaceBefore=20
            )
            
            story.append(Paragraph("Рекомендації та висновки:", rec_heading_style))
            story.append(Spacer(1, 10))
            
            safety_status = scan_data.get('safety_status', 'safe')
            recommendations = self._get_recommendations(safety_status)
            
            # Простой стиль для рекомендаций без HTML
            rec_style = ParagraphStyle(
                'Recommendation',
                parent=normal_style,
                leftIndent=20,
                firstLineIndent=-20,
                spaceAfter=8
            )
            
            for rec in recommendations:
                # Убираем HTML теги для простоты
                clean_rec = rec.replace('<b>', '').replace('</b>', '').replace('<font color="red">', '').replace('</font>', '')
                story.append(Paragraph(f"• {self.normalize_text(clean_rec)}", rec_style))
            
            story.append(Spacer(1, 30))
            
            # Футер
            footer_style = ParagraphStyle(
                'Footer',
                parent=normal_style,
                fontSize=9,
                textColor=colors.grey,
                spaceAfter=6,
                alignment=TA_CENTER
            )
            
            story.append(Paragraph(
                f"Звіт створено: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}",
                footer_style
            ))
            story.append(Paragraph(
                "Згенеровано за допомогою Skipley - сканера косметичних інгредієнтів",
                footer_style
            ))
            
            # Создаем PDF
            doc.build(story)
            
            # Получаем bytes
            pdf_bytes = buffer.getvalue()
            buffer.close()
            
            print(f"✅ PDF создан, размер: {len(pdf_bytes)} байт")
            return pdf_bytes
            
        except Exception as e:
            print(f"❌ Ошибка создания PDF: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Возвращаем простой PDF с сообщением об ошибке
            return self._create_error_pdf(str(e))
    
    def _create_error_pdf(self, error_message):
        """Создать простой PDF с сообщением об ошибке"""
        try:
            buffer = io.BytesIO()
            
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            styles = getSampleStyleSheet()
            
            story = []
            
            story.append(Paragraph("ПОМИЛКА ПРИ СТВОРЕННІ ЗВІТУ", styles['Title']))
            story.append(Spacer(1, 20))
            story.append(Paragraph(f"Помилка: {error_message}", styles['Normal']))
            story.append(Spacer(1, 20))
            story.append(Paragraph("Будь ласка, спробуйте ще раз або зверніться до адміністратора.", styles['Normal']))
            
            doc.build(story)
            pdf_bytes = buffer.getvalue()
            buffer.close()
            
            return pdf_bytes
            
        except:
            # Если даже это не сработало, возвращаем пустой PDF
            return b''
    
    def _get_recommendations(self, safety_status):
        """Получить рекомендации по уровню безопасности"""
        if safety_status in ['danger', 'high']:
            return [
                "Продукт містить інгредієнти високого ризику.",
                "Рекомендуємо уникати регулярного використання цього продукту.",
                "Розгляньте альтернативні продукти без небезпечних компонентів.",
                "Консультуйтеся з дерматологом при виникненні подразнень.",
                "Завжди перевіряйте склад перед придбанням косметики."
            ]
        elif safety_status in ['warning', 'medium']:
            return [
                "Продукт містить інгредієнти середнього ризику.",
                "Використовуйте продукт з обережністю та спостерігайте за реакцією шкіри.",
                "Не використовуйте продукт на пошкодженій шкірі.",
                "При тривалому використанні робіть перерви.",
                "Проводьте тест на алергію перед першим використанням."
            ]
        else:
            return [
                "Продукт відносно безпечний для використання.",
                "Дотримуйтесь інструкцій використання від виробника.",
                "Проводьте тест на алергію перед першим використанням.",
                "Зберігайте продукт відповідно до вказівок виробника.",
                "Регулярно оновлюйте інформацію про безпеку інгредієнтів."
            ]
    
    def _get_type_text(self, type_code):
        types = {
            'manual': 'Текст',
            'camera': 'Фото'
        }
        return types.get(type_code, 'Невідомий тип')
    
    def _get_method_text(self, method_code):
        methods = {
            'text': 'Ручний ввід',
            'device': 'З пристрою',
            'camera': 'Камера'
        }
        return methods.get(method_code, 'Невідомий метод')
    
    def _get_safety_status_text(self, status):
        statuses = {
            'danger': 'Високий ризик',
            'high': 'Високий ризик',
            'warning': 'Середній ризик',
            'medium': 'Середній ризик',
            'safe': 'Безпечно',
            'low': 'Низький ризик'
        }
        return statuses.get(status, 'Невідомий статус')
    
    def _get_risk_text(self, risk_level):
        texts = {
            'high': 'Високий',
            'danger': 'Високий',
            'medium': 'Середній',
            'warning': 'Середній',
            'low': 'Низький',
            'safe': 'Безпечний',
            'unknown': 'Невідомий'
        }
        return texts.get(risk_level, 'Невідомий')