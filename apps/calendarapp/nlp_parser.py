import re
from datetime import datetime, timedelta
from dateutil import parser as date_parser
import pytz
from langdetect import detect, DetectorFactory
from langdetect.lang_detect_exception import LangDetectException
from django.conf import settings
from django.utils import timezone

# Langdetect uchun seed
DetectorFactory.seed = 0


class CalendarNLPParser:
    """
    NLP parser for calendar events
    Django uchun optimallashtirilgan versiya
    """
    
    def __init__(self):
        self.default_timezone = getattr(settings, 'TIME_ZONE', 'Asia/Tashkent')
        
        # Dastlabki tilni aniqlash uchun so'zlar
        self.language_keywords = {
            'uz': {
                'keywords': ['va', 'lekin', 'yoki', 'ertaga', 'bugun', 'uchun'],
                'common_words': ['va', 'lekin', 'yoki', 'uchun', 'bilan']
            },
            'ru': {
                'keywords': ['и', 'но', 'или', 'завтра', 'сегодня', 'для'],
                'common_words': ['и', 'но', 'или', 'для', 'с']
            },
            'en': {
                'keywords': ['and', 'but', 'or', 'tomorrow', 'today', 'for'],
                'common_words': ['the', 'and', 'for', 'with', 'that']
            }
        }
        
        # Ma'nolari
        self.keywords = {
            'uz': {
                'ertaga': 'tomorrow',
                'bugun': 'today',
                'kecha': 'yesterday',
                'dushanba': 'monday',
                'seshanba': 'tuesday',
                'chorshanba': 'wednesday',
                'payshanba': 'thursday',
                'juma': 'friday',
                'shanba': 'saturday',
                'yakshanba': 'sunday',
                'butun kun': 'all_day',
                'har': 'every',
                'daqiqa': 'minute',
                'soat': 'hour',
                'kun': 'day',
                'hafta': 'week',
                'oy': 'month',
                'yil': 'year',
                'vaqt': 'time',
                'boshlanish': 'start',
                'tugash': 'end',
                'oldin': 'before',
                'keyin': 'after',
                'saat': 'o\'clock',
            },
            'ru': {
                'завтра': 'tomorrow',
                'сегодня': 'today',
                'вчера': 'yesterday',
                'понедельник': 'monday',
                'вторник': 'tuesday',
                'среда': 'wednesday',
                'четверг': 'thursday',
                'пятница': 'friday',
                'суббота': 'saturday',
                'воскресенье': 'sunday',
                'целый день': 'all_day',
                'весь день': 'all_day',
                'каждый': 'every',
                'ежедневно': 'daily',
                'еженедельно': 'weekly',
                'минута': 'minute',
                'час': 'hour',
                'день': 'day',
                'неделя': 'week',
                'месяц': 'month',
                'год': 'year',
                'время': 'time',
                'начало': 'start',
                'конец': 'end',
                'до': 'before',
                'после': 'after',
                'в': 'at',
            },
            'en': {
                'tomorrow': 'tomorrow',
                'today': 'today',
                'yesterday': 'yesterday',
                'monday': 'monday',
                'tuesday': 'tuesday',
                'wednesday': 'wednesday',
                'thursday': 'thursday',
                'friday': 'friday',
                'saturday': 'saturday',
                'sunday': 'sunday',
                'all day': 'all_day',
                'whole day': 'all_day',
                'every': 'every',
                'daily': 'daily',
                'weekly': 'weekly',
                'monthly': 'monthly',
                'minute': 'minute',
                'hour': 'hour',
                'day': 'day',
                'week': 'week',
                'month': 'month',
                'year': 'year',
                'time': 'time',
                'start': 'start',
                'end': 'end',
                'before': 'before',
                'after': 'after',
                'at': 'at',
            }
        }
    
    def get_current_time(self, user_timezone: str = None):
        """Joriy vaqtni olish - Django bilan"""
        if user_timezone:
            tz = pytz.timezone(user_timezone)
            return timezone.now().astimezone(tz)
        return timezone.now()
    
    def detect_language(self, text: str) -> str:
        """
        Matndan tilni avtomatik aniqlash
        1. langdetect kutubxonasi
        2. Keyword orqali aniqlash
        3. Default: 'uz'
        """
        if not text or len(text.strip()) < 3:
            return 'uz'
        
        # 1. Langdetect orqali aniqlash
        try:
            detected_lang = detect(text)
            lang_map = {'en': 'en', 'ru': 'ru'}
            if detected_lang in lang_map:
                return lang_map[detected_lang]
        except LangDetectException:
            pass
        
        # 2. Keyword orqali aniqlash
        text_lower = text.lower()
        
        # Til bo'yicha hisoblash
        scores = {'uz': 0, 'ru': 0, 'en': 0}
        
        # Uz tili uchun (lotin va kirill)
        uz_keywords = ['va', 'lekin', 'yoki', 'uchun', 'bilan', 'da', 'ga', 'ni', 'ning']
        for keyword in uz_keywords:
            if keyword in text_lower:
                scores['uz'] += 1
        
        # Rus tili uchun
        ru_keywords = ['и', 'но', 'или', 'для', 'с', 'в', 'на', 'по']
        for keyword in ru_keywords:
            if keyword in text_lower:
                scores['ru'] += 1
        
        # Ingliz tili uchun
        en_keywords = ['the', 'and', 'for', 'with', 'that', 'this', 'have', 'has']
        for keyword in en_keywords:
            if keyword in text_lower:
                scores['en'] += 1
        
        # Max score bo'lgan til
        max_score_lang = max(scores, key=scores.get)
        
        # Agar hech qaysi tilda aniq belgi bo'lmasa
        if scores[max_score_lang] == 0:
            # Alifbo orqali aniqlash
            if re.search(r'[а-яА-ЯёЁ]', text):
                return 'ru'
            elif re.search(r'[a-zA-Z]', text) and not re.search(r'[а-яА-ЯёЁ]', text):
                return 'en'
            else:
                return 'uz'  # Lotin harflari, default Uzbek
        else:
            return max_score_lang
    
    def parse(self, prompt: str, language: str = None, user_timezone: str = None):
        """
        Promptdan event fieldlarini extract qilish
        Django uchun optimallashtirilgan
        """
        if not prompt or not prompt.strip():
            return {
                'error': 'Prompt is empty',
                'intent': 'UNKNOWN',
                'extracted_data': {},
                'suggestions': ['Please enter a valid prompt']
            }
        
        # Timezone ni aniqlash
        if not user_timezone:
            user_timezone = self.default_timezone
        
        # Tilni aniqlash
        if not language:
            language = self.detect_language(prompt)
        
        prompt_lower = prompt.lower()
        
        # Intent classification
        intent = self._detect_intent(prompt_lower, language)
        
        # Slot filling
        extracted_data = self._extract_slots(prompt, language, user_timezone)
        
        return {
            'intent': intent,
            'language': language,
            'confidence': self._calculate_confidence(prompt, extracted_data),
            'extracted_data': extracted_data,
            'suggestions': self._generate_suggestions(extracted_data, language),
            'original_prompt': prompt
        }
    
    def _calculate_confidence(self, prompt: str, extracted_data: dict) -> float:
        """Ishenchilik darajasini hisoblash"""
        confidence = 0.5  # Base confidence
        
        # Title mavjud bo'lsa
        if extracted_data.get('title') and extracted_data['title'] != 'Event':
            confidence += 0.2
        
        # Vaqt mavjud bo'lsa
        if extracted_data.get('time_start'):
            confidence += 0.2
        
        # Boshqa fieldlar mavjud bo'lsa
        extra_fields = ['repeat', 'invite', 'alert', 'url', 'note']
        for field in extra_fields:
            if extracted_data.get(field):
                confidence += 0.05
        
        # Max 0.95
        return min(confidence, 0.95)
    
    def _detect_intent(self, prompt: str, language: str) -> str:
        """Intent ni aniqlash"""
        intent_keywords = {
            'uz': {
                'create': ['yarat', 'qo\'sh', 'qosh', 'tuz', 'kirit'],
                'update': ['o\'zgartir', 'yangila', 'tahrir', 'edit'],
                'delete': ['o\'chir', 'delete', 'uchir', 'toza'],
                'show': ['ko\'rsat', 'korsat', 'korish', 'qidir'],
                'remind': ['eslat', 'ogoh', 'alert'],
                'cancel': ['bekor', 'cancel', 'otkaz'],
            },
            'ru': {
                'create': ['создать', 'добавить', 'создай', 'добавь'],
                'update': ['изменить', 'обновить', 'редактировать', 'измен'],
                'delete': ['удалить', 'убрать', 'стереть', 'удали'],
                'show': ['показать', 'посмотреть', 'найти', 'искать'],
                'remind': ['напомнить', 'напоминание', 'напомни'],
                'cancel': ['отменить', 'отмена', 'отмени'],
            },
            'en': {
                'create': ['create', 'add', 'make', 'new'],
                'update': ['update', 'edit', 'change', 'modify'],
                'delete': ['delete', 'remove', 'erase', 'cancel'],
                'show': ['show', 'view', 'find', 'search'],
                'remind': ['remind', 'alert', 'notify'],
                'cancel': ['cancel', 'stop', 'abort'],
            }
        }
        
        keywords = intent_keywords.get(language, intent_keywords['en'])
        
        for intent, intent_words in keywords.items():
            for word in intent_words:
                if word in prompt:
                    return intent.upper()
        
        # Agar intent aniqlanmasa, kontekstga qarab
        if '?' in prompt:
            return 'SHOW'
        elif 'eslat' in prompt or 'напом' in prompt or 'remind' in prompt:
            return 'REMIND'
        else:
            return 'CREATE'  # Default
    
    def _extract_slots(self, prompt: str, language: str, user_timezone: str) -> dict:
        """Fieldlarni extract qilish"""
        extracted = {}
        
        # 1. Title (qolgan text)
        extracted['title'] = self._extract_title(prompt, language)
        
        # 2. All-day
        extracted['all_day'] = self._extract_all_day(prompt, language)
        
        # 3. Time start & end
        times = self._extract_time(prompt, language, user_timezone)
        extracted.update(times)
        
        # 4. Repeat
        extracted['repeat'] = self._extract_repeat(prompt, language)
        
        # 5. Invite (email list)
        extracted['invite'] = self._extract_invites(prompt)
        
        # 6. Alert
        extracted['alert'] = self._extract_alerts(prompt, language)
        
        # 7. URL
        extracted['url'] = self._extract_url(prompt)
        
        # 8. Note
        extracted['note'] = self._extract_note(prompt)
        
        return extracted
    
    def _extract_title(self, prompt: str, language: str) -> str:
        """Sarlavha extract"""
        prompt_clean = prompt.strip()
        
        # Vaqt, taklif, ogohlantirish patternlari
        time_patterns = [
            r'\d{1,2}[:.]\d{2}',  # 14:30, 2.30
            r'\d+\s*(daqiqa|soat|kun|hafta|oy|minut|hour|day|week|month)',
            r'ertaga|bugun|kecha|завтра|сегодня|вчера|tomorrow|today|yesterday',
            r'dushanba|seshanba|chorshanba|payshanba|juma|shanba|yakshanba',
            r'понедельник|вторник|среда|четверг|пятница|суббота|воскресенье',
            r'monday|tuesday|wednesday|thursday|friday|saturday|sunday',
            r'@\w+',  # @mention
            r'[\w\.-]+@[\w\.-]+\.\w+',  # Email
            r'https?://\S+',  # URL
        ]
        
        # Promptni tozalash
        cleaned_prompt = prompt_clean
        for pattern in time_patterns:
            cleaned_prompt = re.sub(pattern, '', cleaned_prompt, flags=re.IGNORECASE)
        
        # Maxsus so'zlarni olib tashlash
        stop_words = {
            'uz': ['uchun', 'bilan', 'da', 'ga', 'ni', 'ning', 'va', 'lekin', 'yoki'],
            'ru': ['для', 'с', 'в', 'на', 'по', 'и', 'но', 'или'],
            'en': ['for', 'with', 'at', 'on', 'in', 'and', 'but', 'or', 'the']
        }
        
        words = cleaned_prompt.split()
        filtered_words = []
        
        for word in words:
            if word.lower() not in stop_words.get(language, []):
                filtered_words.append(word)
        
        # Agar sarlavha bo'sh bo'lsa
        if not filtered_words:
            return "Event"
        
        # Max 5 so'z
        title = ' '.join(filtered_words[:5])
        
        # Agar juda qisqa bo'lsa
        if len(title) < 3:
            return "Meeting" if language == 'en' else "Uchrashuv" if language == 'uz' else "Встреча"
        
        return title
    
    def _extract_all_day(self, prompt: str, language: str) -> bool:
        """All-day extract"""
        all_day_keywords = {
            'uz': ['butun kun', 'kun bo\'yi', 'toliq kun', 'kunning hammasi'],
            'ru': ['целый день', 'весь день', 'на весь день', 'полный день'],
            'en': ['all day', 'whole day', 'full day', 'entire day']
        }
        
        keywords = all_day_keywords.get(language, [])
        prompt_lower = prompt.lower()
        
        for keyword in keywords:
            if keyword in prompt_lower:
                return True
        
        return False
    
    def _extract_time(self, prompt: str, language: str, user_timezone: str) -> dict:
        """Vaqt extract - Django bilan"""
        now = self.get_current_time(user_timezone)
        
        # Time patterns
        time_patterns = {
            'uz': {
                'ertaga': now + timedelta(days=1),
                'bugun': now,
                'kecha': now - timedelta(days=1),
                'dushanba': self._next_weekday(now, 0),
                'seshanba': self._next_weekday(now, 1),
                'chorshanba': self._next_weekday(now, 2),
                'payshanba': self._next_weekday(now, 3),
                'juma': self._next_weekday(now, 4),
                'shanba': self._next_weekday(now, 5),
                'yakshanba': self._next_weekday(now, 6),
            },
            'ru': {
                'завтра': now + timedelta(days=1),
                'сегодня': now,
                'вчера': now - timedelta(days=1),
                'понедельник': self._next_weekday(now, 0),
                'вторник': self._next_weekday(now, 1),
                'среда': self._next_weekday(now, 2),
                'четверг': self._next_weekday(now, 3),
                'пятница': self._next_weekday(now, 4),
                'суббота': self._next_weekday(now, 5),
                'воскресенье': self._next_weekday(now, 6),
            },
            'en': {
                'tomorrow': now + timedelta(days=1),
                'today': now,
                'yesterday': now - timedelta(days=1),
                'monday': self._next_weekday(now, 0),
                'tuesday': self._next_weekday(now, 1),
                'wednesday': self._next_weekday(now, 2),
                'thursday': self._next_weekday(now, 3),
                'friday': self._next_weekday(now, 4),
                'saturday': self._next_weekday(now, 5),
                'sunday': self._next_weekday(now, 6),
            }
        }
        
        prompt_lower = prompt.lower()
        
        # Keyword orqali aniqlash
        for keyword, date_obj in time_patterns.get(language, {}).items():
            if keyword in prompt_lower:
                # Soatni aniqlash
                hour_minute = self._extract_hour_minute(prompt)
                if hour_minute:
                    date_obj = date_obj.replace(hour=hour_minute['hour'], 
                                              minute=hour_minute['minute'])
                
                time_end = date_obj + timedelta(hours=1)
                
                return {
                    'time_start': date_obj.isoformat(),
                    'time_end': time_end.isoformat()
                }
        
        # Dateparser orqali
        try:
            parsed_date = date_parser.parse(prompt, fuzzy=True)
            
            if parsed_date:
                tz = pytz.timezone(user_timezone)
                if parsed_date.tzinfo is None:
                    parsed_date = tz.localize(parsed_date)
                else:
                    parsed_date = parsed_date.astimezone(tz)
                    
                time_end = parsed_date + timedelta(hours=1)
                
                return {
                    'time_start': parsed_date.isoformat(),
                    'time_end': time_end.isoformat()
                }
        except:
            pass
        
        # Agar vaqt topilmasa, default (keyingi soat)
        default_start = now + timedelta(hours=1)
        default_end = default_start + timedelta(hours=1)
        
        return {
            'time_start': default_start.isoformat(),
            'time_end': default_end.isoformat()
        }
    
    def _next_weekday(self, d, weekday):
        """Berilgan kundan keyingi hafta kunini topish"""
        days_ahead = weekday - d.weekday()
        if days_ahead <= 0:  # Agar bugun yoki o'tgan bo'lsa
            days_ahead += 7
        return d + timedelta(days_ahead)
    
    def _extract_hour_minute(self, prompt: str):
        """Soat:minute formatini extract qilish"""
        patterns = [
            r'(\d{1,2})[:.](\d{2})',  # 14:30, 2.30
            r'(\d{1,2})\s*soat',  # 2 soat
            r'(\d{1,2})\s*часов',  # 2 часов
            r'(\d{1,2})\s*o\'clock',  # 2 o'clock
            r'(\d{1,2})\s*am',  # 2 am
            r'(\d{1,2})\s*pm',  # 2 pm
            r'(\d{1,2})\s*утра',  # 2 утра
            r'(\d{1,2})\s*вечера',  # 2 вечера
        ]
        
        for pattern in patterns:
            match = re.search(pattern, prompt.lower())
            if match:
                try:
                    hour = int(match.group(1))
                    minute = int(match.group(2)) if len(match.groups()) > 1 and match.group(2) else 0
                    
                    # AM/PM convert
                    if 'pm' in pattern and hour < 12:
                        hour += 12
                    elif 'am' in pattern and hour == 12:
                        hour = 0
                    elif 'вечера' in pattern and hour < 12:
                        hour += 12
                    elif 'утра' in pattern and hour == 12:
                        hour = 0
                    
                    # 24 soat formatida
                    if hour < 24 and minute < 60:
                        return {'hour': hour, 'minute': minute}
                except (IndexError, ValueError):
                    continue
        
        return None
    
    def _extract_repeat(self, prompt: str, language: str) -> str:
        """Repeat extract"""
        repeat_patterns = {
            'uz': {
                'har kun': 'RRULE:FREQ=DAILY',
                'har hafta': 'RRULE:FREQ=WEEKLY',
                'har oy': 'RRULE:FREQ=MONTHLY',
                'har yil': 'RRULE:FREQ=YEARLY',
                'har juma': 'RRULE:FREQ=WEEKLY;BYDAY=FR',
                'dushanba kunlari': 'RRULE:FREQ=WEEKLY;BYDAY=MO',
                'haftasiga': 'RRULE:FREQ=WEEKLY',
                'oyiga': 'RRULE:FREQ=MONTHLY',
            },
            'ru': {
                'каждый день': 'RRULE:FREQ=DAILY',
                'ежедневно': 'RRULE:FREQ=DAILY',
                'каждую неделю': 'RRULE:FREQ=WEEKLY',
                'еженедельно': 'RRULE:FREQ=WEEKLY',
                'каждый месяц': 'RRULE:FREQ=MONTHLY',
                'ежемесячно': 'RRULE:FREQ=MONTHLY',
                'каждую пятницу': 'RRULE:FREQ=WEEKLY;BYDAY=FR',
                'по пятницам': 'RRULE:FREQ=WEEKLY;BYDAY=FR',
                'еженедельно': 'RRULE:FREQ=WEEKLY',
            },
            'en': {
                'every day': 'RRULE:FREQ=DAILY',
                'daily': 'RRULE:FREQ=DAILY',
                'every week': 'RRULE:FREQ=WEEKLY',
                'weekly': 'RRULE:FREQ=WEEKLY',
                'every month': 'RRULE:FREQ=MONTHLY',
                'monthly': 'RRULE:FREQ=MONTHLY',
                'every friday': 'RRULE:FREQ=WEEKLY;BYDAY=FR',
                'on fridays': 'RRULE:FREQ=WEEKLY;BYDAY=FR',
                'bi-weekly': 'RRULE:FREQ=WEEKLY;INTERVAL=2',
            }
        }
        
        patterns = repeat_patterns.get(language, {})
        prompt_lower = prompt.lower()
        
        for pattern, value in patterns.items():
            if pattern in prompt_lower:
                return value
        
        return None
    
    def _extract_invites(self, prompt: str) -> list:
        """Email list extract"""
        emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', prompt)
        return emails
    
    def _extract_alerts(self, prompt: str, language: str) -> list:
        """Alert extract (format: '10m', '1h', '1d')"""
        prompt_lower = prompt.lower()
        
        # Pattern: raqam + m/h/d/w
        patterns = {
            'uz': [
                (r'(\d+)\s*daqiqa\s*oldin', 'm'),
                (r'(\d+)\s*soat\s*oldin', 'h'),
                (r'(\d+)\s*kun\s*oldin', 'd'),
                (r'(\d+)\s*hafta\s*oldin', 'w'),
                (r'(\d+)\s*m\s*oldin', 'm'),
                (r'(\d+)\s*h\s*oldin', 'h'),
                (r'(\d+)\s*d\s*oldin', 'd'),
                (r'(\d+)\s*w\s*oldin', 'w'),
                (r'eslatma\s*(\d+)\s*daqiqa', 'm'),
                (r'eslatma\s*(\d+)\s*soat', 'h'),
            ],
            'ru': [
                (r'(\d+)\s*минут\w*\s*(?:до|перед)', 'm'),
                (r'(\d+)\s*час\w*\s*(?:до|перед)', 'h'),
                (r'(\d+)\s*дн\w*\s*(?:до|перед)', 'd'),
                (r'(\d+)\s*недел\w*\s*(?:до|перед)', 'w'),
                (r'(\d+)\s*м\s*(?:до|перед)', 'm'),
                (r'(\d+)\s*ч\s*(?:до|перед)', 'h'),
                (r'(\d+)\s*д\s*(?:до|перед)', 'd'),
                (r'(\d+)\s*н\s*(?:до|перед)', 'w'),
                (r'напомин\w+\s*(\d+)\s*минут', 'm'),
                (r'напомин\w+\s*(\d+)\s*час', 'h'),
            ],
            'en': [
                (r'(\d+)\s*minutes?\s*before', 'm'),
                (r'(\d+)\s*hours?\s*before', 'h'),
                (r'(\d+)\s*days?\s*before', 'd'),
                (r'(\d+)\s*weeks?\s*before', 'w'),
                (r'(\d+)\s*m\s*before', 'm'),
                (r'(\d+)\s*h\s*before', 'h'),
                (r'(\d+)\s*d\s*before', 'd'),
                (r'(\d+)\s*w\s*before', 'w'),
                (r'remind\w*\s*(\d+)\s*minutes?', 'm'),
                (r'remind\w*\s*(\d+)\s*hours?', 'h'),
            ]
        }
        
        alerts = []
        lang_patterns = patterns.get(language, patterns['en'])
        
        for pattern, unit in lang_patterns:
            matches = re.findall(pattern, prompt_lower, re.IGNORECASE)
            for value in matches:
                alerts.append(f"{value}{unit}")
        
        return alerts[:3]  # Max 3 ta alert
    
    def _extract_url(self, prompt: str) -> str:
        """URL extract"""
        urls = re.findall(r'https?://\S+', prompt)
        return urls[0] if urls else None
    
    def _extract_note(self, prompt: str) -> str:
        """Note extract"""
        # Max 500 belgi
        if len(prompt) > 500:
            return prompt[:497] + "..."
        return prompt
    
    def _generate_suggestions(self, extracted_data: dict, language: str) -> list:
        """Tilga mos takliflar generatsiya"""
        suggestions = []
        
        translations = {
            'uz': {
                'time_missing': "Iltimos, vaqtni ko'rsating (masalan: 'ertaga 14:00', 'juma kuni')",
                'short_duration': "Bu vaqt juda qisqa, davomiylikni ko'paytirishni xohlaysizmi?",
                'long_duration': "Bu vaqt juda uzoq, davomiylikni qisqartirishni xohlaysizmi?",
                'add_alert': "Ogohlantirish qo'shishni xohlaysizmi?",
                'add_repeat': "Takrorlanish qo'shishni xohlaysizmi?",
            },
            'ru': {
                'time_missing': "Пожалуйста, укажите время (например: 'завтра 14:00', 'в пятницу')",
                'short_duration': "Это очень короткое время, хотите увеличить продолжительность?",
                'long_duration': "Это очень долгое время, хотите сократить продолжительность?",
                'add_alert': "Хотите добавить напоминание?",
                'add_repeat': "Хотите добавить повторение?",
            },
            'en': {
                'time_missing': "Please specify time (e.g., 'tomorrow 14:00', 'on Friday')",
                'short_duration': "This is very short duration, do you want to extend it?",
                'long_duration': "This is very long duration, do you want to shorten it?",
                'add_alert': "Do you want to add an alert?",
                'add_repeat': "Do you want to add repetition?",
            }
        }
        
        lang_translations = translations.get(language, translations['en'])
        
        # Agar vaqt berilmagan bo'lsa
        if 'time_start' not in extracted_data:
            suggestions.append(lang_translations['time_missing'])
        
        # Agar duration katta bo'lsa
        if 'time_start' in extracted_data and 'time_end' in extracted_data:
            try:
                start = datetime.fromisoformat(extracted_data['time_start'].replace('Z', '+00:00'))
                end = datetime.fromisoformat(extracted_data['time_end'].replace('Z', '+00:00'))
                duration = end - start
                
                if duration < timedelta(minutes=15):
                    suggestions.append(lang_translations['short_duration'])
                elif duration > timedelta(days=7):
                    suggestions.append(lang_translations['long_duration'])
            except:
                pass
        
        # Boshqa takliflar
        if not extracted_data.get('alert'):
            suggestions.append(lang_translations['add_alert'])
        
        if not extracted_data.get('repeat'):
            suggestions.append(lang_translations['add_repeat'])
        
        return suggestions[:3]  # Max 3 ta taklif


# Django uchun helper funksiyalar
class CalendarNLPHelper:
    """Django model bilan integratsiya uchun helper"""
    
    @staticmethod
    def create_draft_from_parse(user, parse_result):
        """Parsed natijadan draft yaratish"""
        from .models import ParsedEventDraft
        
        draft = ParsedEventDraft.objects.create(
            user=user,
            original_text=parse_result['original_prompt'],
            language=parse_result['language'],
            intent=parse_result['intent'],
            extracted_data=parse_result['extracted_data'],
            expires_at=timezone.now() + timedelta(hours=24)  # 24 soat
        )
        return draft
    
    @staticmethod
    def create_event_from_draft(draft):
        """Draft dan event yaratish"""
        from .models import Event, EventInvite, EventAlert
        
        extracted = draft.extracted_data
        
        # Timezone convert
        tz = pytz.timezone('Asia/Tashkent')
        time_start = datetime.fromisoformat(extracted['time_start'])
        time_end = datetime.fromisoformat(extracted['time_end'])
        
        if time_start.tzinfo is None:
            time_start = tz.localize(time_start)
        if time_end.tzinfo is None:
            time_end = tz.localize(time_end)
        
        # Event yaratish
        event = Event.objects.create(
            user=draft.user,
            title=extracted.get('title', 'Event'),
            all_day=extracted.get('all_day', False),
            time_start=time_start,
            time_end=time_end,
            repeat=extracted.get('repeat'),
            url=extracted.get('url'),
            note=extracted.get('note'),
        )
        
        # Invites qo'shish
        for email in extracted.get('invite', []):
            EventInvite.objects.create(
                event=event,
                email=email,
                status='pending'
            )
        
        # Alerts qo'shish
        for alert_str in extracted.get('alert', []):
            # '10m' -> value=10, unit='m'
            match = re.match(r'(\d+)([mhdw])', alert_str)
            if match:
                EventAlert.objects.create(
                    event=event,
                    value=int(match.group(1)),
                    unit=match.group(2)
                )
        
        # Draft ni confirmed qilish
        draft.is_confirmed = True
        draft.confirmed_at = timezone.now()
        draft.save()
        
        return event



