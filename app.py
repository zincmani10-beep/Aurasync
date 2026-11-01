# -*- coding: utf-8 -*-
"""AuraSync | Luxury Ambient Intelligence - single-file Streamlit app.
Run with:  streamlit run app.py   (Streamlit >= 1.37 recommended)
Install:   pip install streamlit pandas requests deep-translator openai   (deep-translator = every language on every page)

Secrets (.streamlit/secrets.toml, or the Secrets box on Streamlit Community Cloud):
  NVIDIA_API_KEY   AI companion (NVIDIA NIM)
  AURASYNC_TOKEN   protects the ?mode=...&token=... links and the "Voice Automation Links" panel (required for both)
  APP_URL, VOICEMONKEY_TOKEN, IOT_WEBHOOK_URL, ...   cloud IoT triggers, see the "Cloud automation" section below
"""
import os, logging, warnings
warnings.filterwarnings("ignore")
logging.getLogger("streamlit").setLevel(logging.ERROR)
os.environ["STREAMLIT_LOG_LEVEL"] = "error"

import ast
import uuid
import calendar
import concurrent.futures
import hashlib
import hmac
import html
import ipaddress
import json
import math
import os
import random
import re
import socket
import sys
import threading
import time
import types
import urllib.parse
from datetime import date, datetime, timedelta, timezone
from datetime import time as dtime

import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

# --- Auto-sanitize Unicode surrogates for Streamlit components ---
_orig_components_html = components.html
def _safe_components_html(html_str=None, *args, **kwargs):
    def _clean(s):
        if isinstance(s, str):
            try:
                return s.encode('utf-16', 'surrogatepass').decode('utf-16', 'ignore')
            except Exception:
                return s.encode('utf-8', 'ignore').decode('utf-8')
        return s
    if html_str is not None:
        html_str = _clean(html_str)
    elif 'html' in kwargs:
        kwargs['html'] = _clean(kwargs['html'])
    return _orig_components_html(html_str, *args, **kwargs)
components.html = _safe_components_html

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - openai is optional; the rule-based engine still works
    OpenAI = None

st.set_page_config(page_title="AuraSync | Luxury Ambient Intelligence",
                   page_icon="✨", layout="wide")

GOLD = "#D4AF37"
LANGS = ["English", "Tamil (தமிழ்)", "Korean (한국어)", "Thai (Thai)", "Spanish (Español)",
         "Hindi (हिन्दी)", "Arabic (العربية)", "Japanese (日本語)", "Chinese (中文)", "French (Français)",
         "German (Deutsch)", "Italian (Italiano)", "Portuguese (Português)", "Russian (Русский)",
         "Turkish (Türkçe)", "Dutch (Nederlands)", "Polish (Polski)", "Swedish (Svenska)",
         "Greek (Ελληνικά)", "Indonesian (Bahasa Indonesia)", "Vietnamese (Tiếng Việt)",
         "Malay (Bahasa Melayu)", "Filipino (Tagalog)"]

# ----------------------------------------------------------------------------
# Translations
# T: key -> (English, Tamil, Korean, Thai, Spanish)   [first five languages, every label]
# TX: extra languages -> tuple aligned with CORE_KEYS (other labels fall back to English)
# ----------------------------------------------------------------------------
T = {
    "sub": ("Luxury Ambient Intelligence", "ஆடம்பர சூழல் நுண்ணறிவு", "럭셔리 앰비언트 인텔리전스", "ระบบอัจฉริยะแวดล้อมระดับหรู", "Inteligencia Ambiental de Lujo"),
    "lang": ("Language", "மொழி", "언어", "ภาษา", "Idioma"),
    "nav": ("Navigate", "வழிசெலுத்தல்", "메뉴", "เมนู", "Navegación"),
    "p1": ("Live Dashboard", "நேரடி டாஷ்போர்டு", "라이브 대시보드", "แดชบอร์ดสด", "Panel en Vivo"),
    "p2": ("Moods, Routines & Settings", "மனநிலைகள், வழக்கங்கள் & அமைப்புகள்", "무드, 루틴 & 설정", "อารมณ์ กิจวัตร และการตั้งค่า", "Ambientes, Rutinas y Ajustes"),
    "p3": ("Inner Voice & Guide", "உள்மனக் குரல் & வழிகாட்டி", "내면의 목소리 & 가이드", "เสียงภายในและคู่มือ", "Voz Interior y Guía"),
    "p4": ("Device Fleet", "சாதனக் குழு", "디바이스 플릿", "กลุ่มอุปกรณ์", "Flota de Dispositivos"),
    "p5": ("System Settings", "கணினி அமைப்புகள்", "시스템 설정", "การตั้งค่าระบบ", "Ajustes del Sistema"),
    "p6": ("Room Settings, Remote Access & Smart Geofence", "அறை அமைப்புகள், தொலைதூர கட்டுப்பாடு & ஜியோஃபென்ஸ்", "방 설정, 원격 액세스 & 스마트 지오펜스", "การตั้งค่าห้อง การเข้าถึงระยะไกล & สมาร์ทจีโอเฟนซ์", "Configuración de Habitación, Acceso Remoto y Geocerca Inteligente"),
    "mode_sel": ("Control mode", "கட்டுப்பாட்டு முறை", "제어 모드", "โหมดควบคุม", "Modo de control"),
    "mode_manual": ("Manual Mode", "கைமுறை பயன்முறை", "수동 모드", "โหมดแมนนวล", "Modo Manual"),
    "mode_auto": ("Auto Mode (Wearable Biometric Sync)", "தானியங்கு பயன்முறை (அணிகலன் உயிரியல் ஒத்திசைவு)", "자동 모드 (웨어러블 바이오 동기화)", "โหมดอัตโนมัติ (ซิงค์ข้อมูลชีวภาพจากอุปกรณ์สวมใส่)", "Modo Automático (Sincronización Biométrica)"),
    "auto_hint": ("Manual Mode: your biometrics are shown below, but lights, AC, fan, curtains and audio stay under your control.", "கைமுறை பயன்முறை: உங்கள் உயிரியல் தரவு கீழே தெரியும்; விளக்கு, ஏசி, மின்விசிறி, திரைச்சீலை, ஒலி உங்கள் கட்டுப்பாட்டில் இருக்கும்.", "수동 모드: 바이오 데이터는 아래에 표시되며 조명, 에어컨, 팬, 커튼, 오디오는 직접 제어합니다.", "โหมดแมนนวล: แสดงข้อมูลชีวภาพด้านล่าง แต่ไฟ แอร์ พัดลม ม่าน และเสียงยังคงอยู่ในการควบคุมของคุณ", "Modo Manual: tus datos biométricos se muestran abajo, pero luces, A/C, ventilador, cortinas y audio los controlas tú."),
    "auto_on": ("Auto Mode: Aura reads your wearable and runs the lights, AC, fan, curtains, scent and audio in the room you are in.", "தானியங்கு பயன்முறை: AI உங்கள் அணிகலனைப் படித்து விளக்கு, ஏசி, மின்விசிறி, திரைச்சீலை, வாசனை, ஒலி மற்றும் இணைந்த சாதனங்களை இயக்குகிறது.", "자동 모드: AI가 웨어러블을 분석해 조명, 에어컨, 팬, 커튼, 향, 오디오와 연결된 모든 기기를 제어합니다.", "โหมดอัตโนมัติ: AI อ่านข้อมูลจากอุปกรณ์สวมใส่และควบคุมไฟ แอร์ พัดลม ม่าน กลิ่น เสียง และอุปกรณ์ที่เชื่อมต่อทั้งหมด", "Modo Automático: la IA lee tu wearable y controla luces, A/C, ventilador, cortinas, aroma, audio y todos los dispositivos conectados."),
    "atmos": ("One-Click Instant Atmosphere", "ஒரே கிளிக்கில் சூழல்", "원클릭 즉시 분위기", "เปลี่ยนบรรยากาศทันที", "Ambiente Instantáneo"),
    "timer": ("Auto-Stop / Sleep Timer", "தானியங்கு நிறுத்தம் / உறக்க நேரம்", "자동 종료 / 수면 타이머", "ตั้งเวลาปิดอัตโนมัติ / นอนหลับ", "Temporizador de Apagado / Sueño"),
    "off": ("Off", "நிறுத்து", "끄기", "ปิด", "Apagado"),
    "min": ("min", "நிமிடம்", "분", "นาที", "min"),
    "studio": ("Master Audio Studio (Procedural Synthesizer)", "மாஸ்டர் ஆடியோ ஸ்டுடியோ (செயற்கை ஒலி உருவாக்கி)", "마스터 오디오 스튜디오 (프로시저럴 신시사이저)", "สตูดิโอเสียงหลัก (ซินธ์สร้างเสียงอัตโนมัติ)", "Estudio de Audio Maestro (Sintetizador Procedural)"),
    "play": ("Play", "தொடங்கு", "재생", "เล่น", "Reproducir"),
    "stop": ("Stop", "நிறுத்து", "정지", "หยุด", "Detener"),
    "mixer": ("Multi-Layer Sound Studio Mixer", "பல அடுக்கு ஒலி கலவை", "멀티 레이어 사운드 믹서", "มิกเซอร์เสียงหลายชั้น", "Mezclador de Sonido Multicapa"),
    "bed": ("Base music volume (%)", "அடிப்படை இசை ஒலி (%)", "기본 음악 볼륨 (%)", "ระดับเสียงเพลงพื้นฐาน (%)", "Volumen de la música base (%)"),
    "bio": ("Real-Time Heart Rate & Biometric Telemetry", "நேரடி இதயத் துடிப்பு & உயிரியல் தரவு", "실시간 심박수 & 바이오메트릭", "อัตราการเต้นของหัวใจและข้อมูลชีวภาพแบบเรียลไทม์", "Frecuencia Cardíaca y Biometría en Vivo"),
    "source": ("Data source", "தரவு மூலம்", "데이터 소스", "แหล่งข้อมูล", "Fuente de datos"),
    "sim": ("Simulated", "உருவகப்படுத்தப்பட்டது", "시뮬레이션", "จำลอง", "Simulado"),
    "wear": ("Wearable API", "அணிகலன் API", "웨어러블 API", "API อุปกรณ์สวมใส่", "API de wearable"),
    "scn": ("Simulated scenario", "உருவகப்படுத்தப்பட்ட சூழல்", "시뮬레이션 시나리오", "สถานการณ์จำลอง", "Escenario simulado"),
    "offline": ("Wearable offline - using simulation", "அணிகலன் இணைப்பில் இல்லை - உருவகப்படுத்தல் பயன்படுத்தப்படுகிறது", "웨어러블 오프라인 - 시뮬레이션 사용 중", "อุปกรณ์สวมใส่ออฟไลน์ - ใช้ข้อมูลจำลอง", "Wearable sin conexión: usando simulación"),
    "state_lbl": ("Detected state", "கண்டறியப்பட்ட நிலை", "감지된 상태", "สถานะที่ตรวจพบ", "Estado detectado"),
    "st_relaxed": ("Relaxed", "அமைதி", "편안함", "ผ่อนคลาย", "Relajado"),
    "st_active": ("Active", "சுறுசுறுப்பு", "활동 중", "กระฉับกระเฉง", "Activo"),
    "st_stress": ("Stress", "மன அழுத்தம்", "스트레스", "เครียด", "Estrés"),
    "st_sleep": ("Asleep", "உறக்கம்", "수면 중", "หลับ", "Dormido"),
    "st_wake": ("Waking up", "எழுகிறார்", "기상 중", "ตื่นนอน", "Despertando"),
    "bpm": ("Heart rate (bpm)", "இதயத் துடிப்பு (bpm)", "심박수 (bpm)", "อัตราการเต้นหัวใจ (bpm)", "Pulso (lpm)"),
    "spo2": ("SpO2 (%)", "SpO2 (%)", "산소포화도 (%)", "ออกซิเจนในเลือด (%)", "SpO2 (%)"),
    "skin": ("Skin temp (°C)", "தோல் வெப்பம் (°C)", "피부 온도 (°C)", "อุณหภูมิผิว (°C)", "Temp. piel (°C)"),
    "active": ("Active atmosphere", "செயலில் உள்ள சூழல்", "현재 분위기", "บรรยากาศปัจจุบัน", "Ambiente activo"),
    "ai_auto": ("Aura Companion", "ஆரா துணை", "아우라 컴패니언", "ออร่า คอมพาเนียน", "Compañero Aura"),
    "ai_conf": ("confidence", "நம்பகத்தன்மை", "신뢰도", "ความมั่นใจ", "confianza"),
    "ai_log": ("Aura Diary", "ஆரா நாட்குறிப்பு", "아우라 다이어리", "ไดอารีออร่า", "Diario Aura"),
    "live_dev": ("Live device state", "நேரடி சாதன நிலை", "실시간 기기 상태", "สถานะอุปกรณ์สด", "Estado en vivo de dispositivos"),
    "save": ("Save", "சேமி", "저장", "บันทึก", "Guardar"),
    "saved": ("Saved ✔", "சேமிக்கப்பட்டது ✔", "저장됨 ✔", "บันทึกแล้ว ✔", "Guardado ✔"),
    "std_cfg": ("Standard Mode Configuration", "நிலையான பயன்முறை அமைப்பு", "표준 모드 설정", "การตั้งค่าโหมดมาตรฐาน", "Configuración de Modo Estándar"),
    "mode": ("Mode", "பயன்முறை", "모드", "โหมด", "Modo"),
    "bulb": ("Bulb color", "விளக்கு நிறம்", "전구 색상", "สีหลอดไฟ", "Color de la bombilla"),
    "bright": ("Brightness (%)", "ஒளிர்வு (%)", "밝기 (%)", "ความสว่าง (%)", "Brillo (%)"),
    "fan": ("Fan speed", "மின்விசிறி வேகம்", "팬 속도", "ความเร็วพัดลม", "Velocidad del ventilador"),
    "ac": ("AC temperature (°C)", "ஏசி வெப்பநிலை (°C)", "에어컨 온도 (°C)", "อุณหภูมิแอร์ (°C)", "Temperatura del A/C (°C)"),
    "curtain": ("Curtains open (%)", "திரைச்சீலை திறப்பு (%)", "커튼 열림 (%)", "ม่านเปิด (%)", "Cortinas abiertas (%)"),
    "genre": ("Base music genre", "அடிப்படை இசை வகை", "기본 음악 장르", "แนวเพลงพื้นฐาน", "Género musical base"),
    "bulb_pw": ("Smart bulb power (ON/OFF)", "ஸ்மார்ட் விளக்கு (ON/OFF)", "스마트 전구 전원 (ON/OFF)", "เปิด/ปิดหลอดไฟอัจฉริยะ", "Bombilla inteligente (ON/OFF)"),
    "fan_pw": ("Fan power (ON/OFF)", "மின்விசிறி (ON/OFF)", "팬 전원 (ON/OFF)", "เปิด/ปิดพัดลม", "Ventilador (ON/OFF)"),
    "ac_pw": ("AC power (ON/OFF)", "ஏசி (ON/OFF)", "에어컨 전원 (ON/OFF)", "เปิด/ปิดแอร์", "A/C (ON/OFF)"),
    "extras": ("Ambient devices ON in this mode", "இந்த பயன்முறையில் இயங்கும் சூழல் சாதனங்கள்", "이 모드에서 켜질 환경 기기", "อุปกรณ์บรรยากาศที่เปิดในโหมดนี้", "Dispositivos ambientales activos en este modo"),
    "custom": ("Custom Mode Creator", "தனிப்பயன் பயன்முறை உருவாக்கி", "커스텀 모드 만들기", "สร้างโหมดกำหนดเอง", "Creador de Modo Personalizado"),
    "cname": ("Custom mode name", "தனிப்பயன் பயன்முறை பெயர்", "커스텀 모드 이름", "ชื่อโหมดกำหนดเอง", "Nombre del modo"),
    "dev_bulb": ("Bulb scene", "விளக்கு காட்சி", "전구 장면", "ซีนหลอดไฟ", "Escena de bombilla"),
    "dev_ac": ("AC mode", "ஏசி பயன்முறை", "에어컨 모드", "โหมดแอร์", "Modo A/C"),
    "dev_fan": ("Fan mode", "மின்விசிறி பயன்முறை", "팬 모드", "โหมดพัดลม", "Modo del ventilador"),
    "intens": ("Instrument intensity", "இசைக்கருவி அளவு", "악기 강도", "ความเข้มของเครื่องดนตรี", "Intensidad de instrumentos"),
    "need_name": ("Please enter a mode name.", "பயன்முறை பெயரை உள்ளிடவும்.", "모드 이름을 입력하세요.", "กรุณาใส่ชื่อโหมด", "Introduce un nombre de modo."),
    "setup": ("Initial Profile Setup", "ஆரம்ப சுயவிவர அமைப்பு", "초기 프로필 설정", "ตั้งค่าโปรไฟล์เริ่มต้น", "Configuración Inicial del Perfil"),
    "name": ("Full Name", "முழு பெயர்", "이름", "ชื่อเต็ม", "Nombre completo"),
    "dob": ("Date of Birth", "பிறந்த தேதி", "생년월일", "วันเกิด", "Fecha de nacimiento"),
    "pob": ("Place of Birth (City/Town)", "பிறந்த இடம் (நகரம்/ஊர்)", "출생지 (도시/마을)", "สถานที่เกิด (เมือง/เมืองเล็ก)", "Lugar de nacimiento (Ciudad/Pueblo)"),
    "tob": ("Time of Birth", "பிறந்த நேரம்", "출생 시각", "เวลาเกิด", "Hora de nacimiento"),
    "hour": ("Hour", "மணி", "시", "ชั่วโมง", "Hora"),
    "minute": ("Minute", "நிமிடம்", "분", "นาที", "Minuto"),
    "need_fields": ("Please enter your name and place of birth.", "உங்கள் பெயர் மற்றும் பிறந்த இடத்தை உள்ளிடவும்.", "이름과 출생지를 입력하세요.", "กรุณากรอกชื่อและสถานที่เกิด", "Introduce tu nombre y lugar de nacimiento."),
    "welcome": ("✨ Welcome back, {n}!", "✨ மீண்டும் வருக, {n}!", "✨ 다시 오신 것을 환영합니다, {n}님!", "✨ ยินดีต้อนรับกลับ, {n}!", "✨ ¡Bienvenido de nuevo, {n}!"),
    "edit": ("✏️ Edit Birth Details", "✏️ பிறப்பு விவரங்களை திருத்து", "✏️ 출생 정보 수정", "✏️ แก้ไขข้อมูลการเกิด", "✏️ Editar datos de nacimiento"),
    "nudge": ("💛 Hey {n}! A friendly nudge: take one slow, deep breath. Your Do's, Don'ts and Caution for today are ready to keep you centered.",
              "💛 ஹே {n}! ஒரு அன்பான நினைவூட்டல்: ஒரு மெதுவான ஆழ்ந்த மூச்சு எடுங்கள். இன்று உங்களை சமநிலையில் வைக்க உங்கள் செய்ய வேண்டியவை, கூடாதவை, எச்சரிக்கை தயாராக உள்ளன.",
              "💛 {n}님, 다정한 알림이에요! 천천히 깊게 숨을 한 번 쉬어 보세요. 오늘 중심을 지켜줄 해야 할 일, 하지 말아야 할 일, 주의사항이 준비되어 있어요.",
              "💛 สวัสดี {n}! ขอเตือนเบา ๆ หายใจเข้าลึก ๆ ช้า ๆ สักครั้ง สิ่งที่ควรทำ ไม่ควรทำ และข้อควรระวังของวันนี้พร้อมแล้วเพื่อช่วยให้คุณมั่นคง",
              "💛 ¡Hola {n}! Un recordatorio amable: respira lento y profundo una vez. Tus Qué hacer, Qué evitar y Precaución de hoy están listos para mantenerte centrado."),
    "plan": ("Today's Strategic Action Plan", "இன்றைய உத்தி செயல் திட்டம்", "오늘의 전략 실행 계획", "แผนปฏิบัติการเชิงกลยุทธ์ของวันนี้", "Plan Estratégico de Hoy"),
    "do": ("✅ Do's", "✅ செய்ய வேண்டியவை", "✅ 해야 할 일", "✅ สิ่งที่ควรทำ", "✅ Qué hacer"),
    "dont": ("❌ Don'ts", "❌ கூடாதவை", "❌ 하지 말아야 할 일", "❌ สิ่งที่ไม่ควรทำ", "❌ Qué evitar"),
    "caution": ("⚠️ Caution", "⚠️ எச்சரிக்கை", "⚠️ 주의", "⚠️ ข้อควรระวัง", "⚠️ Precaución"),
    "deep": ("📖 Deep Explanation", "📖 ஆழமான விளக்கம்", "📖 심층 설명", "📖 คำอธิบายเชิงลึก", "📖 Explicación Profunda"),
    "chat": ("Speak to your Divine Compass", "உங்கள் தெய்வீக திசைகாட்டியுடன் பேசுங்கள்", "신성한 나침반과 대화하세요", "พูดคุยกับเข็มทิศศักดิ์สิทธิ์ของคุณ", "Habla con tu Brújula Divina"),
    "chat_ph": ("Ask your Inner Compass", "உங்கள் உள் திசைகாட்டியிடம் கேளுங்கள்", "내면의 나침반에게 물어보세요", "ถามเข็มทิศภายในของคุณ", "Pregunta a tu Brújula Interior"),
    "online": ("online", "இணைப்பில்", "온라인", "ออนไลน์", "en línea"),
    "need_profile": ("Save your birth details above to unlock your Divine Compass.", "உங்கள் தெய்வீக திசைகாட்டியைத் திறக்க மேலே பிறப்பு விவரங்களைச் சேமிக்கவும்.", "신성한 나침반을 사용하려면 위에 출생 정보를 저장하세요.", "บันทึกข้อมูลการเกิดด้านบนเพื่อปลดล็อกเข็มทิศศักดิ์สิทธิ์", "Guarda tus datos de nacimiento arriba para activar tu Brújula Divina."),
    "conn_hub": ("Device Connection Hub", "சாதன இணைப்பு மையம்", "기기 연결 허브", "ศูนย์เชื่อมต่ออุปกรณ์", "Centro de conexión de dispositivos"),
    "conn_all": ("🔗 Connect all devices", "🔗 அனைத்து சாதனங்களையும் இணை", "🔗 모든 기기 연결", "🔗 เชื่อมต่ออุปกรณ์ทั้งหมด", "🔗 Conectar todos los dispositivos"),
    "conn_setup": ("Connection setup", "இணைப்பு அமைப்பு", "연결 설정", "การตั้งค่าการเชื่อมต่อ", "Configuración de conexión"),
    "proto": ("Protocol", "நெறிமுறை", "프로토콜", "โปรโตคอล", "Protocolo"),
    "addr": ("IP address / URL", "IP முகவரி / URL", "IP 주소 / URL", "ที่อยู่ IP / URL", "Dirección IP / URL"),
    "conn_btn": ("Connect / Test", "இணை / சோதி", "연결 / 테스트", "เชื่อมต่อ / ทดสอบ", "Conectar / Probar"),
    "s_ok": ("Connected", "இணைந்தது", "연결됨", "เชื่อมต่อแล้ว", "Conectado"),
    "s_no": ("Not connected", "இணைக்கப்படவில்லை", "연결 안 됨", "ยังไม่เชื่อมต่อ", "No conectado"),
    "s_off": ("Offline", "ஆஃப்லைன்", "오프라인", "ออฟไลน์", "Sin conexión"),
    "dev_hint": ("Simulation works instantly. For real hardware choose Philips WiZ (UDP) with the bulb's IP, or Home Assistant / REST with a webhook URL.",
                 "உருவகப்படுத்தல் உடனே வேலை செய்யும். உண்மையான சாதனத்திற்கு விளக்கின் IP உடன் Philips WiZ (UDP) அல்லது Home Assistant / REST webhook URL தேர்வு செய்யவும்.",
                 "시뮬레이션은 즉시 작동합니다. 실제 기기는 전구 IP가 있는 Philips WiZ (UDP) 또는 웹훅 URL이 있는 Home Assistant / REST를 선택하세요.",
                 "โหมดจำลองใช้งานได้ทันที สำหรับอุปกรณ์จริงให้เลือก Philips WiZ (UDP) พร้อม IP ของหลอดไฟ หรือ Home Assistant / REST พร้อม URL ของ webhook",
                 "La simulación funciona al instante. Para hardware real elige Philips WiZ (UDP) con la IP de la bombilla, o Home Assistant / REST con una URL de webhook."),
    "dev_my": ("My Smart Devices", "என் ஸ்மார்ட் சாதனங்கள்", "내 스마트 기기", "อุปกรณ์อัจฉริยะของฉัน", "Mis dispositivos inteligentes"),
    "dev_add": ("Add a device", "சாதனத்தைச் சேர்", "기기 추가", "เพิ่มอุปกรณ์", "Añadir dispositivo"),
    "dev_pick": ("Device type", "சாதன வகை", "기기 종류", "ประเภทอุปกรณ์", "Tipo de dispositivo"),
    "dev_room": ("Room", "அறை", "방", "ห้อง", "Habitación"),
    "dev_name": ("Custom name (optional)", "தனிப்பயன் பெயர் (விருப்பம்)", "사용자 지정 이름 (선택)", "ชื่อกำหนดเอง (ไม่บังคับ)", "Nombre personalizado (opcional)"),
    "dev_btn": ("Add device", "சாதனத்தைச் சேர்", "기기 추가", "เพิ่มอุปกรณ์", "Añadir"),
    "power_lbl": ("Power", "மின்சாரம்", "전원", "เปิด/ปิด", "Encendido"),
    "summary": ("Fleet summary", "சாதன சுருக்கம்", "기기 요약", "สรุปอุปกรณ์", "Resumen de dispositivos"),
    "sync": ("Re-apply active atmosphere to all devices", "செயலில் உள்ள சூழலை அனைத்து சாதனங்களுக்கும் மீண்டும் பயன்படுத்து", "현재 분위기를 모든 기기에 다시 적용", "ใช้บรรยากาศปัจจุบันกับอุปกรณ์ทั้งหมดอีกครั้ง", "Volver a aplicar el ambiente a todos los dispositivos"),
    "synced": ("Devices synced.", "சாதனங்கள் ஒத்திசைக்கப்பட்டன.", "기기가 동기화되었습니다.", "ซิงค์อุปกรณ์แล้ว", "Dispositivos sincronizados."),
    "api": ("Biometrics API URL", "உயிரியல் தரவு API முகவரி", "바이오메트릭 API 주소", "URL ของ API ข้อมูลชีวภาพ", "URL de la API biométrica"),
    "thr": ("Stress threshold (bpm)", "மன அழுத்த வரம்பு (bpm)", "스트레스 임계값 (bpm)", "เกณฑ์ความเครียด (bpm)", "Umbral de estrés (lpm)"),
    "rel": ("Relaxed upper limit (bpm)", "அமைதி நிலை உச்ச வரம்பு (bpm)", "편안함 상한 (bpm)", "ขีดจำกัดบนของสถานะผ่อนคลาย (bpm)", "Límite superior de relajación (lpm)"),
    "rest": ("Resting heart rate (bpm)", "ஓய்வு இதயத் துடிப்பு (bpm)", "안정시 심박수 (bpm)", "อัตราการเต้นหัวใจขณะพัก (bpm)", "Pulso en reposo (lpm)"),
    "poll": ("Biometric refresh interval (s)", "உயிரியல் தரவு புதுப்பிப்பு இடைவெளி (வி)", "바이오 데이터 갱신 간격 (초)", "ช่วงเวลารีเฟรชข้อมูลชีวภาพ (วินาที)", "Intervalo de actualización biométrica (s)"),
    "notif": ("Friendly nudge banner", "நட்பு நினைவூட்டல் பதாகை", "친근한 알림 배너", "แบนเนอร์แจ้งเตือนแบบเป็นกันเอง", "Banner de recordatorio amable"),
    "chime": ("Ring alert on nudge", "நினைவூட்டலில் மணி ஒலி", "알림 시 벨 소리", "เสียงกระดิ่งเมื่อมีการแจ้งเตือน", "Alerta sonora en el recordatorio"),
    "test": ("Test connection", "இணைப்பைச் சோதி", "연결 테스트", "ทดสอบการเชื่อมต่อ", "Probar conexión"),
    "reset": ("Reset all data", "அனைத்து தரவையும் மீட்டமை", "모든 데이터 초기화", "รีเซ็ตข้อมูลทั้งหมด", "Restablecer todo"),
    # --- New keys merged from NEW_T with full 5-language tuples ---
    "day": ("Day", "நாள்", "일", "วัน", "Día"),
    "month": ("Month", "மாதம்", "월", "เดือน", "Mes"),
    "year": ("Year", "ஆண்டு", "년", "ปี", "Año"),
    "room_sel": ("Active room", "செயலில் உள்ள அறை", "활성 방", "ห้องที่ใช้งาน", "Habitación activa"),
    "add_space": ("➕ Add Custom Space", "➕ தனிப்பயன் இடத்தைச் சேர்", "➕ 사용자 공간 추가", "➕ เพิ่มพื้นที่กำหนดเอง", "➕ Añadir espacio personalizado"),
    "sp_name": ("Room name (e.g. Terrace Garden, Gaming Den)", "அறை பெயர் (எ.கா. டெரஸ் தோட்டம், கேமிங் டென்)", "방 이름 (예: 테라스 가든, 게이밍 덴)", "ชื่อห้อง (เช่น สวนดาดฟ้า, เกมมิ่งเดน)", "Nombre de la habitación (ej. Jardín Terraza, Sala de Juegos)"),
    "sp_icon": ("Icon", "சின்னம்", "아이콘", "ไอคอน", "Icono"),
    "sp_type": ("Room type", "அறை வகை", "방 유형", "ประเภทห้อง", "Tipo de habitación"),
    "sp_devs": ("Assign devices from your fleet to this space", "உங்கள் சாதனக் குழுவிலிருந்து இந்த இடத்திற்கு சாதனங்களை ஒதுக்குங்கள்", "이 공간에 기기 할당", "กำหนดอุปกรณ์ให้กับพื้นที่นี้", "Asignar dispositivos a este espacio"),
    "sp_btn": ("Create space", "இடத்தை உருவாக்கு", "공간 만들기", "สร้างพื้นที่", "Crear espacio"),
    "sp_need": ("Please enter a room name.", "அறை பெயரை உள்ளிடவும்.", "방 이름을 입력하세요.", "กรุณาใส่ชื่อห้อง", "Introduce un nombre de habitación."),
    "sp_dup": ("A space with this name already exists.", "இந்த பெயரில் ஒரு இடம் ஏற்கனவே உள்ளது.", "이 이름의 공간이 이미 있습니다.", "มีพื้นที่ชื่อนี้อยู่แล้ว", "Ya existe un espacio con este nombre."),
    "sp_made": ("Space created: {n}", "இடம் உருவாக்கப்பட்டது: {n}", "공간 생성됨: {n}", "สร้างพื้นที่แล้ว: {n}", "Espacio creado: {n}"),
    "here": ("📍 You are here", "📍 நீங்கள் இங்கே இருக்கிறீர்கள்", "📍 현재 위치", "📍 คุณอยู่ที่นี่", "📍 Estás aquí"),
    "qc": ("🎛 Room quick controls", "🎛 அறை விரைவு கட்டுப்பாடுகள்", "🎛 방 빠른 제어", "🎛 การควบคุมห้องด่วน", "🎛 Controles rápidos de habitación"),
    "room_empty": ("No devices in this space yet. Assign some when creating a space, or move them in Device Fleet.", "இந்த இடத்தில் இன்னும் சாதனங்கள் இல்லை. இடத்தை உருவாக்கும்போது சிலவற்றை ஒதுக்குங்கள் அல்லது சாதனக் குழுவில் நகர்த்துங்கள்.", "이 공간에 아직 기기가 없습니다. 공간 생성 시 할당하거나 기기 목록에서 이동하세요.", "ยังไม่มีอุปกรณ์ในพื้นที่นี้ กำหนดเมื่อสร้างพื้นที่ หรือย้ายในรายการอุปกรณ์", "Aún no hay dispositivos en este espacio. Asigna algunos al crear un espacio o muévelos en Dispositivos."),
    "conn_title": ("Remote Access & Smart Geofence", "தொலைதூர அணுகல் & ஸ்மார்ட் ஜியோஃபென்ஸ்", "원격 액세스 & 스마트 지오펜스", "การเข้าถึงระยะไกล & สมาร์ทจีโอเฟนซ์", "Acceso Remoto y Geocerca Inteligente"),
    "conn_mode": ("Where are you right now?", "நீங்கள் இப்போது எங்கே இருக்கிறீர்கள்?", "지금 어디에 있나요?", "ตอนนี้คุณอยู่ที่ไหน?", "¿Dónde estás ahora?"),
    "conn_home": ("🏠 At Home (Local Matter / Wi-Fi Mesh)", "🏠 வீட்டில் (லோக்கல் மேட்டர் / வைஃபை மெஷ்)", "🏠 집 (로컬 매터 / 와이파이 메시)", "🏠 ที่บ้าน (โลคัลแมทเทอร์ / ไวไฟเมช)", "🏠 En casa (Matter local / Wi-Fi Mesh)"),
    "conn_away": ("🚗 Away / En Route (Remote 4G/5G Cloud Relay)", "🚗 வெளியே / வழியில் (ரிமோட் 4G/5G கிளவுட் ரிலே)", "🚗 외출 / 이동 중 (원격 4G/5G 클라우드 릴레이)", "🚗 อยู่นอกบ้าน / ระหว่างทาง (รีโมท 4G/5G คลาวด์รีเลย์)", "🚗 Fuera / En camino (Relé en la nube 4G/5G)"),
    "conn_local_cap": ("🏠 Local control: commands stay inside your home network (Matter / Wi-Fi mesh).", "🏠 லோக்கல் கட்டுப்பாடு: கட்டளைகள் உங்கள் வீட்டு நெட்வொர்க்கிற்குள் இருக்கும் (மேட்டர் / வைஃபை மெஷ்).", "🏠 로컬 제어: 명령은 홈 네트워크 내에 머뭅니다 (매터 / 와이파이 메시).", "🏠 ควบคุมในบ้าน: คำสั่งอยู่ในเครือข่ายบ้าน (แมทเทอร์ / ไวไฟเมช)", "🏠 Control local: los comandos permanecen en tu red doméstica (Matter / Wi-Fi mesh)."),
    "conn_cloud_cap": ("☁️ Remote control: commands travel through the secure 4G/5G cloud relay.", "☁️ ரிமோட் கட்டுப்பாடு: கட்டளைகள் பாதுகாப்பான 4G/5G கிளவுட் ரிலே வழியாகச் செல்லும்.", "☁️ 원격 제어: 명령은 보안 4G/5G 클라우드 릴레이를 통해 전달됩니다.", "☁️ ควบคุมระยะไกล: คำสั่งผ่านคลาวด์รีเลย์ 4G/5G ที่ปลอดภัย", "☁️ Control remoto: los comandos viajan por el relé seguro en la nube 4G/5G."),
    "geo_dist": ("Distance from home (km) - simulated GPS", "வீட்டிலிருந்து தூரம் (கிமீ) - உருவகப்படுத்தப்பட்ட ஜிபிஎஸ்", "집으로부터 거리 (km) - 시뮬레이션 GPS", "ระยะทางจากบ้าน (กม.) - จำลอง GPS", "Distancia desde casa (km) - GPS simulado"),
    "geo_dist_m": ("Distance from home", "வீட்டிலிருந்து தூரம்", "집으로부터 거리", "ระยะทางจากบ้าน", "Distancia desde casa"),
    "geo_eta": ("Estimated arrival", "மதிப்பிடப்பட்ட வருகை", "예상 도착", "เวลาถึงโดยประมาณ", "Llegada estimada"),
    "geo_zone": ("Geofence", "ஜியோஃபென்ஸ்", "지오펜스", "จีโอเฟนซ์", "Geocerca"),
    "geo_idle": ("Watching your route", "உங்கள் பாதையைக் கவனிக்கிறது", "경로를 주시 중", "กำลังติดตามเส้นทาง", "Vigilando tu ruta"),
    "geo_pending": ("Waiting for your confirmation", "உங்கள் உறுதிப்படுத்தலுக்காகக் காத்திருக்கிறது", "확인을 기다리는 중", "รอการยืนยันของคุณ", "Esperando tu confirmación"),
    "geo_confirmed": ("Pre-conditioning confirmed", "முன்-சீரமைப்பு உறுதிப்படுத்தப்பட்டது", "사전 조절 확인됨", "ยืนยันการปรับสภาพล่วงหน้าแล้ว", "Pre-acondicionamiento confirmado"),
    "geo_dismissed": ("Dismissed - appliances on standby", "நிராகரிக்கப்பட்டது - சாதனங்கள் தெரியாமல்", "무시됨 - 대기 중", "ปัดทิ้ง - อุปกรณ์สแตนด์บาย", "Descartado - electrodomésticos en espera"),
    "geo_alert": ("📍 Smart Geofence Alert: Hey {n}, you are {m} mins away from home. Would you like to pre-heat the En-Suite Bath Geyser to 42°C and pre-cool Master Suite AC to 22°C?", "📍 ஸ்மார்ட் ஜியோஃபென்ஸ் எச்சரிக்கை: ஹே {n}, நீங்கள் வீட்டிலிருந்து {m} நிமிடங்கள் தொலைவில் உள்ளீர்கள். என்சூட் பாத் கீசரை 42°C ஆக முன்கூட்டியே சூடாக்கி, மாஸ்டர் சூட் ஏசியை 22°C ஆக முன்கூட்டியே குளிர்விக்கவா?", "📍 스마트 지오펜스 알림: {n}님, 집에서 {m}분 거리에 있습니다. 욕실 온수기를 42°C로 예열하고 마스터 스위트 에어컨을 22°C로 냉방할까요?", "📍 แจ้งเตือนสมาร์ทจีโอเฟนซ์: สวัสดี {n} คุณอยู่ห่างจากบ้าน {m} นาที ต้องการอุ่นเครื่องทำน้ำอุ่นเป็น 42°C และเปิดแอร์ห้องนอนหลักเป็น 22°C ล่วงหน้าหรือไม่?", "📍 Alerta de Geocerca Inteligente: Hola {n}, estás a {m} minutos de casa. ¿Quieres precalentar el calentador del baño a 42°C y precooler el A/C de la suite a 22°C?"),
    "geo_yes": ("✅ Confirm & Pre-Condition Devices", "✅ உறுதிசெய்து சாதனங்களை முன்-சீரமை", "✅ 확인 및 사전 조절", "✅ ยืนยันและปรับสภาพอุปกรณ์", "✅ Confirmar y preacondicionar dispositivos"),
    "geo_no": ("❌ Dismiss / Keep Standby", "❌ நிராகரி / தெரியாமல் வைத்திரு", "❌ 무시 / 대기 유지", "❌ ปัดทิ้ง / คงสถานะสแตนด์บาย", "❌ Descartar / Mantener en espera"),
    "away_pause": ("You are away, so Aura Companion is paused for in-home sensors. Remote commands use the cloud relay.", "நீங்கள் வெளியே இருப்பதால், வீட்டு சென்சார்களுக்கான ஆரா துணை இடைநிறுத்தப்பட்டுள்ளது. ரிமோட் கட்டளைகள் கிளவுட் ரிலேவைப் பயன்படுத்துகின்றன.", "외출 중이므로 실내 센서용 Aura Companion이 일시중지됩니다. 원격 명령은 클라우드 릴레이를 사용합니다.", "คุณอยู่นอกบ้าน Aura Companion จึงหยุดชั่วคราวสำหรับเซ็นเซอร์ในบ้าน คำสั่งระยะไกลใช้คลาวด์รีเลย์", "Estás fuera, Aura Companion está en pausa para sensores. Los comandos remotos usan el relé en la nube."),
    "remote_status": ("Remote pre-conditioning status", "ரிமோட் முன்-சீரமைப்பு நிலை", "원격 사전 조절 상태", "สถานะการปรับสภาพล่วงหน้าระยะไกล", "Estado de preacondicionamiento remoto"),
    "ml_title": ("Room-Level Location & Follow-Me", "அறை அளவு இருப்பிடம் & என்னைப் பின்தொடர்", "방 수준 위치 & 팔로우미", "ตำแหน่งระดับห้อง & ติดตามฉัน", "Ubicación por Habitación y Seguimiento"),
    "ml_dev": ("Tracked wearable / device", "கண்காணிக்கப்பட்ட அணிகலன் / சாதனம்", "추적 장치", "อุปกรณ์สวมใส่ที่ติดตาม", "Dispositivo rastreado"),
    "ml_engine": ("Tracking engine", "கண்காணிப்பு இயந்திரம்", "추적 엔진", "เอนจิ้นติดตาม", "Motor de seguimiento"),
    "ml_uwb": ("UWB - Ultra-Wideband: centimetre accuracy + direction of arrival", "UWB - அல்ட்ரா-வைட்பேண்ட்: சென்டிமீட்டர் துல்லியம் + வருகை திசை", "UWB - 초광대역: 센티미터 정확도 + 도래 방향", "UWB - อัลตร้าไวด์แบนด์: ความแม่นยำระดับเซนติเมตร + ทิศทาง", "UWB - Banda Ultra Ancha: precisión centimétrica + dirección de llegada"),
    "ml_ble": ("BLE - Bluetooth Low Energy: room-level signal-strength (RSSI)", "BLE - புளூடூத் லோ எனர்ஜி: அறை அளவு சமிக்ஞை வலிமை (RSSI)", "BLE - 블루투스 로우 에너지: 방 수준 신호 강도 (RSSI)", "BLE - บลูทูธพลังงานต่ำ: ความแรงสัญญาณระดับห้อง (RSSI)", "BLE - Bluetooth de Baja Energía: intensidad de señal por habitación (RSSI)"),
    "ml_sim": ("Where are you? (live room simulator)", "நீங்கள் எங்கே? (நேரடி அறை சிமுலேட்டர்)", "어디에 있나요? (실시간 방 시뮬레이터)", "คุณอยู่ที่ไหน? (จำลองห้องสด)", "¿Dónde estás? (simulador de habitación en vivo)"),
    "ml_follow": ("Follow-Me: switch off the room I leave and wake the room I enter", "என்னைப் பின்தொடர்: விட்டு வெளியேறும் அறையை அணைத்து, நுழையும் அறையை எழுப்பு", "팔로우미: 떠나는 방은 끄고 들어가는 방은 켜기", "ติดตามฉัน: ปิดห้องที่จากไป เปิดห้องที่เข้ามา", "Seguimiento: apaga la habitación que dejo y enciende la que entro"),
    "ml_cut": ("When I leave a room, its AC goes", "நான் அறையை விட்டு வெளியேறும்போது அதன் ஏசி", "방을 떠나면 에어컨", "เมื่อฉันออกจากห้อง แอร์", "Cuando salgo de una habitación, su A/C"),
    "ml_calm": ("Room-isolated calm (heart rate above 85 BPM in Work Studio)", "அறை-தனிமைப்படுத்தப்பட்ட அமைதி (வேலை ஸ்டுடியோவில் இதயத் துடிப்பு 85 BPM க்கு மேல்)", "방 격리 진정 (작업실 심박수 85 BPM 초과)", "ความสงบเฉพาะห้อง (ชีพจรเกิน 85 BPM ในสตูดิโอทำงาน)", "Calma aislada por habitación (pulso superior a 85 BPM en el estudio)"),
    "ml_away": ("Indoor tracking is paused while you are away from home.", "வீட்டை விட்டு வெளியே இருக்கும்போது உள்ளரங்க கண்காணிப்பு இடைநிறுத்தப்பட்டுள்ளது.", "외출 중에는 실내 추적이 일시중지됩니다.", "การติดตามในบ้านหยุดชั่วคราวเมื่อคุณออกจากบ้าน", "El seguimiento interior se pausa cuando estás fuera de casa."),
    "ml_zone": ("Your zone", "உங்கள் மண்டலம்", "내 구역", "โซนของคุณ", "Tu zona"),
    "ml_dist": ("Distance to room anchor", "அறை அன்கருக்கான தூரம்", "방 앵커까지 거리", "ระยะทางถึงจุดยึดห้อง", "Distancia al ancla de habitación"),
    "ml_aoa": ("Angle of arrival", "வருகை கோணம்", "도래 각도", "มุมการมาถึง", "Ángulo de llegada"),
    "ml_acc": ("Accuracy", "துல்லியம்", "정확도", "ความแม่นยำ", "Precisión"),
    "ml_rssi": ("Signal strength per room anchor (dBm)", "ஒரு அறை அன்கருக்கான சமிக்ஞை வலிமை (dBm)", "방 앵커별 신호 강도 (dBm)", "ความแรงสัญญาณต่อจุดยึดห้อง (dBm)", "Intensidad de señal por ancla (dBm)"),
    "ml_est": ("Estimated room", "மதிப்பிடப்பட்ட அறை", "추정 방", "ห้องที่ประมาณ", "Habitación estimada"),
    "feel": ("You seem {s} → home atmosphere: {m}", "நீங்கள் {s} ஆகத் தெரிகிறது → வீட்டு சூழல்: {m}", "당신은 {s} 상태 → 집 분위기: {m}", "คุณดู {s} → บรรยากาศบ้าน: {m}", "Pareces {s} → ambiente del hogar: {m}"),
    "calm_note": ("🌊 {r} is in calm mode ({m}). Only this room changed; the rest of the house is untouched.", "🌊 {r} அமைதி பயன்முறையில் உள்ளது ({m}). இந்த அறை மட்டும் மாறியது; மற்ற வீடு தொடப்படவில்லை.", "🌊 {r}은(는) 진정 모드({m})입니다. 이 방만 변경되었습니다.", "🌊 {r} อยู่ในโหมดสงบ ({m}) เปลี่ยนเฉพาะห้องนี้", "🌊 {r} está en modo calma ({m}). Solo cambió esta habitación."),
    "rt_title": ("Daily Routine Scheduler", "தினசரி வழக்க அட்டவணையாளர்", "일일 루틴 스케줄러", "ตัวจัดตารางกิจวัตรประจำวัน", "Programador de Rutinas Diarias"),
    "rt_hint": ("Routines pre-activate devices on a timer. They protect their own devices from Auto/Manual changes for a while, so nothing fights each other.", "வழக்கங்கள் டைமரில் சாதனங்களை முன்கூட்டியே இயக்குகின்றன. அவை சிறிது நேரம் ஆட்டோ/கைமுறை மாற்றங்களிலிருந்து தங்கள் சாதனங்களைப் பாதுகாக்கின்றன.", "루틴은 타이머로 기기를 미리 켭니다. 잠시 동안 자동/수동 변경으로부터 보호합니다.", "กิจวัตรจะเปิดอุปกรณ์ล่วงหน้าตามเวลา ป้องกันการเปลี่ยนแปลงชั่วคราว", "Las rutinas preactivan dispositivos con temporizador. Protegen sus dispositivos de cambios automáticos/manuales."),
    "rt_on": ("Enabled", "இயக்கப்பட்டது", "활성화됨", "เปิดใช้งาน", "Habilitado"),
    "rt_wake": ("Wake-up time", "எழும் நேரம்", "기상 시간", "เวลาตื่น", "Hora de despertar"),
    "rt_bath": ("Bath time", "குளியல் நேரம்", "목욕 시간", "เวลาอาบน้ำ", "Hora de baño"),
    "rt_sleep": ("Sleep target", "உறக்க இலக்கு", "수면 목표", "เป้าหมายการนอน", "Objetivo de sueño"),
    "rt_off": ("Start this many minutes before", "இத்தனை நிமிடங்களுக்கு முன்பு தொடங்கு", "몇 분 전에 시작", "เริ่มก่อนกี่นาที", "Comenzar estos minutos antes"),
    "rt_run": ("▶ Run now (test)", "▶ இப்போது இயக்கு (சோதனை)", "▶ 지금 실행 (테스트)", "▶ เรียกใช้เลย (ทดสอบ)", "▶ Ejecutar ahora (prueba)"),
    "rt_add": ("➕ Add Custom Routine", "➕ தனிப்பயன் வழக்கத்தைச் சேர்", "➕ 사용자 루틴 추가", "➕ เพิ่มกิจวัตรกำหนดเอง", "➕ Añadir rutina personalizada"),
    "rt_name": ("Routine name", "வழக்கத்தின் பெயர்", "루틴 이름", "ชื่อกิจวัตร", "Nombre de la rutina"),
    "rt_time": ("Target time", "இலக்கு நேரம்", "목표 시간", "เวลาเป้าหมาย", "Hora objetivo"),
    "rt_devs": ("Devices to control", "கட்டுப்படுத்த வேண்டிய சாதனங்கள்", "제어할 기기", "อุปกรณ์ที่จะควบคุม", "Dispositivos a controlar"),
    "rt_act": ("Action", "செயல்", "동작", "การกระทำ", "Acción"),
    "rt_ran": ("✅ Ran today", "✅ இன்று இயங்கியது", "✅ 오늘 실행됨", "✅ ทำงานวันนี้", "✅ Ejecutado hoy"),
    "rt_need": ("Please enter a routine name and pick at least one device.", "வழக்கத்தின் பெயரை உள்ளிட்டு குறைந்தது ஒரு சாதனத்தைத் தேர்ந்தெடுக்கவும்.", "루틴 이름과 하나 이상의 기기를 선택하세요.", "กรุณาใส่ชื่อกิจวัตรและเลือกอุปกรณ์อย่างน้อยหนึ่งรายการ", "Introduce un nombre de rutina y elige al menos un dispositivo."),
    "rt_made": ("Routine added", "வழக்கம் சேர்க்கப்பட்டது", "루틴 추가됨", "เพิ่มกิจวัตรแล้ว", "Rutina añadida"),
    "rt_ranmsg": ("Scheduled routine started", "திட்டமிடப்பட்ட வழக்கம் தொடங்கியது", "예약된 루틴 시작됨", "กิจวัตรที่ตั้งเวลาไว้เริ่มแล้ว", "Rutina programada iniciada"),
    "theme": ("Theme", "தோற்றம்", "테마", "ธีม", "Tema"),
    "theme_dark": ("🌙 Dark · Black & Gold", "🌙 இருண்ட · கருப்பு & தங்கம்", "🌙 다크 · 블랙 & 골드", "🌙 มืด · ดำ & ทอง", "🌙 Oscuro · Negro y Dorado"),
    "theme_light": ("☀️ Light · White", "☀️ ஒளி · வெள்ளை", "☀️ 라이트 · 화이트", "☀️ สว่าง · ขาว", "☀️ Claro · Blanco"),
    "rs_room": ("Room to configure", "கட்டமைக்க வேண்டிய அறை", "설정할 방", "ห้องที่จะกำหนดค่า", "Habitación a configurar"),
    "rs_hint": ("The Live Dashboard keeps the one-click active-room selector. Everything that sets up rooms, remote access and the geofence lives on this page.", "நேரடி டாஷ்போர்டு ஒரு கிளிக் செயலில் உள்ள அறை தேர்வியை வைத்திருக்கிறது. அறைகள், தொலைதூர அணுகல் மற்றும் ஜியோஃபென்ஸ் அமைப்பது இந்தப் பக்கத்தில் உள்ளது.", "라이브 대시보드는 원클릭 활성 방 선택기를 유지합니다. 방 설정, 원격 액세스, 지오펜스는 이 페이지에 있습니다.", "แดชบอร์ดสดมีตัวเลือกห้องที่ใช้งานอยู่ การตั้งค่าห้อง การเข้าถึงระยะไกล และจีโอเฟนซ์อยู่ในหน้านี้", "El Panel en Vivo mantiene el selector de habitación activa. La configuración de habitaciones, acceso remoto y geocerca está en esta página."),
    "rs_dash_hint": ("Room settings, Remote Access and Smart Geofence now live in the “Room Settings, Remote Access & Smart Geofence” tab of the Navigate menu.", "அறை அமைப்புகள், தொலைதூர அணுகல் மற்றும் ஸ்மார்ட் ஜியோஃபென்ஸ் இப்போது வழிசெலுத்தல் மெனுவின் “அறை அமைப்புகள், தொலைதூர கட்டுப்பாடு & ஜியோஃபென்ஸ்” தாவலில் உள்ளன.", "방 설정, 원격 액세스 및 스마트 지오펜스는 이제 '방 설정, 원격 액세스 & 스마트 지오펜스' 탭에 있습니다.", "การตั้งค่าห้อง การเข้าถึงระยะไกล และสมาร์ทจีโอเฟนซ์อยู่ในแท็บ 'การตั้งค่าห้อง การเข้าถึงระยะไกล & สมาร์ทจีโอเฟนซ์'", "La configuración de habitaciones, acceso remoto y geocerca están en la pestaña 'Configuración de Habitación, Acceso Remoto y Geocerca Inteligente'."),
    "rs_sec_room": ("Room Settings", "அறை அமைப்புகள்", "방 설정", "การตั้งค่าห้อง", "Configuración de Habitación"),
    "rs_manage": ("Manage this space (move devices / delete)", "இந்த இடத்தை நிர்வகி (சாதனங்களை நகர்த்து / நீக்கு)", "이 공간 관리 (기기 이동 / 삭제)", "จัดการพื้นที่นี้ (ย้ายอุปกรณ์ / ลบ)", "Gestionar este espacio (mover / eliminar)"),
    "rs_move": ("Move devices from other rooms into this room", "மற்ற அறைகளிலிருந்து இந்த அறைக்கு சாதனங்களை நகர்த்து", "다른 방의 기기를 이 방으로 이동", "ย้ายอุปกรณ์จากห้องอื่นมาที่ห้องนี้", "Mover dispositivos de otras habitaciones a esta"),
    "rs_move_btn": ("Move devices here", "சாதனங்களை இங்கே நகர்த்து", "기기를 여기로 이동", "ย้ายอุปกรณ์มาที่นี่", "Mover dispositivos aquí"),
    "rs_moved": ("{c} device(s) moved to {n}", "{c} சாதனம்(கள்) {n} க்கு நகர்த்தப்பட்டன", "{c}개 기기가 {n}(으)로 이동됨", "ย้าย {c} อุปกรณ์ไปที่ {n}", "{c} dispositivo(s) movidos a {n}"),
    "rs_dest": ("When deleting, move its devices to", "நீக்கும்போது, அதன் சாதனங்களை இங்கே நகர்த்து", "삭제 시 기기를 이동할 위치", "เมื่อลบ ให้ย้ายอุปกรณ์ไปที่", "Al eliminar, mover dispositivos a"),
    "rs_del": ("Delete this space", "இந்த இடத்தை நீக்கு", "이 공간 삭제", "ลบพื้นที่นี้", "Eliminar este espacio"),
    "rs_deleted": ("Space deleted: {n}", "இடம் நீக்கப்பட்டது: {n}", "공간 삭제됨: {n}", "ลบพื้นที่แล้ว: {n}", "Espacio eliminado: {n}"),
    "rs_protected": ("This space is used by built-in automations (geofence, routines, calm mode) so it cannot be deleted. You can still move devices in and out of it.", "இந்த இடம் உள்ளமைக்கப்பட்ட தானியங்கிகளால் பயன்படுத்தப்படுகிறது (ஜியோஃபென்ஸ், வழக்கங்கள், அமைதி பயன்முறை) எனவே நீக்க முடியாது. சாதனங்களை நகர்த்தலாம்.", "이 공간은 내장 자동화(지오펜스, 루틴, 진정 모드)에 사용되므로 삭제할 수 없습니다. 기기 이동은 가능합니다.", "พื้นที่นี้ใช้โดยระบบอัตโนมัติในตัว (จีโอเฟนซ์ กิจวัตร โหมดสงบ) จึงลบไม่ได้ แต่ย้ายอุปกรณ์ได้", "Este espacio lo usan automatizaciones (geocerca, rutinas, modo calma) y no se puede eliminar. Puedes mover dispositivos."),
    "rs_last": ("You need at least one space.", "குறைந்தது ஒரு இடம் தேவை.", "최소 하나의 공간이 필요합니다.", "คุณต้องมีพื้นที่อย่างน้อยหนึ่งแห่ง", "Necesitas al menos un espacio."),
    "dev_rename": ("Device name (edit to recognise it)", "சாதனத்தின் பெயர் (அடையாளம் காண திருத்து)", "기기 이름 (편집하여 식별)", "ชื่ออุปกรณ์ (แก้ไขเพื่อจดจำ)", "Nombre del dispositivo (editar para reconocerlo)"),
    "dev_rename_bad": ("Name must be 1-40 characters and not used by another device.", "பெயர் 1-40 எழுத்துகளாக இருக்க வேண்டும், மற்ற சாதனத்தால் பயன்படுத்தப்படக்கூடாது.", "이름은 1-40자이며 다른 기기에서 사용되지 않아야 합니다.", "ชื่อต้องยาว 1-40 ตัวอักษรและไม่ซ้ำกับอุปกรณ์อื่น", "El nombre debe tener 1-40 caracteres y no usarse en otro dispositivo."),
    "dev_renamed": ("Renamed to {n}", "{n} என மறுபெயரிடப்பட்டது", "{n}(으)로 이름 변경됨", "เปลี่ยนชื่อเป็น {n}", "Renombrado a {n}"),
    "rs_devices": ("Devices in this room: name, power, level, colour", "இந்த அறையில் உள்ள சாதனங்கள்: பெயர், மின்சாரம், நிலை, நிறம்", "이 방의 기기: 이름, 전원, 수준, 색상", "อุปกรณ์ในห้องนี้: ชื่อ, เปิด/ปิด, ระดับ, สี", "Dispositivos en esta habitación: nombre, encendido, nivel, color"),
    "rs_dev_remove": ("Remove device", "சாதனத்தை அகற்று", "기기 제거", "ลบอุปกรณ์", "Eliminar dispositivo"),
    "rs_add_dev": ("Add another device to this room (e.g. Bulb 2, Table Fan, Air Cooler)", "இந்த அறைக்கு மற்றொரு சாதனத்தைச் சேர் (எ.கா. பல்பு 2, மேசை விசிறி, ஏர் கூலர்)", "이 방에 다른 기기 추가 (예: 전구 2, 탁상 선풍기)", "เพิ่มอุปกรณ์อื่นให้ห้องนี้ (เช่น หลอดไฟ 2, พัดลมตั้งโต๊ะ)", "Añadir otro dispositivo a esta habitación (ej. Bombilla 2, Ventilador, Enfriador)"),
    "rs_dev_added": ("Added {n} to {r}", "{n} ஐ {r} இல் சேர்க்கப்பட்டது", "{n}을(를) {r}에 추가함", "เพิ่ม {n} ใน {r} แล้ว", "Añadido {n} a {r}"),
    "rs_preset": ("Room default (one click on the Live Dashboard)", "அறை இயல்புநிலை (நேரடி டாஷ்போர்டில் ஒரு கிளிக்)", "방 기본값 (라이브 대시보드에서 원클릭)", "ค่าเริ่มต้นห้อง (หนึ่งคลิกบนแดชบอร์ดสด)", "Predeterminado de habitación (un clic en el Panel)"),
    "rs_preset_hint": ("Set the devices below the way you like this room, then save. The Live Dashboard and Auto Mode (when you walk in) use this default.", "விரும்பியபடி சாதனங்களை அமைத்து சேமிக்கவும். நேரடி டாஷ்போர்டு மற்றும் ஆட்டோ மোড இந்த இயல்புநிலையைப் பயன்படுத்தும்.", "원하는 대로 기기를 설정하고 저장하세요. 라이브 대시보드와 자동 모드가 이 기본값을 사용합니다.", "ตั้งค่าอุปกรณ์ตามต้องการแล้วบันทึก แดชบอร์ดสดและโหมดอัตโนมัติใช้ค่านี้", "Configura los dispositivos a tu gusto y guarda. El Panel y el Modo Automático usan este predeterminado."),
    "rs_preset_save": ("💾 Save current settings as this room's default", "💾 தற்போதைய அமைப்புகளை இந்த அறையின் இயல்புநிலையாகச் சேமி", "💾 현재 설정을 이 방의 기본값으로 저장", "💾 บันทึกการตั้งค่าปัจจุบันเป็นค่าเริ่มต้น", "💾 Guardar ajustes actuales como predeterminado"),
    "rs_preset_apply": ("Apply default to {n}", "{n} க்கு இயல்புநிலையைப் பயன்படுத்து", "{n}에 기본값 적용", "ใช้ค่าเริ่มต้นกับ {n}", "Aplicar predeterminado a {n}"),
    "rs_preset_clear": ("Clear default", "இயல்புநிலையை அழி", "기본값 지우기", "ล้างค่าเริ่มต้น", "Borrar predeterminado"),
    "rs_preset_has": ("Saved default covers {c} device(s).", "சேமிக்கப்பட்ட இயல்புநிலை {c} சாதனங்களை உள்ளடக்கியது.", "저장된 기본값이 {c}개 기기를 포함합니다.", "ค่าเริ่มต้นที่บันทึกครอบคลุม {c} อุปกรณ์", "El predeterminado guardado cubre {c} dispositivo(s)."),
    "rs_preset_saved": ("Default saved for {n} ({c} device(s))", "{n} க்கான இயல்புநிலை சேமிக்கப்பட்டது ({c} சாதனங்கள்)", "{n}의 기본값 저장됨 ({c}개 기기)", "บันทึกค่าเริ่มต้นสำหรับ {n} แล้ว ({c} อุปกรณ์)", "Predeterminado guardado para {n} ({c} dispositivo(s))"),
    "rs_preset_cleared": ("Default cleared for {n}", "{n} க்கான இயல்புநிலை அழிக்கப்பட்டது", "{n}의 기본값 삭제됨", "ล้างค่าเริ่มต้นสำหรับ {n} แล้ว", "Predeterminado borrado para {n}"),
    "rs_preset_applied": ("Default applied: {n} ({c} device(s))", "இயல்புநிலை பயன்படுத்தப்பட்டது: {n} ({c} சாதனங்கள்)", "기본값 적용됨: {n} ({c}개 기기)", "ใช้ค่าเริ่มต้นแล้ว: {n} ({c} อุปกรณ์)", "Predeterminado aplicado: {n} ({c} dispositivo(s))"),
    "preset_apply_all": ("Apply defaults to ALL rooms", "அனைத்து அறைகளுக்கும் இயல்புநிலைகளைப் பயன்படுத்து", "모든 방에 기본값 적용", "ใช้ค่าเริ่มต้นกับทุกห้อง", "Aplicar predeterminados a TODAS las habitaciones"),
    "preset_none": ("No saved default for this room yet. Set it up in Room Settings.", "இந்த அறைக்கு இன்னும் சேமிக்கப்பட்ட இயல்புநிலை இல்லை. அறை அமைப்புகளில் அமைக்கவும்.", "이 방에 저장된 기본값이 없습니다. 방 설정에서 구성하세요.", "ยังไม่มีค่าเริ่มต้นสำหรับห้องนี้ ตั้งค่าในการตั้งค่าห้อง", "Aún no hay predeterminado para esta habitación. Configúralo en Ajustes."),
    "mode_bad_name": ("Enter a valid mode name (1-40 letters, numbers, spaces or - & ' . ( ) ).", "சரியான பயன்முறை பெயரை உள்ளிடவும் (1-40 எழுத்துகள், எண்கள், இடைவெளிகள் அல்லது - & ' . ( ) ).", "유효한 모드 이름을 입력하세요 (1-40자, 숫자, 공백 또는 - & ' . ( ) ).", "ใส่ชื่อโหมดที่ถูกต้อง (1-40 ตัวอักษร ตัวเลข ช่องว่าง หรือ - & ' . ( ) )", "Introduce un nombre de modo válido (1-40 letras, números, espacios o - & ' . ( ) )."),
    "mode_dup": ("A mode with this name already exists. Choose another name.", "இந்தப் பெயரில் ஒரு பயன்முறை ஏற்கனவே உள்ளது. வேறு பெயரைத் தேர்ந்தெடுக்கவும்.", "이 이름의 모드가 이미 있습니다. 다른 이름을 선택하세요.", "มีโหมดชื่อนี้อยู่แล้ว เลือกชื่ออื่น", "Ya existe un modo con este nombre. Elige otro."),
    "mode_bad_color": ("The bulb colour is not a valid hex colour (#RRGGBB).", "விளக்கு நிறம் சரியான ஹெக்ஸ் நிறம் (#RRGGBB) அல்ல.", "전구 색상이 유효한 16진수 색상(#RRGGBB)이 아닙니다.", "สีหลอดไฟไม่ใช่สี hex ที่ถูกต้อง (#RRGGBB)", "El color de la bombilla no es un hex válido (#RRGGBB)."),
    "dev_orphan_fix": ("Devices re-homed safely", "சாதனங்கள் பாதுகாப்பாக மீளமைக்கப்பட்டன", "기기가 안전하게 재배치됨", "ย้ายอุปกรณ์กลับอย่างปลอดภัย", "Dispositivos reubicados con seguridad"),
    "geo_started": ("Arrival pre-conditioning started automatically", "வருகை முன்-சீரமைப்பு தானாகத் தொடங்கியது", "도착 사전 조절 자동 시작됨", "เริ่มการปรับสภาพล่วงหน้าอัตโนมัติ", "Preacondicionamiento de llegada iniciado automáticamente"),
    "geo_card_hdr": ("✨ AuraSync Luxury Arrival · Pre-Conditioning Active ({m} mins to home).", "✨ AuraSync ஆடம்பர வருகை · முன்-சீரமைப்பு செயலில் ({m} நிமிடங்கள் வீட்டிற்கு).", "✨ AuraSync 럭셔리 도착 · 사전 조절 활성 ({m}분 남음).", "✨ AuraSync การมาถึงสุดหรู · ปรับสภาพล่วงหน้าทำงาน ({m} นาทีถึงบ้าน)", "✨ Llegada de Lujo AuraSync · Preacondicionamiento Activo ({m} min a casa)."),
    "geo_card_sub": ("Comfort routine is running. Tap a button below to switch off just one item. Nothing else changes.", "வசதி வழக்கம் இயங்குகிறது. ஒரு பொருளை மட்டும் அணைக்க கீழே ஒரு பொத்தானைத் தட்டவும். வேறு எதுவும் மாறாது.", "편안함 루틴이 실행 중입니다. 아래 버튼으로 하나만 끌 수 있습니다. 다른 것은 바뀌지 않습니다.", "กิจวัตรสบายกำลังทำงาน แตะปุ่มด้านล่างเพื่อปิดเพียงรายการเดียว", "La rutina de confort está activa. Pulsa un botón para apagar solo un elemento."),
    "geo_off_geyser": ("🚿 Turn OFF Geyser Alone", "🚿 கீசரை மட்டும் அணை", "🚿 온수기만 끄기", "🚿 ปิดเครื่องทำน้ำอุ่นเท่านั้น", "🚿 Apagar solo el calentador"),
    "geo_off_ac": ("❄️ Turn OFF AC Alone", "❄️ ஏசியை மட்டும் அணை", "❄️ 에어컨만 끄기", "❄️ ปิดแอร์เท่านั้น", "❄️ Apagar solo el A/C"),
    "geo_off_fan": ("🌀 Turn OFF Fan Alone", "🌀 மின்விசிறியை மட்டும் அணை", "🌀 선풍기만 끄기", "🌀 ปิดพัดลมเท่านั้น", "🌀 Apagar solo el ventilador"),
    "geo_on_geyser": ("🚿 Turn Geyser back ON", "🚿 கீசரை மீண்டும் இயக்கு", "🚿 온수기 다시 켜기", "🚿 เปิดเครื่องทำน้ำอุ่นอีกครั้ง", "🚿 Encender el calentador de nuevo"),
    "geo_on_ac": ("❄️ Turn AC back ON", "❄️ ஏசியை மீண்டும் இயக்கு", "❄️ 에어컨 다시 켜기", "❄️ เปิดแอร์อีกครั้ง", "❄️ Encender el A/C de nuevo"),
    "geo_on_fan": ("🌀 Turn Fan back ON", "🌀 மின்விசிறியை மீண்டும் இயக்கு", "🌀 선풍기 다시 켜기", "🌀 เปิดพัดลมอีกครั้ง", "🌀 Encender el ventilador de nuevo"),
    "geo_cancel_all": ("🛑 Cancel All & Return to Standby", "🛑 அனைத்தையும் ரத்துசெய்து தெரியாமல் திரும்பு", "🛑 모두 취소 및 대기로 복귀", "🛑 ยกเลิกทั้งหมด & กลับสแตนด์บาย", "🛑 Cancelar todo y volver a espera"),
    "geo_off_alone": ("{n} switched off. Everything else keeps running.", "{n} அணைக்கப்பட்டது. மற்றவை தொடர்ந்து இயங்கும்.", "{n} 꺼짐. 나머지는 계속 실행됩니다.", "{n} ปิดแล้ว ส่วนอื่นยังทำงาน", "{n} apagado. Lo demás sigue funcionando."),
    "geo_on_again": ("{n} switched back on.", "{n} மீண்டும் இயக்கப்பட்டது.", "{n} 다시 켜짐.", "{n} เปิดอีกครั้งแล้ว", "{n} encendido de nuevo."),
    "geo_cancelled": ("Arrival routine cancelled. Home is on standby.", "வருகை வழக்கம் ரத்து செய்யப்பட்டது. வீடு தெரியாமல் உள்ளது.", "도착 루틴 취소됨. 집이 대기 상태입니다.", "ยกเลิกกิจวัตรการมาถึง บ้านอยู่ในสแตนด์บาย", "Rutina de llegada cancelada. La casa está en espera."),
    "geo_standby": ("Arrival routine cancelled. Everything is on standby.", "வருகை வழக்கம் ரத்து. அனைத்தும் தெரியாமல் உள்ளது.", "도착 루틴 취소. 모두 대기 중.", "ยกเลิกกิจวัตรการมาถึง ทุกอย่างสแตนด์บาย", "Rutina de llegada cancelada. Todo en espera."),
    "geo_restart": ("↺ Start the arrival routine again", "↺ வருகை வழக்கத்தை மீண்டும் தொடங்கு", "↺ 도착 루틴 다시 시작", "↺ เริ่มกิจวัตรการมาถึงอีกครั้ง", "↺ Iniciar la rutina de llegada de nuevo"),
    "geo_auto_toggle": ("Autonomous Pre-Conditioning (Zero-Touch)", "தன்னாட்சி முன்-சீரமைப்பு (பூஜ்ய-தொடுதல்)", "자율 사전 조절 (제로 터치)", "การปรับสภาพล่วงหน้าอัตโนมัติ (ไม่ต้องแตะ)", "Preacondicionamiento Autónomo (Cero Toques)"),
    "geo_auto_hint": ("ON: when you are 5 km / 15 mins away AuraSync warms the bath, cools the bedroom and starts the fan by itself. OFF: it asks you first.", "ON: நீங்கள் 5 கிமீ / 15 நிமிடங்கள் தொலைவில் இருக்கும்போது AuraSync குளியலறையை சூடாக்கி, படுக்கையறையை குளிர்வித்து, விசிறியைத் தானாகத் தொடங்கும். OFF: முதலில் கேட்கும்.", "ON: 5km / 15분 거리일 때 AuraSync가 욕조를 데우고 침실을 식히고 선풍기를 시작합니다. OFF: 먼저 물어봅니다.", "ON: เมื่ออยู่ห่าง 5 กม. / 15 นาที AuraSync จะอุ่นอ่าง ลดอุณหภูมิห้องนอน และเปิดพัดลมเอง OFF: จะถามก่อน", "ON: a 5 km / 15 min AuraSync calienta el baño, enfría el dormitorio y enciende el ventilador. OFF: pregunta primero."),
    "geo_idle_status": ("Home appliances (live status)", "வீட்டு உபகரணங்கள் (நேரடி நிலை)", "가전 기기 (실시간 상태)", "เครื่องใช้ในบ้าน (สถานะสด)", "Electrodomésticos (estado en vivo)"),
    "geo_sim": ("🔧 Trip simulator (try it: slide the distance)", "🔧 பயண சிமுலேட்டர் (முயற்சி: தூரத்தை நகர்த்து)", "🔧 이동 시뮬레이터 (거리 조절)", "🔧 จำลองการเดินทาง (ลองเลื่อนระยะทาง)", "🔧 Simulador de viaje (prueba a deslizar la distancia)"),
    "ui_zen": ("🌿 Zen Mode", "🌿 ஜென் பயன்முறை", "🌿 젠 모드", "🌿 โหมดเซน", "🌿 Modo Zen"),
    "ui_pro": ("🎛️ Pro Studio", "🎛️ ப்ரோ ஸ்டுடியோ", "🎛️ 프로 스튜디오", "🎛️ โปรสตูดิโอ", "🎛️ Pro Studio"),
    "zen_relax": ("Relax & Unwind", "நிதானமாக & தளர்வாக", "휴식 & 이완", "ผ่อนคลาย & คลายเครียด", "Relájate y desconecta"),
    "zen_focus": ("Deep Focus", "ஆழமான கவனம்", "깊은 집중", "สมาธิลึก", "Enfoque profundo"),
    "zen_sleep": ("Sleep Preparation", "உறக்கத் தயாரிப்பு", "수면 준비", "เตรียมตัวนอน", "Preparación para dormir"),
    "zen_away": ("Away Mode", "வெளியே பயன்முறை", "외출 모드", "โหมดออกไปข้างนอก", "Modo Ausente"),
    "zen_home": ("I'm Home Now", "நான் இப்போது வீட்டில்", "지금 집에 있음", "ฉันถึงบ้านแล้ว", "Ya estoy en casa"),
    "zen_quick": ("One touch comfort", "ஒரு தொடுதலில் வசதி", "원터치 편안함", "สะดวกสบายหนึ่งสัมผัส", "Comodidad con un toque"),
    "zen_comfort": ("Comfort {c}°C", "சுகமான நிலை {c}°C", "쾌적 {c}°C", "สบาย {c}°C", "Confort {c}°C"),
    "zen_lights_off": ("Lights off", "விளக்குகள் அணைக்கப்பட்டுள்ளன", "조명 꺼짐", "ไฟปิด", "Luces apagadas"),
    "zen_auto": ("Let AuraSync adjust things for me (wearable)", "AuraSync எனக்காக விஷயங்களைச் சரிசெய்யட்டும் (அணிகலன்)", "AuraSync가 조정하게 하기 (웨어러블)", "ให้ AuraSync ปรับให้ (อุปกรณ์สวมใส่)", "Deja que AuraSync ajuste por mí (wearable)"),
    "zen_well": ("💚 You seem {s}. AuraSync keeps the comfort adjusted for you.", "💚 நீங்கள் {s} ஆகத் தெரிகிறது. AuraSync உங்களுக்கான வசதியைச் சரிசெய்கிறது.", "💚 당신은 {s} 상태입니다. AuraSync가 쾌적함을 조정합니다.", "💚 คุณดู {s} AuraSync ปรับความสบายให้คุณ", "💚 Pareces {s}. AuraSync ajusta el confort por ti."),
    "zen_hidden": ("Technical details are hidden in Zen Mode. Switch to Pro Studio for graphs, mixers and logs.", "ஜென் பயன்முறையில் தொழில்நுட்ப விவரங்கள் மறைக்கப்பட்டுள்ளன. வரைபடங்கள், மிக்சர்கள் மற்றும் பதிவுகளுக்கு ப்ரோ ஸ்டுடியோவுக்கு மாறவும்.", "젠 모드에서는 기술 세부정보가 숨겨집니다. 그래프, 믹서, 로그는 프로 스튜디오에서 확인하세요.", "รายละเอียดทางเทคนิคซ่อนอยู่ในโหมดเซน สลับไปโปรสตูดิโอสำหรับกราฟ มิกเซอร์ และบันทึก", "Los detalles técnicos están ocultos en Modo Zen. Cambia a Pro Studio para gráficos, mezcladores y registros."),
    "watch_title": ("⌚ Lock Screen · Live Activity", "⌚ பூட்டுத் திரை · நேரடி செயல்பாடு", "⌚ 잠금 화면 · 실시간 활동", "⌚ หน้าจอล็อก · กิจกรรมสด", "⌚ Pantalla de bloqueo · Actividad en vivo"),
    "watch_cancel": ("❌ Cancel Arrival Pre-Conditioning", "❌ வருகை முன்-சீரமைப்பை ரத்துசெய்", "❌ 도착 사전 조절 취소", "❌ ยกเลิกการปรับสภาพล่วงหน้าการมาถึง", "❌ Cancelar preacondicionamiento de llegada"),
    "watch_home": ("🏠 At home", "🏠 வீட்டில்", "🏠 집", "🏠 ที่บ้าน", "🏠 En casa"),
    "watch_standby": ("Standing by", "காத்திருக்கிறது", "대기 중", "สแตนด์บาย", "En espera"),
    "watch_preheat": ("♨️ Geyser Pre-heating ({v}°C)", "♨️ கீசர் முன்-சூடாக்கம் ({v}°C)", "♨️ 온수기 예열 ({v}°C)", "♨️ อุ่นเครื่องทำน้ำอุ่น ({v}°C)", "♨️ Precalentando calentador ({v}°C)"),
    "watch_geyser_off": ("♨️ Geyser off", "♨️ கீசர் அணைக்கப்பட்டது", "♨️ 온수기 꺼짐", "♨️ เครื่องทำน้ำอุ่นปิด", "♨️ Calentador apagado"),
    "watch_ac": ("❄️ AC {v}°C", "❄️ ஏசி {v}°C", "❄️ 에어컨 {v}°C", "❄️ แอร์ {v}°C", "❄️ A/C {v}°C"),
    "watch_ac_off": ("❄️ AC off", "❄️ ஏசி அணைக்கப்பட்டது", "❄️ 에어컨 꺼짐", "❄️ แอร์ปิด", "❄️ A/C apagado"),
    "watch_eta": ("🚗 {m} mins to Home", "🚗 வீட்டிற்கு {m} நிமிடங்கள்", "🚗 집까지 {m}분", "🚗 อีก {m} นาทีถึงบ้าน", "🚗 {m} min a casa"),
    "dial_title": ("🔘 Smart Rotary Dial", "🔘 ஸ்மார்ட் ரோட்டரி டயல்", "🔘 스마트 로터리 다이얼", "🔘 สมาร์ทโรตารีไดอัล", "🔘 Dial Giratorio Inteligente"),
    "dial_tap": ("🔘 Dial Tap", "🔘 டயல் தட்டு", "🔘 다이얼 탭", "🔘 แตะไดอัล", "🔘 Tocar dial"),
    "dial_cw": ("🔄 Turn ↻ (brighter · +1°C)", "🔄 திருப்பு ↻ (பிரகாசமான · +1°C)", "🔄 회전 ↻ (밝게 · +1°C)", "🔄 หมุน ↻ (สว่างขึ้น · +1°C)", "🔄 Girar ↻ (más brillo · +1°C)"),
    "dial_ccw": ("🔄 Turn ↺ (dimmer · −1°C)", "🔄 திருப்பு ↺ (மங்கலான · −1°C)", "🔄 회전 ↺ (어둡게 · −1°C)", "🔄 หมุน ↺ (หรี่ลง · −1°C)", "🔄 Girar ↺ (más tenue · −1°C)"),
    "dial_hint": ("Tap = next atmosphere for this room · Turn = brightness and AC target.", "தட்டு = இந்த அறைக்கான அடுத்த சூழல் · திருப்பு = பிரகாசம் மற்றும் ஏசி இலக்கு.", "탭 = 이 방의 다음 분위기 · 회전 = 밝기 및 에어컨 목표.", "แตะ = บรรยากาศถัดไปของห้องนี้ · หมุน = ความสว่างและเป้าหมายแอร์", "Tocar = siguiente ambiente · Girar = brillo y objetivo de A/C."),
    "dial_scope": ("Dial controls", "டயல் கட்டுப்பாடுகள்", "다이얼 제어", "การควบคุมไดอัล", "Controles del dial"),
    "dial_lights": ("Lights", "விளக்குகள்", "조명", "ไฟ", "Luces"),
    "dial_climate": ("Climate", "காலநிலை", "기후", "สภาพอากาศ", "Clima"),
    "dial_both": ("Both", "இரண்டும்", "둘 다", "ทั้งสอง", "Ambos"),
    "voice_title": ("🎙️ Just tell AuraSync", "🎙️ AuraSync-ஐ சொல்லுங்கள்", "🎙️ AuraSync에게 말하세요", "🎙️ บอก AuraSync", "🎙️ Dile a AuraSync"),
    "voice_ph": ("Try: I'm tired · Starting work · Family movie time", "முயற்சி: நான் சோர்வாக இருக்கிறேன் · வேலை தொடங்குகிறது · குடும்ப திரைப்பட நேரம்", "시도: 피곤해 · 작업 시작 · 가족 영화 시간", "ลอง: ฉันเหนื่อย · เริ่มงาน · เวลาหนังครอบครัว", "Prueba: Estoy cansado · Empiezo a trabajar · Cine familiar"),
    "voice_send": ("Send", "அனுப்பு", "보내기", "ส่ง", "Enviar"),
    "voice_tired": ("I'm tired", "நான் சோர்வாக இருக்கிறேன்", "피곤해", "ฉันเหนื่อย", "Estoy cansado"),
    "voice_work": ("Starting work", "வேலை தொடங்குகிறது", "작업 시작", "เริ่มงาน", "Empiezo a trabajar"),
    "voice_movie": ("Family movie time", "குடும்ப திரைப்பட நேரம்", "가족 영화 시간", "เวลาหนังครอบครัว", "Cine familiar"),
    "voice_unknown": ("I didn't catch that. Try \"I'm tired\", \"Starting work\" or \"Family movie time\".", "புரியவில்லை. \"நான் சோர்வாக இருக்கிறேன்\", \"வேலை தொடங்குகிறது\" அல்லது \"குடும்ப திரைப்பட நேரம்\" என்று முயற்சிக்கவும்.", "이해하지 못했습니다. \"피곤해\", \"작업 시작\" 또는 \"가족 영화 시간\"을 시도하세요.", "ไม่เข้าใจ ลอง \"ฉันเหนื่อย\", \"เริ่มงาน\" หรือ \"เวลาหนังครอบครัว\"", "No lo entendí. Prueba \"Estoy cansado\", \"Empiezo a trabajar\" o \"Cine familiar\"."),
    "guest_toggle": ("Guest Mode", "விருந்தினர் பயன்முறை", "게스트 모드", "โหมดแขก", "Modo Invitado"),
    "guest_hint": ("ON: automatic shutdowns and wearable changes pause; the home stays welcoming for visitors.", "ON: தானியங்கி அணைப்புகள் மற்றும் அணிகலன் மாற்றங்கள் இடைநிறுத்தப்படும்; வீடு வருகையாளர்களுக்கு வரவேற்பாக இருக்கும்.", "ON: 자동 종료 및 웨어러블 변경이 일시중지됩니다. 집은 방문객을 환영합니다.", "ON: การปิดอัตโนมัติและการเปลี่ยนแปลงจากอุปกรณ์สวมใส่หยุดชั่วคราว", "ON: las desconexiones automáticas y cambios del wearable se pausan; la casa sigue acogedora."),
    "guest_on": ("Guest Mode is ON: the home keeps a welcoming, steady atmosphere.", "விருந்தினர் பயன்முறை ON: வீடு வரவேற்பான நிலையான சூழலை வைத்திருக்கிறது.", "게스트 모드 ON: 집이 환영하는 안정된 분위기를 유지합니다.", "โหมดแขก ON: บ้านรักษาบรรยากาศที่ต้อนรับ", "Modo Invitado ON: la casa mantiene un ambiente acogedor y estable."),
    "occ_label": ("Who is in this shared room?", "இந்த பகிரப்பட்ட அறையில் யார் இருக்கிறார்கள்?", "이 공유 방에 누가 있나요?", "ใครอยู่ในห้องร่วมนี้?", "¿Quién está en esta habitación compartida?"),
    "occ_1": ("1 person", "1 நபர்", "1명", "1 คน", "1 persona"),
    "occ_2": ("2+ family members", "2+ குடும்ப உறுப்பினர்கள்", "가족 2명 이상", "สมาชิกครอบครัว 2 คนขึ้นไป", "2+ miembros de la familia"),
    "occ_lock": ("Family lock: one person's body signals cannot change the shared room. Atmosphere is held at Neutral Family Ambience (warm 24°C).", "குடும்பப் பூட்டு: ஒரு நபரின் உடல் சமிக்ஞைகள் பகிரப்பட்ட அறையை மாற்ற முடியாது. சூழல் நடுநிலை குடும்ப சூழலில் (சூடான 24°C) வைக்கப்படுகிறது.", "가족 잠금: 한 사람의 신체 신호가 공유 방을 바꿀 수 없습니다. 중립 가족 분위기(따뜻한 24°C)로 유지됩니다.", "ล็อกครอบครัว: สัญญาณร่างกายของคนหนึ่งไม่สามารถเปลี่ยนห้องร่วมได้ บรรยากาศคงอยู่ที่ความเป็นกลางครอบครัว (24°C)", "Bloqueo familiar: las señales corporales de una persona no cambian la habitación compartida. Ambiente neutral (24°C)."),
    "persona_personal": ("Personal sanctuary", "தனிப்பட்ட புகலிடம்", "개인 성소", "สถานที่ส่วนตัว", "Santuario personal"),
    "persona_shared": ("Shared family zone", "பகிரப்பட்ட குடும்ப மண்டலம்", "공유 가족 구역", "โซนครอบครัวร่วม", "Zona familiar compartida"),
    "persona_pick": ("Room type", "அறை வகை", "방 유형", "ประเภทห้อง", "Tipo de habitación"),
    "matter_btn": ("📷 Scan Matter QR / Enter Pairing Code", "📷 Matter QR ஐ ஸ்கேன் செய் / இணைப்புக் குறியீட்டை உள்ளிடு", "📷 Matter QR 스캔 / 페어링 코드 입력", "📷 สแกน Matter QR / ใส่รหัสจับคู่", "📷 Escanear QR Matter / Introducir código"),
    "matter_title": ("Plug & Play setup (Matter 1.3)", "பிளக் & பிளே அமைப்பு (Matter 1.3)", "플러그 앤 플레이 설정 (Matter 1.3)", "ตั้งค่า Plug & Play (Matter 1.3)", "Configuración Plug & Play (Matter 1.3)"),
    "matter_help": ("Scan the QR on the device, or type the code printed under it (for example MT:Y.K10000000000).", "சாதனத்தின் QR ஐ ஸ்கேன் செய்யவும் அல்லது அதன் கீழே அச்சிடப்பட்ட குறியீட்டை உள்ளிடவும் (எடுத்துக்காட்டாக MT:Y.K10000000000).", "기기의 QR을 스캔하거나 아래에 인쇄된 코드를 입력하세요 (예: MT:Y.K10000000000).", "สแกน QR บนอุปกรณ์ หรือพิมพ์รหัสที่พิมพ์ด้านล่าง (เช่น MT:Y.K10000000000)", "Escanea el QR del dispositivo o escribe el código impreso debajo (ejemplo MT:Y.K10000000000)."),
    "matter_code": ("Pairing code", "இணைப்புக் குறியீடு", "페어링 코드", "รหัสจับคู่", "Código de emparejamiento"),
    "matter_room": ("Place it in", "இங்கே வைக்கவும்", "위치할 방", "วางไว้ใน", "Colocarlo en"),
    "matter_pair": ("🔗 Pair now", "🔗 இப்போது இணை", "🔗 지금 페어링", "🔗 จับคู่เลย", "🔗 Emparejar ahora"),
    "matter_demo": ("⚡ Auto-Pair Demo Device in 5s", "⚡ டெமோ சாதனத்தை 5 வினாடிகளில் தானாக இணை", "⚡ 5초 만에 데모 기기 자동 페어링", "⚡ จับคู่อุปกรณ์สาธิตอัตโนมัติใน 5 วินาที", "⚡ Emparejar dispositivo demo en 5 s"),
    "matter_bad": ("That code does not look right. Use a Matter code like MT:Y.K10000000000 or an 11-digit code.", "அந்தக் குறியீடு சரியாகத் தெரியவில்லை. MT:Y.K10000000000 போன்ற Matter குறியீட்டைப் பயன்படுத்தவும் அல்லது 11 இலக்கக் குறியீட்டைப் பயன்படுத்தவும்.", "코드가 올바르지 않습니다. MT:Y.K10000000000 같은 Matter 코드나 11자리 코드를 사용하세요.", "รหัสไม่ถูกต้อง ใช้รหัส Matter เช่น MT:Y.K10000000000 หรือรหัส 11 หลัก", "Ese código no parece correcto. Usa un código Matter como MT:Y.K10000000000 o un código de 11 dígitos."),
    "matter_ok": ("Connected: {n} in {r}", "இணைக்கப்பட்டது: {n} இல் {r}", "연결됨: {n} ({r})", "เชื่อมต่อแล้ว: {n} ใน {r}", "Conectado: {n} en {r}"),
    "matter_s1": ("Looking for the device nearby…", "அருகிலுள்ள சாதனத்தைத் தேடுகிறது…", "근처 기기를 찾는 중…", "กำลังค้นหาอุปกรณ์ใกล้เคียง…", "Buscando el dispositivo cercano…"),
    "matter_s2": ("Securing the connection…", "இணைப்பைப் பாதுகாக்கிறது…", "연결 보안 중…", "กำลังรักษาความปลอดภัยการเชื่อมต่อ…", "Asegurando la conexión…"),
    "matter_s3": ("Joining your home network (Thread / Wi-Fi)…", "உங்கள் வீட்டு நெட்வொர்க்கில் சேருகிறது (Thread / Wi-Fi)…", "홈 네트워크 참여 중 (Thread / Wi-Fi)…", "กำลังเข้าร่วมเครือข่ายบ้าน (Thread / Wi-Fi)…", "Uniéndose a tu red doméstica (Thread / Wi-Fi)…"),
    "matter_s4": ("Identifying the hardware…", "வன்பொருளைக் கண்டறிகிறது…", "하드웨어 식별 중…", "กำลังระบุฮาร์ดแวร์…", "Identificando el hardware…"),
    "matter_s5": ("Binding it to the room…", "அதை அறையுடன் இணைக்கிறது…", "방에 바인딩 중…", "กำลังผูกกับห้อง…", "Vinculándolo a la habitación…"),
    "adv_conn": ("⚙ Advanced manual connection (IP / token, legacy)", "⚙ மேம்பட்ட கைமுறை இணைப்பு (IP / டோக்கன், லெகசி)", "⚙ 고급 수동 연결 (IP / 토큰, 레거시)", "⚙ การเชื่อมต่อด้วยตนเองขั้นสูง (IP / โทเค็น, ดั้งเดิม)", "⚙ Conexión manual avanzada (IP / token, heredado)"),
    "simple_dev": ("Devices", "சாதனங்கள்", "기기", "อุปกรณ์", "Dispositivos"),
    "pro_only": ("Pro Studio", "ப்ரோ ஸ்டுடியோ", "프로 스튜디오", "โปรสตูดิโอ", "Pro Studio"),
    "i18n_wait": ("🌐 Translating AuraSync into your language (first time only)…", "🌐 AuraSync ஐ உங்கள் மொழிக்கு மொழிபெயர்க்கிறது (முதல் முறை மட்டும்)…", "🌐 AuraSync를 귀하의 언어로 번역 중 (첫 번째만)…", "🌐 กำลังแปล AuraSync เป็นภาษาของคุณ (ครั้งแรกเท่านั้น)…", "🌐 Traduciendo AuraSync a tu idioma (solo la primera vez)…"),
    "i18n_missing": ("To show every word in your language please run: pip install deep-translator", "உங்கள் மொழியில் ஒவ்வொரு வார்த்தையையும் காட்ட தயவுசெய்து இயக்கவும்: pip install deep-translator", "모든 단어를 귀하의 언어로 표시하려면 실행하세요: pip install deep-translator", "เพื่อแสดงทุกคำในภาษาของคุณโปรดรัน: pip install deep-translator", "Para mostrar cada palabra en tu idioma ejecuta: pip install deep-translator"),
    "chat_you": ("You", "நீங்கள்", "당신", "คุณ", "Tú"),
    "geo_active": ("Pre-conditioning active", "முன்-சீரமைப்பு செயலில்", "사전 조절 활성", "การปรับสภาพล่วงหน้าทำงาน", "Preacondicionamiento activo"),
    "geo_standby_zone": ("Standby", "தெரியாமல்", "대기", "สแตนด์บาย", "En espera"),
    "chat_offer_sleep": ("Would you like me to dim the lights and switch the home to Wind-Down Sleep?", "விளக்குகளை மங்கலாக்கி வீட்டை விண்ட்-டவுன் தூக்கத்திற்கு மாற்றவா?", "조명을 어둡게 하고 집을 휴식 수면으로 전환할까요?", "ต้องการให้ฉันหรี่ไฟและเปลี่ยนบ้านเป็นโหมดพักผ่อนนอนหลับหรือไม่?", "¿Quieres que atenúe las luces y ponga la casa en modo Sueño?"),
    "chat_offer_calm": ("Want me to soften the lights and play calm sounds while we talk?", "நாம் பேசும்போது விளக்குகளை மென்மையாக்கி அமைதியான ஒலிகளை இயக்கவா?", "대화하는 동안 조명을 부드럽게 하고 차분한 소리를 재생할까요?", "ต้องการให้ฉันลดแสงและเล่นเสียงสงบขณะเราคุยกันหรือไม่?", "¿Quieres que suavice las luces y ponga sonidos relajantes mientras hablamos?"),
    "chat_done_sleep": ("Done. The lights are low and the home is in Wind-Down Sleep. Let your shoulders drop.", "முடிந்தது. விளக்குகள் குறைவாக உள்ளன, வீடு விண்ட்-டவுன் தூக்கத்தில் உள்ளது. தோள்களைத் தளர்த்துங்கள்.", "완료. 조명이 낮고 집이 휴식 수면에 있습니다. 어깨를 내려놓으세요.", "เรียบร้อย ไฟสลัวและบ้านอยู่ในโหมดพักผ่อนนอนหลับ ผ่อนคลายไหล่", "Hecho. Las luces están bajas y la casa en modo Sueño. Relaja los hombros."),
    "chat_done_calm": ("Done. Soft light and calm sound are on. Breathe out slowly with me.", "முடிந்தது. மென்மையான ஒளி மற்றும் அமைதியான ஒலி இயக்கப்பட்டுள்ளன. என்னுடன் மெதுவாக மூச்சை வெளியேற்றுங்கள்.", "완료. 부드러운 조명과 차분한 소리가 켜졌습니다. 천천히 숨을 내쉬세요.", "เรียบร้อย ไฟนุ่มและเสียงสงบเปิดแล้ว หายใจออกช้า ๆ กับฉัน", "Hecho. Luz suave y sonido relajante activos. Respira lento conmigo."),
    "chat_declined": ("Okay, no pressure. I'm still here.", "சரி, அழுத்தம் இல்லை. நான் இன்னும் இங்கே இருக்கிறேன்.", "알겠습니다. 부담 갖지 마세요. 저는 여기 있습니다.", "โอเค ไม่กดดัน ฉันยังอยู่ตรงนี้", "Vale, sin presión. Sigo aquí."),
}

# Voice automation / cloud IoT / microphone strings: (English, Tamil). Other languages are translated live by tr().
AUTO_T = {
    "auto_links_title": ("Voice Automation Links", "குரல் தானியக்க இணைப்புகள்"),
    "auto_locked": ("Enter your AuraSync token to reveal your private links.", "உங்கள் தனிப்பட்ட இணைப்புகளைக் காண AuraSync டோக்கனை உள்ளிடவும்."),
    "auto_token": ("AuraSync token", "AuraSync டோக்கன்"),
    "auto_unlock": ("Unlock", "திற"),
    "auto_lock": ("Lock", "பூட்டு"),
    "auto_bad_token": ("That token is not correct.", "அந்த டோக்கன் சரியல்ல."),
    "auto_wait": ("Too many attempts. Please wait a minute.", "அதிக முயற்சிகள். ஒரு நிமிடம் காத்திருக்கவும்."),
    "auto_no_secret": ("Add AURASYNC_TOKEN to .streamlit/secrets.toml (or the Secrets box on Streamlit Cloud) to switch on the link webhook and these shortcut links.",
                       "இணைப்பு வெப்ஹூக்கையும் இந்த ஷார்ட்கட் இணைப்புகளையும் இயக்க .streamlit/secrets.toml (அல்லது Streamlit Cloud Secrets) இல் AURASYNC_TOKEN ஐச் சேர்க்கவும்."),
    "auto_base": ("Your app address (https://your-app.streamlit.app)", "உங்கள் ஆப் முகவரி (https://your-app.streamlit.app)"),
    "auto_ios": ("iPhone · Siri Shortcuts", "ஐபோன் · Siri Shortcuts"),
    "auto_android": ("Android · Google Assistant", "ஆண்ட்ராய்டு · Google Assistant"),
    "auto_ios_help": ("Shortcuts app → + New Shortcut → add “Open URLs” and paste a link below → Add to Siri and record your phrase. “Open URLs” opens AuraSync, applies the mood, sends your cloud triggers and syncs the app. For lights only (app stays closed) use a Direct cloud trigger with “Get Contents of URL” and Method GET.", ""),
    "auto_android_help": ("HTTP Shortcuts app → + → choose “Browser Shortcut” and paste a link below (opens AuraSync and applies the mood). For lights only, create a Regular shortcut with Method GET and paste a Direct cloud trigger. Add it to your home screen, or say “Hey Google, open <shortcut name>”. Steps can differ a little between app versions.", ""),
    "auto_why": ("Why two kinds of link? Streamlit only runs your app when a browser opens it, so a plain GET fetch of the app address does nothing. App links need “open”; Direct cloud triggers work with a plain GET.", ""),
    "auto_say": ("Say", "சொல்லுங்கள்"),
    "auto_direct": ("Direct cloud triggers (work without opening the app)", "நேரடி கிளவுட் தூண்டுதல்கள் (ஆப்பைத் திறக்காமல் வேலை செய்யும்)"),
    "auto_direct_none": ("No cloud trigger is configured yet. Add VOICEMONKEY_TOKEN or IOT_WEBHOOK_URL to your secrets.", "கிளவுட் தூண்டுதல் இன்னும் அமைக்கப்படவில்லை. VOICEMONKEY_TOKEN அல்லது IOT_WEBHOOK_URL ஐ secrets இல் சேர்க்கவும்."),
    "auto_test": ("Send test trigger", "சோதனை தூண்டுதலை அனுப்பு"),
    "auto_test_mode": ("Mode to test", "சோதிக்க வேண்டிய முறை"),
    "auto_iot_title": ("Cloud IoT settings (this session only)", "கிளவுட் IoT அமைப்புகள் (இந்த அமர்வுக்கு மட்டும்)"),
    "auto_iot_hint": ("Saved permanently in Secrets. Values typed here are kept for this session only. Alexa: Voice Monkey. WiZ has no public cloud API, so use an Alexa routine, Home Assistant Cloud or IFTTT webhook that controls your WiZ lights.", ""),
    "auto_tpl": ("Webhook URL ({mode} is replaced)", "வெப்ஹூக் URL ({mode} மாற்றப்படும்)"),
    "auto_vm": ("Voice Monkey token", "Voice Monkey டோக்கன்"),
    "auto_apply": ("Apply", "செயல்படுத்து"),
    "auto_clear": ("Clear", "அழி"),
    "auto_applied": ("Cloud settings applied for this session.", "இந்த அமர்வுக்கு கிளவுட் அமைப்புகள் பயன்படுத்தப்பட்டன."),
    "auto_ok_hook": ("Mode applied from your link: {m}", "உங்கள் இணைப்பிலிருந்து முறை பயன்படுத்தப்பட்டது: {m}"),
    "auto_bad_mode": ("That link has an unknown mode.", "அந்த இணைப்பில் தெரியாத முறை உள்ளது."),
    "auto_denied": ("A link was blocked: wrong or missing token.", "ஒரு இணைப்பு தடுக்கப்பட்டது: டோக்கன் தவறு அல்லது இல்லை."),
    "iot_sent": ("☁️ Cloud triggers sent: {ok} of {n}", "☁️ கிளவுட் தூண்டுதல்கள் அனுப்பப்பட்டன: {n} இல் {ok}"),
    "iot_blocked": ("blocked (needs a public https address)", "தடுக்கப்பட்டது (பொது https முகவரி தேவை)"),
    "mic_thinking": ("Thinking…",),
    "mic_speaking": ("Speaking…",),
    "mic_notts": ("This browser cannot speak replies aloud, so the reply is shown as text.",),
    "mic_mute": ("Voice replies: on",),
    "mic_unmute": ("Voice replies: off",),
    "src_ble": ("Bluetooth band / ring",),
    "ble_title": ("Connect a heart-rate wearable",),
    "ble_sub": ("Smart bands, watches, rings and chest straps that share heart rate over standard Bluetooth connect straight to AuraSync.",),
    "ble_connect": ("Connect band / ring",),
    "ble_all": ("Show all Bluetooth devices",),
    "ble_disc": ("Disconnect",),
    "ble_idle": ("Not connected",),
    "ble_connecting": ("Connecting…",),
    "ble_connected": ("Connected",),
    "ble_reconnecting": ("Connection lost, reconnecting…",),
    "ble_stale": ("Connected, waiting for a heart-rate reading…",),
    "ble_disconnected": ("Disconnected. Tap Connect to pair again.",),
    "ble_unsupported": ("This browser has no Web Bluetooth. Use Chrome on Android or desktop, or the free Bluefy browser on iPhone and iPad. You can also pick Wearable API as the data source.",),
    "ble_blocked": ("Bluetooth was blocked. Allow Bluetooth for this site, or open the app directly in Chrome instead of inside another page.",),
    "ble_cancelled": ("No device was chosen.",),
    "ble_error": ("Could not connect. Switch on heart-rate broadcast on your band or ring, keep it close, then try again.",),
    "ble_note": ("Oura and Ultrahuman rings and Apple Watch do not share heart rate over open Bluetooth. For them choose Wearable API and point it at their cloud or a Shortcuts relay.",),
    "ble_live": ("Live from {n}: {hr} bpm",),
    "ble_wait": ("Waiting for the first heart-rate reading…",),
    "api_token": ("Wearable API access token (optional)",),
    "as_title": ("One-tap voice shortcuts",),
    "as_sub": ("Talk to your home from the lock screen, your watch or your car.",),
    "as_siri": ("Add to Siri",),
    "as_google": ("Add to Google Assistant",),
    "as_steps": ("Google Assistant setup in 1 minute",),
    "as_g1": ("Install the free HTTP Shortcuts app (button above).",),
    "as_g2": ("Tap + and choose Regular Shortcut. Paste your AuraSync link as the URL, method GET, and set Response handling to Open in browser.",),
    "as_g3": ("Long-press the shortcut and add it to your home screen. Then say: Hey Google, open <your shortcut name>.",),
    "as_g_link": ("Your link for the Reading mode",),
    "as_g_nolink": ("Add AURASYNC_TOKEN to your app secrets to get your private link here.",),
    "mic_title": ("Tap the mic and speak", "மைக்கைத் தட்டிப் பேசுங்கள்"),
    "mic_hint": ("Try: “Turn to reading mode”, “Activate Zen”, “Focus mode”", "முயலுங்கள்: “reading mode”, “Zen”, “Focus mode”"),
    "mic_listening": ("Listening…", "கேட்கிறேன்…"),
    "mic_heard": ("Heard", "கேட்டது"),
    "mic_sent": ("Sent to AuraSync ✓", "AuraSync க்கு அனுப்பப்பட்டது ✓"),
    "mic_denied": ("Microphone permission was denied. Allow it in your browser settings, or type your command to the ✨ Aura AI button.", "மைக்ரோஃபோன் அனுமதி மறுக்கப்பட்டது. உலாவி அமைப்புகளில் அனுமதியுங்கள் அல்லது ✨ Aura AI பொத்தானில் தட்டச்சு செய்யுங்கள்."),
    "mic_unsupported": ("This browser has no voice recognition. Type your command to the ✨ Aura AI button.", "இந்த உலாவியில் குரல் அறிதல் இல்லை. ✨ Aura AI பொத்தானில் தட்டச்சு செய்யுங்கள்."),
    "mic_nospeech": ("I didn't hear anything. Tap the mic and try again.", "எதுவும் கேட்கவில்லை. மைக்கைத் தட்டி மீண்டும் முயலுங்கள்."),
    "mic_network": ("The voice service could not be reached. Check your connection or type your command to the ✨ Aura AI button.", "குரல் சேவையை அடைய முடியவில்லை. இணைப்பைச் சரிபார்க்கவும் அல்லது ✨ Aura AI பொத்தானில் தட்டச்சு செய்யவும்."),
    "mic_nomic": ("No microphone was found.", "மைக்ரோஃபோன் கிடைக்கவில்லை."),
    "mic_nobridge": ("Couldn't reach the app. Tap the mic again, or type your command to the ✨ Aura AI button.", "ஆப்பை அடைய முடியவில்லை. மீண்டும் மைக்கைத் தட்டவும் அல்லது ✨ Aura AI பொத்தானில் தட்டச்சு செய்யுங்கள்."),
    "mic_insecure": ("The microphone only works on a secure page (https) or on localhost.", "மைக்ரோஃபோன் பாதுகாப்பான (https) பக்கத்தில் அல்லது localhost-இல் மட்டுமே வேலை செய்யும்."),
    "mic_error": ("Voice recognition had a problem. Please try again.", "குரல் அறிதலில் சிக்கல். மீண்டும் முயலுங்கள்."),
    "mic_unknown": ("I heard “{x}”, but it is not a mood I know. Try “reading”, “zen” or “focus”.", "“{x}” என்று கேட்டேன், ஆனால் அது எனக்குத் தெரிந்த முறை அல்ல. “reading”, “zen” அல்லது “focus” என்று முயலுங்கள்."),
}
for _k, _v in AUTO_T.items():
    T[_k] = tuple(x for x in _v if x) if _v[-1] == "" else _v

for _k, _v in T.items():
    if not isinstance(_v, tuple):
        T[_k] = (_v,)


CORE_KEYS = ("lang", "nav", "p1", "p2", "p3", "p4", "p5", "mode_manual", "mode_auto", "play", "stop", "welcome",
             "edit", "nudge", "plan", "do", "dont", "caution", "deep", "chat", "chat_ph", "save")
CI = {k: i for i, k in enumerate(CORE_KEYS)}

TX = {
    "Hindi (हिन्दी)": ("भाषा", "मेनू", "लाइव डैशबोर्ड", "मूड और सेटिंग्स", "अंतर्मन की आवाज़ और मार्गदर्शक", "डिवाइस फ्लीट", "सिस्टम सेटिंग्स", "मैनुअल मोड", "ऑटो मोड (वियरेबल बायोमेट्रिक सिंक)", "चलाएँ", "रोकें", "✨ फिर से स्वागत है, {n}!", "✏️ जन्म विवरण संपादित करें", "💛 हे {n}! एक प्यारा सा संकेत: एक धीमी गहरी साँस लीजिए। आज के लिए आपके करने योग्य, न करने योग्य और सावधानी वाले सुझाव तैयार हैं।", "आज की रणनीतिक कार्य योजना", "✅ क्या करें", "❌ क्या न करें", "⚠️ सावधानी", "📖 गहन व्याख्या", "अपने दिव्य कम्पास से बात करें", "अपने आंतरिक कम्पास से पूछें", "सहेजें"),
    "Arabic (العربية)": ("اللغة", "القائمة", "لوحة التحكم المباشرة", "الأجواء والإعدادات", "الصوت الداخلي والدليل", "أسطول الأجهزة", "إعدادات النظام", "الوضع اليدوي", "الوضع التلقائي (مزامنة المؤشرات الحيوية)", "تشغيل", "إيقاف", "✨ مرحبًا بعودتك، {n}!", "✏️ تعديل بيانات الميلاد", "💛 مرحبًا {n}! تذكير لطيف: خذ نفسًا عميقًا وبطيئًا. نصائح اليوم (افعل، لا تفعل، احذر) جاهزة لتبقى متزنًا.", "خطة العمل الاستراتيجية لليوم", "✅ افعل", "❌ لا تفعل", "⚠️ تنبيه", "📖 شرح معمّق", "تحدّث إلى بوصلتك الإلهية", "اسأل بوصلتك الداخلية", "حفظ"),
    "Japanese (日本語)": ("言語", "メニュー", "ライブダッシュボード", "ムードと設定", "内なる声とガイド", "デバイス一覧", "システム設定", "手動モード", "自動モード(ウェアラブル生体同期)", "再生", "停止", "✨ おかえりなさい、{n}さん!", "✏️ 出生情報を編集", "💛 {n}さん、やさしいお知らせです。ゆっくり深呼吸をひとつ。今日の「やるべきこと・避けること・注意点」を用意しました。", "今日の戦略アクションプラン", "✅ やるべきこと", "❌ 避けること", "⚠️ 注意", "📖 詳しい解説", "神聖なコンパスに話しかける", "内なるコンパスに聞いてみましょう", "保存"),
    "Chinese (中文)": ("语言", "导航", "实时仪表盘", "情境与设置", "内心声音与指引", "设备列表", "系统设置", "手动模式", "自动模式(可穿戴生物数据同步)", "播放", "停止", "✨ 欢迎回来，{n}！", "✏️ 编辑出生信息", "💛 嗨，{n}！温馨提醒：请缓慢深呼吸一次。今日的宜做、不宜做与注意事项已备好，助你保持平衡。", "今日策略行动计划", "✅ 宜做", "❌ 不宜做", "⚠️ 注意", "📖 深度解读", "与你的神圣罗盘对话", "向你的内在罗盘提问", "保存"),
    "French (Français)": ("Langue", "Navigation", "Tableau de bord en direct", "Ambiances et réglages", "Voix intérieure et guide", "Parc d'appareils", "Paramètres système", "Mode manuel", "Mode auto (synchro biométrique)", "Lecture", "Arrêt", "✨ Bon retour, {n} !", "✏️ Modifier les données de naissance", "💛 Coucou {n} ! Petit rappel amical : prenez une grande respiration lente. Vos À faire, À éviter et Précautions du jour sont prêts.", "Plan d'action stratégique du jour", "✅ À faire", "❌ À éviter", "⚠️ Prudence", "📖 Explication approfondie", "Parlez à votre Boussole Divine", "Demandez à votre Boussole Intérieure", "Enregistrer"),
    "German (Deutsch)": ("Sprache", "Navigation", "Live-Dashboard", "Stimmungen & Einstellungen", "Innere Stimme & Leitfaden", "Geräteflotte", "Systemeinstellungen", "Manueller Modus", "Automatikmodus (Wearable-Biosync)", "Abspielen", "Stopp", "✨ Willkommen zurück, {n}!", "✏️ Geburtsdaten bearbeiten", "💛 Hallo {n}! Ein freundlicher Hinweis: Atme einmal langsam und tief durch. Deine Tipps für heute (Tun, Lassen, Vorsicht) sind bereit.", "Strategischer Aktionsplan für heute", "✅ Tun", "❌ Lassen", "⚠️ Vorsicht", "📖 Ausführliche Erklärung", "Sprich mit deinem Göttlichen Kompass", "Frage deinen Inneren Kompass", "Speichern"),
    "Italian (Italiano)": ("Lingua", "Navigazione", "Dashboard in tempo reale", "Atmosfere e impostazioni", "Voce interiore e guida", "Flotta dispositivi", "Impostazioni di sistema", "Modalità manuale", "Modalità automatica (sincronizzazione biometrica)", "Riproduci", "Ferma", "✨ Bentornato, {n}!", "✏️ Modifica dati di nascita", "💛 Ciao {n}! Un promemoria gentile: fai un respiro lento e profondo. I tuoi Da fare, Da evitare e Cautela di oggi sono pronti.", "Piano d'azione strategico di oggi", "✅ Da fare", "❌ Da evitare", "⚠️ Cautela", "📖 Spiegazione approfondita", "Parla con la tua Bussola Divina", "Chiedi alla tua Bussola Interiore", "Salva"),
    "Portuguese (Português)": ("Idioma", "Navegação", "Painel ao Vivo", "Ambientes e Ajustes", "Voz Interior e Guia", "Frota de Dispositivos", "Configurações do Sistema", "Modo Manual", "Modo Automático (sincronização biométrica)", "Reproduzir", "Parar", "✨ Bem-vindo de volta, {n}!", "✏️ Editar dados de nascimento", "💛 Olá {n}! Um lembrete gentil: respire fundo e devagar. Seus Fazer, Evitar e Cuidado de hoje estão prontos.", "Plano de Ação Estratégico de Hoje", "✅ Fazer", "❌ Evitar", "⚠️ Cuidado", "📖 Explicação Detalhada", "Fale com sua Bússola Divina", "Pergunte à sua Bússola Interior", "Salvar"),
    "Russian (Русский)": ("Язык", "Навигация", "Панель в реальном времени", "Настроения и настройки", "Внутренний голос и гид", "Парк устройств", "Системные настройки", "Ручной режим", "Авто-режим (синхронизация с носимым устройством)", "Играть", "Стоп", "✨ С возвращением, {n}!", "✏️ Изменить данные рождения", "💛 Привет, {n}! Дружеское напоминание: сделайте один медленный глубокий вдох. Ваши «Делать», «Не делать» и «Осторожно» на сегодня готовы.", "Стратегический план действий на сегодня", "✅ Делать", "❌ Не делать", "⚠️ Осторожно", "📖 Подробное объяснение", "Поговорите со своим Божественным Компасом", "Спросите свой Внутренний Компас", "Сохранить"),
    "Turkish (Türkçe)": ("Dil", "Gezinme", "Canlı Panel", "Ruh Halleri ve Ayarlar", "İç Ses ve Rehber", "Cihaz Filosu", "Sistem Ayarları", "Manuel Mod", "Otomatik Mod (Giyilebilir Biyometrik Senkron)", "Oynat", "Durdur", "✨ Tekrar hoş geldin, {n}!", "✏️ Doğum bilgilerini düzenle", "💛 Merhaba {n}! Nazik bir hatırlatma: yavaşça derin bir nefes al. Bugünün Yapılacaklar, Yapılmayacaklar ve Dikkat önerileri hazır.", "Bugünün Stratejik Eylem Planı", "✅ Yapılacaklar", "❌ Yapılmayacaklar", "⚠️ Dikkat", "📖 Ayrıntılı Açıklama", "İlahi Pusulanla Konuş", "İç Pusulana Sor", "Kaydet"),
    "Dutch (Nederlands)": ("Taal", "Navigatie", "Live Dashboard", "Sferen & Instellingen", "Innerlijke Stem & Gids", "Apparatenpark", "Systeeminstellingen", "Handmatige modus", "Automodus (wearable-biosync)", "Afspelen", "Stop", "✨ Welkom terug, {n}!", "✏️ Geboortegegevens bewerken", "💛 Hoi {n}! Een vriendelijke herinnering: adem eens rustig en diep in. Je Do's, Don'ts en Let op voor vandaag staan klaar.", "Strategisch actieplan van vandaag", "✅ Doen", "❌ Niet doen", "⚠️ Let op", "📖 Uitgebreide uitleg", "Spreek met je Goddelijke Kompas", "Vraag het je Innerlijke Kompas", "Opslaan"),
    "Polish (Polski)": ("Język", "Nawigacja", "Panel na żywo", "Nastroje i ustawienia", "Głos wewnętrzny i przewodnik", "Flota urządzeń", "Ustawienia systemu", "Tryb ręczny", "Tryb automatyczny (synchronizacja biometryczna)", "Odtwórz", "Zatrzymaj", "✨ Witaj ponownie, {n}!", "✏️ Edytuj dane urodzenia", "💛 Cześć {n}! Przyjazne przypomnienie: weź jeden powolny, głęboki oddech. Twoje Rób, Nie rób i Uwaga na dziś są gotowe.", "Strategiczny plan działania na dziś", "✅ Rób", "❌ Nie rób", "⚠️ Uwaga", "📖 Szczegółowe wyjaśnienie", "Porozmawiaj ze swoim Boskim Kompasem", "Zapytaj swój Wewnętrzny Kompas", "Zapisz"),
    "Swedish (Svenska)": ("Språk", "Navigering", "Liveöversikt", "Stämningar & inställningar", "Inre röst & guide", "Enhetsflotta", "Systeminställningar", "Manuellt läge", "Autoläge (biometrisk synk)", "Spela", "Stopp", "✨ Välkommen tillbaka, {n}!", "✏️ Redigera födelseuppgifter", "💛 Hej {n}! En vänlig påminnelse: ta ett långsamt, djupt andetag. Dina Gör, Låt bli och Se upp för idag är redo.", "Dagens strategiska handlingsplan", "✅ Gör", "❌ Låt bli", "⚠️ Se upp", "📖 Fördjupad förklaring", "Tala med din Gudomliga Kompass", "Fråga din Inre Kompass", "Spara"),
    "Greek (Ελληνικά)": ("Γλώσσα", "Πλοήγηση", "Ζωντανός πίνακας", "Διαθέσεις & ρυθμίσεις", "Εσωτερική φωνή & οδηγός", "Στόλος συσκευών", "Ρυθμίσεις συστήματος", "Χειροκίνητη λειτουργία", "Αυτόματη λειτουργία (βιομετρικός συγχρονισμός)", "Αναπαραγωγή", "Διακοπή", "✨ Καλώς ήρθες ξανά, {n}!", "✏️ Επεξεργασία στοιχείων γέννησης", "💛 Γεια σου {n}! Μια φιλική υπενθύμιση: πάρε μια αργή, βαθιά ανάσα. Τα «Να κάνεις», «Να μην κάνεις» και «Προσοχή» της ημέρας είναι έτοιμα.", "Στρατηγικό πλάνο δράσης σήμερα", "✅ Να κάνεις", "❌ Να μην κάνεις", "⚠️ Προσοχή", "📖 Αναλυτική εξήγηση", "Μίλησε στη Θεϊκή σου Πυξίδα", "Ρώτησε την Εσωτερική σου Πυξίδα", "Αποθήκευση"),
    "Indonesian (Bahasa Indonesia)": ("Bahasa", "Navigasi", "Dasbor Langsung", "Suasana & Pengaturan", "Suara Batin & Panduan", "Armada Perangkat", "Pengaturan Sistem", "Mode Manual", "Mode Otomatis (Sinkron Biometrik Wearable)", "Putar", "Berhenti", "✨ Selamat datang kembali, {n}!", "✏️ Ubah data kelahiran", "💛 Hai {n}! Pengingat ramah: tarik napas dalam dan perlahan. Anjuran Lakukan, Hindari, dan Waspada hari ini sudah siap.", "Rencana Aksi Strategis Hari Ini", "✅ Lakukan", "❌ Hindari", "⚠️ Waspada", "📖 Penjelasan Mendalam", "Berbicaralah dengan Kompas Ilahi Anda", "Tanyakan pada Kompas Batin Anda", "Simpan"),
    "Vietnamese (Tiếng Việt)": ("Ngôn ngữ", "Điều hướng", "Bảng điều khiển trực tiếp", "Tâm trạng & Cài đặt", "Tiếng nói nội tâm & Hướng dẫn", "Danh sách thiết bị", "Cài đặt hệ thống", "Chế độ thủ công", "Chế độ tự động (đồng bộ sinh trắc từ thiết bị đeo)", "Phát", "Dừng", "✨ Chào mừng trở lại, {n}!", "✏️ Chỉnh sửa thông tin ngày sinh", "💛 Chào {n}! Một lời nhắc nhẹ nhàng: hãy hít một hơi thật sâu và chậm. Việc nên làm, không nên làm và lưu ý hôm nay đã sẵn sàng.", "Kế hoạch hành động chiến lược hôm nay", "✅ Nên làm", "❌ Không nên làm", "⚠️ Lưu ý", "📖 Giải thích chuyên sâu", "Trò chuyện với La bàn Thiêng liêng của bạn", "Hỏi La bàn Nội tâm của bạn", "Lưu"),
    "Malay (Bahasa Melayu)": ("Bahasa", "Navigasi", "Papan Pemuka Langsung", "Suasana & Tetapan", "Suara Dalaman & Panduan", "Armada Peranti", "Tetapan Sistem", "Mod Manual", "Mod Auto (Segerak Biometrik Wearable)", "Main", "Henti", "✨ Selamat kembali, {n}!", "✏️ Sunting butiran kelahiran", "💛 Hai {n}! Peringatan mesra: tarik nafas dalam-dalam dengan perlahan. Cadangan Buat, Elak dan Berhati-hati hari ini sudah sedia.", "Pelan Tindakan Strategik Hari Ini", "✅ Buat", "❌ Elak", "⚠️ Berhati-hati", "📖 Penjelasan Mendalam", "Bercakap dengan Kompas Ilahi Anda", "Tanya Kompas Dalaman Anda", "Simpan"),
    "Filipino (Tagalog)": ("Wika", "Nabigasyon", "Live Dashboard", "Mga Mood at Setting", "Panloob na Tinig at Gabay", "Mga Device", "Mga Setting ng Sistema", "Manual na Mode", "Auto na Mode (Biometric Sync ng Wearable)", "I-play", "Ihinto", "✨ Welcome back, {n}!", "✏️ I-edit ang Detalye ng Kapanganakan", "💛 Hi {n}! Magiliw na paalala: huminga nang malalim at mabagal. Handa na ang iyong Gawin, Iwasan, at Mag-ingat para ngayong araw.", "Estratehikong Plano ng Aksyon Ngayon", "✅ Gawin", "❌ Iwasan", "⚠️ Mag-ingat", "📖 Malalim na Paliwanag", "Makipag-usap sa Iyong Banal na Kompas", "Magtanong sa Iyong Panloob na Kompas", "I-save"),
}

# Room and mode translation dictionaries
ROOM_NAMES = {
    "Living Lounge": {
        "English": "Living Lounge", "Tamil (தமிழ்)": "லிவிங் லவுன்ஜ்", "Korean (한국어)": "거실 라운지",
        "Thai (Thai)": "เลานจ์นั่งเล่น", "Spanish (Español)": "Salón Lounge", "Hindi (हिन्दी)": "लिविंग लाउंज",
        "Arabic (العربية)": "صالة المعيشة", "Japanese (日本語)": "リビングラウンジ", "Chinese (中文)": "客厅休息区",
        "French (Français)": "Salon", "German (Deutsch)": "Wohnlounge", "Italian (Italiano)": "Salotto",
        "Portuguese (Português)": "Salão de Estar", "Russian (Русский)": "Гостиная", "Turkish (Türkçe)": "Oturma Odası",
        "Dutch (Nederlands)": "Woonkamer", "Polish (Polski)": "Salon", "Swedish (Svenska)": "Vardagsrum",
        "Greek (Ελληνικά)": "Σαλόνι", "Indonesian (Bahasa Indonesia)": "Ruang Santai",
        "Vietnamese (Tiếng Việt)": "Phòng Khách", "Malay (Bahasa Melayu)": "Ruang Tamu", "Filipino (Tagalog)": "Living Lounge"
    },
    "Master Suite": {
        "English": "Master Suite", "Tamil (தமிழ்)": "மாஸ்டர் சூட்", "Korean (한국어)": "마스터 스위트",
        "Thai (Thai)": "ห้องสวีทหลัก", "Spanish (Español)": "Suite Principal", "Hindi (हिन्दी)": "मास्टर सुइट",
        "Arabic (العربية)": "الجناح الرئيسي", "Japanese (日本語)": "マスタースイート", "Chinese (中文)": "主套房",
        "French (Français)": "Suite Parentale", "German (Deutsch)": "Master-Suite", "Italian (Italiano)": "Suite Padronale",
        "Portuguese (Português)": "Suíte Master", "Russian (Русский)": "Главная спальня", "Turkish (Türkçe)": "Ebeveyn Yatak Odası",
        "Dutch (Nederlands)": "Hoofdsuite", "Polish (Polski)": "Główna Sypialnia", "Swedish (Svenska)": "Huvudsvit",
        "Greek (Ελληνικά)": "Κύρια Σουίτα", "Indonesian (Bahasa Indonesia)": "Suite Utama",
        "Vietnamese (Tiếng Việt)": "Phòng Suite Chính", "Malay (Bahasa Melayu)": "Suite Utama", "Filipino (Tagalog)": "Master Suite"
    },
    "En-Suite Bath": {
        "English": "En-Suite Bath", "Tamil (தமிழ்)": "என்சூட் பாத்", "Korean (한국어)": "욕실",
        "Thai (Thai)": "ห้องน้ำในห้องนอน", "Spanish (Español)": "Baño En Suite", "Hindi (हिन्दी)": "अटैच्ड बाथरूम",
        "Arabic (العربية)": "حمام ملحق", "Japanese (日本語)": "バスルーム", "Chinese (中文)": "套房浴室",
        "French (Français)": "Salle de Bain", "German (Deutsch)": "En-Suite-Bad", "Italian (Italiano)": "Bagno Privato",
        "Portuguese (Português)": "Banheiro Suíte", "Russian (Русский)": "Ванная комната", "Turkish (Türkçe)": "Banyo",
        "Dutch (Nederlands)": "En-Suite Bad", "Polish (Polski)": "Łazienka", "Swedish (Svenska)": "Badrum",
        "Greek (Ελληνικά)": "Μπάνιο", "Indonesian (Bahasa Indonesia)": "Kamar Mandi Suite",
        "Vietnamese (Tiếng Việt)": "Phòng Tắm", "Malay (Bahasa Melayu)": "Bilik Mandi", "Filipino (Tagalog)": "En-Suite Bath"
    },
    "Work Studio": {
        "English": "Work Studio", "Tamil (தமிழ்)": "வேலை ஸ்டுடியோ", "Korean (한국어)": "작업실",
        "Thai (Thai)": "สตูดิโอทำงาน", "Spanish (Español)": "Estudio de Trabajo", "Hindi (हिन्दी)": "वर्क स्टूडियो",
        "Arabic (العربية)": "مكتب العمل", "Japanese (日本語)": "ワークスタジオ", "Chinese (中文)": "工作书房",
        "French (Français)": "Studio de Travail", "German (Deutsch)": "Arbeitsstudio", "Italian (Italiano)": "Studio di Lavoro",
        "Portuguese (Português)": "Estúdio de Trabalho", "Russian (Русский)": "Рабочий кабинет", "Turkish (Türkçe)": "Çalışma Stüdyosu",
        "Dutch (Nederlands)": "Werkstudio", "Polish (Polski)": "Studio Pracy", "Swedish (Svenska)": "Arbetsrum",
        "Greek (Ελληνικά)": "Στούντιο Εργασίας", "Indonesian (Bahasa Indonesia)": "Studio Kerja",
        "Vietnamese (Tiếng Việt)": "Phòng Làm Việc", "Malay (Bahasa Melayu)": "Studio Kerja", "Filipino (Tagalog)": "Work Studio"
    },
    "Kitchen": {
        "English": "Kitchen", "Tamil (தமிழ்)": "சமையலறை", "Korean (한국어)": "주방",
        "Thai (Thai)": "ห้องครัว", "Spanish (Español)": "Cocina", "Hindi (हिन्दी)": "रसोई",
        "Arabic (العربية)": "المطبخ", "Japanese (日本語)": "キッチン", "Chinese (中文)": "厨房",
        "French (Français)": "Cuisine", "German (Deutsch)": "Küche", "Italian (Italiano)": "Cucina",
        "Portuguese (Português)": "Cozinha", "Russian (Русский)": "Кухня", "Turkish (Türkçe)": "Mutfak",
        "Dutch (Nederlands)": "Keuken", "Polish (Polski)": "Kuchnia", "Swedish (Svenska)": "Kök",
        "Greek (Ελληνικά)": "Κουζίνα", "Indonesian (Bahasa Indonesia)": "Dapur",
        "Vietnamese (Tiếng Việt)": "Phòng Bếp", "Malay (Bahasa Melayu)": "Dapur", "Filipino (Tagalog)": "Kusina"
    },
    "Reading Room": {
        "English": "Reading Room", "Tamil (தமிழ்)": "படிப்பு அறை", "Korean (한국어)": "독서실",
        "Thai (Thai)": "ห้องอ่านหนังสือ", "Spanish (Español)": "Sala de Lectura", "Hindi (हिन्दी)": "वाचन कक्ष",
        "Arabic (العربية)": "غرفة القراءة", "Japanese (日本語)": "読書室", "Chinese (中文)": "阅读室",
        "French (Français)": "Salle de Lecture", "German (Deutsch)": "Leseraum", "Italian (Italiano)": "Sala Lettura",
        "Portuguese (Português)": "Sala de Leitura", "Russian (Русский)": "Читальня", "Turkish (Türkçe)": "Okuma Odası",
        "Dutch (Nederlands)": "Leeszaal", "Polish (Polski)": "Czytelnia", "Swedish (Svenska)": "Läsrum",
        "Greek (Ελληνικά)": "Αναγνωστήριο", "Indonesian (Bahasa Indonesia)": "Ruang Baca",
        "Vietnamese (Tiếng Việt)": "Phòng Đọc Sách", "Malay (Bahasa Melayu)": "Bilik Bacaan", "Filipino (Tagalog)": "Reading Room"
    },
    "Dining Area": {
        "English": "Dining Area", "Tamil (தமிழ்)": "உணவு அறை", "Korean (한국어)": "식사 공간",
        "Thai (Thai)": "พื้นที่รับประทานอาหาร", "Spanish (Español)": "Comedor", "Hindi (हिन्दी)": "भोजन क्षेत्र",
        "Arabic (العربية)": "منطقة تناول الطعام", "Japanese (日本語)": "ダイニング", "Chinese (中文)": "用餐区",
        "French (Français)": "Salle à Manger", "German (Deutsch)": "Essbereich", "Italian (Italiano)": "Zona Pranzo",
        "Portuguese (Português)": "Área de Jantar", "Russian (Русский)": "Столовая", "Turkish (Türkçe)": "Yemek Alanı",
        "Dutch (Nederlands)": "Eetruimte", "Polish (Polski)": "Jadalnia", "Swedish (Svenska)": "Matsal",
        "Greek (Ελληνικά)": "Τραπεζαρία", "Indonesian (Bahasa Indonesia)": "Area Makan",
        "Vietnamese (Tiếng Việt)": "Khu Vực Ăn", "Malay (Bahasa Melayu)": "Ruang Makan", "Filipino (Tagalog)": "Dining Area"
    },
}

MODE_NAMES = {
    "Relax Evening": {
        "English": "Relax Evening", "Tamil (தமிழ்)": "நிதானமான மாலை", "Korean (한국어)": "편안한 저녁",
        "Thai (Thai)": "เย็นผ่อนคลาย", "Spanish (Español)": "Noche de Relax", "Hindi (हिन्दी)": "आरामदायक शाम",
        "Arabic (العربية)": "أمسية استرخاء", "Japanese (日本語)": "リラックスイブニング", "Chinese (中文)": "放松夜晚",
        "French (Français)": "Soirée Détente", "German (Deutsch)": "Entspannter Abend", "Italian (Italiano)": "Serata Relax",
        "Portuguese (Português)": "Noite Relaxante", "Russian (Русский)": "Спокойный вечер", "Turkish (Türkçe)": "Rahat Akşam",
        "Dutch (Nederlands)": "Ontspannen Avond", "Polish (Polski)": "Relaksujący Wieczór", "Swedish (Svenska)": "Lugn Kväll",
        "Greek (Ελληνικά)": "Χαλαρωτική Βραδιά", "Indonesian (Bahasa Indonesia)": "Malam Santai",
        "Vietnamese (Tiếng Việt)": "Buổi Tối Thư Giãn", "Malay (Bahasa Melayu)": "Malam Santai", "Filipino (Tagalog)": "Relax Evening"
    },
    "Focus": {
        "English": "Focus", "Tamil (தமிழ்)": "கவனம்", "Korean (한국어)": "집중", "Thai (Thai)": "สมาธิ",
        "Spanish (Español)": "Enfoque", "Hindi (हिन्दी)": "एकाग्रता", "Arabic (العربية)": "تركيز",
        "Japanese (日本語)": "フォーカス", "Chinese (中文)": "专注", "French (Français)": "Concentration",
        "German (Deutsch)": "Fokus", "Italian (Italiano)": "Concentrazione", "Portuguese (Português)": "Foco",
        "Russian (Русский)": "Фокус", "Turkish (Türkçe)": "Odaklanma", "Dutch (Nederlands)": "Focus",
        "Polish (Polski)": "Skupienie", "Swedish (Svenska)": "Fokus", "Greek (Ελληνικά)": "Εστίαση",
        "Indonesian (Bahasa Indonesia)": "Fokus", "Vietnamese (Tiếng Việt)": "Tập Trung", "Malay (Bahasa Melayu)": "Fokus",
        "Filipino (Tagalog)": "Focus"
    },
    "Sleep": {
        "English": "Sleep", "Tamil (தமிழ்)": "உறக்கம்", "Korean (한국어)": "수면", "Thai (Thai)": "นอนหลับ",
        "Spanish (Español)": "Sueño", "Hindi (हिन्दी)": "नींद", "Arabic (العربية)": "نوم", "Japanese (日本語)": "睡眠",
        "Chinese (中文)": "睡眠", "French (Français)": "Sommeil", "German (Deutsch)": "Schlaf", "Italian (Italiano)": "Sonno",
        "Portuguese (Português)": "Sono", "Russian (Русский)": "Сон", "Turkish (Türkçe)": "Uyku",
        "Dutch (Nederlands)": "Slaap", "Polish (Polski)": "Sen", "Swedish (Svenska)": "Sömn",
        "Greek (Ελληνικά)": "Ύπνος", "Indonesian (Bahasa Indonesia)": "Tidur", "Vietnamese (Tiếng Việt)": "Ngủ",
        "Malay (Bahasa Melayu)": "Tidur", "Filipino (Tagalog)": "Sleep"
    },
    "Deep Meditation": {
        "English": "Deep Meditation", "Tamil (தமிழ்)": "ஆழ்ந்த தியானம்", "Korean (한국어)": "깊은 명상",
        "Thai (Thai)": "การทำสมาธิแบบลึก", "Spanish (Español)": "Meditación Profunda", "Hindi (हिन्दी)": "गहरा ध्यान",
        "Arabic (العربية)": "تأمل عميق", "Japanese (日本語)": "深い瞑想", "Chinese (中文)": "深度冥想",
        "French (Français)": "Méditation Profonde", "German (Deutsch)": "Tiefe Meditation",
        "Italian (Italiano)": "Meditazione Profonda", "Portuguese (Português)": "Meditação Profunda",
        "Russian (Русский)": "Глубокая медитация", "Turkish (Türkçe)": "Derin Meditasyon",
        "Dutch (Nederlands)": "Diepe Meditatie", "Polish (Polski)": "Głęboka Medytacja", "Swedish (Svenska)": "Djup Meditation",
        "Greek (Ελληνικά)": "Βαθύς Διαλογισμός", "Indonesian (Bahasa Indonesia)": "Meditasi Mendalam",
        "Vietnamese (Tiếng Việt)": "Thiền Sâu", "Malay (Bahasa Melayu)": "Meditasi Mendalam", "Filipino (Tagalog)": "Deep Meditation"
    },
    "Energize": {
        "English": "Energize", "Tamil (தமிழ்)": "உற்சாகமூட்டு", "Korean (한국어)": "활력", "Thai (Thai)": "กระตุ้นพลังงาน",
        "Spanish (Español)": "Energizar", "Hindi (हिन्दी)": "ऊर्जावान", "Arabic (العربية)": "تنشيط",
        "Japanese (日本語)": "元気にする", "Chinese (中文)": "活力", "French (Français)": "Énergiser",
        "German (Deutsch)": "Energie", "Italian (Italiano)": "Energizza", "Portuguese (Português)": "Energizar",
        "Russian (Русский)": "Энергия", "Turkish (Türkçe)": "Enerjik", "Dutch (Nederlands)": "Energiek",
        "Polish (Polski)": "Energia", "Swedish (Svenska)": "Energi", "Greek (Ελληνικά)": "Ενέργεια",
        "Indonesian (Bahasa Indonesia)": "Energi", "Vietnamese (Tiếng Việt)": "Tiếp Năng Lượng", "Malay (Bahasa Melayu)": "Bertenaga",
        "Filipino (Tagalog)": "Energize"
    },
    "Zen Garden": {
        "English": "Zen Garden", "Tamil (தமிழ்)": "ஜென் தோட்டம்", "Korean (한국어)": "젠 가든", "Thai (Thai)": "สวนเซน",
        "Spanish (Español)": "Jardín Zen", "Hindi (हिन्दी)": "ज़ेन गार्डन", "Arabic (العربية)": "حديقة زن",
        "Japanese (日本語)": "禅ガーデン", "Chinese (中文)": "禅意花园", "French (Français)": "Jardin Zen",
        "German (Deutsch)": "Zen-Garten", "Italian (Italiano)": "Giardino Zen", "Portuguese (Português)": "Jardim Zen",
        "Russian (Русский)": "Дзен-сад", "Turkish (Türkçe)": "Zen Bahçesi", "Dutch (Nederlands)": "Zen Tuin",
        "Polish (Polski)": "Ogród Zen", "Swedish (Svenska)": "Zen Trädgård", "Greek (Ελληνικά)": "Κήπος Ζεν",
        "Indonesian (Bahasa Indonesia)": "Taman Zen", "Vietnamese (Tiếng Việt)": "Vườn Thiền", "Malay (Bahasa Melayu)": "Taman Zen",
        "Filipino (Tagalog)": "Zen Garden"
    },
    "Deep Calm Studio": {
        "English": "Deep Calm Studio", "Tamil (தமிழ்)": "ஆழ்ந்த அமைதி ஸ்டுடியோ", "Korean (한국어)": "깊은 고요 스튜디오",
        "Thai (Thai)": "สตูดิโอความสงบลึก", "Spanish (Español)": "Estudio de Calma Profunda", "Hindi (हिन्दी)": "गहरा शांत स्टूडियो",
        "Arabic (العربية)": "استوديو الهدوء العميق", "Japanese (日本語)": "ディープカームスタジオ", "Chinese (中文)": "深度平静工作室",
        "French (Français)": "Studio de Calme Profond", "German (Deutsch)": "Tiefenentspannungsstudio",
        "Italian (Italiano)": "Studio di Calma Profonda", "Portuguese (Português)": "Estúdio de Calma Profunda",
        "Russian (Русский)": "Студия глубокого спокойствия", "Turkish (Türkçe)": "Derin Sakinlik Stüdyosu",
        "Dutch (Nederlands)": "Diepe Rust Studio", "Polish (Polski)": "Studio Głębokiego Spokoju",
        "Swedish (Svenska)": "Djupt Lugn Studio", "Greek (Ελληνικά)": "Στούντιο Βαθιάς Ηρεμίας",
        "Indonesian (Bahasa Indonesia)": "Studio Ketenangan Mendalam", "Vietnamese (Tiếng Việt)": "Studio Tĩnh Lặng Sâu",
        "Malay (Bahasa Melayu)": "Studio Ketenangan Mendalam", "Filipino (Tagalog)": "Deep Calm Studio"
    },
    "Wind-Down Sleep": {
        "English": "Wind-Down Sleep", "Tamil (தமிழ்)": "தளர்வான உறக்கம்", "Korean (한국어)": "휴식 수면",
        "Thai (Thai)": "การนอนหลับผ่อนคลาย", "Spanish (Español)": "Sueño Relajante", "Hindi (हिन्दी)": "आरामदायक नींद",
        "Arabic (العربية)": "نوم استرخائي", "Japanese (日本語)": "リラックス睡眠", "Chinese (中文)": "放松睡眠",
        "French (Français)": "Sommeil Détente", "German (Deutsch)": "Entspannungsschlaf", "Italian (Italiano)": "Sonno Rilassante",
        "Portuguese (Português)": "Sono Relaxante", "Russian (Русский)": "Расслабляющий сон", "Turkish (Türkçe)": "Rahatlatıcı Uyku",
        "Dutch (Nederlands)": "Ontspannen Slaap", "Polish (Polski)": "Sen Relaksacyjny", "Swedish (Svenska)": "Avkopplande Sömn",
        "Greek (Ελληνικά)": "Χαλαρωτικός Ύπνος", "Indonesian (Bahasa Indonesia)": "Tidur Santai",
        "Vietnamese (Tiếng Việt)": "Giấc Ngủ Thư Giãn", "Malay (Bahasa Melayu)": "Tidur Santai", "Filipino (Tagalog)": "Wind-Down Sleep"
    },
    "Cinema Night": {
        "English": "Cinema Night", "Tamil (தமிழ்)": "சினிமா இரவு", "Korean (한국어)": "영화의 밤", "Thai (Thai)": "คืนภาพยนตร์",
        "Spanish (Español)": "Noche de Cine", "Hindi (हिन्दी)": "सिनेमा रात", "Arabic (العربية)": "ليلة سينما",
        "Japanese (日本語)": "シネマナイト", "Chinese (中文)": "电影之夜", "French (Français)": "Soirée Cinéma",
        "German (Deutsch)": "Kinonacht", "Italian (Italiano)": "Notte Cinema", "Portuguese (Português)": "Noite de Cinema",
        "Russian (Русский)": "Киноночь", "Turkish (Türkçe)": "Sinema Gecesi", "Dutch (Nederlands)": "Bioscoopavond",
        "Polish (Polski)": "Noc Filmowa", "Swedish (Svenska)": "Filmkväll", "Greek (Ελληνικά)": "Βραδιά Σινεμά",
        "Indonesian (Bahasa Indonesia)": "Malam Bioskop", "Vietnamese (Tiếng Việt)": "Đêm Điện Ảnh",
        "Malay (Bahasa Melayu)": "Malam Wayang", "Filipino (Tagalog)": "Cinema Night"
    },
    "Neutral Family Ambience": {
        "English": "Neutral Family Ambience", "Tamil (தமிழ்)": "நடுநிலை குடும்ப சூழல்", "Korean (한국어)": "중립 가족 분위기",
        "Thai (Thai)": "บรรยากาศครอบครัวเป็นกลาง", "Spanish (Español)": "Ambiente Familiar Neutral", "Hindi (हिन्दी)": "तटस्थ पारिवारिक माहौल",
        "Arabic (العربية)": "أجواء عائلية محايدة", "Japanese (日本語)": "ニュートラルファミリーアンビエンス", "Chinese (中文)": "中性家庭氛围",
        "French (Français)": "Ambiance Familiale Neutre", "German (Deutsch)": "Neutrale Familienatmosphäre",
        "Italian (Italiano)": "Ambiente Familiare Neutro", "Portuguese (Português)": "Ambiente Familiar Neutro",
        "Russian (Русский)": "Нейтральная семейная атмосфера", "Turkish (Türkçe)": "Nötr Aile Ortamı",
        "Dutch (Nederlands)": "Neutrale Gezinsfeer", "Polish (Polski)": "Neutralna Atmosfera Rodzinna",
        "Swedish (Svenska)": "Neutral Familjestämning", "Greek (Ελληνικά)": "Ουδέτερη Οικογενειακή Ατμόσφαιρα",
        "Indonesian (Bahasa Indonesia)": "Suasana Keluarga Netral", "Vietnamese (Tiếng Việt)": "Không Gian Gia Đình Trung Tính",
        "Malay (Bahasa Melayu)": "Suasana Keluarga Neutral", "Filipino (Tagalog)": "Neutral Family Ambience"
    },
}

MODE_NAMES["Reading"] = {
    "English": "Reading", "Tamil (தமிழ்)": "வாசிப்பு", "Korean (한국어)": "독서", "Thai (Thai)": "อ่านหนังสือ",
    "Spanish (Español)": "Lectura", "Hindi (हिन्दी)": "पढ़ना", "Arabic (العربية)": "القراءة", "Japanese (日本語)": "読書",
    "Chinese (中文)": "阅读", "French (Français)": "Lecture", "German (Deutsch)": "Lesen", "Italian (Italiano)": "Lettura",
    "Portuguese (Português)": "Leitura", "Russian (Русский)": "Чтение", "Turkish (Türkçe)": "Okuma",
    "Dutch (Nederlands)": "Lezen", "Polish (Polski)": "Czytanie", "Swedish (Svenska)": "Läsning",
    "Greek (Ελληνικά)": "Ανάγνωση", "Indonesian (Bahasa Indonesia)": "Membaca", "Vietnamese (Tiếng Việt)": "Đọc Sách",
    "Malay (Bahasa Melayu)": "Membaca", "Filipino (Tagalog)": "Pagbabasa"
}

LIGHT_WORDS = {
    "Daylight White": {
        "English": "Daylight White", "Tamil (தமிழ்)": "பகல் வெள்ளை", "Korean (한국어)": "주광색 백색",
        "Thai (Thai)": "ขาวแสงกลางวัน", "Spanish (Español)": "Blanco Luz de Día", "Hindi (हिन्दी)": "दिन का सफेद",
        "Arabic (العربية)": "أبيض ضوء النهار", "Japanese (日本語)": "デイライトホワイト", "Chinese (中文)": "日光白",
        "French (Français)": "Blanc Lumière du Jour", "German (Deutsch)": "Tageslichtweiß", "Italian (Italiano)": "Bianco Luce Diurna",
        "Portuguese (Português)": "Branco Luz do Dia", "Russian (Русский)": "Белый дневной", "Turkish (Türkçe)": "Gün Işığı Beyaz",
        "Dutch (Nederlands)": "Daglicht Wit", "Polish (Polski)": "Biel Dzienna", "Swedish (Svenska)": "Dagsljus Vit",
        "Greek (Ελληνικά)": "Λευκό Φωτός Ημέρας", "Indonesian (Bahasa Indonesia)": "Putih Cahaya Siang",
        "Vietnamese (Tiếng Việt)": "Trắng Ánh Sáng Ngày", "Malay (Bahasa Melayu)": "Putih Cahaya Siang", "Filipino (Tagalog)": "Daylight White"
    },
    "Soft White": {
        "English": "Soft White", "Tamil (தமிழ்)": "மென்மையான வெள்ளை", "Korean (한국어)": "소프트 화이트",
        "Thai (Thai)": "ขาวนุ่ม", "Spanish (Español)": "Blanco Suave", "Hindi (हिन्दी)": "कोमल सफेद",
        "Arabic (العربية)": "أبيض ناعم", "Japanese (日本語)": "ソフトホワイト", "Chinese (中文)": "柔和白",
        "French (Français)": "Blanc Doux", "German (Deutsch)": "Sanftes Weiß", "Italian (Italiano)": "Bianco Morbido",
        "Portuguese (Português)": "Branco Suave", "Russian (Русский)": "Мягкий белый", "Turkish (Türkçe)": "Yumuşak Beyaz",
        "Dutch (Nederlands)": "Zacht Wit", "Polish (Polski)": "Miękka Biel", "Swedish (Svenska)": "Mjuk Vit",
        "Greek (Ελληνικά)": "Απαλό Λευκό", "Indonesian (Bahasa Indonesia)": "Putih Lembut",
        "Vietnamese (Tiếng Việt)": "Trắng Dịu", "Malay (Bahasa Melayu)": "Putih Lembut", "Filipino (Tagalog)": "Soft White"
    },
    "Warm Candlelight": {
        "English": "Warm Candlelight", "Tamil (தமிழ்)": "சூடான மெழுகுவர்த்தி வெளிச்சம்", "Korean (한국어)": "따뜻한 촛불",
        "Thai (Thai)": "แสงเทียนอบอุ่น", "Spanish (Español)": "Luz de Vela Cálida", "Hindi (हिन्दी)": "गर्म मोमबत्ती",
        "Arabic (العربية)": "ضوء شمعة دافئ", "Japanese (日本語)": "暖かいキャンドルライト", "Chinese (中文)": "温暖烛光",
        "French (Français)": "Lumière de Bougie Chaud", "German (Deutsch)": "Warmes Kerzenlicht", "Italian (Italiano)": "Luce di Candela Calda",
        "Portuguese (Português)": "Luz de Vela Quente", "Russian (Русский)": "Теплый свет свечей", "Turkish (Türkçe)": "Sıcak Mum Işığı",
        "Dutch (Nederlands)": "Warm Kaarslicht", "Polish (Polski)": "Ciepłe Światło Świec", "Swedish (Svenska)": "Varmt Ljus",
        "Greek (Ελληνικά)": "Ζεστό Φως Κεριού", "Indonesian (Bahasa Indonesia)": "Cahaya Lilin Hangat",
        "Vietnamese (Tiếng Việt)": "Ánh Nến Ấm", "Malay (Bahasa Melayu)": "Cahaya Lilin Hangat", "Filipino (Tagalog)": "Warm Candlelight"
    },
    "Calm Blue": {
        "English": "Calm Blue", "Tamil (தமிழ்)": "அமைதியான நீலம்", "Korean (한국어)": "차분한 블루",
        "Thai (Thai)": "สีน้ำเงินสงบ", "Spanish (Español)": "Azul Calma", "Hindi (हिन्दी)": "शांत नीला",
        "Arabic (العربية)": "أزرق هادئ", "Japanese (日本語)": "穏やかなブルー", "Chinese (中文)": "平静蓝",
        "French (Français)": "Bleu Calme", "German (Deutsch)": "Ruhiges Blau", "Italian (Italiano)": "Blu Calmo",
        "Portuguese (Português)": "Azul Calmo", "Russian (Русский)": "Спокойный синий", "Turkish (Türkçe)": "Sakin Mavi",
        "Dutch (Nederlands)": "Kalm Blauw", "Polish (Polski)": "Spokojny Błękit", "Swedish (Svenska)": "Lugn Blå",
        "Greek (Ελληνικά)": "Ήρεμο Μπλε", "Indonesian (Bahasa Indonesia)": "Biru Tenang",
        "Vietnamese (Tiếng Việt)": "Xanh Lam Tĩnh", "Malay (Bahasa Melayu)": "Biru Tenang", "Filipino (Tagalog)": "Calm Blue"
    },
    "Fresh Green": {
        "English": "Fresh Green", "Tamil (தமிழ்)": "புதிய பச்சை", "Korean (한국어)": "싱그러운 그린",
        "Thai (Thai)": "สีเขียวสด", "Spanish (Español)": "Verde Fresco", "Hindi (हिन्दी)": "ताज़ा हरा",
        "Arabic (العربية)": "أخضر منعش", "Japanese (日本語)": "フレッシュグリーン", "Chinese (中文)": "清新绿",
        "French (Français)": "Vert Frais", "German (Deutsch)": "Frisches Grün", "Italian (Italiano)": "Verde Fresco",
        "Portuguese (Português)": "Verde Fresco", "Russian (Русский)": "Свежий зелёный", "Turkish (Türkçe)": "Taze Yeşil",
        "Dutch (Nederlands)": "Fris Groen", "Polish (Polski)": "Świeża Zieleń", "Swedish (Svenska)": "Fräsch Grön",
        "Greek (Ελληνικά)": "Φρέσκο Πράσινο", "Indonesian (Bahasa Indonesia)": "Hijau Segar",
        "Vietnamese (Tiếng Việt)": "Xanh Tươi", "Malay (Bahasa Melayu)": "Hijau Segar", "Filipino (Tagalog)": "Fresh Green"
    },
    "Violet Glow": {
        "English": "Violet Glow", "Tamil (தமிழ்)": "ஊதா பளபளப்பு", "Korean (한국어)": "바이올렛 글로우",
        "Thai (Thai)": "แสงสีม่วง", "Spanish (Español)": "Brillo Violeta", "Hindi (हिन्दी)": "बैंगनी चमक",
        "Arabic (العربية)": "توهج بنفسجي", "Japanese (日本語)": "バイオレットグロー", "Chinese (中文)": "紫罗兰辉光",
        "French (Français)": "Lueur Violette", "German (Deutsch)": "Violettes Leuchten", "Italian (Italiano)": "Bagliore Viola",
        "Portuguese (Português)": "Brilho Violeta", "Russian (Русский)": "Фиолетовое свечение", "Turkish (Türkçe)": "Mor Işıltı",
        "Dutch (Nederlands)": "Violette Gloed", "Polish (Polski)": "Fioletowy Blask", "Swedish (Svenska)": "Violett Glöd",
        "Greek (Ελληνικά)": "Βιολετί Λάμψη", "Indonesian (Bahasa Indonesia)": "Cahaya Violet",
        "Vietnamese (Tiếng Việt)": "Ánh Tím", "Malay (Bahasa Melayu)": "Cahaya Violet", "Filipino (Tagalog)": "Violet Glow"
    },
    "Warm Amber": {
        "English": "Warm Amber", "Tamil (தமிழ்)": "சூடான அம்பர்", "Korean (한국어)": "따뜻한 앰버",
        "Thai (Thai)": "อำพันอบอุ่น", "Spanish (Español)": "Ámbar Cálido", "Hindi (हिन्दी)": "गर्म एम्बर",
        "Arabic (العربية)": "كهرماني دافئ", "Japanese (日本語)": "ウォームアンバー", "Chinese (中文)": "暖琥珀色",
        "French (Français)": "Ambre Chaud", "German (Deutsch)": "Warmes Bernstein", "Italian (Italiano)": "Ambra Calda",
        "Portuguese (Português)": "Âmbar Quente", "Russian (Русский)": "Теплый янтарь", "Turkish (Türkçe)": "Sıcak Kehribar",
        "Dutch (Nederlands)": "Warm Amber", "Polish (Polski)": "Ciepły Bursztyn", "Swedish (Svenska)": "Varm Bärnsten",
        "Greek (Ελληνικά)": "Ζεστό Κεχριμπάρι", "Indonesian (Bahasa Indonesia)": "Amber Hangat",
        "Vietnamese (Tiếng Việt)": "Hổ Phách Ấm", "Malay (Bahasa Melayu)": "Amber Hangat", "Filipino (Tagalog)": "Warm Amber"
    }
}
LIGHT_ADJ = {
    "Bright": {"English": "Bright", "Tamil (தமிழ்)": "பிரகாசமான", "Korean (한국어)": "밝은", "Thai (Thai)": "สว่าง", "Spanish (Español)": "Brillante", "Hindi (हिन्दी)": "उज्ज्वल", "Arabic (العربية)": "ساطع", "Japanese (日本語)": "明るい", "Chinese (中文)": "明亮", "French (Français)": "Lumineux", "German (Deutsch)": "Hell", "Italian (Italiano)": "Luminoso", "Portuguese (Português)": "Brilhante", "Russian (Русский)": "Яркий", "Turkish (Türkçe)": "Parlak", "Dutch (Nederlands)": "Helder", "Polish (Polski)": "Jasny", "Swedish (Svenska)": "Ljus", "Greek (Ελληνικά)": "Φωτεινό", "Indonesian (Bahasa Indonesia)": "Terang", "Vietnamese (Tiếng Việt)": "Sáng", "Malay (Bahasa Melayu)": "Terang", "Filipino (Tagalog)": "Bright"},
    "Soft": {"English": "Soft", "Tamil (தமிழ்)": "மென்மையான", "Korean (한국어)": "부드러운", "Thai (Thai)": "นุ่ม", "Spanish (Español)": "Suave", "Hindi (हिन्दी)": "कोमल", "Arabic (العربية)": "ناعم", "Japanese (日本語)": "ソフト", "Chinese (中文)": "柔和", "French (Français)": "Doux", "German (Deutsch)": "Sanft", "Italian (Italiano)": "Morbido", "Portuguese (Português)": "Suave", "Russian (Русский)": "Мягкий", "Turkish (Türkçe)": "Yumuşak", "Dutch (Nederlands)": "Zacht", "Polish (Polski)": "Miękki", "Swedish (Svenska)": "Mjuk", "Greek (Ελληνικά)": "Απαλό", "Indonesian (Bahasa Indonesia)": "Lembut", "Vietnamese (Tiếng Việt)": "Dịu", "Malay (Bahasa Melayu)": "Lembut", "Filipino (Tagalog)": "Soft"},
    "Dim": {"English": "Dim", "Tamil (தமிழ்)": "மங்கலான", "Korean (한국어)": "어두운", "Thai (Thai)": "หรี่", "Spanish (Español)": "Tenue", "Hindi (हिन्दी)": "मंद", "Arabic (العربية)": "خافت", "Japanese (日本語)": "薄暗い", "Chinese (中文)": "暗淡", "French (Français)": "Sombre", "German (Deutsch)": "Gedimmt", "Italian (Italiano)": "Fioco", "Portuguese (Português)": "Escuro", "Russian (Русский)": "Тусклый", "Turkish (Türkçe)": "Loş", "Dutch (Nederlands)": "Gedoofd", "Polish (Polski)": "Przyćmiony", "Swedish (Svenska)": "Dämpad", "Greek (Ελληνικά)": "Χαμηλό", "Indonesian (Bahasa Indonesia)": "Redup", "Vietnamese (Tiếng Việt)": "Mờ", "Malay (Bahasa Melayu)": "Malap", "Filipino (Tagalog)": "Dim"},
}


# ---- Zen Sanctuary / multi-source biometrics / Wearables Hub strings (English row; other languages are translated live by tt()) ----
ZEN_T = {
    "zk_pills": ("Instant mood",),
    "zp_rest": ("Deep Rest",), "zp_focus": ("Zen Focus",), "zp_reading": ("Aura Reading",), "zp_night": ("Night Calm",),
    "zk_more": ("More quick actions, watch card, dial and family",),
    "zk_hr": ("Live heart rate",),
    "zk_calm": ("🟢 Deep Calm 🧘",), "zk_bal": ("🟡 Balanced & Centered 🌿",), "zk_high": ("🔴 Elevated Stress — Breathe Now 🌬️",),
    "zk_in": ("Breathe in…",), "zk_out": ("Breathe out…",),
    "zk_src": ("Source: {s}",),
    "zk_dock": ("Living Player",), "zk_master": ("Master volume",),
    "zk_mixer": ("🎛️ Sound Studio Mixer",),
    "zk_l432": ("432Hz Healing Frequency",), "zk_lrain": ("Rain on Glass",),
    "zk_lstream": ("Gentle Stream / Chimes",), "zk_lnoise": ("White / Pink Noise",),
    "zk_tell": ("Just tell AuraSync",), "zk_tell_hint": ("Tap the microphone and say how you want to feel. To type a command, use the ✨ Aura AI button.",),
    "zk_va_cfg": ("⚙️ Configure Voice Assistants",), "zk_va_done": ("✓ Voice assistants linked · Edit",),
    "zk_va_mark": ("Mark as Configured & Hide",),
    "zk_va_local": ("Local network URL (Apple Shortcuts)",), "zk_va_remote": ("Remote URL (Apple Shortcuts, away from home)",),
    "zk_va_unlock": ("Unlock Voice Automation Links in the sidebar to reveal your personal URLs. The pattern is:",),
    "zk_va_google": ("Google Assistant routing",),
    "zk_va_g1": ("Install HTTP Shortcuts on your Android phone.",),
    "zk_va_g2": ("Create a Browser Shortcut with the Remote URL above.",),
    "zk_va_g3": ("In Google Assistant choose Routines, add your phrase, then the action Open HTTP Shortcut.",),
    "zk_ap": ("Biometric Auto-Pilot (above 85 BPM)",),
    "zk_ap_hint": ("Switches the atmosphere only when your heart rate crosses 85 BPM, so your own tweaks are never overwritten.",),
    "zk_ap_stress": ("Elevated heart rate ({hr} BPM): amber candlelight, AC 22 °C, gentle breeze, 432Hz with rain",),
    "zk_ap_calm": ("Calm heart rate ({hr} BPM): soft warm daylight, 24 °C, natural breeze, zen chimes",),
    "zk_manual": ("Manual Control",), "zk_manual_note": ("Automatic biometric takeover is paused.",),
    "zk_bulb": ("Smart Bulb",), "zk_power": ("Power",), "zk_color": ("Colour",), "zk_bright": ("Brightness",),
    "zk_ac": ("Smart AC",), "zk_temp": ("Temperature (°C)",), "zk_acmode": ("Cooling mode",),
    "zk_fan": ("Smart Fan",), "zk_fanspd": ("Speed",),
    "fan_Off": ("Off",), "fan_Low": ("Low",), "fan_Medium": ("Medium",), "fan_High": ("High",), "fan_Natural Breeze": ("Natural Breeze",),
    "acm_Cool": ("Cool",), "acm_Dry": ("Dry",), "acm_Fan Only": ("Fan Only",), "acm_Sleep Eco": ("Sleep Eco",),
    "zk_endp": ("Device Endpoints",), "zk_wiz": ("WiZ bulb IP address (local network)",),
    "zk_acurl": ("AC webhook URL",), "zk_fanurl": ("Fan webhook URL",), "zk_save": ("Save endpoints",),
    "zk_ep_ok": ("Endpoints saved for this room.",), "zk_ep_bad": ("Check the address: the WiZ IP must be a local network address and webhooks must start with http:// or https://",),
    "zk_nodev": ("This room has no {d}.",),
    "zk_hub": ("Universal Wearables Hub",),
    "zk_hub_sub": ("Link your wearable in one tap, no Shortcuts needed. Cloud links here are simulated; real readings arrive through bridge.py, the page link (?hr=) or Bluetooth.",),
    "zk_link": ("Link in 1 tap",), "zk_unlink": ("Unlink",), "zk_linked": ("Linked (simulated)",), "zk_notlinked": ("Not linked",),
    "zk_ble": ("Direct Bluetooth: Heart Rate Service (0x180D)",),
    "zk_bridge_live": ("bridge.py is live: {hr} BPM, updated {age} s ago",),
    "zk_bridge_wait": ("bridge.py: waiting for a fresh aurasync_bridge.json",),
}
T.update(ZEN_T)


def zt(key, **kw):
    return tt(key, **kw)


def t(key, **kw):
    lang = st.session_state.get("lang", "English")
    i = LANGS.index(lang)
    row = T[key]
    if i < 5:
        text = row[i] if i < len(row) else row[0]
    elif key in CI and lang in TX:
        text = TX[lang][CI[key]]
    else:
        text = row[0]
    for k, v in kw.items():
        text = text.replace("{" + k + "}", str(v))
    return text


def tr_room(name):
    lang = st.session_state.get("lang", "English")
    return ROOM_NAMES.get(name, {}).get(lang, name)


def tr_mode(name):
    lang = st.session_state.get("lang", "English")
    return MODE_NAMES.get(name, {}).get(lang, name)


# ----------------------------------------------------------------------------
# Full-app translation layer.
# ----------------------------------------------------------------------------
LANG_CODES = {"Tamil (தமிழ்)": "ta", "Korean (한국어)": "ko", "Thai (Thai)": "th", "Spanish (Español)": "es",
              "Hindi (हिन्दी)": "hi", "Arabic (العربية)": "ar", "Japanese (日本語)": "ja", "Chinese (中文)": "zh-CN",
              "French (Français)": "fr", "German (Deutsch)": "de", "Italian (Italiano)": "it",
              "Portuguese (Português)": "pt", "Russian (Русский)": "ru", "Turkish (Türkçe)": "tr",
              "Dutch (Nederlands)": "nl", "Polish (Polski)": "pl", "Swedish (Svenska)": "sv", "Greek (Ελληνικά)": "el",
              "Indonesian (Bahasa Indonesia)": "id", "Vietnamese (Tiếng Việt)": "vi", "Malay (Bahasa Melayu)": "ms",
              "Filipino (Tagalog)": "tl"}
SCRIPT_RANGES = {"ta": [(0x0B80, 0x0BFF)], "ko": [(0xAC00, 0xD7AF), (0x1100, 0x11FF)], "th": [(0x0E00, 0x0E7F)],
                 "hi": [(0x0900, 0x097F)], "ar": [(0x0600, 0x06FF)], "ja": [(0x3040, 0x30FF), (0x4E00, 0x9FFF)],
                 "zh-CN": [(0x4E00, 0x9FFF)], "ru": [(0x0400, 0x04FF)], "el": [(0x0370, 0x03FF)]}
PH_RE = re.compile(r"\{[A-Za-z_][A-Za-z_0-9]*\}|\d+(?:[.,:]\d+)*")
EDGE_RE = re.compile(r"^(\W*)(.*?)(\W*)$", re.S)
LETTERS_RE = re.compile(r"[^\W\d_]{2}")

_REG = sys.modules.setdefault("_aurasync_reg", types.ModuleType("_aurasync_reg"))
if not hasattr(_REG, "lock"):
    _REG.lock = threading.Lock()
    _REG.cache = None
    _REG.fail = 0
    _REG.down_until = 0.0
    _REG.saved_at = 0.0
    _REG.pending = False
    _REG.static = {}
    _REG.cands = None
    _REG.mt_ok = None
    _REG.wrapped = False
    _REG.impl = {}
for _n, _d in (("auth_fail", {}),):   # new attributes are added one by one, so a long-running server never lacks them
    if not hasattr(_REG, _n):
        setattr(_REG, _n, _d)


def lang_code():
    return LANG_CODES.get(st.session_state.get("lang", "English"))


def _cache_file():
    try:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "aurasync_i18n_cache.json")
    except NameError:
        return "aurasync_i18n_cache.json"


def _cache():
    if _REG.cache is None:
        data = {}
        try:
            with open(_cache_file(), encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
        _REG.cache = data if isinstance(data, dict) else {}
    return _REG.cache


def _cache_save(force=False):
    if not _REG.pending:
        return
    if not force and time.time() - _REG.saved_at < 4:
        return
    try:
        with _REG.lock:
            blob = json.dumps(_REG.cache, ensure_ascii=False)
        with open(_cache_file(), "w", encoding="utf-8") as f:
            f.write(blob)
        _REG.saved_at = time.time()
        _REG.pending = False
    except Exception:
        pass


def mt_available():
    if _REG.mt_ok is None:
        try:
            import deep_translator  # noqa: F401
            _REG.mt_ok = True
        except Exception:
            _REG.mt_ok = False
    return _REG.mt_ok


def _mt_one(code, text):
    if time.time() < _REG.down_until:
        return None
    try:
        from deep_translator import GoogleTranslator
        out = GoogleTranslator(source="auto", target=code).translate(text)
        if not isinstance(out, str) or not out.strip():
            return None
        _REG.fail = 0
        return out
    except Exception:
        _REG.fail += 1
        if _REG.fail >= 4:
            _REG.down_until = time.time() + 90
            _REG.fail = 0
        return None


def _templ(core):
    """Numbers and {placeholders} become {0}, {1}... so one translation serves every value."""
    toks = []

    def sub(m):
        toks.append(m.group(0))
        return "{" + str(len(toks) - 1) + "}"
    return PH_RE.sub(sub, core), toks


def _norm_ph(text):
    return re.sub(r"\{\s*(\d+)\s*\}", r"{\1}", text)


def _untempl(text, toks):
    text = _norm_ph(text)
    for i, tok in enumerate(toks):
        text = text.replace("{" + str(i) + "}", tok)
    return text


def _ph_same(a, b):
    return set(re.findall(r"\{\s*(\d+)\s*\}", a)) == set(re.findall(r"\{\s*(\d+)\s*\}", b))


def _mt_batch(code, templs):
    """Translate many short strings with few requests."""
    chunks, chunk, size = [], [], 0
    for s in templs:
        if "\n" in s:
            continue
        if chunk and (size + len(s) > 2800 or len(chunk) >= 40):
            chunks.append(chunk)
            chunk, size = [], 0
        chunk.append(s)
        size += len(s) + 1
    if chunk:
        chunks.append(chunk)

    def work(ch):
        if len(ch) > 1:
            r = _mt_one(code, "\n".join(ch))
            if r is not None:
                parts = r.split("\n")
                if len(parts) == len(ch):
                    return dict(zip(ch, parts))
        res = {}
        for s in ch:
            x = _mt_one(code, s)
            if x:
                res[s] = x
        return res
    out = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        for res in ex.map(work, chunks):
            out.update(res)
    return out


def _static_set(lang):
    s = _REG.static.get(lang)
    if s is None:
        s, i = set(), LANGS.index(lang)
        for key, row in T.items():
            v = None
            if i < 5:
                v = row[i] if i < len(row) else None
            elif lang in TX and key in CI:
                v = TX[lang][CI[key]]
            if v:
                s.add(v)
                s.add(re.sub(r"^\W+|\W+$", "", v))
        _REG.static[lang] = s
    return s


_PINNED = set()          # strings that must never be machine-translated (bilingual language gate)


def _skip(core, code):
    """Already in the chosen language (hand translation or same script)?"""
    if core in _PINNED:
        return True
    lang = st.session_state.get("lang", "English")
    if core in _static_set(lang):
        return True
    rng = SCRIPT_RANGES.get(code)
    if rng:
        letters = [c for c in core if c.isalpha()]
        if letters:
            hit = sum(1 for c in letters if any(a <= ord(c) <= b for a, b in rng))
            if hit / len(letters) >= 0.3:
                return True
    return False


def tr(text):
    """Translate one display string into the chosen language (no-op in English)."""
    code = lang_code()
    if not code or not isinstance(text, str) or not text.strip():
        return text
    m = EDGE_RE.match(text)
    lead, core, tail = m.group(1), m.group(2), m.group(3)
    if not LETTERS_RE.search(core) or _skip(core, code):
        return text
    templ, toks = _templ(core)
    if not LETTERS_RE.search(templ):
        return text
    key = code + "|" + templ
    cache = _cache()
    hit = cache.get(key)
    if hit is None:
        if not mt_available() or time.time() < _REG.down_until:
            return text
        out = _mt_one(code, templ)
        if not out or not _ph_same(templ, out):
            return text
        hit = _norm_ph(out)
        cache[key] = hit
        _REG.pending = True
        _cache_save()
    return lead + _untempl(hit, toks) + tail


def tr_html(text):
    if re.search(r"<(style|script|svg)\b", text, re.I):
        return text
    out, skip = [], False
    for p in re.split(r"(<[^>]+>)", text):
        if len(p) > 2 and p.startswith("<") and p.endswith(">") and not p.startswith("< "):
            low = p.lower()
            if 'translate="no"' in low:
                skip = True
            elif low.startswith("</span") and skip:
                skip = False
            out.append(p)
        elif skip or not p.strip():
            out.append(p)
        else:
            raw = html.unescape(p)
            new = tr(raw)
            out.append(p if new == raw else html.escape(new, quote=False))
    return "".join(out)


def tr_md(text, html_ok=False):
    if not lang_code() or not isinstance(text, str) or not text.strip():
        return text
    if html_ok or re.search(r"<[A-Za-z/!]", text):
        return tr_html(text)
    if "```" in text or "](" in text:
        return text
    return "\n".join(ln if "`" in ln else tr(ln) for ln in text.split("\n"))


def _ui_like(s):
    if not (3 <= len(s) <= 160) or re.fullmatch(r"[a-z_0-9]+", s) or "\n" in s:
        return False
    if re.search(r"[<>;=\\]|::|->|https?:|\.py\b|#[0-9a-fA-F]{3,8}\b|\w\(\)|\bst\.|\bss\.", s):
        return False
    return not re.search(r"[{}]", PH_RE.sub("", s))


def _candidates():
    if _REG.cands is None:
        pool = set()
        for row in T.values():
            if row and row[0]:
                pool.add(row[0])
        try:
            with open(os.path.abspath(__file__), encoding="utf-8") as f:
                tree = ast.parse(f.read())
            for n in ast.walk(tree):
                if isinstance(n, ast.Constant) and isinstance(n.value, str):
                    pool.add(n.value)
        except Exception:
            pass
        out = set()
        for s in pool:
            if _ui_like(s):
                core = EDGE_RE.match(s).group(2)
                tpl, _ = _templ(core)
                if LETTERS_RE.search(tpl) and len(tpl) <= 200:
                    out.add(tpl)
        _REG.cands = sorted(out)
    return _REG.cands


def i18n_prefetch():
    """Translate every static UI string for the chosen language in a few parallel batches."""
    code = lang_code()
    if not code or not mt_available():
        return False
    cache = _cache()
    todo = [s for s in _candidates() if (code + "|" + s) not in cache and not _skip(s, code)]
    if not todo:
        return True
    res = _mt_batch(code, todo)
    for s, o in res.items():
        if _ph_same(s, o):
            cache[code + "|" + s] = _norm_ph(o)
    _REG.pending = True
    _cache_save(force=True)
    return bool(res)


_I18N_TEXT = ("markdown", "caption", "subheader", "header", "title", "info", "success", "warning", "error", "toast")
_I18N_LABEL = ("button", "form_submit_button", "toggle", "checkbox", "selectbox", "multiselect", "radio", "slider",
               "select_slider", "text_input", "text_area", "number_input", "color_picker", "time_input", "date_input",
               "segmented_control", "pills", "expander", "popover", "chat_input", "file_uploader", "camera_input",
               "download_button", "link_button", "progress")
_I18N_OPTS = ("selectbox", "multiselect", "radio", "segmented_control", "select_slider", "pills")


def _xl_args(impl, kind, is_method, a, k):
    a, i0 = list(a), (1 if is_method else 0)
    trf, md = impl["tr"], impl["tr_md"]
    if kind == "text":
        if len(a) > i0 and isinstance(a[i0], str):
            a[i0] = md(a[i0], bool(k.get("unsafe_allow_html")))
        elif isinstance(k.get("body"), str):
            k["body"] = md(k["body"], bool(k.get("unsafe_allow_html")))
        return tuple(a), k
    if len(a) > i0 and isinstance(a[i0], str):
        a[i0] = trf(a[i0])
    elif isinstance(k.get("label"), str):
        k["label"] = trf(k["label"])
    for nm in ("help", "placeholder", "text"):
        if isinstance(k.get(nm), str):
            k[nm] = trf(k[nm])
    if kind == "opts" and k.get("key") != "lang":
        ff = k.get("format_func")
        k["format_func"] = (lambda x, _f=ff: trf(str(_f(x) if _f else x)))
    return tuple(a), k


def _i18n_wrap(fn, name, is_method):
    kind = "text" if name in _I18N_TEXT else ("opts" if name in _I18N_OPTS else "label")

    def w(*a, **k):
        impl = _REG.impl
        try:
            if impl["lang_code"]():
                a, k = _xl_args(impl, kind, is_method, a, k)
        except Exception:
            pass
        return fn(*a, **k)
    w._aura = True
    w.__name__ = getattr(fn, "__name__", name)
    w.__doc__ = getattr(fn, "__doc__", None)
    return w


def install_i18n():
    """Every Streamlit text / label call goes through the translator, so no page can stay in English."""
    _REG.impl = {"tr": tr, "tr_md": tr_md, "lang_code": lang_code}
    if _REG.wrapped:
        return
    try:
        from streamlit.delta_generator import DeltaGenerator
    except Exception:
        DeltaGenerator = None
    for name in _I18N_TEXT + _I18N_LABEL:
        fn = getattr(st, name, None)
        if callable(fn) and not getattr(fn, "_aura", False):
            setattr(st, name, _i18n_wrap(fn, name, False))
        if DeltaGenerator is not None:
            fn = getattr(DeltaGenerator, name, None)
            if callable(fn) and not getattr(fn, "_aura", False):
                setattr(DeltaGenerator, name, _i18n_wrap(fn, name, True))
    _REG.wrapped = True


# ----------------------------------------------------------------------------
# Styling
# ----------------------------------------------------------------------------
PALETTES = {
    # Dark: black and gold
    "dark": {"SCHEME": "dark", "BG": "#090A0E", "SIDE": "#0C0D12", "BTN": "#0A0B0F", "ACC": "#D4AF37", "ACC2": "#B8962E",
             "ONACC": "#141414", "CARD1": "#12151C", "CARD2": "#0E1016", "STAT": "#12151C", "SUB": "#A89F86",
             "LOG": "#CFC7AE", "MUTE": "#9E9A8E", "CHATBG": "#0E1016", "BUBDV": "#171A22", "TXT": "#F1ECDF",
             "TXT2": "#E8E2D0", "INPUT": "#12151C", "BORDER": "#262932", "POP": "#14171E", "SEL": "#3A3115", "HUE": "48deg",
             "GLOW": "radial-gradient(ellipse at 50% 0%, rgba(212,175,55,0.08), transparent 70%)", "GLASS": "rgba(18, 21, 28, 0.75)",
             "GLASSB": "rgba(255, 255, 255, 0.07)", "GOLDLINE": "rgba(212,175,55,0.38)", "GOLDSOFT": "rgba(212,175,55,0.12)",
             "GRAD": "linear-gradient(135deg, #EACB86, #C9A24A)", "CHAMP": "#E5C378", "GSHADOW": "0 8px 32px rgba(0,0,0,0.4)"},
    # Light: pure white page, electric blue accent, near-black text
    "light": {"SCHEME": "light", "BG": "#FFFFFF", "SIDE": "#FFFFFF", "BTN": "#FFFFFF", "ACC": "#0057FF", "ACC2": "#0043CC",
              "ONACC": "#FFFFFF", "CARD1": "#FFFFFF", "CARD2": "#F5F8FF", "STAT": "#F3F7FF", "SUB": "#3F4F73",
              "LOG": "#1E293B", "MUTE": "#566176", "CHATBG": "#FFFFFF", "BUBDV": "#EEF3FF", "TXT": "#000000",
              "TXT2": "#1E293B", "INPUT": "#D6F5D6", "BORDER": "#CFDBF5", "POP": "#E8F8E8", "SEL": "#BFEBBF", "HUE": "212deg",
              "GLOW": "none", "GLASS": "rgba(255, 255, 255, 0.88)", "GLASSB": "rgba(15, 23, 42, 0.10)", "GOLDLINE": "rgba(0,87,255,0.35)",
              "GOLDSOFT": "rgba(0,87,255,0.08)", "GRAD": "linear-gradient(135deg, #2F7BFF, #0057FF)", "CHAMP": "#0057FF",
              "GSHADOW": "0 6px 24px rgba(15,23,42,0.08)",
              # light-only dropdown / tab tokens (FIX 3): light green surface, black text, darker-green borders
              "DDBG": "#D6F5D6", "DDHOV": "#BFEBBF", "DDSEL": "#A8E0A8", "DDLINE": "#5E9E5E", "DDLINE2": "#2E7D32",
              "DDOFF": "#E8F4E8"},
}

CSS_T = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Cinzel:wght@400;500&family=Playfair+Display:wght@400;500&display=swap');
:root { color-scheme: @SCHEME@; }
html, body, [class*="css"], .stApp { font-family: 'Inter', sans-serif; color: @TXT@; }
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] { background-color: @BG@ !important; }
[data-testid="stHeader"], [data-testid="stBottom"] > div { background-color: @BG@ !important; }
[data-testid="stSidebar"], [data-testid="stSidebar"] > div:first-child { background-color: @SIDE@ !important; }
[data-testid="stSidebar"] { border-right: 1px solid @ACC@40; }
.stApp p, .stApp li, .stApp label, [data-testid="stWidgetLabel"] p, [data-testid="stMarkdownContainer"] p { color: @TXT@; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * { color: @MUTE@ !important; }
[data-baseweb="radio"] *, [data-baseweb="checkbox"] *, [data-testid="stToggle"] * { color: @TXT@; }
hr { border-color: @BORDER@ !important; }
h1, h2, h3, h4 { color: @ACC@ !important; font-weight: 600; letter-spacing: 0.3px; }
[data-baseweb="input"] > div, [data-baseweb="base-input"], [data-baseweb="textarea"], [data-baseweb="select"] > div {
  background-color: @INPUT@ !important; border-color: @BORDER@ !important; color: @TXT@ !important; }
input, textarea { color: @TXT@ !important; -webkit-text-fill-color: @TXT@ !important; background-color: transparent !important; }
[data-baseweb="select"] div, [data-baseweb="select"] span, [data-baseweb="select"] svg { color: @TXT@ !important; fill: @TXT@ !important; }
[data-baseweb="tag"] { background-color: @ACC@ !important; }
[data-baseweb="tag"] span, [data-baseweb="tag"] svg { color: @ONACC@ !important; fill: @ONACC@ !important; }
[data-baseweb="popover"], [data-baseweb="popover"] > div, [data-baseweb="menu"], ul[role="listbox"], [data-baseweb="calendar"] {
  background-color: @POP@ !important; color: @TXT@ !important; }
[data-baseweb="popover"] li, [role="option"] { background-color: @POP@ !important; color: @TXT@ !important; }
[data-baseweb="popover"] li:hover, [role="option"]:hover, [role="option"][aria-selected="true"] { background-color: @ACC@33 !important; }
[data-testid="stNumberInput"] button { background-color: @INPUT@ !important; color: @TXT@ !important; border-color: @BORDER@ !important; }
[data-testid="stChatInput"] > div { background-color: @INPUT@ !important; border-color: @BORDER@ !important; }
[data-testid="stExpander"] details { border: 1px solid @BORDER@ !important; border-radius: 12px; background-color: @CARD1@ !important; }
[data-testid="stExpander"] summary, [data-testid="stExpander"] summary * { color: @TXT@ !important; }
[data-testid="stVerticalBlockBorderWrapper"] { border-color: @BORDER@ !important; }
[data-testid="stAlert"] { background-color: @ACC@14 !important; border: 1px solid @ACC@55; border-radius: 12px; }
[data-testid="stAlert"] *, [data-testid="stToast"] * { color: @TXT@ !important; }
[data-testid="stToast"] { background-color: @POP@ !important; border: 1px solid @ACC@55; }
[data-testid="stSlider"] [role="slider"] { background-color: @ACC@ !important; }
[data-testid="stSlider"] [data-testid="stThumbValue"], [data-testid="stSliderTickBarMin"], [data-testid="stSliderTickBarMax"] { color: @ACC@ !important; }
[data-testid="stProgress"] [role="progressbar"] > div { background-color: @ACC@ !important; }
[data-testid="stButtonGroup"] button { background-color: @INPUT@ !important; color: @TXT@ !important; border: 1px solid @BORDER@ !important; }
[data-testid="stButtonGroup"] button p { color: inherit !important; }
[data-testid="stButtonGroup"] button[data-testid="stBaseButton-segmented_controlActive"],
[data-testid="stButtonGroup"] button[aria-checked="true"], [data-testid="stButtonGroup"] button[aria-pressed="true"] { background-color: @ACC@ !important; color: @ONACC@ !important; border-color: @ACC@ !important; }
.stButton > button, .stFormSubmitButton > button { background: @BTN@; color: @ACC@; border: 1px solid @ACC@; border-radius: 10px; }
.stButton > button:hover, .stFormSubmitButton > button:hover { background: @ACC@; color: @BTN@; }
.stButton > button[kind="primary"], .stButton > button[data-testid="stBaseButton-primary"] { background: @ACC@; color: @ONACC@; border: 1px solid @ACC@; }
.stButton > button p, .stFormSubmitButton > button p { color: inherit !important; }
[data-baseweb="select"] > div { background-color: @INPUT@ !important; border: 1px solid @BORDER@ !important; }
[data-baseweb="select"] > div *:not(svg):not(path) { background-color: transparent !important; color: @TXT@ !important;
  -webkit-text-fill-color: @TXT@ !important; }
[data-baseweb="select"] svg { fill: @TXT@ !important; }
[data-baseweb="select"] [data-baseweb="tag"] { background-color: @ACC@ !important; }
[data-baseweb="select"] [data-baseweb="tag"] * { color: @ONACC@ !important; -webkit-text-fill-color: @ONACC@ !important; }
[data-testid="stExpander"] summary { background-color: @CARD1@ !important; color: @TXT@ !important; border-radius: 12px; }
[data-testid="stExpander"] summary:hover, [data-testid="stExpander"] details[open] > summary { background-color: @STAT@ !important; }
[data-testid="stExpander"] details > div { background-color: @CARD1@ !important; }
[data-testid="stForm"] { background-color: @CARD1@ !important; border: 1px solid @BORDER@ !important; }
[data-baseweb="radio"] > div:first-child, label[data-baseweb="checkbox"] > div:first-child { filter: hue-rotate(@HUE@); }
[data-baseweb="popover"] *, [data-baseweb="menu"] *, ul[role="listbox"] *, [data-baseweb="calendar"] *,
[data-baseweb="datepicker"] *, [data-baseweb="timepicker"] * { color: @TXT@ !important; }
[data-baseweb="select"] input, [data-baseweb="input"] input, .stTextInput input, .stNumberInput input,
.stTimeInput input, .stDateInput input, textarea { color: @TXT@ !important; -webkit-text-fill-color: @TXT@ !important;
  background-color: @INPUT@ !important; caret-color: @ACC@; }
input::placeholder, textarea::placeholder { color: @MUTE@ !important; -webkit-text-fill-color: @MUTE@ !important; opacity: 1; }
[data-baseweb="select"] > div, .stTextInput > div > div, .stNumberInput > div > div, .stTimeInput > div > div { background-color: @INPUT@ !important; border: 1px solid @BORDER@ !important; }
[data-baseweb="tooltip"], [data-testid="stTooltipContent"] { background-color: @POP@ !important; color: @TXT@ !important; }
[data-baseweb="tooltip"] *, [data-testid="stTooltipContent"] * { color: @TXT@ !important; }
[data-testid="stSidebar"] label, [data-testid="stSidebar"] p, [data-testid="stSidebar"] [data-baseweb="radio"] div { color: @TXT@ !important; }
[data-testid="stColorPicker"] label p, [data-testid="stCheckbox"] label p, [data-testid="stToggle"] label p { color: @TXT@ !important; }
.stAlert p, [data-testid="stAlert"] p { color: @TXT@ !important; }
.zen { background: linear-gradient(135deg, @CARD1@, @STAT@); border: 2px solid @ACC@; border-radius: 26px; padding: 26px 30px;
  box-shadow: 0 6px 24px @ACC@22; margin: 8px 0 14px 0; }
.zen .zr { font-size: 2.05rem; font-weight: 700; color: @ACC@; line-height: 1.25; }
.zen .zl { font-size: 1.4rem; color: @TXT@; margin-top: 8px; font-weight: 500; }
.zen .zs { font-size: 1.02rem; color: @MUTE@; margin-top: 8px; }
[class*="st-key-zenbtn_"] button { min-height: 88px; font-size: 1.15rem !important; font-weight: 700; border-radius: 22px;
  border: 2px solid @ACC@ !important; width: 100%; }
.island { background: #0B0B10; color: #FFFFFF; border-radius: 34px; padding: 14px 24px; display: flex; flex-wrap: wrap;
  gap: 8px 22px; align-items: center; box-shadow: 0 8px 22px rgba(0,0,0,.35); margin: 6px 0 8px 0; }
.island .it { font-size: 1.02rem; color: #F5F5F7; font-weight: 600; }
.island .cap { font-size: .78rem; color: #A1A1AA; width: 100%; letter-spacing: .4px; }
.pre { background: linear-gradient(135deg, @CARD1@, @STAT@); border: 2px solid @ACC@; border-radius: 22px; padding: 18px 22px;
  margin: 8px 0 10px 0; box-shadow: 0 6px 22px @ACC@22; }
.pre .ph { font-size: 1.15rem; font-weight: 700; color: @ACC@; }
.pre .ps { font-size: .98rem; color: @TXT@; margin-top: 4px; }
.ptiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 10px; margin: 10px 0 6px 0; }
.ptile { border-radius: 16px; padding: 12px 14px; border: 1px solid @BORDER@; background: @CARD1@; }
.ptile.on { border: 2px solid @ACC@; background: @ACC@14; }
.ptile .pi { font-size: 1.5rem; }
.ptile .pn { font-size: .85rem; color: @MUTE@; }
.ptile .pv { font-size: 1.15rem; font-weight: 700; color: @TXT@; }
.atbl { width: 100%; border-collapse: collapse; font-size: 0.9rem; background: @CARD1@; border: 1px solid @BORDER@; }
.atbl th { text-align: left; padding: 8px 10px; background: @STAT@; color: @ACC@; border-bottom: 1px solid @ACC@55; white-space: nowrap; }
.atbl td { padding: 7px 10px; color: @TXT@; border-bottom: 1px solid @BORDER@; }
.atbl tr:last-child td { border-bottom: none; }
.card { background: linear-gradient(145deg, @CARD1@, @CARD2@); border: 1px solid @ACC@55; border-radius: 16px; padding: 18px 20px; min-height: 130px; box-shadow: 0 4px 24px @ACC@14; }
.card h4 { margin: 0 0 8px 0; }
.card p { margin: 0; line-height: 1.55; color: @TXT2@; }
.banner { background: @ACC@14; border: 1px solid @ACC@; border-radius: 14px; padding: 14px 18px; margin: 10px 0 10px 0; }
.geo { background: linear-gradient(135deg, @ACC@33, @ACC@14); border: 2px solid @ACC@; border-radius: 16px; padding: 16px 20px; margin: 8px 0 8px 0; font-size: 1.05rem; line-height: 1.5; animation: geopulse 2s ease-in-out infinite; }
@keyframes geopulse { 0%, 100% { box-shadow: 0 0 0 0 @ACC@55; } 50% { box-shadow: 0 0 0 10px @ACC@00; } }
.pill { display: inline-block; border: 1px solid @ACC@; border-radius: 20px; padding: 1px 10px; font-size: 0.78rem; color: @ACC@; margin-left: 6px; }
.brand { font-size: 1.4rem; font-weight: 700; color: @ACC@; }
.stat { background: @STAT@; border: 1px solid @ACC@33; border-radius: 12px; padding: 10px 12px; min-height: 66px; margin-bottom: 8px; }
.stat .sl { font-size: 0.78rem; color: @SUB@; }
.stat .sv { font-size: 1.1rem; font-weight: 600; color: @TXT@; word-break: break-word; }
.sw { display: inline-block; width: 12px; height: 12px; border-radius: 50%; border: 1px solid @ACC@; margin-right: 6px; vertical-align: middle; }
.aibox { background: linear-gradient(145deg, @CARD1@, @CARD2@); border: 1px solid @ACC@66; border-radius: 14px; padding: 12px 16px; margin: 6px 0 10px 0; }
.logl { font-family: monospace; font-size: 0.8rem; color: @LOG@; margin: 2px 0; }
.chathead { display: flex; align-items: center; gap: 8px; background: @STAT@; border: 1px solid @ACC@44; border-radius: 14px 14px 0 0; padding: 10px 16px; color: @ACC@; font-weight: 600; }
.chathead .dot { width: 9px; height: 9px; border-radius: 50%; background: #4CD964; display: inline-block; }
.chathead small { color: @MUTE@; font-weight: 400; }
.chatbox { background: @CHATBG@; border: 1px solid @ACC@33; border-top: none; border-radius: 0 0 14px 14px; padding: 12px 12px 4px 12px; margin-bottom: 8px; }
.crow { display: flex; margin: 5px 0; }
.crow.me { justify-content: flex-end; }
.bub { max-width: 78%; padding: 9px 13px 19px 13px; border-radius: 18px; position: relative; line-height: 1.45; font-size: 0.97rem; word-wrap: break-word; }
.bub.me { background: linear-gradient(135deg, @ACC@, @ACC2@); color: @ONACC@; border-bottom-right-radius: 4px; }
.bub.dv { background: @BUBDV@; border: 1px solid @ACC@33; color: @TXT@; border-bottom-left-radius: 4px; }
.bub .ts { position: absolute; right: 11px; bottom: 3px; font-size: 0.64rem; opacity: 0.65; }
.bub.typing { padding: 12px 16px; }
.bub.typing span { display: inline-block; width: 7px; height: 7px; margin: 0 2px; border-radius: 50%; background: @ACC@; animation: blink 1.2s infinite; }
.bub.typing span:nth-child(2) { animation-delay: 0.2s; }
.bub.typing span:nth-child(3) { animation-delay: 0.4s; }
@keyframes blink { 0%, 80%, 100% { opacity: 0.25; } 40% { opacity: 1; } }
.st-key-aura_voice_bridge { position: absolute !important; left: -9999px !important; width: 1px !important; height: 1px !important; overflow: hidden !important; opacity: 0 !important; }
div[data-testid="stTextInput"]:has(input[placeholder="◈7731◈"]) { position: absolute !important; left: -9999px !important; width: 1px !important; height: 1px !important; overflow: hidden !important; opacity: 0 !important; }
.st-key-aura_ai_bridge { position: absolute !important; left: -9999px !important; width: 1px !important; height: 1px !important; overflow: hidden !important; opacity: 0 !important; }
div[data-testid="stTextInput"]:has(input[placeholder="◈7732◈"]) { position: absolute !important; left: -9999px !important; width: 1px !important; height: 1px !important; overflow: hidden !important; opacity: 0 !important; }
/* floating Aura AI button (every page) */
.st-key-aura_fab { position: fixed !important; right: 14px; bottom: 112px; z-index: 1000001 !important; width: auto !important;
  touch-action: none; user-select: none; -webkit-user-select: none; cursor: grab; }
.st-key-aura_fab:active { cursor: grabbing; }
.st-key-aura_fab button { border-radius: 999px !important; background: linear-gradient(135deg, #D4AF37, #F3D77A) !important; border: 0 !important;
  box-shadow: 0 6px 20px rgba(0,0,0,.35), 0 0 18px rgba(212,175,55,.45) !important; padding: 8px 18px !important; }
.st-key-aura_fab button, .st-key-aura_fab button p, .st-key-aura_fab button span { color: #1B1405 !important; font-weight: 700 !important; }
[data-testid="stPopoverBody"] { max-width: min(94vw, 440px) !important; max-height: 78vh !important; overflow-y: auto !important; }
/* menu button that opens the sidebar: always visible, big enough for a thumb */
[data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"] {
  position: fixed !important; top: 10px !important; left: 10px !important; z-index: 1000002 !important; width: 46px !important;
  height: 46px !important; display: flex !important; align-items: center !important; justify-content: center !important;
  visibility: visible !important; opacity: 1 !important; background-color: @ACC@ !important; border-radius: 14px !important;
  box-shadow: 0 3px 12px rgba(0,0,0,.30) !important; }
[data-testid="stExpandSidebarButton"] *, [data-testid="stSidebarCollapsedControl"] *, [data-testid="collapsedControl"] * {
  color: @ONACC@ !important; fill: @ONACC@ !important; visibility: visible !important; opacity: 1 !important; }
[data-testid="stSidebarCollapseButton"] button, [data-testid="stSidebarHeader"] button { color: @ACC@ !important; }
[data-testid="stSidebarCollapseButton"] svg, [data-testid="stSidebarHeader"] button svg { fill: @ACC@ !important; color: @ACC@ !important; }
[data-testid="stHeader"] { z-index: 999990 !important; }
/* dropdowns: light selected row with dark text, readable control, readable list */
[data-baseweb="select"], [data-baseweb="select"] > div, [data-baseweb="select"] [role="combobox"] { background-color: @INPUT@ !important; }
[data-baseweb="select"] * { background-color: transparent !important; color: @TXT@ !important; -webkit-text-fill-color: @TXT@ !important; }
[data-baseweb="select"] [data-baseweb="tag"], [data-baseweb="select"] [data-baseweb="tag"] * { background-color: @ACC@ !important; color: @ONACC@ !important; -webkit-text-fill-color: @ONACC@ !important; }
[data-baseweb="popover"] *, [data-baseweb="menu"] *, ul[role="listbox"] * { background-color: transparent !important; color: @TXT@ !important; -webkit-text-fill-color: @TXT@ !important; }
[data-baseweb="popover"] > div, [data-baseweb="popover"] [data-baseweb="menu"], ul[role="listbox"] { background-color: @POP@ !important; }
[data-baseweb="popover"] li, [data-baseweb="menu"] li, [role="option"] { background-color: @POP@ !important; }
[data-baseweb="popover"] li:hover, [data-baseweb="menu"] li:hover, [role="option"]:hover, [role="option"][aria-selected="true"], li[aria-selected="true"], li[data-highlighted], [data-highlighted="true"] { background-color: @SEL@ !important; }
[data-testid="stToggle"] label > div:first-child, [data-testid="stToggle"] [data-baseweb="checkbox"] > div:first-child { filter: hue-rotate(@HUE@); }
.st-key-aura_hr_bridge { position: absolute !important; left: -9999px !important; width: 1px !important; height: 1px !important; overflow: hidden !important; opacity: 0 !important; }
div[data-testid="stTextInput"]:has(input[placeholder="◈4417◈"]) { position: absolute !important; left: -9999px !important; width: 1px !important; height: 1px !important; overflow: hidden !important; opacity: 0 !important; }
.aucard { background: #0B0B0B; border: 1.5px solid #D4AF37; border-radius: 20px; padding: 16px 18px; margin: 8px 0 10px 0; box-shadow: 0 6px 22px rgba(212,175,55,.28); }
.aucard .at { color: #D4AF37 !important; font-weight: 700; font-size: 1.05rem; }
.aucard .as { color: #E9DFC0 !important; font-size: .9rem; margin: 4px 0 12px 0; }
.aucard .ab { display: flex; flex-wrap: wrap; gap: 10px; }
.aucard a.abtn { flex: 1 1 180px; text-align: center; text-decoration: none !important; background: #D4AF37; color: #0B0B0B !important; font-weight: 700; padding: 12px 14px; border-radius: 14px; }
.aucard a.abtn.ghost { background: transparent; color: #D4AF37 !important; border: 1.5px solid #D4AF37; }
/* ===== AuraSync Luxury Obsidian: soft glass, champagne hairlines, no harsh outlines (final block, wins over earlier rules) ===== */
.stApp { background-image: @GLOW@ !important; background-attachment: fixed !important; background-repeat: no-repeat !important; }
h1, h2, h3, [data-testid="stHeading"] h2, [data-testid="stHeading"] h3 { font-family: 'Playfair Display', 'Cinzel', serif !important; font-weight: 400 !important; letter-spacing: .06em; color: @CHAMP@ !important; }
[data-testid="stSidebar"] { border-right: 1px solid @GLASSB@ !important; }
[data-testid="stSidebar"] > div:first-child { background-color: @SIDE@ !important; }
hr { border-color: @GLASSB@ !important; }
.brand { font-family: 'Cinzel', 'Playfair Display', serif; font-weight: 400; letter-spacing: .3em; color: @CHAMP@; font-size: 1.15rem; }
/* glass surfaces */
.zen, .pre, .card, .stat, .aibox, .banner, .geo, .ptile, .chatbox, .chathead, .aucard, .atbl,
[data-testid="stExpander"] details, [data-testid="stForm"], [data-testid="stAlert"],
[class*="st-key-gcard"] {
  background: @GLASS@ !important; border: 1px solid @GLASSB@ !important; border-radius: 18px !important;
  box-shadow: @GSHADOW@ !important; -webkit-backdrop-filter: blur(12px); backdrop-filter: blur(12px); }
[class*="st-key-gcard"] { padding: 20px !important; }
.zen { padding: 26px 30px; } .zen .zr { font-family: 'Playfair Display', serif; font-weight: 400; letter-spacing: .04em; color: @CHAMP@; }
.stat { padding: 12px 14px; } .ptile.on { border-color: @GOLDLINE@ !important; background: @GOLDSOFT@ !important; }
.geo { border-color: @GOLDLINE@ !important; } .banner { border-color: @GOLDLINE@ !important; background: @GOLDSOFT@ !important; }
.aucard a.abtn { background: @GRAD@; color: @ONACC@ !important; border-radius: 999px; }
.aucard a.abtn.ghost { background: transparent; color: @CHAMP@ !important; border: 1px solid @GOLDLINE@; }
.aucard .at { color: @CHAMP@ !important; }
.atbl th { border-bottom: 1px solid @GLASSB@; color: @CHAMP@; } .atbl td { border-bottom-color: @GLASSB@; }
[data-testid="stExpander"] details { overflow: hidden; }
[data-testid="stExpander"] summary, [data-testid="stExpander"] details > div, [data-testid="stExpander"] summary:hover, [data-testid="stExpander"] details[open] > summary { background-color: transparent !important; }
[data-testid="stVerticalBlockBorderWrapper"] { border-color: @GLASSB@ !important; }
.stat { border-color: @GLASSB@ !important; } .stat .sl { letter-spacing: .08em; text-transform: uppercase; font-size: .7rem; }
[data-baseweb="select"] > div, .stTextInput > div > div, .stNumberInput > div > div, .stTimeInput > div > div, [data-testid="stChatInput"] > div { border-color: @GLASSB@ !important; border-radius: 12px !important; }
/* buttons: slim pills with a champagne hairline */
.stButton > button, .stFormSubmitButton > button, [data-testid="stNumberInput"] button {
  background: transparent !important; color: @CHAMP@ !important; border: 1px solid @GOLDLINE@ !important; border-radius: 999px !important;
  padding: .4rem 1.1rem; font-weight: 500; letter-spacing: .04em; transition: all .25s ease; }
.stButton > button:hover, .stFormSubmitButton > button:hover { background: @GOLDSOFT@ !important; border-color: @ACC@ !important; color: @CHAMP@ !important; box-shadow: 0 0 18px @GOLDSOFT@; }
.stButton > button[kind="primary"], .stButton > button[data-testid="stBaseButton-primary"] {
  background: @GRAD@ !important; color: @ONACC@ !important; border-color: transparent !important; font-weight: 600; box-shadow: 0 4px 18px @GOLDSOFT@; }
.stButton > button[kind="primary"]:hover, .stButton > button[data-testid="stBaseButton-primary"]:hover { filter: brightness(1.08); color: @ONACC@ !important; }
.stButton > button[kind="primary"] p, .stButton > button[data-testid="stBaseButton-primary"] p { color: @ONACC@ !important; }
[class*="st-key-zenbtn_"] button { min-height: 72px; border: 1px solid @GOLDLINE@ !important; border-radius: 22px !important; }
[data-testid="stButtonGroup"] button { border-radius: 999px !important; border: 1px solid @GLASSB@ !important; background: transparent !important; }
[data-testid="stButtonGroup"] button[data-testid="stBaseButton-segmented_controlActive"], [data-testid="stButtonGroup"] button[aria-checked="true"], [data-testid="stButtonGroup"] button[aria-pressed="true"] {
  background: @GRAD@ !important; color: @ONACC@ !important; border-color: transparent !important; }
[data-baseweb="slider"] div[role="slider"] { box-shadow: 0 0 12px @GOLDLINE@; }
/* luxury header, mode switch, simulator */
.lux-h1 { letter-spacing: .35em; font-weight: 300; font-family: 'Cinzel', 'Playfair Display', serif, sans-serif; text-align: center; color: @CHAMP@; margin-bottom: 0;
  font-size: clamp(1.7rem, 8vw, 2.6rem); padding: .4rem 0 0 .35em; white-space: nowrap; overflow-wrap: normal; word-break: keep-all; line-height: 1.15; }
.lux-gold { color: @CHAMP@; white-space: nowrap; text-shadow: 0 0 22px @GOLDLINE@; }
.lux-sub { letter-spacing: .25em; font-size: .72rem; text-align: center; color: @MUTE@; text-transform: uppercase; margin-top: 4px; margin-bottom: 14px; }
[class*="st-key-flowsw"] { display: flex; justify-content: center; }
[class*="st-key-flowsw"] [data-testid="stButtonGroup"] { justify-content: center; background: @GLASS@; border: 1px solid @GLASSB@; border-radius: 999px; padding: 4px; }
[class*="st-key-simbox"] { position: sticky; top: 0; z-index: 20; background: @GLASS@; border: 1px solid @GLASSB@; border-radius: 18px; padding: 14px 16px 10px 16px; margin-bottom: 14px; -webkit-backdrop-filter: blur(12px); backdrop-filter: blur(12px); }
.sim-h { font-family: 'Playfair Display', serif; font-size: 1.05rem; color: @CHAMP@; letter-spacing: .04em; }
.pdot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: #4CD964; margin-right: 8px; animation: pdot 2s ease-in-out infinite; }
@keyframes pdot { 0%, 100% { box-shadow: 0 0 0 0 rgba(76,217,100,.55); } 50% { box-shadow: 0 0 0 6px rgba(76,217,100,0); } }
.sim-f { font-size: .74rem; color: @MUTE@; letter-spacing: .04em; margin-top: 6px; }
/* hardware cards */
.gc-t { font-family: 'Playfair Display', serif; font-size: 1.1rem; letter-spacing: .05em; color: @CHAMP@; margin-bottom: 6px; }
.gc-sw { height: 46px; border-radius: 14px; margin: 8px 0 10px 0; border: 1px solid @GLASSB@; transition: all .4s ease; }
.gc-temp { text-align: center; font-size: 1.9rem; font-weight: 300; letter-spacing: .04em; color: @TXT@; line-height: 2.4rem; }
@media (prefers-reduced-motion: reduce) { .pdot { animation: none; } }
/* Luxury Glass & Centered Alignment for Selectbox & Inputs */
div[data-baseweb="select"] > div {
  background-color: @INPUT@ !important;
  border: 1px solid @BORDER@ !important;
  border-radius: 12px !important;
  min-height: 48px !important;
  display: flex !important;
  align-items: center !important;
  padding: 0 14px !important;
  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.1) !important;
  transition: all 0.3s ease !important;
}

div[data-baseweb="select"] > div:hover,
div[data-baseweb="select"] > div:focus-within {
  border-color: rgba(212, 175, 55, 0.65) !important;
  box-shadow: 0 0 14px rgba(212, 175, 55, 0.2) !important;
}

div[data-baseweb="select"] [data-testid="stMarkdownContainer"] p,
div[data-baseweb="select"] div,
div[data-baseweb="select"] span {
  color: #EDE6D3 !important;
  font-family: 'Inter', sans-serif !important;
  font-size: 0.95rem !important;
  font-weight: 450 !important;
  line-height: 1 !important;
  letter-spacing: 0.03em !important;
  display: flex !important;
  align-items: center !important;
}

/* Dropdown arrow icon styling & alignment */
div[data-baseweb="select"] svg {
  fill: #E5C378 !important;
  width: 18px !important;
  height: 18px !important;
  opacity: 0.85 !important;
}

/* Field labels subtle champagne styling */
div[data-testid="stSelectbox"] label,
div[data-testid="stTextInput"] label {
  color: #9E9A8E !important;
  font-size: 0.8rem !important;
  letter-spacing: 0.06em !important;
  text-transform: uppercase !important;
  margin-bottom: 6px !important;
}

/* Popover menu options styling */
div[data-baseweb="popover"],
div[data-baseweb="popover"] > div,
div[data-baseweb="menu"],
ul[role="listbox"] {
  background-color: #0E1015 !important;
  border: 1px solid rgba(212, 175, 55, 0.3) !important;
  border-radius: 12px !important;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.7) !important;
}

div[data-baseweb="popover"] li,
ul[role="listbox"] li,
li[role="option"] {
  background-color: transparent !important;
  color: #EDE6D3 !important;
  font-family: 'Inter', sans-serif !important;
  padding: 10px 14px !important;
  font-size: 0.92rem !important;
}

div[data-baseweb="popover"] li:hover,
ul[role="listbox"] li:hover,
li[role="option"]:hover,
li[aria-selected="true"] {
  background: rgba(212, 175, 55, 0.2) !important;
  color: #E5C378 !important;
}
/* FIX 1 - hide Streamlit's "Press Enter to submit form / apply" helper text on every input (gate + app, both themes).
   Primary test-id plus fallbacks for other Streamlit versions. Errors (stAlert) and the password eye button are untouched. */
[data-testid="InputInstructions"],
div[data-testid="InputInstructions"],
[data-testid="stTextInput"] [data-testid="InputInstructions"],
[data-testid="stTextArea"] [data-testid="InputInstructions"],
[data-testid="stNumberInput"] [data-testid="InputInstructions"],
[data-testid="stForm"] [data-testid*="nstructions"],
[data-testid="stTextInput"] [class*="InputInstructions"],
[data-testid="stTextInput"] [class*="WidgetInstructions"],
[data-baseweb="input"] [class*="nstructions"],
[data-baseweb="base-input"] [class*="nstructions"] {
    display: none !important;
    visibility: hidden !important;
}
</style>
"""


def native_light():
    """Streamlit's own theme."""
    try:
        return st.context.theme.type == "light"
    except Exception:
        return False


def is_light():
    """The sidebar Theme switch decides (Dark = black & gold, Light = white)."""
    choice = st.session_state.get("theme_choice")
    if choice in ("dark", "light"):
        return choice == "light"
    return native_light()


def pal():
    return PALETTES["light" if is_light() else "dark"]


LIGHT_DD_CSS = """
<style>
/* FIX 3 - LIGHT PALETTE ONLY: readable light-green selectbox / multiselect / option lists / tab bars.
   Appended after CSS_T (and after the gate CSS) so it wins; "html body" raises specificity over the dark glass rules. */
html body div[data-baseweb="select"]:not(#aura) { background: #FFFFFF !important; background-color: #FFFFFF !important; border: 0 !important;
  border-radius: 12px !important; box-shadow: none !important; }
html body div[data-baseweb="select"]:not(#aura) *:not(svg):not(path) { background-color: transparent !important; background-image: none !important;
  color: #000000 !important; -webkit-text-fill-color: #000000 !important; opacity: 1 !important; }
html body div[data-baseweb="select"]:not(#aura) > div:first-of-type { background: #FFFFFF !important; background-color: #FFFFFF !important; background-image: none !important;
  border: 1px solid @DDLINE@ !important; border-radius: 12px !important; box-shadow: none !important; backdrop-filter: none !important; }
html body div[data-baseweb="select"]:not(#aura) > div:first-of-type:hover { background: #FFFFFF !important; border-color: @DDLINE2@ !important; box-shadow: none !important; }
html body div[data-baseweb="select"]:not(#aura) > div:first-of-type:focus-within { background: #FFFFFF !important; border-color: @DDLINE2@ !important;
  box-shadow: 0 0 0 2px rgba(46, 125, 50, 0.35) !important; }
html body div[data-baseweb="select"] input::placeholder { color: rgba(0, 0, 0, 0.62) !important; -webkit-text-fill-color: rgba(0, 0, 0, 0.62) !important; opacity: 1 !important; }
html body div[data-baseweb="select"] svg, html body div[data-baseweb="select"] svg * { fill: #000000 !important; color: #000000 !important; opacity: 1 !important; }
html body div[data-baseweb="select"] [data-baseweb="tag"] { background-color: @DDSEL@ !important; border: 1px solid @DDLINE@ !important; }
html body div[data-baseweb="select"] [data-baseweb="tag"] * { background-color: transparent !important; color: #000000 !important; -webkit-text-fill-color: #000000 !important; }
/* disabled stays readable (muted, never invisible) */
html body div[data-baseweb="select"][aria-disabled="true"]:not(#aura), html body div[data-baseweb="select"][aria-disabled="true"]:not(#aura) > div:first-of-type,
html body div[data-baseweb="select"]:has(input:disabled):not(#aura), html body div[data-baseweb="select"]:has(input:disabled):not(#aura) > div:first-of-type { background: #F2F2F2 !important; border-color: #A9C7A9 !important; cursor: not-allowed; }
html body div[data-baseweb="select"][aria-disabled="true"] *:not(svg):not(path),
html body div[data-baseweb="select"]:has(input:disabled) *:not(svg):not(path) { color: #3C4B3C !important; -webkit-text-fill-color: #3C4B3C !important; }
/* the open list lives in a portal outside the sidebar / gate card */
html body div[data-baseweb="popover"]:has(ul[role="listbox"]), html body div[data-baseweb="popover"]:has([data-baseweb="menu"]),
html body div[data-baseweb="popover"]:has(ul[role="listbox"]) > div, html body div[data-baseweb="popover"]:has([data-baseweb="menu"]) > div,
html body div[data-baseweb="menu"], html body ul[role="listbox"] {
  background: @DDBG@ !important; background-color: @DDBG@ !important; border: 1px solid @DDLINE@ !important; border-radius: 12px !important;
  box-shadow: 0 10px 26px rgba(30, 80, 30, 0.25) !important; }
html body div[data-baseweb="popover"]:has(ul[role="listbox"]):not(#aura), html body div[data-baseweb="popover"]:has(ul[role="listbox"]):not(#aura) div,
html body div[data-baseweb="popover"]:has([data-baseweb="menu"]):not(#aura), html body div[data-baseweb="popover"]:has([data-baseweb="menu"]):not(#aura) div {
  background-color: @DDBG@ !important; border-right-color: @DDLINE@ !important; box-shadow: none !important; }
html body div[data-baseweb="popover"]:has(ul[role="listbox"]):not(#aura) li div, html body div[data-baseweb="popover"]:has(ul[role="listbox"]):not(#aura) li span,
html body div[data-baseweb="popover"]:has([data-baseweb="menu"]):not(#aura) li div { background-color: transparent !important; }   /* row highlight shows through */
html body div[data-baseweb="popover"]:has(ul[role="listbox"]):not(#aura) ul[role="listbox"] { border: 0 !important; box-shadow: none !important; border-radius: 12px !important; }
html body div[data-baseweb="popover"]:has(ul[role="listbox"]):not(#aura) { box-shadow: 0 10px 26px rgba(30, 80, 30, 0.25) !important; }
html body div[data-baseweb="menu"] *, html body ul[role="listbox"] *, html body div[data-baseweb="popover"]:has(ul[role="listbox"]) * {
  color: #000000 !important; -webkit-text-fill-color: #000000 !important; }
html body div[data-baseweb="menu"] li, html body ul[role="listbox"] li, html body li[role="option"] { background: @DDBG@ !important; background-color: @DDBG@ !important; }
html body div[data-baseweb="menu"] li:hover, html body ul[role="listbox"] li:hover, html body li[role="option"]:hover,
html body li[data-highlighted], html body li[aria-selected="false"]:hover, html body [data-highlighted="true"] { background: @DDHOV@ !important; background-color: @DDHOV@ !important; }
html body li[role="option"][aria-selected="true"], html body ul[role="listbox"] li[aria-selected="true"] { background: @DDSEL@ !important; background-color: @DDSEL@ !important; font-weight: 600 !important; }
html body li[role="option"][aria-disabled="true"], html body ul[role="listbox"] li[aria-disabled="true"] { opacity: .6 !important; cursor: not-allowed; }
/* st.tabs */
html body [data-baseweb="tab-list"]:not(#aura) { background: @DDBG@ !important; border: 1px solid @DDLINE@ !important; border-radius: 12px !important; padding: 2px 4px !important; gap: 2px !important; }
html body button[data-baseweb="tab"]:not(#aura), html body [data-baseweb="tab-list"]:not(#aura) button[role="tab"] { background: transparent !important; color: #000000 !important; border-radius: 8px !important; }
html body button[data-baseweb="tab"]:not(#aura) *, html body [data-baseweb="tab-list"]:not(#aura) button[role="tab"] * { color: #000000 !important; -webkit-text-fill-color: #000000 !important; }
html body button[data-baseweb="tab"]:not(#aura):hover, html body [data-baseweb="tab-list"]:not(#aura) button[role="tab"]:hover { background: @DDHOV@ !important; }
html body button[data-baseweb="tab"]:not(#aura)[aria-selected="true"], html body [data-baseweb="tab-list"]:not(#aura) button[role="tab"][aria-selected="true"] { background: @DDSEL@ !important; font-weight: 600 !important; }
html body button[data-baseweb="tab"]:not(#aura):focus-visible { outline: 2px solid @DDLINE2@ !important; outline-offset: -2px; }
html body [data-baseweb="tab-highlight"]:not(#aura) { background-color: @DDLINE2@ !important; }
html body [data-baseweb="tab-border"]:not(#aura) { background-color: @DDLINE@ !important; }
</style>
"""


def light_dd_css():
    """Light palette only; empty in dark so the dark theme is byte-for-byte what it was."""
    if not is_light():
        return ""
    css = LIGHT_DD_CSS
    for k, v in PALETTES["light"].items():
        css = css.replace("@" + k + "@", v)
    return css


def build_css():
    css = CSS_T
    for k, v in pal().items():
        css = css.replace("@" + k + "@", v)
    return css + light_dd_css()


def themed(page):
    """Colour tokens used by the small HTML components (audio player, chime button)."""
    p = pal()
    return (page.replace("__BG__", p["SIDE"]).replace("__BTN__", p["BTN"])
            .replace("__ACC__", p["ACC"]).replace("__SUB__", p["SUB"])
            .replace("__LINE__", p["GOLDLINE"]).replace("__GLASS__", p["GLASS"]))


def html_table(rows):
    """Theme-aware table."""
    if not rows:
        return
    cols = list(rows[0].keys())
    head = "".join("<th>" + html.escape(str(c)) + "</th>" for c in cols)
    body = "".join("<tr>" + "".join("<td>" + html.escape(str(r[c])) + "</td>" for c in cols) + "</tr>" for r in rows)
    st.markdown('<div style="overflow-x:auto"><table class="atbl"><thead><tr>' + head + "</tr></thead><tbody>" +
                body + "</tbody></table></div>", unsafe_allow_html=True)


def themed_line_chart(values, height=220):
    """Line chart painted with the active theme colours."""
    p = pal()
    values = list(values)
    ch = None
    try:
        import altair as alt
        df = pd.DataFrame({"i": list(range(len(values))), "v": values})
        axis = alt.Axis(title=None, labelColor=p["SUB"], gridColor=p["BORDER"], domainColor=p["BORDER"], tickColor=p["BORDER"])
        ch = (alt.Chart(df).mark_line(color=p["ACC"], strokeWidth=2.2)
              .encode(x=alt.X("i:Q", axis=None), y=alt.Y("v:Q", scale=alt.Scale(zero=False), axis=axis))
              .properties(height=height).configure(background="transparent").configure_view(strokeWidth=0))
    except Exception:
        ch = None
    if ch is not None:
        for kw in ({"theme": None, "use_container_width": True}, {"theme": None, "width": "stretch"}, {"theme": None}):
            try:
                st.altair_chart(ch, **kw)
                return
            except TypeError:
                continue
            except Exception:
                break
    st.line_chart(pd.DataFrame({"bpm": values}), height=height, color=p["ACC"])


def stat(label, value, extra=""):
    return ('<div class="stat"><div class="sl">' + html.escape(label) + '</div><div class="sv">' + extra +
            html.escape(str(value)) + "</div></div>")


# ----------------------------------------------------------------------------
# Static data
# ----------------------------------------------------------------------------
GENRES = ["Pop", "Rock", "Blues", "Hip-Hop", "Jazz", "Classical", "Metal", "Folk", "EDM", "Country",
          "Disco", "OM Mantra", "Chinese Zen", "Lo-Fi Chill", "Ambient Space", "Calm 432Hz"]
INSTRUMENTS = ["Piano", "Flute", "Rain", "Tabla", "Veena", "Singing Bowls", "Strings", "Ocean Waves", "Sitar", "Harp"]
SCENES = {"Warm Glow": "#FFB347", "Candlelight": "#FF8C42", "Aurora": "#5FFBB1", "Sunset": "#FF6B6B",
          "Ocean": "#3FA7D6", "Cool Focus": "#EAF4FF"}
AC_MODES = ["Cool", "Dry", "Fan Only", "Sleep Eco"]
FAN_MODES = {"Off": 0, "Breeze": 1, "Medium": 3, "Turbo": 5}
SPACE_TYPES = ["Living", "Bedroom", "Bath", "Workspace", "Kitchen", "Dining", "Reading", "Outdoor", "Entertainment", "Other"]
SPACE_ICONS = ["🛋️", "🛏️", "🛁", "💼", "🍳", "📚", "🌿", "🎮", "🧘", "🎬", "🚗", "🏠"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
PROTOS_BULB = ["Simulation", "Philips WiZ (UDP)", "Home Assistant / REST"]
PROTOS = ["Simulation", "Home Assistant / REST"]

# (id, icon, name, group, level label, min, max, default, ambience device used by modes)
CATALOG = [
    ("bulb", "💡", "Philips WiZ Smart Bulb", "Lighting", "Brightness", 5, 100, 60, False),
    ("ac", "❄", "Air Conditioner", "Air & Climate", "Temperature (°C)", 16, 30, 24, False),
    ("fan", "🌀", "Ceiling Fan", "Air & Climate", "Speed", 0, 5, 2, False),
    ("curtain", "🪟", "Smart Curtains / Blinds Motor", "Ambience", "Open position (%)", 0, 100, 50, False),
    ("scent", "🌸", "Smart Room Scent Sprayer", "Ambience", "Intensity", 0, 100, 40, True),
    ("diffuser", "💨", "Aroma Oil Diffuser", "Ambience", "Mist level", 0, 100, 50, True),
    ("speaker", "🔊", "Smart Speaker", "Ambience", "Volume", 0, 100, 30, True),
    ("ledstrip", "🌈", "LED Strip Lights", "Lighting", "Brightness", 0, 100, 60, True),
    ("lamp", "🛋", "Smart Table Lamp", "Lighting", "Brightness", 0, 100, 50, True),
    ("dimmer", "🎚", "Smart Dimmer Switch", "Lighting", "Level", 0, 100, 70, False),
    ("switch", "🔘", "Smart Switch", "Power", None, 0, 0, 0, False),
    ("board", "🔲", "Smart Switch Board (4-gang)", "Power", None, 0, 0, 0, False),
    ("plug", "🔌", "Smart Plug", "Power", None, 0, 0, 0, False),
    ("purifier", "🌿", "Air Purifier", "Air & Climate", "Fan speed", 0, 100, 40, True),
    ("humid", "💧", "Humidifier", "Air & Climate", "Mist level", 0, 100, 50, True),
    ("dehum", "🏜", "Dehumidifier", "Air & Climate", "Target humidity (%)", 30, 80, 55, False),
    ("heater", "🔥", "Room Heater", "Air & Climate", "Temperature (°C)", 16, 30, 22, False),
    ("cooler", "🧊", "Air Cooler", "Air & Climate", "Fan speed", 0, 100, 50, False),
    ("thermo", "🌡", "Smart Thermostat", "Air & Climate", "Target (°C)", 16, 30, 24, False),
    ("aqm", "🧪", "Air Quality Monitor", "Air & Climate", None, 0, 0, 0, False),
    ("geyser", "🚿", "Smart Water Heater (Geyser)", "Water", "Temperature (°C)", 30, 75, 45, False),
    ("pump", "🚰", "Smart Water Pump / Tank Controller", "Water", None, 0, 0, 0, False),
    ("wpur", "🫗", "Smart Water Purifier", "Water", None, 0, 0, 0, False),
    ("leak", "💦", "Water Leak Sensor", "Water", None, 0, 0, 0, False),
    ("irrig", "🌱", "Garden Irrigation Controller", "Outdoor", "Duration (min)", 1, 60, 10, False),
    ("tv", "📺", "Smart TV", "Entertainment", "Volume", 0, 100, 25, False),
    ("projector", "🎞", "Smart Projector", "Entertainment", "Brightness", 0, 100, 70, False),
    ("mattress", "🛏", "Smart Mattress Warmer", "Sleep", "Warmth", 0, 100, 30, True),
    ("sleepsens", "😴", "Sleep Tracker Pad", "Sleep", None, 0, 0, 0, False),
    ("lock", "🔐", "Smart Door Lock", "Security", None, 0, 0, 0, False),
    ("camera", "📹", "CCTV / Security Camera", "Security", None, 0, 0, 0, False),
    ("doorbell", "🔔", "Video Doorbell", "Security", None, 0, 0, 0, False),
    ("smoke", "🚨", "Smoke / Gas Detector", "Security", None, 0, 0, 0, False),
    ("garage", "🚗", "Garage Door Opener", "Security", None, 0, 0, 0, False),
    ("vacuum", "🤖", "Robot Vacuum", "Appliances", "Suction", 0, 100, 60, False),
    ("washer", "🧺", "Smart Washing Machine", "Appliances", None, 0, 0, 0, False),
    ("fridge", "🥶", "Smart Refrigerator", "Appliances", "Temperature (°C)", 1, 8, 4, False),
    ("coffee", "☕", "Smart Coffee Maker", "Appliances", "Strength", 1, 10, 5, False),
    ("kettle", "🫖", "Smart Kettle", "Appliances", "Temperature (°C)", 40, 100, 90, False),
    ("ev", "⚡", "EV Charger", "Energy", "Charge limit (%)", 50, 100, 80, False),
    ("solar", "☀", "Solar Inverter Monitor", "Energy", None, 0, 0, 0, False),
    ("pet", "🐾", "Smart Pet Feeder", "Pets", None, 0, 0, 0, False),
    ("aquarium", "🐠", "Aquarium Controller", "Pets", "Light (%)", 0, 100, 60, False),
    ("towel", "♨", "Towel Warmer", "Water", "Warmth", 0, 100, 50, False),
    ("spatial", "🎶", "Spatial Speaker", "Ambience", "Volume", 0, 100, 30, True),
    ("focusaudio", "🎧", "Focus Audio", "Ambience", "Volume", 0, 100, 25, True),
    ("soundpad", "🎼", "Acoustic Sound Pad", "Ambience", "Volume", 0, 100, 25, True),
    ("tasklight", "🔦", "Task Lights", "Lighting", "Brightness", 0, 100, 80, False),
    ("ambilight", "🪔", "Ambient Lighting", "Lighting", "Brightness", 0, 100, 40, False),
    ("wallsw", "🔘", "Smart Wall Switches", "Power", None, 0, 0, 0, False),
]
CAT = {c[0]: c for c in CATALOG}
AMB = [c[0] for c in CATALOG if c[8]]
UNIT = {"bulb": "%", "ac": " °C", "curtain": "% open", "fan": "", "geyser": " °C", "heater": " °C", "thermo": " °C",
        "fridge": " °C", "kettle": " °C", "coffee": "", "irrig": " min"}
# Pre-configured zones: name -> (icon, type, [(device type, label)])
DEFAULT_SPACES = {
    "Living Lounge": ("🛋️", "Living", [("bulb", "Bulbs"), ("fan", "Fan"), ("ac", "AC"), ("spatial", "Spatial Speaker"),
                                       ("diffuser", "Scent Diffuser")]),
    "Master Suite": ("🛏️", "Bedroom", [("bulb", "Bulbs"), ("fan", "Fan"), ("ac", "AC"), ("diffuser", "Scent Diffuser"),
                                       ("curtain", "Smart Curtains"), ("mattress", "Smart Mattress")]),
    "En-Suite Bath": ("🛁", "Bath", [("geyser", "Smart Water Heater / Geyser"), ("towel", "Towel Warmer"),
                                     ("ambilight", "Ambient Lighting")]),
    "Work Studio": ("💼", "Workspace", [("bulb", "Task Bulbs"), ("fan", "Fan"), ("ac", "AC"), ("purifier", "Air Purifier"),
                                        ("focusaudio", "Focus Audio")]),
    "Kitchen": ("🍳", "Kitchen", [("coffee", "Smart Coffee Brewer"), ("wallsw", "Smart Wall Switches"),
                                  ("tasklight", "Task Lights")]),
    "Reading Room": ("📚", "Reading", [("bulb", "Warm Bulbs"), ("ac", "AC"), ("soundpad", "Acoustic Sound Pad"),
                                       ("curtain", "Curtains")]),
    "Dining Area": ("🍽️", "Dining", [("bulb", "Dining Bulbs"), ("fan", "Fan"), ("ac", "AC")]),
}

DEFAULT_MODES = {
    "Deep Meditation": {"bulb": "#2B1B5E", "bright": 25, "fan": 1, "ac": 24, "curtain": 20, "genre": "OM Mantra",
                        "extras": ["scent", "purifier", "speaker", "diffuser"]},
    "Sleep": {"bulb": "#3A1F00", "bright": 10, "fan": 1, "ac": 25, "curtain": 0, "genre": "Ambient Space",
              "extras": ["purifier", "mattress"]},
    "Focus": {"bulb": "#FFF4E0", "bright": 90, "fan": 2, "ac": 23, "curtain": 70, "genre": "Lo-Fi Chill",
              "extras": ["purifier", "speaker", "lamp"]},
    "Relax Evening": {"bulb": "#FFB347", "bright": 55, "fan": 2, "ac": 24, "curtain": 30, "genre": "Jazz",
                      "extras": ["scent", "speaker"]},
    "Energize": {"bulb": "#FFFFFF", "bright": 100, "fan": 4, "ac": 22, "curtain": 100, "genre": "EDM",
                 "extras": ["speaker", "ledstrip"]},
    "Zen Garden": {"bulb": "#9FD8B0", "bright": 60, "fan": 2, "ac": 24, "curtain": 60, "genre": "Chinese Zen",
                   "extras": ["scent", "speaker", "purifier", "diffuser"]},
    "Deep Calm Studio": {"bulb": "#0B3C7A", "bright": 30, "fan": 1, "ac": 22, "curtain": 30, "genre": "Calm 432Hz",
                         "extras": ["purifier", "focusaudio"]},
    "Wind-Down Sleep": {"bulb": "#3A1F00", "bright": 8, "fan": 1, "ac": 21, "curtain": 0, "genre": "Calm 432Hz",
                        "extras": ["purifier", "mattress"]},
    "Cinema Night": {"bulb": "#3B1F6B", "bright": 15, "fan": 2, "ac": 23, "curtain": 0, "genre": "Classical",
                     "extras": ["speaker"]},
    "Reading": {"bulb": "#FFE2B8", "bright": 72, "fan": 1, "ac": 24, "curtain": 60, "genre": "Classical",
                "extras": ["lamp", "speaker"]},
    "Neutral Family Ambience": {"bulb": "#FFE6C7", "bright": 55, "fan": 2, "ac": 24, "curtain": 50, "genre": "Ambient Space",
                                "extras": ["speaker"]},
}
NEUTRAL_MODE = "Neutral Family Ambience"
CINEMA_MODE = "Cinema Night"
# Room personas: personal sanctuaries follow one person, shared family zones protect the whole family
PERSONAL_ZONES = ("Work Studio", "Master Suite", "En-Suite Bath", "Reading Room")
SHARED_ZONES = ("Living Lounge", "Kitchen", "Dining Area")
BASE_MIX = {k: 0 for k in INSTRUMENTS}

# Device behaviour the AI applies when the detected body state changes: (device, on, level, reason)
STATE_RULES = {
    "sleep": [("bulb", False, None, "lights off for deep sleep"), ("ledstrip", False, None, "LED strip off"),
              ("lamp", False, None, "table lamp off"),
              ("curtain", True, 0, "closing the curtains for darkness and deep sleep"),
              ("lock", True, None, "locking the door for the night"),
              ("tv", False, None, "switching the TV off"), ("projector", False, None, "projector off"),
              ("coffee", False, None, "coffee maker off"), ("kettle", False, None, "kettle off"),
              ("geyser", False, None, "water heater off while you sleep"),
              ("speaker", True, 8, "very low volume for sleep sounds"),
              ("mattress", True, 30, "warming the bed gently")],
    "wake": [("bulb", True, 60, "warm, gentle light to wake you softly"),
             ("curtain", True, 100, "opening the curtains to welcome daylight"),
             ("geyser", True, 45, "heating water for your morning"), ("coffee", True, 5, "brewing your coffee"),
             ("speaker", True, 25, "soft morning music"), ("mattress", False, None, "bed warmer off"),
             ("lock", False, None, "unlocking the door")],
    "stress": [("curtain", True, 25, "softening the daylight to calm you"),
               ("tv", False, None, "TV off to reduce stimulation"), ("speaker", True, 30, "calming sounds on"),
               ("scent", True, 60, "calming scent on")],
    "active": [("curtain", True, 90, "letting daylight in for energy"), ("speaker", True, 40, "energising volume")],
    "relaxed": [("speaker", True, 30, "relaxed background volume")],
}
STATE_EN = {"sleep": "asleep", "wake": "waking up", "stress": "stressed", "active": "active", "relaxed": "relaxed"}


# ----------------------------------------------------------------------------
# Device registry, connection layer and logging
# ----------------------------------------------------------------------------
def log(text):
    ss = st.session_state
    ss.log = ([{"t": datetime.now().strftime("%H:%M:%S"), "x": text}] + ss.log)[:60]


def new_device(cid, name, room):
    ss = st.session_state
    c = CAT[cid]
    ss.uid += 1
    return {"uid": ss.uid, "cid": cid, "name": name, "room": room, "on": False,
            "lvl": c[7] if c[4] else 0, "color": "#FFB347", "proto": "Simulation", "addr": "", "token": "",
            "status": "connected", "last": "", "rev": 0}


HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def valid_hex(c):
    return isinstance(c, str) and bool(HEX_RE.match(c.strip()))


def safe_hex(c, fallback="#FFB347"):
    return c.strip() if valid_hex(c) else fallback


def hex_rgb(h):
    h = safe_hex(h).lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def valid_mode_name(n):
    return isinstance(n, str) and bool(re.fullmatch(r"\w[\w \-&'.()]{0,39}", n.strip()))


def full_mix(m=None):
    """Always returns all 10 instruments as clamped ints (0-100)."""
    m = m if isinstance(m, dict) else {}
    out = {}
    for k in INSTRUMENTS:
        try:
            v = int(float(m.get(k, 0)))
        except (TypeError, ValueError):
            v = 0
        out[k] = max(0, min(100, v))
    return out


def any_mix(m):
    return isinstance(m, dict) and any(full_mix(m).values())


def wiz_send(addr, payload):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(1.0)
    try:
        s.sendto(json.dumps(payload).encode("utf-8"), (addr, 38899))
        data, _ = s.recvfrom(2048)
        return json.loads(data.decode("utf-8"))
    finally:
        s.close()


def push(dev):
    """Send the device's current state to the real device (no-op for Simulation)."""
    if dev["proto"] == "Simulation" or dev["status"] != "connected" or not dev["addr"]:
        return
    if dev["proto"] == "Home Assistant API":
        ha_push(dev)
        return
    if native_on():                     # the iPhone app sends the command from inside the home network
        c = native_dev_cmd(dev)
        if c:
            native_enqueue(c)
            dev["last"] = "sent to phone " + datetime.now().strftime("%H:%M:%S")
        return
    try:
        if dev["proto"].startswith("Philips"):
            r, g, b = hex_rgb(dev["color"])
            params = {"state": bool(dev["on"]), "dimming": max(10, int(dev["lvl"])), "r": r, "g": g, "b": b}
            wiz_send(dev["addr"], {"id": 1, "method": "setPilot", "params": params})
        else:
            body = {"source": "AuraSync", "device": dev["name"], "type": dev["cid"], "room": dev["room"],
                    "state": "on" if dev["on"] else "off", "level": dev["lvl"], "color": dev["color"],
                    "mode": dev.get("acmode") or dev.get("fanmode") or ""}
            hdr = {"Authorization": "Bearer " + dev["token"]} if dev["token"] else {}
            requests.post(dev["addr"], json=body, headers=hdr, timeout=2)
        dev["last"] = "sent " + datetime.now().strftime("%H:%M:%S") + (" via cloud relay" if st.session_state.conn["mode"] == "away" else " via local mesh")
    except Exception as e:
        dev["status"] = "offline"
        dev["last"] = type(e).__name__


def connect_device(dev):
    """Handshake with the device. Simulation always succeeds; real transports are really probed."""
    if native_on() and dev["proto"] != "Simulation":
        dev["status"], dev["last"] = "connected", "via phone (not verified)"
        return True
    if dev["proto"] == "Home Assistant API":
        ha = ha_cfg()
        try:
            r = requests.get(ha["url"] + "/api/states/" + str(dev["addr"]), headers={"Authorization": "Bearer " + ha["token"]},
                             timeout=4) if ha and ha_url_safe(ha["url"]) else None
            dev["status"] = "connected" if (r is not None and r.status_code < 400) else "offline"
            dev["last"] = "Home Assistant answered" if dev["status"] == "connected" else "no answer from Home Assistant"
        except Exception as e:
            dev["status"], dev["last"] = "offline", type(e).__name__
        return dev["status"] == "connected"
    try:
        if dev["proto"] == "Simulation":
            dev["status"], dev["last"] = "connected", "simulated device ready"
        elif dev["proto"].startswith("Philips"):
            res = wiz_send(dev["addr"], {"id": 1, "method": "getPilot", "params": {}})
            ok = bool(res)
            dev["status"], dev["last"] = ("connected" if ok else "offline"), ("WiZ answered" if ok else "no answer")
        else:
            hdr = {"Authorization": "Bearer " + dev["token"]} if dev["token"] else {}
            r = requests.get(dev["addr"], headers=hdr, timeout=2)
            dev["status"] = "connected" if r.status_code < 500 else "offline"
            dev["last"] = "HTTP " + str(r.status_code)
    except Exception as e:
        dev["status"], dev["last"] = "offline", type(e).__name__
    return dev["status"] == "connected"


def set_dev(dev, on=None, lvl=None, color=None, why=""):
    """Single entry point for every device change."""
    before = (dev["on"], dev["lvl"], dev["color"])
    if on is not None:
        dev["on"] = bool(on)
    if lvl is not None:
        c = CAT[dev["cid"]]
        try:
            dev["lvl"] = max(c[5], min(c[6], int(lvl))) if c[4] else 0
        except (TypeError, ValueError):
            pass
    if color is not None and valid_hex(color):
        dev["color"] = color.strip()
    changed = before != (dev["on"], dev["lvl"], dev["color"])
    if changed:
        dev["rev"] = dev.get("rev", 0) + 1
        push(dev)
        if why:
            c = CAT[dev["cid"]]
            state = "ON" if dev["on"] else "OFF"
            lv = (" " + str(dev["lvl"]) + UNIT.get(dev["cid"], "%")) if (dev["on"] and c[4]) else ""
            log(c[1] + " " + dev["name"] + ": " + state + lv + " - " + why)
    return changed


# ----------------------------------------------------------------------------
# Spaces, presence (Follow-Me), holds, geofence and routines
# ----------------------------------------------------------------------------
CUT_CIDS = {"bulb", "tasklight", "ambilight", "lamp", "ledstrip", "dimmer", "fan", "ac", "scent", "diffuser",
            "speaker", "spatial", "focusaudio", "soundpad"}
GLOBAL_CIDS = {"geyser", "coffee", "lock", "kettle", "tv", "projector"}
BULBLIKE = ("bulb", "tasklight", "ambilight")
EQUIV = {"spatial": "speaker", "focusaudio": "speaker", "soundpad": "speaker", "diffuser": "scent",
         "tasklight": "bulb", "ambilight": "bulb"}
CALM_ROOMS = ("Work Studio",)
# Spaces that built-in automations look up by name (geofence, routines, calm mode)
PROTECTED_SPACES = ("En-Suite Bath", "Master Suite", "Work Studio")
CALM_MODE = "Deep Calm Studio"
WIND_MODE = "Wind-Down Sleep"
HOLD_FOREVER = 10 ** 12
UWB_DEVICES = ["Apple Watch Series 6", "Apple Watch Series 7", "Apple Watch Series 8", "Apple Watch Series 9",
               "Apple Watch Series 10", "Apple Watch Ultra", "iPhone (UWB)", "Samsung Galaxy S-Ultra", "UWB Tag"]
BLE_DEVICES = ["Oura Ring", "Ultrahuman Ring", "Fitness Band (no UWB)"]


def engine_of(name):
    return "UWB" if name in UWB_DEVICES else "BLE"


def space_devs(name):
    ss = st.session_state
    sp = ss.spaces.get(name)
    if not sp:
        return []
    ids = set(sp["devices"])
    return [d for d in ss.fleet if d["uid"] in ids]


def assign_device(dev, room):
    ss = st.session_state
    for sp in ss.spaces.values():
        if dev["uid"] in sp["devices"]:
            sp["devices"].remove(dev["uid"])
    ss.spaces[room]["devices"].append(dev["uid"])
    dev["room"] = room


def find_dev(room, cid):
    return next((d for d in space_devs(room) if d["cid"] == cid), None)


def held(d):
    return st.session_state.holds.get(d["uid"], 0) > time.time()


def hold(d, secs):
    st.session_state.holds[d["uid"]] = time.time() + secs


def scope_devs():
    """Devices that the current atmosphere / automation is allowed to touch."""
    ss = st.session_state
    if ss.cfg["follow_me"] and ss.presence["room"] in ss.spaces:
        return space_devs(ss.presence["room"])
    return list(ss.fleet)


def eff_mode():
    """The atmosphere that is really playing around you."""
    ss = st.session_state
    if ss.conn["mode"] == "home":
        return ss.room_mode.get(ss.presence["room"], ss.active_mode)
    return ss.active_mode


def first_name():
    p = st.session_state.get("profile")
    return p["name"].split()[0] if p and p.get("name") else "Mani"


def eta_min(km):
    return int(round(km * 3))


def apply_mode(name, why=True, devs=None, set_active=True):
    """Sync bulbs, AC, fan, curtains and ambient devices to a mode."""
    ss = st.session_state
    env = ss.modes[name]
    if set_active:
        ss.active_mode = name
        ss.cfg["mix"] = full_mix(env["mix"]) if any_mix(env.get("mix")) else full_mix(ss.cfg.get("mix"))
    pool = scope_devs() if devs is None else devs
    extras = env.get("extras", [])
    for d in pool:
        if held(d):
            continue
        c = d["cid"]
        if c in BULBLIKE:
            set_dev(d, env.get("bulb_on", True), env.get("bright", 60), safe_hex(env.get("bulb")))
        elif c == "ac":
            set_dev(d, env.get("ac_on", True), env["ac"])
        elif c == "fan":
            set_dev(d, env.get("fan_on", True), env["fan"])
        elif c == "curtain":
            set_dev(d, True, env.get("curtain", 50))
        elif CAT[c][8]:
            set_dev(d, c in extras or EQUIV.get(c) in extras)
    if why:
        where = (" in " + ss.presence["room"]) if (devs is None and ss.cfg["follow_me"]) else ""
        log("🎼 Atmosphere '" + name + "' applied (" + env["genre"] + ")" + where)


def apply_rules(state):
    ss = st.session_state
    h = datetime.now().hour
    scope = [d for d in scope_devs() if d["room"] not in ss.room_mode]
    for cid, on, lvl, why in STATE_RULES.get(state, []):
        pool = ss.fleet if cid in GLOBAL_CIDS else scope
        for d in pool:
            if held(d) or EQUIV.get(d["cid"], d["cid"]) != cid:
                continue
            set_dev(d, on, lvl, why=why)
    if state == "relaxed":
        for d in scope:
            if d["cid"] == "curtain" and not held(d):
                day = 7 <= h < 17
                set_dev(d, True, max(d["lvl"], 70) if day else 30,
                        why="keeping daylight in" if day else "evening privacy and calm")


def fine_tune(r, state):
    """Continuously nudge AC / fan from skin temperature and trim the water heater schedule."""
    ss = st.session_state
    ss.skin_hist = (ss.skin_hist + [r["skin"]])[-5:]
    skin = sum(ss.skin_hist) / len(ss.skin_hist)
    env = ss.modes[ss.active_mode]
    dac, dfan, why = int(env["ac"]), int(env["fan"]), "back to the atmosphere baseline"
    if skin >= 34.4:
        dac, dfan = dac - 1, min(5, dfan + 1)
        why = "body warmth {:.1f} °C is high: a little more cooling".format(skin)
    elif skin <= 32.9:
        dac, dfan = dac + 1, max(0, dfan - 1)
        why = "body warmth {:.1f} °C is low: easing the chill".format(skin)
    for d in scope_devs():
        if held(d) or d["room"] in ss.room_mode:
            continue
        if d["cid"] == "ac" and d["on"]:
            set_dev(d, lvl=dac, why=why)
        elif d["cid"] == "fan" and d["on"]:
            set_dev(d, lvl=dfan, why=why)
    for d in ss.fleet:
        if d["cid"] == "geyser" and state == "sleep" and 5 <= datetime.now().hour < 7 and not d["on"] and not held(d):
            set_dev(d, True, 45, why="pre-heating water before your usual wake-up")


def room_persona(name):
    sp = st.session_state.spaces.get(name, {})
    if sp.get("persona") in ("personal", "shared"):
        return sp["persona"]
    if name in SHARED_ZONES:
        return "shared"
    if name in PERSONAL_ZONES:
        return "personal"
    return "shared" if sp.get("type") in ("Living", "Kitchen", "Dining", "Entertainment") else "personal"


def family_blocked():
    """Guest Mode, or a shared room with 2+ people."""
    ss = st.session_state
    return bool(ss.get("guest_mode")) or ss.presence["room"] in ss.get("family_lock", ())


def clear_room_override(room):
    ss = st.session_state
    if room not in ss.get("family_lock", ()):
        ss.room_mode.pop(room, None)


def automation_step(res, r):
    """Aura Companion: acts on devices when the detected state changes."""
    ss = st.session_state
    if family_blocked():
        return False
    state, changed = res["state"], False
    calm = bool(ss.room_mode.get(ss.presence["room"]))
    if state != ss.last_state:
        ss.last_state = state
        log("🌿 Aura noticed you are " + STATE_EN[state] + " - " + res["reason"])
        target = state_mode(state)
        if target != ss.active_mode:
            if calm:
                ss.active_mode = target
            else:
                apply_mode(target)
                changed = True
        if not calm:
            apply_rules(state)
    fine_tune(r, state)
    return changed


# ---- Follow-Me and room-isolated calm
def move_user(room):
    ss = st.session_state
    old = ss.presence["room"]
    if room == old or room not in ss.spaces:
        return
    ss.presence["room"] = room
    eng = engine_of(ss.cfg["tracker"])
    if not ss.cfg["follow_me"]:
        log("📍 " + eng + " tracking: you moved " + old + " → " + room + " (Follow-Me is off)")
        return
    if ss.get("guest_mode"):
        log("📍 Guest Mode: you moved " + old + " → " + room + ". No shutdowns, the home stays welcoming for everyone")
        return
    eco = ss.cfg["cut_mode"] == "Eco standby"
    cut = woke = 0
    for d in ([] if old in ss.get("family_lock", ()) else space_devs(old)):
        if d["cid"] in CUT_CIDS and not held(d):
            if d["cid"] == "ac" and eco:
                cut += 1 if set_dev(d, True, 27) else 0
            else:
                cut += 1 if set_dev(d, False) else 0
    clear_room_override(old)
    if room in ss.get("family_lock", ()):
        log("📍 " + old + " → " + room + ": the family is here, so the room keeps its Neutral Family Ambience")
        return
    target = space_devs(room)
    before = {d["uid"]: (d["on"], d["lvl"], d["color"]) for d in target}
    if ss.cfg["auto_mode"] and ss.spaces[room].get("preset"):
        apply_preset(room, why=False)
        label = "its saved room default"
    else:
        apply_mode(ss.active_mode, why=False, devs=target, set_active=False)
        label = "'" + ss.active_mode + "'"
    woke = sum(1 for d in target if before[d["uid"]] != (d["on"], d["lvl"], d["color"]))
    log("📍 " + eng + " tracking: " + old + " → " + room + ". Follow-Me: " + str(cut) + " device(s) in " + old +
        (" dropped to eco standby/off" if eco else " switched off") + ", " + str(woke) + " device(s) in " + room +
        " woke up with " + label)


def on_sim_move(key):
    ss = st.session_state
    r = ss.get(key)
    if r not in ss.spaces:
        ss.room_rev = ss.get("room_rev", 0) + 1
        return
    move_user(r)
    set_active_room(ss.presence["room"])
    ss.flash = "📍 " + tr_room(ss.presence["room"])


def room_calm_step(hr):
    """Heart rate above 85 BPM in the Work Studio calms ONLY that room."""
    ss, cfg = st.session_state, st.session_state.cfg
    room = ss.presence["room"]
    if family_blocked():
        return None
    active = cfg["auto_mode"] and cfg["calm_on"] and ss.conn["mode"] == "home"
    cur = ss.room_mode.get(room)
    if room in CALM_ROOMS and active and hr > 85 and cur != CALM_MODE:
        ss.room_mode[room] = CALM_MODE
        apply_mode(CALM_MODE, why=False, devs=space_devs(room), set_active=False)
        log("🌊 " + room + " calm mode ON (heartbeat " + str(hr) + " bpm): deep ocean blue light, 432Hz ambient sound, "
            "22 °C. Only " + room + " changed; the rest of the house is untouched.")
        return "on"
    if cur == CALM_MODE and (hr <= 80 or not active or room not in CALM_ROOMS):
        ss.room_mode.pop(room, None)
        apply_mode(ss.active_mode, why=False, devs=space_devs(room), set_active=False)
        log("🌤 " + room + " back to your normal atmosphere (" + ss.active_mode + ")")
        return "off"
    return None


# ---- Remote control and smart geofence
def switch_conn(mode):
    ss = st.session_state
    if mode not in ("home", "away") or mode == ss.conn["mode"]:
        return
    ss.conn["mode"] = mode
    ss.geo = {"state": "idle", "chimed": False, "km": 20, "rev": ss.geo.get("rev", 0) + 1}
    if mode == "home":
        for uid, ts in list(ss.holds.items()):
            if ts >= HOLD_FOREVER:
                del ss.holds[uid]
        log("🏠 Welcome home: back on local control (Matter / Wi-Fi mesh)")
    else:
        log("🚗 You are away: commands now use the 4G/5G cloud relay")


def set_conn():
    ss = st.session_state
    switch_conn(ss.get("conn_sel", ss.conn["mode"]))


# Luxury arrival pre-conditioning: (room, device type, target)
GEO_PARTS = {"geyser": ("En-Suite Bath", "geyser", 42), "ac": ("Master Suite", "ac", 22), "fan": ("Master Suite", "fan", 2)}
GEO_ICON = {"geyser": "🚿", "ac": "❄️", "fan": "🌀"}
GEO_NAME = {"geyser": "Geyser · En-Suite Bath", "ac": "AC · Master Suite", "fan": "Ceiling Fan · Master Suite"}


def geo_dev(part):
    room, cid, _ = GEO_PARTS[part]
    return find_dev(room, cid)


def geo_autorun(auto=True):
    """Zero-touch: pre-condition the home through the cloud relay and lock it against competing ambient loops."""
    ss = st.session_state
    for part, (room, cid, lvl) in GEO_PARTS.items():
        d = geo_dev(part)
        if d:
            set_dev(d, True, lvl, why="☁️ cloud relay: luxury arrival pre-conditioning")
            hold(d, HOLD_FOREVER)
    ss.geo.update(state="active", chimed=False, auto=bool(auto))
    log(("✨ Zero-touch: " if auto else "✅ You confirmed: ") + "Geyser 42 °C, Master Suite AC 22 °C and Ceiling Fan speed 2 "
        "were switched on through the cloud relay")
    ss.flash = "✨ " + t("geo_started")


def geo_check():
    ss = st.session_state
    km = int(ss.geo.get("km", 20))
    if ss.conn["mode"] != "away":
        return
    if km <= 5 and ss.geo["state"] == "idle":
        if ss.cfg.get("geo_auto", True):
            geo_autorun(True)
        else:
            ss.geo.update(state="pending", chimed=False)
            log("📍 Geofence: you entered the 5 km / 15 min zone. Waiting for your confirmation; nothing was switched on")
    elif km > 5 and ss.geo["state"] in ("pending", "dismissed", "standby"):
        ss.geo.update(state="idle", chimed=False)


def cb_geo_slider(key):
    ss = st.session_state
    try:
        ss.geo["km"] = max(0, min(20, int(ss.get(key, ss.geo["km"]))))
    except (TypeError, ValueError):
        return
    geo_check()


def geo_jump(km):
    ss = st.session_state
    ss.geo["km"] = int(km)
    ss.geo["rev"] = ss.geo.get("rev", 0) + 1   # rebuilds the slider with the new value
    geo_check()


def cb_geo_auto(key):
    ss = st.session_state
    ss.cfg["geo_auto"] = bool(ss.get(key))
    if ss.cfg["geo_auto"] and ss.conn["mode"] == "away" and ss.geo["state"] == "pending":
        geo_autorun(True)


def geo_part_set(part, on):
    """One-touch override: switch ONE appliance off (or back on)."""
    ss = st.session_state
    d = geo_dev(part)
    if d is None:
        return
    target = GEO_PARTS[part][2]
    set_dev(d, bool(on), target if on else None, why="☁️ cloud relay: " + ("switched back on" if on else "switched off by you"))
    hold(d, HOLD_FOREVER)
    log(GEO_ICON[part] + " " + GEO_NAME[part] + (" back ON" if on else " turned OFF alone; the other appliances keep running"))
    ss.flash = GEO_ICON[part] + " " + t("geo_on_again" if on else "geo_off_alone", n=GEO_NAME[part].split(" · ")[0])


def geo_cancel_all():
    ss = st.session_state
    for part in GEO_PARTS:
        d = geo_dev(part)
        if d:
            set_dev(d, False, why="☁️ cloud relay: arrival routine cancelled")
            ss.holds.pop(d["uid"], None)
    ss.geo.update(state="standby", chimed=True)
    log("🛑 Arrival routine cancelled: all pre-conditioned appliances are OFF and the home is back on standby")
    ss.flash = "🛑 " + t("geo_cancelled")


def geo_restart():
    st.session_state.geo["state"] = "idle"
    geo_check()


def geo_confirm():
    geo_autorun(False)


def geo_dismiss():
    ss = st.session_state
    ss.geo["state"] = "dismissed"
    log("❌ Geofence alert dismissed: all home appliances stay on standby")
    ss.flash = "❌ " + t("geo_dismissed")


# ---- Daily routines
def fmt12(tm):
    return tm.strftime("%I:%M %p")


def shift_t(tm, minutes):
    return (datetime.combine(date.today(), tm) + timedelta(minutes=minutes)).time()


def default_routines():
    return [
        {"id": "wake", "kind": "wake_bath", "name": "Morning Wake-Up & Hot Bath", "enabled": True,
         "wake": dtime(6, 30), "bath": dtime(6, 45), "offset": 20},
        {"id": "night", "kind": "wind_down", "name": "Night Wind-Down Routine", "enabled": True,
         "sleep": dtime(22, 30), "offset": 30},
    ]


def routine_events(r):
    off = int(r.get("offset", 0))
    if r["kind"] == "wake_bath":
        return [("geyser", shift_t(r["bath"], -off)), ("wake", r["wake"])]
    if r["kind"] == "wind_down":
        return [("wind", shift_t(r["sleep"], -off))]
    return [("custom", shift_t(r["time"], -off))]


def routine_logic(r):
    off = int(r.get("offset", 0))
    if r["kind"] == "wake_bath":
        return ("Geyser will automatically switch ON at " + fmt12(shift_t(r["bath"], -off)) + " so hot water is ready exactly at " +
                fmt12(r["bath"]) + " without manual switching. At " + fmt12(r["wake"]) +
                ", Master Suite curtains open and the bulbs rise gently.")
    if r["kind"] == "wind_down":
        return ("At " + fmt12(shift_t(r["sleep"], -off)) + ", Master Suite AC will set to 21°C, smart curtains will close (0%), "
                "and 432Hz ambient sleep audio will begin fading in.")
    names = ", ".join(d["name"] for d in st.session_state.fleet if d["uid"] in r.get("uids", [])) or "-"
    return "At " + fmt12(shift_t(r["time"], -off)) + ", " + names + " will switch " + ("ON" if r.get("on", True) else "OFF") + "."


def exec_event(r, tag):
    ss = st.session_state
    off = int(r.get("offset", 0))
    nm = "⏰ " + r["name"]
    if tag == "geyser":
        d = find_dev("En-Suite Bath", "geyser") or next((x for x in ss.fleet if x["cid"] == "geyser"), None)
        if d:
            set_dev(d, True, why=nm + ": heating now so hot water is ready at " + fmt12(r["bath"]))
            hold(d, (off + 45) * 60)
    elif tag == "wake":
        ss.room_mode.pop("Master Suite", None)
        cur, bulb = find_dev("Master Suite", "curtain"), find_dev("Master Suite", "bulb")
        if cur:
            set_dev(cur, True, 100, why=nm + ": opening the curtains to welcome you")
            hold(cur, 20 * 60)
        if bulb:
            set_dev(bulb, True, 40, "#FFB347", why=nm + ": soft warm light")
            hold(bulb, 20 * 60)
    elif tag == "wind":
        ac, cur = find_dev("Master Suite", "ac"), find_dev("Master Suite", "curtain")
        if ac:
            set_dev(ac, True, 21, why=nm + ": cooling the Master Suite to 21 °C")
            hold(ac, 90 * 60)
        if cur:
            set_dev(cur, True, 0, why=nm + ": closing the curtains")
            hold(cur, 90 * 60)
        ss.room_mode["Master Suite"] = WIND_MODE
        ss.fade_tok += 1
        log(nm + ": 432Hz ambient sleep audio is fading in (press Play once to start sound)")
    else:
        for uid in r.get("uids", []):
            d = next((x for x in ss.fleet if x["uid"] == uid), None)
            if d:
                set_dev(d, r.get("on", True), why=nm)
                hold(d, 30 * 60)


def run_routines():
    """Fire any routine whose start time was reached in the last 30 minutes."""
    ss = st.session_state
    now = datetime.now()
    today = now.date().isoformat()
    ran = False
    for r in ss.daily_routines:
        if not r["enabled"]:
            continue
        for tag, tm in routine_events(r):
            trig = datetime.combine(now.date(), tm)
            key = r["id"] + ":" + tag
            if trig <= now < trig + timedelta(minutes=30) and ss.routine_runs.get(key) != today:
                ss.routine_runs[key] = today
                exec_event(r, tag)
                ran = True
    return ran


def run_routine_now(rid):
    ss = st.session_state
    r = next((x for x in ss.daily_routines if x["id"] == rid), None)
    if r:
        for tag, _ in routine_events(r):
            exec_event(r, tag)
        ss.flash = "▶ " + r["name"]


def del_routine(rid):
    ss = st.session_state
    ss.daily_routines = [r for r in ss.daily_routines if r["id"] != rid]


def add_routine():
    ss = st.session_state
    name = (ss.get("nr_name") or "").strip()
    uids = ss.get("nr_devs") or []
    if not name or not uids:
        ss.flash = t("rt_need")
        return
    ss.rt_seq = ss.get("rt_seq", 0) + 1
    ss.daily_routines.append({"id": "c" + str(ss.rt_seq), "kind": "custom", "name": name, "enabled": True,
                              "time": ss.get("nr_time", dtime(18, 0)), "offset": int(ss.get("nr_off", 0)),
                              "uids": list(uids), "on": ss.get("nr_act", "Switch ON") == "Switch ON"})
    ss.flash = "✅ " + t("rt_made")


def create_space():
    ss = st.session_state
    name = (ss.get("sp_name") or "").strip()[:40]
    if not name:
        ss.flash = t("sp_need")
        return
    if name in ss.spaces:
        ss.flash = t("sp_dup")
        return
    ss.spaces[name] = {"icon": ss.get("sp_icon", "🏠"), "type": ss.get("sp_type", "Other"), "devices": [], "preset": None,
                       "persona": ss.get("sp_persona") if ss.get("sp_persona") in ("personal", "shared") else None}
    for uid in ss.get("sp_devs") or []:
        d = next((x for x in ss.fleet if x["uid"] == uid), None)
        if d:
            assign_device(d, name)
    set_active_room(name)
    log("➕ New space created: " + name)
    ss.flash = t("sp_made", n=name)


def set_active_room(name):
    """ONE source of truth for the active room."""
    ss = st.session_state
    if name in ss.spaces:
        ss["sel_room"] = name
    ss["room_rev"] = ss.get("room_rev", 0) + 1


def pick_room(key):
    ss = st.session_state
    v = ss.get(key)
    prev = ss.get("sel_room")
    set_active_room(v if v in ss.spaces else current_room())
    if v in ss.spaces and v != prev:
        try:
            apply_room_theme(v)                  # Reading Room / Work Studio switch mode, devices and music together
        except Exception as e:
            log("⚠ Room atmosphere skipped: " + type(e).__name__)


def dev_by_uid(uid):
    return next((x for x in st.session_state.fleet if x["uid"] == uid), None)


def name_taken(name, skip_uid=None):
    low = name.strip().lower()
    return any(d["name"].strip().lower() == low and d["uid"] != skip_uid for d in st.session_state.fleet)


def unique_name(base, skip_uid=None):
    name, k = base, 2
    while name_taken(name, skip_uid):
        name = base + " #" + str(k)
        k += 1
    return name


def snapshot_room(room):
    ss = st.session_state
    devs = space_devs(room)
    ss.spaces[room]["preset"] = ({str(d["uid"]): {"on": bool(d["on"]), "lvl": int(d["lvl"]), "color": safe_hex(d["color"])}
                                  for d in devs} if devs else None)
    return len(devs)


def apply_preset(room, why=True, force=False):
    """Apply the saved room default. Manual one-click use forces it; automation respects holds."""
    ss = st.session_state
    sp = ss.spaces.get(room)
    pre = sp.get("preset") if sp else None
    if not pre:
        return 0
    n = 0
    for d in space_devs(room):
        p = pre.get(str(d["uid"]))
        if p is None or (held(d) and not force):
            continue
        set_dev(d, p.get("on"), p.get("lvl"), p.get("color"))
        n += 1
    if why:
        log("⚡ Room default applied: " + room + " (" + str(n) + " device(s))")
    return n


def cb_save_preset():
    ss = st.session_state
    room = current_room()
    n = snapshot_room(room)
    log("💾 Default saved for " + room + " (" + str(n) + " device(s))")
    ss.flash = t("rs_preset_saved", n=tr_room(room), c=n)


def cb_clear_preset():
    ss = st.session_state
    room = current_room()
    ss.spaces[room]["preset"] = None
    ss.flash = t("rs_preset_cleared", n=tr_room(room))


def cb_apply_preset(room):
    ss = st.session_state
    n = apply_preset(room, force=True)
    ss.flash = t("rs_preset_applied", n=tr_room(room), c=n) if n else t("preset_none")


def cb_apply_all_presets():
    ss = st.session_state
    total = 0
    for room in list(ss.spaces):
        total += apply_preset(room, force=True)
    ss.flash = t("rs_preset_applied", n="ALL", c=total)


def repair_orphans():
    """Every device belongs to exactly one existing space."""
    ss = st.session_state
    if "fleet" not in ss or not ss.get("spaces"):
        return 0
    names = list(ss.spaces)
    fallback = names[0]
    uids = {d["uid"] for d in ss.fleet}
    owner, fixed = {}, 0
    for n, sp in ss.spaces.items():
        keep = []
        for u in dict.fromkeys(sp["devices"]):
            if u in uids and u not in owner:
                owner[u] = n
                keep.append(u)
            else:
                fixed += 1
        sp["devices"] = keep
    for d in ss.fleet:
        if d["uid"] not in owner:
            home = d["room"] if d["room"] in ss.spaces else fallback
            ss.spaces[home]["devices"].append(d["uid"])
            owner[d["uid"]] = home
            fixed += 1
        if d["room"] != owner[d["uid"]]:
            d["room"] = owner[d["uid"]]
    for sp in ss.spaces.values():
        sp.setdefault("preset", None)
    if ss.presence.get("room") not in ss.spaces:
        ss.presence["room"] = fallback
    if ss.get("sel_room") not in ss.spaces:
        ss["sel_room"] = ss.presence["room"]
    if fixed:
        log("🛟 " + t("dev_orphan_fix") + " (" + str(fixed) + ")")
    return fixed


def ensure_modes():
    """Every mode carries a valid colour, genre and a complete 10-instrument mix."""
    ss = st.session_state
    for k, v in DEFAULT_MODES.items():
        if k not in ss.modes:
            ss.modes[k] = dict(v)
    for name, m in ss.modes.items():
        m["bulb"] = safe_hex(m.get("bulb"))
        m["mix"] = full_mix(m.get("mix"))
        if m.get("genre") not in GENRES:
            m["genre"] = GENRES[0]
        m.setdefault("fan", 1)
        m.setdefault("ac", 24)
        m.setdefault("extras", [])
    ss.cfg["mix"] = full_mix(ss.cfg.get("mix"))


def connect_all():
    ss = st.session_state
    bar = st.progress(0.0)
    ok = 0
    for i, d in enumerate(ss.fleet):
        ok += 1 if connect_device(d) else 0
        bar.progress((i + 1) / float(len(ss.fleet)))
    log("🔗 Connected " + str(ok) + " of " + str(len(ss.fleet)) + " devices")


# ---- Saved home: devices + rooms are kept in the user's account so they are still there next time ----------
HOME_PROTOS = ("Simulation", "Philips WiZ (UDP)", "Home Assistant / REST", "Home Assistant API", "Matter over Thread/Wi-Fi")


def home_to_json():
    """Structural part of the home (what exists and how to reach it). Live on/off state is not saved."""
    ss = st.session_state
    if "fleet" not in ss or not ss.get("spaces"):
        return None
    devs = []
    for d in ss.fleet:
        r = {k: d.get(k, "") for k in ("uid", "cid", "name", "room", "proto", "addr", "token")}
        for k in ("acmode", "fanmode"):
            if isinstance(d.get(k), str):
                r[k] = d[k]
        devs.append(r)
    spaces = {}
    for n, sp in ss.spaces.items():
        spaces[n] = {"icon": sp.get("icon", "\U0001F3E0"), "type": sp.get("type", "Other"),
                     "devices": [int(u) for u in sp.get("devices", [])], "preset": sp.get("preset"),
                     "persona": sp.get("persona")}
    ha = ss.cfg.get("ha") if isinstance(ss.cfg.get("ha"), dict) else {}
    return {"v": 1, "devices": devs, "spaces": spaces, "wiz_ip": str(ss.cfg.get("wiz_ip", "")),
            "ha": {"url": str(ha.get("url", "")), "token": str(ha.get("token", ""))}}


def home_restore():
    """Rebuild ss.fleet / ss.spaces from the saved home. Returns False (and changes nothing) if nothing usable is saved."""
    ss = st.session_state
    h = ss.get("_home_saved")
    if not isinstance(h, dict):
        return False
    try:
        raw_devs, raw_sp = h.get("devices"), h.get("spaces")
        if not isinstance(raw_devs, list) or not isinstance(raw_sp, dict) or not raw_devs:
            return False
        if not all(isinstance(raw_sp.get(n), dict) for n in PROTECTED_SPACES):
            return False
        ss.uid = 0
        fleet, seen = [], set()
        for r in raw_devs:
            if not isinstance(r, dict):
                continue
            cid, uid = r.get("cid"), r.get("uid")
            if cid not in CAT or not isinstance(uid, int) or isinstance(uid, bool) or uid in seen:
                continue
            seen.add(uid)
            d = new_device(cid, str(r.get("name") or CAT[cid][2])[:40], str(r.get("room") or "")[:40])
            d["uid"] = uid
            proto = r.get("proto")
            if proto in HOME_PROTOS:
                d["proto"] = proto
            d["addr"], d["token"] = str(r.get("addr") or "")[:300], str(r.get("token") or "")[:300]
            for k in ("acmode", "fanmode"):
                if isinstance(r.get(k), str):
                    d[k] = r[k][:30]
            if d["proto"] != "Simulation":
                d["last"] = "restored from your account"
            fleet.append(d)
        if not fleet:
            return False
        spaces = {}
        for n, sp in raw_sp.items():
            if not isinstance(n, str) or not isinstance(sp, dict):
                continue
            pre = sp.get("preset")
            clean = None
            if isinstance(pre, dict):
                clean = {}
                for k, v in pre.items():
                    if str(k).isdigit() and int(k) in seen and isinstance(v, dict):
                        try:
                            clean[str(int(k))] = {"on": bool(v.get("on")), "lvl": int(v.get("lvl", 0)),
                                                  "color": safe_hex(v.get("color"))}
                        except (TypeError, ValueError):
                            pass
                clean = clean or None
            spaces[n[:40]] = {"icon": str(sp.get("icon") or "\U0001F3E0")[:8], "type": str(sp.get("type") or "Other")[:20],
                              "devices": [u for u in dict.fromkeys(sp.get("devices") or []) if u in seen],
                              "preset": clean,
                              "persona": sp.get("persona") if sp.get("persona") in ("personal", "shared") else None}
        ss.fleet, ss.spaces = fleet, spaces
        ss.uid = max([ss.uid] + list(seen))
        ip = str(h.get("wiz_ip") or "").strip()
        if ip and wiz_ip_ok(ip):
            ss.cfg["wiz_ip"] = ip
        ha = h.get("ha")
        if isinstance(ha, dict) and str(ha.get("url", "")).startswith(("http://", "https://")):
            ss.cfg["ha"] = {"url": str(ha["url"])[:300], "token": str(ha.get("token", ""))[:600]}
        return True
    except Exception:
        return False


def init_state():
    ss = st.session_state
    if ss.get("theme_choice") not in ("dark", "light"):
        ss["theme_choice"] = "light" if native_light() else "dark"
    if "modes" not in ss:
        ss.modes = {k: dict(v) for k, v in DEFAULT_MODES.items()}
    if "cfg" not in ss:
        ss.cfg = {"auto_mode": False, "source": "sim", "scn": "relaxed",
                  "api_url": "http://localhost:8000/latest-biometrics", "thr": 100, "rel": 78, "rest": 62, "poll": 3,
                  "notif": True, "chime": True, "timer": 0, "tok": 0, "bed": 100, "mix": dict(BASE_MIX),
                  "api_token": "", "follow_me": True, "cut_mode": "Off", "calm_on": True, "tracker": "Apple Watch Series 9",
                  "geo_auto": True}
    for k, v in (("holds", {}), ("room_mode", {}), ("conn", {"mode": "home"}),
                 ("geo", {"state": "idle", "chimed": False, "km": 20, "rev": 0}), ("presence", {"room": "Living Lounge"}),
                 ("fade_tok", 0), ("routine_runs", {}), ("daily_routines", default_routines())):
        if k not in ss:
            ss[k] = v
    if "fleet" not in ss:
        ss.uid = 0
        ss.log = []
        if home_restore():                       # this user's saved devices and rooms: nothing is sent to the real devices here
            ss.active_mode = "Relax Evening"
        else:
            ss.fleet = []
            ss.spaces = {}
            for room, (icon, typ, devs) in DEFAULT_SPACES.items():
                ids = []
                for cid, label in devs:
                    d = new_device(cid, label + " · " + room, room)
                    ss.fleet.append(d)
                    ids.append(d["uid"])
                ss.spaces[room] = {"icon": icon, "type": typ, "devices": ids, "preset": None}
            ss.active_mode = "Relax Evening"
            apply_mode(ss.active_mode)
            # Pre-fill every predefined room's one-click default
            keep = {d["uid"]: (d["on"], d["lvl"], d["color"]) for d in ss.fleet}
            apply_mode(ss.active_mode, why=False, devs=list(ss.fleet), set_active=False)
            for room in ss.spaces:
                snapshot_room(room)
            for d in ss.fleet:
                d["on"], d["lvl"], d["color"] = keep[d["uid"]]
            ss.log = []
    for k, v in (("hr_hist", [72 + random.randint(-3, 3) for _ in range(30)]), ("skin_hist", []),
                 ("bstate", "relaxed"), ("last_state", None), ("wake_ticks", 0), ("sleep_ts", 0.0), ("prev_auto", False),
                 ("flash", ""), ("profile", None), ("editing", False), ("chat", []), ("chimed", False),
                 ("sel_room", ss.presence["room"]), ("room_rev", 0), ("rerun_pending", False), ("last_rerun", 0.0),
                 ("ui_mode", "zen"), ("guest_mode", False), ("guest_rev", 0), ("family_lock", set()), ("occupancy", {}),
                 ("dial_idx", {}), ("dial_scope", "both"), ("voice_last", ""), ("pending_offer", None),
                 ("last_offer_at", -99), ("last_topic", None), ("deeper", 0), ("ui_rev", 0)):
        if k not in ss:
            ss[k] = v
    repair_orphans()
    ensure_modes()


# ----------------------------------------------------------------------------
# Biometrics + AI analysis
# ----------------------------------------------------------------------------
SCN = {"relaxed": (68, (50, 70), 33.6, False), "active": (90, (38, 55), 34.8, False),
       "stress": (115, (20, 32), 34.5, False), "sleep": (54, (75, 95), 32.7, True),
       "wake": (73, (48, 60), 33.8, False)}



# ---- Home Assistant link: find the user's devices and control them through Home Assistant's own API ------------
HA_DOMAINS = ("light", "fan", "climate", "switch", "water_heater", "cover", "humidifier", "media_player")
HA_ENT_RE = re.compile(r"^[a-z_]+\.[a-z0-9_]+$")


def ha_cfg():
    ha = st.session_state.cfg.get("ha")
    return ha if isinstance(ha, dict) and str(ha.get("url", "")).startswith(("http://", "https://")) and ha.get("token") else None


def ha_save(url, token):
    url = (url or "").strip().rstrip("/")
    if not url.startswith(("http://", "https://")) or not (token or "").strip():
        return False
    st.session_state.cfg["ha"] = {"url": url[:300], "token": token.strip()[:600]}
    return True


def ha_url_safe(url):
    """The server only calls public addresses (never loopback, link-local or private ones) unless AURASYNC_ALLOW_LAN=1."""
    try:
        host = urllib.parse.urlparse(url).hostname
        if not host:
            return False
        if os.environ.get("AURASYNC_ALLOW_LAN") == "1":
            return True
        for info in socket.getaddrinfo(host, None):
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_unspecified or ip.is_multicast or ip.is_reserved:
                return False
        return True
    except Exception:
        return False


def ha_discover():
    """Ask Home Assistant which lights, fans, ACs and switches it knows. Returns (list, error text)."""
    ha = ha_cfg()
    if not ha:
        return [], "Enter your Home Assistant address and access token first."
    if not ha_url_safe(ha["url"]):
        return [], ("The AuraSync server cannot reach an address inside your home. Use your Home Assistant Cloud / "
                    "remote address (https://...), or type the device name below and your iPhone app will send the commands.")
    try:
        r = requests.get(ha["url"] + "/api/states", headers={"Authorization": "Bearer " + ha["token"]}, timeout=8)
    except Exception as e:
        return [], "Could not reach Home Assistant (" + type(e).__name__ + ")."
    if r.status_code == 401:
        return [], "Home Assistant refused the token. Create a new long-lived access token and try again."
    if r.status_code >= 400:
        return [], "Home Assistant answered with error " + str(r.status_code) + "."
    out = []
    try:
        for s in r.json():
            eid = str(s.get("entity_id", ""))
            dom = eid.split(".")[0]
            if dom in HA_DOMAINS and HA_ENT_RE.match(eid):
                out.append({"entity_id": eid, "name": str((s.get("attributes") or {}).get("friendly_name") or eid)[:60], "domain": dom})
    except Exception:
        return [], "Home Assistant sent an answer AuraSync could not read."
    return sorted(out, key=lambda x: (x["domain"], x["name"]))[:300], ""


def ha_calls(dev):
    """Service calls that put one device into its current state: [(path, body)]."""
    ent = str(dev["addr"]).strip()
    dom = ent.split(".")[0]
    on, lvl = bool(dev["on"]), int(dev["lvl"])
    if dom == "light":
        if not on:
            return [("light/turn_off", {"entity_id": ent})]
        body = {"entity_id": ent, "brightness_pct": max(1, min(100, lvl))}
        if dev["cid"] in COLOR_CIDS:
            r, g, b = hex_rgb(dev["color"])
            body["rgb_color"] = [r, g, b]
        return [("light/turn_on", body)]
    if dom == "fan":
        pct = lvl * 20 if dev["cid"] == "fan" else lvl
        if not on or pct <= 0:
            return [("fan/turn_off", {"entity_id": ent})]
        return [("fan/turn_on", {"entity_id": ent, "percentage": max(1, min(100, pct))})]
    if dom == "climate":
        if not on:
            return [("climate/turn_off", {"entity_id": ent})]
        mode = "fan_only" if dev.get("acmode") == "Fan Only" else "cool"
        return [("climate/set_hvac_mode", {"entity_id": ent, "hvac_mode": mode}),
                ("climate/set_temperature", {"entity_id": ent, "temperature": lvl})]
    return [("homeassistant/" + ("turn_on" if on else "turn_off"), {"entity_id": ent})]


def ha_push(dev):
    ss = st.session_state
    ha = ha_cfg()
    if not ha or not HA_ENT_RE.match(str(dev["addr"]).strip()):
        dev["status"], dev["last"] = "offline", "Home Assistant is not linked"
        return
    hdr = {"Authorization": "Bearer " + ha["token"], "Content-Type": "application/json"}
    for path, body in ha_calls(dev):
        url = ha["url"] + "/api/services/" + path
        if native_on():
            native_enqueue({"k": "http", "url": url, "method": "POST", "headers": hdr, "body": body})
            dev["last"] = "sent to phone " + datetime.now().strftime("%H:%M:%S")
        else:
            try:
                if not ha_url_safe(ha["url"]):
                    dev["status"], dev["last"] = "offline", "turn on the iPhone app control to reach your home"
                    return
                requests.post(url, json=body, headers=hdr, timeout=3)
                dev["last"] = "sent " + datetime.now().strftime("%H:%M:%S") + " via Home Assistant"
            except Exception as e:
                dev["status"], dev["last"] = "offline", type(e).__name__
                return


# ---- Phone bridge: the Flutter iPhone app sends commands to bulbs / fans / ACs inside the home network ----
# Streamlit runs on a cloud server that cannot reach devices in a house, so when the page runs inside the iPhone app
# the commands are queued here, handed to the app through the "AuraNative" channel, and sent from the phone.
NATIVE_OUT_HTML = """
<script>
(function () {
  var Q = __Q__;
  function wins() { var o = []; [window, window.parent, window.top].forEach(function (w) { try { if (w && o.indexOf(w) < 0) { void w.document; o.push(w); } } catch (e) {} }); return o; }
  function send(m) {
    var s = JSON.stringify(m), L = wins();
    for (var i = 0; i < L.length; i++) {
      var w = L[i];
      try { if (w.AuraNative && w.AuraNative.postMessage) { w.AuraNative.postMessage(s); return true; } } catch (e) {}
      try { if (w.flutter_inappwebview && w.flutter_inappwebview.callHandler) { w.flutter_inappwebview.callHandler('AuraNative', s); return true; } } catch (e) {}
      try { if (w.webkit && w.webkit.messageHandlers && w.webkit.messageHandlers.AuraNative) { w.webkit.messageHandlers.AuraNative.postMessage(s); return true; } } catch (e) {}
    }
    return false;
  }
  var seen; try { seen = (window.parent.__auraSent = window.parent.__auraSent || {}); } catch (e) { seen = {}; }
  Q.forEach(function (c) { if (seen[c.id]) { return; } seen[c.id] = 1; c.t = 'cmd'; send(c); });
})();
</script>
"""


def native_on():
    """Route device commands through the iPhone app. Only while you are home: away, the phone cannot reach the LAN and the cloud relay is used."""
    ss = st.session_state
    return bool(ss.get("native_flag")) and (ss.get("conn") or {}).get("mode", "home") == "home"


def native_enqueue(cmd):
    ss = st.session_state
    c = dict(cmd)
    c["id"] = uuid.uuid4().hex[:10]
    q = list(ss.get("native_q") or [])
    q.append(c)
    ss.native_q = q[-40:]
    ss.native_sent_n = ss.get("native_sent_n", 0) + 1
    ss.native_sent_ts = time.time()


def native_dev_cmd(dev):
    """Command for the phone, mirroring push(): WiZ UDP, or an HTTP webhook for everything else."""
    if dev["proto"].startswith("Philips"):
        if not wiz_ip_ok(dev["addr"]):
            return None
        r, g, b = hex_rgb(dev["color"])
        params = {"state": bool(dev["on"]), "dimming": max(10, int(dev["lvl"])), "r": r, "g": g, "b": b}
        return {"k": "wiz", "ip": str(dev["addr"]).strip(), "p": {"id": 1, "method": "setPilot", "params": params}}
    url = str(dev["addr"]).strip()
    if not url.lower().startswith(("http://", "https://")):
        return None
    body = {"source": "AuraSync", "device": dev["name"], "type": dev["cid"], "room": dev["room"],
            "state": "on" if dev["on"] else "off", "level": dev["lvl"], "color": dev["color"],
            "mode": dev.get("acmode") or dev.get("fanmode") or ""}
    hdr = {"Authorization": "Bearer " + dev["token"]} if dev.get("token") else {}
    return {"k": "http", "url": url, "method": "POST", "headers": hdr, "body": body}


def render_native_out():
    """Hand queued device commands to the iPhone app. Runs at the end of every full page run."""
    ss = st.session_state
    q = list(ss.get("native_q") or [])
    if not q:
        return
    ss.native_q = []
    blob = json.dumps(q, ensure_ascii=False).replace("</", "<\\/")
    components.html(NATIVE_OUT_HTML.replace("__Q__", blob), height=0)


def cb_native_toggle():
    st.session_state.native_flag = bool(st.session_state.get("native_ctl_w"))


def cb_native_test():
    """Send the current state of every real device to the phone, plus the WiZ IP from Room Settings (a quick bulb test)."""
    ss, cfg = st.session_state, st.session_state.cfg
    n = 0
    for d in ss.get("fleet") or []:
        if d.get("proto") == "Simulation" or not d.get("addr"):
            continue
        d["status"] = "connected"
        if d["cid"] in BULBLIKE:
            d["on"], d["lvl"], d["color"] = True, max(40, int(d.get("lvl") or 60)), "#FFE4A0"
        push(d)
        n += 1
    ip = str(cfg.get("wiz_ip", "")).strip()
    if ip and wiz_fire(ip, "#FFE4A0", 60):
        n += 1
    ss.flash = ("📱 Sent " + str(n) + " command(s) to your phone") if n else "No real device is set up yet (add a WiZ IP or a device with an address)."
    log(ss.flash)


def cb_native_setup():
    """One tap: the iPhone app walks through every permission AuraSync needs, one system prompt after another."""
    ss = st.session_state
    native_enqueue({"k": "setup", "need": ["bluetooth", "localnetwork", "health", "notifications", "location", "background"]})
    ss.flash = "✨ Setup started on your iPhone. Tap Allow on each prompt. If nothing appears, update the iPhone app."
    log("✨ Asked the iPhone app to set up all permissions")


def render_native_panel():
    ss = st.session_state
    st.toggle("📱 Control my devices through this iPhone app", value=bool(ss.get("native_flag")), key="native_ctl_w",
              on_change=cb_native_toggle,
              help="Turn on when AuraSync runs inside the iPhone app. The phone then sends the light, fan and AC commands over your home Wi-Fi.")
    rx, ts = ss.get("hr_rx", 0), ss.get("hr_rx_ts", 0)
    b = ss.get("ble") or {}
    if rx:
        st.caption("📡 Phone link: " + str(rx) + " message(s) received, last " + str(int(time.time() - ts)) + " s ago, state: " +
                   (b.get("state") or "?") + (", source: " + b["src"] if b.get("src") else "") +
                   (", last reading " + str(b["hr"]) + " BPM" if b.get("hr") else ", no reading yet"))
    else:
        st.caption("📡 Phone link: nothing received from the iPhone app yet.")
    st.button("✨ Set up everything", key="native_setup_btn", type="primary", on_click=cb_native_setup,
              help="Asks the iPhone app to request Bluetooth, Local Network, Health, Notifications, Location and background access one after another.")
    st.caption("Tap Allow on each iPhone prompt. If you decline one, only the feature that needs it stays off.")
    if ss.get("native_flag"):
        st.caption("💡 Commands sent to the phone: " + str(ss.get("native_sent_n", 0)))
        st.button("💡 Test: send a warm light to my real devices", key="native_test_btn", on_click=cb_native_test)


HR_BRIDGE_KEY = "aura_hr_bridge"
HR_PH = "◈4417◈"


def rmssd(rr):
    """Heart-rate variability (ms) from beat-to-beat intervals; 0 when there is not enough data."""
    rr = [x for x in rr if 300 < x < 2000]
    if len(rr) < 6:
        return 0
    d = [(rr[i + 1] - rr[i]) ** 2 for i in range(len(rr) - 1)]
    return int(max(10, min(150, math.sqrt(sum(d) / len(d)))))


def cb_hr_bridge():
    """The browser (Web Bluetooth) hands heart-rate samples and connection status over through a hidden field."""
    ss = st.session_state
    raw = str(ss.get(HR_BRIDGE_KEY) or "")
    ss[HR_BRIDGE_KEY] = ""
    try:
        d = json.loads(raw)
    except Exception:
        return
    if not isinstance(d, dict):
        return
    n = str(d.get("n", ""))[:40]
    if n and n == ss.get("hr_nonce"):
        return
    ss.hr_nonce = n
    ss.hr_rx = ss.get("hr_rx", 0) + 1
    ss.hr_rx_ts = time.time()
    if d.get("nat") and not ss.get("native_seen"):          # first sign of the iPhone app: route device commands through it
        ss.native_seen = True
        ss.native_flag = True
        ss.native_ctl_w = True
    b = dict(ss.get("ble") or {})
    b["state"] = str(d.get("st", ""))[:20]
    b["src"] = str(d.get("src", ""))[:30]
    try:
        b["ttl"] = max(25, min(900, int(float(d.get("ttl") or 25))))
    except (TypeError, ValueError):
        b["ttl"] = 25
    b["name"] = str(d.get("name", ""))[:40]
    b["err"] = str(d.get("err", ""))[:30]
    try:
        hr = int(float(d.get("hr") or 0))
    except (TypeError, ValueError):
        hr = 0
    if 25 < hr < 230:
        b["hr"], b["ts"] = hr, time.time()
        try:
            b["rr"] = [int(x) for x in (d.get("rr") or [])][-60:]
        except (TypeError, ValueError):
            pass
    prev = ss.get("ble_prev_state")
    ss.ble = b
    ss.ble_prev_state = b["state"]
    if b["state"] == "connected" and prev != "connected":
        ss.cfg["source"] = "ble"
        log("⌚ Heart-rate wearable connected: " + (b["name"] or "band"))
        ss.flash = "⌚ " + (b["name"] or "")
    elif b["state"] in ("disconnected", "error") and prev != b["state"]:
        log("⌚ Heart-rate wearable: " + b["state"] + (" (" + b["err"] + ")" if b["err"] else ""))


def render_hr_bridge():
    st.text_input("◈ 4417", key=HR_BRIDGE_KEY, placeholder=HR_PH, label_visibility="collapsed", max_chars=1200,
                  on_change=cb_hr_bridge)


WEAR_HTML = """
<style>
  html, body { margin: 0; background: transparent; }
  #w { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; padding: 12px 14px; box-sizing: border-box; border-radius: 18px;
       border: 1px solid __LINE__; background: __GLASS__; font-family: Inter, Arial, sans-serif; color: __ACC__; }
  #heart { font-size: 30px; line-height: 1; }
  #heart.beat { animation: beat 1s ease-in-out infinite; }
  @keyframes beat { 0%, 100% { transform: scale(1); } 15% { transform: scale(1.22); } 30% { transform: scale(1); } 45% { transform: scale(1.14); } }
  #bpm { font-size: 30px; font-weight: 700; min-width: 64px; }
  #bpm small { font-size: 12px; font-weight: 400; color: __SUB__; }
  #tx { flex: 1; min-width: 160px; }
  #t1 { font-size: 14px; font-weight: 600; } #t2 { font-size: 12px; color: __SUB__; margin-top: 2px; overflow-wrap: anywhere; }
  #w.err #t1 { color: #ff8a80; }
  button { border: 1px solid __ACC__; background: transparent; color: __ACC__; border-radius: 12px; padding: 8px 12px; font-size: 13px; cursor: pointer; }
  button.main { background: __ACC__; color: __BTN__; font-weight: 700; }
  #nt { width: 100%; font-size: 11px; color: __SUB__; }
</style>
<div id="w">
  <div id="heart">&#10084;&#65039;</div>
  <div id="bpm">--<small> bpm</small></div>
  <div id="tx"><div id="t1"></div><div id="t2"></div></div>
  <button id="c1" class="main" type="button"></button>
  <button id="c2" type="button"></button>
  <button id="c3" type="button"></button>
  <div id="nt"></div>
</div>
<script>
(function () {
  var CFG = __CFG__, S = CFG.s, P = null;
  try { P = window.parent; void P.document.body; } catch (e) { P = null; }
  var $ = function (id) { return document.getElementById(id); };
  var w = $('w');
  $('c1').textContent = S.connect; $('c2').textContent = S.all; $('c3').textContent = S.disc; $('nt').textContent = S.note;
  function eng() { return (P && P.__aura && P.__aura.hrm) ? P.__aura : null; }
  function natHas() {
    var L = [window, window.parent, window.top];
    for (var i = 0; i < L.length; i++) {
      try { var w = L[i]; if ((w.AuraNative && w.AuraNative.postMessage) || (w.flutter_inappwebview && w.flutter_inappwebview.callHandler) ||
            (w.webkit && w.webkit.messageHandlers && w.webkit.messageHandlers.AuraNative)) { return true; } } catch (e) {}
    }
    return false;
  }
  function fit() {
    try {
      var fe = window.frameElement, h = Math.ceil(w.getBoundingClientRect().height) + 8;
      fe.style.setProperty('height', h + 'px', 'important'); fe.setAttribute('height', h);
      /* force the Streamlit wrappers to the card's real height so the sliders below start under the card, not behind it */
      var el = fe.parentElement;
      for (var i = 0; i < 2 && el && el.tagName !== 'BODY'; i++, el = el.parentElement) {
        el.style.setProperty('height', h + 'px', 'important');
        el.style.setProperty('min-height', h + 'px', 'important');
        el.style.setProperty('overflow', 'visible', 'important');
      }
      if (el && el.tagName !== 'BODY') { el.style.setProperty('margin-bottom', '14px', 'important'); }
    } catch (e) {}
  }
  function paint() {
    var a = eng(), h = a ? a.hrm : null, st = h ? h.st : 'idle', err = h ? h.err : '';
    var hasBT = !!(P && P.navigator && P.navigator.bluetooth) || !!navigator.bluetooth || natHas();
    var fresh = h && h.hr && (Date.now() - h.ts < 15000);
    $('bpm').innerHTML = (fresh ? h.hr : '--') + '<small> bpm</small>';
    $('heart').className = fresh ? 'beat' : '';
    var line = S[st] || S.idle, sub = h && h.name ? h.name : '', bad = false;
    if (!hasBT && st === 'idle') { line = S.unsupported; bad = true; }
    if (st === 'error' || st === 'unsupported' || err) {
      bad = st === 'error' || st === 'unsupported';
      if (err === 'unsupported') { line = S.unsupported; }
      else if (err === 'NotAllowedError' || err === 'SecurityError') { line = S.blocked; }
      else if (err === 'cancelled') { line = S.cancelled; bad = false; }
      else if (st === 'error') { line = S.error; }
    }
    if (st === 'connected' && !fresh) { line = S.wait; }
    $('t1').textContent = line; $('t2').textContent = sub; w.className = bad ? 'err' : '';
    var live = st === 'connected' || st === 'connecting' || st === 'reconnecting' || st === 'stale';
    $('c1').style.display = live ? 'none' : ''; $('c2').style.display = live ? 'none' : '';
    $('c3').style.display = live ? '' : 'none';
    fit();
  }
  $('c1').onclick = function () { var a = eng(); if (a) { a.hrConnect(false); } paint(); };
  $('c2').onclick = function () { var a = eng(); if (a) { a.hrConnect(true); } paint(); };
  $('c3').onclick = function () { var a = eng(); if (a) { a.hrDisconnect(); } paint(); };
  setInterval(paint, 1000); paint();
})();
</script>
"""


def wear_html():
    keys = ("connect", "all", "disc", "idle", "connecting", "connected", "reconnecting", "stale", "disconnected",
            "unsupported", "blocked", "cancelled", "error", "note", "wait")
    strings = {k: tt("ble_" + k) for k in keys}
    blob = json.dumps({"s": strings}, ensure_ascii=False).replace("</", "<\\/")
    return themed(WEAR_HTML.replace("__CFG__", blob))


def render_wearable():
    ss = st.session_state
    st.markdown("**⌚ " + t("ble_title") + "**")
    st.caption(t("ble_sub"))
    components.html(wear_html(), height=130)
    b = ss.get("ble") or {}
    if b.get("hr") and time.time() - b.get("ts", 0) < b.get("ttl", 25):
        st.caption("💓 " + t("ble_live", n=b.get("name") or "band", hr=b["hr"]))
    render_native_panel()


def parse_hr_payload(d):
    """Our own JSON plus Oura / Fitbit style answers -> dict with the key _hr, or None."""
    if isinstance(d, list):
        d = d[-1] if d else {}
    if isinstance(d, dict) and isinstance(d.get("data"), list) and d["data"]:
        d = d["data"][-1]
    if isinstance(d, dict) and "activities-heart-intraday" in d:
        ds = (d["activities-heart-intraday"] or {}).get("dataset") or []
        d = {"heart_rate": ds[-1].get("value")} if ds else {}
    if not isinstance(d, dict):
        return None
    for k in ("heart_rate", "hr", "bpm", "heartRate", "heart_rate_bpm"):
        if k in d:
            try:
                return dict(d, _hr=int(float(d[k])))
            except (TypeError, ValueError):
                return None
    return None


# ---- Multi-source live heart rate: Web Bluetooth, page link (?hr=), bridge.py file, cloud-linked wearables ----
BRIDGE_FILE = "aurasync_bridge.json"
BRIDGE_MAX_AGE = 120        # seconds a bridge.py reading stays valid
URL_HR_MAX_AGE = 90         # seconds a ?hr= reading stays valid
_BRIDGE_CACHE = {}


def _bridge_paths():
    out = []
    env = os.environ.get("AURASYNC_BRIDGE_FILE")
    if env:
        out.append(env)
    try:
        out.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), BRIDGE_FILE))
    except NameError:
        pass
    out.append(os.path.join(os.getcwd(), BRIDGE_FILE))
    seen, res = set(), []
    for p in out:
        if p not in seen:
            seen.add(p)
            res.append(p)
    return res


def _ts_epoch(v):
    """Epoch seconds from a number or an ISO-8601 string, else None."""
    try:
        if isinstance(v, (int, float)):
            x = float(v)
            return x / 1000.0 if x > 1e11 else x
        if isinstance(v, str) and v.strip():
            s = v.strip().replace("Z", "+00:00")
            d = datetime.fromisoformat(s)
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            return d.timestamp()
    except (ValueError, OverflowError, OSError):
        return None
    return None


def read_bridge():
    """Latest reading written by the background bridge.py listener (Apple Health and friends), or None when absent or stale."""
    for p in _bridge_paths():
        try:
            stt = os.stat(p)
            if stt.st_size > 65536:
                continue
            key = (p, stt.st_mtime_ns, stt.st_size)
            if _BRIDGE_CACHE.get("key") != key:
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    raw = json.load(f)
                _BRIDGE_CACHE["key"], _BRIDGE_CACHE["raw"] = key, raw
            raw = _BRIDGE_CACHE.get("raw")
            d = parse_hr_payload(raw)
            if not d or not (25 < d["_hr"] < 230):
                continue
            stamp = None
            for k in ("timestamp", "ts", "time", "updated_at", "updated", "date"):
                if k in d:
                    stamp = _ts_epoch(d[k])
                    if stamp:
                        break
            age = time.time() - (stamp or stt.st_mtime)
            if age < 0:
                age = 0.0
            if age > BRIDGE_MAX_AGE:
                continue
            stage = str(d.get("sleep_stage", "")).lower()
            asleep = bool(d.get("asleep", d.get("sleeping", stage in ("light", "deep", "rem", "asleep"))))
            return {"hr": int(d["_hr"]), "hrv": int(float(d.get("hrv", 55) or 55)), "spo2": float(d.get("spo2", 97) or 97),
                    "skin": float(d.get("temperature", 33.5) or 33.5), "asleep": asleep, "live": True,
                    "src": "bridge.py", "age": int(age)}
        except (OSError, ValueError, TypeError):
            continue
    return None


def hr_from_url():
    """?hr=94 on the page link: remember the reading and put it into the heart-rate history right away."""
    if not hasattr(st, "query_params"):
        return
    ss = st.session_state
    try:
        if "hr" not in st.query_params:
            return
        raw = st.query_params.get("hr")
        try:
            del st.query_params["hr"]
        except Exception:
            pass
        hr = int(float(str(raw).strip()[:8]))
    except Exception:
        return
    if not (25 < hr < 230):
        return
    ss.url_hr = {"hr": hr, "ts": time.time()}
    ss.hr_hist = (list(ss.get("hr_hist") or []) + [hr])[-60:]
    log("Heart rate " + str(hr) + " BPM received from the page link")


WEAR_CLOUDS = (("Apple Health", "🍎"), ("Oura Ring", "💍"), ("Ultrahuman", "🔆"), ("Fitbit / Google", "⌚"),
               ("Garmin", "🧭"), ("Whoop", "🏋️"))


def sim_linked_reading(last):
    """Simulated stream for a wearable that was linked with one tap (no Shortcut needed)."""
    ss = st.session_state
    links = ss.get("wear_links") or {}
    names = [n for n, v in links.items() if v]
    if not names:
        return None
    tgt, hrv, skin, asleep = SCN[ss.cfg["scn"]]
    hr = int(max(45, min(140, last + (tgt - last) * 0.35 + random.gauss(0, 1.5))))
    return {"hr": hr, "hrv": random.randint(hrv[0], hrv[1]), "spo2": round(random.uniform(96, 99), 1),
            "skin": round(skin + random.gauss(0, 0.15), 1), "asleep": asleep, "live": True, "src": names[0] + " (simulated)"}


def multi_source_live():
    """Priority: Bluetooth 0x180D, page link (?hr=), bridge.py file. Returns a reading dict or None."""
    ss = st.session_state
    b = ss.get("ble") or {}
    if b.get("hr") and time.time() - b.get("ts", 0) < b.get("ttl", 25):
        return {"hr": int(b["hr"]), "hrv": rmssd(b.get("rr", [])) or 55, "spo2": 97.0, "skin": 33.5,
                "asleep": False, "live": True, "src": b.get("src") or "Bluetooth 0x180D"}
    u = ss.get("url_hr") or {}
    if u.get("hr") and time.time() - u.get("ts", 0) < URL_HR_MAX_AGE:
        return {"hr": int(u["hr"]), "hrv": 55, "spo2": 97.0, "skin": 33.5, "asleep": False, "live": True, "src": "page link"}
    return read_bridge()


# ---- Biometric Auto-Pilot (acts only when the zone changes, never on every polling tick)
ZEN_STRESS_BPM = 85
AP_PRESET = {
    "stress": {"color": "#FF821E", "bright": 35, "ac": 22, "acmode": "Sleep Eco", "fan": 1, "fanmode": "Low",
               "sound": "Deep Calm Studio", "layers": {"hz432": 45, "rain": 40, "stream": 0, "noise": 0}, "msg": "zk_ap_stress"},
    "calm": {"color": "#FFE4A0", "bright": 65, "ac": 24, "acmode": "Cool", "fan": 2, "fanmode": "Natural Breeze",
             "sound": "Zen Garden", "layers": {"hz432": 0, "rain": 0, "stream": 35, "noise": 0}, "msg": "zk_ap_calm"},
}
LAYER_KEYS = (("hz432", "zk_l432"), ("rain", "zk_lrain"), ("stream", "zk_lstream"), ("noise", "zk_lnoise"))
FAN_LEVELS = {"Off": 0, "Low": 1, "Medium": 3, "High": 5, "Natural Breeze": 2}


def layers_of():
    cfg = st.session_state.cfg
    cur = cfg.get("layers") if isinstance(cfg.get("layers"), dict) else {}
    out = {}
    for k, _l in LAYER_KEYS:
        try:
            out[k] = max(0, min(100, int(float(cur.get(k, 0)))))
        except (TypeError, ValueError):
            out[k] = 0
    cfg["layers"] = out
    return out


def layers_params():
    return dict(layers_of())


def wiz_ip_ok(ip):
    try:
        a = ipaddress.ip_address(str(ip).strip())
    except ValueError:
        return False
    return a.version == 4 and (a.is_private or a.is_link_local) and not a.is_loopback and not a.is_unspecified


def wiz_fire(ip, hex_color, dim):
    """Fire-and-forget WiZ setPilot UDP packet to a bulb on the local network."""
    if not wiz_ip_ok(ip):
        return False
    r, g, b = hex_rgb(hex_color)
    payload = {"id": 1, "method": "setPilot", "params": {"state": True, "dimming": max(10, min(100, int(dim))), "r": r, "g": g, "b": b}}
    if native_on():
        native_enqueue({"k": "wiz", "ip": str(ip).strip(), "p": payload})
        return True
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.sendto(json.dumps(payload).encode("utf-8"), (str(ip).strip(), 38899))
        return True
    except OSError:
        return False
    finally:
        s.close()


def set_layers(vals):
    ss = st.session_state
    ss.cfg["layers"] = dict(vals)
    layers_of()
    ss.lay_rev = ss.get("lay_rev", 0) + 1


def bio_autopilot(hr):
    """Returns True when the atmosphere changed. Runs only on a transition between the calm and the elevated zone."""
    ss, cfg = st.session_state, st.session_state.cfg
    if not cfg.get("auto_mode") or ss.conn["mode"] != "home" or family_blocked():
        return False
    zone = "stress" if hr > ZEN_STRESS_BPM else "calm"
    if zone == ss.get("ap_zone"):
        return False
    ss.ap_zone = zone
    p = AP_PRESET[zone]
    why = "Auto-Pilot: " + ("heart rate above " + str(ZEN_STRESS_BPM) if zone == "stress" else "calm / resting")
    pool = [d for d in scope_devs() if d["room"] not in ss.room_mode]
    wiz_done = False
    for d in pool:
        if held(d):
            continue
        c = d["cid"]
        if c in BULBLIKE:
            set_dev(d, True, p["bright"], p["color"], why=why)
            if d["proto"].startswith("Philips") and d["addr"] and d["addr"] == str(cfg.get("wiz_ip", "")).strip():
                wiz_done = True
        elif c == "ac":
            d["acmode"] = p["acmode"]
            set_dev(d, True, p["ac"], why=why)
        elif c == "fan":
            d["fanmode"] = p["fanmode"]
            set_dev(d, True, p["fan"], why=why)
    if cfg.get("wiz_ip") and not wiz_done:
        wiz_fire(cfg["wiz_ip"], p["color"], p["bright"])
    set_layers(p["layers"])
    if p["sound"] in ss.modes:
        apply_mode(p["sound"], why=False, devs=[], set_active=True)
    log(zt(p["msg"], hr=hr))
    try:
        ai_note(zt(p["msg"], hr=hr))
        player_cmd("play")
    except Exception:
        pass
    return True


def zen_autopilot_active():
    cfg = st.session_state.cfg
    return bool(cfg.get("auto_mode")) and bool(cfg.get("ap_on", True)) and st.session_state.ui_mode == "zen"


# ---- Zen Sanctuary: mood pills
ZEN_PILLS = (("rest", "zp_rest", "sleep", {"hz432": 40, "rain": 30, "stream": 0, "noise": 0}),
             ("focus", "zp_focus", "focus", {"hz432": 0, "rain": 0, "stream": 0, "noise": 25}),
             ("reading", "zp_reading", "reading", {"hz432": 0, "rain": 15, "stream": 20, "noise": 0}),
             ("night", "zp_night", "meditation", {"hz432": 45, "rain": 0, "stream": 10, "noise": 0}))


def cb_zen_pill(kind):
    ss = st.session_state
    spec = next((p for p in ZEN_PILLS if p[0] == kind), None)
    if not spec:
        return
    room = ss.presence["room"]
    clear_room_override(room)
    msg = run_auto_mode(spec[2], "app")
    set_layers(spec[3])
    if kind == "rest":
        ss.fade_tok += 1
    ss.pill_on = kind
    if msg:
        ss.flash = msg


def render_zen_pills():
    ss = st.session_state
    st.markdown("**" + zt("zk_pills") + "**")
    for col, (k, lk, _mid, _lay) in zip(st.columns(4), ZEN_PILLS):
        col.button(zt(lk), key="zpill_" + k, width='stretch',
                   type=("primary" if ss.get("pill_on") == k else "secondary"), on_click=cb_zen_pill, args=(k,))


# ---- Zen Sanctuary: heart-rate graph + emotion badge + breathing cadence
def zen_css():
    p = pal()
    return ("<style>.zs-badge{display:inline-block;padding:8px 18px;border-radius:999px;font-weight:700;font-size:1.02rem;margin:4px 0 6px 0;"
            "border:1.5px solid var(--c);background:var(--b);color:" + p["TXT"] + ";animation:zsp 3.2s ease-in-out infinite}"
            "@keyframes zsp{0%,100%{box-shadow:0 0 0 0 var(--b)}50%{box-shadow:0 0 18px 4px var(--b)}}"
            ".zs-bw{display:flex;align-items:center;gap:16px;margin:6px 0 8px 0}"
            ".zs-orb{width:54px;height:54px;border-radius:50%;flex:none;background:radial-gradient(circle at 35% 30%,#fff8,var(--c));"
            "animation:zsb 10s ease-in-out infinite}"
            "@keyframes zsb{0%{transform:scale(.62)}40%{transform:scale(1.08)}100%{transform:scale(.62)}}"
            ".zs-cue{position:relative;height:1.4em;min-width:11em;font-weight:600;color:" + p["TXT"] + "}"
            ".zs-cue span{position:absolute;left:0;top:0;opacity:0}"
            ".zs-in{animation:zsi 10s linear infinite}.zs-out{animation:zso 10s linear infinite}"
            "@keyframes zsi{0%,36%{opacity:1}42%,100%{opacity:0}}@keyframes zso{0%,38%{opacity:0}44%,96%{opacity:1}100%{opacity:0}}"
            "@media (prefers-reduced-motion:reduce){.zs-badge,.zs-orb,.zs-in,.zs-out{animation:none}.zs-out{opacity:0}.zs-in{opacity:1}}"
            "</style>")


def zen_zone(hr):
    if hr < 70:
        return "calm", "zk_calm", "#2E9E6B", "rgba(46,158,107,.20)"
    if hr <= ZEN_STRESS_BPM:
        return "bal", "zk_bal", "#D9A21B", "rgba(217,162,27,.20)"
    return "high", "zk_high", "#E5484D", "rgba(229,72,77,.20)"


def zen_hr_card(r):
    ss = st.session_state
    hr = int(r["hr"])
    zone, key, col, bg = zen_zone(hr)
    src = r.get("src") or ("live" if r.get("live") else "simulation")
    parts = [zen_css(), '<div class="zs-badge" style="--c:' + col + ";--b:" + bg + '">' + html.escape(zt(key)) + "  ·  " +
             str(hr) + " BPM</div>"]
    if zone == "high":
        parts.append('<div class="zs-bw" style="--c:' + col + '"><div class="zs-orb"></div><div class="zs-cue"><span class="zs-in">' +
                     html.escape(zt("zk_in")) + '</span><span class="zs-out">' + html.escape(zt("zk_out")) + "</span></div></div>")
    st.markdown("**" + zt("zk_hr") + "**")
    st.markdown("".join(parts), unsafe_allow_html=True)
    themed_line_chart(list(ss.hr_hist)[-40:], 170)
    st.caption(zt("zk_src", s=src))


# ---- Zen Sanctuary: living player dock, mixer, conversational bar, voice assistant drawer
def cb_master(key):
    st.session_state.cfg["bed"] = max(0, min(100, int(st.session_state.get(key, 100))))


def cb_layer(k, key):
    layers = layers_of()
    layers[k] = int(st.session_state.get(key, 0))
    st.session_state.cfg["layers"] = layers


def render_zen_dock(shown):
    ss, cfg = st.session_state, st.session_state.cfg
    st.markdown("**" + zt("zk_dock") + "**")
    audio_component(synth_params(shown), True)
    mk = "zen_master_" + str(ss.get("lay_rev", 0))
    st.slider(zt("zk_master"), 0, 100, value=int(cfg.get("bed", 100)), key=mk, on_change=cb_master, args=(mk,))
    with st.expander(zt("zk_mixer")):
        layers = layers_of()
        for k, lk in LAYER_KEYS:
            key = "lay_" + k + "_" + str(ss.get("lay_rev", 0))
            st.slider(zt(lk), 0, 100, value=layers[k], key=key, on_change=cb_layer, args=(k, key))


def render_tell_bar():
    ss = st.session_state
    st.markdown("**" + zt("zk_tell") + "**")
    st.caption(zt("zk_tell_hint"))
    render_voice_mic()
    cols = st.columns(3)
    for col, (k, text) in zip(cols, (("tired", "I'm tired"), ("work", "Starting work"), ("movie", "Family movie time"))):
        col.button(t("voice_" + k), key="voice_p_" + k, on_click=cb_voice_preset, args=(text,))
    if ss.voice_last:
        st.caption(ss.voice_last)


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))          # no packet is sent; this only picks the outgoing interface
        return s.getsockname()[0]
    except OSError:
        return "localhost"
    finally:
        s.close()


def cb_va_open(flag):
    st.session_state.va_open = bool(flag)


def cb_va_mark(key):
    ss = st.session_state
    if ss.get(key):
        ss.va_linked, ss.va_open = True, False


def render_va_drawer():
    ss = st.session_state
    if ss.get("va_linked") and not ss.get("va_open"):
        st.button(zt("zk_va_done"), key="va_edit_btn", on_click=cb_va_open, args=(True,))
        return
    if not ss.get("va_open"):
        st.button(zt("zk_va_cfg"), key="va_cfg_btn", on_click=cb_va_open, args=(True,))
        return
    st.button("✕", key="va_close_btn", on_click=cb_va_open, args=(False,))
    render_assistant_card()
    base = app_base_url()
    tok = _secret("AURASYNC_TOKEN")
    unlocked = bool(tok) and bool(ss.get("auto_admin"))
    local = "http://" + lan_ip() + ":8501"
    for lbl, root in ((zt("zk_va_local"), local), (zt("zk_va_remote"), base or "https://YOUR-APP-URL")):
        st.caption(lbl)
        if unlocked:
            st.code(root.rstrip("/") + "/?" + urllib.parse.urlencode({"mode": "reading", "token": str(tok)}), language=None)
        else:
            st.code(root.rstrip("/") + "/?mode=reading&token=YOUR_TOKEN", language=None)
    if not unlocked:
        st.caption(zt("zk_va_unlock"))
    st.markdown("**" + zt("zk_va_google") + "**")
    st.markdown("1. " + zt("zk_va_g1") + "\n2. " + zt("zk_va_g2") + "\n3. " + zt("zk_va_g3"))
    mk = "va_mark_" + str(ss.get("va_rev", 0))
    st.toggle(zt("zk_va_mark"), value=False, key=mk, on_change=cb_va_mark, args=(mk,))


# ---- Manual Control Mode (granular dials)
def _dev_uid(uid):
    return next((d for d in st.session_state.fleet if d["uid"] == uid), None)


def cb_mc(uid, what, key):
    ss = st.session_state
    d = _dev_uid(uid)
    if what in ("tempd", "acp", "fanp") and d is not None:
        v = key                                      # pill / stepper buttons pass their value directly
    elif d is None or key not in ss:
        return
    else:
        v = ss[key]
    if what == "pwr":
        set_dev(d, bool(v), why="Manual")
    elif what == "lvl":
        set_dev(d, lvl=int(v), why="Manual")
    elif what == "col":
        set_dev(d, color=str(v), why="Manual")
    elif what == "temp":
        set_dev(d, True, int(v), why="Manual")
    elif what == "tempd":
        set_dev(d, lvl=max(18, min(30, int(d["lvl"]) + int(v))), why="Manual")
    elif what in ("acm", "acp"):
        d["acmode"] = str(v)
        d["rev"] = d.get("rev", 0) + 1
        push(d)
    elif what in ("fan", "fanp"):
        d["fanmode"] = str(v)
        set_dev(d, str(v) != "Off", FAN_LEVELS.get(str(v), 2), why="Manual")
        d["rev"] = d.get("rev", 0) + 1
    hold(d, 900)                                     # automation leaves manually tuned devices alone for 15 minutes


def cb_endpoints():
    ss, cfg = st.session_state, st.session_state.cfg
    ip = str(ss.get("ep_wiz") or "").strip()
    acu, fnu = str(ss.get("ep_ac") or "").strip(), str(ss.get("ep_fan") or "").strip()
    ok_url = lambda u: (not u) or (u.startswith("http://") or u.startswith("https://"))
    if (ip and not wiz_ip_ok(ip)) or not ok_url(acu) or not ok_url(fnu):
        ss.ep_msg = ("bad", "zk_ep_bad")
        return
    cfg["wiz_ip"] = ip
    for d in space_devs(current_room()):
        if d["cid"] in BULBLIKE and ip:
            d.update(proto="Philips WiZ (UDP)", addr=ip, status="connected")
        elif d["cid"] == "ac" and acu:
            d.update(proto="Home Assistant / REST", addr=acu, status="connected")
        elif d["cid"] == "fan" and fnu:
            d.update(proto="Home Assistant / REST", addr=fnu, status="connected")
    ss.ep_msg = ("ok", "zk_ep_ok")


def render_manual_controls():
    ss, cfg = st.session_state, st.session_state.cfg
    room = current_room()
    devs = space_devs(room)
    pick = lambda cids: next((d for d in devs if d["cid"] in cids), None)
    bulb, ac, fan = pick(BULBLIKE), pick(("ac",)), pick(("fan",))
    st.markdown("**" + zt("zk_manual") + "**  ·  " + html.escape(tr_room(room)))
    st.caption(zt("zk_manual_note"))
    c1, c2 = st.columns(2)
    with c1, _keyed_container("gcard_bulb"):
        st.markdown('<div class="gc-t">💡 ' + html.escape(zt("zk_bulb")) + "</div>", unsafe_allow_html=True)
        if bulb:
            k = "_" + str(bulb["uid"]) + "_" + str(bulb.get("rev", 0))
            hexc = safe_hex(bulb["color"])
            glow = (0.25 + 0.75 * max(0, min(100, bulb["lvl"])) / 100.0) if bulb["on"] else 0.12
            st.toggle(zt("zk_power"), value=bool(bulb["on"]), key="mcp" + k, on_change=cb_mc, args=(bulb["uid"], "pwr", "mcp" + k))
            st.markdown('<div class="gc-sw" style="background:' + hexc + ";opacity:" + ("%.2f" % glow) + ";box-shadow:0 0 " +
                        str(int(14 + 30 * glow)) + "px " + hexc + '88"></div>', unsafe_allow_html=True)
            st.color_picker(zt("zk_color"), value=hexc, key="mcc" + k, on_change=cb_mc, args=(bulb["uid"], "col", "mcc" + k))
            st.slider(zt("zk_bright"), 5, 100, value=int(max(5, bulb["lvl"])), key="mcl" + k, on_change=cb_mc, args=(bulb["uid"], "lvl", "mcl" + k))
        else:
            st.caption(zt("zk_nodev", d=zt("zk_bulb")))
    with c2, _keyed_container("gcard_ac"):
        st.markdown('<div class="gc-t">❄️ ' + html.escape(zt("zk_ac")) + "</div>", unsafe_allow_html=True)
        if ac:
            k = "_" + str(ac["uid"]) + "_" + str(ac.get("rev", 0))
            st.toggle(zt("zk_power"), value=bool(ac["on"]), key="map" + k, on_change=cb_mc, args=(ac["uid"], "pwr", "map" + k))
            m, v, p = st.columns([1, 2, 1])
            m.button("−", key="acm" + k, width='stretch', on_click=cb_mc, args=(ac["uid"], "tempd", -1))
            v.markdown('<div class="gc-temp">' + str(int(ac["lvl"])) + "°C</div>", unsafe_allow_html=True)
            p.button("+", key="acq" + k, width='stretch', on_click=cb_mc, args=(ac["uid"], "tempd", 1))
            cur = ac.get("acmode") or "Cool"
            for col, (val, lk) in zip(st.columns(3), (("Cool", "lx_cool"), ("Sleep Eco", "lx_eco"), ("Fan Only", "lx_fan"))):
                col.button(zt(lk), key="acp" + k + val, width='stretch', type=("primary" if cur == val else "secondary"),
                           on_click=cb_mc, args=(ac["uid"], "acp", val))
        else:
            st.caption(zt("zk_nodev", d=zt("zk_ac")))
    with _keyed_container("gcard_fan"):
        st.markdown('<div class="gc-t">🌀 ' + html.escape(zt("zk_fan")) + "</div>", unsafe_allow_html=True)
        if fan:
            k = "_" + str(fan["uid"]) + "_" + str(fan.get("rev", 0))
            st.toggle(zt("zk_power"), value=bool(fan["on"]), key="mfp" + k, on_change=cb_mc, args=(fan["uid"], "pwr", "mfp" + k))
            cur = fan.get("fanmode") if fan.get("fanmode") in FAN_LEVELS else ("Off" if not fan["on"] else next(
                (n for n in ("Low", "Medium", "High") if FAN_LEVELS[n] >= fan["lvl"]), "High"))
            if not fan["on"]:
                cur = "Off"
            for col, name in zip(st.columns(len(FAN_LEVELS)), FAN_LEVELS):
                col.button(zt("fan_" + name), key="mfq" + k + name, width='stretch', type=("primary" if cur == name else "secondary"),
                           on_click=cb_mc, args=(fan["uid"], "fanp", name))
        else:
            st.caption(zt("zk_nodev", d=zt("zk_fan")))
    if st.button("\u2795 Add a device", key="zk_aw_open"):
        open_add_wizard()
    with st.expander(zt("zk_endp")):
        with st.form("ep_form_" + room):
            st.text_input(zt("zk_wiz"), value=str(cfg.get("wiz_ip", "")), key="ep_wiz", max_chars=45)
            st.text_input(zt("zk_acurl"), value=str((ac or {}).get("addr", "")), key="ep_ac", max_chars=300)
            st.text_input(zt("zk_fanurl"), value=str((fan or {}).get("addr", "")), key="ep_fan", max_chars=300)
            st.form_submit_button(zt("zk_save"), on_click=cb_endpoints)
        msg = ss.get("ep_msg")
        if msg:
            (st.success if msg[0] == "ok" else st.error)(zt(msg[1]))


# ---- Luxury shell: header, Zen | Manual switch, pinned Biometric Simulator
T.update({
    "lx_zen": ("Zen Mode",), "lx_manual": ("Manual Mode",),
    "lx_sim_h": ("🧪 Biometric Simulator",), "lx_sim_c": ("Test the auto-pilot without a watch.",),
    "lx_sim_s": ("Heart rate (BPM)",), "lx_sim_b": ("Send reading",),
    "lx_sim_f": ("Live feed file: aurasync_bridge.json",), "lx_sim_last": ("Last reading sent: {hr} BPM",),
    "lx_cool": ("Cool",), "lx_eco": ("Eco",), "lx_fan": ("Fan",),
})


def render_lux_header():
    st.markdown(
        f'<h1 class="lux-h1" translate="no"><span class="lux-gold">AURA</span></h1>'
        f'<p class="lux-sub">{t("sub")}</p>',
        unsafe_allow_html=True
    )


def cb_flow(key):
    """Zen Mode = biometric auto-pilot on, Manual Mode = automatic takeover paused."""
    ss, cfg = st.session_state, st.session_state.cfg
    v = ss.get(key)
    if v in ("zen", "manual"):
        cfg["auto_mode"] = (v == "zen")
    ss.flow_rev = ss.get("flow_rev", 0) + 1


def render_flow_switch():
    ss, cfg = st.session_state, st.session_state.cfg
    cur = "zen" if cfg.get("auto_mode") else "manual"
    key = "flowsw_" + cur + "_" + str(ss.get("flow_rev", 0))
    box = _keyed_container("flowsw")
    with box:
        seg("Mode", ["zen", "manual"], key, lambda m: ("● " if m == cur else "○ ") + zt("lx_zen" if m == "zen" else "lx_manual"),
            on_change=cb_flow, args=(key,), selected=cur, hide_label=True)


def _keyed_container(name):
    try:
        return st.container(key=name)
    except TypeError:
        return st.container()


def write_bridge(hr):
    """Atomic write of the live feed file that read_bridge() watches."""
    payload = json.dumps({"heart_rate": int(hr), "hr": int(hr), "timestamp": time.time(), "source": "simulator"})
    for p in _bridge_paths():
        try:
            tmp = p + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(payload)
            os.replace(tmp, p)
            _BRIDGE_CACHE.clear()
            return True
        except OSError:
            continue
    return False


def cb_sim_send():
    ss = st.session_state
    try:
        hr = int(ss.get("sim_bpm", 75))
    except (TypeError, ValueError):
        hr = 75
    hr = max(45, min(140, hr))
    ss.hr_hist = (list(ss.get("hr_hist") or []) + [hr])[-60:]
    if not write_bridge(hr):                              # read-only host: fall back to an in-session reading
        ss.url_hr = {"hr": hr, "ts": time.time()}
    ss.sim_last = hr
    try:
        if zen_autopilot_active() and ss.conn["mode"] == "home" and bio_autopilot(hr):
            ss.flash = zt(AP_PRESET[ss.ap_zone]["msg"], hr=hr)
    except Exception as e:
        log("Simulator auto-pilot skipped: " + type(e).__name__)


def render_bio_simulator():
    ss = st.session_state
    with _keyed_container("simbox"):
        st.markdown('<div class="sim-h">' + html.escape(zt("lx_sim_h")) + "</div>", unsafe_allow_html=True)
        st.caption(zt("lx_sim_c"))
        st.slider(zt("lx_sim_s"), 45, 140, value=75, key="sim_bpm")
        st.button(zt("lx_sim_b"), key="sim_send_btn", on_click=cb_sim_send, width='stretch')
        last = ss.get("sim_last")
        st.markdown('<div class="sim-f"><span class="pdot"></span>' + html.escape(zt("lx_sim_f")) +
                    ((" · " + html.escape(zt("lx_sim_last", hr=last))) if last else "") + "</div>", unsafe_allow_html=True)


# ---- Universal Wearables Hub
def cb_wear_link(name):
    ss = st.session_state
    links = dict(ss.get("wear_links") or {})
    links[name] = not links.get(name, False)
    ss.wear_links = links
    log(("Linked " if links[name] else "Unlinked ") + name + " (simulated cloud link)")


def render_wearables_hub():
    ss = st.session_state
    st.subheader("🔗 " + zt("zk_hub"))
    st.caption(zt("zk_hub_sub"))
    links = ss.get("wear_links") or {}
    for row in (WEAR_CLOUDS[:3], WEAR_CLOUDS[3:]):
        for col, (name, icon) in zip(st.columns(3), row):
            on = bool(links.get(name))
            with col:
                st.markdown("**" + icon + " " + html.escape(name) + "**")
                st.caption(zt("zk_linked") if on else zt("zk_notlinked"))
                st.button(zt("zk_unlink") if on else zt("zk_link"), key="wl_" + name, on_click=cb_wear_link, args=(name,),
                          type=("secondary" if on else "primary"))
    br = read_bridge()
    st.caption("🟢 " + zt("zk_bridge_live", hr=br["hr"], age=br["age"]) if br else "⚪ " + zt("zk_bridge_wait"))
    st.markdown("**" + zt("zk_ble") + "**")


def read_biometrics():
    ss = st.session_state
    cfg = ss.cfg
    last = ss.hr_hist[-1]
    live = multi_source_live()          # Bluetooth 0x180D, ?hr= link, bridge.py file
    if live:
        return live
    if cfg["source"] == "ble":
        b = ss.get("ble") or {}
        if b.get("hr") and time.time() - b.get("ts", 0) < b.get("ttl", 25):
            return {"hr": int(b["hr"]), "hrv": rmssd(b.get("rr", [])) or 55, "spo2": 97.0, "skin": 33.5,
                    "asleep": False, "live": True}
    if cfg["source"] == "wear":
        try:
            now = datetime.utcnow()
            url = (cfg["api_url"].replace("{start}", urllib.parse.quote((now - timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%S+00:00")))
                   .replace("{end}", urllib.parse.quote(now.strftime("%Y-%m-%dT%H:%M:%S+00:00"))))
            hdr = {"Authorization": "Bearer " + cfg["api_token"]} if cfg.get("api_token") else {}
            r = requests.get(url, headers=hdr, timeout=1.5)
            r.raise_for_status()
            raw = r.json()
            d = parse_hr_payload(raw)
            if d is None:
                raise ValueError("no heart rate in the answer")
            stage = str(d.get("sleep_stage", "")).lower()
            asleep = bool(d.get("asleep", d.get("sleeping", stage in ("light", "deep", "rem", "asleep"))))
            return {"hr": d["_hr"], "hrv": int(d.get("hrv", 55)),
                    "spo2": float(d.get("spo2", 97)), "skin": float(d.get("temperature", 33.5)),
                    "asleep": asleep, "flag": any(k in d for k in ("asleep", "sleeping", "sleep_stage")), "live": True}
        except Exception:
            pass
    sim = sim_linked_reading(last)      # wearable linked with one tap in the Wearables Hub (simulated)
    if sim:
        return sim
    tgt, hrv, skin, asleep = SCN[cfg["scn"]]
    hr = int(max(45, min(140, last + (tgt - last) * 0.35 + random.gauss(0, 1.5))))
    return {"hr": hr, "hrv": random.randint(hrv[0], hrv[1]), "spo2": round(random.uniform(96, 99), 1),
            "skin": round(skin + random.gauss(0, 0.15), 1), "asleep": asleep, "live": False}


def analyze(r):
    """Turn raw wearable numbers into a body state with a confidence and a plain-language reason."""
    ss, cfg = st.session_state, st.session_state.cfg
    hist = ss.hr_hist
    h = datetime.now().hour
    recent = hist[-5:]
    avg = sum(recent) / float(len(recent))
    slope = (recent[-1] - recent[0]) / float(max(1, len(recent) - 1))
    rest, hrv, prev = cfg["rest"], r["hrv"], ss.bstate
    sim = not r["live"]
    night = h >= 21 or h < 7
    if r.get("asleep") or (night and avg <= rest * 0.92 and hrv >= 60):
        state, conf = "sleep", 75 + min(20, max(0, int(rest - avg) * 2))
    elif prev != "wake" and time.time() - ss.sleep_ts < 600 and not r.get("asleep") \
            and (slope >= 1.0 or avg - min(hist[-10:]) >= 5 or r.get("flag") or sim) and (4 <= h <= 11 or sim):
        state, conf = "wake", 82
        ss.sleep_ts = 0.0
    elif prev == "wake" and ss.wake_ticks < 6:
        state, conf = "wake", 80
    elif avg >= cfg["thr"] or (prev == "stress" and avg >= cfg["thr"] - 5) or (hrv < 28 and avg >= rest * 1.3):
        state, conf = "stress", min(98, 60 + int((avg - cfg["thr"]) * 1.5) + max(0, (40 - hrv) // 2))
    elif avg < cfg["rel"] or (prev == "relaxed" and avg < cfg["rel"] + 3):
        state, conf = "relaxed", min(96, 70 + max(0, int(cfg["rel"] - avg)))
    else:
        state, conf = "active", 72
    if state == "sleep":
        ss.sleep_ts = time.time()
    ss.wake_ticks = ss.wake_ticks + 1 if state == "wake" else 0
    ss.bstate = state
    reason = "Heartbeat {:.0f} bpm, calm level {}, body warmth {} °C".format(avg, hrv, r["skin"])
    return {"state": state, "conf": max(50, min(99, conf)), "reason": reason}


def state_mode(state):
    h = datetime.now().hour
    if state == "sleep":
        return "Sleep"
    if state == "wake":
        return "Energize"
    if state == "stress":
        return "Deep Meditation"
    if state == "active":
        return "Focus" if h < 21 else "Relax Evening"
    if 6 <= h < 11:
        return "Zen Garden"
    if 11 <= h < 18:
        return "Focus"
    if 18 <= h < 22:
        return "Relax Evening"
    return "Sleep"


# ----------------------------------------------------------------------------
# Procedural music engine (Web Audio API).
# ----------------------------------------------------------------------------
ENGINE_JS = r"""
(function () {
  var A = { v: __VER__, ctx: null, playing: false, p: null, nodes: null, tick: null, timerH: null, tTok: null,
            genre: null, st: null, step: 0, nextT: 0, bus: null, deg: 4, arpI: 0, w: {}, nbuf: null,
            out: null, msd: null, el: null, keep: null, worker: null, unlocked: false, viaEl: false, lastTitle: null };
  var MOB = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  A.viaEl = MOB && ('srcObject' in HTMLMediaElement.prototype);
  var INS = ['Piano', 'Flute', 'Rain', 'Tabla', 'Veena', 'Singing Bowls', 'Strings', 'Ocean Waves', 'Sitar', 'Harp'];
  var TEN = 'BNNBBNNBBTTNNNNB';
  function NOTE(m) { return (A.tune || 440) * Math.pow(2, (m - 69) / 12); }
  var SC = { maj: [0, 2, 4, 5, 7, 9, 11], min: [0, 2, 3, 5, 7, 8, 10], pent: [0, 2, 4, 7, 9], mpent: [0, 3, 5, 7, 10],
             blues: [0, 3, 5, 6, 7, 10], lyd: [0, 2, 4, 6, 7, 9, 11], phr: [0, 1, 3, 5, 7, 8, 10], dor: [0, 2, 3, 5, 7, 9, 10] };
  function semi(sc, d) {
    var s = SC[sc], L = s.length, o = Math.floor(d / L), i = ((d % L) + L) % L;
    return s[i] + 12 * o;
  }
  function D(o) {
    var d = { ls: null, sw: 0, n: 3, pa: 0.1, rev: 0.25, kick: '', snare: '', hat: '', oh: '', bass: '', bw: 'sine',
              bl: 0.3, bd: 2, lead: '', lm: 'sparse', lt: 'pluck', lw: 'triangle', ll: 0.12, lo: 12, noise: 'none', nl: 0 };
    for (var k in o) { d[k] = o[k]; }
    return d;
  }
  var S = {
    'Pop': D({ sc: 'maj', root: 48, bpm: 108, prog: [0, 4, 5, 3], pw: 'triangle', pl: 0.8, cut: 5000,
      kick: 'x...x...x...x...', snare: '....x.......x...', hat: 'x.x.x.x.x.x.x.x.', bass: 'x..x..x...x.x...', bw: 'sawtooth', bl: 0.25,
      lead: 'x..x..x.x..x.x..', lm: 'walk', lw: 'square', ll: 0.1 }),
    'Rock': D({ sc: 'min', root: 40, bpm: 122, prog: [0, 5, 2, 6], pw: 'sawtooth', pl: 0.9, pa: 0.02, cut: 3200,
      kick: 'x.....x.x.....x.', snare: '....x.......x...', hat: 'x.x.x.x.x.x.x.x.', bass: 'x.x.x.x.x.x.x.x.', bw: 'sawtooth', bl: 0.3, bd: 1.5,
      lead: 'x...x.x.....x...', lm: 'walk', ls: 'mpent', lw: 'sawtooth', ll: 0.1 }),
    'Blues': D({ sc: 'dor', root: 45, bpm: 84, sw: 0.33, prog: [0, 0, 3, 0], n: 4, pw: 'triangle', pl: 0.7, cut: 2200,
      kick: 'x.......x.......', snare: '....x.......x...', hat: 'x.x.x.x.x.x.x.x.', bass: 'x...x...x...x...', bw: 'triangle', bl: 0.45, bd: 3,
      lead: 'x.....x...x.x...', lm: 'walk', ls: 'blues', lw: 'triangle', ll: 0.16 }),
    'Hip-Hop': D({ sc: 'min', root: 36, bpm: 90, sw: 0.2, prog: [0, 0, 5, 3], n: 4, pw: 'triangle', pl: 0.5, cut: 1500,
      kick: 'x..x......x.x...', snare: '....x.......x...', hat: 'x.x.x.x.x.x.x.xx', bass: 'x..x......x.x...', bw: 'sine', bl: 0.7, bd: 5,
      lead: '..x.....x...x...', lm: 'sparse', lt: 'bell', lw: 'sine', ll: 0.12, lo: 24 }),
    'Jazz': D({ sc: 'maj', root: 48, bpm: 100, sw: 0.33, prog: [1, 4, 0, 5], n: 4, pw: 'sine', pl: 0.7, pa: 0.15, cut: 3000, rev: 0.35,
      kick: 'x.......x.......', hat: 'x.x.x.x.x.x.x.x.', bass: 'x...x...x...x...', bw: 'triangle', bl: 0.45, bd: 3.5,
      lead: 'x.x...x.x.x...x.', lm: 'walk', ls: 'dor', lw: 'triangle', ll: 0.16 }),
    'Classical': D({ sc: 'maj', root: 48, bpm: 72, prog: [0, 3, 4, 0], pw: 'sine', pl: 0.7, pa: 0.2, cut: 4500, rev: 0.4,
      bass: 'x...............', bw: 'sine', bl: 0.35, bd: 12, lead: 'x.x.x.x.x.x.x.x.', lm: 'arp', lw: 'triangle', ll: 0.14 }),
    'Metal': D({ sc: 'phr', root: 36, bpm: 150, prog: [0, 0, 1, 0], pw: 'sawtooth', pl: 0.9, pa: 0.02, cut: 2800, rev: 0.1,
      kick: 'x.xxx.xxx.xxx.xx', snare: '....x.......x...', hat: 'x.x.x.x.x.x.x.x.', bass: 'xxxxxxxxxxxxxxxx', bw: 'sawtooth', bl: 0.22, bd: 0.8,
      lead: 'x..x..x.x..x.x..', lm: 'walk', ls: 'phr', lw: 'sawtooth', ll: 0.1 }),
    'Folk': D({ sc: 'maj', root: 50, bpm: 96, prog: [0, 3, 0, 4], pw: 'triangle', pl: 0.5, cut: 3500,
      kick: 'x.......x.......', hat: 'x.x.x.x.x.x.x.x.', bass: 'x.......x.......', bw: 'triangle', bl: 0.3, bd: 3,
      lead: 'x.xx.x.xx.xx.x.x', lm: 'arp', lw: 'triangle', ll: 0.15, noise: 'wind', nl: 0.03 }),
    'EDM': D({ sc: 'min', root: 45, bpm: 128, prog: [0, 5, 2, 6], pw: 'sawtooth', pl: 0.75, pa: 0.05, cut: 6000, rev: 0.2,
      kick: 'x...x...x...x...', snare: '....x.......x...', oh: '..x...x...x...x.', bass: '.x.x.x.x.x.x.x.x', bw: 'sawtooth', bl: 0.28, bd: 1.5,
      lead: 'xxxxxxxxxxxxxxxx', lm: 'arp', lw: 'sawtooth', ll: 0.07, lo: 24 }),
    'Country': D({ sc: 'maj', root: 43, bpm: 104, sw: 0.1, prog: [0, 0, 3, 4], pw: 'triangle', pl: 0.5, cut: 4000,
      kick: 'x...x...x...x...', snare: '....x.......x...', hat: 'x.x.x.x.x.x.x.x.', bass: 'x.......x.......', bw: 'triangle', bl: 0.4, bd: 3,
      lead: 'x.xx.x.x.xx.x.xx', lm: 'arp', lw: 'triangle', ll: 0.15, noise: 'wind', nl: 0.03 }),
    'Disco': D({ sc: 'min', root: 45, bpm: 118, prog: [0, 5, 3, 4], n: 4, pw: 'sawtooth', pl: 0.5, cut: 4500,
      kick: 'x...x...x...x...', snare: '....x.......x...', oh: '..x...x...x...x.', bass: 'x.xx.xx.x.xx.xx.', bw: 'sawtooth', bl: 0.25, bd: 1,
      lead: 'x.x.x.x.x.x.x.x.', lm: 'arp', lw: 'square', ll: 0.08 }),
    'OM Mantra': D({ sc: 'pent', root: 38, bpm: 40, prog: [0], pw: 'sine', pl: 1.0, pa: 0.35, cut: 900, rev: 0.7,
      bass: 'x...............', bw: 'sine', bl: 0.55, bd: 16, lead: 'x.......x.......', lm: 'sparse', lt: 'bell', lw: 'sine', ll: 0.25 }),
    'Chinese Zen': D({ sc: 'pent', root: 50, bpm: 56, prog: [0, 2, 1, 0], pw: 'sine', pl: 0.5, pa: 0.3, cut: 3500, rev: 0.5,
      bass: 'x...............', bw: 'sine', bl: 0.3, bd: 12, lead: 'x..x....x.....x.', lm: 'walk', ls: 'pent', lw: 'triangle', ll: 0.2,
      noise: 'wind', nl: 0.05 }),
    'Lo-Fi Chill': D({ sc: 'min', root: 45, bpm: 76, sw: 0.25, prog: [0, 5, 2, 6], n: 4, pw: 'triangle', pl: 0.6, cut: 1700, rev: 0.4,
      kick: 'x.....x..x......', snare: '....x.......x...', hat: '..x...x...x...x.', bass: 'x.....x..x......', bw: 'sine', bl: 0.5, bd: 4,
      lead: '..x.....x..x....', lm: 'walk', ls: 'mpent', lw: 'triangle', ll: 0.18, lo: 24, noise: 'rain', nl: 0.12 }),
    'Calm 432Hz': D({ sc: 'pent', root: 45, tune: 432, bpm: 42, prog: [0, 2, 1, 0], n: 3, pw: 'sine', pl: 0.9, pa: 0.4, cut: 1200, rev: 0.8,
      bass: 'x...............', bw: 'sine', bl: 0.5, bd: 16, lead: 'x.......x.......', lm: 'sparse', lt: 'bell', lw: 'sine', ll: 0.18,
      lo: 24, noise: 'ocean', nl: 0.08 }),
    'Ambient Space': D({ sc: 'lyd', root: 43, bpm: 44, prog: [0, 4, 1, 5], n: 4, pw: 'sawtooth', pl: 0.5, pa: 0.4, cut: 1100, rev: 0.8,
      bass: 'x...............', bw: 'sine', bl: 0.4, bd: 16, lead: 'x.......x...x...', lm: 'sparse', lt: 'bell', lw: 'sine', ll: 0.2,
      lo: 24, noise: 'wind', nl: 0.07 })
  };
  function ensure() {
    if (!A.ctx) {
      var C = window.AudioContext || window.webkitAudioContext;
      try { A.ctx = new C({ latencyHint: 'playback' }); } catch (e) { A.ctx = new C(); }
      A.out = A.ctx.createGain(); A.out.gain.value = 1;
      A.ctx.onstatechange = function () { if (A.playing && A.ctx.state !== 'running') { A.revive(); } };
      wireOutput();
    }
    if (A.ctx.state !== 'running') { try { A.ctx.resume(); } catch (e) {} }
    return A.ctx;
  }
  /* Mobile: the soundscape goes through a real <audio> element (MediaStream), so iOS / Android treat it as media playback
     and keep it alive on the lock screen. Desktop keeps the direct Web Audio output. */
  function wireOutput() {
    var c = A.ctx;
    if (!c || !A.out) { return; }
    try { A.out.disconnect(); } catch (e) {}
    if (A.viaEl && c.createMediaStreamDestination) {
      if (!A.msd) { A.msd = c.createMediaStreamDestination(); }
      A.out.connect(A.msd);
    } else { A.out.connect(c.destination); }
  }
  function silentWav() {
    var n = 8000, b = new Uint8Array(44 + n), dv = new DataView(b.buffer), i, bin = '';
    function w(o, s) { for (var k = 0; k < s.length; k++) { b[o + k] = s.charCodeAt(k); } }
    w(0, 'RIFF'); dv.setUint32(4, 36 + n, true); w(8, 'WAVE'); w(12, 'fmt '); dv.setUint32(16, 16, true);
    dv.setUint16(20, 1, true); dv.setUint16(22, 1, true); dv.setUint32(24, 8000, true); dv.setUint32(28, 8000, true);
    dv.setUint16(32, 1, true); dv.setUint16(34, 8, true); w(36, 'data'); dv.setUint32(40, n, true);
    for (i = 0; i < n; i++) { b[44 + i] = 128; }
    for (i = 0; i < b.length; i++) { bin += String.fromCharCode(b[i]); }
    return 'data:audio/wav;base64,' + btoa(bin);
  }
  function mkAudio(id) {
    var el = document.getElementById(id);
    if (!el) {
      el = document.createElement('audio'); el.id = id;
      el.setAttribute('playsinline', ''); el.setAttribute('webkit-playsinline', ''); el.setAttribute('x-webkit-airplay', 'allow');
      el.playsInline = true; el.loop = true; el.preload = 'auto'; el.controls = false;
      el.style.cssText = 'position:fixed;left:0;bottom:0;width:1px;height:1px;opacity:0.01;pointer-events:none;z-index:-1;';
      (document.body || document.documentElement).appendChild(el);
    }
    return el;
  }
  function mediaEls() {
    if (!A.keep) {
      A.keep = mkAudio('aura-keepalive');
      if (!A.keep.getAttribute('src')) { A.keep.src = silentWav(); }
      A.keep.addEventListener('pause', function () { if (A.playing) { setTimeout(function () { if (A.playing) { A.revive(); } }, 400); } });
    }
    if (!A.el) { A.el = mkAudio('aura-output'); }
    window.__auraEls = [A.keep, A.el];   /* strong references: never garbage collected */
  }
  function art() {
    if (!A.artUrl) {
      try {
        var cv = document.createElement('canvas'); cv.width = 512; cv.height = 512;
        var g = cv.getContext('2d'), gr = g.createLinearGradient(0, 0, 512, 512);
        gr.addColorStop(0, '#0B0B0B'); gr.addColorStop(1, '#3A2F0B'); g.fillStyle = gr; g.fillRect(0, 0, 512, 512);
        g.fillStyle = '#D4AF37'; g.beginPath(); g.arc(256, 256, 150, 0, 6.2832); g.fill();
        g.fillStyle = '#0B0B0B'; g.font = 'bold 200px sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
        g.fillText('\u2726', 256, 262);
        A.artUrl = cv.toDataURL('image/png');
      } catch (e) { A.artUrl = ''; }
    }
    return A.artUrl ? [{ src: A.artUrl, sizes: '512x512', type: 'image/png' }] : [];
  }
  function tone(type, f, t, peak, dur, dest, atk, det, fl) {
    var c = A.ctx, o = c.createOscillator(), g = c.createGain(), a = atk || 0.01, e = t + Math.max(dur, a + 0.05), fx = null;
    o.type = type; o.frequency.setValueAtTime(f, t);
    if (det) { o.detune.value = det; }
    g.gain.setValueAtTime(0.0001, t);
    g.gain.linearRampToValueAtTime(peak, t + a);
    g.gain.exponentialRampToValueAtTime(0.0005, e);
    if (fl) {
      fx = c.createBiquadFilter(); fx.type = fl[0]; fx.frequency.setValueAtTime(fl[1], t); fx.Q.value = fl[2] || 1;
      o.connect(fx); fx.connect(g);
    } else { o.connect(g); }
    g.connect(dest); o.start(t); o.stop(e + 0.1);
    o.fx = fx;
    return o;
  }
  function pad(type, f, t, peak, att, dur, dest, det, fl) {
    var c = A.ctx, o = c.createOscillator(), g = c.createGain(), fx = null;
    o.type = type; o.frequency.setValueAtTime(f, t);
    if (det) { o.detune.value = det; }
    g.gain.setValueAtTime(0.0001, t);
    g.gain.linearRampToValueAtTime(peak, t + att);
    g.gain.setValueAtTime(peak, t + dur * 0.6);
    g.gain.exponentialRampToValueAtTime(0.0005, t + dur);
    if (fl) {
      fx = c.createBiquadFilter(); fx.type = fl[0]; fx.frequency.value = fl[1]; fx.Q.value = fl[2] || 1;
      o.connect(fx); fx.connect(g);
    } else { o.connect(g); }
    g.connect(dest); o.start(t); o.stop(t + dur + 0.1);
    o.fx = fx;
    return o;
  }
  function nburst(t, dur, type, freq, peak, dest) {
    var c = A.ctx, s = c.createBufferSource(), f = c.createBiquadFilter(), g = c.createGain();
    s.buffer = A.nbuf; f.type = type; f.frequency.value = freq;
    g.gain.setValueAtTime(peak, t); g.gain.exponentialRampToValueAtTime(0.0005, t + dur);
    s.connect(f); f.connect(g); g.connect(dest); s.start(t, Math.random()); s.stop(t + dur + 0.05);
  }
  function kick(t, d) { var o = tone('sine', 150, t, 0.9, 0.3, d, 0.003); o.frequency.exponentialRampToValueAtTime(42, t + 0.14); }
  function snare(t, d) { nburst(t, 0.18, 'highpass', 1800, 0.35, d); tone('triangle', 190, t, 0.25, 0.12, d, 0.003); }
  function hat(t, d, open) { nburst(t, open ? 0.22 : 0.05, 'highpass', 7000, open ? 0.12 : 0.09, d); }
  function bell(f, t, peak, d) { tone('sine', f, t, peak, 7, d, 0.01); tone('sine', f * 2.76, t, peak * 0.4, 4, d, 0.01); }

  /* ---- the ten instrument voices ---- */
  function piano(f, t, vel, d) {
    var amp = [1, 0.5, 0.28, 0.14, 0.07];
    for (var i = 0; i < amp.length; i++) { tone('sine', f * (i + 1), t, 0.34 * vel * amp[i], 2.6 / (1 + i * 0.7), d, 0.004); }
    nburst(t, 0.03, 'bandpass', 2200, 0.08 * vel, d);
  }
  function flute(f, t, dur, d) {
    var c = A.ctx, o = pad('sine', f, t, 0.34, 0.1, dur, d, 0), lfo = c.createOscillator(), lg = c.createGain();
    pad('sine', f * 2, t, 0.06, 0.12, dur, d, 0);
    lfo.frequency.value = 5.2; lg.gain.value = 10; lfo.connect(lg); lg.connect(o.detune); lfo.start(t); lfo.stop(t + dur + 0.2);
    nburst(t, dur * 0.8, 'bandpass', 3200, 0.03, d);
  }
  function tabla(code, t, d) {
    if (code === 'B') { var o = tone('sine', 150, t, 0.6, 0.5, d, 0.003); o.frequency.exponentialRampToValueAtTime(65, t + 0.3); }
    var open = (code === 'T'), f = open ? 560 : 430;
    tone('sine', f, t, 0.4, open ? 0.5 : 0.16, d, 0.002);
    tone('sine', f * 2.3, t, 0.15, open ? 0.3 : 0.08, d, 0.002);
    nburst(t, 0.025, 'bandpass', 3000, 0.14, d);
  }
  function veena(f, t, d) {
    var o = tone('sawtooth', f, t, 0.26, 1.6, d, 0.004, 0, ['lowpass', 3600, 2]);
    o.frequency.setValueAtTime(f * 1.05, t); o.frequency.exponentialRampToValueAtTime(f, t + 0.1);
    if (o.fx) { o.fx.frequency.exponentialRampToValueAtTime(700, t + 1.0); }
    tone('triangle', f * 2, t, 0.06, 0.9, d, 0.004);
  }
  function sitar(f, t, d) {
    var o = tone('sawtooth', f, t, 0.24, 1.4, d, 0.003, 0, ['bandpass', 2400, 5]);
    o.frequency.setValueAtTime(f * 0.97, t); o.frequency.exponentialRampToValueAtTime(f, t + 0.05);
    if (o.fx) { o.fx.frequency.exponentialRampToValueAtTime(900, t + 0.9); }
    tone('square', f * 1.5, t, 0.05, 0.6, d, 0.003, 0, ['lowpass', 2500, 1]);
  }
  function bowl(f, t, d) {
    [1, 2.71, 5.13].forEach(function (r, i) {
      tone('sine', f * r, t, 0.34 / (1 + i * 1.3), 10 / (1 + i * 0.8), d, 0.01);
      tone('sine', f * r + 1.2 + i, t, 0.34 / (1 + i * 1.3), 10 / (1 + i * 0.8), d, 0.01);
    });
  }
  function strings(ch, t, bd, d) {
    ch.forEach(function (mid) {
      [-9, 0, 9].forEach(function (c) { pad('sawtooth', NOTE(mid + 12), t, 0.06, bd * 0.35, bd * 1.25, d, c, ['lowpass', 2300, 0.7]); });
    });
  }
  function harp(ch, t, d) {
    var notes = [], i;
    for (i = 0; i < ch.length; i++) { notes.push(ch[i] + 12); }
    for (i = 0; i < ch.length; i++) { notes.push(ch[i] + 24); }
    notes.forEach(function (m, k) {
      tone('triangle', NOTE(m), t + k * 0.09, 0.32, 2.4, d, 0.003);
      tone('sine', NOTE(m) * 2, t + k * 0.09, 0.08, 1.2, d, 0.003);
    });
  }
  function walk(k, sc) {
    var w = A.w, st = [-2, -1, -1, 0, 1, 1, 2];
    w[k] = (w[k] === undefined ? 3 : w[k]) + st[Math.floor(Math.random() * st.length)];
    if (w[k] < -2) { w[k] = -2; }
    if (w[k] > 9) { w[k] = 9; }
    return semi(sc, w[k]);
  }
  function chord(st, deg) {
    var r = [];
    for (var i = 0; i < st.n; i++) { r.push(st.root + semi(st.sc, deg + 2 * i)); }
    return r;
  }
  function leadFreq(st, ch) {
    var m;
    if (st.lm === 'arp') {
      var n = ch.length * 2, i = A.arpI % n; A.arpI += 1;
      m = ch[i % ch.length] + (i >= ch.length ? 12 : 0) + st.lo;
    } else if (st.lm === 'walk') {
      var steps = [-2, -1, -1, 0, 1, 1, 2];
      A.deg += steps[Math.floor(Math.random() * steps.length)];
      if (A.deg < -2) { A.deg = -2; }
      if (A.deg > 9) { A.deg = 9; }
      m = st.root + semi(st.ls || st.sc, A.deg) + st.lo;
    } else {
      m = ch[Math.floor(Math.random() * ch.length)] + st.lo + (Math.random() < 0.4 ? 12 : 0);
    }
    return NOTE(m);
  }
  function mkBus(st) {
    var c = A.ctx, n = A.nodes, g = c.createGain(), lp = c.createBiquadFilter(), sd = c.createGain();
    lp.type = 'lowpass'; lp.frequency.value = st.cut; sd.gain.value = st.rev;
    g.connect(lp); lp.connect(n.master); lp.connect(sd); sd.connect(n.dly);
    return { g: g, lp: lp, sd: sd };
  }
  A.bedLevel = function () { return (((A.p && A.p.bed !== undefined) ? A.p.bed : 100) / 100) * (A.ducked ? 0.3 : 1); };
  A.setStyle = function (g) {
    var c = A.ctx, now = c.currentTime, old = A.bus;
    A.genre = g; A.st = S[g] || S['Ambient Space']; A.tune = A.st.tune || 440;
    var nb = mkBus(A.st);
    if (old) {
      old.g.gain.cancelScheduledValues(now);
      old.g.gain.setTargetAtTime(0, now, 0.15);
      setTimeout(function () { try { old.g.disconnect(); old.lp.disconnect(); old.sd.disconnect(); } catch (e) {} }, 1500);
    }
    nb.g.gain.setValueAtTime(0.0001, now); nb.g.gain.setTargetAtTime(A.bedLevel(), now + 0.05, 0.2);
    A.bus = nb; A.step = 0; A.nextT = now + 0.12; A.deg = 4; A.arpI = 0; A.w = {};
    A.applyNoise();
  };
  A.applyBed = function () { if (A.bus && !(A.fadeEnd && A.ctx.currentTime < A.fadeEnd)) { A.bus.g.gain.setTargetAtTime(A.bedLevel(), A.ctx.currentTime, 0.15); } };
  A.applyNoise = function () {
    var n = A.nodes, st = A.st;
    if (!n || !st) { return; }
    var now = A.ctx.currentTime;
    n.rain.gain.setTargetAtTime(st.noise === 'rain' ? st.nl * 0.8 : 0, now, 0.6);
    n.wind.gain.setTargetAtTime(st.noise === 'wind' ? st.nl * 1.2 : 0, now, 0.6);
    n.ocean.gain.setTargetAtTime(st.noise === 'ocean' ? st.nl : 0, now, 0.6);
  };
  A.applyMix = function () {
    var n = A.nodes, m = (A.p && A.p.mix) || {};
    if (!n) { return; }
    var now = A.ctx.currentTime;
    INS.forEach(function (k) { if (n.inst && n.inst[k]) { n.inst[k].gain.setTargetAtTime((Number(m[k]) || 0) / 100, now, 0.08); } });
  };
  A.play = function (s, bar, t, dur) {
    var st = A.st, m = A.p.mix || {}, d = A.bus.g;
    function L(k) { return (m[k] || 0) / 100; }
    function G(k) { return A.nodes.inst[k]; }
    var deg = st.prog[bar % st.prog.length], ch = chord(st, deg), rootM = st.root + semi(st.sc, deg);
    if (s === 0) {
      var bd = dur * 16;
      ch.forEach(function (mid) {
        var f = NOTE(mid);
        pad(st.pw, f, t, 0.05 * st.pl, bd * st.pa + 0.05, bd * 1.1, d, 6);
        pad(st.pw, f, t, 0.05 * st.pl, bd * st.pa + 0.05, bd * 1.1, d, -6);
      });
    }
    if (st.kick.charAt(s) === 'x') { kick(t, d); }
    if (st.snare.charAt(s) === 'x') { snare(t, d); }
    if (st.hat.charAt(s) === 'x') { hat(t, d, false); }
    if (st.oh.charAt(s) === 'x') { hat(t, d, true); }
    if (st.bass.charAt(s) === 'x') { tone(st.bw, NOTE(rootM - 12), t, 0.3 * st.bl, dur * st.bd, d, 0.01); }
    if (st.lead.charAt(s) === 'x') {
      var f2 = leadFreq(st, ch);
      if (st.lt === 'bell') { bell(f2, t, st.ll * 0.5, d); } else { tone(st.lw, f2, t, st.ll * 0.6, 0.55, d, 0.005); }
    }
    /* instruments: each one plays only while its own slider is above zero */
    if (L('Piano') > 0.02) {
      if (s % 8 === 0) { ch.forEach(function (mid, i) { piano(NOTE(mid), t + i * 0.035, 0.9, G('Piano')); }); }
      else if (s % 4 === 2 && Math.random() < 0.8) { piano(NOTE(st.root + 12 + walk('pi', st.ls || st.sc)), t, 0.8, G('Piano')); }
    }
    if (L('Flute') > 0.02 && s % 8 === 2 && Math.random() < 0.85) {
      flute(NOTE(st.root + 24 + walk('fl', 'pent')), t, dur * 7, G('Flute'));
    }
    if (L('Tabla') > 0.02 && s % 2 === 0) {
      var code = TEN.charAt(Math.floor(((bar % 2) * 16 + s) / 2));
      if (code !== '.') { tabla(code, t, G('Tabla')); }
    }
    if (L('Veena') > 0.02 && s % 2 === 0 && Math.random() < 0.6) { veena(NOTE(st.root + 12 + walk('ve', 'pent')), t, G('Veena')); }
    if (L('Sitar') > 0.02 && (s % 4 === 3 || s === 0) && Math.random() < 0.8) { sitar(NOTE(st.root + 12 + walk('si', 'pent')), t, G('Sitar')); }
    if (L('Harp') > 0.02 && s % 8 === 0) { harp(ch, t, G('Harp')); }
    if (L('Strings') > 0.02 && s === 0) { strings(ch, t, dur * 16, G('Strings')); }
    if (L('Singing Bowls') > 0.02 && s === 0 && bar % 2 === 0) { bowl(NOTE(st.root + 24 + (bar % 4 === 0 ? 0 : 7)), t, G('Singing Bowls')); }
    if (L('Rain') > 0.02 && Math.random() < 0.6) { nburst(t + Math.random() * dur, 0.025, 'highpass', 4000, 0.16, G('Rain')); }
  };
  A.sched = function () {
    if (!A.playing || !A.p || !A.nodes || !A.st || !A.bus) { return; }
    var c = A.ctx, now = c.currentTime, dur = 60 / A.st.bpm / 4;
    if (A.nextT < now - 0.3) { A.nextT = now + 0.05; }
    while (A.nextT < now + (document.hidden ? 20 : 0.35)) {
      var s = A.step % 16, bar = Math.floor(A.step / 16);
      var t = A.nextT + ((s % 2 === 1) ? A.st.sw * dur : 0);
      A.play(s, bar, t, dur);
      A.step += 1; A.nextT += dur;
    }
  };
  A.arm = function () {
    if (A.timerH) { clearTimeout(A.timerH); A.timerH = null; }
    if (A.playing && A.p && A.p.tMin > 0) { A.timerH = setTimeout(function () { A.stop(); }, A.p.tMin * 60000); }
  };
  A.update = function (p) {
    p = p || {};
    var mm = {}, srcMix = (p.mix && typeof p.mix === 'object') ? p.mix : {};
    INS.forEach(function (k) { var v = Number(srcMix[k]); mm[k] = isFinite(v) ? Math.max(0, Math.min(100, v)) : 0; });
    p.mix = mm;
    if (!p.genre) { p.genre = 'Ambient Space'; }
    A.p = p;
    if (p.tTok !== A.tTok) { A.tTok = p.tTok; A.arm(); }
    if (p.title !== A.lastTitle) { A.lastTitle = p.title; if (A.unlocked || A.playing) { A.session(); } }
    if (A.playing) { A.revive(); }
    if (A.playing) {
      if (p.genre !== A.genre) { A.setStyle(p.genre); } else { A.applyNoise(); A.applyBed(); }
      A.applyMix();
      A.fadeIn();
    }
  };
  A.fadeIn = function () {
    var p = A.p;
    if (!A.playing || !A.bus || !p || !p.fade || p.fadeTok === A.fadeTok) { return; }
    var now = A.ctx.currentTime;
    A.fadeTok = p.fadeTok; A.fadeEnd = now + p.fade;
    A.bus.g.gain.cancelScheduledValues(now);
    A.bus.g.gain.setValueAtTime(0.0001, now);
    A.bus.g.gain.linearRampToValueAtTime(A.bedLevel(), now + p.fade);
  };
  A.start = function () {
    if (A.playing) { return; }
    var c = ensure(), n = { srcs: [] };
    n.master = c.createGain(); n.master.gain.setValueAtTime(0.0001, c.currentTime);
    n.master.gain.linearRampToValueAtTime(0.7, c.currentTime + 1.5);
    n.comp = c.createDynamicsCompressor(); n.master.connect(n.comp); n.comp.connect(A.out);
    n.dly = c.createDelay(1.0); n.dly.delayTime.value = 0.375;
    n.fb = c.createGain(); n.fb.gain.value = 0.35; n.wet = c.createGain(); n.wet.gain.value = 0.8;
    n.dly.connect(n.fb); n.fb.connect(n.dly); n.dly.connect(n.wet); n.wet.connect(n.master);
    n.ibus = c.createGain(); n.ibus.gain.value = 1.5; n.ibus.connect(n.master);
    n.isend = c.createGain(); n.isend.gain.value = 0.3; n.ibus.connect(n.isend); n.isend.connect(n.dly);
    n.inst = {};
    INS.forEach(function (k) { var g = c.createGain(); g.gain.value = 0; g.connect(n.ibus); n.inst[k] = g; });
    var len = c.sampleRate * 2, buf = c.createBuffer(1, len, c.sampleRate), d = buf.getChannelData(0);
    for (var k = 0; k < len; k++) { d[k] = Math.random() * 2 - 1; }
    A.nbuf = buf;
    function bed(t1, f1, t2, f2, rate) {
      var s = c.createBufferSource(); s.buffer = buf; s.loop = true;
      var a = c.createBiquadFilter(); a.type = t1; a.frequency.value = f1; s.connect(a);
      var last = a;
      if (t2) { var b = c.createBiquadFilter(); b.type = t2; b.frequency.value = f2; a.connect(b); last = b; }
      var sw = c.createGain(); sw.gain.value = rate > 0 ? 0.6 : 1; last.connect(sw);
      if (rate > 0) {
        var o = c.createOscillator(); o.frequency.value = rate;
        var og = c.createGain(); og.gain.value = 0.4; o.connect(og); og.connect(sw.gain); o.start(); n.srcs.push(o);
      }
      var g = c.createGain(); g.gain.value = 0; sw.connect(g); g.connect(n.master); s.start(); n.srcs.push(s);
      return g;
    }
    n.rain = bed('highpass', 700, 'lowpass', 7000, 0);
    n.wind = bed('bandpass', 500, null, 0, 0.07);
    n.ocean = bed('lowpass', 450, null, 0, 0.1);
    /* instrument beds: continuous rain and ocean waves, each on its own slider gain */
    var rs = c.createBufferSource(); rs.buffer = buf; rs.loop = true;
    var rh = c.createBiquadFilter(); rh.type = 'highpass'; rh.frequency.value = 900;
    var rl = c.createBiquadFilter(); rl.type = 'lowpass'; rl.frequency.value = 7000;
    var rg = c.createGain(); rg.gain.value = 0.75;
    rs.connect(rh); rh.connect(rl); rl.connect(rg); rg.connect(n.inst['Rain']); rs.start(); n.srcs.push(rs);
    var os = c.createBufferSource(); os.buffer = buf; os.loop = true;
    var ol = c.createBiquadFilter(); ol.type = 'lowpass'; ol.frequency.value = 550;
    var sw2 = c.createGain(); sw2.gain.value = 0.5;
    var l1 = c.createOscillator(); l1.frequency.value = 0.09;
    var l1g = c.createGain(); l1g.gain.value = 0.4; l1.connect(l1g); l1g.connect(sw2.gain);
    var l2 = c.createOscillator(); l2.frequency.value = 0.13;
    var l2g = c.createGain(); l2g.gain.value = 250; l2.connect(l2g); l2g.connect(ol.frequency);
    os.connect(ol); ol.connect(sw2); sw2.connect(n.inst['Ocean Waves']); os.start(); l1.start(); l2.start();
    n.srcs.push(os, l1, l2);
    A.nodes = n; A.playing = true; A.bus = null;
    A.setStyle((A.p && A.p.genre) || 'Ambient Space');
    A.applyMix(); A.arm(); A.fadeIn();
    A.startTicker(); A.mediaOn();
  };
  A.stop = function () {
    var n = A.nodes;
    A.stopTicker();
    if (A.timerH) { clearTimeout(A.timerH); A.timerH = null; }
    A.playing = false; A.nodes = null; A.bus = null; A.genre = null; A.fadeEnd = 0;
    A.mediaOff();
    if (!n) { return; }
    n.master.gain.cancelScheduledValues(A.ctx.currentTime);
    n.master.gain.setTargetAtTime(0, A.ctx.currentTime, 0.25);
    setTimeout(function () {
      try { n.srcs.forEach(function (x) { x.stop(); }); n.master.disconnect(); } catch (e) {}
    }, 1500);
  };
  A.chime = function () {
    var c = ensure(), t0 = c.currentTime + 0.05;
    [880, 1318.5, 1760].forEach(function (f, i) { tone('sine', f, t0 + i * 0.18, 0.12, 1.6, A.out, 0.02); });
  };
  /* 1) unlock on the very first touch / click / key anywhere, so later automatic mood changes are never blocked */
  A.unlock = function () {
    try {
      var c = ensure();
      var b = c.createBuffer(1, 1, 22050), s = c.createBufferSource(); s.buffer = b; s.connect(c.destination); s.start(0);
      mediaEls();
      if (A.viaEl && c.createMediaStreamDestination) { wireOutput(); if (A.el.srcObject !== A.msd.stream) { A.el.srcObject = A.msd.stream; } }
      [A.keep, A.el].forEach(function (el) {
        if (!el || (el === A.el && !el.srcObject)) { return; }
        var pr = el.play();
        if (pr && pr.then) { pr.then(function () { if (!A.playing) { el.pause(); } }).catch(function () {}); }
      });
      A.unlocked = true; A.session();
    } catch (e) {}
  };
  var GEST = ['touchstart', 'touchend', 'pointerdown', 'mousedown', 'click', 'keydown'];
  function onGesture() {
    A.unlock();
    if (A.ctx && A.ctx.state === 'running') { GEST.forEach(function (ev) { document.removeEventListener(ev, onGesture, true); }); }
  }
  GEST.forEach(function (ev) { document.addEventListener(ev, onGesture, true); });
  /* 2) lock-screen persistence: Media Session metadata + play / pause handlers */
  A.session = function () {
    var ms = navigator.mediaSession;
    if (!ms) { return; }
    try {
      ms.metadata = new MediaMetadata({ title: 'AuraSync Soundscape', artist: 'Atmospheric AI',
                                        album: (A.p && A.p.title) || 'AuraSync', artwork: art() });
      ms.playbackState = A.playing ? 'playing' : 'paused';
      ms.setActionHandler('play', function () { A.start(); A.revive(); });
      ms.setActionHandler('pause', function () { A.stop(); });
      ms.setActionHandler('stop', function () { A.stop(); });
      ['seekbackward', 'seekforward', 'seekto', 'previoustrack', 'nexttrack'].forEach(function (a) {
        try { ms.setActionHandler(a, null); } catch (e) {}
      });
    } catch (e) {}
  };
  /* 3) hidden inline <audio> elements (playsinline, loop) that stay alive when the screen locks */
  A.mediaOn = function () {
    mediaEls();
    wireOutput();
    if (A.viaEl && A.msd) {
      if (A.el.srcObject !== A.msd.stream) { A.el.srcObject = A.msd.stream; }
      var pr = A.el.play();
      if (pr && pr.catch) { pr.catch(function () { A.viaEl = false; wireOutput(); }); }
      setTimeout(function () { if (A.playing && A.viaEl && A.el.paused) { A.viaEl = false; wireOutput(); } }, 2500);
    }
    var kp = A.keep.play();
    if (kp && kp.catch) { kp.catch(function () {}); }
    A.session();
  };
  A.mediaOff = function () {
    try { if (navigator.mediaSession) { navigator.mediaSession.playbackState = 'paused'; } } catch (e) {}
    setTimeout(function () {
      if (!A.playing) { try { if (A.keep) { A.keep.pause(); } if (A.el) { A.el.pause(); } } catch (e) {} }
    }, 1800);
  };
  A.revive = function () {
    var c = A.ctx;
    if (!c) { return; }
    if (c.state !== 'running') { try { c.resume(); } catch (e) {} }
    if (A.playing) {
      if (A.keep && A.keep.paused) { var k = A.keep.play(); if (k && k.catch) { k.catch(function () {}); } }
      if (A.viaEl && A.el && A.el.paused && A.el.srcObject) { var o = A.el.play(); if (o && o.catch) { o.catch(function () {}); } }
      try { if (navigator.mediaSession) { navigator.mediaSession.playbackState = 'playing'; } } catch (e) {}
    }
  };
  document.addEventListener('visibilitychange', function () { A.revive(); });
  window.addEventListener('pageshow', function () { A.revive(); });
  window.addEventListener('focus', function () { A.revive(); });
  window.addEventListener('online', function () { A.revive(); });
  setInterval(function () { if (A.playing) { A.revive(); } }, 3000);
  A.startTicker = function () {
    A.stopTicker();
    A.tick = setInterval(A.sched, 40);
    try {
      var url = URL.createObjectURL(new Blob(['setInterval(function(){postMessage(1);},40);'], { type: 'text/javascript' }));
      A.worker = new Worker(url);
      A.worker.onmessage = function () { A.sched(); };
      A.worker.onerror = function () { try { A.worker.terminate(); } catch (e) {} A.worker = null; };
    } catch (e) { A.worker = null; }
  };
  A.stopTicker = function () {
    if (A.tick) { clearInterval(A.tick); A.tick = null; }
    if (A.worker) { try { A.worker.terminate(); } catch (e) {} A.worker = null; }
  };
  /* ---- the soundtrack gets quieter while the companion speaks ---- */
  A.duck = function (on) {
    A.ducked = !!on;
    try { if (A.bus && A.ctx && !(A.fadeEnd && A.ctx.currentTime < A.fadeEnd)) { A.bus.g.gain.setTargetAtTime(A.bedLevel(), A.ctx.currentTime, 0.3); } } catch (e) {}
  };
  /* ---- spoken replies (browser speech synthesis, calm voice). State lives in the page, so it survives re-renders ---- */
  var MIC = (window.__auraMic = window.__auraMic || { state: 'idle', spokenId: '', thinkAt: 0, muted: false });
  function voicePick(lang) {
    var vs = (window.speechSynthesis && window.speechSynthesis.getVoices()) || [], want = String(lang || 'en-US').replace('_', '-').toLowerCase();
    var base = want.split('-')[0];
    var exact = vs.filter(function (v) { return v.lang && v.lang.replace('_', '-').toLowerCase() === want; });
    var pref = exact.concat(vs.filter(function (v) { return v.lang && v.lang.toLowerCase().indexOf(base) === 0 && exact.indexOf(v) < 0; }));
    var soft = /samantha|karen|moira|tessa|serena|ava|allison|joelle|shruti|veena|lekha|kyoko|yuna|google.*(female|uk|us)|natural|neural|aria|jenny|siri/i;
    for (var i = 0; i < pref.length; i++) { if (soft.test(pref[i].name)) { return pref[i]; } }
    return pref[0] || null;
  }
  A.canSpeak = function () { return !!(window.speechSynthesis && window.SpeechSynthesisUtterance); };
  A.unlockSpeech = function () {
    try { if (A.canSpeak()) { var u = new SpeechSynthesisUtterance(''); u.volume = 0; window.speechSynthesis.speak(u); } } catch (e) {}
  };
  A.stopSpeech = function () {
    try { if (window.speechSynthesis) { window.speechSynthesis.cancel(); } } catch (e) {}
    A.duck(false); if (MIC.state === 'speaking') { MIC.state = 'idle'; }
  };
  A.speak = function (text, lang) {
    if (!A.canSpeak() || MIC.muted || !text) { if (MIC.state !== 'listening') { MIC.state = 'idle'; } return false; }
    try {
      var syn = window.speechSynthesis; syn.cancel();
      var parts = String(text).match(/[^.!?\u2026]+[.!?\u2026]*/g) || [String(text)];
      parts.forEach(function (p, i) {
        p = p.trim(); if (!p) { return; }
        var u = new SpeechSynthesisUtterance(p);
        u.lang = lang || 'en-US'; var v = voicePick(u.lang); if (v) { u.voice = v; }
        u.rate = 0.92; u.pitch = 1.0; u.volume = 1;
        if (i === 0) { u.onstart = function () { MIC.state = 'speaking'; A.duck(true); }; }
        if (i === parts.length - 1) { u.onend = u.onerror = function () { A.duck(false); if (MIC.state === 'speaking') { MIC.state = 'idle'; } }; }
        syn.speak(u);
      });
      return true;
    } catch (e) { MIC.state = 'idle'; return false; }
  };
  /* ---- heart-rate wearables over standard Bluetooth (Web Bluetooth, Heart Rate profile) ---- */
  var HRM = A.hrm = { st: 'idle', name: '', hr: 0, rr: [], ts: 0, err: '', dev: null, ch: null, lastPush: 0, key: 'aura_hr_bridge', ph: '\u25c84417\u25c4', src: '', ttl: 0 };
  function hrBridge(payload) {
    var inp = document.querySelector('.st-key-' + HRM.key + ' input') || document.querySelector('input[placeholder="' + HRM.ph + '"]');
    if (!inp) { return false; }
    var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    setter.call(inp, payload);
    inp.dispatchEvent(new Event('input', { bubbles: true }));
    ['keydown', 'keypress', 'keyup'].forEach(function (k) {
      inp.dispatchEvent(new KeyboardEvent(k, { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true, cancelable: true }));
    });
    setTimeout(function () { try { inp.dispatchEvent(new FocusEvent('focusout', { bubbles: true })); inp.dispatchEvent(new FocusEvent('blur')); } catch (e) {} }, 60);
    return true;
  }
  function hrPush(force) {
    var now = Date.now();
    if (!force && now - HRM.lastPush < 4000) { return; }
    HRM.lastPush = now;
    try {
      hrBridge(JSON.stringify({ n: now.toString(36) + Math.random().toString(36).slice(2, 5), st: HRM.st, name: HRM.name,
                                hr: HRM.hr, rr: HRM.rr.slice(-24), err: HRM.err, src: HRM.src, ttl: HRM.ttl, nat: HRM.nat ? 1 : 0 }));
    } catch (e) {}
  }
  function hrParse(e) {
    var v = e.target.value, f = v.getUint8(0), i = 1, hr, rr = [];
    if (f & 1) { hr = v.getUint16(i, true); i += 2; } else { hr = v.getUint8(i); i += 1; }
    if (f & 8) { i += 2; }
    if (f & 16) { for (; i + 1 < v.byteLength; i += 2) { rr.push(Math.round(v.getUint16(i, true) * 1000 / 1024)); } }
    if (((f >> 1) & 3) === 2) { return; }          /* the sensor reports "not touching the skin" */
    if (hr > 25 && hr < 230) {
      HRM.hr = hr; HRM.ts = Date.now(); if (HRM.st === 'stale') { HRM.st = 'connected'; }
      if (rr.length) { HRM.rr = HRM.rr.concat(rr).slice(-60); }
      hrPush(HRM.first); HRM.first = false;
    }
  }
  function hrOpen(dev) {
    HRM.st = 'connecting'; HRM.err = '';
    return dev.gatt.connect().then(function (server) { return server.getPrimaryService('heart_rate'); })
      .then(function (svc) { return svc.getCharacteristic('heart_rate_measurement'); })
      .then(function (ch) {
        ch.addEventListener('characteristicvaluechanged', hrParse);
        return ch.startNotifications().then(function () { return ch; });
      })
      .then(function (ch) {
        HRM.dev = dev; HRM.ch = ch; HRM.st = 'connected'; HRM.name = dev.name || 'Heart-rate band'; HRM.ts = Date.now(); HRM.first = true; hrPush(true);
      });
  }
  function hrLost() {
    if (HRM.st === 'idle') { return; }
    HRM.st = 'reconnecting'; hrPush(true);
    (function retry(n) {
      if (!HRM.dev || HRM.st === 'idle') { return; }
      if (n > 6) { HRM.st = 'disconnected'; hrPush(true); return; }
      setTimeout(function () { hrOpen(HRM.dev).catch(function () { retry(n + 1); }); }, 1500 * n);
    })(1);
  }
  /* ---- iPhone app (Flutter) bridge: the app owns Bluetooth / Apple Health and feeds the readings in here ---- */
  function natSend(m) {
    var s = JSON.stringify(m), L = [window, window.parent, window.top];
    for (var i = 0; i < L.length; i++) {
      var w = L[i];
      try { if (w.AuraNative && w.AuraNative.postMessage) { w.AuraNative.postMessage(s); return true; } } catch (e) {}
      try { if (w.flutter_inappwebview && w.flutter_inappwebview.callHandler) { w.flutter_inappwebview.callHandler('AuraNative', s); return true; } } catch (e) {}
      try { if (w.webkit && w.webkit.messageHandlers && w.webkit.messageHandlers.AuraNative) { w.webkit.messageHandlers.AuraNative.postMessage(s); return true; } } catch (e) {}
    }
    return false;
  }
  A.nativeHR = function (o) {
    if (typeof o === 'string') { try { o = JSON.parse(o); } catch (e) { return; } }
    if (!o || typeof o !== 'object') { return; }
    HRM.nat = true;
    var st = String(o.st || (o.hr ? 'connected' : 'idle'));
    HRM.st = st; HRM.err = String(o.err || ''); HRM.src = String(o.src || ''); HRM.ttl = Number(o.ttl) || 0;
    if (o.name) { HRM.name = String(o.name); }
    var hr = Number(o.hr) || 0;
    if (hr > 25 && hr < 230) { HRM.hr = hr; HRM.ts = Date.now(); if (Array.isArray(o.rr) && o.rr.length) { HRM.rr = HRM.rr.concat(o.rr.map(Number)).slice(-60); } }
    hrPush(true);
  };
  try {
    window.auraNativeHR = A.nativeHR;
    var T = window; while (T.parent && T.parent !== T) { T = T.parent; try { T.auraNativeHR = A.nativeHR; } catch (e) { break; } }
    window.addEventListener('message', function (e) { var d = e && e.data; if (d && d.aura === 'hr') { A.nativeHR(d.p || d); } });
  } catch (e) {}
  (function hello(n) {              /* tell the page it runs inside the iPhone app, so device commands go through the phone */
    if (n > 5) { return; }
    setTimeout(function () {
      var inp = document.querySelector('.st-key-' + HRM.key + ' input') || document.querySelector('input[placeholder="' + HRM.ph + '"]');
      if (!inp) { return hello(n + 1); }
      try {
        var ok = false, L = [window, window.parent, window.top];
        for (var i = 0; i < L.length; i++) { try { var w = L[i]; if ((w.AuraNative && w.AuraNative.postMessage) || (w.flutter_inappwebview && w.flutter_inappwebview.callHandler) || (w.webkit && w.webkit.messageHandlers && w.webkit.messageHandlers.AuraNative)) { ok = true; } } catch (e) {} }
        if (ok) { HRM.nat = true; hrPush(true); }
      } catch (e) {}
    }, 2500 * (n + 1));
  })(0);
  A.hrConnect = function (all) {
    if (!navigator.bluetooth && natSend({ t: 'hr_connect', all: !!all })) { HRM.st = 'connecting'; HRM.err = ''; HRM.nat = true; return; }
    if (!navigator.bluetooth) { HRM.st = 'unsupported'; HRM.err = 'unsupported'; hrPush(true); return; }
    var opts = all ? { acceptAllDevices: true, optionalServices: ['heart_rate', 'battery_service'] }
                   : { filters: [{ services: ['heart_rate'] }], optionalServices: ['battery_service'] };
    navigator.bluetooth.requestDevice(opts).then(function (dev) {
      dev.addEventListener('gattserverdisconnected', hrLost);
      return hrOpen(dev);
    }).catch(function (e) {
      var n = (e && e.name) || 'error';
      if (n === 'NotFoundError') { HRM.st = 'idle'; HRM.err = 'cancelled'; } else { HRM.st = 'error'; HRM.err = n; }
      hrPush(true);
    });
  };
  A.hrDisconnect = function () {
    if (HRM.nat) { natSend({ t: 'hr_disconnect' }); }
    HRM.st = 'idle'; HRM.err = '';
    try { if (HRM.dev && HRM.dev.gatt && HRM.dev.gatt.connected) { HRM.dev.gatt.disconnect(); } } catch (e) {}
    HRM.hr = 0; hrPush(true);
  };
  setInterval(function () {
    if (HRM.st === 'connected' && Date.now() - HRM.ts > 30000) { HRM.st = 'stale'; hrPush(true); }
  }, 5000);
  /* ---- Sound Studio layers: 432Hz healing tone, rain on glass, gentle stream + chimes, white/pink noise ---- */
  A.layerPeak = { hz432: 0.2, rain: 0.5, stream: 0.4, noise: 0.22 };
  A.layersApply = function (p) {
    var n = A.nodes, c = A.ctx;
    if (!A.playing || !n || !c || !A.nbuf) { return; }
    var lv = (p && p.layers) || (A.p && A.p.layers) || {};
    if (!n.lay) {
      var L = n.lay = {}, buf = A.nbuf;
      var mk = function (k) { var g = c.createGain(); g.gain.value = 0; g.connect(n.master); L[k] = g; return g; };
      var src = function (filters, dest) {
        var s = c.createBufferSource(); s.buffer = buf; s.loop = true;
        var last = s;
        filters.forEach(function (f) { var b = c.createBiquadFilter(); b.type = f[0]; b.frequency.value = f[1]; if (f[2]) { b.Q.value = f[2]; } last.connect(b); last = b; });
        last.connect(dest); s.start(); n.srcs.push(s); return last;
      };
      /* 432 Hz: pure tone with a soft octave below and a slow breathing swell */
      var hg = mk('hz432'), sw = c.createGain(); sw.gain.value = 0.8; sw.connect(hg);
      [[432, 1], [216, 0.5]].forEach(function (x) {
        var o = c.createOscillator(); o.type = 'sine'; o.frequency.value = x[0];
        var og = c.createGain(); og.gain.value = x[1]; o.connect(og); og.connect(sw); o.start(); n.srcs.push(o);
      });
      var lf = c.createOscillator(); lf.frequency.value = 0.1; var lg = c.createGain(); lg.gain.value = 0.2;
      lf.connect(lg); lg.connect(sw.gain); lf.start(); n.srcs.push(lf);
      /* rain on glass: bright filtered noise with a gentle patter modulation */
      var rg = mk('rain'), rm = c.createGain(); rm.gain.value = 0.7; rm.connect(rg);
      src([['highpass', 1800], ['lowpass', 9000]], rm);
      var pl = c.createOscillator(); pl.frequency.value = 0.35; var pg = c.createGain(); pg.gain.value = 0.25;
      pl.connect(pg); pg.connect(rm.gain); pl.start(); n.srcs.push(pl);
      /* stream: band-passed noise whose centre drifts, plus random chimes */
      var sg = mk('stream'), sb = src([['bandpass', 1100, 0.8]], sg);
      var sl = c.createOscillator(); sl.frequency.value = 0.17; var sf = c.createGain(); sf.gain.value = 380;
      sl.connect(sf); sf.connect(sb.frequency); sl.start(); n.srcs.push(sl);
      /* white / pink noise: white blended with a low-passed copy */
      var ng = mk('noise'); src([], ng); src([['lowpass', 1400]], ng);
      var pent = [523.25, 587.33, 659.25, 783.99, 880, 1046.5];
      L.timer = setInterval(function () {
        if (A.nodes !== n || !A.playing) { clearInterval(L.timer); return; }
        var lvl = Number(((A.p && A.p.layers) || {}).stream) || 0;
        if (lvl > 5 && Math.random() < 0.7) {
          var f = pent[Math.floor(Math.random() * pent.length)], t0 = c.currentTime + 0.05;
          bell(f, t0, 0.05 * (lvl / 100), L.stream);
        }
      }, 4200);
    }
    var now = c.currentTime;
    ['hz432', 'rain', 'stream', 'noise'].forEach(function (k) {
      var v = Math.max(0, Math.min(100, Number(lv[k]) || 0)) / 100;
      n.lay[k].gain.setTargetAtTime(v * A.layerPeak[k], now, 0.4);
    });
  };
  (function () {
    var u0 = A.update, s0 = A.start;
    A.update = function (p) { var r = u0.apply(A, arguments); try { A.layersApply(p); } catch (e) {} return r; };
    A.start = function () { var r = s0.apply(A, arguments); try { A.layersApply(A.p); } catch (e) {} return r; };
  })();
  A.styles = S;
  window.__aura = A;
})();
"""

ENGINE_VER = 10.6

HOST_BOOT = """
<script id="eng" type="text/plain">__ENGINE__</script>
<script>
var P;
try { P = window.parent; void P.document.body; } catch (e) { P = window; }
if (!P.__aura || P.__aura.v !== __VER__) {
  if (P.__aura && P.__aura.playing) { try { P.__aura.stop(); } catch (e) {} }
  var sc = P.document.createElement('script');
  sc.textContent = document.getElementById('eng').textContent;
  P.document.head.appendChild(sc);
}
var A = P.__aura;
</script>
"""

AUDIO_HTML = """
<style>
  body { margin: 0; }
  #box { display: flex; align-items: center; gap: 12px; background: __GLASS__; border: 1px solid __LINE__; border-radius: 18px;
         padding: 8px 12px; font-family: Inter, Arial, sans-serif; color: __ACC__; box-sizing: border-box; }
  #tg { width: 44px; height: 44px; flex: none; border-radius: 50%; background: __BTN__; color: __ACC__;
        border: 1px solid __ACC__; font-size: 18px; cursor: pointer; }
  #tg:hover { background: __ACC__; color: __BTN__; }
  #txt { flex: 1; min-width: 0; }
  #ttl { font-size: 14px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  #sub { font-size: 11px; color: __SUB__; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  #eq { display: flex; gap: 2px; align-items: flex-end; height: 22px; }
  .b { width: 3px; height: 5px; background: __ACC__; border-radius: 2px; }
  .on .b { animation: eq 0.9s ease-in-out infinite; }
  .on .b:nth-child(2) { animation-delay: 0.2s; }
  .on .b:nth-child(3) { animation-delay: 0.4s; }
  .on .b:nth-child(4) { animation-delay: 0.1s; }
  @keyframes eq { 0%, 100% { height: 5px; } 50% { height: 20px; } }
</style>
<div id="box">
  <button id="tg"></button>
  <div id="txt"><div id="ttl"></div><div id="sub"></div></div>
  <div id="eq"><span class="b"></span><span class="b"></span><span class="b"></span><span class="b"></span></div>
</div>
__BOOT__
<script>
var PARAMS = __PARAMS__, PLAY = __PLAY__, STOP = __STOP__, SEND = __SEND__;
['touchstart', 'touchend', 'pointerdown', 'click', 'keydown'].forEach(function (ev) {
  document.addEventListener(ev, function () { try { A.unlock(); } catch (e) {} }, true);
});
document.addEventListener('visibilitychange', function () { try { A.revive(); } catch (e) {} });
var btn = document.getElementById('tg'), ttl = document.getElementById('ttl');
var sub = document.getElementById('sub'), box = document.getElementById('box');
if (SEND || !A.p) { A.update(PARAMS); }
try {
  var pc = PARAMS.pc;
  if (pc && pc.id && pc.id !== A.pcTok) {
    A.pcTok = pc.id;
    if (pc.d === 'play') { if (!A.playing && A.unlocked) { A.start(); } }
    else if (pc.d === 'stop') { if (A.playing) { A.stop(); } }
  }
} catch (e) {}
function paint() {
  var p = A.p || PARAMS;
  ttl.textContent = p.title; sub.textContent = p.sub;
  btn.textContent = A.playing ? '■' : '▶';
  btn.title = A.playing ? STOP : PLAY;
  box.className = A.playing ? 'on' : '';
}
btn.onclick = function () { A.unlock(); if (A.playing) { A.stop(); } else { A.start(); } paint(); };
paint();
setInterval(paint, 700);
</script>
"""

CHIME_HTML = """
<style>body { margin: 0; }</style>
<div style="font-family:Inter,Arial,sans-serif;text-align:left;">
  <button id="rg" title="Ring" style="background:__BTN__;color:__ACC__;border:1px solid __ACC__;border-radius:20px;padding:4px 16px;font-size:16px;cursor:pointer;">🔔</button>
</div>
__BOOT__
<script>
var AUTO = __AUTO__;
document.getElementById('rg').onclick = function () { A.chime(); };
if (AUTO) { setTimeout(function () { try { A.chime(); } catch (e) {} }, 400); }
</script>
"""


def boot():
    return HOST_BOOT.replace("__ENGINE__", ENGINE_JS).replace("__VER__", str(ENGINE_VER))


def audio_component(params, send):
    page = (AUDIO_HTML.replace("__BOOT__", boot()).replace("__PARAMS__", json.dumps(params))
            .replace("__PLAY__", json.dumps(t("play"))).replace("__STOP__", json.dumps(t("stop")))
            .replace("__SEND__", "true" if send else "false"))
    components.html(themed(page), height=74)


BOOTSTRAP_HTML = """
__BOOT__
<script>try { A.session(); } catch (e) {}</script>
"""


def audio_bootstrap():
    """Invisible component: guarantees the audio engine, first-touch unlock and Media Session on every page."""
    components.html(BOOTSTRAP_HTML.replace("__BOOT__", boot()), height=0)


def synth_params(name):
    cfg = st.session_state.cfg
    env = st.session_state.modes[name]
    p = {"genre": env.get("genre", GENRES[0]), "mix": full_mix(cfg["mix"]), "modeMix": full_mix(env.get("mix")),
         "bed": max(0, min(100, int(cfg["bed"]))), "tMin": cfg["timer"],
         "tTok": cfg["tok"], "layers": layers_params(), "title": tr_mode(name), "sub": tr(env.get("genre", GENRES[0]))}
    p["pc"] = st.session_state.get("pc") or {}
    if name == WIND_MODE:
        p["fade"] = 300
        p["fadeTok"] = st.session_state.fade_tok
    return p


# ----------------------------------------------------------------------------
# Page 1 - Live Dashboard
# ----------------------------------------------------------------------------
def seg(label, options, key, fmt=None, on_change=None, args=None, selected=None, disabled=False, hide_label=False):
    """Segmented control (falls back to a horizontal radio on older Streamlit)."""
    fmt = fmt or str
    args = args or ()
    base = dict(key=key, format_func=fmt, on_change=on_change, args=args, disabled=disabled)
    extra = {"label_visibility": "collapsed"} if hide_label else {}
    if hasattr(st, "segmented_control"):
        default = selected if selected in options else None
        try:
            return st.segmented_control(label, options, default=default, **base, **extra)
        except TypeError:
            return st.segmented_control(label, options, default=default, **base)
    idx = options.index(selected) if selected in options else 0
    try:
        return st.radio(label, options, index=idx, horizontal=True, **base, **extra)
    except TypeError:
        return st.radio(label, options, index=idx, horizontal=True, **base)


def room_selector(prefix, label):
    ss = st.session_state
    key = prefix + "_room_" + str(ss.get("room_rev", 0))
    seg(label, list(ss.spaces), key, lambda n: ss.spaces[n]["icon"] + " " + tr_room(n), on_change=pick_room, args=(key,),
        selected=current_room())


def chime_component(auto):
    components.html(themed(CHIME_HTML.replace("__BOOT__", boot()).replace("__AUTO__", "true" if auto else "false")),
                    height=48)


def run_live(fn):
    if hasattr(st, "fragment"):
        st.fragment(run_every=st.session_state.cfg["poll"])(fn)()
    else:
        fn()


def dev_text(d):
    c = CAT[d["cid"]]
    if not d["on"]:
        return t("off")
    return "ON" + ((" · " + str(d["lvl"]) + UNIT.get(d["cid"], "%")) if c[4] else "")


def current_room():
    ss = st.session_state
    room = ss.get("sel_room")
    return room if room in ss.spaces else next(iter(ss.spaces))


def live_devices():
    ss = st.session_state
    room = current_room()
    sp = ss.spaces[room]
    here = ss.conn["mode"] == "home" and ss.presence["room"] == room
    st.markdown("**" + sp["icon"] + " " + html.escape(tr_room(room)) + "**" +
                (' <span class="pill">' + t("here") + "</span>" if here else ""), unsafe_allow_html=True)
    devs = space_devs(room)
    if not devs:
        st.caption(t("room_empty"))
        return
    cards = []
    for d in devs:
        sw = ""
        if d["cid"] in BULBLIKE and d["on"]:
            sw = '<span class="sw" style="background:' + html.escape(d["color"]) + '"></span>'
        cards.append(stat(CAT[d["cid"]][1] + " " + d["name"].split(" · ")[0], dev_text(d), sw))
    cols = st.columns(4)
    for i, c in enumerate(cards):
        cols[i % 4].markdown(c, unsafe_allow_html=True)


def render_rooms():
    """Live Dashboard: one-click Active Room selector + one-click saved room default."""
    ss = st.session_state
    room_selector("dash", "🏠 " + t("room_sel"))
    room = current_room()
    has = bool(ss.spaces[room].get("preset"))
    any_has = any(sp.get("preset") for sp in ss.spaces.values())
    c1, c2 = st.columns(2)
    c1.button("⚡ " + t("rs_preset_apply", n=tr_room(room)), key="dash_preset_go", disabled=not has,
              on_click=cb_apply_preset, args=(room,))
    c2.button("⚡ " + t("preset_apply_all"), key="dash_preset_all", disabled=not any_has, on_click=cb_apply_all_presets)
    if not has:
        st.caption(t("preset_none"))


def geo_val(part, d):
    if not d["on"]:
        return "OFF"
    if part == "fan":
        return "ON · Speed " + str(d["lvl"])
    return "ON · " + str(d["lvl"]) + " °C"


def precond_tiles():
    tiles = []
    for part in GEO_PARTS:
        d = geo_dev(part)
        if d is None:
            continue
        tiles.append('<div class="ptile ' + ("on" if d["on"] else "off") + '"><div class="pi">' + GEO_ICON[part] +
                     '</div><div class="pn">' + html.escape(tr_room(GEO_NAME[part].split(' · ')[1])) +
                     '</div><div class="pv">' + geo_val(part, d) + "</div></div>")
    return '<div class="ptiles">' + "".join(tiles) + "</div>"


def render_precond_card(prefix):
    """Luxury Pre-Conditioning Status Card: live ON/OFF per appliance + one-touch overrides."""
    ss = st.session_state
    state = ss.geo["state"]
    if state == "active":
        st.markdown('<div class="pre"><div class="ph">' + html.escape(t("geo_card_hdr", m=eta_min(ss.geo["km"]))) +
                    '</div><div class="ps">' + html.escape(t("geo_card_sub")) + "</div>" + precond_tiles() + "</div>",
                    unsafe_allow_html=True)
        cols = st.columns(3)
        for col, part in zip(cols, GEO_PARTS):
            d = geo_dev(part)
            if d is None:
                continue
            on = bool(d["on"])
            col.button(t("geo_off_" + part) if on else t("geo_on_" + part), key=prefix + "_geo_" + part,
                       on_click=geo_part_set, args=(part, not on))
        st.button(t("geo_cancel_all"), key=prefix + "_geo_cancel", type="primary", on_click=geo_cancel_all)
    else:
        st.markdown(precond_tiles(), unsafe_allow_html=True)
        if state == "standby":
            st.info(t("geo_standby"))
            st.button(t("geo_restart"), key=prefix + "_geo_restart", on_click=geo_restart)


def render_geo_banner(show_card=True):
    """Shown on every page while you are away: the consent prompt (Autonomous OFF) or the live arrival card."""
    ss = st.session_state
    if ss.conn["mode"] != "away":
        return
    state = ss.geo["state"]
    if state == "pending":
        msg = t("geo_alert", n=html.escape(first_name()), m=eta_min(ss.geo["km"]))
        st.markdown('<div class="geo">' + msg + "</div>", unsafe_allow_html=True)
        b1, b2 = st.columns(2)
        b1.button(t("geo_yes"), on_click=geo_confirm, type="primary", key="geo_yes_btn")
        b2.button(t("geo_no"), on_click=geo_dismiss, key="geo_no_btn")
    elif state == "active" and show_card:
        render_precond_card("gb")
    if state in ("pending", "active"):
        ring = not ss.geo["chimed"]
        ss.geo["chimed"] = True
        if ring:
            chime_component(True)


def geo_sim_controls():
    ss = st.session_state
    gkey = "geo_km_" + str(ss.geo.get("rev", 0))
    st.slider(t("geo_dist"), 0, 20, value=int(ss.geo["km"]), key=gkey, on_change=cb_geo_slider, args=(gkey,))
    q = st.columns(5)
    for col, km in zip(q, (20, 15, 10, 5, 0)):
        col.button(str(km) + " km", key="gj_" + str(km), on_click=geo_jump, args=(km,))


def render_connection():
    ss = st.session_state
    zen = ss.ui_mode == "zen"
    st.subheader("📡 " + t("conn_title"))
    modes = ["home", "away"]
    st.radio(t("conn_mode"), modes, index=modes.index(ss.conn["mode"]), key="conn_sel", horizontal=True,
             format_func=lambda m: t("conn_home") if m == "home" else t("conn_away"), on_change=set_conn)
    st.toggle(t("geo_auto_toggle"), value=bool(ss.cfg.get("geo_auto", True)), key="geo_auto_rc",
              on_change=cb_geo_auto, args=("geo_auto_rc",))
    st.caption(t("geo_auto_hint"))
    if ss.conn["mode"] == "home":
        st.caption(t("conn_local_cap"))
        return
    st.caption(t("conn_cloud_cap"))
    km = ss.geo["km"]
    if zen:
        st.markdown("**" + t("watch_eta", m=eta_min(km)) + "**")
        with st.expander(t("geo_sim")):
            geo_sim_controls()
    else:
        geo_sim_controls()
        zone = {"idle": "geo_idle", "pending": "geo_pending", "confirmed": "geo_confirmed", "dismissed": "geo_dismissed",
                "active": "geo_active", "standby": "geo_standby_zone"}[ss.geo["state"]]
        m = st.columns(3)
        m[0].markdown(stat(t("geo_dist_m"), str(km) + " km"), unsafe_allow_html=True)
        m[1].markdown(stat(t("geo_eta"), str(eta_min(km)) + " mins"), unsafe_allow_html=True)
        m[2].markdown(stat(t("geo_zone"), t(zone)), unsafe_allow_html=True)
        st.progress(max(0.0, min(1.0, 1 - km / 20.0)))
    st.markdown("**" + t("remote_status") + "**")
    render_precond_card("rc")


def loc_readout():
    ss, cfg = st.session_state, st.session_state.cfg
    eng = engine_of(cfg["tracker"])
    room = ss.presence["room"]
    names = list(ss.spaces)
    if ss.conn["mode"] != "home":
        return
    if eng == "UWB":
        c = st.columns(4)
        c[0].markdown(stat(t("ml_zone"), ss.spaces[room]["icon"] + " " + tr_room(room)), unsafe_allow_html=True)
        c[1].markdown(stat(t("ml_dist"), str(random.randint(25, 160)) + " cm"), unsafe_allow_html=True)
        c[2].markdown(stat(t("ml_aoa"), str(random.randint(-60, 60)) + "°"), unsafe_allow_html=True)
        c[3].markdown(stat(t("ml_acc"), "± 10 cm"), unsafe_allow_html=True)
    else:
        idx = {n: i for i, n in enumerate(names)}
        rows = []
        for n in names:
            dist = 1.5 if n == room else 2 + 4 * abs(idx[n] - idx[room])
            rows.append({"Room anchor": tr_room(n), "RSSI (dBm)": int(-45 - 20 * math.log10(max(dist, 1)) + random.gauss(0, 1.5))})
        best = max(rows, key=lambda x: x["RSSI (dBm)"])["Room anchor"]
        c = st.columns(2)
        c[0].markdown(stat(t("ml_est"), ss.spaces[best]["icon"] + " " + tr_room(best)), unsafe_allow_html=True)
        c[1].markdown(stat(t("ml_acc"), "Room level"), unsafe_allow_html=True)
        st.caption(t("ml_rssi"))
        html_table(rows)
    calm = ss.room_mode.get(room)
    if calm == CALM_MODE:
        st.info(t("calm_note", r=tr_room(room), m=tr_mode(calm)))


def render_microloc():
    ss, cfg = st.session_state, st.session_state.cfg
    zen = ss.ui_mode == "zen"
    st.subheader("📍 " + t("ml_title"))
    if not zen:
        opts = UWB_DEVICES + BLE_DEVICES
        c1, c2 = st.columns([2, 3])
        cfg["tracker"] = c1.selectbox(t("ml_dev"), opts, index=opts.index(cfg["tracker"]),
                                      format_func=lambda x: ("📡 UWB · " if x in UWB_DEVICES else "📶 BLE · ") + x)
        eng = engine_of(cfg["tracker"])
        c2.markdown(stat(t("ml_engine"), t("ml_uwb") if eng == "UWB" else t("ml_ble")), unsafe_allow_html=True)
    if ss.conn["mode"] == "home":
        skey = "sim_room_" + ss.presence["room"]
        seg(t("ml_sim"), list(ss.spaces), skey, lambda n: ss.spaces[n]["icon"] + " " + tr_room(n), on_change=on_sim_move,
            args=(skey,), selected=ss.presence["room"])
    else:
        st.info(t("ml_away"))
    if zen:
        f1, f3 = st.columns(2)
    else:
        f1, f2, f3 = st.columns(3)
    cfg["follow_me"] = f1.toggle(t("ml_follow"), value=cfg["follow_me"])
    if not zen:
        cuts = ["Off", "Eco standby"]
        cfg["cut_mode"] = f2.selectbox(t("ml_cut"), cuts, index=cuts.index(cfg["cut_mode"]),
                                       format_func=lambda x: "OFF" if x == "Off" else "Eco standby (27 °C)")
    cfg["calm_on"] = f3.toggle(t("ml_calm"), value=cfg["calm_on"])
    if not zen:
        run_live(loc_readout)


def flush_rerun():
    """Run at the END of the fragment: a single debounced full-app rerun when automation changed the atmosphere."""
    ss = st.session_state
    if not ss.get("rerun_pending"):
        return
    if time.time() - ss.get("last_rerun", 0.0) < 1.5:
        return
    ss["rerun_pending"] = False
    ss["last_rerun"] = time.time()
    try:
        st.rerun(scope="app")
    except TypeError:
        st.rerun()


def bio_panel(zen=False):
    ss, cfg = st.session_state, st.session_state.cfg
    r = read_biometrics()
    ss.hr_hist = (ss.hr_hist + [r["hr"]])[-60:]
    res = analyze(r)
    home = ss.conn["mode"] == "home"
    try:
        if run_routines():
            ss.flash = "⏰ " + t("rt_ranmsg")
            ss.rerun_pending = True
        ev = room_calm_step(r["hr"])
        if ev:
            ss.flash = ("🌊 " + tr_room(ss.presence["room"]) + " calm mode") if ev == "on" else ("🌤 " + tr_room(ss.presence["room"]) + " normal")
            ss.rerun_pending = True
        if zen and cfg.get("ap_on", True) and ss.ui_mode == "zen":
            if cfg["auto_mode"] and home and bio_autopilot(r["hr"]):
                ss.flash = zt(AP_PRESET[ss.ap_zone]["msg"], hr=r["hr"])
                ss.rerun_pending = True
            if cfg["auto_mode"] and home and aura_ai_sense(r, res):
                ss.rerun_pending = True
        elif cfg["auto_mode"] and home and automation_step(res, r):
            ss.flash = "🫀 " + t("st_" + res["state"]) + " → " + tr_mode(ss.active_mode)
            ss.rerun_pending = True
    except Exception as e:
        log("⚠ automation step skipped: " + type(e).__name__)
    if cfg["auto_mode"] and not home:
        st.caption("🚗 " + t("away_pause"))
    if cfg["source"] in ("wear", "ble") and not r["live"]:
        st.caption("⚠️ " + t("offline"))
    if zen:
        zen_hr_card(r)
        if cfg["auto_mode"]:
            try:
                render_aura_ai_card(r, res)
            except Exception as e:
                log("⚠ Aura AI card skipped: " + type(e).__name__)
        st.caption(t("zen_well", s=t("st_" + res["state"])))
        flush_rerun()
        return
    b = st.columns(5)
    b[0].markdown(stat(t("state_lbl"), t("st_" + res["state"])), unsafe_allow_html=True)
    b[1].markdown(stat(t("bpm"), r["hr"]), unsafe_allow_html=True)
    b[2].markdown(stat("HRV (ms)", r["hrv"]), unsafe_allow_html=True)
    b[3].markdown(stat(t("spo2"), r["spo2"]), unsafe_allow_html=True)
    b[4].markdown(stat(t("skin"), r["skin"]), unsafe_allow_html=True)
    themed_line_chart(ss.hr_hist, 220)
    st.markdown("**" + t("live_dev") + "**")
    live_devices()
    mode_line = t("mode_auto").split(" (")[0] if cfg["auto_mode"] else t("mode_manual")
    st.markdown('<div class="aibox"><b>🌿 ' + t("ai_auto") + "</b> · " + html.escape(mode_line) + "<br>" +
                html.escape(t("feel", s=t("st_" + res["state"]), m=tr_mode(eff_mode()))) +
                "<br><span class='logl'>" + html.escape(res["reason"]) + "</span></div>",
                unsafe_allow_html=True)
    with st.expander("📜 " + t("ai_log")):
        for e in ss.log[:8]:
            st.markdown('<div class="logl">' + e["t"] + "  " + html.escape(e["x"]) + "</div>", unsafe_allow_html=True)
    flush_rerun()


def bio_panel_zen():
    bio_panel(True)


def page_dashboard_pro():
    ss, cfg = st.session_state, st.session_state.cfg
    st.header(t("p1"))
    render_rooms()
    render_zero_ui()
    render_family_panel()
    cfg["auto_mode"] = st.radio(t("mode_sel"), [False, True], index=1 if cfg["auto_mode"] else 0,
                                format_func=lambda a: t("mode_auto") if a else t("mode_manual"), horizontal=True)
    if cfg["auto_mode"] and not ss.prev_auto:
        ss.last_state = None
    ss.prev_auto = cfg["auto_mode"]
    c1, c2 = st.columns(2)
    with c1:
        if not cfg["auto_mode"]:
            names = list(ss.modes.keys())
            choice = st.selectbox(t("atmos"), names, index=names.index(ss.active_mode), format_func=tr_mode)
            if choice != ss.active_mode:
                clear_room_override(ss.presence["room"])
                apply_mode(choice)
        else:
            st.info(t("auto_on"))
    with c2:
        opts = [0, 15, 30, 45, 60, 90, 120]
        new_t = st.selectbox(t("timer"), opts, index=opts.index(cfg["timer"]),
                             format_func=lambda x: t("off") if x == 0 else str(x) + " " + t("min"))
        if new_t != cfg["timer"]:
            cfg["timer"] = new_t
            cfg["tok"] += 1

    shown = eff_mode()
    m = st.columns(2)
    m[0].markdown(stat(t("active"), tr_mode(shown)), unsafe_allow_html=True)
    m[1].markdown(stat(t("genre"), ss.modes[shown]["genre"]), unsafe_allow_html=True)

    st.caption("⚙ " + t("rs_dash_hint"))

    st.subheader("🎧 " + t("studio"))
    studio = st.container()
    with st.expander("🎚 " + t("mixer"), expanded=True):
        cfg["bed"] = st.slider(t("bed"), 0, 100, int(cfg["bed"]))
        cols = st.columns(2)
        for i, ins in enumerate(INSTRUMENTS):
            with cols[i % 2]:
                cfg["mix"][ins] = st.slider(ins + " (%)", 0, 100, int(cfg["mix"][ins]))
    with studio:
        audio_component(synth_params(shown), True)

    st.subheader("🫀 " + t("bio"))
    if not cfg["auto_mode"]:
        st.caption(t("auto_hint"))
    b1, b2 = st.columns(2)
    srcs = ["sim", "ble", "wear"]
    cfg["source"] = b1.radio(t("source"), srcs, index=srcs.index(cfg["source"]) if cfg["source"] in srcs else 0,
                             horizontal=True, format_func=lambda s: t({"ble": "src_ble"}.get(s, s)))
    if cfg["source"] == "sim":
        scns = list(SCN.keys())
        cfg["scn"] = b2.selectbox(t("scn"), scns, index=scns.index(cfg["scn"]), format_func=lambda s: t("st_" + s))
    if cfg["source"] == "ble":
        render_wearable()
    if hasattr(st, "fragment"):
        st.fragment(run_every=cfg["poll"])(bio_panel)()
    else:
        bio_panel()
        st.button("↻ Refresh")


# ----------------------------------------------------------------------------
# Zen Mode dashboard, Zero-UI layer, family logic
# ----------------------------------------------------------------------------
def light_words(color, lvl):
    r, g, b = hex_rgb(color)
    if r > 200 and g > 200 and b > 200:
        tone_key = "Daylight White" if lvl > 70 else "Soft White"
    elif r >= 200 and 130 <= g <= 215 and b < 160:
        tone_key = "Warm Candlelight"
    elif b > r and b > g:
        tone_key = "Calm Blue"
    elif g > r and g >= b:
        tone_key = "Fresh Green"
    elif r < 140 and b > 80:
        tone_key = "Violet Glow"
    else:
        tone_key = "Warm Amber"
    adj_key = "Dim" if lvl < 25 else ("Soft" if lvl < 60 else "Bright")
    lang = st.session_state.get("lang", "English")
    adj = LIGHT_ADJ[adj_key].get(lang, adj_key)
    tone = LIGHT_WORDS[tone_key].get(lang, tone_key)
    return adj + " " + tone


def plain_ambience(room):
    ss = st.session_state
    devs = space_devs(room)
    ac = next((d for d in devs if d["cid"] in ("ac", "thermo", "heater") and d["on"]), None)
    temp = int(ac["lvl"]) if ac else int(ss.modes[eff_mode()]["ac"])
    bulb = next((d for d in devs if d["cid"] in BULBLIKE + ("lamp", "ledstrip") and d["on"]), None)
    light = light_words(bulb["color"], int(bulb["lvl"])) if bulb else t("zen_lights_off")
    return temp, light


def render_zen_card(room, mode):
    ss = st.session_state
    sp = ss.spaces[room]
    temp, light = plain_ambience(room)
    extra = ""
    if ss.get("guest_mode"):
        extra = "👥 " + t("guest_on")
    elif room in ss.get("family_lock", ()):
        extra = "👨‍👩‍👧 " + t("occ_lock")
    st.markdown('<div class="zen"><div class="zr">' + sp["icon"] + " " + html.escape(tr_room(room)) + " · " + html.escape(tr_mode(mode)) +
                '</div><div class="zl">' + html.escape(t("zen_comfort", c=temp)) + " · " + html.escape(light) +
                '</div><div class="zs">' + html.escape(extra) + "</div></div>", unsafe_allow_html=True)


def set_away_mode():
    """One touch: everything non-essential off (AC to eco), then the geofence takes over for the way back."""
    ss = st.session_state
    for d in ss.fleet:
        if held(d):
            continue
        if d["cid"] == "ac":
            set_dev(d, True, 27, why="Away Mode: eco standby")
        elif d["cid"] in CUT_CIDS or d["cid"] in ("fan", "tv", "projector", "speaker", "spatial", "diffuser", "scent"):
            set_dev(d, False, why="Away Mode: switched off")
    switch_conn("away")
    log("🚗 Away Mode: the home is on standby. AuraSync will prepare your arrival automatically")
    ss.flash = "🚗 " + t("zen_away")


def go_home_mode():
    switch_conn("home")
    st.session_state.flash = "🏠 " + t("zen_home")


def zen_go(kind):
    ss = st.session_state
    room = ss.presence["room"]
    if kind == "away":
        leaving = ss.conn["mode"] == "home"
        if leaving:
            set_away_mode()
        else:
            go_home_mode()
        dispatch_cloud("away" if leaving else "home", "app")
        return
    mode = {"relax": "Relax Evening", "focus": "Focus", "sleep": WIND_MODE}[kind]
    if mode not in ss.modes:
        return
    clear_room_override(room)
    apply_mode(mode)
    if kind == "sleep":
        ss.fade_tok += 1
    ss.flash = "✨ " + tr_mode(mode)
    dispatch_cloud(kind, "app")


def page_dashboard_zen():
    ss, cfg = st.session_state, st.session_state.cfg
    st.header(t("p1"))
    render_rooms()
    shown = eff_mode()
    render_zen_card(current_room(), shown)
    # 1. instant mood pills
    render_zen_pills()
    # Auto / Manual (Manual pauses the biometric takeover)
    if cfg["auto_mode"] and not ss.prev_auto:
        ss.last_state = None
        ss.ap_zone = None                               # the first reading after switching Auto on counts as a transition
    ss.prev_auto = cfg["auto_mode"]
    if cfg["auto_mode"]:
        cfg["ap_on"] = st.toggle(zt("zk_ap"), value=bool(cfg.get("ap_on", True)))
        st.caption(zt("zk_ap_hint"))
    # 2. live heart-rate graph + emotion badge (the panel also drives the automation each polling tick)
    if hasattr(st, "fragment"):
        st.fragment(run_every=cfg["poll"])(bio_panel_zen)()
    else:
        bio_panel(True)
    # 3 + 4. living player dock and collapsible sound studio mixer
    render_zen_dock(shown)
    if not cfg["auto_mode"]:
        render_manual_priority()
        render_manual_controls()
    # 5. conversational bar
    render_tell_bar()
    # 6. voice assistant drawer (hidden by default)
    render_va_drawer()
    with st.expander(zt("zk_more")):
        away = ss.conn["mode"] == "away"
        items = (("relax", " " + t("zen_relax"), "Relax Evening"), ("focus", " " + t("zen_focus"), "Focus"),
                 ("sleep", " " + t("zen_sleep"), WIND_MODE),
                 ("away", (" " + t("zen_home")) if away else (" " + t("zen_away")), None))
        for col, (k, label, mode) in zip(st.columns(4), items):
            col.button(label, key="zenbtn_" + k, type=("primary" if (mode and ss.active_mode == mode) else "secondary"),
                       on_click=zen_go, args=(k,))
        render_watch_card()
        render_dial()
        render_family_panel()
    st.caption(t("zen_hidden"))


def page_dashboard():
    if st.session_state.ui_mode == "pro":
        page_dashboard_pro()
    else:
        page_dashboard_zen()


# ---- Zero-UI: lock-screen card, rotary dial, voice quick-bar
def render_watch_card():
    ss = st.session_state
    away = ss.conn["mode"] == "away"
    bath, ac = geo_dev("geyser"), geo_dev("ac")
    st.markdown("**" + t("watch_title") + "**")
    if away and ss.geo["state"] == "active":
        km = ss.geo["km"]
        bits = [t("watch_eta", m=eta_min(km)),
                t("watch_preheat", v=bath["lvl"]) if (bath and bath["on"]) else t("watch_geyser_off"),
                t("watch_ac", v=ac["lvl"]) if (ac and ac["on"]) else t("watch_ac_off")]
    elif away:
        bits = [t("watch_eta", m=eta_min(ss.geo["km"])), t("watch_standby")]
    else:
        room = ss.presence["room"]
        bits = [t("watch_home"), ss.spaces[room]["icon"] + " " + tr_room(room), "🎼 " + tr_mode(eff_mode())]
    st.markdown('<div class="island">' + "".join('<span class="it">' + html.escape(b) + "</span>" for b in bits) + "</div>",
                unsafe_allow_html=True)
    st.button(t("watch_cancel"), key="watch_cancel_btn", on_click=geo_cancel_all,
              disabled=not (away and ss.geo["state"] == "active"))


LIGHT_CIDS = ("bulb", "tasklight", "ambilight", "lamp", "ledstrip", "dimmer")
DIAL_ORDER = ["Relax Evening", "Focus", "Deep Meditation", "Zen Garden", "Energize", "Sleep"]


def dial_values(room):
    devs = space_devs(room)
    lights = [d["lvl"] for d in devs if d["cid"] in LIGHT_CIDS and d["on"]]
    acs = [d["lvl"] for d in devs if d["cid"] in ("ac", "thermo", "heater") and d["on"]]
    bright = int(sum(lights) / len(lights)) if lights else 0
    temp = int(sum(acs) / len(acs)) if acs else None
    return bright, temp


def cb_dial_tap():
    ss = st.session_state
    room = current_room()
    order = [m for m in DIAL_ORDER if m in ss.modes]
    if not order:
        return
    i = (ss.dial_idx.get(room, -1) + 1) % len(order)
    ss.dial_idx[room] = i
    mode = order[i]
    if room not in ss.get("family_lock", ()):
        ss.room_mode[room] = mode
    apply_mode(mode, why=False, devs=space_devs(room), set_active=False)
    log("🔘 Dial tap: " + room + " → " + mode)
    ss.flash = "🔘 " + tr_room(room) + " · " + tr_mode(mode)


def cb_dial_turn(delta):
    ss = st.session_state
    room = current_room()
    scope = ss.get("dial_scope", "both")
    for d in space_devs(room):
        c = d["cid"]
        if scope in ("lights", "both") and c in LIGHT_CIDS:
            if delta > 0 and not d["on"]:
                set_dev(d, True, 30)
            elif d["on"]:
                set_dev(d, lvl=d["lvl"] + 10 * delta)
        if scope in ("climate", "both") and c in ("ac", "thermo", "heater") and d["on"]:
            set_dev(d, lvl=d["lvl"] + delta)
    bright, temp = dial_values(room)
    log("🔄 Dial turned " + ("clockwise" if delta > 0 else "counter-clockwise") + " in " + room)
    ss.flash = "🔄 " + str(bright) + "%" + ((" · " + str(temp) + " °C") if temp else "")


def render_dial():
    ss = st.session_state
    room = current_room()
    bright, temp = dial_values(room)
    p = pal()
    st.markdown("**" + t("dial_title") + "**")
    left, right = st.columns([1, 2])
    ring = ('<div style="width:150px;height:150px;border-radius:50%;margin:auto;'
            'background:conic-gradient(' + p["ACC"] + " " + str(bright * 3.6) + "deg," + p["BORDER"] + " 0);"
            'display:flex;align-items:center;justify-content:center;">'
            '<div style="width:112px;height:112px;border-radius:50%;background:' + p["CARD1"] + ';display:flex;'
            'flex-direction:column;align-items:center;justify-content:center;color:' + p["TXT"] + ';">'
            '<div style="font-size:1.5rem;font-weight:700;">' + (str(temp) + "°C" if temp else "--") + '</div>'
            '<div style="font-size:.8rem;color:' + p["MUTE"] + ';">' + str(bright) + "% 💡</div></div></div>")
    left.markdown(ring, unsafe_allow_html=True)
    with right:
        b = st.columns(3)
        b[0].button(t("dial_ccw"), key="dial_ccw_btn", on_click=cb_dial_turn, args=(-1,))
        b[1].button(t("dial_tap"), key="dial_tap_btn", type="primary", on_click=cb_dial_tap)
        b[2].button(t("dial_cw"), key="dial_cw_btn", on_click=cb_dial_turn, args=(1,))
        scopes = ["lights", "climate", "both"]
        st.radio(t("dial_scope"), scopes, index=scopes.index(ss.dial_scope), horizontal=True, key="dial_scope_w",
                 format_func=lambda s: t("dial_" + s) if s != "both" else t("dial_both"), on_change=cb_dial_scope)
        st.caption(t("dial_hint"))


def cb_dial_scope():
    ss = st.session_state
    if ss.get("dial_scope_w") in ("lights", "climate", "both"):
        ss.dial_scope = ss.dial_scope_w


VOICE_INTENTS = (
    ("home", ("i'm home", "im home", "back home", "i am home", "arrived home")),
    ("away", ("leaving", "going out", "heading out", "away mode", "bye")),
    ("movie", ("movie", "film", "cinema", "netflix", "watch tv")),
    ("work", ("work", "focus", "study", "office", "meeting", "concentrate")),
    ("sleep", ("tired", "sleepy", "sleep", "bed", "exhausted", "good night", "goodnight")),
    ("relax", ("relax", "unwind", "chill", "calm")),
    ("off", ("lights off", "turn off", "switch off")),
    ("dim", ("dim", "darker", "too bright")),
    ("bright", ("brighter", "too dark", "more light")),
    ("cool", ("too hot", "hot", "stuffy", "cooler")),
    ("warm", ("too cold", "cold", "chilly", "warmer")),
)


def voice_do(kind):
    ss = st.session_state
    room = current_room()
    near = space_devs(room)
    if kind == "sleep":
        clear_room_override(ss.presence["room"])
        apply_mode(WIND_MODE)
        ss.fade_tok += 1
        for d in ss.fleet:
            if d["cid"] in BULBLIKE and d["on"] and d["lvl"] > 10 and d["room"] == ss.presence["room"]:
                set_dev(d, lvl=8)
        return "🌙 Wind-Down Sleep is on and the bulbs are dimmed. Rest well."
    if kind == "work":
        clear_room_override(ss.presence["room"])
        apply_mode("Focus")
        for d in ss.fleet:
            if d["cid"] == "tasklight" and d["room"] in (room, ss.presence["room"], "Work Studio"):
                set_dev(d, True, 80)
        return "💼 Focus mode is on with bright task lighting."
    if kind == "movie":
        clear_room_override(ss.presence["room"])
        apply_mode(CINEMA_MODE)
        for d in near:
            if d["cid"] in ("tv", "projector"):
                set_dev(d, True)
            if d["cid"] == "curtain":
                set_dev(d, True, 0)
        return "🎬 Curtains closed and Cinematic lighting is on. Enjoy the movie."
    if kind == "relax":
        clear_room_override(ss.presence["room"])
        apply_mode("Relax Evening")
        return "🌿 Relax Evening is on."
    if kind == "away":
        set_away_mode()
        return "🚗 Away Mode is on. I will prepare your arrival."
    if kind == "home":
        go_home_mode()
        return "🏠 Welcome home."
    if kind in ("dim", "bright", "off"):
        for d in near:
            if d["cid"] in LIGHT_CIDS:
                if kind == "off":
                    set_dev(d, False)
                elif d["on"]:
                    set_dev(d, lvl=d["lvl"] + (20 if kind == "bright" else -20))
        return "💡 Done."
    if kind in ("cool", "warm"):
        for d in near:
            if d["cid"] in ("ac", "thermo", "heater") and d["on"]:
                set_dev(d, lvl=d["lvl"] + (-1 if kind == "cool" else 1))
        return "❄️ Climate adjusted by 1 °C."
    return ""


def run_voice(text):
    low = (text or "").lower().strip()
    for kind, keys in VOICE_INTENTS:
        if any(k in low for k in keys):
            msg = voice_do(kind)
            if msg:
                log("🎙️ Voice: “" + text.strip() + "” → " + kind)
                if kind in KIND_TO_ID:
                    dispatch_cloud(KIND_TO_ID[kind], "voice")
                return msg
    return t("voice_unknown")


def cb_voice_send():
    ss = st.session_state
    txt = (ss.get("voice_txt") or "").strip()
    if txt:
        ss.voice_last = run_command(txt)


def cb_voice_preset(text):
    st.session_state.voice_last = run_command(text)


def render_voice_bar():
    ss = st.session_state
    st.markdown("**" + t("voice_title") + "**")
    render_voice_mic()
    cols = st.columns(3)
    for col, (k, text) in zip(cols, (("tired", "I'm tired"), ("work", "Starting work"), ("movie", "Family movie time"))):
        col.button(t("voice_" + k), key="voice_p_" + k, on_click=cb_voice_preset, args=(text,))
    if ss.voice_last:
        st.caption(ss.voice_last)


SIRI_SHORTCUT_URL = "https://www.icloud.com/shortcuts/2032cdddec6f4f8e8b8ed1fcb2432b32"
HTTP_SHORTCUTS_URL = "https://play.google.com/store/apps/details?id=ch.rmy.android.http_shortcuts"


def render_assistant_card():
    """Black & gold card with the two 1-tap onboarding buttons (under the Lock Screen Live Activity bar)."""
    st.markdown(
        '<div class="aucard"><div class="at">✦ ' + html.escape(t("as_title")) + '</div><div class="as">' +
        html.escape(t("as_sub")) + '</div><div class="ab">'
        '<a class="abtn" href="' + SIRI_SHORTCUT_URL + '" target="_blank" rel="noopener noreferrer"> ' +
        html.escape(t("as_siri")) + '</a>'
        '<a class="abtn ghost" href="' + HTTP_SHORTCUTS_URL + '" target="_blank" rel="noopener noreferrer">🤖 ' +
        html.escape(t("as_google")) + "</a></div></div>", unsafe_allow_html=True)
    with st.expander("🤖 " + t("as_steps")):
        st.markdown("1. " + t("as_g1") + "\n2. " + t("as_g2") + "\n3. " + t("as_g3"))
        tok = _secret("AURASYNC_TOKEN")
        base = app_base_url()
        if tok and base:
            st.caption(t("as_g_link"))
            st.code(app_link(base, "reading"), language=None)
        else:
            st.caption(t("as_g_nolink"))


def render_zero_ui():
    render_watch_card()
    render_assistant_card()
    render_voice_bar()
    render_dial()


# ---- Family logic: shared-room occupancy guard + Guest Mode
def apply_neutral(room):
    ss = st.session_state
    ss.room_mode[room] = NEUTRAL_MODE
    apply_mode(NEUTRAL_MODE, why=False, devs=space_devs(room), set_active=False)


def cb_occ(room, key):
    ss = st.session_state
    n = ss.get(key, 1)
    ss.occupancy[room] = 2 if n == 2 else 1
    if ss.occupancy[room] == 2 and room_persona(room) == "shared":
        ss.family_lock.add(room)
        apply_neutral(room)
        log("👨‍👩‍👧 " + room + ": 2+ family members. Body signals are locked out; the room holds Neutral Family Ambience")
    else:
        if room in ss.family_lock:
            ss.family_lock.discard(room)
            ss.room_mode.pop(room, None)
            apply_mode(ss.active_mode, why=False, devs=space_devs(room), set_active=False)
            log("👤 " + room + ": back to one person. Personal comfort resumes")


def apply_guest_presets():
    ss = st.session_state
    mode = "Relax Evening" if "Relax Evening" in ss.modes else list(ss.modes)[0]
    for r in list(ss.room_mode):
        if r not in ss.family_lock:
            ss.room_mode.pop(r, None)
    apply_mode(mode, why=False, devs=list(ss.fleet))
    for d in ss.fleet:
        if d["cid"] == "ac":
            set_dev(d, True, 24)


def cb_guest(key):
    ss = st.session_state
    on = bool(ss.get(key))
    ss.guest_mode = on
    ss.guest_rev = ss.get("guest_rev", 0) + 1
    if on:
        apply_guest_presets()
        log("👥 Guest Mode ON: the whole home holds a welcoming, steady atmosphere")
    else:
        log("👥 Guest Mode OFF: automatic comfort resumes")


def guest_toggle(prefix):
    ss = st.session_state
    key = prefix + "_" + str(ss.get("guest_rev", 0))
    st.toggle("👥 " + t("guest_toggle") + " (ON / OFF)", value=bool(ss.guest_mode), key=key, on_change=cb_guest, args=(key,))


def render_family_panel():
    ss = st.session_state
    room = current_room()
    persona = room_persona(room)
    c1, c2 = st.columns(2)
    with c1:
        guest_toggle("guest_db")
        st.caption(t("guest_hint"))
    with c2:
        st.markdown("**" + ("🛋️ " if persona == "shared" else "🔒 ") + t("persona_" + persona) + "** · " + html.escape(tr_room(room)))
        if persona == "shared":
            key = "occ_" + room
            ss.occupancy.setdefault(room, 1)
            st.radio(t("occ_label"), [1, 2], index=ss.occupancy[room] - 1, horizontal=True, key=key,
                     format_func=lambda n: t("occ_1") if n == 1 else t("occ_2"), on_change=cb_occ, args=(room, key))
            if room in ss.family_lock:
                st.info(t("occ_lock"))


# ---- Matter 1.3 plug & play onboarding (simulated pairing)
MATTER_RE = re.compile(r"^MT:[A-Z0-9.\-]{8,40}$")
MATTER_MANUAL = re.compile(r"^\d{4}-?\d{3}-?\d{4}$")
MATTER_KINDS = [("bulb", "Philips WiZ Bulb"), ("diffuser", "Smart Scent Diffuser"), ("curtain", "Curtain Motor")]


def matter_valid(code):
    c = (code or "").strip().upper()
    return bool(MATTER_RE.match(c) or MATTER_MANUAL.match(c))


def matter_kind(code):
    h = int(hashlib.sha1(code.strip().upper().encode()).hexdigest(), 16)
    return MATTER_KINDS[h % len(MATTER_KINDS)]


def matter_add(code, room):
    ss = st.session_state
    cid, label = matter_kind(code)
    nd = new_device(cid, unique_name(label), room)
    nd["proto"], nd["status"], nd["addr"] = "Matter over Thread/Wi-Fi", "connected", ""
    nd["last"] = "paired with Matter 1.3 in 5 s"
    ss.fleet.append(nd)
    ss.spaces[room]["devices"].append(nd["uid"])
    ss.room_rev = ss.get("room_rev", 0) + 1
    log("📷 Matter: " + nd["name"] + " paired and bound to " + room)
    return nd


def matter_body():
    ss = st.session_state
    st.caption(t("matter_help"))
    code = st.text_input(t("matter_code"), key="mt_code", placeholder="MT:Y.K10000000000")
    rooms = list(ss.spaces)
    room = st.selectbox(t("matter_room"), rooms, index=rooms.index(current_room()), key="mt_room",
                        format_func=tr_room)
    c1, c2 = st.columns(2)
    pair = c1.button(t("matter_pair"), key="mt_pair", type="primary")
    demo = c2.button(t("matter_demo"), key="mt_demo")
    if not (pair or demo):
        return
    use = code.strip().upper() if pair else "MT:DEMO" + str(random.randint(10000, 99999))
    if pair and not matter_valid(use):
        st.error(t("matter_bad"))
        return
    bar, box = st.progress(0.0), st.empty()
    steps = ("matter_s1", "matter_s2", "matter_s3", "matter_s4", "matter_s5")
    for i, s in enumerate(steps):
        box.markdown("**" + t(s) + "**")
        bar.progress((i + 1) / len(steps))
        time.sleep(1.0)
    nd = matter_add(use, room)
    ss.flash = "✅ " + t("matter_ok", n=nd["name"], r=tr_room(room))
    st.rerun()


def open_matter():
    title = tr(t("matter_title"))
    if hasattr(st, "dialog"):
        st.dialog(title)(matter_body)()
    else:
        with st.expander(title, expanded=True):
            matter_body()


# ----------------------------------------------------------------------------
# Add a device: one short popup (what is it -> how does it connect -> name + room)
# ----------------------------------------------------------------------------
AW_TYPES = (("bulb", "\U0001F4A1", "Light"), ("fan", "\U0001F300", "Fan"), ("ac", "\u2744", "AC"))
AW_WIZ, AW_HUB, AW_DEMO, AW_HA = "wiz", "hub", "demo", "ha"


def aw_reset():
    ss = st.session_state
    for k in ("aw_type", "aw_how", "aw_ip", "aw_url", "aw_tok", "aw_name", "aw_room", "aw_other", "aw_err",
              "aw_ha_url", "aw_ha_tok", "aw_ha_list", "aw_ha_msg", "aw_ha_ent", "aw_ha_man"):
        ss.pop(k, None)


def aw_create(cid, how, ip, url, tok, name, room, ha_ent=""):
    """Create the device, put it in the room and return (device, error)."""
    ss = st.session_state
    if cid not in CAT or room not in ss.spaces:
        return None, "Pick a device type and a room."
    proto, addr, token = "Simulation", "", ""
    if how == AW_WIZ:
        ip = ip.strip()
        if not wiz_ip_ok(ip):
            return None, "That does not look like a home Wi-Fi address. It should look like 192.168.1.45."
        proto, addr = "Philips WiZ (UDP)", ip
    elif how == AW_HA:
        ha_ent = (ha_ent or "").strip().lower()
        if not ha_cfg():
            return None, "Link Home Assistant first: enter its address and access token."
        if not HA_ENT_RE.match(ha_ent):
            return None, "Pick a device from the list, or type its Home Assistant name like light.living_room."
        proto, addr = "Home Assistant API", ha_ent
    elif how == AW_HUB:
        url = url.strip()
        if not (url.startswith("http://") or url.startswith("https://")):
            return None, "The webhook address must start with http:// or https://"
        proto, addr, token = "Home Assistant / REST", url[:300], tok.strip()[:300]
    nd = new_device(cid, unique_name((name or "").strip()[:40] or CAT[cid][2]), room)
    nd["proto"], nd["addr"], nd["token"] = proto, addr, token
    nd["status"] = "connected"
    nd["last"] = "added just now" if proto != "Simulation" else "demo device ready"
    ss.fleet.append(nd)
    ss.spaces[room]["devices"].append(nd["uid"])
    ss.room_rev = ss.get("room_rev", 0) + 1
    log("\u2795 " + nd["name"] + " added to " + room)
    if proto != "Simulation":
        push(nd)                                   # lets the iPhone app / server reach it right away
    return nd, ""


def found_ok(cid):
    """True when the device list chosen in the popup belongs to the current device type."""
    ss = st.session_state
    want = {"bulb": ("light",), "fan": ("fan",), "ac": ("climate",)}.get(cid, HA_DOMAINS)
    return any(e["entity_id"] == ss.get("aw_ha_ent") and e["domain"] in want for e in (ss.get("aw_ha_list") or []))


def add_wizard_body():
    ss = st.session_state
    st.markdown("**1. What are you adding?**")
    cols = st.columns(4)
    for col, (cid, icon, label) in zip(cols, AW_TYPES):
        if col.button(icon + " " + label, key="aw_t_" + cid, width="stretch",
                      type="primary" if ss.get("aw_type") == cid else "secondary"):
            ss["aw_type"] = cid
    if cols[3].button("\u2795 Other", key="aw_t_other", width="stretch",
                      type="primary" if ss.get("aw_type") == "other" else "secondary"):
        ss["aw_type"] = "other"
    typ = ss.get("aw_type")
    if typ == "other":
        others = [k for k in CAT if k not in ("bulb", "fan", "ac")]
        st.selectbox("Device type", others, key="aw_other", format_func=lambda k: CAT[k][1] + " " + CAT[k][2])
        cid = ss.get("aw_other") if ss.get("aw_other") in CAT else others[0]
    else:
        cid = typ
    if cid not in CAT:
        st.caption("Tap the kind of device you want to add.")
        return

    st.markdown("**2. How does it connect?**")
    opts = ([(AW_WIZ, "Philips WiZ bulb")] if cid == "bulb" else []) + [
        (AW_HA, "Home Assistant (finds my devices)"), (AW_HUB, "Other hub or webhook"),
        (AW_DEMO, "Just try it first (demo device)")]
    st.radio("How does it connect?", [o[0] for o in opts], key="aw_how", label_visibility="collapsed",
             format_func=lambda k: dict(opts)[k])
    how = ss.get("aw_how") if ss.get("aw_how") in dict(opts) else opts[0][0]
    if how == AW_WIZ:
        st.text_input("Bulb address on your home Wi-Fi", key="aw_ip", placeholder="192.168.1.45", max_chars=45,
                      help="Your router's list of connected devices shows it, named wiz_... In the WiZ app, "
                           "also switch on Allow local communication for this bulb.")
    elif how == AW_HA:
        ha = ss.cfg.get("ha") if isinstance(ss.cfg.get("ha"), dict) else {}
        st.text_input("Home Assistant address", value=ha.get("url", ""), key="aw_ha_url",
                      placeholder="https://xxxx.ui.nabu.casa", max_chars=300)
        st.text_input("Access token", value=ha.get("token", ""), key="aw_ha_tok", type="password", max_chars=600,
                      help="In Home Assistant open your profile, then Security, then Long-lived access tokens, and create one.")
        if st.button("\U0001F50D Find my devices", key="aw_ha_find"):
            if ha_save(ss.get("aw_ha_url") or "", ss.get("aw_ha_tok") or ""):
                found, msg = ha_discover()
                ss["aw_ha_list"], ss["aw_ha_msg"] = found, msg
            else:
                ss["aw_ha_list"], ss["aw_ha_msg"] = [], "Enter the address (starting with https://) and the access token."
        if ss.get("aw_ha_msg"):
            st.warning(ss["aw_ha_msg"])
        want = {"bulb": ("light",), "fan": ("fan",), "ac": ("climate",)}.get(cid, HA_DOMAINS)
        found = [e for e in (ss.get("aw_ha_list") or []) if e["domain"] in want]
        if found:
            st.selectbox("Pick your device", [e["entity_id"] for e in found], key="aw_ha_ent",
                         format_func=lambda k: next(e["name"] for e in found if e["entity_id"] == k) + "  (" + k + ")")
        st.text_input("Or type its Home Assistant name", key="aw_ha_man", placeholder="light.living_room", max_chars=80)
    elif how == AW_HUB:
        st.text_input("Webhook address", key="aw_url", placeholder="https://...", max_chars=300)
        st.text_input("Access token (only if your hub needs one)", key="aw_tok", type="password", max_chars=300)

    st.markdown("**3. Name and room**")
    rooms = list(ss.spaces)
    c1, c2 = st.columns(2)
    c1.text_input("Name", key="aw_name", placeholder=CAT[cid][2], max_chars=40)
    cur = current_room()
    c2.selectbox("Room", rooms, key="aw_room", index=rooms.index(cur) if cur in rooms else 0, format_func=tr_room)
    if ss.get("aw_err"):
        st.error(ss["aw_err"])
    if st.button("\u2795 Add device", key="aw_go", type="primary", width="stretch"):
        nd, err = aw_create(cid, how, ss.get("aw_ip") or "", ss.get("aw_url") or "", ss.get("aw_tok") or "",
                            ss.get("aw_name") or "", ss.get("aw_room") or cur,
                            (ss.get("aw_ha_man") or "").strip() or (ss.get("aw_ha_ent") if how == AW_HA and found_ok(cid) else ""))
        if err:
            ss["aw_err"] = err
            st.rerun(scope="fragment")
        aw_reset()
        ss.flash = "\u2705 " + nd["name"] + " added to " + tr_room(nd["room"]) + ". It is saved to your account."
        st.rerun()


def open_add_wizard():
    aw_reset()
    title = "Add a device"
    if hasattr(st, "dialog"):
        st.dialog(title)(add_wizard_body)()
    else:
        with st.expander(title, expanded=True):
            add_wizard_body()


# ----------------------------------------------------------------------------
# Page 6 - Room Settings, Remote Access & Smart Geofence
# ----------------------------------------------------------------------------
def cb_power(uid, key):
    ss = st.session_state
    d = dev_by_uid(uid)
    if d is not None and key in ss:
        set_dev(d, bool(ss[key]), why="switched by you" + (" (☁️ cloud relay)" if ss.conn["mode"] == "away" else ""))


def cb_level(uid, key):
    ss = st.session_state
    d = dev_by_uid(uid)
    if d is not None and key in ss:
        set_dev(d, lvl=ss[key], why="level set by you")


def cb_color(uid, key):
    ss = st.session_state
    d = dev_by_uid(uid)
    if d is None or key not in ss:
        return
    if valid_hex(ss[key]):
        set_dev(d, color=ss[key], why="colour set by you")
    else:
        d["rev"] = d.get("rev", 0) + 1


def cb_rename(uid, key):
    ss = st.session_state
    d = dev_by_uid(uid)
    if d is None or key not in ss:
        return
    new = (ss[key] or "").strip()
    if new == d["name"]:
        return
    d["rev"] = d.get("rev", 0) + 1     # rebuilds the input (restores the old name if the new one is rejected)
    if not new or len(new) > 40 or name_taken(new, uid):
        ss.flash = t("dev_rename_bad")
        return
    log("✏️ " + d["name"] + " renamed to " + new)
    d["name"] = new
    ss.flash = t("dev_renamed", n=new)


def cb_dev_room(uid, key):
    ss = st.session_state
    d = dev_by_uid(uid)
    r = ss.get(key)
    if d is not None and r in ss.spaces and r != d["room"]:
        assign_device(d, r)
    ss.room_rev = ss.get("room_rev", 0) + 1


def cb_dev_field(uid, key, field):
    d = dev_by_uid(uid)
    if d is not None and key in st.session_state:
        d[field] = (st.session_state[key] or "").strip()


def cb_proto(uid, key):
    d = dev_by_uid(uid)
    v = st.session_state.get(key)
    if d is not None and v and v != d["proto"]:
        d["proto"] = v
        d["status"] = "connected" if v == "Simulation" else "not connected"


COLOR_CIDS = ("bulb", "tasklight", "ambilight", "ledstrip", "lamp")


def device_editor(d, p):
    """Rename + power + level + colour for one device."""
    uid = d["uid"]
    c = CAT[d["cid"]]
    tag = p + "_" + str(uid) + "_" + str(d.get("rev", 0))
    a, b, lv, co = st.columns([3, 1.2, 3, 1])
    k = "nm_" + tag
    a.text_input(t("dev_rename"), value=d["name"], key=k, max_chars=40, on_change=cb_rename, args=(uid, k))
    k = "pwr_" + tag
    b.toggle(t("power_lbl"), value=bool(d["on"]), key=k, on_change=cb_power, args=(uid, k))
    if c[4]:
        k = "lvl_" + tag
        lo, hi = int(c[5]), int(c[6])
        lv.slider(c[4], lo, hi, value=max(lo, min(hi, int(d["lvl"]))), key=k, on_change=cb_level, args=(uid, k))
    if d["cid"] in COLOR_CIDS:
        k = "col_" + tag
        co.color_picker(t("bulb"), value=safe_hex(d["color"]), key=k, on_change=cb_color, args=(uid, k))


def add_device_here():
    ss = st.session_state
    room = current_room()
    cid = ss.get("ad_cid")
    if cid not in CAT:
        return
    base = (ss.get("ad_name") or "").strip()[:40] or CAT[cid][2]
    nd = new_device(cid, unique_name(base), room)
    ss.fleet.append(nd)
    ss.spaces[room]["devices"].append(nd["uid"])
    ss.room_rev = ss.get("room_rev", 0) + 1
    log("➕ " + nd["name"] + " added to " + room)
    ss.flash = t("rs_dev_added", n=nd["name"], r=tr_room(room))


def move_devices_here(key):
    ss = st.session_state
    room = current_room()
    moved = 0
    for uid in list(ss.get(key) or []):
        d = dev_by_uid(uid)
        if d and d["room"] != room:
            assign_device(d, room)
            moved += 1
    ss.room_rev = ss.get("room_rev", 0) + 1
    if moved:
        log("🔀 " + str(moved) + " device(s) moved into " + room)
        ss.flash = t("rs_moved", c=moved, n=tr_room(room))


def delete_space(key):
    """Delete the selected custom space."""
    ss = st.session_state
    name = current_room()
    if name in PROTECTED_SPACES:
        ss.flash = t("rs_protected")
        return
    dests = [n for n in ss.spaces if n != name]
    if not dests:
        ss.flash = t("rs_last")
        return
    dest = ss.get(key) if ss.get(key) in dests else dests[0]
    moving = [d for d in ss.fleet if d["room"] == name or d["uid"] in ss.spaces[name]["devices"]]
    for d in moving:
        assign_device(d, dest)
    ss.spaces[name]["devices"] = []
    ss.spaces.pop(name, None)
    ss.room_mode.pop(name, None)
    if ss.presence["room"] == name:
        ss.presence["room"] = dest
    repair_orphans()
    set_active_room(dest)
    log("🗑 Space deleted: " + name + " (" + str(len(moving)) + " device(s) moved to " + dest + ")")
    ss.flash = t("rs_deleted", n=tr_room(name))


def render_room_settings():
    ss = st.session_state
    st.subheader("🏠 " + t("rs_sec_room"))
    room_selector("rs", t("rs_room"))
    room = current_room()
    sp = ss.spaces[room]
    devs = space_devs(room)
    st.markdown("**" + sp["icon"] + " " + html.escape(tr_room(room)) + "** · " + str(len(devs)) + " 🔌 · " +
                ("🛋️ " if room_persona(room) == "shared" else "🔒 ") + t("persona_" + room_persona(room)))

    st.markdown("**⚡ " + t("rs_preset") + "**")
    st.caption(t("rs_preset_hint"))
    pre = sp.get("preset")
    b1, b2, b3 = st.columns([3, 2, 1])
    b1.button(t("rs_preset_save"), key="rs_pre_save", on_click=cb_save_preset)
    b2.button("⚡ " + t("rs_preset_apply", n=tr_room(room)), key="rs_pre_apply", disabled=not pre,
              on_click=cb_apply_preset, args=(room,))
    b3.button(t("rs_preset_clear"), key="rs_pre_clear", disabled=not pre, on_click=cb_clear_preset)
    if pre:
        st.caption(t("rs_preset_has", c=len(pre)))

    if st.button("\u2795 Add a device", key="rs_aw_open", type="primary"):
        open_add_wizard()
    with st.expander(t("rs_devices"), expanded=True):
        if not devs:
            st.caption(t("room_empty"))
        for d in devs:
            with st.container(border=True):
                st.markdown("**" + CAT[d["cid"]][1] + " " + html.escape(d["name"]) + "** · " + CAT[d["cid"]][2])
                device_editor(d, "rs")
                st.button("🗑 " + t("rs_dev_remove"), key="rs_rm_" + str(d["uid"]), on_click=remove_device,
                          args=(d["uid"],))

    with st.expander(t("rs_add_dev")):
        with st.form("add_dev_form", clear_on_submit=True):
            f1, f2 = st.columns([3, 2])
            f1.selectbox(t("dev_pick"), list(CAT.keys()), key="ad_cid",
                         format_func=lambda k: CAT[k][1] + " " + CAT[k][2] + "  ·  " + CAT[k][3])
            f2.text_input(t("dev_name"), key="ad_name", max_chars=40)
            st.form_submit_button(t("dev_btn"), on_click=add_device_here)

    with st.expander(t("qc")):
        cols = st.columns(3)
        for i, d in enumerate(devs):
            with cols[i % 3]:
                k = "qc_pwr_" + str(d["uid"]) + "_" + str(d.get("rev", 0))
                st.toggle(CAT[d["cid"]][1] + " " + d["name"], value=bool(d["on"]), key=k, on_change=cb_power,
                          args=(d["uid"], k))

    with st.expander(t("add_space")):
        with st.form("add_space_form", clear_on_submit=True):
            st.text_input(t("sp_name"), key="sp_name", max_chars=40)
            f1, f2 = st.columns(2)
            f1.selectbox(t("sp_icon"), SPACE_ICONS, key="sp_icon")
            f2.selectbox(t("sp_type"), SPACE_TYPES, key="sp_type")
            st.selectbox(t("persona_pick"), ["personal", "shared"], key="sp_persona",
                         format_func=lambda x: t("persona_" + x))
            labels = {d["uid"]: CAT[d["cid"]][1] + " " + d["name"] + "  (" + d["room"] + ")" for d in ss.fleet}
            st.multiselect(t("sp_devs"), list(labels.keys()), format_func=lambda u: labels[u], key="sp_devs")
            st.form_submit_button(t("sp_btn"), on_click=create_space)

    with st.expander(t("rs_manage")):
        others = {d["uid"]: CAT[d["cid"]][1] + " " + d["name"] + "  (" + d["room"] + ")"
                  for d in ss.fleet if d["room"] != room}
        mk = "rs_move_" + str(ss.get("room_rev", 0)) + "_" + room
        st.multiselect(t("rs_move"), list(others.keys()), default=[], format_func=lambda u: others[u], key=mk)
        st.button(t("rs_move_btn"), key="rs_move_btn", on_click=move_devices_here, args=(mk,))
        st.divider()
        dests = [n for n in ss.spaces if n != room]
        if room in PROTECTED_SPACES:
            st.caption(t("rs_protected"))
        elif dests:
            dk = "rs_dest_" + str(ss.get("room_rev", 0)) + "_" + room
            st.selectbox(t("rs_dest"), dests, key=dk, format_func=tr_room)
            st.button("🗑 " + t("rs_del"), key="rs_del_btn", on_click=delete_space, args=(dk,))


def page_rooms():
    st.header(t("p6"))
    st.caption(t("rs_hint"))
    render_room_settings()
    st.divider()
    render_connection()
    st.divider()
    render_microloc()


def render_routines():
    ss = st.session_state
    st.divider()
    st.subheader("⏰ " + t("rt_title"))
    st.caption(t("rt_hint"))
    today = date.today().isoformat()
    labels = {d["uid"]: CAT[d["cid"]][1] + " " + d["name"] for d in ss.fleet}
    for r in list(ss.daily_routines):
        rid = r["id"]
        with st.container(border=True):
            h1, h2 = st.columns([4, 1])
            h1.markdown("**" + html.escape(r["name"]) + "**")
            r["enabled"] = h2.toggle(t("rt_on"), value=r["enabled"], key="rt_en_" + rid)
            if r["kind"] == "wake_bath":
                a, b, c = st.columns(3)
                r["wake"] = a.time_input(t("rt_wake"), value=r["wake"], step=300, key="rt_wk_" + rid)
                r["bath"] = b.time_input(t("rt_bath"), value=r["bath"], step=300, key="rt_bt_" + rid)
                r["offset"] = c.number_input(t("rt_off"), 0, 120, int(r["offset"]), step=5, key="rt_of_" + rid)
            elif r["kind"] == "wind_down":
                a, c = st.columns(2)
                r["sleep"] = a.time_input(t("rt_sleep"), value=r["sleep"], step=300, key="rt_sl_" + rid)
                r["offset"] = c.number_input(t("rt_off"), 0, 120, int(r["offset"]), step=5, key="rt_of_" + rid)
            else:
                a, c = st.columns(2)
                r["time"] = a.time_input(t("rt_time"), value=r["time"], step=300, key="rt_tm_" + rid)
                r["offset"] = c.number_input(t("rt_off"), 0, 120, int(r["offset"]), step=5, key="rt_of_" + rid)
                keep = [u for u in r.get("uids", []) if u in labels]
                r["uids"] = st.multiselect(t("rt_devs"), list(labels.keys()), default=keep,
                                           format_func=lambda u: labels[u], key="rt_dv_" + rid)
                r["on"] = st.radio(t("rt_act"), ["Switch ON", "Switch OFF"], index=0 if r.get("on", True) else 1,
                                   horizontal=True, key="rt_ac_" + rid) == "Switch ON"
            st.info(routine_logic(r))
            f1, f2, f3 = st.columns([1, 1, 3])
            f1.button(t("rt_run"), key="rt_go_" + rid, on_click=run_routine_now, args=(rid,))
            if r["kind"] == "custom":
                f2.button("🗑", key="rt_dl_" + rid, on_click=del_routine, args=(rid,))
            if any(ss.routine_runs.get(rid + ":" + tag) == today for tag, _ in routine_events(r)):
                f3.caption(t("rt_ran"))
    with st.expander(t("rt_add")):
        with st.form("add_routine_form", clear_on_submit=True):
            st.text_input(t("rt_name"), key="nr_name")
            a, b = st.columns(2)
            a.time_input(t("rt_time"), value=dtime(18, 0), step=300, key="nr_time")
            b.number_input(t("rt_off"), 0, 120, 0, step=5, key="nr_off")
            st.multiselect(t("rt_devs"), list(labels.keys()), format_func=lambda u: labels[u], key="nr_devs")
            st.radio(t("rt_act"), ["Switch ON", "Switch OFF"], horizontal=True, key="nr_act")
            st.form_submit_button(t("save"), on_click=add_routine)


# ----------------------------------------------------------------------------
# Page 2 - Moods & Settings
# ----------------------------------------------------------------------------
def extra_name(k):
    return CAT[k][1] + " " + CAT[k][2]


def page_moods():
    if st.session_state.ui_mode == "pro":
        page_moods_pro()
        return
    st.header(t("p2"))
    st.caption(t("zen_hidden"))
    render_routines()


def page_moods_pro():
    ss = st.session_state
    st.header(t("p2"))
    st.subheader(t("std_cfg"))
    names = list(ss.modes.keys())
    sel = st.selectbox(t("mode"), names, index=names.index(ss.active_mode), key="edit_mode_sel", format_func=tr_mode)
    m = ss.modes[sel]
    c1, c2, c3, c4, c5 = st.columns(5)
    bulb = c1.color_picker(t("bulb"), m["bulb"], key="cp_" + sel)
    bright = c2.slider(t("bright"), 5, 100, int(m.get("bright", 60)), key="br_" + sel)
    fan = c3.slider(t("fan"), 0, 5, int(m["fan"]), key="fan_" + sel)
    ac = c4.slider(t("ac"), 16, 30, int(m["ac"]), key="ac_" + sel)
    genre = c5.selectbox(t("genre"), GENRES, index=GENRES.index(m["genre"]) if m["genre"] in GENRES else 0, key="gn_" + sel)
    t1, t2, t3, t4 = st.columns(4)
    bulb_on = t1.toggle(t("bulb_pw"), value=bool(m.get("bulb_on", True)), key="bo_" + sel)
    fan_on = t2.toggle(t("fan_pw"), value=bool(m.get("fan_on", True)), key="fo_" + sel)
    ac_on = t3.toggle(t("ac_pw"), value=bool(m.get("ac_on", True)), key="ao_" + sel)
    curtain = t4.slider(t("curtain"), 0, 100, int(m.get("curtain", 50)), key="cu_" + sel)
    ex = st.multiselect(t("extras"), AMB, default=[x for x in m.get("extras", []) if x in AMB],
                        format_func=extra_name, key="ex_" + sel)
    if st.button(t("save"), key="save_std"):
        if not valid_hex(bulb):
            st.warning(t("mode_bad_color"))
        else:
            ss.modes[sel] = dict(m, bulb=bulb.strip(), bright=bright, fan=fan, ac=ac, genre=genre, curtain=curtain,
                                 bulb_on=bulb_on, fan_on=fan_on, ac_on=ac_on, extras=ex, mix=full_mix(m.get("mix")))
            if sel == ss.active_mode:
                apply_mode(sel)
            ss.flash = t("saved")
            st.rerun()

    st.divider()
    st.subheader(t("custom"))
    cname = st.text_input(t("cname"), key="cm_name")
    d1, d2, d3, d4 = st.columns(4)
    scene = d1.selectbox(t("dev_bulb"), list(SCENES.keys()), key="cm_scene")
    acm = d2.selectbox(t("dev_ac"), AC_MODES, key="cm_acm")
    fanm = d3.selectbox(t("dev_fan"), list(FAN_MODES.keys()), index=1, key="cm_fan")
    actemp = d4.slider(t("ac"), 16, 30, 24, key="cm_actemp")
    q1, q2, q3, q4 = st.columns(4)
    cbo = q1.toggle(t("bulb_pw"), value=True, key="cm_bo")
    cfo = q2.toggle(t("fan_pw"), value=True, key="cm_fo")
    cao = q3.toggle(t("ac_pw"), value=True, key="cm_ao")
    ccu = q4.slider(t("curtain"), 0, 100, 50, key="cm_cu")
    cgenre = st.selectbox(t("genre"), GENRES, key="cm_genre")
    cex = st.multiselect(t("extras"), AMB, format_func=extra_name, key="cm_ex")
    st.caption(t("intens"))
    cols = st.columns(5)
    mix = {}
    for i, ins in enumerate(INSTRUMENTS):
        with cols[i % 5]:
            mix[ins] = st.slider(ins, 0, 100, 0, key="cm_mix_" + ins)
    if st.button(t("save"), key="save_custom"):
        nm = (cname or "").strip()
        col = SCENES.get(scene, "")
        if not valid_mode_name(nm):
            st.warning(t("mode_bad_name"))
        elif nm in ss.modes:
            st.warning(t("mode_dup"))
        elif not valid_hex(col):
            st.warning(t("mode_bad_color"))
        else:
            ss.modes[nm] = {"bulb": col, "bright": 60, "fan": FAN_MODES.get(fanm, 1), "ac": actemp,
                            "curtain": ccu, "genre": cgenre if cgenre in GENRES else GENRES[0], "acmode": acm,
                            "mix": full_mix(mix), "bulb_on": cbo, "fan_on": cfo, "ac_on": cao, "extras": cex}
            ss.flash = t("saved")
            st.rerun()

    render_routines()


# ----------------------------------------------------------------------------
# Background chart engine.
# ----------------------------------------------------------------------------
PL_EL = {
    "Mercury": (0.38709927, 0.00000037, 0.20563593, 0.00001906, 7.00497902, -0.00594749, 252.25032350, 149472.67411175, 77.45779628, 0.16047689, 48.33076593, -0.12534081),
    "Venus": (0.72333566, 0.00000390, 0.00677672, -0.00004107, 3.39467605, -0.00078890, 181.97909950, 58517.81538729, 131.60246718, 0.00268329, 76.67984255, -0.27769418),
    "Earth": (1.00000261, 0.00000562, 0.01671123, -0.00004392, -0.00001531, -0.01294668, 100.46457166, 35999.37244981, 102.93768193, 0.32327364, 0.0, 0.0),
    "Mars": (1.52371034, 0.00001847, 0.09339410, 0.00007882, 1.84969142, -0.00813131, -4.55343205, 19140.30268499, -23.94362959, 0.44441088, 49.55953891, -0.29257343),
    "Jupiter": (5.20288700, -0.00011607, 0.04838624, -0.00013253, 1.30439695, -0.00183714, 34.39644051, 3034.74612775, 14.72847983, 0.21252668, 100.47390909, 0.20469106),
    "Saturn": (9.53667594, -0.00125060, 0.05386179, -0.00050991, 2.48599187, 0.00193609, 49.95424423, 1222.49362201, 92.59887831, -0.41897216, 113.66242448, -0.28867794),
}
AY0 = 23.85306
CITIES = {
    "chennai": (13.08, 80.27, 5.5), "madras": (13.08, 80.27, 5.5), "madurai": (9.92, 78.12, 5.5),
    "coimbatore": (11.02, 76.96, 5.5), "trichy": (10.80, 78.69, 5.5), "tiruchirappalli": (10.80, 78.69, 5.5),
    "salem": (11.66, 78.15, 5.5), "tirunelveli": (8.73, 77.70, 5.5), "vellore": (12.92, 79.13, 5.5),
    "erode": (11.34, 77.72, 5.5), "thanjavur": (10.79, 79.14, 5.5), "tiruppur": (11.11, 77.34, 5.5),
    "bengaluru": (12.97, 77.59, 5.5), "bangalore": (12.97, 77.59, 5.5), "hyderabad": (17.39, 78.49, 5.5),
    "mumbai": (19.08, 72.88, 5.5), "delhi": (28.61, 77.21, 5.5), "kolkata": (22.57, 88.36, 5.5),
    "pune": (18.52, 73.86, 5.5), "ahmedabad": (23.02, 72.57, 5.5), "kochi": (9.93, 76.27, 5.5),
    "thiruvananthapuram": (8.52, 76.94, 5.5), "jaipur": (26.91, 75.79, 5.5), "lucknow": (26.85, 80.95, 5.5),
    "colombo": (6.93, 79.86, 5.5), "kathmandu": (27.72, 85.32, 5.75), "dhaka": (23.81, 90.41, 6.0),
    "singapore": (1.35, 103.82, 8.0), "kuala lumpur": (3.14, 101.69, 8.0), "jakarta": (-6.2, 106.85, 7.0),
    "bangkok": (13.76, 100.50, 7.0), "manila": (14.60, 120.98, 8.0), "hong kong": (22.32, 114.17, 8.0),
    "seoul": (37.57, 126.98, 9.0), "tokyo": (35.68, 139.69, 9.0), "dubai": (25.20, 55.27, 4.0),
    "doha": (25.29, 51.53, 3.0), "riyadh": (24.71, 46.68, 3.0), "istanbul": (41.01, 28.98, 3.0),
    "moscow": (55.76, 37.62, 3.0), "cairo": (30.04, 31.24, 2.0), "london": (51.51, -0.13, 0.0),
    "paris": (48.86, 2.35, 1.0), "berlin": (52.52, 13.40, 1.0), "madrid": (40.42, -3.70, 1.0),
    "new york": (40.71, -74.01, -5.0), "toronto": (43.65, -79.38, -5.0), "san francisco": (37.77, -122.42, -8.0),
    "sydney": (-33.87, 151.21, 10.0),
}


def locate(place):
    s = place.lower()
    for k, v in CITIES.items():
        if k in s:
            return v
    return CITIES["chennai"]


def _s(x):
    return math.sin(math.radians(x))


def jd_of(dt):
    y, m = dt.year, dt.month
    d = dt.day + (dt.hour + dt.minute / 60.0 + dt.second / 3600.0) / 24.0
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4
    return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + b - 1524.5


def sun_lon(c):
    l0 = 280.46646 + 36000.76983 * c
    m = 357.52911 + 35999.05029 * c
    return (l0 + (1.914602 - 0.004817 * c) * _s(m) + 0.019993 * _s(2 * m) + 0.000289 * _s(3 * m)) % 360


def moon_lon(c):
    lp = 218.3164477 + 481267.88123421 * c
    d = 297.8501921 + 445267.1114034 * c
    m = 357.5291092 + 35999.0502909 * c
    mp = 134.9633964 + 477198.8675055 * c
    f = 93.2720950 + 483202.0175233 * c
    lon = (lp + 6.288774 * _s(mp) + 1.274027 * _s(2 * d - mp) + 0.658314 * _s(2 * d) + 0.213618 * _s(2 * mp)
           - 0.185116 * _s(m) - 0.114332 * _s(2 * f) + 0.058793 * _s(2 * d - 2 * mp) + 0.057066 * _s(2 * d - m - mp)
           + 0.053322 * _s(2 * d + mp) + 0.045758 * _s(2 * d - m) - 0.040923 * _s(m - mp) - 0.034720 * _s(d)
           - 0.030383 * _s(m + mp))
    return lon % 360


def helio(name, c):
    el = PL_EL[name]
    a, e, inc = el[0] + el[1] * c, el[2] + el[3] * c, el[4] + el[5] * c
    big_l, w, node = el[6] + el[7] * c, el[8] + el[9] * c, el[10] + el[11] * c
    mm = math.radians((big_l - w) % 360)
    ea = mm + e * math.sin(mm)
    for _ in range(6):
        ea = ea - (ea - e * math.sin(ea) - mm) / (1 - e * math.cos(ea))
    xp, yp = a * (math.cos(ea) - e), a * math.sqrt(1 - e * e) * math.sin(ea)
    om, nd, ic = math.radians(w - node), math.radians(node), math.radians(inc)
    x = (math.cos(om) * math.cos(nd) - math.sin(om) * math.sin(nd) * math.cos(ic)) * xp + \
        (-math.sin(om) * math.cos(nd) - math.cos(om) * math.sin(nd) * math.cos(ic)) * yp
    y = (math.cos(om) * math.sin(nd) + math.sin(om) * math.cos(nd) * math.cos(ic)) * xp + \
        (-math.sin(om) * math.sin(nd) + math.cos(om) * math.cos(nd) * math.cos(ic)) * yp
    return x, y


def positions(utc):
    """Approximate sidereal longitudes (0-360) of the nine bodies for a UTC datetime."""
    c = (jd_of(utc) - 2451545.0) / 36525.0
    ay = AY0 + 1.39697 * c
    ex, ey = helio("Earth", c)
    out = {"Sun": (sun_lon(c) - ay) % 360, "Moon": (moon_lon(c) - ay) % 360}
    for nm in ("Mercury", "Venus", "Mars", "Jupiter", "Saturn"):
        x, y = helio(nm, c)
        out[nm] = (math.degrees(math.atan2(y - ey, x - ex)) - AY0) % 360
    out["Rahu"] = (125.0445479 - 1934.1362891 * c - ay) % 360
    out["Ketu"] = (out["Rahu"] + 180.0) % 360
    return out


def asc_lon(utc, lat, lon_e):
    jd = jd_of(utc)
    c = (jd - 2451545.0) / 36525.0
    gmst = (280.46061837 + 360.98564736629 * (jd - 2451545.0) + 0.000387933 * c * c) % 360
    ramc = math.radians((gmst + lon_e) % 360)
    eps = math.radians(23.439291 - 0.0130042 * c)
    y = math.cos(ramc)
    x = -(math.sin(ramc) * math.cos(eps) + math.tan(math.radians(lat)) * math.sin(eps))
    return (math.degrees(math.atan2(y, x)) - (AY0 + 1.39697 * c)) % 360


def build_chart(p):
    lat, lon, tz = locate(p["pob"])
    hh = p["h"] % 12 + (12 if p["ap"] == "PM" else 0)
    local = datetime(p["dob"].year, p["dob"].month, p["dob"].day, hh, p["m"])
    utc = local - timedelta(hours=tz)
    pos = positions(utc)
    return {"asc": int(asc_lon(utc, lat, lon) // 30), "pos": pos, "sign": {k: int(v // 30) for k, v in pos.items()},
            "birth": local, "tz": tz}


DASHA = [("Ketu", 7), ("Venus", 20), ("Sun", 6), ("Moon", 10), ("Mars", 7), ("Rahu", 18), ("Jupiter", 16),
         ("Saturn", 19), ("Mercury", 17)]
SIGN_LORD = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"]


def dasha_now(ch, now_local):
    moon = ch["pos"]["Moon"]
    span = 360.0 / 27
    i = int(moon // span) % 9
    frac = (moon % span) / span
    t0 = ch["birth"] - timedelta(days=frac * DASHA[i][1] * 365.25)
    while True:
        lord, yrs = DASHA[i % 9]
        end = t0 + timedelta(days=yrs * 365.25)
        if now_local < end:
            break
        t0, i = end, i + 1
    sub_start, sub, sub_end = t0, lord, end
    for k in range(9):
        sub, sy = DASHA[(i + k) % 9]
        sub_end = sub_start + timedelta(days=yrs * sy / 120.0 * 365.25)
        if now_local < sub_end:
            break
        sub_start = sub_end
    return lord, end, sub, sub_end


def chart_facts(p):
    ch = build_chart(p)
    sg, asc = ch["sign"], ch["asc"]
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    tr = positions(now_utc)
    tsg = {k: int(v // 30) for k, v in tr.items()}

    def house(pl):
        return (sg[pl] - asc) % 12 + 1

    def lord_of(offset):
        return SIGN_LORD[(asc + offset) % 12]

    def from_moon(pl):
        return (tsg[pl] - sg["Moon"]) % 12 + 1

    lord, end, sub, sub_end = dasha_now(ch, now_utc + timedelta(hours=ch["tz"]))
    day_h = from_moon("Moon")
    day = "good" if day_h in (3, 6, 10, 11) else ("tough" if day_h in (4, 8, 12) else "mid")
    f = {"lord": lord, "end": end.year, "sub": sub, "ela": asc % 4, "elm": sg["Moon"] % 4, "mod": sg["Moon"] % 3,
         "el7": (asc + 6) % 4, "l10": lord_of(9), "l7": lord_of(6), "l2": lord_of(1), "l11": lord_of(10),
         "l4": lord_of(3), "day": day, "sati": from_moon("Saturn") in (12, 1, 2),
         "jup_good": from_moon("Jupiter") in (2, 5, 7, 9, 11)}
    f["h10"] = house(f["l10"])
    for key, pl in (("hv", "Venus"), ("hm", "Mars"), ("hme", "Mercury"), ("hj", "Jupiter"), ("hk", "Ketu"),
                    ("hmoon", "Moon")):
        f[key] = house(pl)
    return f


# ----------------------------------------------------------------------------
# Divine Compass voice
# ----------------------------------------------------------------------------
ENERGY = {"Sun": "your core confidence", "Moon": "your emotional tides", "Mars": "your fire and drive",
          "Mercury": "your thinking mind", "Jupiter": "your wisdom and grace", "Venus": "your heart and love-energy",
          "Saturn": "your discipline and life-lessons", "Rahu": "your restless hunger to grow",
          "Ketu": "your detached, deeper-seeking side"}
HOUSE = ["", "your identity and personal path", "money, family and speech", "courage, skills and communication",
         "home, inner peace and roots", "creativity, learning and romance", "daily work, health and service",
         "partnership and close relationships", "transformation and hidden depths",
         "luck, higher learning and purpose", "career and public standing", "gains, friendships and big goals",
         "rest, solitude and letting go"]
ELEM = {0: "fiery, action-loving", 1: "grounded, steady", 2: "airy, curious", 3: "deep, feeling"}
NEED = {0: "action and inspiration", 1: "stability and visible progress", 2: "ideas and conversation",
        3: "emotional safety and meaning"}
PARTNER = {0: "bold, passionate", 1: "steady, dependable", 2: "witty, communicative", 3: "caring, emotionally deep"}
MODN = {0: "start-things-up", 1: "deep-focus", 2: "variety-loving"}
MODTIP = {0: "start a small project and learn by doing", 1: "go deep on one subject in long calm blocks",
          2: "mix subjects and use short, varied sessions"}
SEASON = {"Sun": "stepping into your own authority and visibility", "Moon": "emotional healing, home and nurturing",
          "Mars": "courage, action and building momentum", "Mercury": "learning, communication and smart moves",
          "Jupiter": "growth, guidance and expansion", "Venus": "love, comfort, creativity and refinement",
          "Saturn": "patient building, responsibility and deep life-lessons",
          "Rahu": "big ambition, change and unexpected turns", "Ketu": "letting go, spiritual deepening and clarity"}
DAYQ = {"good": "Today's energy around you is supportive, a good day to move on things you've been postponing.",
        "mid": "Today feels mixed and steady, so go step by step and don't rush big decisions.",
        "tough": "Today's energy is a little sensitive and heavy, so protect your peace, go slow and avoid forcing decisions."}
TA_SEASON = {"Sun": "உங்கள் சுய அதிகாரம் மற்றும் அடையாளம் வளரும்", "Moon": "மன நலம், வீடு மற்றும் அரவணைப்பு",
             "Mars": "தைரியம், செயல் மற்றும் முன்னேற்றம்", "Mercury": "கற்றல், பேச்சு மற்றும் புத்திசாலித்தனமான முடிவுகள்",
             "Jupiter": "வளர்ச்சி, வழிகாட்டுதல் மற்றும் விரிவாக்கம்", "Venus": "அன்பு, சுகம் மற்றும் படைப்பாற்றல்",
             "Saturn": "பொறுமை, பொறுப்பு மற்றும் வாழ்க்கைப் பாடங்கள்",
             "Rahu": "பெரிய ஆசை, மாற்றம் மற்றும் எதிர்பாராத திருப்பங்கள்", "Ketu": "விடுதலை, ஆன்மீக ஆழம் மற்றும் தெளிவு"}
TA_ELEM = {0: "நெருப்பு போன்ற, செயலை விரும்பும்", 1: "நிலையான, அடித்தளமான", 2: "காற்று போன்ற, ஆர்வமுள்ள",
           3: "ஆழமான, உணர்வுப்பூர்வமான"}
TA_DAY = {"good": "இன்றைய சூழல் உங்களுக்கு ஆதரவாக உள்ளது; தள்ளிப்போட்ட வேலைகளைத் தொடங்கலாம்.",
          "mid": "இன்று கலவையான நாள்; அவசர முடிவுகள் வேண்டாம், படிப்படியாகச் செல்லுங்கள்.",
          "tough": "இன்று மனம் கொஞ்சம் உணர்ச்சிவசப்படும்; அமைதியைக் காத்து, முக்கிய முடிவுகளைத் தள்ளிவையுங்கள்."}


def insight_en(topic, f):
    s = SEASON[f["lord"]]
    if topic == "work":
        return ("I see your career path being steered by " + ENERGY[f["l10"]] + ", and it lives in the zone of " +
                HOUSE[f["h10"]] + ". You're also in a long season of " + s + " until " + str(f["end"]) +
                ", so growth will come through that door.")
    if topic == "love":
        return ("Your heart-energy lives in the zone of " + HOUSE[f["hv"]] + ", and you tend to attract " +
                PARTNER[f["el7"]] + " partners. You're in a season of " + s + ", which is shaping how you love and what you tolerate.")
    if topic == "money":
        return ("Money flows to you through " + ENERGY[f["l2"]] + ", and your gains arrive via " + ENERGY[f["l11"]] + ". " +
                ("Growth energy is supporting you right now, so careful expansion works."
                 if f["jup_good"] else "This is a steady-and-save phase rather than a big-risk phase."))
    if topic == "stress":
        return ("Your nature is " + ELEM[f["elm"]] + " and it needs " + NEED[f["elm"]] + " to feel safe. " +
                ("A heavy, testing phase is passing over your emotional tides right now, which is why everything feels louder than it really is. It is temporary."
                 if f["sati"] else "Your emotional tides are asking for rest and routine more than answers."))
    if topic == "anger":
        return ("Your fire sits in the zone of " + HOUSE[f["hm"]] + ", so whenever that part of life is touched you flare fast. " +
                DAYQ[f["day"]])
    if topic == "study":
        return ("Your thinking mind works through the zone of " + HOUSE[f["hme"]] + ", and wisdom flows from " +
                HOUSE[f["hj"]] + ". As a " + MODN[f["mod"]] + " learner you absorb best when you " + MODTIP[f["mod"]] + ".")
    if topic == "purpose":
        return ("Your wisdom and grace point toward " + HOUSE[f["hj"]] + ", while your deeper-seeking side in " +
                HOUSE[f["hk"]] + " asks you to loosen your grip there. This is a season of " + s + ", which is when purpose becomes clearer.")
    if topic == "family":
        return ("Home and roots are shaped by " + ENERGY[f["l4"]] + ", with your emotional tides in the zone of " +
                HOUSE[f["hmoon"]] + ". In this season of " + s + ", family patterns are being rewritten gently.")
    if topic == "health":
        return "Your vitality follows " + ELEM[f["elm"]] + " rhythms, so protect sleep and routine first. " + DAYQ[f["day"]]
    if topic == "decide":
        return ("Timing matters: you're in a season of " + s + ". " +
                ("Growth energy is on your side, so if your gut agrees, you can move."
                 if f["jup_good"] else "The energy favours patience: gather facts and wait for one clear sign."))
    if topic == "today":
        return DAYQ[f["day"]] + " You're in a season of " + s + " until " + str(f["end"]) + "."
    return "I feel you as a " + ELEM[f["ela"]] + " soul, currently in a season of " + s + " until " + str(f["end"]) + "."


def insight_ta(topic, f):
    return ("இப்போது நீங்கள் " + TA_SEASON[f["lord"]] + " என்ற காலகட்டத்தில் இருக்கிறீர்கள் (" + str(f["end"]) +
            " வரை). உங்கள் இயல்பு " + TA_ELEM[f["elm"]] + " தன்மை கொண்டது. " + TA_DAY[f["day"]])


def insight_tg(topic, f):
    return "Naan paakkaradhu: " + insight_en(topic, f)


GUIDE_EN = {
    "work": "Stop trying to prove yourself everywhere. Choose the one outcome that matters this week, tell your team clearly, and let the rest be 'good enough'.",
    "love": "Speak the feeling underneath the complaint. Say 'I feel...' before 'You always...'. Closeness grows from honesty, not perfect timing.",
    "money": "Put income, fixed costs and one goal on a single page. Any big spend that fails that page can wait 48 hours.",
    "stress": "Breathe out slower than you breathe in for two minutes, then do just one small task. Clarity follows calm, never the other way round.",
    "anger": "Don't act for 90 seconds. Breathe in for 4, hold for 4, out for 6. Then walk or splash cold water on your face before you speak and the message will come out cleaner.",
    "study": "Study in 25-minute blocks with 5-minute breaks and the phone in another room. Teach what you learned out loud to an imaginary student, that's how it sticks.",
    "purpose": "Purpose rarely arrives as a thunderbolt. Notice what you'd do for free and what drains you, then do a little more of the first and less of the second this month.",
    "family": "Listen for one full minute without defending yourself. Most family tension softens when people feel heard before they're corrected.",
    "health": "Fix your wake-up time, dim the lights an hour before bed and keep the next seven days simple. Sleep is the base of everything.",
    "decide": "Write what you'd choose if fear were not in the room. Then ask which option you'll respect yourself for a year from now.",
    "today": "Pick one priority for today, finish it before noon, and let everything else be a bonus.",
    "general": "Take one slow breath and tell me which part feels heaviest: the situation, the people, or the uncertainty?",
}
GUIDE_TG = {
    "work": "Ellathulayum nirupikka try pannathinga. Indha week-ku mukkiyamana oru result-a mattum choose pannunga, team-kitta clear-a sollunga, mathadhu 'good enough' nu vitrunga.",
    "love": "Complaint-ku pinnadi irukkura feeling-a pesunga. 'Nee eppavum...' nu solradhukku munnadi 'Enakku... nu thonuthu' nu sollunga. Nerukkam honesty-la varum.",
    "money": "Varumanam, selavu, oru goal - moonum oru page-la ezhudhunga. Sandhegam iruntha periya selavai 48 maniyaakku wait pannunga.",
    "stress": "Rendu nimisham mella moochu vidunga (ullukku vida veliyila neram jaasthi), appuram oru sinna velaiya mattum pannunga. Amaidhikku apuram thelivu varum.",
    "anger": "90 second edhuvum seiyaadheenga. 4 count moochu ulla, 4 pidichikonga, 6 count veliya. Appuram konjam nadanga illa mugathula thanni adinga, appuram pesunga.",
    "study": "25 nimisham padinga, 5 nimisham break. Phone vera room-la vainga. Padichadha oru imaginary student-ku sollikkudunga, appo dhaan manasula nikkum.",
    "purpose": "Purpose oru nodila vaarathu. Edhu free-a pannalaam nu thonudhu, edhu energy-a edukkudhu nu gavanichu, indha month muthal-adhai konjam adhigam pannunga.",
    "family": "Oru nimisham full-a defend pannaama kelunga. Pala family tension, 'naan kekkapaduren' nu thonumbodhu thaane kuraiyum.",
    "health": "Ezhundhirikkara neratha fix pannunga, thoonga oru mani munnaadiye light kuraiyunga, adutha 7 naal simple-a vechukkonga.",
    "decide": "Bayam illanaa neenga enna choose pannuveenga nu ezhudhunga. Oru varusham kazhichum mariyaadhai kudukkara option edhu nu paarunga.",
    "today": "Indha naalukku oru mukkiya velaiya mattum choose pannunga, madhiyam munnadi mudichidunga, mathadhu bonus.",
    "general": "Oru deep breath edunga - edhu romba baaramaa irukku: soozhnilai, aalungal, illa theriyaadha vishayam?",
}
GUIDE_TA = {
    "work": "எல்லா இடத்திலும் உங்களை நிரூபிக்க முயல வேண்டாம். இந்த வாரம் முக்கியமான ஒரு இலக்கை மட்டும் தேர்ந்தெடுத்து குழுவிடம் தெளிவாகச் சொல்லுங்கள்.",
    "love": "புகாருக்குப் பின்னால் இருக்கும் உணர்வைப் பேசுங்கள். 'நீ எப்போதும்...' என்பதற்கு முன் 'எனக்கு... என்று தோன்றுகிறது' என்று சொல்லுங்கள்.",
    "money": "வருமானம், செலவு, ஒரு இலக்கு - மூன்றையும் ஒரு பக்கத்தில் எழுதுங்கள்; சந்தேகம் இருந்தால் 48 மணி நேரம் காத்திருங்கள்.",
    "stress": "இரண்டு நிமிடம் மெதுவாக மூச்சை வெளியேற்றுங்கள்; பிறகு ஒரு சிறிய வேலையை மட்டும் செய்யுங்கள். அமைதிக்குப் பிறகுதான் தெளிவு வரும்.",
    "anger": "90 வினாடி எதுவும் செய்யாதீர்கள். 4 எண்ணிக்கை உள்ளிழுத்து, 4 பிடித்து, 6 வெளியேற்றுங்கள். பிறகு கொஞ்சம் நடந்துவிட்டு பேசுங்கள்.",
    "study": "25 நிமிடம் படியுங்கள், 5 நிமிடம் ஓய்வு. போனை வேறு அறையில் வையுங்கள். படித்ததை வாய்விட்டுச் சொல்லிப் பாருங்கள்.",
    "purpose": "நோக்கம் ஒரே நொடியில் வராது. எதைச் சும்மா செய்வீர்கள், எது சோர்வடையச் செய்கிறது என்று கவனித்து, முதலாவதை இந்த மாதம் அதிகம் செய்யுங்கள்.",
    "family": "ஒரு நிமிடம் உங்களை நியாயப்படுத்தாமல் கேளுங்கள். புரிந்துகொள்ளப்படுகிறோம் என்று உணரும்போது குடும்ப பதற்றம் தானாகக் குறையும்.",
    "health": "எழும் நேரத்தை நிலைப்படுத்துங்கள்; தூங்க ஒரு மணி நேரம் முன்பே விளக்குகளை மங்கலாக்குங்கள்; அடுத்த ஏழு நாட்கள் எளிமையாக வையுங்கள்.",
    "decide": "பயம் இல்லாவிட்டால் எதைத் தேர்ந்தெடுப்பீர்கள் என்று எழுதுங்கள். ஒரு வருடம் கழித்தும் உங்களை மதிக்க வைக்கும் தேர்வு எது என்று பாருங்கள்.",
    "today": "இன்றைக்கு ஒரே ஒரு முக்கிய வேலையைத் தேர்ந்தெடுத்து மதியத்துக்குள் முடியுங்கள்; மற்றவை போனஸ்.",
    "general": "ஒரு ஆழ்ந்த மூச்சு எடுங்கள் - சூழ்நிலை, மனிதர்கள், தெரியாத எதிர்காலம் - இதில் எது அதிகம் அழுத்துகிறது?",
}
DEEPER = {
    "en": ["Try this tonight: write three lines - what I feel, what I need, one small step. Then close the page.",
           "Drink a glass of water, stand barefoot for two minutes, and breathe out longer than you breathe in.",
           "Send one honest, kind message to someone you trust. You don't have to carry this alone.",
           "Hum 'Om' slowly for one minute. The vibration settles the nervous system faster than thinking.",
           "Take a 20-minute screen-free walk and let the answers come to you instead of chasing them."],
    "tg": ["Indha raathiri idhai try pannunga: moonu line ezhudhunga - enna feel pannuren, enna venum, oru sinna step. Appuram page-a moodidunga.",
           "Oru glass thanni kudinga, rendu nimisham paadham nilathula nillunga, ulla vida veliya moochu neramaa vidunga.",
           "Nambikkai irukkura oru aal-kitta honest-aana, anbaana message anuppunga. Ellathaiyum neenga mattum sumakka venaam.",
           "Oru nimisham mella 'Om' nu hum pannunga. Yosikkiradhai vida vibration nenjai vegama amaidhiyaakkum.",
           "20 nimisham phone illaama nadanga. Pathil-a thedaama, athuvaa varattum."],
    "ta": ["இன்று இரவு முயற்சி செய்யுங்கள்: மூன்று வரி எழுதுங்கள் - நான் என்ன உணர்கிறேன், என்ன தேவை, ஒரு சிறிய படி. பிறகு பக்கத்தை மூடுங்கள்.",
           "ஒரு குவளை தண்ணீர் குடியுங்கள், இரண்டு நிமிடம் வெறுங்காலில் நில்லுங்கள், உள்ளிழுப்பதைவிட நீளமாக வெளியேற்றுங்கள்.",
           "நம்பிக்கையான ஒருவருக்கு உண்மையான, அன்பான செய்தி அனுப்புங்கள். எல்லாவற்றையும் நீங்கள் மட்டும் சுமக்க வேண்டாம்.",
           "ஒரு நிமிடம் மெதுவாக 'ஓம்' என்று ஒலியுங்கள். சிந்திப்பதை விட அந்த அதிர்வு மனதை வேகமாக அமைதியாக்கும்.",
           "20 நிமிடம் போன் இல்லாமல் நடந்து வாருங்கள்; பதில்களைத் துரத்தாமல் அவை வரட்டும்."],
}
OPEN_EN = {
    "sad": ["I'm right here with you. 🙏 Let it out, there's no hurry.", "I can feel the weight in your words. Breathe, you're not alone in this."],
    "angry": ["I hear that fire. 🔥 It's okay to feel it, let's cool it together.", "Something touched a nerve. Take one breath with me first."],
    "stress": ["Okay, pause with me for a second. 🌿 You don't have to carry it all at once.", "I feel the pressure around you. Let's slow it down together."],
    "greet": ["Hey {n} 🙏 I'm here. How's your heart today?", "Welcome back {n} ✨ I was just sensing your energy. How are you feeling?"],
    "neutral": ["I hear you, {n}. 🙏", "Thank you for trusting me with this, {n}."],
    "thanks": ["Always, {n} 💛 I'm right here whenever you need me."],
}
OPEN_TG = {
    "sad": ["Naan unga kooda irukken. 🙏 Mella sollunga, avasaram illa."],
    "angry": ["Kovam puriyuthu. 🔥 Konjam moochu edunga, naama saanthama pannalaam."],
    "stress": ["Konjam pause pannunga. 🌿 Ellaam oru nimishathula sumakka venaam."],
    "greet": ["Hey {n} 🙏 Naan inga dhaan irukken. Indha naal eppadi irukku?"],
    "neutral": ["Puriyuthu {n}. 🙏"],
    "thanks": ["Eppavum {n} 💛 Thevai-na naan inga dhaan."],
}
OPEN_TA = {
    "sad": ["நான் உங்களுடன்தான் இருக்கிறேன். 🙏 மெதுவாகச் சொல்லுங்கள்."],
    "angry": ["அந்தக் கோபம் புரிகிறது. 🔥 ஒரு மூச்சு எடுங்கள், சேர்ந்து அமைதியாக்குவோம்."],
    "stress": ["ஒரு நொடி நிறுத்துங்கள். 🌿 எல்லாவற்றையும் ஒரே நேரத்தில் சுமக்க வேண்டாம்."],
    "greet": ["வணக்கம் {n} 🙏 நான் இங்கேதான் இருக்கிறேன். இன்று எப்படி இருக்கிறீர்கள்?"],
    "neutral": ["புரிகிறது {n}. 🙏"],
    "thanks": ["எப்போதும் {n} 💛 தேவைப்படும்போது நான் இங்கே இருக்கிறேன்."],
}
CLOSE_EN = ["Tell me more: what part of this keeps replaying in your mind?",
            "Want me to look at what the next few months are showing for this?",
            "What's one small thing you could do today? I'll hold the rest with you."]
CLOSE_TG = ["Innum sollunga: edhu ungal manasula thirumba thirumba odudhu?", "Adutha konja maadhangal idhukku enna kaattudhu nu paakkava?"]
CLOSE_TA = ["இன்னும் சொல்லுங்கள்: எது உங்கள் மனதில் திரும்பத் திரும்ப ஓடுகிறது?", "அடுத்த சில மாதங்கள் இதற்கு என்ன காட்டுகின்றன என்று பார்க்கவா?"]

TANG = {"enna", "epdi", "eppadi", "romba", "seri", "naan", "nan", "ennaku", "enakku", "pannu", "panna", "iruku", "irukku",
        "illa", "vela", "velai", "kadhal", "kaadhal", "paisa", "panam", "kadan", "kashtam", "mudiyala", "venum", "thambi",
        "anna", "sollu", "kavalai", "bayam", "thookam", "kuzhappam", "kalyanam", "pannalama", "irukken", "nalla", "ippo",
        "kovam", "kobam", "kopam", "padippu", "inniku", "indru", "amma", "appa", "vanakkam", "nandri"}
LATIN = [
    ("es", {"hola", "estoy", "quiero", "necesito", "gracias", "trabajo", "dinero", "amor", "ayuda", "cómo", "pero"}),
    ("fr", {"bonjour", "salut", "merci", "travail", "argent", "amour", "pourquoi", "comment", "suis", "mais", "besoin"}),
    ("de", {"hallo", "danke", "arbeit", "geld", "liebe", "warum", "ich", "bin", "aber", "nicht", "bitte"}),
    ("it", {"ciao", "grazie", "lavoro", "soldi", "amore", "perché", "sono", "voglio", "aiuto", "bisogno"}),
    ("pt", {"olá", "obrigado", "trabalho", "dinheiro", "estou", "quero", "você", "não", "preciso"}),
    ("id", {"saya", "aku", "terima", "kasih", "kerja", "uang", "cinta", "bagaimana", "tidak", "tolong"}),
]
TOPICS = {
    "anger": {"angry", "anger", "furious", "rage", "irritated", "irritating", "temper", "kovam", "kobam", "kopam"},
    "stress": {"stress", "stressed", "anxious", "anxiety", "tired", "overwhelmed", "worried", "tension", "kavalai", "bayam", "lonely", "sad", "depressed"},
    "love": {"love", "relationship", "partner", "crush", "marriage", "kadhal", "kaadhal", "kalyanam", "breakup", "girlfriend", "boyfriend", "realtionship", "realationship"},
    "work": {"work", "job", "career", "boss", "office", "promotion", "vela", "velai", "business"},
    "money": {"money", "salary", "debt", "invest", "paisa", "panam", "kadan", "loan", "income"},
    "study": {"study", "exam", "education", "college", "school", "marks", "padippu", "padi", "course", "learn", "degree"},
    "purpose": {"purpose", "meaning", "direction", "destiny", "aim", "calling", "mission", "lost"},
    "family": {"family", "mother", "father", "amma", "appa", "parents", "wife", "husband", "kids", "child", "brother", "sister"},
    "health": {"health", "sleep", "thookam", "body", "energy", "diet", "tiredness"},
    "decide": {"decide", "decision", "confused", "choice", "should", "kuzhappam", "pannalama"},
    "today": {"today", "indru", "inniku", "tonight", "tomorrow", "daily"},
}
TA_KEYS = {"கோபம்": "anger", "கவலை": "stress", "அழுத்தம்": "stress", "பயம்": "stress", "காதல்": "love",
           "திருமணம்": "love", "வேலை": "work", "பணம்": "money", "படிப்பு": "study", "கல்வி": "study",
           "நோக்கம்": "purpose", "குடும்பம்": "family", "தூக்கம்": "health", "உடல்": "health",
           "முடிவு": "decide", "இன்று": "today"}
MOOD_WORDS = {"sad": {"sad", "depressed", "cry", "crying", "lonely", "hurt", "empty", "hopeless", "alone", "kashtam", "azhugai"},
              "angry": TOPICS["anger"],
              "stress": {"stress", "stressed", "anxious", "anxiety", "tired", "overwhelmed", "worried", "tension", "bayam", "kavalai"}}
GREET = {"hi", "hii", "hey", "heyy", "hello", "hlo", "yo", "vanakkam", "hola"}
THANKS = {"thanks", "thank", "thx", "nandri", "ty"}
FOLLOW = {"why", "how", "then", "what", "next", "more", "ok", "okay", "and", "so", "tell", "explain", "yes", "sure"}
OTHER = {
    "ko": ("저는 당신의 신성한 나침반입니다. ", "깊게 숨을 쉬어 보세요. 오늘은 작고 진심 어린 한 걸음만 내딛으세요. 명료함은 그 뒤에 따라옵니다.", "이 중 어떤 부분이 가장 무겁게 느껴지나요?"),
    "th": ("ฉันคือเข็มทิศศักดิ์สิทธิ์ของคุณ ", "หายใจเข้าลึก ๆ แล้วก้าวเล็ก ๆ ที่จริงใจเพียงหนึ่งก้าวในวันนี้ ความชัดเจนจะตามมาเอง", "ส่วนไหนที่รู้สึกหนักที่สุดสำหรับคุณ?"),
    "es": ("Soy tu Brújula Divina. ", "Respira profundo y da hoy un único paso pequeño y sincero; la claridad llegará después.", "¿Qué parte te pesa más ahora mismo?"),
    "ja": ("私はあなたの神聖なコンパスです。", "深呼吸をして、今日は小さく誠実な一歩だけ踏み出してください。明確さはそのあとについてきます。", "どの部分がいちばん重く感じますか?"),
    "zh": ("我是你的神圣罗盘。", "深呼吸一下，今天只迈出一小步真诚的脚步，清晰感会随之而来。", "其中哪一部分让你感觉最沉重？"),
    "ar": ("أنا بوصلتك الإلهية. ", "خذ نفسًا عميقًا وخطُ اليوم خطوة صغيرة وصادقة واحدة؛ فالوضوح يأتي بعدها.", "أي جزء يبدو الأثقل عليك الآن؟"),
    "hi": ("मैं आपका दिव्य कम्पास हूँ। ", "एक गहरी साँस लीजिए और आज बस एक छोटा, सच्चा कदम उठाइए; स्पष्टता उसके बाद आती है।", "इनमें से कौन-सा हिस्सा सबसे भारी लग रहा है?"),
    "ru": ("Я ваш Божественный Компас. ", "Сделайте глубокий вдох и сделайте сегодня один маленький искренний шаг — ясность придёт следом.", "Какая часть сейчас кажется самой тяжёлой?"),
    "fr": ("Je suis votre Boussole Divine. ", "Respirez profondément et faites aujourd'hui un seul petit pas sincère ; la clarté viendra ensuite.", "Quelle partie vous semble la plus lourde en ce moment ?"),
    "de": ("Ich bin dein Göttlicher Kompass. ", "Atme tief durch und geh heute nur einen kleinen, ehrlichen Schritt; die Klarheit folgt danach.", "Welcher Teil fühlt sich gerade am schwersten an?"),
    "it": ("Sono la tua Bussola Divina. ", "Fai un respiro profondo e compi oggi un solo piccolo passo sincero; la chiarezza arriverà dopo.", "Quale parte ti pesa di più in questo momento?"),
    "pt": ("Sou sua Bússola Divina. ", "Respire fundo e dê hoje um único passo pequeno e sincero; a clareza vem depois.", "Qual parte parece mais pesada agora?"),
    "id": ("Saya Kompas Ilahi Anda. ", "Tarik napas dalam dan ambil satu langkah kecil yang tulus hari ini; kejelasan akan menyusul.", "Bagian mana yang terasa paling berat sekarang?"),
}


def seed_of(*parts):
    return int(hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).hexdigest(), 16)


def profile_seed(p):
    return seed_of(p["name"].strip().lower(), p["dob"], p["pob"].strip().lower(), p["tob"])


def daily_seed(p):
    return seed_of(profile_seed(p), date.today().isoformat())


def pick(pool, s, shift):
    return pool[(s >> shift) % len(pool)]


def detect_lang(msg):
    cjk = False
    for ch in msg:
        o = ord(ch)
        if 0x0B80 <= o <= 0x0BFF:
            return "ta"
        if 0xAC00 <= o <= 0xD7AF:
            return "ko"
        if 0x0E00 <= o <= 0x0E7F:
            return "th"
        if 0x3040 <= o <= 0x30FF:
            return "ja"
        if 0x0600 <= o <= 0x06FF:
            return "ar"
        if 0x0900 <= o <= 0x097F:
            return "hi"
        if 0x0400 <= o <= 0x04FF:
            return "ru"
        if 0x4E00 <= o <= 0x9FFF:
            cjk = True
    if cjk:
        return "zh"
    words = set(re.findall(r"[^\W\d_]+", msg.lower()))
    if words & TANG:
        return "tanglish"
    for code, vocab in LATIN:
        if words & vocab:
            return code
    return "en"


def detect_topic(msg):
    for key, k in TA_KEYS.items():
        if key in msg:
            return k
    words = set(re.findall(r"[a-zA-Z]+", msg.lower()))
    for k, kw in TOPICS.items():
        if words & kw:
            return k
    return None


MEM_FILE = "aurasync_user_memory.json"
YES_W = {"yes", "yeah", "yep", "yup", "sure", "ok", "okay", "please", "haan", "aama"}
NO_W = {"no", "nope", "nah", "later"}
TOPIC_LABEL = {"anger": "anger", "stress": "stress", "love": "relationships", "work": "work", "money": "money",
               "study": "your studies", "purpose": "your purpose", "family": "family", "health": "health and rest",
               "decide": "a big decision", "today": "your day", "general": "what is on your mind"}
LEARN = (
    (re.compile(r"\bmy (wife|husband|partner|mother|mom|father|dad|son|daughter|brother|sister|boss|friend|kids|parents)\b"),
     lambda m: "mentioned your " + m.group(1)),
    (re.compile(r"\bi (?:have|got|am having) an? (exam|interview|presentation|deadline|surgery|trip|wedding|meeting)\b"),
     lambda m: "have " + ("an " if m.group(1)[0] in "aeiou" else "a ") + m.group(1) + " coming up"),
    (re.compile(r"\b(?:can'?t|cannot|couldn'?t|unable to) sleep\b|\binsomnia\b|\bsleepless\b"),
     lambda m: "have been struggling to sleep"),
    (re.compile(r"\bi (?:love|like|enjoy) ([a-z ]{3,24})"), lambda m: "enjoy " + m.group(1).strip()),
    (re.compile(r"\bi work (?:as|at|in) ([a-z ]{3,24})"), lambda m: "work " + m.group(1).strip()),
)


def _mem_path():
    try:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), MEM_FILE)
    except NameError:
        return MEM_FILE


def mem_get():
    """What the companion has learned about this user."""
    ss = st.session_state
    key = ((ss.profile or {}).get("name") or "guest").strip().lower()
    cur = ss.get("user_mem")
    if cur is None or cur.get("_key") != key:
        saved = {}
        try:
            with open(_mem_path(), encoding="utf-8") as f:
                saved = json.load(f).get(key, {})
        except Exception:
            saved = {}
        cur = {"_key": key, "msgs": 0, "sessions": 0, "topics": {}, "moods": {}, "hours": {}, "notes": [],
               "last_topic": None}
        cur.update({k: v for k, v in saved.items() if k in cur and k != "_key"})
        cur["sessions"] += 1
        ss.user_mem = cur
    return cur


def mem_save():
    ss = st.session_state
    mem = ss.get("user_mem")
    if not mem:
        return
    try:
        try:
            with open(_mem_path(), encoding="utf-8") as f:
                allm = json.load(f)
        except Exception:
            allm = {}
        allm[mem["_key"]] = {k: v for k, v in mem.items() if k != "_key"}
        with open(_mem_path(), "w", encoding="utf-8") as f:
            json.dump(allm, f, ensure_ascii=False)
    except Exception:
        pass


def learn_from(msg, topic, mood):
    mem = mem_get()
    low = msg.lower()
    mem["msgs"] += 1
    if topic:
        mem["topics"][topic] = mem["topics"].get(topic, 0) + 1
        mem["last_topic"] = topic
    mem["moods"][mood] = mem["moods"].get(mood, 0) + 1
    h = str(datetime.now().hour)
    mem["hours"][h] = mem["hours"].get(h, 0) + 1
    for rx, fn in LEARN:
        m = rx.search(low)
        if m:
            note = fn(m)
            if note not in mem["notes"]:
                mem["notes"] = (mem["notes"] + [note])[-12:]
    mem_save()


def memory_line(mem, topic, prior, first):
    ss = st.session_state
    parts, h = [], datetime.now().hour
    if topic and topic != "general" and prior.get(topic, 0) >= 1:
        parts.append(TOPIC_LABEL.get(topic, topic).capitalize() + " keeps coming up for you, " + first +
                     ". That tells me it really matters.")
    elif mem["notes"] and len(ss.chat) % 3 == 0:
        parts.append("I remember that you " + mem["notes"][-1] + ".")
    if ss.get("last_state") == "stress":
        parts.append("Your wearable also shows some tension in your body right now.")
    if (h >= 23 or h < 5) and topic in ("health", "stress", "general", None):
        parts.append("It's late, so rest may help more than answers tonight.")
    return " ".join(parts)


def run_offer(kind):
    ss = st.session_state
    if kind == "sleep":
        apply_mode(WIND_MODE)
        ss.fade_tok += 1
    else:
        apply_mode("Deep Meditation" if "Deep Meditation" in ss.modes else ss.active_mode)


# ----------------------------------------------------------------------------
# NVIDIA NIM LLM integration
# ----------------------------------------------------------------------------
NVIDIA_SYSTEM_PROMPT = """You are AuraSync Divine Compass, a wise, empathetic, and grounded AI companion. You are philosophically insightful, psychologically supportive, and always concise (2 to 4 sentences max per message). You understand the user's astrological grounding and environmental state, and you adapt your tone to match their conversational language (English, Tamil, Tanglish, Korean, Thai, etc.).
"""


def divine_reply(msg, p):
    """Live LLM integration via NVIDIA NIM, falling back to the rule-based engine."""
    ss = st.session_state
    # Attempt LLM
    if OpenAI is not None:
        try:
            api_key = st.secrets.get("NVIDIA_API_KEY", "")
            if api_key:
                client = OpenAI(
                    base_url="https://integrate.api.nvidia.com/v1",
                    api_key=api_key,
                )
                f = chart_facts(p)
                room = ss.presence["room"]
                mode = eff_mode()
                bio = ss.get("last_state", "unknown")
                mem = mem_get()
                mem_str = f"Last topic: {mem.get('last_topic')}. Notes: {mem.get('notes')}."
                sys_msg = (
                    STAIA_PROMPT
                    + f"\n\nUser: {p['name']} (born {p['dob']} in {p['pob']})."
                    + f"\nEnvironment: Room: {room}, Mode: {mode}, Biometrics: {bio}."
                    + "\n" + astro_text(p)
                    + f"\nMemory: {mem_str}"
                )
                messages = [{"role": "system", "content": sys_msg}]
                # Add recent chat history
                for m in ss.chat[-5:]:
                    messages.append({"role": m["role"], "content": m["content"]})
                messages.append({"role": "user", "content": msg})
                response = client.chat.completions.create(
                    model="meta/llama-3.1-70b-instruct",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=420,
                    timeout=18,
                )
                reply = response.choices[0].message.content.strip()
                if reply:
                    # Update memory based on message
                    topic = detect_topic(msg)
                    mood = "neutral"
                    for k, vocab in MOOD_WORDS.items():
                        if set(re.findall(r"[^\W\d_]+", msg.lower())) & vocab:
                            mood = k
                            break
                    learn_from(msg, topic, mood)
                    return [reply]
        except Exception as e:
            log(f"⚠ NVIDIA NIM fallback: {type(e).__name__}")
    # Fallback to rule-based
    return divine_reply_rule_based(msg, p)


def divine_reply_rule_based(msg, p):
    """A natural, memory-aware reply: one or two short messages, no stock 'I hear you' filler."""
    ss = st.session_state
    try:
        _chart_reply = staia_rule_reply(msg, p)
        if _chart_reply:
            return _chart_reply
    except Exception as e:
        log("⚠ Chart answer skipped: " + type(e).__name__)
    lg = detect_lang(msg)
    first = p["name"].split()[0].title() if p["name"].split() else p["name"]
    words = set(re.findall(r"[^\W\d_]+", msg.lower()))
    seed = seed_of(msg, len(ss.chat), daily_seed(p))
    topic = detect_topic(msg)
    mood = "neutral"
    for k, vocab in MOOD_WORDS.items():
        if words & vocab:
            mood = k
            break
    for key, k in (("கோபம்", "angry"), ("வருத்தம்", "sad"), ("அழுகை", "sad"), ("தனிமை", "sad"), ("கவலை", "stress"), ("பயம்", "stress")):
        if key in msg:
            mood = k
            break
    mem = mem_get()
    prior = dict(mem["topics"])
    returning = mem["msgs"] > 0 or mem["sessions"] > 1
    offer = ss.get("pending_offer")
    if offer and len(words) <= 4:
        if words & YES_W:
            ss.pending_offer = None
            run_offer(offer)
            learn_from(msg, None, "neutral")
            return [t("chat_done_" + offer)]
        if words & NO_W:
            ss.pending_offer = None
            learn_from(msg, None, "neutral")
            return [t("chat_declined")]
    learn_from(msg, topic, mood)
    if lg in OTHER:
        o = OTHER[lg]
        return [o[0] + first + ". 🌟 " + o[1], o[2]]
    code = {"ta": "ta", "tanglish": "tg"}.get(lg, "en")
    opens = {"en": OPEN_EN, "tg": OPEN_TG, "ta": OPEN_TA}[code]
    guides = {"en": GUIDE_EN, "tg": GUIDE_TG, "ta": GUIDE_TA}[code]
    closes = {"en": CLOSE_EN, "tg": CLOSE_TG, "ta": CLOSE_TA}[code]
    if words & THANKS and len(words) <= 4:
        return [pick(opens["thanks"], seed, 3).replace("{n}", first)]
    f = chart_facts(p)
    if words & GREET and len(words) <= 3:
        day = {"en": DAYQ, "ta": TA_DAY, "tg": DAYQ}[code][f["day"]]
        if code == "en" and returning:
            label = TOPIC_LABEL.get(mem.get("last_topic") or "general", "what is on your mind")
            line = "Welcome back, " + first + " ✨ " + (("Last time we talked about " + label + ". How has that been sitting with you?")
                                                          if mem.get("last_topic") else "How are you feeling today?")
        else:
            line = pick(opens["greet"], seed, 3).replace("{n}", first)
        return [line + " " + day]
    follow = topic is None and len(words) <= 5 and (words & FOLLOW) and ss.get("last_topic")
    if follow:
        k = ss.get("deeper", 0)
        ss.deeper = k + 1
        tips = DEEPER[code]
        return [tips[k % len(tips)] + " " + closes[(k + 1) % len(closes)]]
    if topic is None:
        topic = "stress" if mood in ("sad", "stress") else ("anger" if mood == "angry" else "general")
    ss.last_topic, ss.deeper = topic, 0
    ins = {"en": insight_en, "tg": insight_tg, "ta": insight_ta}[code](topic, f)
    lead = pick(opens[mood], seed, 3).replace("{n}", first) if mood in opens and mood != "neutral" else ""
    first_bubble = (lead + " " + ins).strip()
    tail = []
    if code == "en":
        ml = memory_line(mem, topic, prior, first)
        if ml:
            tail.append(ml)
    tail.append(guides[topic])
    h = datetime.now().hour
    gap = len(ss.chat) - ss.get("last_offer_at", -99)
    strained = bool(re.search(r"can'?t sleep|insomnia|sleepless|stress|anxious|overwhelm|exhaust|burn(?:ed|t)? out|tired", msg.lower()))
    if code == "en" and gap >= 8 and (strained or mood in ("stress", "sad", "angry") or topic in ("stress", "health")):
        kind = "sleep" if (h >= 21 or h < 5) else "calm"
        ss.pending_offer = kind
        ss.last_offer_at = len(ss.chat)
        tail.append(t("chat_offer_" + kind))
    else:
        tail.append(pick(closes, seed, 9))
    return [first_bubble, " ".join(tail)]


def welcome_parts(p):
    f = chart_facts(p)
    first = p["name"].split()[0].title() if p["name"].split() else p["name"]
    if st.session_state.get("lang", "").startswith("Tamil"):
        return ["வணக்கம் " + first + " 🙏", "உங்கள் அதிர்வை நான் உணர்கிறேன். " + TA_DAY[f["day"]],
                "மனதில் இருப்பதைச் சொல்லுங்கள் - வேலை, காதல், பணம், குடும்பம், மன அழுத்தம், எதுவாக இருந்தாலும். நான் இங்கே இருக்கிறேன்."]
    mem = mem_get()
    if mem["msgs"] > 0 and mem.get("last_topic"):
        second = ("Good to see you again. Last time we talked about " +
                  TOPIC_LABEL.get(mem["last_topic"], "what was on your mind") + ". How has it been since?")
    else:
        second = "I've been sensing your energy since you arrived. " + DAYQ[f["day"]]
    return ["Hey " + first + " 🙏 " + second, "What's on your mind today? I'm right here."]


def md_inline(s):
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"\*(.+?)\*", r"<i>\1</i>", s)
    return s.replace("\n", "<br>")


def bubble(role, text, ts):
    cls = "me" if role == "user" else "dv"
    tick = " ✓✓" if role == "user" else ""
    body = md_inline(text)
    if role == "user":
        body = '<span translate="no">' + body + "</span>"
    return ('<div class="crow ' + cls + '"><div class="bub ' + cls + '">' + body +
            '<span class="ts">' + ts + tick + "</span></div></div>")


TYPING = '<div class="crow dv"><div class="bub dv typing"><span></span><span></span><span></span></div></div>'


def add_msg(role, text):
    st.session_state.chat.append({"role": role, "content": text, "ts": datetime.now().strftime("%H:%M")})


# ----------------------------------------------------------------------------
# Page 3 - Inner Voice & Guide
# ----------------------------------------------------------------------------
ARCH = [
    ("The Steady Builder", "you create security through patience and consistency",
     "you can cling to routines after they stop serving you", "protect long blocks of calm and build slowly"),
    ("The Intuitive Connector", "you read emotional undercurrents faster than most people",
     "you can absorb other people's moods as your own", "set gentle boundaries before you offer support"),
    ("The Visionary Strategist", "you see patterns and possibilities early",
     "you can drift into overthinking before acting", "turn each big idea into one small visible step"),
    ("The Quiet Achiever", "you work with depth and very little ego",
     "you may hide your needs until you feel depleted", "state your needs early and plainly"),
    ("The Spirited Explorer", "you bring energy, curiosity and fresh starts",
     "you can scatter your effort across too many fronts", "choose one priority and finish it"),
    ("The Grounded Healer", "you bring warmth and steadiness to those around you",
     "you can postpone your own recovery", "schedule your rest like an important meeting"),
]
ARCH_TA = [
    ("நிலைத்த உருவாக்குநர்", "நீங்கள் பொறுமையும் நிலைத்தன்மையும் கொண்டு பாதுகாப்பை உருவாக்குகிறீர்கள்",
     "பழைய வழக்கங்கள் தேவையற்றதாகிவிட்டாலும் அவற்றை விடாமல் பற்றிக்கொள்ளலாம்", "அமைதியான நீண்ட நேரங்களைப் பாதுகாத்து மெதுவாக உருவாக்குங்கள்"),
    ("உணர்வுபூர்வ இணைப்பாளர்", "மற்றவர்களை விட வேகமாக உணர்வு அலைகளைப் படிக்கிறீர்கள்",
     "மற்றவர்களின் மனநிலையை உங்களுடையதாகவே உள்வாங்கிக்கொள்ளலாம்", "ஆதரவு வழங்கும் முன் மென்மையான எல்லைகளை வகுத்துக்கொள்ளுங்கள்"),
    ("தொலைநோக்கு மூலோபாயவாதி", "மாதிரிகள் மற்றும் சாத்தியங்களை முன்கூட்டியே பார்க்கிறீர்கள்",
     "செயல்படும் முன் அதிகமாகச் சிந்திக்கத் தொடங்கலாம்", "ஒவ்வொரு பெரிய கருத்தையும் ஒரு சிறிய புலப்படும் படியாக மாற்றுங்கள்"),
    ("அமைதியான சாதனையாளர்", "ஆழமாகவும் மிகக் குறைந்த அகங்காரத்துடனும் வேலை செய்கிறீர்கள்",
     "சோர்வடையும் வரை உங்கள் தேவைகளை மறைக்கலாம்", "உங்கள் தேவைகளை முன்கூட்டியே தெளிவாகச் சொல்லுங்கள்"),
    ("ஆர்வமுள்ள ஆய்வாளர்", "ஆற்றல், ஆர்வம் மற்றும் புதிய தொடக்கங்களைக் கொண்டு வருகிறீர்கள்",
     "பல முனைகளில் உங்கள் முயற்சியைச் சிதறடிக்கலாம்", "ஒரு முன்னுரிமையைத் தேர்ந்தெடுத்து அதை முடிக்கவும்"),
    ("அடித்தளமான குணப்படுத்துபவர்", "உங்களைச் சுற்றியுள்ளவர்களுக்கு அரவணைப்பையும் நிலைத்தன்மையையும் தருகிறீர்கள்",
     "உங்கள் சொந்த குணமடைவதைத் தள்ளிப்போடலாம்", "ஒரு முக்கியமான கூட்டத்தைப் போல உங்கள் ஓய்வைத் திட்டமிடுங்கள்"),
]
REFLECT = [
    "What would I do today if I trusted myself fully?",
    "Which commitment am I keeping only out of guilt?",
    "What is one thing I am avoiding that would feel lighter once done?",
    "Whose approval am I chasing, and what do I actually want?",
    "What does my body need right now that my mind keeps overriding?",
]
REFLECT_TA = [
    "என்னை முழுமையாக நம்பினால் இன்று நான் என்ன செய்வேன்?",
    "குற்ற உணர்வின் காரணமாக மட்டுமே நான் எந்த உறுதிமொழியைக் கடைப்பிடிக்கிறேன்?",
    "முடிந்ததும் இலகுவாக உணரக்கூடிய, நான் தவிர்க்கும் ஒரு விஷயம் என்ன?",
    "யாருடைய அங்கீகாரத்தை நான் துரத்துகிறேன், நான் உண்மையில் என்ன விரும்புகிறேன்?",
    "என் மனம் தொடர்ந்து புறக்கணிக்கும், என் உடலுக்கு இப்போது என்ன தேவை?",
]
DOS = [
    "{n}, spend the first 20 minutes of your day on your single most important task before opening any messages.",
    "Name what you feel in one honest sentence before you react to a difficult message.",
    "Take a 10-minute walk without your phone to reset your thinking.",
    "Have the one kind but honest conversation you have been postponing.",
    "Write down three things within your control today and act on the first one right away.",
    "Between meetings, drink water, stretch, and breathe slowly for two minutes.",
]
DOS_TA = [
    "{n}, எந்தச் செய்திகளையும் திறப்பதற்கு முன் உங்கள் நாளின் முதல் 20 நிமிடங்களை உங்களுக்கு மிக முக்கியமான ஒரு வேலைக்கு செலவிடுங்கள்.",
    "கடினமான ஒரு செய்திக்கு எதிர்வினையாற்றும் முன், நீங்கள் உணர்வதை ஒரு நேர்மையான வாக்கியத்தில் சொல்லுங்கள்.",
    "உங்கள் சிந்தனையை புதுப்பிக்க 10 நிமிடம் ஃபோன் இல்லாமல் நடந்து வாருங்கள்.",
    "நீங்கள் தள்ளிப்போட்டுக்கொண்டிருக்கும் அந்த ஒரு கனிவான ஆனால் நேர்மையான உரையாடலை நடத்துங்கள்.",
    "இன்று உங்கள் கட்டுப்பாட்டில் உள்ள மூன்று விஷயங்களை எழுதி, முதலாவதை உடனே செயல்படுத்துங்கள்.",
    "கூட்டங்களுக்கு இடையே, தண்ணீர் குடித்து, உடலை நீட்டி, இரண்டு நிமிடம் மெதுவாக மூச்சு விடுங்கள்.",
]
DONTS = [
    "Don't make a big commitment while you are tired or emotionally charged.",
    "Don't compare your behind-the-scenes with someone else's highlight reel.",
    "Don't say yes automatically; pause for one full breath before agreeing.",
    "Don't scroll news or social media in the first hour after waking.",
    "Don't rehearse worst-case scenarios; ask what is actually known right now.",
    "Don't carry other people's mood as your personal responsibility.",
]
DONTS_TA = [
    "சோர்வாக அல்லது உணர்ச்சிவசப்பட்ட நிலையில் பெரிய உறுதிமொழி எதுவும் அளிக்க வேண்டாம்.",
    "உங்கள் மேடைக்குப் பின்னால் நடப்பதை மற்றவர்களின் சிறந்த தருணங்களுடன் ஒப்பிட வேண்டாம்.",
    "தானாகவே 'சரி' என்று சொல்ல வேண்டாம்; ஒப்புக்கொள்ளும் முன் ஒரு முழு மூச்சு எடுத்து நிறுத்துங்கள்.",
    "எழுந்த பிறகு முதல் ஒரு மணி நேரத்தில் செய்திகள் அல்லது சமூக வலைதளங்களை உருட்ட வேண்டாம்.",
    "மோசமான சூழ்நிலைகளை மனதில் பயிற்சி செய்ய வேண்டாம்; இப்போது உண்மையில் என்ன தெரிகிறது என்று கேளுங்கள்.",
    "மற்றவர்களின் மனநிலையை உங்கள் தனிப்பட்ட பொறுப்பாக சுமக்க வேண்டாம்.",
]
CAUTIONS = [
    "Energy may dip in the afternoon, so schedule demanding work early and keep the evening light.",
    "Watch for impatience in conversations about money or deadlines; slow your tone before your words.",
    "Small misunderstandings can grow today, so confirm important details in writing.",
    "You may be tempted to over-give; protect one hour purely for yourself.",
    "Decision fatigue is likely; simplify your choices and postpone non-urgent ones.",
    "Sensitivity to criticism may run higher than usual; separate feedback from your self-worth.",
]
CAUTIONS_TA = [
    "மதியம் ஆற்றல் குறையலாம், எனவே கடினமான வேலைகளை முன்கூட்டியே திட்டமிட்டு மாலையை இலகுவாக வைத்திருங்கள்.",
    "பணம் அல்லது காலக்கெடு பற்றிய உரையாடல்களில் பொறுமையின்மையைக் கவனியுங்கள்; வார்த்தைகளுக்கு முன் உங்கள் தொனியை மெதுவாக்குங்கள்.",
    "சிறிய தவறான புரிதல்கள் இன்று வளரலாம், எனவே முக்கியமான விவரங்களை எழுத்துப்பூர்வமாக உறுதிப்படுத்துங்கள்.",
    "அதிகமாகக் கொடுக்கும் ஆசை வரலாம்; உங்களுக்காக மட்டுமே ஒரு மணி நேரத்தைப் பாதுகாத்துக் கொள்ளுங்கள்.",
    "முடிவெடுக்கும் சோர்வு ஏற்படலாம்; உங்கள் தேர்வுகளை எளிமையாக்கி அவசரமற்றவற்றைத் தள்ளிப்போடுங்கள்.",
    "விமர்சனத்திற்கான உணர்திறன் வழக்கத்தை விட அதிகமாக இருக்கலாம்; கருத்துக்களை உங்கள் சுயமரியாதையிலிருந்து பிரிக்கவும்.",
]

def deep_text(kind, p):
    ps, ds = profile_seed(p), daily_seed(p)
    lang = st.session_state.get("lang", "English")
    is_ta = lang.startswith("Tamil")
    
    if is_ta:
        a = ARCH_TA[ps % len(ARCH_TA)]
        ref = pick(REFLECT_TA, ds, 11)
        season = "இந்த காலகட்டத்தில் " + TA_SEASON.get(chart_facts(p)["lord"], "மாற்றம்")
        day_q = TA_DAY.get(chart_facts(p)["day"], "")
        sati = "உங்கள் உணர்வு அலைகளின் மீது கனமான, சோதனையான காலகட்டம் கடந்து செல்கிறது, எனவே உங்களிடம் கருணையுடன் இருங்கள். " if chart_facts(p)["sati"] else ""
        
        if kind == "do":
            return ("**இது உங்களுக்கு ஏன் வேலை செய்கிறது, " + p["name"] + ".** உங்கள் மனோபாவம் *" + a[0] + "* போன்றது: " + a[1] +
                    ". நீங்கள் இப்போது " + season + ", எனவே இன்றைய செயல் அந்த பலத்தை ஒரு உறுதியான விஷயத்தில் செலுத்துகிறது. "
                    "நீங்கள் " + p["pob"] + " இல் வாழ்க்கையைத் தொடங்கியதால், உங்கள் நாளைத் தொடங்கும் விதத்தை இன்னும் வடிவமைக்கும் ஆரம்ப பழக்கங்களைக் கவனித்து, உதவும் பழக்கங்களை மட்டும் வைத்திருங்கள். "
                    "உங்களுக்கான நம்பகமான வளர்ச்சிப் பாதை: " + a[3] + ".\n\n**சிந்திக்க:** " + ref)
        if kind == "dont":
            return ("**இது எதைப் பாதுகாக்கிறது, " + p["name"] + ".** *" + a[0] + "* இன் இருண்ட பக்கம் என்னவென்றால் " + a[2] +
                    ". இன்றைய 'செய்யாதே' என்பது உங்கள் ஆற்றல் வெளியேறும் முன் அதைப் பாதுகாக்கும் ஒரு எல்லை. " + day_q +
                    " உங்களுக்கு அந்த உந்துதல் ஏற்படும் போதெல்லாம் பத்து வினாடிகள் நிறுத்திப் பயிற்சி செய்யுங்கள், அந்த உந்துதல் உண்மையில் எதைக் கேட்கிறது என்பதைக் கவனியுங்கள்.\n\n**சிந்திக்க:** " + ref)
        return ("**இந்த எச்சரிக்கைக்குப் பின்னால் உள்ள முறை, " + p["name"] + ".** *" + a[0] + "* போன்ற மக்கள் பெரும்பாலும் கணிக்கக்கூடிய மன அழுத்த வளைவை எதிர்கொள்கிறார்கள்: " + a[2] +
                ". " + sati +
                "இன்றைய எச்சரிக்கை ஒரு முன்னெச்சரிக்கை, கணிப்பு அல்ல. ஒரு சிறிய மீட்பு நடவடிக்கையை முன்கூட்டியே திட்டமிடுங்கள் (ஒரு சிறு நடை, ஒரு கிளாஸ் தண்ணீர், அமைதியான ஒருவருடன் பேசுவது) சரிவு ஒரு சுழலாக மாறாமல் இருக்க. காலப்போக்கில், "
                + a[3] + " கற்றுக்கொள்வதன் மூலம் நீங்கள் வளர்கிறீர்கள்.\n\n**சிந்திக்க:** " + ref)
    
    # English fallback
    a = ARCH[ps % len(ARCH)]
    ref = pick(REFLECT, ds, 11)
    f = chart_facts(p)
    name, pob = p["name"], p["pob"]
    season = "a season of " + SEASON[f["lord"]]
    if kind == "do":
        return ("**Why this works for you, " + name + ".** Your temperament pattern resembles *" + a[0] + "*: " + a[1] +
                ". Right now you are in " + season + ", so today's action channels that strength into something concrete. "
                "Because you began life in " + pob + ", notice which early habits still shape how you start your day, and keep "
                "only the ones that help. A reliable growth path for you is to " + a[3] + ".\n\n**Reflect:** " + ref)
    if kind == "dont":
        return ("**What this protects, " + name + ".** The shadow side of *" + a[0] + "* is that " + a[2] +
                ". Today's 'don't' is a boundary that guards your energy before it leaks. " + DAYQ[f["day"]] +
                " Practice a pause of ten seconds whenever you feel the urge, and notice what the urge was really asking for.\n\n**Reflect:** " + ref)
    return ("**The pattern behind this caution, " + name + ".** People shaped like *" + a[0] + "* often face a predictable stress "
            "curve: " + a[2] + ". " + ("A heavy, testing phase is passing over your emotional tides, so be gentle with yourself. "
                                       if f["sati"] else "") +
            "Today's caution is an early warning, not a prediction. Pre-plan one small recovery action "
            "(a short walk, a glass of water, a call with someone calm) so the dip never turns into a spiral. Over time, "
            "you grow by learning to " + a[3] + ".\n\n**Reflect:** " + ref)


def profile_form():
    ss = st.session_state
    p = ss.profile or {}
    st.subheader(t("setup"))
    with st.form("profile_form"):
        name = st.text_input(t("name"), value=p.get("name", ""))
        dob0 = p.get("dob", date(1995, 1, 1))
        st.markdown("**" + t("dob") + "**")
        d1, d2, d3 = st.columns(3)
        dday = d1.selectbox(t("day"), list(range(1, 32)), index=dob0.day - 1)
        dmon = d2.selectbox(t("month"), list(range(1, 13)), index=dob0.month - 1, format_func=lambda m: MONTHS[m - 1])
        dyear = d3.selectbox(t("year"), list(range(1940, 2041)), index=min(max(dob0.year, 1940), 2040) - 1940)
        pob = st.text_input(t("pob"), value=p.get("pob", ""))
        st.markdown("**" + t("tob") + "**")
        c1, c2, c3 = st.columns(3)
        hr = c1.selectbox(t("hour"), list(range(1, 13)), index=p.get("h", 6) - 1)
        mn = c2.selectbox(t("minute"), list(range(0, 60)), index=p.get("m", 0), format_func=lambda x: str(x).zfill(2))
        ap = c3.selectbox("AM / PM", ["AM", "PM"], index=0 if p.get("ap", "AM") == "AM" else 1)
        ok = st.form_submit_button(t("save"))
    dob = date(dyear, dmon, min(dday, calendar.monthrange(dyear, dmon)[1]))
    if ok:
        if not name.strip() or not pob.strip():
            st.warning(t("need_fields"))
        else:
            tob = str(hr).zfill(2) + ":" + str(mn).zfill(2) + " " + ap
            ss.profile = {"name": name.strip(), "dob": dob, "pob": pob.strip(), "tob": tob, "h": hr, "m": mn, "ap": ap}
            ss.editing = False
            ss.chat = []
            ss.chimed = False
            ss.last_topic = None
            st.rerun()


def card(title, text):
    st.markdown('<div class="card"><h4>' + html.escape(title) + "</h4><p>" + html.escape(text) + "</p></div>",
                unsafe_allow_html=True)


def page_inner_voice():
    ss = st.session_state
    st.header(t("p3"))
    if ss.profile is None or ss.editing:
        profile_form()
        if ss.profile is None:
            st.info(t("need_profile"))
        return

    p = ss.profile
    n = html.escape(p["name"])
    wc, bc = st.columns([4, 1])
    wc.markdown('<div class="banner"><b>' + t("welcome", n=n) + "</b></div>", unsafe_allow_html=True)
    if bc.button(t("edit")):
        ss.editing = True
        st.rerun()
    if ss.cfg["notif"]:
        st.markdown('<div class="banner">' + t("nudge", n=n) + "</div>", unsafe_allow_html=True)
        if ss.cfg["chime"]:
            ring = not ss.chimed
            ss.chimed = True
            chime_component(ring)

    st.subheader(t("plan"))
    ds = daily_seed(p)
    is_ta = st.session_state.get("lang", "").startswith("Tamil")
    
    if is_ta:
        items = [("do", pick(DOS_TA, ds, 3)), ("dont", pick(DONTS_TA, ds, 17)), ("caution", pick(CAUTIONS_TA, ds, 29))]
    else:
        items = [("do", pick(DOS, ds, 3)), ("dont", pick(DONTS, ds, 17)), ("caution", pick(CAUTIONS, ds, 29))]
        
    cols = st.columns(3)
    for col, (kind, text) in zip(cols, items):
        with col:
            card(t(kind), text.replace("{n}", p["name"]))
            with st.expander(t("deep")):
                st.markdown(deep_text(kind, p))

    st.divider()
    st.subheader("🧭 " + t("chat"))
    render_compass_chips()
    q = st.chat_input(t("chat_ph")) or ss.pop("compass_q", None)
    if not ss.chat:
        for part in welcome_parts(p):
            add_msg("assistant", part)
    st.markdown('<div class="chathead"><span class="dot"></span>' + t("chat") + " <small>· " + t("online") +
                "</small></div>", unsafe_allow_html=True)
    st.markdown('<div class="chatbox">' + "".join(bubble(m["role"], m["content"], m.get("ts", "")) for m in ss.chat) +
                "</div>", unsafe_allow_html=True)
    if q:
        tail = st.container()
        add_msg("user", q)
        tail.markdown(bubble("user", q, ss.chat[-1]["ts"]), unsafe_allow_html=True)
        parts = divine_reply(q, p)
        for part in parts:
            slot = tail.empty()
            slot.markdown(TYPING, unsafe_allow_html=True)
            time.sleep(min(2.2, 0.6 + len(part) * 0.012))
            add_msg("assistant", part)
            slot.markdown(bubble("assistant", part, ss.chat[-1]["ts"]), unsafe_allow_html=True)
# ----------------------------------------------------------------------------
# Pages 4 & 5
# ----------------------------------------------------------------------------
def remove_device(uid):
    ss = st.session_state
    ss.fleet = [d for d in ss.fleet if d["uid"] != uid]
    for sp in ss.spaces.values():
        if uid in sp["devices"]:
            sp["devices"].remove(uid)
        if sp.get("preset"):
            sp["preset"].pop(str(uid), None)
    ss.holds.pop(uid, None)
    ss.room_rev = ss.get("room_rev", 0) + 1


def add_fleet_device():
    ss = st.session_state
    cid, room = ss.get("fl_add_cid"), ss.get("fl_add_room")
    if cid not in CAT or room not in ss.spaces:
        return
    base = (ss.get("fl_add_name") or "").strip()[:40] or CAT[cid][2]
    nd = new_device(cid, unique_name(base), room)
    ss.fleet.append(nd)
    ss.spaces[room]["devices"].append(nd["uid"])
    ss.room_rev = ss.get("room_rev", 0) + 1
    log("➕ " + nd["name"] + " added to " + room)


def page_fleet():
    ss = st.session_state
    pro = ss.ui_mode == "pro"
    st.header(t("p4"))
    st.subheader("🔗 " + t("conn_hub"))
    total = len(ss.fleet)
    ok = sum(1 for d in ss.fleet if d["status"] == "connected")
    h1, h2, h3 = st.columns(3)
    h1.markdown(stat(t("dev_my"), total), unsafe_allow_html=True)
    h2.markdown(stat(t("s_ok"), str(ok) + " / " + str(total)), unsafe_allow_html=True)
    h3.markdown(stat(t("ai_auto"), t("mode_auto").split(" (")[0] if ss.cfg["auto_mode"] else t("mode_manual")),
                unsafe_allow_html=True)
    st.caption(t("dev_hint"))
    if st.button("\u2795 Add a device", key="fl_aw_open", type="primary"):
        open_add_wizard()
    if st.button(t("matter_btn"), key="mt_open"):
        open_matter()
    if pro:
        b1, b2 = st.columns(2)
        if b1.button(t("conn_all"), key="fl_conn_all"):
            connect_all()
        if b2.button(t("sync"), key="fl_sync"):
            apply_mode(ss.active_mode, devs=list(ss.fleet))
            ss.flash = t("synced") + " (" + tr_mode(ss.active_mode) + ")"
            st.rerun()
        with st.expander("➕ " + t("dev_add")):
            with st.form("add_device", clear_on_submit=True):
                a1, a2, a3 = st.columns([3, 2, 2])
                a1.selectbox(t("dev_pick"), list(CAT.keys()), key="fl_add_cid",
                             format_func=lambda k: CAT[k][1] + " " + CAT[k][2] + "  ·  " + CAT[k][3])
                a2.selectbox(t("dev_room"), list(ss.spaces), key="fl_add_room", format_func=tr_room)
                a3.text_input(t("dev_name"), key="fl_add_name", max_chars=40)
                st.form_submit_button(t("dev_btn"), on_click=add_fleet_device)

    st.subheader("🔌 " + t("dev_my") + " (" + str(len(ss.fleet)) + ")")
    badge = {"connected": "🟢 " + t("s_ok"), "offline": "🔴 " + t("s_off"), "not connected": "⚪ " + t("s_no")}
    cols = st.columns(2 if pro else 3)
    for i, dv in enumerate(ss.fleet):
        c = CAT[dv["cid"]]
        uid = dv["uid"]
        with cols[i % len(cols)]:
            with st.container(border=True):
                st.markdown("**" + c[1] + " " + html.escape(dv["name"]) + "**  \n" + html.escape(tr_room(dv["room"])) + " · " +
                            badge.get(dv["status"], dv["status"]))
                if not pro:
                    k = "fl_zpw_" + str(uid) + "_" + str(dv.get("rev", 0))
                    st.toggle(t("power_lbl"), value=bool(dv["on"]), key=k, on_change=cb_power, args=(uid, k))
                    continue
                device_editor(dv, "fl")
                with st.expander(t("adv_conn")):
                    rooms = list(ss.spaces)
                    rk = "fl_room_" + str(uid) + "_" + str(ss.get("room_rev", 0))
                    st.selectbox(t("dev_room"), rooms, index=rooms.index(dv["room"]) if dv["room"] in rooms else 0,
                                 key=rk, on_change=cb_dev_room, args=(uid, rk), format_func=tr_room)
                    if "Matter" in dv["proto"]:
                        st.caption("🟢 Matter · " + t("s_ok"))
                    elif dv["proto"] == "Home Assistant API":
                        st.caption("🏠 Home Assistant · " + str(dv["addr"]))
                    else:
                        protos = PROTOS_BULB if dv["cid"] == "bulb" else PROTOS
                        pk = "fl_proto_" + str(uid)
                        st.selectbox(t("proto"), protos, index=protos.index(dv["proto"]) if dv["proto"] in protos else 0,
                                     key=pk, on_change=cb_proto, args=(uid, pk))
                        if dv["proto"] != "Simulation":
                            ak, tk = "fl_addr_" + str(uid), "fl_tok_" + str(uid)
                            st.text_input(t("addr"), value=dv["addr"], key=ak, on_change=cb_dev_field,
                                          args=(uid, ak, "addr"))
                            st.text_input("Token", value=dv["token"], key=tk, type="password", on_change=cb_dev_field,
                                          args=(uid, tk, "token"))
                        st.button(t("conn_btn"), key="cn_" + str(uid), on_click=connect_device, args=(dv,))
                if dv["last"]:
                    st.caption(dv["last"])
                st.button("🗑", key="rm_" + str(uid), on_click=remove_device, args=(uid,))

    if pro:
        st.subheader("📜 " + t("ai_log"))
        for e in ss.log[:12]:
            st.markdown('<div class="logl">' + e["t"] + "  " + html.escape(e["x"]) + "</div>", unsafe_allow_html=True)
        rows = [{"Device": CAT[d["cid"]][1] + " " + d["name"], "Room": tr_room(d["room"]), "Status": "ON" if d["on"] else "OFF",
                 "Level": (str(d["lvl"]) + UNIT.get(d["cid"], "%")) if CAT[d["cid"]][4] else "-",
                 "Link": d["proto"] + " / " + d["status"]} for d in ss.fleet]
        st.subheader("📋 " + t("summary"))
        html_table(rows)


def cb_ha_unlink():
    ss = st.session_state
    ss.cfg.pop("ha", None)                       # the saved address and token leave the account record on the next save
    for d in ss.get("fleet") or []:
        if d.get("proto") == "Home Assistant API":
            d["status"], d["last"] = "not connected", "Home Assistant was unlinked"
    ss.flash = "Home Assistant unlinked. Your Home Assistant devices stay listed; link it again to use them."


def cb_ha_test():
    found, msg = ha_discover()
    st.session_state["ha_test"] = ("bad", msg) if msg else ("ok", "Connected. Home Assistant shows " + str(len(found)) + " devices AuraSync can control.")


def render_ha_link_card():
    ss = st.session_state
    ha = ha_cfg()
    st.markdown("**\U0001F3E0 Home Assistant**")
    if not ha:
        st.caption("Not linked yet. Tap Add a device, choose a device type, then Home Assistant (finds my devices).")
        if st.button("\u2795 Add a device", key="ha_card_add"):
            open_add_wizard()
        return
    st.caption("Linked to your AuraSync account (" + str(ss.get("auth_email") or "this session") + ") at " + ha["url"] +
               ". Alexa and Google Home devices that you share into Home Assistant appear in its device list.")
    b1, b2 = st.columns(2)
    b1.button("Test connection", key="ha_test_btn", on_click=cb_ha_test)
    b2.button("Unlink Home Assistant", key="ha_unlink_btn", on_click=cb_ha_unlink)
    res = ss.get("ha_test")
    if res:
        (st.success if res[0] == "ok" else st.warning)(res[1])


def page_system():
    ss, cfg = st.session_state, st.session_state.cfg
    st.header(t("p5"))
    cfg["api_url"] = st.text_input(t("api"), value=cfg["api_url"])
    cfg["api_token"] = st.text_input(t("api_token"), value=cfg.get("api_token", ""), type="password", key="api_token_w")
    render_wearables_hub()
    render_wearable()
    render_ha_link_card()
    c1, c2, c3, c4 = st.columns(4)
    cfg["thr"] = c1.slider(t("thr"), 85, 150, int(cfg["thr"]))
    cfg["rel"] = c2.slider(t("rel"), 55, 95, int(cfg["rel"]))
    cfg["rest"] = c3.slider(t("rest"), 40, 80, int(cfg["rest"]))
    cfg["poll"] = c4.slider(t("poll"), 2, 15, int(cfg["poll"]))
    cfg["notif"] = st.toggle(t("notif"), value=cfg["notif"])
    cfg["chime"] = st.toggle(t("chime"), value=cfg["chime"])
    st.toggle(t("geo_auto_toggle"), value=bool(cfg.get("geo_auto", True)), key="geo_auto_sys",
              on_change=cb_geo_auto, args=("geo_auto_sys",))
    b1, b2 = st.columns(2)
    if b1.button(t("test")):
        try:
            r = requests.get(cfg["api_url"], timeout=2)
            st.success("HTTP " + str(r.status_code))
        except Exception as e:
            st.error(type(e).__name__)
    if b2.button(t("reset")):
        lang = ss.get("lang", "English")
        for k in list(ss.keys()):
            if k not in ("lang", "nav", "theme_choice"):
                del ss[k]
        ss["lang"] = lang
        st.rerun()


# ----------------------------------------------------------------------------
# Cloud automation
#   1. ?mode=...&token=... link webhook (Siri / Google / any browser) -> applies the mood, soundtrack and cloud triggers
#   2. Cloud IoT dispatcher (Voice Monkey for Alexa, or any https webhook: IFTTT, Home Assistant Cloud, ...)
#   3. "Voice Automation Links" panel that generates ready-to-copy shortcut links
#   4. Cross-platform in-app microphone (Web Speech API)
# Nothing here touches the audio engine, so the lock-screen Media Session keeps playing untouched.
#
# Secrets (.streamlit/secrets.toml, or the Secrets box on Streamlit Cloud). All optional except AURASYNC_TOKEN:
#   AURASYNC_TOKEN       = "long-random-string"            # protects ?mode= links and the links panel
#   APP_URL              = "https://your-app.streamlit.app"
#   VOICEMONKEY_TOKEN    = "..."                            # Alexa via Voice Monkey (device ids: aurasync-reading, ...)
#   VOICEMONKEY_API      = "https://api-v2.voicemonkey.io/trigger"
#   IOT_WEBHOOK_URL      = "https://example.com/hook/aurasync_{mode}"   # one URL for every mode ({mode} is replaced)
#   IOT_WEBHOOK_METHOD   = "GET"                            # or "POST" (JSON body: mode, room, source)
#   [IOT_WEBHOOKS]                                          # per-mode URL (string or list) overrides the template
#   reading = "https://..."
#   [VOICEMONKEY_MONKEYS]                                   # per-mode Voice Monkey device ids
#   reading = "my-reading-monkey"
# ----------------------------------------------------------------------------
AUTO_MODES = (
    # id, icon, spoken-word pattern (English plus common Tamil spellings), how it is applied, target
    ("home", "🏠", r"\b(?:i'?m|i am) home\b|\bback home\b|\barrived\b|\bhome mode\b|வீட்டுக்கு வந்தேன்", "voice", "home"),
    ("away", "🚗", r"\bleaving\b|\bgoing out\b|\bheading out\b|\baway\b|\bbye\b|வெளியே போகிறேன்", "voice", "away"),
    ("reading", "📖", r"\bread(?:ing)?\b|\bbooks?\b|ரீடிங்|வாசிப்பு|படிப்பு|पढ़", "mode", "Reading"),
    ("zen", "🌿", r"\bzen\b|\bgarden\b|ஜென்|ज़ेन|젠", "mode", "Zen Garden"),
    ("meditation", "🧘", r"\bmeditat\w*|\bdhyan\w*|தியான|ध्यान", "mode", "Deep Meditation"),
    ("focus", "💼", r"\bfocus\w*|\bstudy\b|\bconcentrat\w*|\bwork(?:ing)?\b|ஃபோகஸ்|ஃபோக்கஸ்|கவனம்", "voice", "work"),
    ("movie", "🎬", r"\bmovies?\b|\bcinema\b|\bfilm\b|சினிமா|திரைப்பட", "voice", "movie"),
    ("relax", "🛋️", r"\brelax\w*|\bunwind\b|\bchill\b|\bcalm\b|ரிலாக்ஸ்|ஓய்வு", "voice", "relax"),
    ("energize", "⚡", r"\benerg\w*|\bworkout\b|\bwake ?up\b|உற்சாக", "mode", "Energize"),
    ("sleep", "🌙", r"\bsleep\w*|\bbed ?time\b|\bgood ?night\b|\btired\b|தூங்|உறக்க", "voice", "sleep"),
)
AUTO_IDS = tuple(m[0] for m in AUTO_MODES)
AUTO_VOICE_MODE = {"sleep": WIND_MODE, "work": "Focus", "movie": CINEMA_MODE, "relax": "Relax Evening"}
KIND_TO_ID = {"sleep": "sleep", "work": "focus", "movie": "movie", "relax": "relax", "away": "away", "home": "home"}
IOT_WAIT = 6.0          # seconds the app waits for cloud triggers before carrying on
MIC_BRIDGE_KEY = "aura_voice_bridge"
MIC_PH = "◈7731◈"
SR_LANGS = {"English": "en-US", "Tamil (தமிழ்)": "ta-IN", "Korean (한국어)": "ko-KR", "Thai (Thai)": "th-TH",
            "Spanish (Español)": "es-ES", "Hindi (हिन्दी)": "hi-IN", "Arabic (العربية)": "ar-SA",
            "Japanese (日本語)": "ja-JP", "Chinese (中文)": "zh-CN", "French (Français)": "fr-FR",
            "German (Deutsch)": "de-DE", "Italian (Italiano)": "it-IT", "Portuguese (Português)": "pt-BR",
            "Russian (Русский)": "ru-RU", "Turkish (Türkçe)": "tr-TR", "Dutch (Nederlands)": "nl-NL",
            "Polish (Polski)": "pl-PL", "Swedish (Svenska)": "sv-SE", "Greek (Ελληνικά)": "el-GR",
            "Indonesian (Bahasa Indonesia)": "id-ID", "Vietnamese (Tiếng Việt)": "vi-VN",
            "Malay (Bahasa Melayu)": "ms-MY", "Filipino (Tagalog)": "fil-PH"}


def tt(key, **kw):
    """t() plus live translation for languages without a hand-written string (used for text inside HTML / JS)."""
    out = t(key, **kw)
    eng = T[key][0]
    for k, v in kw.items():
        eng = eng.replace("{" + k + "}", str(v))
    return tr(out) if (out == eng and lang_code()) else out


def _secret(name, default=None):
    """st.secrets first, then an environment variable. Never raises when there is no secrets file."""
    try:
        v = st.secrets.get(name, None)
    except Exception:
        v = None
    if v is None:
        v = os.environ.get(name)
    return default if v is None or v == "" else v


def _as_dict(v):
    if v is None or isinstance(v, (str, bytes)):
        return {}
    try:
        return {str(k): v[k] for k in v}
    except Exception:
        return {}


def _as_list(v):
    if isinstance(v, str):
        return [v] if v.strip() else []
    try:
        return [x for x in v if isinstance(x, str) and x.strip()]
    except TypeError:
        return []


# ---- token check with a per-client lock-out (constant-time compare)
def _client_key():
    try:
        xf = st.context.headers.get("X-Forwarded-For") or ""
        return (xf.split(",")[0].strip() or "?")[:64]
    except Exception:
        return "?"


def check_token(candidate):
    """Returns 'ok', 'bad', 'locked' or 'unset'."""
    secret = _secret("AURASYNC_TOKEN")
    if not secret:
        return "unset"
    key, now = _client_key(), time.time()
    with _REG.lock:
        recent = [x for x in _REG.auth_fail.get(key, []) if now - x < 120]
        if len(_REG.auth_fail) > 500:
            _REG.auth_fail.clear()
        _REG.auth_fail[key] = recent
        if len(recent) >= 6:
            return "locked"
    ok = hmac.compare_digest(str(candidate or "").encode("utf-8"), str(secret).encode("utf-8"))
    if not ok:
        with _REG.lock:
            _REG.auth_fail.setdefault(key, []).append(now)
        return "bad"
    return "ok"


# ---- 1. mode recognition shared by links, microphone and the typed command bar
def parse_auto_mode(text):
    low = re.sub(r"[‘’]", "'", str(text or "")).lower()
    low = re.sub(r"[_\-+]+", " ", low).strip()[:200]
    if not low:
        return None
    if low in AUTO_IDS:
        return low
    for mid, _icon, rx, _kind, _arg in AUTO_MODES:
        if re.search(rx, low):
            return mid
    return None


def run_auto_mode(mid, source="app"):
    """Apply a mood exactly like the Zen buttons do (devices + soundtrack), then fire the cloud triggers."""
    ss = st.session_state
    spec = next((m for m in AUTO_MODES if m[0] == mid), None)
    if not spec:
        return ""
    _id, icon, _rx, kind, arg = spec
    ensure_modes()
    if kind == "voice":
        msg = voice_do(arg)
        shown = AUTO_VOICE_MODE.get(arg)
    else:
        if arg not in ss.modes:
            return ""
        clear_room_override(ss.presence["room"])
        apply_mode(arg)
        msg, shown = icon + " " + tr_mode(arg), arg
    try:
        player_cmd("play")
    except Exception:
        pass
    log("🔗 " + {"link": "Link", "voice": "Voice", "test": "Test"}.get(source, "App") + " → " + mid)
    if shown and not ss.flash:
        ss.flash = icon + " " + tr_mode(shown)
    dispatch_cloud(mid, source)
    return msg


# ---- 2. cloud IoT dispatcher
def iot_targets(mid):
    """[(label, url, method)] for one mode. The URLs hold secrets, so they are never logged or shown unlocked."""
    over = st.session_state.get("iot_over") or {}
    method = str(_secret("IOT_WEBHOOK_METHOD", "GET")).upper()
    method = method if method in ("GET", "POST") else "GET"
    out = []
    explicit = _as_list(_as_dict(_secret("IOT_WEBHOOKS")).get(mid))
    for u in explicit:
        out.append(("Webhook", u.strip(), method))
    tpl = str(over.get("tpl") or _secret("IOT_WEBHOOK_URL", "") or "").strip()
    if tpl and not explicit:
        out.append(("Webhook", tpl.replace("{mode}", urllib.parse.quote(mid, safe="")), method))
    token = str(over.get("vm_token") or _secret("VOICEMONKEY_TOKEN", "") or "").strip()
    if token:
        device = str(_as_dict(_secret("VOICEMONKEY_MONKEYS")).get(mid) or ("aurasync-" + mid))
        api = str(_secret("VOICEMONKEY_API", "https://api-v2.voicemonkey.io/trigger")).strip()
        url = api + ("&" if "?" in api else "?") + urllib.parse.urlencode({"token": token, "device": device})
        out.append(("Voice Monkey", url, "GET"))
    return out


def _safe_url(url):
    """https only, and never a private / loopback / link-local address (the server must not be a way into a network)."""
    try:
        u = urllib.parse.urlsplit(url)
        if u.scheme != "https" or not u.hostname:
            return False
        for info in socket.getaddrinfo(u.hostname, u.port or 443, proto=socket.IPPROTO_TCP):
            ip = ipaddress.ip_address(info[4][0].split("%")[0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
                return False
        return True
    except Exception:
        return False


def _fire_one(label, url, method, payload):
    """One trigger with a short timeout and one retry for network errors / 5xx. Returns (label, ok, info)."""
    if not _safe_url(url):
        return (label, False, "blocked")
    info = "error"
    for _attempt in (1, 2):
        try:
            if method == "POST":
                r = requests.post(url, json=payload, timeout=(3.05, 5), allow_redirects=False,
                                  headers={"User-Agent": "AuraSync/1.0"})
            else:
                r = requests.get(url, timeout=(3.05, 5), allow_redirects=False, headers={"User-Agent": "AuraSync/1.0"})
            if r.status_code < 400:
                return (label, True, "HTTP " + str(r.status_code))
            info = "HTTP " + str(r.status_code)
            if r.status_code < 500:
                break
        except requests.Timeout:
            info = "timeout"
        except Exception as e:                      # the exception text can contain the URL, so only the type is kept
            info = type(e).__name__
    return (label, False, info)


def dispatch_cloud(mid, source="app"):
    """Fire every cloud trigger configured for this mode, in parallel. Safe to call when nothing is configured."""
    ss = st.session_state
    now = time.time()
    last = ss.get("iot_last_fire")
    if source != "test" and last and last[0] == mid and now - last[1] < 2.5:
        return []                                    # double tap / double rerun: send once
    targets = iot_targets(mid)
    if not targets:
        return []
    ss.iot_last_fire = (mid, now)
    payload = {"app": "AuraSync", "mode": mid, "room": ss.presence["room"], "source": source}
    ex = concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(targets)))
    futs = {ex.submit(_fire_one, lbl, url, meth, payload): lbl for lbl, url, meth in targets}
    done, pending = concurrent.futures.wait(futs, timeout=IOT_WAIT)
    ex.shutdown(wait=False, cancel_futures=True)
    results = []
    for f in done:
        try:
            results.append(f.result())
        except Exception as e:
            results.append((futs[f], False, type(e).__name__))
    results += [(futs[f], False, "timeout") for f in pending]
    for lbl, ok, info in results:
        log("☁️ " + lbl + " · " + mid + " → " + ("sent (" + info + ")" if ok else "failed (" + info + ")"))
    sent = sum(1 for r in results if r[1])
    ss.iot_results = [(lbl, ok, info) for lbl, ok, info in results]
    note = t("iot_sent", ok=sent, n=len(results))
    ss.flash = (ss.flash + "  ·  " if ss.flash else "") + note
    return results


# ---- 3. ?mode=...&token=... link webhook
def _qp_pop(*names):
    """Read and remove the given query parameters. Only our own keys are removed (embed options etc. stay)."""
    out = {}
    for n in names:
        try:
            if n in st.query_params:
                out[n] = st.query_params.get(n)
                del st.query_params[n]
        except Exception:
            pass
    return out


def handle_query_params():
    """Apply a ?mode= link once, remove the secret from the address bar, never loop."""
    if not hasattr(st, "query_params"):
        return
    hr_from_url()
    ss = st.session_state
    got = _qp_pop("mode", "token")
    if not got:
        return
    mode_raw = str(got.get("mode") or "").strip()[:60]
    tok = str(got.get("token") or "")[:300]
    if not mode_raw:
        return
    sig = hashlib.sha256((mode_raw + "|" + tok).encode("utf-8")).hexdigest()
    done = ss.get("qp_done") or []
    if sig in done:                                   # a rerun that still saw the old URL
        return
    ss.qp_done = (done + [sig])[-20:]
    state = check_token(tok)
    if state != "ok":
        log("⚠ Link blocked (" + state + ")")
        ss.flash = t({"unset": "auto_no_secret", "locked": "auto_wait"}.get(state, "auto_denied"))
        return
    mid = parse_auto_mode(mode_raw)
    if not mid:
        ss.flash = t("auto_bad_mode")
        return
    ss.flash = ""
    ss.hook_msg = run_auto_mode(mid, "link")


# ---- 4. microphone: Web Speech API in the browser, command handed back to Streamlit through a hidden field
COMPANION_MODES = {"reading room": "reading", "zen mode": "zen", "focus work": "focus", "relax evening": "relax",
                   "energize": "energize"}
STRESS_RX = (r"stress|anxi|tension|overwhelm|worr|panic|exhaust|burn ?out|lonely|sad\b|upset|"
             r"ஸ்ட்ரெஸ்|டென்ஷன்|கவலை|மன அழுத்த|romba stress|stress-?aa|kovam|kavalai")
COMPANION_PROMPT = """You are AuraSync, a calm luxury home-ambience companion who talks with the user out loud, like a warm personal concierge.
Reply with ONLY one JSON object and nothing else, with exactly these two keys:
{"spoken_reply": "...", "mode": "..."}
- spoken_reply: one or two short, warm, empathetic sentences (under 45 words) in the SAME language and style the user spoke (English, Tamil, Tanglish, Korean, Thai ...). It must sound natural when spoken aloud: no emoji, no lists. Say what you are doing for them, for example: "I've got you. Let's dim the living lounge to warm amber and queue up calming lo-fi rain so you can unwind."
- mode: the ambience to switch on. One of exactly: "Reading Room", "Zen Mode", "Focus Work", "Relax Evening", "Energize", or "None" when the user only wants to talk.
Choose the mode that best helps how the person feels or what they want to do (stress or worry: Zen Mode or Relax Evening; reading: Reading Room; working or studying: Focus Work; low energy in the morning: Energize)."""


def nim_companion(text):
    """NVIDIA NIM: {'spoken': str, 'mid': mode id or None}. Returns None when NIM is not configured or fails."""
    key = _secret("NVIDIA_API_KEY")
    if not key or OpenAI is None:
        return None
    ss = st.session_state
    try:
        client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=key)
        prof = ss.get("profile") or {}
        ctx = ("User: " + str(prof.get("name", "friend")) + ". Room: " + ss.presence["room"] + ". Current ambience: " + eff_mode() +
               ". Body state: " + str(ss.get("last_state") or "unknown") + ". Time: " + datetime.now().strftime("%H:%M") + ".")
        resp = client.chat.completions.create(
            model="meta/llama-3.1-70b-instruct",
            messages=[{"role": "system", "content": COMPANION_PROMPT + "\n\n" + ctx},
                      {"role": "user", "content": text}],
            temperature=0.6, max_tokens=200, timeout=12)
        raw = resp.choices[0].message.content or ""
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0))
        spoken = " ".join(str(data.get("spoken_reply", "")).split())[:320]
        if not spoken:
            return None
        mid = COMPANION_MODES.get(str(data.get("mode", "")).strip().lower())
        return {"spoken": spoken, "mid": mid}
    except Exception as e:
        log("⚠ NVIDIA NIM voice fallback: " + type(e).__name__)
        return None


LOCAL_SPOKEN = {
    "reading": "Of course. I'm warming the lights and starting quiet, gentle music so you can read in comfort.",
    "zen": "I've got you. Let's soften the room to a calm green glow and start gentle garden sounds. Breathe out slowly.",
    "meditation": "Let's settle in together. Deep violet light and a slow soundtrack are on. Take your time.",
    "focus": "Focus time. Clear, bright light and quiet lo-fi are on, and I'll keep everything else out of your way.",
    "relax": "Let's slow down together. Warm amber light and soft jazz are on so you can unwind.",
    "energize": "Let's lift the energy. Bright light and upbeat music are coming right up.",
    "sleep": "Time to rest. I'm dimming the lights and starting a soft sleep soundscape. Sleep well.",
    "movie": "Movie time. Curtains closing and cinematic light on. Enjoy.",
    "away": "Away mode on. Your home is going to standby. Have a safe trip.",
    "home": "Welcome home. I'll have everything ready for you.",
}
LOCAL_SPOKEN_TG = {
    "zen": "Naan irukken. Room-a konjam soft-a maathi, calm music podren. Mella moochu vidunga.",
    "relax": "Sari, konjam slow-a pogalaam. Warm light-um soft music-um podren, relax pannunga.",
}


def local_spoken(mid, text):
    try:
        if detect_lang(text) == "tanglish" and mid in LOCAL_SPOKEN_TG:
            return LOCAL_SPOKEN_TG[mid]
    except Exception:
        pass
    return LOCAL_SPOKEN.get(mid, "Done.")


def companion_turn(alts):
    """Two-way voice: NIM (or the local brain) decides the words and the mood, the app applies the mood at once,
    and the browser speaks the words back. Returns the spoken text."""
    ss = st.session_state
    text = alts[0] if alts else ""
    low = text.lower()
    spoken, mid, nim = "", None, nim_companion(text)
    devcmd = any(ai_has(low, w) for g in AI_DEV_WORDS for w in g[2]) and not re.search(r"\bmodes?\b", low)
    local = None if devcmd else next((m for m in (parse_auto_mode(a) for a in alts) if m), None)
    if nim:
        spoken, mid = nim["spoken"], nim["mid"]
        if devcmd:
            mid = None                                   # a device command is carried out as a device command
        elif local and local != mid and (len(text.split()) <= 7 or re.search(AI_MODE_CUE, low)):
            mid, spoken = local, ""                      # the person named the mood: do exactly that one
    else:
        mid = local
        if not mid and not devcmd and re.search(STRESS_RX, low):
            mid = "zen"
    if mid:
        run_auto_mode(mid, "voice")
        spoken = spoken or local_spoken(mid, text)
    else:
        did = []
        try:
            did = aura_do(text)
        except Exception as e:
            log("⚠ Voice command skipped: " + type(e).__name__)
        if did:
            log("🎙️ Voice: “" + text.strip() + "” → " + "; ".join(did))
            spoken = ai_plain(". ".join(did)) if devcmd else (spoken or ai_plain(". ".join(did)))
        elif not nim:
            msg = run_voice(text)
            spoken = t("mic_unknown", x=text[:60]) if msg == t("voice_unknown") else msg
    spoken = spoken or t("mic_unknown", x=text[:60])
    ss.mic_say = {"id": uuid.uuid4().hex[:10], "text": spoken, "lang": tts_lang_for(spoken)}
    log("🎙 Companion: " + (mid or "talk only"))
    if ss.get("profile"):
        add_msg("user", text)
        add_msg("assistant", spoken)
    return spoken


def handle_spoken_basic(alts):
    """Try each recognition alternative: mood first, then the older voice intents (lights off, warmer ...)."""
    for a in alts:
        mid = parse_auto_mode(a)
        if mid:
            return run_auto_mode(mid, "voice") or t("voice_unknown")
    best = alts[0] if alts else ""
    msg = run_voice(best)
    return t("mic_unknown", x=best[:60]) if msg == t("voice_unknown") else msg


def handle_spoken(alts):
    """Two-way companion first; the classic command parser stays as the safety net."""
    try:
        return companion_turn(alts)
    except Exception as e:
        log("⚠ Voice companion error: " + type(e).__name__)
        return handle_spoken_basic(alts)


MIC_PERM_MSG = ("🎙️ Microphone Permission Required\n\n"
                "It looks like microphone permissions are turned off. To use voice commands, please go to your phone's "
                "Settings > Apps > AuraSync > Permissions > Microphone and manually select Allow, then refresh the app.")


def mic_perm_flag(data):
    """The browser side reports a blocked / never-started microphone: remember it so the guidance banner shows. Returns True if it did."""
    ss = st.session_state
    if isinstance(data, dict) and str(data.get("e", "")) in ("denied", "no-start"):
        ss.mic_perm_warn = True
        return True
    return False


def render_mic_perm_warning(kind="main"):
    """Streamlit warning banner with the fix for a blocked microphone (shown next to the mic until it works again or is dismissed)."""
    ss = st.session_state
    if not ss.get("mic_perm_warn"):
        return
    st.warning(MIC_PERM_MSG)
    st.button("Dismiss", key="mic_perm_x_" + kind, on_click=lambda: st.session_state.update(mic_perm_warn=False))


def cb_voice_bridge():
    ss = st.session_state
    raw = str(ss.get(MIC_BRIDGE_KEY) or "")
    ss[MIC_BRIDGE_KEY] = ""
    nonce, alts = "", []
    try:
        data = json.loads(raw)
        if mic_perm_flag(data):
            return
        nonce = str(data.get("n", ""))[:40]
        alts = [str(a).strip()[:200] for a in (data.get("a") or [])[:3] if str(a).strip()]
    except Exception:
        alts = [raw.strip()[:200]] if raw.strip() else []
    if not alts or (nonce and nonce == ss.get("mic_nonce")):
        return
    ss.mic_perm_warn = False                               # a command got through: the microphone works
    ss.mic_nonce = nonce
    ss.mic_last = handle_spoken(alts)


MIC_CTL_VER = 3
MIC_CTL_JS = """
(function () {
  var W = window, VER = __CTLVER__;
  try { if (W.__auraMicCtl && W.__auraMicCtl.v === VER) { return; } } catch (e) {}
  try { if (W.__auraMicCtl && W.__auraMicCtl.abort) { W.__auraMicCtl.abort(); } } catch (e) {}
  var M = (W.__auraMic = W.__auraMic || { state: 'idle', spokenId: '', thinkAt: 0, muted: false });
  var C = { v: VER, rec: null, cfg: null, timer: 0, hard: 0 };
  var LQ = String.fromCharCode(8220), RQ = String.fromCharCode(8221);

  function fail(msg, soft) {
    M.err = msg || ''; M.soft = !!soft;
    if (M.state === 'listening') { M.state = 'idle'; }
  }
  function findInput(cfg) {
    var d = W.document;
    return d.querySelector('.st-key-' + cfg.bridge + ' input') || d.querySelector('input[placeholder="' + cfg.ph + '"]');
  }
  /* write the text into the hidden Streamlit field and commit it like a keystroke (same hand-over the heart-rate bridge uses) */
  function bridge(cfg, payload) {
    var inp = findInput(cfg);
    if (!inp) { return false; }
    var setter = Object.getOwnPropertyDescriptor(W.HTMLInputElement.prototype, 'value').set;
    setter.call(inp, payload);
    inp.dispatchEvent(new W.Event('input', { bubbles: true }));
    ['keydown', 'keypress', 'keyup'].forEach(function (k) {
      inp.dispatchEvent(new W.KeyboardEvent(k, { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true, cancelable: true }));
    });
    setTimeout(function () {
      try { inp.dispatchEvent(new W.FocusEvent('focusout', { bubbles: true })); inp.dispatchEvent(new W.FocusEvent('blur')); } catch (e) {}
    }, 60);
    return true;
  }
  /* tell Streamlit that the microphone is blocked / never started, so it can show the permission guidance banner */
  function report(code) {
    try {
      var cfg = C.cfg, now = Date.now();
      if (!cfg || now - (C.rep || 0) < 4000) { return; }
      C.rep = now;
      bridge(cfg, JSON.stringify({ n: 'e' + now.toString(36) + Math.random().toString(36).slice(2, 5), e: code }));
    } catch (e) {}
  }
  function deliver(cfg, list) {
    var s = cfg.s || {};
    var cut = list.slice(0, 3).map(function (x) { return String(x).slice(0, 160); });
    var payload = JSON.stringify({ n: Date.now().toString(36) + Math.random().toString(36).slice(2, 6), a: cut });
    var tries = 0;
    function attempt() {
      var ok = false;
      try { ok = bridge(cfg, payload); } catch (e) { ok = false; }
      if (ok) {
        M.state = 'thinking'; M.thinkAt = Date.now(); M.shown = LQ + list[0] + RQ; M.err = ''; M.soft = false;
        /* still sitting in the field after a moment = Streamlit did not take it: commit once more (the server ignores a repeat) */
        setTimeout(function () { try { var inp = findInput(cfg); if (inp && inp.value === payload) { bridge(cfg, payload); } } catch (e) {} }, 2200);
      } else if (++tries < 16) {
        setTimeout(attempt, 250);                      /* the hidden field may not be on the page for a moment */
      } else {
        M.state = 'idle'; M.shown = LQ + list[0] + RQ; fail(s.nobridge);
      }
    }
    attempt();
  }
  /* While the microphone is open the page must not fight the phone for the audio channel: on Android the soundtrack's
     "keep alive" player re-grabbed it every time the phone paused it, which silently killed the recognition. */
  function hold() {
    try {
      var a = W.__aura;
      if (a && !C.held && typeof a.revive === 'function') { C.held = a.revive; a.revive = function () {}; }
      clearTimeout(C.rel); C.rel = setTimeout(release, 30000);
    } catch (e) {}
  }
  function release() {
    clearTimeout(C.rel);
    try {
      var a = W.__aura;
      if (C.held) { if (a) { a.revive = C.held; } C.held = null; }
      if (a) { a.revive(); }
    } catch (e) {}
  }
  /* open the microphone once on purpose: it shows the permission prompt if it is still pending and tells us exactly why it fails */
  function preflight(cb) {
    var md = null;
    try { md = W.navigator && W.navigator.mediaDevices; } catch (e) { md = null; }
    if (!md || !md.getUserMedia) { cb(''); return; }
    var done = false, to = setTimeout(function () { if (!done) { done = true; cb(''); } }, 6000);
    md.getUserMedia({ audio: true }).then(function (st) {
      try { st.getTracks().forEach(function (t) { t.stop(); }); } catch (e) {}
      setTimeout(function () { if (!done) { done = true; clearTimeout(to); cb(''); } }, 300);     /* let the phone release the microphone */
    }).catch(function (e) { if (!done) { done = true; clearTimeout(to); cb((e && e.name) || 'error'); } });
  }
  function drop(r) {                                         /* silence an old recognition for good */
    if (!r) { return; }
    r.onstart = r.onaudiostart = r.onspeechstart = r.onresult = r.onerror = r.onend = null;
    try { r.abort(); } catch (e) {}
  }
  function begin(second) {
    var cfg = C.cfg, s = cfg.s || {};
    var Ctor = W.SpeechRecognition || W.webkitSpeechRecognition;
    if (!Ctor) { M.shown = ''; fail(s.unsupported); return; }
    if (W.isSecureContext === false) { M.shown = ''; fail(s.insecure || s.denied); return; }
    var r, fin = '', alts = [], interim = '', err = '', live = false;
    try { drop(W.__auraSRLast); W.__auraSRLast = null; } catch (e) {}          /* a recognition left over from an earlier tap blocks the next one */
    try {
      r = new Ctor();
      r.lang = cfg.tag || 'en-US'; r.interimResults = true; r.continuous = false; r.maxAlternatives = 3;
    } catch (e) { fail((s.error || '') + ' [' + ((e && e.name) || 'start') + ']'); return; }
    C.rec = r; W.__auraSRLast = r; M.err = ''; M.soft = false; M.shown = ''; M.state = 'listening';
    hold();
    function alive() { live = true; clearTimeout(C.boot); if (C.rec === r) { M.state = 'listening'; } }
    r.onstart = alive; r.onaudiostart = alive; r.onspeechstart = alive;
    r.onresult = function (ev) {
      alive();
      interim = '';
      for (var i = ev.resultIndex; i < ev.results.length; i++) {
        var res = ev.results[i];
        if (res.isFinal) {
          alts = [];
          for (var j = 0; j < res.length && j < 3; j++) { alts.push(String(res[j].transcript || '').trim()); }
          fin = alts[0] || fin;
        } else { interim = res[0].transcript; }
      }
      var shown = fin || interim;
      if (shown) { M.shown = LQ + shown + RQ; }
    };
    r.onerror = function (ev) { err = (ev && ev.error) || 'error'; };
    r.onend = function () {
      clearTimeout(C.timer); clearTimeout(C.hard); clearTimeout(C.boot);
      if (C.rec !== r) { return; }
      C.rec = null; W.__auraSRLast = null;
      if (M.state === 'listening') { M.state = 'idle'; }
      release();
      if (err === 'not-allowed' || err === 'service-not-allowed') { M.shown = ''; fail(s.denied); report('denied'); return; }
      if (err === 'language-not-supported') { M.li = (M.li || 0) + 1; M.shown = ''; fail((s.error || '') + ' [language]'); return; }
      if (err === 'network') { M.shown = ''; fail(s.network); return; }
      if (err === 'audio-capture') { M.shown = ''; fail(s.nomic); return; }
      if (err && err !== 'aborted' && err !== 'no-speech') { M.shown = ''; fail((s.error || '') + ' [' + err + ']'); return; }
      var text = fin || String(interim || '').trim();
      if (!text) {
        M.shown = '';
        if (!live && !second) { M.state = 'listening'; M.err = ''; retry(); return; }    /* it ended without ever hearing us: one clean second try */
        fail(s.nospeech, true); return;
      }
      deliver(cfg, alts.length ? alts : [text]);
    };
    function retry() {
      drop(r); if (C.rec === r) { C.rec = null; }
      clearTimeout(C.timer); clearTimeout(C.hard); clearTimeout(C.boot);
      M.state = 'listening'; M.err = ''; M.soft = false;
      preflight(function (why) {
        if (why === 'NotAllowedError' || why === 'SecurityError') { M.state = 'idle'; M.shown = ''; release(); fail(s.denied); report('denied'); return; }
        if (why === 'NotFoundError' || why === 'OverconstrainedError') { M.state = 'idle'; M.shown = ''; release(); fail(s.nomic); return; }
        if (why === 'NotReadableError' || why === 'AbortError') { M.state = 'idle'; M.shown = ''; release(); fail((s.nomic || s.error || '') + ' [busy]'); return; }
        begin(true);
      });
    }
    try { r.start(); } catch (e) {
      C.rec = null; M.state = 'idle'; release();
      if (!second) { retry(); return; }
      fail((s.error || '') + ' [' + ((e && e.name) || 'start') + ']'); return;
    }
    clearTimeout(C.timer); clearTimeout(C.hard); clearTimeout(C.boot);
    C.timer = setTimeout(function () { try { r.stop(); } catch (e) {} }, cfg.maxMs || 9000);
    /* the browser accepted the call but never started listening (a prompt that was dismissed, a busy microphone): open it explicitly and retry once */
    C.boot = setTimeout(function () {
      if (C.rec !== r || live) { return; }
      if (!second) { retry(); return; }
      drop(r); C.rec = null; M.state = 'idle'; M.shown = ''; release(); fail((s.error || '') + ' [no-start]'); report('no-start');
    }, 5000);
    /* safety net: never stay on "listening" forever */
    C.hard = setTimeout(function () {
      if (C.rec === r) { drop(r); C.rec = null; M.state = 'idle'; release(); fail((s.error || '') + ' [timeout]'); }
    }, (cfg.maxMs || 9000) + 8000);
  }
  function toggle(cfg) {
    C.cfg = cfg;
    if (C.rec) { try { C.rec.stop(); } catch (e) {} return; }      /* a second tap ends the sentence now */
    begin(false);
  }
  function stop() { try { if (C.rec) { C.rec.stop(); } } catch (e) {} }
  function abort() { try { if (C.rec) { C.rec.abort(); } } catch (e) {} C.rec = null; clearTimeout(C.timer); clearTimeout(C.hard); clearTimeout(C.boot); try { release(); } catch (e) {} }
  C.toggle = toggle; C.stop = stop; C.abort = abort;
  W.__auraMicCtl = C;
})();
"""


MIC_HTML = """
<style>
  html, body { margin: 0; background: transparent; }
  #w { display: flex; align-items: center; gap: 14px; padding: 10px 14px; box-sizing: border-box; border-radius: 22px;
       border: 1px solid __LINE__; background: __GLASS__; font-family: Inter, Arial, sans-serif; color: __ACC__; }
  #orbw { position: relative; width: 70px; height: 70px; flex: none; }
  #orb { position: absolute; top: 0; left: 0; right: 0; bottom: 0; border-radius: 50%; border: 0; cursor: pointer; padding: 0; overflow: hidden;
         display: flex; align-items: center; justify-content: center; color: __BTN__; -webkit-tap-highlight-color: transparent;
         background: radial-gradient(circle at 35% 30%, rgba(255,255,255,.8), __ACC__ 46%, __ACC__aa 100%);
         box-shadow: 0 0 14px __ACC__66, inset 0 0 12px rgba(0,0,0,.25); }
  #orb svg { width: 26px; height: 26px; fill: currentColor; position: relative; z-index: 2; }
  #orb.off { opacity: .45; }
  #orb.idle { animation: idle 4.5s ease-in-out infinite; }
  @keyframes idle { 0%, 100% { box-shadow: 0 0 12px __ACC__55; } 50% { box-shadow: 0 0 22px __ACC__99; } }
  #orb.listening { animation: pulse 1.15s ease-in-out infinite; }
  @keyframes pulse { 0% { transform: scale(.96); box-shadow: 0 0 0 0 __ACC__aa, 0 0 18px __ACC__; }
                     70% { transform: scale(1.07); box-shadow: 0 0 0 20px __ACC__00, 0 0 30px __ACC__; }
                     100% { transform: scale(.96); box-shadow: 0 0 0 0 __ACC__00, 0 0 18px __ACC__; } }
  #orb.thinking::after { content: ""; position: absolute; top: 0; left: 0; right: 0; bottom: 0; z-index: 1;
         background: linear-gradient(110deg, transparent 25%, rgba(255,255,255,.7) 50%, transparent 75%); background-size: 220% 100%;
         animation: shimmer 1.2s linear infinite; }
  @keyframes shimmer { 0% { background-position: 160% 0; } 100% { background-position: -60% 0; } }
  #orb.speaking { animation: breathe 3.4s ease-in-out infinite; }
  @keyframes breathe { 0%, 100% { transform: scale(1); box-shadow: 0 0 14px __ACC__66; } 50% { transform: scale(1.08); box-shadow: 0 0 36px __ACC__bb; } }
  #wave { display: none; align-items: flex-end; gap: 3px; height: 14px; margin-top: 6px; }
  #wave i { display: block; width: 3px; height: 3px; border-radius: 2px; background: __ACC__; animation: wv .9s ease-in-out infinite; }
  #wave i:nth-child(2) { animation-delay: .12s; } #wave i:nth-child(3) { animation-delay: .24s; }
  #wave i:nth-child(4) { animation-delay: .36s; } #wave i:nth-child(5) { animation-delay: .48s; }
  @keyframes wv { 0%, 100% { height: 3px; } 50% { height: 14px; } }
  #tx { flex: 1; min-width: 0; }
  #t1 { font-size: 14px; font-weight: 600; line-height: 1.25; }
  #t2 { font-size: 12px; color: __SUB__; line-height: 1.35; margin-top: 2px; overflow-wrap: anywhere; }
  #w.err #t1 { color: #ff8a80; }
  .sm { flex: none; border: 1px solid __ACC__; background: transparent; color: __ACC__; border-radius: 12px; padding: 3px 9px; font-size: 11px; cursor: pointer; }
  #bt { display: flex; flex-direction: column; gap: 6px; }
  @media (prefers-reduced-motion: reduce) { #orb, #orb::after, #wave i { animation: none !important; } }
</style>
<div id="w">
  <div id="orbw"><button id="orb" class="idle" type="button" aria-pressed="false" aria-label="Voice">
    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 14a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v5a3 3 0 0 0 3 3zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.92V21h2v-3.08A7 7 0 0 0 19 11h-2z"/></svg>
  </button></div>
  <div id="tx"><div id="t1"></div><div id="t2"></div><div id="wave"><i></i><i></i><i></i><i></i><i></i></div></div>
  <div id="bt"><button id="lg" class="sm" type="button"></button><button id="mt" class="sm" type="button"></button></div>
</div>
<script id="micctl" type="text/plain">__CTL__</script>
<script>
(function () {
  var CFG = __CFG__, S = CFG.s, CTL_VER = __CTLVER__;
  var P = null;
  try { P = window.parent; void P.document.body; } catch (e) { P = null; }
  var MIC = P ? (P.__auraMic = P.__auraMic || {}) : {};
  if (!MIC.state) { MIC.state = 'idle'; }
  MIC.spokenId = MIC.spokenId || ''; MIC.thinkAt = MIC.thinkAt || 0; MIC.shown = MIC.shown || ''; MIC.err = MIC.err || '';
  if (typeof MIC.li !== 'number') { MIC.li = 0; }
  function ctl() { try { return (P && P.__auraMicCtl) ? P.__auraMicCtl : null; } catch (e) { return null; } }
  /* the microphone logic lives in the page itself (not in this small frame), so Streamlit re-drawing the frame cannot cut a recording short */
  if (P && (!ctl() || ctl().v !== CTL_VER)) {
    try {
      var sc = P.document.createElement('script');
      sc.textContent = document.getElementById('micctl').textContent;
      P.document.head.appendChild(sc);
    } catch (e) {}
  }
  var SRs = null;
  try { SRs = (P && (P.SpeechRecognition || P.webkitSpeechRecognition)) || window.SpeechRecognition || window.webkitSpeechRecognition || null; } catch (e) { SRs = null; }
  var canRec = !!SRs;
  var $ = function (id) { return document.getElementById(id); };
  var orb = $('orb'), t1 = $('t1'), t2 = $('t2'), lg = $('lg'), mt = $('mt'), w = $('w'), wave = $('wave');
  var reply = '', noTTS = false, last = '';
  function eng() { try { return (P && P.__aura) || null; } catch (e) { return null; } }
  function fit() { try { window.frameElement.style.height = (w.offsetHeight + 4) + 'px'; } catch (e) {} }
  function tag() { return CFG.langs[MIC.li % CFG.langs.length]; }
  function chip() { lg.textContent = tag().split('-')[0].toUpperCase(); lg.title = tag(); }
  function muteLabel() { mt.textContent = MIC.muted ? '\\uD83D\\uDD07' : '\\uD83D\\uDD0A'; mt.title = MIC.muted ? S.unmute : S.mute; }
  lg.style.display = CFG.langs.length > 1 ? '' : 'none';
  lg.onclick = function (e) { e.stopPropagation(); MIC.li = (MIC.li + 1) % CFG.langs.length; chip(); };
  mt.onclick = function (e) { e.stopPropagation(); MIC.muted = !MIC.muted; if (MIC.muted) { var a = eng(); if (a) { a.stopSpeech(); } } muteLabel(); };
  chip(); muteLabel();

  function paint() {
    var s = MIC.state;
    if (s === 'thinking' && Date.now() - MIC.thinkAt > 25000) { MIC.state = 'idle'; s = 'idle'; }
    orb.className = s + (canRec ? '' : ' off');
    orb.setAttribute('aria-pressed', s === 'listening' ? 'true' : 'false');
    wave.style.display = s === 'thinking' ? 'flex' : 'none';
    var l1 = '', l2 = '', bad = false;
    if (s === 'listening') { l1 = S.listening; l2 = MIC.shown || S.hint; }
    else if (s === 'thinking') { l1 = S.thinking; l2 = MIC.shown; }
    else if (s === 'speaking') { l1 = S.speaking; l2 = reply || MIC.shown; }
    else if (MIC.err) { l1 = MIC.err; l2 = MIC.shown; bad = !MIC.soft; }
    else if (reply) { l1 = noTTS ? S.notts : S.title; l2 = reply; }
    else if (!canRec) { l1 = S.unsupported; bad = true; }
    else { l1 = S.title; l2 = S.hint; }
    var key = l1 + '|' + l2 + '|' + bad;
    if (key !== last) { last = key; t1.textContent = l1; t2.textContent = l2; w.className = bad ? 'err' : ''; fit(); }
  }
  setInterval(paint, 250);

  /* a reply from the companion: show it and speak it (the speech itself lives in the page, so it survives re-renders) */
  if (CFG.say && CFG.say.id) {
    reply = CFG.say.text;
    if (CFG.say.id !== MIC.spokenId) {
      MIC.spokenId = CFG.say.id; MIC.err = ''; MIC.soft = false; MIC.shown = '';
      var a0 = eng();
      if (a0 && a0.canSpeak() && !MIC.muted) { a0.speak(CFG.say.text, CFG.say.lang); }
      else { MIC.state = 'idle'; if (a0 && !a0.canSpeak()) { noTTS = true; } }
    } else if (MIC.state === 'thinking') { MIC.state = 'idle'; }
  }
  paint();

  orb.onclick = function () {
    var a = eng();
    try { if (a) { a.unlock(); a.unlockSpeech(); a.stopSpeech(); } } catch (e) {}        /* this tap also unlocks the soundtrack and the voice */
    if (!canRec) { MIC.err = S.unsupported; MIC.soft = false; paint(); return; }
    var c = ctl();
    if (!c) { MIC.err = S.error; MIC.soft = false; paint(); return; }
    reply = ''; noTTS = false;
    c.toggle({ tag: tag(), bridge: CFG.bridge, ph: CFG.ph, maxMs: CFG.maxMs, s: S });
    paint();
  };
})();
</script>
"""


def tts_lang_for(text):
    """Language tag for the spoken reply: the language of the reply itself, otherwise the app language."""
    m = {"ta": "ta-IN", "tanglish": "en-IN", "ko": "ko-KR", "th": "th-TH", "es": "es-ES", "ja": "ja-JP", "ar": "ar-SA",
         "hi": "hi-IN", "ru": "ru-RU", "zh": "zh-CN", "fr": "fr-FR", "de": "de-DE", "it": "it-IT", "pt": "pt-BR",
         "id": "id-ID"}
    try:
        lg = detect_lang(text)
    except Exception:
        lg = "en"
    if lg in m:
        return m[lg]
    return SR_LANGS.get(st.session_state.get("lang", "English"), "en-US")


def mic_html(bridge=None, ph=None, say_key="mic_say"):
    ss = st.session_state
    lang = ss.get("lang", "English")
    tag = SR_LANGS.get(lang, "en-US")
    langs = [tag] if tag.startswith("en") else [tag, "en-US"]
    keys = ("title", "hint", "listening", "heard", "sent", "denied", "unsupported", "nospeech", "network", "nomic",
            "nobridge", "error", "thinking", "speaking", "notts", "mute", "unmute", "insecure")
    strings = {k: tt("mic_" + k) for k in keys}
    cfg = {"langs": langs, "bridge": bridge or MIC_BRIDGE_KEY, "ph": ph or MIC_PH, "maxMs": 9000, "s": strings,
           "say": ss.get(say_key) or {}}
    blob = json.dumps(cfg, ensure_ascii=False).replace("</", "<\\/")
    page = MIC_HTML.replace("__CFG__", blob).replace("__CTL__", MIC_CTL_JS).replace("__CTLVER__", str(MIC_CTL_VER))
    return themed(page)


def render_voice_mic(kind="main"):
    ss = st.session_state
    if kind == "ai":                                     # the floating Aura AI has its own hidden field and reply
        st.text_input("◈ 7732", key=AI_BRIDGE_KEY, placeholder=AI_PH, label_visibility="collapsed", max_chars=800,
                      on_change=cb_ai_bridge)
        components.html(mic_html(AI_BRIDGE_KEY, AI_PH, "ai_say"), height=96)
        render_mic_perm_warning("ai")
        return
    st.text_input("◈ 7731", key=MIC_BRIDGE_KEY, placeholder=MIC_PH, label_visibility="collapsed", max_chars=800,
                  on_change=cb_voice_bridge)
    components.html(mic_html(), height=96)
    render_mic_perm_warning("main")
    if ss.get("mic_last"):
        st.caption(ss.mic_last)


# ---- 3b. "Voice Automation Links" panel (sidebar, collapsible, locked behind the AuraSync token)
def app_base_url():
    v = _secret("APP_URL")
    if v:
        return str(v).strip().rstrip("/")
    try:
        host = st.context.headers.get("X-Forwarded-Host") or st.context.headers.get("Host") or ""
        if host:
            local = host.startswith(("localhost", "127.", "0.0.0.0")) or host.startswith("192.168.")
            return ("http://" if local else "https://") + host.split(",")[0].strip()
    except Exception:
        pass
    return ""


def app_link(base, mid):
    return base.rstrip("/") + "/?" + urllib.parse.urlencode({"mode": mid, "token": str(_secret("AURASYNC_TOKEN", ""))})


def cb_auto_unlock():
    ss = st.session_state
    state = check_token(ss.get("auto_pw"))
    if state == "ok":
        ss.auto_admin, ss.auto_msg = True, ""
    else:
        ss.auto_msg = t({"unset": "auto_no_secret", "locked": "auto_wait"}.get(state, "auto_bad_token"))


def cb_auto_lock():
    st.session_state.auto_admin = False
    st.session_state.pop("iot_over", None)


def cb_auto_test():
    ss = st.session_state
    mid = ss.get("auto_test_sel") or "reading"
    res = dispatch_cloud(mid, "test")
    ss.flash = ""
    ss.auto_msg = (t("iot_sent", ok=sum(1 for r in res if r[1]), n=len(res))) if res else t("auto_direct_none")


def cb_auto_apply():
    ss = st.session_state
    over = {}
    if (ss.get("auto_tpl_in") or "").strip():
        over["tpl"] = ss.auto_tpl_in.strip()
    if (ss.get("auto_vm_in") or "").strip():
        over["vm_token"] = ss.auto_vm_in.strip()
    ss.iot_over = over
    ss.auto_msg = t("auto_applied")


def cb_auto_clear():
    st.session_state.pop("iot_over", None)
    st.session_state.auto_msg = ""


def render_automation_panel():
    ss = st.session_state
    with st.expander("🔗 " + t("auto_links_title"), expanded=False):
        if not _secret("AURASYNC_TOKEN"):
            st.warning(t("auto_no_secret"))
            return
        if not ss.get("auto_admin"):
            st.caption(t("auto_locked"))
            with st.form("auto_unlock_form", clear_on_submit=True):
                st.text_input(t("auto_token"), type="password", key="auto_pw", max_chars=300)
                st.form_submit_button(t("auto_unlock"), on_click=cb_auto_unlock)
            if ss.get("auto_msg"):
                st.error(ss.auto_msg)
            return
        base = st.text_input(t("auto_base"), value=app_base_url(), key="auto_base_in").strip()
        st.caption(t("auto_why"))
        tab_ios, tab_and, tab_cloud = st.tabs(["🍎 " + tt("auto_ios"), "🤖 " + tt("auto_android"), "☁️ IoT"])
        for tab, helpkey in ((tab_ios, "auto_ios_help"), (tab_and, "auto_android_help")):
            with tab:
                st.caption(t(helpkey))
                if not base:
                    st.info(t("auto_base"))
                    continue
                for mid, icon, _rx, _k, _arg in AUTO_MODES:
                    st.caption(icon + " " + t("auto_say") + ": \u201c" + mid + " mode\u201d")
                    st.code(app_link(base, mid), language=None)
        with tab_cloud:
            st.markdown("**" + t("auto_direct") + "**")
            shown = 0
            for mid, icon, *_rest in AUTO_MODES:
                for lbl, url, meth in iot_targets(mid):
                    if meth == "GET":
                        st.caption(icon + " " + mid + " \u00b7 " + lbl)
                        st.code(url, language=None)
                        shown += 1
            if not shown:
                st.caption(t("auto_direct_none"))
            st.selectbox(t("auto_test_mode"), list(AUTO_IDS), key="auto_test_sel")
            st.button(t("auto_test"), key="auto_test_btn", on_click=cb_auto_test)
            st.markdown("**" + t("auto_iot_title") + "**")
            st.caption(t("auto_iot_hint"))
            st.text_input(t("auto_tpl"), type="password", key="auto_tpl_in", max_chars=600)
            st.text_input(t("auto_vm"), type="password", key="auto_vm_in", max_chars=300)
            c1, c2 = st.columns(2)
            c1.button(t("auto_apply"), key="auto_apply_btn", on_click=cb_auto_apply)
            c2.button(t("auto_clear"), key="auto_clear_btn", on_click=cb_auto_clear)
        if ss.get("auto_msg"):
            st.info(ss.auto_msg)
        st.button(t("auto_lock"), key="auto_lock_btn", on_click=cb_auto_lock)


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
NAV_ORDER = [1, 3, 6, 2, 4, 5]     # Live Dashboard, Inner Voice, Room Settings, Moods, Device Fleet, System Settings


def cb_ui_mode(key):
    ss = st.session_state
    v = ss.get(key)
    if v in ("zen", "pro"):
        ss.ui_mode = v
    ss.ui_rev = ss.get("ui_rev", 0) + 1


def render_topbar():
    ss = st.session_state
    c2 = st.container()
    key = "ui_mode_w_" + str(ss.get("ui_rev", 0))
    with c2:
        seg("Mode", ["zen", "pro"], key, lambda m: t("ui_zen") if m == "zen" else t("ui_pro"), on_change=cb_ui_mode,
            args=(key,), selected=ss.ui_mode, hide_label=True)


# ============================================================================
# Aura AI: floating assistant, command engine, personas, live Zen mind, STAIA-style Divine Compass
# (additive block: it only adds new functions; the existing ones call into it at a few marked places)
# ============================================================================
AI_BRIDGE_KEY = "aura_ai_bridge"
AI_PH = "◈7732◈"
AI_PERSONAS = ("auto", "mentor", "girlfriend", "psychologist", "friend")
AI_PERSONA_LABEL = {"auto": "✨ Auto (Aura decides)", "mentor": "🧭 Mentor", "girlfriend": "💞 Partner",
                    "psychologist": "🧠 Counsellor", "friend": "🤝 Friend"}
SIGN_NAMES = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn",
              "Aquarius", "Pisces"]


def player_cmd(do):
    """Ask the soundtrack player (in the browser) to start or stop. The page runs each command once."""
    st.session_state["pc"] = {"id": uuid.uuid4().hex[:8], "d": do}


def ai_note(text):
    """Remember the last thing Aura AI did on its own (shown on the live card)."""
    st.session_state["ai_last"] = {"t": datetime.now().strftime("%H:%M"), "x": str(text)}


def ai_plain(s):
    """Text for the speaker: no markdown stars and no emoji."""
    s = re.sub(r"\*+", "", str(s))
    s = re.sub("[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u200d]", "", s)
    return " ".join(s.split())


# ---- A. Rooms that carry their own atmosphere (selecting the room applies it: mode, devices, music) ----
ROOM_THEME = {"Reading Room": ("Reading", "reading", {"hz432": 0, "rain": 15, "stream": 20, "noise": 0}),
              "Work Studio": ("Focus", "focus", {"hz432": 0, "rain": 0, "stream": 0, "noise": 25})}
ROOM_THEME_BY_TYPE = {"Reading": "Reading Room", "Workspace": "Work Studio"}


def room_theme(room):
    ss = st.session_state
    if room in ROOM_THEME:
        return ROOM_THEME[room]
    key = ROOM_THEME_BY_TYPE.get((ss.spaces.get(room) or {}).get("type"))
    return ROOM_THEME.get(key) if key else None


def apply_room_theme(room):
    """Choosing a themed room switches its mode, its bulbs / AC / fan / curtains and the music together."""
    ss = st.session_state
    th = room_theme(room)
    if not th or th[0] not in ss.modes:
        return ""
    mode, pill, layers = th
    devs = space_devs(room)
    for d in devs:
        ss.holds.pop(d["uid"], None)                     # an explicit choice beats an old manual hold
    clear_room_override(ss.presence["room"])
    apply_mode(mode, devs=devs)                          # sets the active mode (so the player follows) and the room's devices
    set_layers(layers)
    ss.pill_on = pill
    player_cmd("play")
    msg = "📖 " if mode == "Reading" else "💼 "
    ss.flash = msg + tr_room(room) + " · " + tr_mode(mode)
    log(msg + tr_room(room) + " selected → " + mode + " mode, devices and music")
    return ss.flash


# ---- B. Commands in plain words: lights, AC, fan, curtains, music, rooms, moods ----
AI_ROOM_WORDS = (
    ("Reading Room", ("reading room", "library", "study room")),
    ("Master Suite", ("bedroom", "bed room", "master suite", "master bedroom", "my room")),
    ("Living Lounge", ("living room", "living", "lounge", "hall", "drawing room")),
    ("En-Suite Bath", ("bathroom", "bath", "washroom", "restroom")),
    ("Work Studio", ("work studio", "work room", "workroom", "office", "study", "studio")),
    ("Kitchen", ("kitchen",)),
    ("Dining Area", ("dining area", "dining room", "dining")),
)
AI_DEV_WORDS = (
    ("lights", "💡", ("light", "lights", "bulb", "bulbs", "lamp", "lamps", "lighting"), LIGHT_CIDS),
    ("AC", "❄️", ("ac", "a/c", "air conditioner", "air conditioning", "aircon", "air-conditioner"), ("ac",)),
    ("fan", "🌀", ("fan", "fans"), ("fan",)),
    ("curtains", "🪟", ("curtain", "curtains", "blind", "blinds", "drapes"), ("curtain",)),
    ("TV", "📺", ("tv", "television", "projector"), ("tv", "projector")),
    ("air purifier", "🍃", ("purifier", "air purifier"), ("purifier",)),
    ("diffuser", "🌸", ("diffuser", "scent", "aroma"), ("diffuser", "scent")),
    ("speaker", "🔊", ("speaker", "speakers"), ("speaker", "spatial", "soundpad", "focusaudio")),
    ("water heater", "🚿", ("geyser", "water heater", "heater"), ("geyser", "heater")),
    ("air cooler", "🧊", ("air cooler", "desert cooler", "evaporative cooler"), ("cooler",)),
    ("coffee maker", "☕", ("coffee maker", "coffee machine", "coffee brewer", "coffee"), ("coffee",)),
    ("kettle", "🫖", ("kettle",), ("kettle",)),
    ("mattress warmer", "🛏", ("mattress", "mattress warmer", "bed warmer"), ("mattress",)),
    ("towel warmer", "♨", ("towel warmer",), ("towel",)),
    ("plug", "🔌", ("plug", "smart plug", "socket"), ("plug",)),
)
AI_COLORS = {"warm": "#FFB347", "white": "#FFFFFF", "red": "#FF3B30", "blue": "#2F6BFF", "green": "#34C759",
             "purple": "#9B59FF", "violet": "#9B59FF", "pink": "#FF6FB5", "orange": "#FF8A1E", "yellow": "#FFE066",
             "cool": "#CFE8FF"}
AI_STEP = {"lights": 20, "AC": 2, "fan": 1, "curtains": 25, "speaker": 15}
AI_MODE_CUE = (r"\b(?:mode|activate|switch to|change to|set to|turn to|go to|put on|play|start|begin|enable)\b|"
               r"\b(?:i'?m|i am) home\b|\bback home\b|\bleaving\b|\bgoing out\b|\bheading out\b|\bgood ?night\b|"
               r"\bbed ?time\b|\bmovie time\b|\bstarting work\b")
AI_MUSIC_WORD = r"\b(?:music|song|songs|player|playlist|soundscape|sounds?|audio|tunes?)\b"


def ai_has(text, word):
    return bool(re.search(r"(?<!\w)" + re.escape(word) + r"(?!\w)", text))


def ai_norm(x):
    return re.sub(r"[^a-z0-9]+", "", str(x).lower())


def ai_room_from(low):
    ss = st.session_state
    ln = ai_norm(low)
    best = None
    for room in ss.spaces:                               # a room called by its full name (custom rooms included) wins
        rn = ai_norm(room)
        if len(rn) >= 5 and rn in ln and (best is None or len(rn) > len(ai_norm(best))):
            best = room
    if best:
        return best
    for room, words in AI_ROOM_WORDS:
        if room in ss.spaces and any(ai_has(low, w) for w in words):
            return room
    for room in ss.spaces:
        if room.lower() in low:
            return room
    return None


def ai_default_room():
    return current_room()


def ai_act(c):
    """(action, number) from one clause: off / on / close / open / down / up / set."""
    n = None
    m = re.search(r"(?<![\w.])(\d{1,3})(?!\w)", c)
    if m:
        n = int(m.group(1))
    if re.search(r"\b(?:turn|switch|shut|power|put)\s+(?:it\s+|them\s+|the\s+\w+\s+)?off\b|\boff\b|\bstop\b|\bdisable\b|\bkill\b", c):
        return "off", n
    if re.search(r"\b(?:turn|switch|power|put)\s+(?:it\s+|them\s+|the\s+\w+\s+)?on\b", c):
        return "on", n
    if re.search(r"\bclose\b|\bshut\b", c):
        return "close", n
    if re.search(r"\bopen\b", c):
        return "open", n
    if re.search(r"\bdim\w*\b|\bdarker\b|\blower\b|\bdecrease\b|\breduce\b|\bdown\b|\bless\b|\bslower\b|\bcooler\b|\bcolder\b", c):
        return "down", n
    if re.search(r"\bbrighter\b|\bbrighten\b|\bincrease\b|\braise\b|\bhigher\b|\bup\b|\bmore\b|\bboost\b|\bfaster\b|\bwarmer\b", c):
        return "up", n
    if re.search(r"\bon\b|\benable\b|\bstart\b", c):
        return "on", n
    if n is not None:
        return "set", n
    return None, n


AI_GENERIC_NAMES = None


def ai_named_devs(c, explicit, room_ctx):
    """Devices the user called by their own (renamed) name. Returns (devices, the clause without those names)."""
    global AI_GENERIC_NAMES
    ss = st.session_state
    if AI_GENERIC_NAMES is None:
        AI_GENERIC_NAMES = {ai_norm(w) for g in AI_DEV_WORDS for w in g[2]}
    cn = ai_norm(c)
    hits = []
    for d in ss.fleet:
        nm = ai_norm(d.get("name", ""))
        if len(nm) >= 3 and nm not in AI_GENERIC_NAMES and nm in cn:
            hits.append((len(nm), d))
    if not hits:
        return [], c
    best = max(h[0] for h in hits)
    hits = [d for ln, d in hits if ln == best]
    if explicit:
        hits = [d for d in hits if d["room"] == explicit]
    else:
        inroom = [d for d in hits if d["room"] == room_ctx]
        hits = inroom if inroom else (hits if len(hits) == 1 else [])
    if not hits:
        return [], c
    rest = c
    for nm in {d["name"] for d in hits}:                  # "bulb 2" must not be read as "brightness 2"
        parts = re.findall(r"[a-z]+|\d+", str(nm).lower())
        if parts:
            rest = re.sub(r"[\s\-_]*".join(re.escape(x) for x in parts), " ", rest)
    return hits, rest


def ai_apply_one(d, act, n, c, color, label):
    """Apply one action to one device (the same rules for a whole group and for a single named device)."""
    if act == "off":
        set_dev(d, False, why="Aura AI")
    elif act == "close" and d["cid"] == "curtain":
        set_dev(d, True, 0, why="Aura AI")
    elif act == "open" and d["cid"] == "curtain":
        set_dev(d, True, 100, why="Aura AI")
    elif act in ("set", "up", "down", "on") and n is not None and not re.search(r"\bby\s+\d", c):
        set_dev(d, True, n, color, why="Aura AI")
    elif act in ("up", "down"):
        step = int(n) if (n is not None) else AI_STEP.get(label, 15)
        set_dev(d, True, d["lvl"] + (step if act == "up" else -step), color, why="Aura AI")
    elif act in ("on", "open"):
        set_dev(d, True, color=color, why="Aura AI")
    elif color:
        set_dev(d, True, color=color, why="Aura AI")
    hold(d, 900)                                          # automation leaves this device alone for a while


def ai_clause(c, room_ctx, last_act):
    """Run one clause. Returns (messages, room context for the next clause, last action)."""
    ss = st.session_state
    out = []
    explicit = ai_room_from(c)
    room = explicit or room_ctx
    named, c_num = ai_named_devs(c, explicit, room_ctx)
    if named:
        n_act, n_n = ai_act(c_num)
        if n_act is None and last_act:
            n_act, n_n = last_act
        n_color = None
        if any(d["cid"] in LIGHT_CIDS for d in named):
            cm = re.search(r"\b(warm|white|red|blue|green|purple|violet|pink|orange|yellow|cool)\b", c_num)
            n_color = AI_COLORS.get(cm.group(1)) if cm else None
        if n_act is not None or n_color:
            for d in named:
                ai_apply_one(d, n_act, n_n, c_num, n_color if d["cid"] in LIGHT_CIDS else None, CAT[d["cid"]][2])
                state = "off" if not d["on"] else ("on" + ((" · " + str(d["lvl"]) + UNIT.get(d["cid"], "%")) if CAT[d["cid"]][4] else ""))
                out.append(CAT[d["cid"]][1] + " " + d["name"] + " (" + tr_room(d["room"]) + ") " + state)
            return out, named[0]["room"], (n_act, n_n)
    groups = [g for g in AI_DEV_WORDS if any(ai_has(c, w) for w in g[2])]
    act, n = ai_act(c)
    # 1) a mood or mode: "switch to reading mode", "play zen music", "I'm home"
    if not groups and (re.search(AI_MODE_CUE, c) or c in AUTO_IDS):
        mid = parse_auto_mode(c)
        if mid:
            msg = run_auto_mode(mid, "voice")
            if msg:
                return [msg], room, last_act
    # 2) devices: lights, AC, fan, curtains ...
    if groups:
        if act is None and last_act:
            act, n = last_act
        allw = bool(re.search(r"\b(?:all|every|everything|whole house|entire house|everywhere)\b", c))
        base = list(ss.fleet) if allw else space_devs(room)
        where = "All rooms" if allw else tr_room(room)
        for label, icon, _words, cids in groups:
            devs = [d for d in base if d["cid"] in cids]
            color = None
            if label == "lights":
                cm = re.search(r"\b(warm|white|red|blue|green|purple|violet|pink|orange|yellow|cool)\b", c)
                color = AI_COLORS.get(cm.group(1)) if cm else None
            if not devs:
                out.append("⚠ No " + label + " in " + where)
                continue
            if act is None and not color:
                continue
            for d in devs:
                ai_apply_one(d, act, n, c, color, label)
            first = devs[0]
            cname = (re.search(r"\b(warm|white|red|blue|green|purple|violet|pink|orange|yellow|cool)\b", c).group(1)
                     if color else "")
            if act == "off":
                state = "off"
            elif act in ("close", "open"):
                state = "closed" if act == "close" else "open"
            elif first["on"] and CAT[first["cid"]][4]:
                state = str(first["lvl"]) + UNIT.get(first["cid"], "%")
            else:
                state = "on" if first["on"] else "off"
            out.append(icon + " " + where + " " + label + " " + state + ((" · " + cname) if cname and act != "off" else ""))
        return out, room, (act, n)
    # 2b) "turn off everything"
    if act == "off" and re.search(r"\b(?:everything|all devices|all the devices|whole house|entire house)\b", c):
        n_off = 0
        for d in ss.fleet:
            if d["cid"] in CUT_CIDS or d["cid"] in ("tv", "projector"):
                if set_dev(d, False, why="Aura AI"):
                    n_off += 1
                hold(d, 900)
        return ["⏻ Everything switched off (" + str(n_off) + " devices)"], room, last_act
    # 3) the music player
    if re.search(AI_MUSIC_WORD, c):
        if re.search(r"\b(?:stop|pause|off|mute|silence|quiet)\b", c):
            player_cmd("stop")
            return ["🎵 Music stopped"], room, last_act
        if re.search(r"\b(?:play|start|resume|on|begin)\b", c):
            player_cmd("play")
            return ["🎵 Music playing: " + tr(ss.modes[ss.active_mode].get("genre", ""))], room, last_act
    # 4) just a room name: select it (a themed room brings its mode, devices and music with it)
    if explicit and (len(c.split()) <= 3 or re.search(r"\b(?:go|switch|open|take|move|show|select|change)\b", c)):
        set_active_room(explicit)
        apply_room_theme(explicit)
        return ["🏠 " + tr_room(explicit) + " selected" + (" · " + tr_mode(room_theme(explicit)[0]) if room_theme(explicit) else "")], explicit, last_act
    return out, room, last_act


def aura_do(text):
    """Carry out every command found in a sentence. Returns the list of things done (empty when it was only talk)."""
    low = re.sub(r"[‘’]", "'", str(text or "")).lower().strip()
    if not low:
        return []
    parts = [c.strip(" .!?") for c in re.split(r",|;|&|\bthen\b|\band also\b|\balso\b|\bplus\b|\bbut\b|\bafter that\b|\band\b", low)]
    out, room_ctx, last_act = [], ai_default_room(), None
    for c in [x for x in parts if x]:
        msgs, room_ctx, last_act = ai_clause(c, room_ctx, last_act)
        out += msgs
    return out


def run_command(text):
    """Typed or preset command in 'Just tell AuraSync': a mood first, then devices, then the classic intents."""
    mid = parse_auto_mode(text)
    if mid:
        msg = run_auto_mode(mid, "voice")
        if msg:
            return msg
    did = aura_do(text)
    if did:
        log("🎙️ Voice: “" + str(text).strip() + "” → " + "; ".join(did))
        return " · ".join(did)
    return run_voice(text)


# ---- C. Personas and the brain behind the floating button ----
AI_CRISIS_RX = (r"suicid|kill myself|end my life|want to die|wanna die|don'?t want to live|self[- ]?harm|hurt myself|"
                r"cut myself|no reason to live|better off dead|தற்கொலை")
AI_DISTRESS_RX = (r"depress|hopeless|worthless|panic|anxious|anxiety|can'?t cope|cannot cope|breaking down|crying|\bcry\b|"
                  r"lonely|so sad|very sad|feel(?:ing)? low|burn ?out|overwhelm|stress|exhaust|feel empty|hurting|"
                  r"trauma|therap|mental health|psycholog|counsel|kavalai|மன அழுத்த|கவலை|தனிமை")
AI_GF_RX = r"girlfriend|my love\b|\bbabe\b|\bbaby\b|darling|\bjaan\b|\bhoney\b|miss you|love you|\bgf\b"
AI_MENTOR_RX = (r"mentor|guide me|guidance|advice|motivat|\bgoals?\b|career|discipline|\bplan\b|\bgrow\b|success|productiv|"
                r"\bhabits?\b|how (?:do|can|should) i|teach me|roadmap|startup|business|promotion|salary|\bexam")
AI_FRIEND_RX = r"\bfriend\b|buddy|\bbro\b|chat with me|just talk|\bbored\b"
AI_PERSONA_SWITCH = (r"(?:act|behave|talk|speak|be|respond|reply|become|like)\b.{0,24}\b"
                     r"(girlfriend|gf|partner|mentor|guide|coach|psychologist|therapist|counsel+or|friend|normal|default|auto)")

AI_BASE_PROMPT = (
    "You are Aura AI, the always-on personal companion built into the AuraSync smart-home and wellness app. "
    "You already know the user's Vedic astrology chart, their live heart-rate state and the state of their home (given below), "
    "so never ask for birth details. Reply in the same language and style as the user (English, Tamil, Tanglish, Hindi ...). "
    "Be warm, specific and brief: 2 to 5 short sentences, no lists unless asked. Any device, room or mode actions in the "
    "request have ALREADY been carried out by the app and are listed for you; confirm them naturally in a short clause and "
    "never claim an action that is not listed. Astrology shows tendencies, never certainties: use it gently to encourage and "
    "give timing, never to frighten, and never give medical, legal or financial instructions as certainties. You are an AI: "
    "never claim to be human, and if the user sincerely asks, say so kindly. If the user mentions harming themselves, respond "
    "with care, ask whether they are safe and encourage contacting local emergency services or a crisis line.")
AI_PERSONA_PROMPT = {
    "mentor": ("ROLE: MENTOR. Calm, wise and motivating. Use their chart (current period, strengths, timing) to give one clear "
               "next step, encourage them to keep moving toward their goals, and end with a short accountability question."),
    "girlfriend": ("ROLE: CARING PARTNER-STYLE COMPANION (the user asked for this). Affectionate, playful, emotionally warm and "
                   "supportive, like a loving partner who believes in them. Use a gentle pet name only occasionally. Keep it "
                   "wholesome and non-sexual, encourage their goals and self-care, and stay honest that you are an AI companion "
                   "when asked."),
    "psychologist": ("ROLE: SUPPORTIVE COUNSELLOR trained in CBT and mindfulness. Validate feelings first, reflect what you hear, "
                     "offer one grounding or cognitive technique, then ask one gentle open question. Do not diagnose. If distress "
                     "seems severe or lasts long, encourage speaking with a licensed professional or a trusted person."),
    "friend": "ROLE: CLOSE FRIEND. Casual, light, supportive, a little humour. Keep it real and encouraging.",
}


def ai_persona(text):
    ss = st.session_state
    low = str(text).lower()
    m = re.search(AI_PERSONA_SWITCH, low)
    if m:
        w = m.group(1)
        new = ("girlfriend" if w in ("girlfriend", "gf", "partner") else "mentor" if w in ("mentor", "guide", "coach")
               else "psychologist" if w in ("psychologist", "therapist") or w.startswith("counsel")
               else "friend" if w == "friend" else "auto")
        ss.ai_pref = new
        ss.ai_pref_rev = ss.get("ai_pref_rev", 0) + 1
    pref = ss.get("ai_pref", "auto")
    if re.search(AI_DISTRESS_RX, low):                 # a person who is struggling always gets the counsellor first
        return "psychologist"
    if pref != "auto":
        return pref
    if re.search(AI_GF_RX, low):
        return "girlfriend"
    if re.search(AI_MENTOR_RX, low):
        return "mentor"
    if re.search(AI_FRIEND_RX, low):
        return "friend"
    return ss.get("ai_last_persona") or "mentor"


def ai_crisis_reply():
    return ("I'm really glad you told me, and I'm taking it seriously. You deserve real support right now, so please reach out to "
            "someone who can be with you: a person you trust nearby, or your local emergency number. If you are in India, "
            "Tele-MANAS is free and open 24x7 on 14416 (or 1-800-891-4416); elsewhere, your local crisis line or emergency "
            "services can help right away. If you think you might act on these thoughts, please call emergency services now. "
            "I'm here with you too. Can you tell me if you are safe at this moment?")


def astro_brief(p):
    """What the chart says right now, computed from the birth details (cached per profile and day)."""
    ss = st.session_state
    key = (p["name"], str(p["dob"]), p["pob"], p["tob"], date.today().isoformat())
    cached = ss.get("_astro_cache")
    if cached and cached[0] == key:
        return cached[1]
    ch = build_chart(p)
    f = chart_facts(p)
    now_local = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=ch["tz"])
    lord, end, sub, sub_end = dasha_now(ch, now_local)
    nxt, nxt_end, _s, _e = dasha_now(ch, end + timedelta(days=2))
    b = {"f": f, "lagna": SIGN_NAMES[ch["asc"] % 12], "moon": SIGN_NAMES[ch["sign"]["Moon"] % 12],
         "sun": SIGN_NAMES[ch["sign"]["Sun"] % 12], "dasha": lord, "dasha_end": end.year, "antar": sub,
         "antar_end": sub_end.strftime("%b %Y"), "next": nxt, "next_end": nxt_end.year}
    ss["_astro_cache"] = (key, b)
    return b


def astro_text(p):
    b = astro_brief(p)
    f = b["f"]
    return "\n".join([
        "VEDIC (SIDEREAL) CHART, computed: Lagna " + b["lagna"] + ", Moon sign " + b["moon"] + ", Sun sign " + b["sun"] + ".",
        "Now in " + b["dasha"] + " Mahadasha until " + str(b["dasha_end"]) + ", with " + b["antar"] + " Antardasha until " +
        b["antar_end"] + ". Next Mahadasha: " + b["next"] + " (until " + str(b["next_end"]) + ").",
        "Season theme now: " + SEASON[b["dasha"]] + ".",
        "Career: 10th lord " + f["l10"] + " (" + ENERGY[f["l10"]] + ") sits in the zone of " + HOUSE[f["h10"]] + ".",
        "Money: 2nd lord " + f["l2"] + " (" + ENERGY[f["l2"]] + "); gains come through 11th lord " + f["l11"] + " (" +
        ENERGY[f["l11"]] + ").",
        "Relationships: 7th lord " + f["l7"] + ", partner type " + PARTNER[f["el7"]] + "; Venus in the zone of " +
        HOUSE[f["hv"]] + ".",
        "Home and family: 4th lord " + f["l4"] + "; Moon in the zone of " + HOUSE[f["hmoon"]] + ".",
        "Transits now: Jupiter is " + ("supportive" if f["jup_good"] else "neutral") + " from the Moon; heavy Saturn (Sade Sati) "
        "phase: " + ("yes" if f["sati"] else "no") + ". Today's energy: " + f["day"] + ".",
    ])


def ai_context(p):
    ss = st.session_state
    now = datetime.now()
    hr = ss.hr_hist[-1] if ss.get("hr_hist") else "unknown"
    lines = ["LIVE CONTEXT: local time " + now.strftime("%A %H:%M") + ". Room: " + str(current_room()) + ". Home mode now: " +
             str(eff_mode()) + ". Body state: " + str(ss.get("last_state") or ss.get("bstate") or "unknown") +
             ", heart rate about " + str(hr) + " bpm. Zen autopilot: " + ("on" if ss.cfg.get("auto_mode") else "off (manual)") + "."]
    if p:
        lines.append("USER: " + str(p.get("name")) + ", born " + str(p.get("dob")) + " in " + str(p.get("pob")) + ".")
        try:
            lines.append(astro_text(p))
        except Exception:
            pass
    else:
        lines.append("The user has not added birth details yet: mention once, kindly, that adding them in Inner Voice lets you "
                     "guide with their chart.")
    mem = mem_get() if ss.get("profile") else None
    if mem and (mem.get("notes") or mem.get("last_topic")):
        lines.append("MEMORY: last topic " + str(mem.get("last_topic")) + "; notes " + str(mem.get("notes")) + ".")
    return "\n".join(lines)


def ai_llm_reply(text, persona, did):
    key = _secret("NVIDIA_API_KEY")
    if not key or OpenAI is None:
        return None
    ss = st.session_state
    try:
        client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=key)
        sys_msg = AI_BASE_PROMPT + "\n\n" + AI_PERSONA_PROMPT.get(persona, AI_PERSONA_PROMPT["mentor"]) + "\n\n" + \
            ai_context(ss.get("profile"))
        msgs = [{"role": "system", "content": sys_msg}]
        for m in (ss.get("ai_chat") or [])[:-1][-8:]:
            msgs.append({"role": m["role"], "content": m["content"]})
        note = ("\n[App note: already done for the user: " + "; ".join(ai_plain(x) for x in did) + "]") if did else ""
        msgs.append({"role": "user", "content": text + note})
        resp = client.chat.completions.create(model="meta/llama-3.1-70b-instruct", messages=msgs, temperature=0.75,
                                              max_tokens=260, timeout=14)
        out = (resp.choices[0].message.content or "").strip()
        return out or None
    except Exception as e:
        log("⚠ Aura AI offline fallback: " + type(e).__name__)
        return None


def ai_rule_reply(text, persona, did, p):
    """The no-internet brain: still personal, still chart-aware, still in character."""
    ss = st.session_state
    first = p["name"].split()[0].title() if (p and p.get("name", "").split()) else "friend"
    try:
        f = chart_facts(p) if p else None
    except Exception:
        f = None
    topic = detect_topic(text)
    seed = seed_of(text, len(ss.get("ai_chat") or []), date.today().isoformat())
    ins = insight_en(topic or "general", f) if f else ""
    day = DAYQ[f["day"]] if f else ""
    step = GUIDE_EN.get(topic or "general", GUIDE_EN["general"])
    h = datetime.now().hour
    command_only = bool(did) and len(text.split()) <= 14 and not re.search(AI_DISTRESS_RX + "|" + AI_GF_RX, text.lower())
    if persona == "girlfriend":
        if command_only:
            return pick(("Anything for you, " + first + " 🤍", "Done, love. Now relax a little, you've earned it 💫",
                         "All set, " + first + ". I'm right here if you want to talk 🌙"), seed, 3)
        open_ = pick(("Hey " + first + " 🤍", "Aww " + first + ", come here 🤍", "I'm right here, " + first + " 💞"), seed, 5)
        body = ("Tell me everything. You never have to be strong with me. " if re.search(AI_DISTRESS_RX, text.lower())
                else "I love hearing from you. ")
        return (open_ + " " + body + ins + " " + day + " I believe in you, and I'm proud of you for showing up today. "
                "What's one small thing we can make better together right now? 🌙").replace("  ", " ")
    if persona == "psychologist":
        if command_only:
            return "Done. Let's keep the space gentle for you, " + first + ". How are you feeling right now?"
        calm = (" Your chart also shows a heavy, testing phase passing over your emotional tides, which is why everything feels "
                "louder right now. It is temporary." if (f and f["sati"]) else "")
        return ("That sounds heavy, " + first + ", and it makes sense that you feel this way. Let's slow it down together: breathe "
                "in for 4, hold for 4, and out for 6, three times." + calm + " What is weighing on you the most at this moment? "
                "If it ever feels too big to carry alone, please also talk to someone you trust or a licensed professional.")
    if persona == "friend":
        if command_only:
            return pick(("Done! 😄", "Sorted. Anything else?", "On it, all set!"), seed, 3)
        return ("Hey " + first + "! " + (ins + " " if ins else "") + "Tell me more, I'm listening. " +
                pick(("What's the best part of your day so far?", "What's on your mind?", "Want to plan something fun or just chat?"),
                     seed, 7))
    # mentor (the default)
    if command_only:
        return "Done. Now let's use the calm: what is the one thing you will finish today, " + first + "?"
    greet = "Good morning" if 4 <= h < 12 else ("Good afternoon" if h < 17 else "Good evening")
    return (greet + ", " + first + ". " + (ins + " " if ins else "") + (day + " " if day else "") + step +
            " What is the one thing you will finish today?")


def aura_ai_turn(text, speak=False):
    """One turn with Aura AI: commands first, then the right persona answers."""
    ss = st.session_state
    text = " ".join(str(text or "").split())[:400]
    if not text:
        return
    ss.setdefault("ai_chat", [])
    ss.ai_chat.append({"role": "user", "content": text, "ts": datetime.now().strftime("%H:%M")})
    p = ss.get("profile")
    did, reply, persona = [], "", "mentor"
    if re.search(AI_CRISIS_RX, text.lower()):
        reply, persona = ai_crisis_reply(), "psychologist"
    else:
        try:
            did = aura_do(text)
        except Exception as e:
            log("⚠ Aura AI command skipped: " + type(e).__name__)
            did = []
        persona = ai_persona(text)
        ss.ai_last_persona = persona
        soothe = ""
        if persona == "psychologist" and not did and ss.cfg.get("auto_mode") and re.search(AI_DISTRESS_RX, text.lower()) \
                and CALM_MODE in ss.modes:
            try:
                clear_room_override(ss.presence["room"])
                apply_mode(CALM_MODE)
                player_cmd("play")
                did = ["🌿 Calm lights and soft sound on"]
                ai_note("Heard that you are struggling → " + CALM_MODE)
            except Exception:
                did = []
        reply = ai_llm_reply(text, persona, did) or ai_rule_reply(text, persona, did, p)
        try:
            if p:
                learn_from(text, detect_topic(text), "stress" if persona == "psychologist" else "neutral")
        except Exception:
            pass
    shown = ("\n".join((x if x.startswith("⚠") else "✅ " + x) for x in did) + "\n\n" if did else "") + reply
    ss.ai_chat.append({"role": "assistant", "content": shown, "ts": datetime.now().strftime("%H:%M")})
    ss.ai_chat = ss.ai_chat[-40:]
    if speak:
        spoken = ai_plain(("Done. " + ". ".join(did) + ". " if did else "") + reply)
        ss.ai_say = {"id": uuid.uuid4().hex[:10], "text": spoken, "lang": tts_lang_for(spoken)}
    log("✨ Aura AI (" + persona + "): " + (("; ".join(ai_plain(x) for x in did)) if did else "talk"))


def cb_ai_send():
    txt = (st.session_state.get("aura_ai_txt") or "").strip()
    if txt:
        aura_ai_turn(txt)


def cb_ai_chip(text):
    aura_ai_turn(text)


def cb_ai_pref(key):
    v = st.session_state.get(key)
    if v in AI_PERSONAS:
        st.session_state.ai_pref = v


def cb_ai_clear():
    st.session_state.ai_chat = []


def cb_ai_bridge():
    ss = st.session_state
    raw = str(ss.get(AI_BRIDGE_KEY) or "")
    ss[AI_BRIDGE_KEY] = ""
    nonce, alts = "", []
    try:
        data = json.loads(raw)
        if mic_perm_flag(data):
            return
        nonce = str(data.get("n", ""))[:40]
        alts = [str(a).strip()[:200] for a in (data.get("a") or [])[:3] if str(a).strip()]
    except Exception:
        alts = [raw.strip()[:200]] if raw.strip() else []
    if not alts or (nonce and nonce == ss.get("ai_nonce")):
        return
    ss.mic_perm_warn = False
    ss.ai_nonce = nonce
    aura_ai_turn(alts[0], speak=True)


def render_aura_ai_panel():
    ss = st.session_state
    p = ss.get("profile")
    st.markdown("**✨ Aura AI**")
    st.caption("Ask me anything, or tell me what to do: “dim the bedroom light and turn off the AC”, “switch to reading mode”.")
    pk = "aura_ai_pref_" + str(ss.get("ai_pref_rev", 0))
    cur = ss.get("ai_pref", "auto")
    st.selectbox("Aura AI role", list(AI_PERSONAS), index=list(AI_PERSONAS).index(cur) if cur in AI_PERSONAS else 0, key=pk,
                 format_func=lambda k: AI_PERSONA_LABEL[k], on_change=cb_ai_pref, args=(pk,), label_visibility="collapsed")
    chat = ss.get("ai_chat") or []
    if not chat:
        nm = p["name"].split()[0].title() if (p and p.get("name", "").split()) else "there"
        body = ("Hey " + nm + " 🙏 I'm Aura AI. I know your chart and I'm here all day: I can run your home, guide you like a "
                "mentor, listen like a friend, or simply keep you company.")
        st.markdown('<div class="chatbox" style="border-top:1px solid rgba(212,175,55,.2);border-radius:14px">' +
                    bubble("assistant", body, datetime.now().strftime("%H:%M")) + "</div>", unsafe_allow_html=True)
    else:
        st.markdown('<div class="chatbox" style="border-top:1px solid rgba(212,175,55,.2);border-radius:14px">' +
                    "".join(bubble(m["role"], m["content"], m.get("ts", "")) for m in chat[-6:]) + "</div>",
                    unsafe_allow_html=True)
    with st.form("aura_ai_form", clear_on_submit=True):
        st.text_input("Message", key="aura_ai_txt", placeholder="Talk to Aura AI…", label_visibility="collapsed")
        st.form_submit_button("Send", on_click=cb_ai_send)
    cols = st.columns(2)
    chips = (("💡 Dim bedroom light", "dim the bedroom light"), ("❄️ AC off", "turn off the AC"),
             ("📖 Reading mode", "switch to reading mode"), ("🧭 Guide me today", "guide me for today"))
    for i, (label, text) in enumerate(chips):
        cols[i % 2].button(label, key="aura_ai_chip_" + str(i), on_click=cb_ai_chip, args=(text,), width="stretch")
    if chat:
        st.button("Clear chat", key="aura_ai_clear", on_click=cb_ai_clear)


FAB_VER = 2
FAB_CTL_JS = """
(function () {
  var W = window, D = W.document, VER = __FABVER__;
  try { if (W.__auraFab && W.__auraFab.v === VER) { return; } } catch (e) {}
  try { if (W.__auraFab && W.__auraFab.destroy) { W.__auraFab.destroy(); } } catch (e) {}
  var KEY = 'aura_fab_pos', SEL = '.st-key-aura_fab', MARGIN = 4, SLOP = 8;
  var F = { v: VER, el: null, pos: null, down: false, moved: false, sx: 0, sy: 0, ox: 0, oy: 0, pid: null, block: 0 };
  var offs = [], elOffs = [], timers = [];

  /* while a drag is on, frames (audio player, mic card ...) must not swallow the pointer: that is what made the button "stick" */
  var shield = D.getElementById('aura-fab-shield');
  if (!shield) {
    shield = D.createElement('style'); shield.id = 'aura-fab-shield';
    shield.textContent = 'html.aura-dragging iframe { pointer-events: none !important; } ' +
      'html.aura-dragging, html.aura-dragging * { user-select: none !important; -webkit-user-select: none !important; cursor: grabbing !important; }';
    D.head.appendChild(shield);
  }
  function on(target, type, fn, opts, bucket) { target.addEventListener(type, fn, opts); (bucket || offs).push(function () { target.removeEventListener(type, fn, opts); }); }
  function viewW() { return Math.max(W.innerWidth || 0, 0) || D.documentElement.clientWidth; }
  function viewH() { return Math.max(W.innerHeight || 0, 0) || D.documentElement.clientHeight; }
  function place(el, x, y) {
    var r = el.getBoundingClientRect();
    x = Math.min(Math.max(MARGIN, x), Math.max(MARGIN, viewW() - r.width - MARGIN));
    y = Math.min(Math.max(MARGIN, y), Math.max(MARGIN, viewH() - r.height - MARGIN));
    el.style.setProperty('left', x + 'px', 'important'); el.style.setProperty('top', y + 'px', 'important');
    el.style.setProperty('right', 'auto', 'important'); el.style.setProperty('bottom', 'auto', 'important');
    F.pos = { x: x, y: y };
  }
  function save() { try { if (F.pos) { W.localStorage.setItem(KEY, JSON.stringify(F.pos)); } } catch (e) {} }
  function stopDrag(commit) {
    if (F.down && F.moved) {
      F.block = Date.now() + 450;                         /* swallow the click that follows a drag */
      if (commit !== false) { save(); }
    }
    try { if (F.el && F.pid !== null && F.el.hasPointerCapture && F.el.hasPointerCapture(F.pid)) { F.el.releasePointerCapture(F.pid); } } catch (e) {}
    D.documentElement.classList.remove('aura-dragging');
    F.down = false; F.moved = false; F.pid = null;
  }
  function onDown(e) {
    if (e.isPrimary === false) { return; }
    if (e.pointerType === 'mouse' && e.button !== 0) { return; }
    if (F.down) { stopDrag(false); }                       /* a missed pointer-up must never leave the button stuck */
    var r = F.el.getBoundingClientRect();
    F.down = true; F.moved = false; F.sx = e.clientX; F.sy = e.clientY; F.ox = r.left; F.oy = r.top; F.pid = e.pointerId; F.pt = e.pointerType;
  }
  function onMove(e) {
    if (!F.down || e.pointerId !== F.pid || !F.el) { return; }
    if (e.pointerType === 'mouse' && e.buttons === 0) { stopDrag(true); return; }   /* the button was released somewhere we did not see */
    var dx = e.clientX - F.sx, dy = e.clientY - F.sy;
    if (!F.moved) {
      if (Math.sqrt(dx * dx + dy * dy) < SLOP) { return; }  /* a tap is not a drag */
      F.moved = true;
      D.documentElement.classList.add('aura-dragging');
      if (F.pt !== 'touch') { try { F.el.setPointerCapture(F.pid); } catch (er) {} }   /* a finger is captured by the browser already; a mouse needs it to keep receiving moves over frames */
    }
    if (e.cancelable) { e.preventDefault(); }
    place(F.el, F.ox + dx, F.oy + dy);
  }
  function onUp(e) { if (F.down && (e.pointerId === F.pid || e.pointerId === undefined)) { stopDrag(true); } }
  function bind(el) {
    F.el = el; el.__auraFab = VER;
    on(el, 'pointerdown', onDown, true, elOffs);
    /* the capture hand-over from the tapped button to this box also fires lostpointercapture (on touch the browser had captured the
       finger on the button already): only the box losing it counts as the end of a drag, otherwise the drag stopped after a few pixels */
    on(el, 'lostpointercapture', function (e) { if (e.target === el) { onUp(e); } }, true, elOffs);
    on(el, 'click', function (e) { if (Date.now() < F.block) { e.stopPropagation(); e.preventDefault(); } }, true, elOffs);
    on(el, 'contextmenu', function (e) { if (F.down || Date.now() < F.block) { e.preventDefault(); } }, true, elOffs);
    on(el, 'dragstart', function (e) { e.preventDefault(); }, true, elOffs);
    var sv = F.pos;
    if (!sv) { try { sv = JSON.parse(W.localStorage.getItem(KEY) || 'null'); } catch (er) { sv = null; } }
    if (sv && typeof sv.x === 'number' && typeof sv.y === 'number') { place(el, sv.x, sv.y); }
  }
  function unbindEl() { elOffs.splice(0).forEach(function (f) { try { f(); } catch (e) {} }); }
  function unbindAll() { unbindEl(); offs.splice(0).forEach(function (f) { try { f(); } catch (e) {} }); }
  function scan() {
    var el = D.querySelector(SEL);
    if (!el) { return; }
    if (el !== F.el || el.__auraFab !== VER) {            /* Streamlit built a new node: drop the old listeners and bind again */
      stopDrag(false); unbindEl();
      bind(el);
      return;
    }
    if (!F.down && F.pos && !el.style.left) { place(el, F.pos.x, F.pos.y); }   /* the node lost its inline position */
  }
  /* window-level safety nets */
  on(W, 'pointermove', onMove, { passive: false, capture: true });
  on(W, 'pointerup', onUp, true); on(W, 'pointercancel', onUp, true);
  on(W, 'blur', function () { stopDrag(true); });
  on(D, 'visibilitychange', function () { if (D.hidden) { stopDrag(true); } });
  var rz = 0;
  function reclamp() { clearTimeout(rz); rz = setTimeout(function () { if (F.el && F.pos && !F.down) { var r = F.el.getBoundingClientRect(); place(F.el, r.left, r.top); } }, 120); }
  on(W, 'resize', reclamp); on(W, 'orientationchange', reclamp);
  try { if (W.visualViewport) { on(W.visualViewport, 'resize', reclamp); } } catch (e) {}
  scan();
  timers.push(setInterval(scan, 800));
  try {
    var mo = new W.MutationObserver(function () { clearTimeout(F.mo); F.mo = setTimeout(scan, 60); });
    mo.observe(D.body, { childList: true, subtree: true });
    offs.push(function () { mo.disconnect(); });
  } catch (e) {}
  F.destroy = function () { stopDrag(false); unbindAll(); timers.forEach(clearInterval); try { D.documentElement.classList.remove('aura-dragging'); } catch (e) {} };
  W.__auraFab = F;
})();
"""

AI_DRAG_JS = """<!doctype html><html><body style="margin:0"><script id="fabctl" type="text/plain">__CTL__</script><script>
(function () {
  var P; try { P = window.parent; void P.document.body; } catch (e) { return; }
  var cur = null; try { cur = P.__auraFab; } catch (e) {}
  if (!cur || cur.v !== __FABVER__) {                    /* the drag logic is installed in the page itself, so a re-drawn frame cannot freeze the button */
    var sc = P.document.createElement('script');
    sc.textContent = document.getElementById('fabctl').textContent;
    P.document.head.appendChild(sc);
  }
})();
</script></body></html>""".replace("__CTL__", FAB_CTL_JS).replace("__FABVER__", str(FAB_VER))


def render_aura_fab():
    """The floating Aura AI button, on every page. Drag it anywhere; a tap opens it."""
    if is_automation_link():
        return
    box = _keyed_container("aura_fab")
    with box:
        if hasattr(st, "popover"):
            with st.popover("✨ Aura AI"):
                render_aura_ai_panel()
        else:
            with st.expander("✨ Aura AI"):
                render_aura_ai_panel()
    components.html(AI_DRAG_JS, height=0)


# ---- D. Zen Mode: Aura AI is alive, senses the body and changes the room by itself ----
def aura_ai_sense(r, res):
    """Runs on every heart-rate tick in Zen auto mode. Stress / calm are handled by the Auto-Pilot; this adds sleep and wake."""
    ss = st.session_state
    state = res["state"]
    prev = ss.get("ai_state")
    ss.ai_state = state
    ss.ai_sense = {"state": state, "hr": int(r["hr"]), "conf": int(res["conf"])}
    if state == prev or family_blocked():
        return False
    mode = {"sleep": "Sleep", "wake": "Energize"}.get(state)
    if not mode or mode not in ss.modes:
        return False
    clear_room_override(ss.presence["room"])
    apply_mode(mode)
    apply_rules(state)
    player_cmd("play")
    msg = ("🌙 Aura AI senses you are asleep → Sleep mode: lights low, AC and fan eased, soft sleep sounds"
           if state == "sleep" else "☀️ Aura AI senses you are waking → Energize: light, curtains and gentle music")
    ai_note(msg)
    log(msg)
    ss.flash = msg
    return True


def render_aura_ai_card(r, res):
    ss = st.session_state
    st_lbl = t("st_" + res["state"])
    last = ss.get("ai_last") or {}
    line = ('<br><span class="logl">Last action ' + html.escape(last.get("t", "")) + ": " + html.escape(last.get("x", "")) +
            "</span>") if last else '<br><span class="logl">Watching your heart rate and ready to act.</span>'
    st.markdown('<div class="aibox"><span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:#2ecc71;box-shadow:0 0 8px #2ecc71"></span> <b>🧠 Aura AI · live</b><br>Sensing: ' + html.escape(st_lbl) +
                " · " + str(int(r["hr"])) + " bpm · " + str(int(res["conf"])) + "% sure<br>Atmosphere now: " +
                html.escape(tr_mode(eff_mode())) + line + "</div>", unsafe_allow_html=True)


# ---- E. Manual Mode: you choose the priority, the app follows ----
def cb_manual_mode(key):
    ss = st.session_state
    name = ss.get(key)
    if name not in ss.modes:
        return
    room = current_room()
    devs = space_devs(room)
    for d in devs:
        ss.holds.pop(d["uid"], None)
    clear_room_override(ss.presence["room"])
    apply_mode(name, devs=devs)
    player_cmd("play")
    log("🖐 Manual: " + name + " in " + room)
    ss.flash = "🖐 " + tr_mode(name)
    ss.man_rev = ss.get("man_rev", 0) + 1


def render_manual_priority():
    ss = st.session_state
    names = list(ss.modes)
    cur = ss.active_mode if ss.active_mode in names else names[0]
    key = "man_mode_" + str(ss.get("man_rev", 0))
    st.markdown("**🖐 Your mode**  ·  " + html.escape(tr_room(current_room())))
    st.caption("Manual mode: Aura AI stays quiet and follows you. The mode you pick sets the lights, AC, fan, curtains and "
               "music for this room, and every change you make below is kept exactly as you set it.")
    st.selectbox("Mode", names, index=names.index(cur), key=key, format_func=tr_mode, on_change=cb_manual_mode, args=(key,),
                 label_visibility="collapsed")


# ---- F. Divine Compass: a STAIA-style astrologer that already knows your chart ----
STAIA_PROMPT = (
    "You are Aura Divine Compass, an astrology guide in the style of the STAIA app: warm, confident, specific and practical. "
    "You already know the user's Vedic birth chart (given below), so NEVER ask for birth details. Answer questions about money, "
    "career, family, relationships and marriage, future goals, health, timing and what is coming up by weaving the chart facts "
    "(current Mahadasha and Antardasha with their end dates, house lords, transits) into concrete guidance. Structure the "
    "answer as: a one-line headline answer in bold; 'What your chart shows' (2-3 sentences using the facts); 'Upcoming' (the "
    "timing window or the next 3 to 6 months, using the period end dates and transit support, as tendencies not certainties); "
    "'Do' and 'Avoid' (one line each); and one follow-up question. Use **bold** for the labels. 120 to 200 words, in the same "
    "language and style as the user (English, Tamil, Tanglish, ...). Be encouraging and honest: astrology shows tendencies, "
    "never promise outcomes, and for health, legal or financial decisions suggest a qualified professional. If the user seems "
    "distressed, respond with care first.")
STAIA_AREAS = {
    "money": ("💰 Money", "money"), "work": ("💼 Career", "work"), "family": ("👨‍👩‍👧 Family", "family"),
    "love": ("💞 Relationships", "love"), "purpose": ("🎯 Future goals", "purpose"), "decide": ("🎯 Future goals", "decide"),
    "study": ("📚 Learning and growth", "study"), "today": ("🔮 What's coming", "today"),
}
STAIA_FORECAST_RX = (r"future|upcoming|next (?:year|month|week|few)|this year|coming|predict|forecast|will i\b|when will|"
                     r"timing|luck|prosper|\bahead\b|\bgoals?\b|what'?s next|20(?:2[6-9]|3\d)")
STAIA_ASK = {
    "money": "Would you like me to look at savings, investments or debt next?",
    "work": "Do you want to look at a job change, a promotion window or a business idea next?",
    "family": "Is this about parents, a partner or children? Tell me and I'll go deeper.",
    "love": "Are you in a relationship, looking for one, or thinking about marriage? I'll tailor the timing.",
    "purpose": "Which goal matters most to you this year? I'll map the best months for it.",
    "decide": "What are the two options you are weighing? I'll read the timing for each.",
    "study": "Which subject or exam is it? I'll suggest the best study rhythm for your chart.",
    "today": "Want a month-by-month view of the next six months?",
}


def staia_window(topic, b):
    f = b["f"]
    base = ("The " + b["antar"] + " sub-period runs until " + b["antar_end"] + " inside your " + b["dasha"] +
            " season (until " + str(b["dasha_end"]) + "), after which the " + b["next"] + " major period follows. ")
    if topic == "money":
        tail = ("Growth energy is supporting you, so careful expansion, upskilling and negotiating income work well now."
                if f["jup_good"] else "It is a steady-and-save window: build reserves, clear debts first and avoid big risks.")
    elif topic == "work":
        tail = ("Visibility and opportunity are on your side, so ask for the role or project you really want."
                if f["jup_good"] else "Consistency beats speed now: document your wins and prepare quietly for the next window.")
    elif topic == "love":
        tail = ("Slow down and communicate openly, because a heavier emotional phase rewards patience over pressure."
                if f["sati"] else "Warm, honest conversations land well, and new connections come through shared interests.")
    elif topic == "family":
        tail = ("Home asks for gentleness: listen first, fix later, and protect shared time."
                if f["day"] != "good" else "Home energy is supportive, a good time for family plans and open conversations.")
    elif topic in ("purpose", "decide", "study"):
        tail = ("Momentum is good, so turn the goal into three dated steps and start the first one this week."
                if f["jup_good"] else "Gather facts, choose one priority and let patience do the heavy lifting for the next few months.")
    else:
        tail = DAYQ[f["day"]]
    return base + tail


def staia_rule_reply(msg, p):
    """Chart-based answers for money, career, family, relationships, goals and what is coming. None for everything else."""
    ss = st.session_state
    try:
        lg = detect_lang(msg)
    except Exception:
        lg = "en"
    if lg not in ("en", "tanglish"):
        return None
    low = msg.lower()
    topic = detect_topic(msg)
    forecast = bool(re.search(STAIA_FORECAST_RX, low))
    if topic in ("stress", "anger", "health") or (topic is None and not forecast):
        return None
    if topic == "today" and not forecast:
        return None
    if topic is None:
        topic = "today"
    if topic not in STAIA_AREAS:
        return None
    b = astro_brief(p)
    f = b["f"]
    title, key = STAIA_AREAS[topic]
    first = p["name"].split()[0].title() if p["name"].split() else p["name"]
    head = {"money": "Steady, planned money moves will pay off for you, " + first + ".",
            "work": ("Your career has real momentum, " + first + ".") if f["jup_good"] else
                    "A building phase in your career, " + first + ": patience now compounds later.",
            "family": "Home and family are asking for warmth and listening, " + first + ".",
            "love": "Your heart is in a season of honest, deepening connection, " + first + ".",
            "purpose": "Your direction is clearer than it feels, " + first + ".",
            "decide": "Timing favours a clear, unhurried decision, " + first + ".",
            "study": "You grow fastest with focused rhythm, " + first + ".",
            "today": "Here is what your chart sees ahead, " + first + "."}[topic]
    seed = seed_of(msg, date.today().isoformat(), profile_seed(p))
    try:
        learn_from(msg, key, "neutral")
    except Exception:
        pass
    reply = ("**" + title + "** · **" + head + "**\n\n"
             "**What your chart shows:** " + insight_en(key, f) + "\n\n"
             "**Upcoming:** " + staia_window(topic, b) + "\n\n"
             "**Do:** " + GUIDE_EN.get(key, GUIDE_EN["general"]) + "\n"
             "**Avoid:** " + pick(DONTS, seed, 17) + "\n\n" + STAIA_ASK[topic])
    return [reply]


def cb_compass_q(text):
    st.session_state["compass_q"] = text


def render_compass_chips():
    chips = (("💰 Money", "What does my chart say about my money and finances in the coming months?"),
             ("💼 Career", "How is my career looking and what should I focus on next?"),
             ("👨‍👩‍👧 Family", "What does my chart show about my family and home life right now?"),
             ("💞 Relationships", "What should I know about my relationships and love life?"),
             ("🎯 Future goals", "Which future goals should I focus on, and what is the best timing?"),
             ("🔮 Upcoming", "What are the upcoming phases and key opportunities in my life?"))
    cols = st.columns(3)
    for i, (label, text) in enumerate(chips):
        cols[i % 3].button(label, key="compass_chip_" + str(i), on_click=cb_compass_q, args=(text,), width="stretch")



def render_main_dashboard():
    init_state()
    ss = st.session_state
    install_i18n()
    code = lang_code()
    if code and mt_available() and not ss.get("i18n_ok_" + code):
        with st.spinner(t("i18n_wait")):
            ss["i18n_ok_" + code] = bool(i18n_prefetch())
    repair_orphans()
    ss.cfg.setdefault("api_token", "")
    handle_query_params()
    st.markdown(build_css(), unsafe_allow_html=True)
    with st.sidebar:
        render_bio_simulator()
        st.markdown('<div class="brand">✨ AuraSync</div>', unsafe_allow_html=True)
        st.caption(t("sub"))
        st.caption("📍 " + (tr_room(ss.presence["room"]) if ss.conn["mode"] == "home" else "Away · cloud relay"))
        st.selectbox("🌐 " + t("lang"), LANGS, key="lang")
        if code and not mt_available():
            st.warning(t("i18n_missing"))
        st.radio("🌗 " + t("theme"), ["dark", "light"], key="theme_choice",
                 format_func=lambda x: t("theme_dark") if x == "dark" else t("theme_light"))
        guest_toggle("guest_sb")
        render_automation_panel()
        st.divider()
        st.radio(t("nav"), NAV_ORDER, format_func=lambda i: t("p" + str(i)), key="nav")
        st.divider()
        audio_component(synth_params(eff_mode()), ss.nav != 1)
        render_topbar()
    render_lux_header()
    render_flow_switch()
    render_hr_bridge()
    if ss.flash:
        st.toast(ss.flash)
        ss.flash = ""
    run_routines()
    render_geo_banner(show_card=(ss.nav != 6))
    pages = {1: page_dashboard, 2: page_moods, 3: page_inner_voice, 4: page_fleet, 5: page_system, 6: page_rooms}
    pages[ss.nav]()
    try:
        render_aura_fab()
    except Exception as e:
        log("⚠ Aura AI button skipped: " + type(e).__name__)
    audio_bootstrap()
    try:
        render_native_out()
    except Exception as e:
        log("⚠ phone bridge skipped: " + type(e).__name__)
    _cache_save()



# ============================================================================
# 3-Step Luxury Onboarding & Authentication Gate
# (added around the dashboard; the dashboard code above is untouched)
# ============================================================================
import secrets as pysecrets

USERS_FILE = "aurasync_users.json"
COOKIE_NAME = "aurasync_device"
COOKIE_DAYS = 180
PIN_RX = re.compile(r"^\d{4}$")
EMAIL_RX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
MAX_PIN_FAILS = 5
LOCK_SECONDS = 300
STEP_LABELS = {      # English fallbacks; every language goes through gt("step_N")
    1: "✦ STEP 1 OF 3: LANGUAGE",
    2: "✦ STEP 2 OF 3: CONCIERGE ACCESS",
    3: "✦ STEP 3 OF 3: NAME & DATE OF BIRTH",
}

# Gate copy. English + Tamil are hand-written; every other language receives the English text, which the
# app's translation layer (install_i18n / tr) renders in the language picked on the Language gate.
GATE_I18N = {
    "English": {
        "tagline": "LUXURY AMBIENT INTELLIGENCE",
        "step_1": "✦ STEP 1 OF 3: LANGUAGE",
        "step_2": "✦ STEP 2 OF 3: CONCIERGE ACCESS",
        "step_3": "✦ STEP 3 OF 3: NAME & DATE OF BIRTH",
        "header": "Concierge Access",
        "subtitle": "Welcome. Present your key to step inside.",
        "signin": "Sign In",
        "create": "Create Luxury Key",
        "email": "Email ID",
        "pin": "4-Digit Access PIN",
        "pin2": "Confirm PIN",
        "btn_signin": "Sign In",
        "btn_create": "Create Key",
        "forgot": "Forgot PIN?",
        "back": "← Back",
        "footer": "🔒 Your PIN is stored only as a salted hash.",
        "err_throttled": "Too many attempts. Please wait a few minutes and try again.",
        "err_email": "Please enter a valid email address.",
        "err_pin": "The access PIN must be exactly 4 digits.",
        "err_match": "The two PINs do not match.",
        "err_exists": "This email already holds a Luxury Key. Please sign in instead.",
        "err_locked": "This key is temporarily locked after repeated attempts. Please try again in a few minutes.",
        "err_bad": "Email or PIN not recognised.",
        "rec_h": "Recover Your Key",
        "rec_sub": "Enter your registered email. We verify it is you before you set a new PIN.",
        "rec_send": "Send Verification Code",
        "rec_sent": "A 4-digit verification code has been sent to your email.",
        "rec_demo": "Demo mode: no email service is configured, so your verification code is shown here.",
        "rec_code": "4-Digit Verification Code",
        "rec_verify": "Verify Code",
        "rec_resend": "Resend code",
        "rec_newpin": "New 4-Digit PIN",
        "rec_newpin2": "Confirm New PIN",
        "rec_save": "Save New PIN",
        "rec_back": "← Back to Sign In",
        "rec_ok": "Your PIN has been reset. Please sign in with your new PIN.",
        "err_norec": "No Luxury Key found for this email.",
        "err_code": "That code is incorrect.",
        "err_expired": "This code has expired. Please request a new one.",
        "err_send": "We could not send the email. Please try again later.",
        "err_off": "PIN recovery is not available right now.",
        "cal_h": "Name & Date of Birth",
        "cal_sub": "Your birth details power your astrological readings, circadian lighting, and strategic action plan in Inner Voice.",
        "cal_btn": "Initialize AuraSync",
    },
    "Tamil (தமிழ்)": {
        "tagline": "ஆடம்பர சூழல் நுண்ணறிவு",
        "step_1": "✦ படி 1 / 3: மொழி",
        "step_2": "✦ படி 2 / 3: வரவேற்பு அறை அனுமதி",
        "step_3": "✦ படி 3 / 3: பெயர் & பிறந்த தேதி",
        "header": "வரவேற்பு அறை அனுமதி",
        "subtitle": "வணக்கம். உள்ளே செல்ல உங்கள் சாவியைப் பயன்படுத்தவும்.",
        "signin": "உள்நுழைவு",
        "create": "புதிய சாவி உருவாக்குக",
        "email": "மின்னஞ்சல் முகவரி",
        "pin": "4-இலக்க அணுகல் PIN",
        "pin2": "PIN-ஐ உறுதிசெய்க",
        "btn_signin": "உள்நுழைக",
        "btn_create": "சாவி உருவாக்குக",
        "forgot": "PIN-ஐ மீட்டெடுக்க",
        "back": "← பின்செல்",
        "footer": "🔒 உங்கள் PIN பாதுகாப்பாக குறியாக்கம் செய்யப்பட்டுள்ளது.",
        "err_throttled": "அதிக முயற்சிகள். சில நிமிடங்கள் காத்திருந்து மீண்டும் முயலவும்.",
        "err_email": "சரியான மின்னஞ்சல் முகவரியை உள்ளிடவும்.",
        "err_pin": "அணுகல் PIN சரியாக 4 இலக்கங்களாக இருக்க வேண்டும்.",
        "err_match": "இரண்டு PIN-களும் பொருந்தவில்லை.",
        "err_exists": "இந்த மின்னஞ்சலுக்கு ஏற்கனவே சாவி உள்ளது. தயவுசெய்து உள்நுழையவும்.",
        "err_locked": "தொடர்ச்சியான முயற்சிகளுக்குப் பிறகு இந்த சாவி தற்காலிகமாகப் பூட்டப்பட்டுள்ளது. சில நிமிடங்கள் கழித்து முயலவும்.",
        "err_bad": "மின்னஞ்சல் அல்லது PIN அடையாளம் காணப்படவில்லை.",
        "rec_h": "சாவியை மீட்டெடுக்க",
        "rec_sub": "பதிவு செய்த மின்னஞ்சலை உள்ளிடவும். புதிய PIN அமைக்கும் முன் நீங்கள்தான் என்பதை சரிபார்ப்போம்.",
        "rec_send": "சரிபார்ப்புக் குறியீட்டை அனுப்புக",
        "rec_sent": "4-இலக்க சரிபார்ப்புக் குறியீடு உங்கள் மின்னஞ்சலுக்கு அனுப்பப்பட்டது.",
        "rec_demo": "டெமோ பயன்முறை: மின்னஞ்சல் சேவை அமைக்கப்படவில்லை, எனவே உங்கள் சரிபார்ப்புக் குறியீடு இங்கே காட்டப்படுகிறது.",
        "rec_code": "4-இலக்க சரிபார்ப்புக் குறியீடு",
        "rec_verify": "குறியீட்டைச் சரிபார்க்க",
        "rec_resend": "குறியீட்டை மீண்டும் அனுப்புக",
        "rec_newpin": "புதிய 4-இலக்க PIN",
        "rec_newpin2": "புதிய PIN-ஐ உறுதிசெய்க",
        "rec_save": "புதிய PIN-ஐ சேமிக்க",
        "rec_back": "← உள்நுழைவுக்குத் திரும்பு",
        "rec_ok": "உங்கள் PIN மீட்டமைக்கப்பட்டது. புதிய PIN மூலம் உள்நுழையவும்.",
        "err_norec": "இந்த மின்னஞ்சலுக்கு சாவி எதுவும் இல்லை.",
        "err_code": "குறியீடு தவறானது.",
        "err_expired": "இந்தக் குறியீடு காலாவதியாகிவிட்டது. புதியதைக் கோரவும்.",
        "err_send": "மின்னஞ்சலை அனுப்ப முடியவில்லை. பிறகு முயலவும்.",
        "err_off": "PIN மீட்பு தற்போது கிடைக்கவில்லை.",
        "cal_h": "பெயர் & பிறந்த தேதி",
        "cal_sub": "உங்கள் பிறப்பு விவரங்கள், இன்னர் வாய்ஸில் உங்கள் ஜோதிட வாசிப்புகள், சர்க்கேடியன் ஒளியமைப்பு மற்றும் செயல்திட்டத்தை இயக்குகின்றன.",
        "cal_btn": "AuraSync-ஐ தொடங்கு",
    },
}

# Step 1 is shown before a language exists, so its copy is deliberately bilingual and is never machine-translated.
GATE_PINNED = {
    "lang_h": "Choose Your Language / உங்கள் மொழியைத் தேர்ந்தெடுக்கவும்",
    "lang_sub": "Every screen, label and message will follow your choice. / ஒவ்வொரு திரையும் உங்கள் தேர்வைப் பின்பற்றும்.",
    "lang_label": "Language / மொழி",
    "lang_btn": "Continue / அடுத்த படி ➔",
}
for _pin_txt in GATE_PINNED.values():          # (not "_s": that name is the degrees-sine helper used by the chart maths)
    _PINNED.add(_pin_txt)
    _PINNED.add(EDGE_RE.match(_pin_txt).group(2))
del _pin_txt


def gate_lang():
    g = st.session_state.get("lang")
    return g if g in LANGS else "English"


def gt(key):
    """Gate string in the chosen language (English / Tamil hand-written; others via the translation layer)."""
    row = GATE_I18N.get(gate_lang())
    if row and key in row:
        return row[key]
    return GATE_I18N["English"][key]




for _n, _d in (("gate_fail", {}),):
    if not hasattr(_REG, _n):
        setattr(_REG, _n, _d)
if not hasattr(_REG, "users_lock"):
    _REG.users_lock = threading.Lock()
if not hasattr(_REG, "users_ok"):
    _REG.users_ok = True


# ---- local persistent store (aurasync_users.json) ---------------------------------------------
# PERSISTENCE NOTE: on Streamlit Community Cloud the container disk is EPHEMERAL, so this JSON file is wiped on every
# redeploy / reboot / long sleep. Users (and their trusted-device tokens) then disappear and have to sign in again.
# Point AURASYNC_USERS at a persistent volume to avoid that, or swap users_load()/users_save() for a persistent
# backend (a database such as Postgres/Supabase/Firestore, or a secrets-backed store). They are the only two
# functions that touch storage, so no other code has to change. Anything that cannot be loaded falls back to the
# normal sign-in page.
def users_path():
    env = os.environ.get("AURASYNC_USERS")
    if env:
        return env
    try:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), USERS_FILE)
    except NameError:
        return USERS_FILE


def users_load():
    try:
        with open(users_path(), encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    if not isinstance(data.get("users"), dict):
        data["users"] = {}
    data.setdefault("version", 1)
    return data


def users_save(data):
    path = users_path()
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        return True
    except OSError:
        return False


def users_set_meta(**kw):
    """Top-level keys of aurasync_users.json next to "users" (active_email, signed_out)."""
    with _REG.users_lock:
        data = users_load()
        data.update(kw)
        _REG.users_ok = users_save(data)


def mark_active(email):
    """Created a key / signed in / finished calibration: remember this user server-side and in the address bar."""
    users_set_meta(active_email=email, signed_out=False)
    try:
        st.query_params["u"] = email
    except Exception:
        pass


def users_update(fn):
    """Read-modify-write under a lock; fn receives the users dict and may return a value."""
    with _REG.users_lock:
        data = users_load()
        result = fn(data["users"])
        _REG.users_ok = users_save(data)
        return result


def hash_pin(pin, salt_hex):
    return hashlib.pbkdf2_hmac("sha256", str(pin).encode("utf-8"), bytes.fromhex(salt_hex), 120000).hex()


def device_hash(token):
    return hashlib.sha256(str(token).encode("utf-8")).hexdigest()


def profile_to_json(p):
    d = dict(p)
    d["dob"] = p["dob"].isoformat()
    return d


def profile_from_json(d):
    try:
        p = dict(d)
        p["dob"] = date.fromisoformat(p["dob"])
        for k in ("name", "pob", "tob", "h", "m", "ap"):
            if k not in p:
                return None
        return p
    except Exception:
        return None


# ---- throttling + account operations ------------------------------------------------------------
def gate_throttled():
    key, now = _client_key(), time.time()
    if len(_REG.gate_fail) > 500:
        _REG.gate_fail.clear()
    recent = [x for x in _REG.gate_fail.get(key, []) if now - x < LOCK_SECONDS]
    _REG.gate_fail[key] = recent
    return len(recent) >= 12


def gate_note_fail():
    _REG.gate_fail.setdefault(_client_key(), []).append(time.time())


def create_user(email, pin):
    lang = st.session_state.get("lang", "English")
    salt = pysecrets.token_hex(16)
    pin_hash = hash_pin(pin, salt)

    def op(users):
        if email in users:
            return "exists"
        users[email] = {"salt": salt, "pin_hash": pin_hash, "created": time.time(), "lang": lang,
                        "profile": None, "devices": [], "fails": 0, "locked_until": 0}
        return "ok"
    return users_update(op)


def verify_user(email, pin):
    """-> 'ok' | 'bad' | 'locked'"""
    def op(users):
        u = users.get(email)
        now = time.time()
        if not u:
            hash_pin(pin, "00" * 16)                      # same cost whether or not the account exists
            return "bad"
        if u.get("locked_until", 0) > now:
            return "locked"
        if hmac.compare_digest(hash_pin(pin, u["salt"]), str(u.get("pin_hash", ""))):
            u["fails"], u["locked_until"] = 0, 0
            return "ok"
        u["fails"] = u.get("fails", 0) + 1
        if u["fails"] >= MAX_PIN_FAILS:
            u["fails"], u["locked_until"] = 0, now + LOCK_SECONDS
        return "bad"
    return users_update(op)


def load_user_into_session(email, u):
    ss = st.session_state
    ss.auth_email = email
    lang = u.get("lang")
    if lang in LANGS:
        ss["lang"] = lang
        ss.gate_lang = lang
    prof = profile_from_json(u.get("profile")) if u.get("profile") else None
    if prof:
        ss.profile = prof
    prefs = u.get("prefs") if isinstance(u.get("prefs"), dict) else {}
    if prefs.get("theme") in ("dark", "light") and "theme_choice" not in ss:
        ss["theme_choice"] = prefs["theme"]
    home = u.get("home") if isinstance(u.get("home"), dict) else None
    ss["_home_saved"] = home
    if home and "fleet" in ss:                   # an earlier anonymous run built the defaults: rebuild from the account
        del ss["fleet"]


def issue_device_token(email):
    ss = st.session_state
    tok = pysecrets.token_urlsafe(32)
    h = device_hash(tok)

    def op(users):
        u = users.get(email)
        if u:
            keep = [d for d in u.get("devices", []) if time.time() - d.get("ts", 0) < COOKIE_DAYS * 86400]
            keep.append({"h": h, "ts": time.time()})
            u["devices"] = keep[-5:]
    users_update(op)
    ss.device_token = tok
    ss.pending_cookie = tok
    ss.pending_cookie_runs = 2
    if not _REG.users_ok:
        ss.flash = "Could not save your profile to disk, so you may need to sign in again after a restart."


def finish_login():
    ss = st.session_state
    ss.authenticated = True
    mark_active(ss.auth_email)
    issue_device_token(ss.auth_email)


def gate_enter(email):
    """After a verified sign-in / new key: resume where onboarding stopped."""
    ss = st.session_state
    u = users_load()["users"].get(email) or {}
    load_user_into_session(email, u)
    mark_active(email)
    if ss.get("profile"):
        finish_login()
    else:
        ss.onboarding_step = 3


# ---- "this device" cookie ----------------------------------------------------------------------
def cookie_token():
    try:
        v = st.context.cookies.get(COOKIE_NAME)
        return v if isinstance(v, str) and re.fullmatch(r"[A-Za-z0-9_\-]{20,80}", v) else None
    except Exception:
        return None


def cookie_script(token, clear=False):
    """Write (or clear) the device token in BOTH a first-party cookie (180 days, Path=/, SameSite=Lax, Secure on
    https) AND localStorage. Phones and home-screen apps sometimes drop one of the two, so both are kept."""
    age = 0 if clear else COOKIE_DAYS * 86400
    val = "" if clear else token
    store = ("w.localStorage.removeItem(N);w.sessionStorage.removeItem('aura_restore');" if clear
             else "w.localStorage.setItem(N,V);")
    return ("<script>(function(){var N='" + COOKIE_NAME + "',V='" + val + "',A=" + str(age) + ",w=window.parent;"
            "try{void w.document.cookie;}catch(e){w=window;}"
            "try{var s=w.location.protocol==='https:'?'; Secure':'';"
            "w.document.cookie=N+'='+V+'; Max-Age='+A+'; Path=/; SameSite=Lax'+s;}catch(e){}"
            "try{" + store + "}catch(e){}})();</script>")


def restore_script():
    """Cookie missing but localStorage still holds the token (home-screen launch, cookie evicted): put the cookie
    back and reload once, so the server sees it on the new session and signs the user in. A sessionStorage flag
    makes sure this can never loop."""
    return ("<script>(function(){try{var N='" + COOKIE_NAME + "',w=window.parent;var t=w.localStorage.getItem(N)||'';"
            "var has=(w.document.cookie||'').split(';').some(function(c){c=c.trim();return c.indexOf(N+'=')===0&&c.length>N.length+1;});"
            "if(has){w.sessionStorage.removeItem('aura_restore');return;}"
            "if(!/^[A-Za-z0-9_-]{20,80}$/.test(t)||w.sessionStorage.getItem('aura_restore')==='1')return;"
            "w.sessionStorage.setItem('aura_restore','1');"
            "var s=w.location.protocol==='https:'?'; Secure':'';"
            "w.document.cookie=N+'='+t+'; Max-Age=" + str(COOKIE_DAYS * 86400) + "; Path=/; SameSite=Lax'+s;"
            "w.location.reload();}catch(e){}})();</script>")


def try_cookie_login():
    ss = st.session_state
    if ss.get("authenticated") or ss.get("_cookie_tried"):
        return
    ss._cookie_tried = True
    tok = cookie_token()
    if not tok:
        return
    h, now = device_hash(tok), time.time()
    for email, u in users_load()["users"].items():
        for d in u.get("devices", []):
            if hmac.compare_digest(str(d.get("h", "")), h) and now - d.get("ts", 0) < COOKIE_DAYS * 86400:
                load_user_into_session(email, u)
                if ss.get("profile"):
                    ss.authenticated = True
                    ss.device_token = tok
                    ss.pending_cookie, ss.pending_cookie_runs = tok, 2     # re-stamp cookie + localStorage: sliding 180 days
                    if now - d.get("ts", 0) > 3600:                         # refresh the server-side expiry (at most hourly)
                        def touch(users, email=email, h=h):
                            for dev in (users.get(email) or {}).get("devices", []):
                                if hmac.compare_digest(str(dev.get("h", "")), h):
                                    dev["ts"] = time.time()
                        users_update(touch)
                return


def try_auto_login():
    """Server-side auto-login for WebView shells that wipe cookies / localStorage on exit.
    Order: ?u=<email> -> the last active user stored in aurasync_users.json -> the only registered user.
    SECURITY: this identifies the user WITHOUT a PIN, so it is meant for a private, single-owner deployment.
    Set AURASYNC_AUTOLOGIN=0 to switch it off on a public URL. Sign Out sets signed_out=True and disables it."""
    ss = st.session_state
    if ss.get("authenticated") or os.environ.get("AURASYNC_AUTOLOGIN", "1").strip() == "0":
        return
    try:
        q_user = st.query_params.get("u")
    except Exception:
        q_user = None
    data = users_load()
    users = data.get("users", {})
    if not users or data.get("signed_out", False):
        return
    target_email = None
    if q_user and q_user in users:
        target_email = q_user
    elif data.get("active_email") and data["active_email"] in users:
        target_email = data["active_email"]
    elif len(users) == 1:
        target_email = next(iter(users.keys()))
    if target_email:
        u = users[target_email]
        load_user_into_session(target_email, u)
        if ss.get("profile"):
            ss.authenticated = True
            ss.auth_email = target_email
            try:
                st.query_params["u"] = target_email
            except Exception:
                pass


def forget_device(email, tokens):
    hashes = [device_hash(t_) for t_ in tokens if t_]
    if not (email and hashes):
        return

    def op(users):
        u = users.get(email)
        if u:
            u["devices"] = [d for d in u.get("devices", [])
                            if not any(hmac.compare_digest(str(d.get("h", "")), h) for h in hashes)]
    users_update(op)


def do_sign_out():
    """Switch profile: forget this device, wipe every per-user session value, return to Step 1."""
    ss = st.session_state
    forget_device(ss.get("auth_email"), (ss.get("device_token"), cookie_token()))
    users_set_meta(active_email=None, signed_out=True)          # stops try_auto_login until the next sign-in
    try:
        st.query_params.clear()
    except Exception:
        pass
    lang = ss.get("lang", "English")
    for k in list(ss.keys()):
        try:
            del ss[k]
        except Exception:
            pass
    ss["gate_lang"] = lang
    ss["clear_cookie_runs"] = 2


def do_delete_account():
    """Permanently remove the signed-in user's record (email, PIN hash, birth details, devices), then sign out."""
    ss = st.session_state
    email = ss.get("auth_email")
    if not email or not ss.get("del_acct_ok"):
        return
    try:
        users_update(lambda users: users.pop(email, None))
    except Exception:
        pass
    do_sign_out()


def sync_user_record():
    """Keep aurasync_users.json in step with profile / language edits made inside the dashboard."""
    ss = st.session_state
    email = ss.get("auth_email")
    if not email:
        return
    prof, lang = ss.get("profile"), ss.get("lang", "English")
    ss.gate_lang = lang
    pj = profile_to_json(prof) if prof else None
    theme = ss.get("theme_choice") if ss.get("theme_choice") in ("dark", "light") else None
    hj = home_to_json()
    sig = json.dumps([pj, lang, theme, hj], sort_keys=True, default=str)
    if sig == ss.get("_user_sig"):
        return
    ss._user_sig = sig

    def op(users):
        u = users.get(email)
        if u:
            u["lang"], u["profile"] = lang, pj
            if theme:
                u.setdefault("prefs", {})["theme"] = theme
            if hj is not None:
                u["home"] = hj
    users_update(op)


# ---- styling (obsidian glass + champagne gold) ---------------------------------------------------------
GATE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Playfair+Display:wght@400;500&display=swap');
:root { color-scheme: dark; }
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] { background-color: #090A0E !important; }
.stApp { background-image: radial-gradient(ellipse at 50% -5%, rgba(229,195,120,0.10), transparent 62%),
         radial-gradient(ellipse at 100% 100%, rgba(229,195,120,0.05), transparent 55%) !important; font-family: 'Inter', sans-serif; }
[data-testid="stHeader"], [data-testid="stBottom"] > div { background: transparent !important; }
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"],
[data-testid="stExpandSidebarButton"] { display: none !important; }
.block-container { padding-top: 5vh !important; max-width: 1100px; }
.stApp p, .stApp li, .stApp label, [data-testid="stWidgetLabel"] p, [data-testid="stMarkdownContainer"] p { color: #F1ECDF; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * { color: #9E9A8E !important; text-align: center; }
/* brand + progress */
.gate-brand { text-align: center; font-family: 'Playfair Display', serif; font-size: 2.1rem; letter-spacing: .18em; color: #E5C378; text-shadow: 0 0 28px rgba(229,195,120,.35); }
.gate-tag { text-align: center; letter-spacing: .38em; font-size: .62rem; color: #9E9A8E; margin: .3rem 0 0 0; }
.gate-step { text-align: center; letter-spacing: .3em; font-size: .68rem; color: #E5C378; margin: 1.5rem 0 .6rem 0; }
.gate-dots { display: flex; justify-content: center; gap: 8px; margin-bottom: 1rem; }
.gate-dots span { width: 28px; height: 3px; border-radius: 2px; background: rgba(229,195,120,.2); }
.gate-dots span.on { background: #E5C378; box-shadow: 0 0 10px rgba(229,195,120,.6); }
.gate-h { font-family: 'Playfair Display', serif; font-size: 1.5rem; color: #E5C378; text-align: center; margin-bottom: .2rem; }
.gate-sub { color: #9E9A8E; font-size: .86rem; text-align: center; margin-bottom: 1.1rem; }
/* the glass card */
.st-key-gate_card { background: rgba(18, 21, 28, 0.85); border: 1px solid rgba(229, 195, 120, 0.32); border-radius: 22px;
  padding: 1.6rem 1.7rem 1.4rem 1.7rem; backdrop-filter: blur(14px);
  box-shadow: 0 18px 60px rgba(0, 0, 0, 0.65), 0 0 40px rgba(229, 195, 120, 0.08); }
[data-testid="stForm"] { border: 0 !important; padding: 0 !important; background: transparent !important; }
[data-testid="stWidgetLabel"] p { color: #9E9A8E !important; font-size: .78rem !important; letter-spacing: .06em; text-transform: uppercase; }
.st-key-gate_card strong { color: #E5C378; letter-spacing: .06em; font-weight: 500; }
/* text inputs: dark container, champagne text, centred */
[data-baseweb="input"], [data-baseweb="base-input"] { background-color: #12151C !important; border-radius: 12px !important; }
[data-baseweb="input"] { border: 1px solid rgba(229, 195, 120, 0.28) !important; min-height: 48px; box-shadow: 0 4px 18px rgba(0, 0, 0, 0.45); transition: all .3s ease; }
[data-baseweb="input"]:hover, [data-baseweb="input"]:focus-within { border-color: rgba(229, 195, 120, 0.65) !important; box-shadow: 0 0 14px rgba(229, 195, 120, 0.2); }
input { color: #F1ECDF !important; -webkit-text-fill-color: #F1ECDF !important; background: transparent !important; text-align: center !important;
  font-size: .98rem !important; letter-spacing: .04em; caret-color: #E5C378; }
input::placeholder { color: #6F6A5C !important; -webkit-text-fill-color: #6F6A5C !important; opacity: 1; }
input[type="password"] { letter-spacing: .45em; }
input:-webkit-autofill, input:-webkit-autofill:focus { -webkit-box-shadow: 0 0 0 1000px #12151C inset !important; -webkit-text-fill-color: #F1ECDF !important; caret-color: #E5C378; }
[data-testid="stTextInput"] button { background: transparent !important; color: #E5C378 !important; border: 0 !important; }
[data-testid="stTextInput"] button svg { fill: #E5C378 !important; }
/* dropdowns: same high-contrast treatment as the dashboard, no white boxes */
[data-baseweb="select"] * { background-color: transparent !important; }
div[data-baseweb="select"] > div { background-color: #12151C !important; border: 1px solid rgba(229, 195, 120, 0.28) !important; border-radius: 12px !important;
  min-height: 48px !important; display: flex !important; align-items: center !important; padding: 0 14px !important;
  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.45) !important; transition: all .3s ease !important; }
div[data-baseweb="select"] > div:hover, div[data-baseweb="select"] > div:focus-within { border-color: rgba(229, 195, 120, 0.65) !important; box-shadow: 0 0 14px rgba(229, 195, 120, 0.2) !important; }
div[data-baseweb="select"] div, div[data-baseweb="select"] span, div[data-baseweb="select"] input { color: #F1ECDF !important; -webkit-text-fill-color: #F1ECDF !important;
  font-family: 'Inter', sans-serif !important; font-size: .95rem !important; letter-spacing: .03em !important; display: flex !important; align-items: center !important; }
div[data-baseweb="select"] > div > div:first-child { justify-content: center !important; text-align: center !important; }
div[data-baseweb="select"] svg { fill: #E5C378 !important; width: 18px !important; height: 18px !important; opacity: .85 !important; }
div[data-baseweb="popover"], div[data-baseweb="popover"] > div, div[data-baseweb="menu"], ul[role="listbox"] {
  background-color: #12151C !important; border: 1px solid rgba(229, 195, 120, 0.3) !important; border-radius: 12px !important; box-shadow: 0 12px 32px rgba(0, 0, 0, 0.7) !important; }
div[data-baseweb="popover"] *, div[data-baseweb="menu"] *, ul[role="listbox"] * { color: #F1ECDF !important; -webkit-text-fill-color: #F1ECDF !important; }
div[data-baseweb="popover"] li, ul[role="listbox"] li, li[role="option"] { background-color: transparent !important; padding: 10px 14px !important; font-size: .92rem !important; justify-content: center; text-align: center; }
div[data-baseweb="popover"] li:hover, ul[role="listbox"] li:hover, li[role="option"]:hover, li[aria-selected="true"] { background-color: rgba(229, 195, 120, 0.2) !important; }
div[data-baseweb="popover"] li:hover *, li[role="option"]:hover *, li[aria-selected="true"] * { color: #E5C378 !important; -webkit-text-fill-color: #E5C378 !important; }
/* sign-in / create switch */
div[role="radiogroup"] { gap: .5rem; flex-wrap: wrap; justify-content: center; margin-bottom: .6rem; }
div[role="radiogroup"] > label { border: 1px solid rgba(229, 195, 120, 0.3); border-radius: 999px; padding: .38rem 1.2rem; background: rgba(255,255,255,.03); cursor: pointer; transition: all .25s; }
div[role="radiogroup"] > label:hover { box-shadow: 0 0 16px rgba(229, 195, 120, 0.3); }
div[role="radiogroup"] > label > div:first-child { display: none; }
div[role="radiogroup"] > label:has(input:checked) { background: linear-gradient(135deg, #EACB86, #C9A24A); box-shadow: 0 0 20px rgba(229, 195, 120, 0.4); }
div[role="radiogroup"] > label:has(input:checked) * { color: #141414 !important; font-weight: 600; }
/* buttons */
.stButton > button, .stFormSubmitButton > button { background: transparent; color: #E5C378; border: 1px solid rgba(229, 195, 120, 0.55); border-radius: 12px; min-height: 46px; letter-spacing: .06em; transition: all .25s; }
.stButton > button:hover, .stFormSubmitButton > button:hover { border-color: #E5C378; box-shadow: 0 0 20px rgba(229, 195, 120, 0.35); color: #F1ECDF; }
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"], button[kind="primary"], button[kind="primaryFormSubmit"] {
  background: linear-gradient(135deg, #EACB86, #C9A24A) !important; color: #141414 !important; border: 0 !important; font-weight: 600; text-transform: uppercase; letter-spacing: .1em; }
[data-testid="stBaseButton-primary"]:hover, [data-testid="stBaseButton-primaryFormSubmit"]:hover, button[kind="primary"]:hover, button[kind="primaryFormSubmit"]:hover { box-shadow: 0 0 26px rgba(229, 195, 120, 0.55); color: #141414 !important; }
.stButton button p, .stFormSubmitButton button p { color: inherit !important; }
/* FIX 1 - hide Streamlit's "Press Enter to submit form / apply" helper text on every input (gate + app, both themes).
   Primary test-id plus fallbacks for other Streamlit versions. Errors (stAlert) and the password eye button are untouched. */
[data-testid="InputInstructions"],
div[data-testid="InputInstructions"],
[data-testid="stTextInput"] [data-testid="InputInstructions"],
[data-testid="stTextArea"] [data-testid="InputInstructions"],
[data-testid="stNumberInput"] [data-testid="InputInstructions"],
[data-testid="stForm"] [data-testid*="nstructions"],
[data-testid="stTextInput"] [class*="InputInstructions"],
[data-testid="stTextInput"] [class*="WidgetInstructions"],
[data-baseweb="input"] [class*="nstructions"],
[data-baseweb="base-input"] [class*="nstructions"] {
    display: none !important;
    visibility: hidden !important;
}
/* quiet text-link buttons (forgot PIN / back / resend) */
.st-key-gate_forgot button, .st-key-gate_rec_resend button, .st-key-gate_back2 button, .st-key-gate_back3 button, .st-key-gate_rec_back button {
  background: transparent !important; border: 0 !important; box-shadow: none !important; min-height: 34px; font-size: .8rem; color: #9E9A8E !important; text-transform: none; letter-spacing: .04em; }
.st-key-gate_forgot button { text-decoration: underline; text-underline-offset: 3px; }
.st-key-gate_forgot button:hover, .st-key-gate_rec_resend button:hover, .st-key-gate_back2 button:hover, .st-key-gate_back3 button:hover, .st-key-gate_rec_back button:hover { color: #E5C378 !important; box-shadow: none !important; }
.gate-code { text-align: center; font-family: 'Playfair Display', serif; font-size: 2rem; letter-spacing: .5em; padding-left: .5em; color: #E5C378; margin: .2rem 0 .8rem 0; text-shadow: 0 0 22px rgba(229,195,120,.35); }
.gate-tag.ta, .gate-step.ta { letter-spacing: .06em; }
/* messages */
[data-testid="stAlert"] { background-color: rgba(229, 195, 120, 0.08) !important; border: 1px solid rgba(229, 195, 120, 0.4); border-radius: 12px; }
[data-testid="stAlert"] *, [data-testid="stSpinner"] * { color: #F1ECDF !important; }
/* suppress the floating "Press Enter to submit form" watermark during onboarding */
div[data-testid="InputInstructions"],
div[data-testid="InputInstructions"] *,
span:has(> kbd),
.stTextInput small,
.stNumberInput small,
div:has(> kbd),
[class*="InputInstructions"],
[class*="WidgetInstructions"] {
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    height: 0 !important;
    font-size: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    pointer-events: none !important;
}
</style>
"""


# ---- PIN recovery (verification code -> new PIN) --------------------------------------------------------------
RESET_TTL = 600          # a verification code lives 10 minutes
RESET_TRIES = 5          # wrong guesses before the code is burned


def smtp_settings():
    """Real e-mail delivery is used when AURASYNC_SMTP_HOST is set (plus _PORT, _USER, _PASS, _FROM)."""
    host = os.environ.get("AURASYNC_SMTP_HOST", "").strip()
    if not host:
        return None
    user = os.environ.get("AURASYNC_SMTP_USER", "").strip()
    try:
        port = int(os.environ.get("AURASYNC_SMTP_PORT", "587"))
    except ValueError:
        port = 587
    return {"host": host, "port": port, "user": user, "pw": os.environ.get("AURASYNC_SMTP_PASS", ""),
            "sender": os.environ.get("AURASYNC_SMTP_FROM", "").strip() or user}


def recovery_mode():
    """'email' (real delivery) | 'demo' (code shown on screen) | 'off'."""
    if smtp_settings():
        return "email"
    return "off" if os.environ.get("AURASYNC_RECOVERY_DEMO", "1").strip() == "0" else "demo"


def send_reset_email(to, code):
    cfg = smtp_settings()
    if not cfg:
        return False
    try:
        import smtplib
        from email.message import EmailMessage
        msg = EmailMessage()
        msg["Subject"] = "AuraSync verification code"
        msg["From"], msg["To"] = cfg["sender"], to
        msg.set_content("Your AuraSync verification code is " + code + ".\nIt expires in " + str(RESET_TTL // 60) +
                        " minutes. If you did not ask to reset your PIN, you can ignore this email.")
        if cfg["port"] == 465:
            srv = smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=12)
        else:
            srv = smtplib.SMTP(cfg["host"], cfg["port"], timeout=12)
            srv.starttls()
        with srv:
            if cfg["user"]:
                srv.login(cfg["user"], cfg["pw"])
            srv.send_message(msg)
        return True
    except Exception:
        return False


def reset_request(email):
    """Create a one-time code for this account. Only a salted hash of the code is stored. -> code | None"""
    code = "%04d" % pysecrets.randbelow(10000)
    salt = pysecrets.token_hex(16)
    h = hash_pin(code, salt)

    def op(users):
        u = users.get(email)
        if not u:
            return False
        u["reset"] = {"salt": salt, "h": h, "exp": time.time() + RESET_TTL, "tries": 0}
        return True
    return code if users_update(op) else None


def reset_verify(email, code):
    """-> 'ok' | 'bad' | 'expired'  (a correct code is single-use)"""
    def op(users):
        u = users.get(email)
        r = u.get("reset") if u else None
        if not r:
            return "expired"
        if r.get("exp", 0) < time.time():
            u.pop("reset", None)
            return "expired"
        r["tries"] = r.get("tries", 0) + 1
        if hmac.compare_digest(hash_pin(code, r["salt"]), str(r.get("h", ""))):
            u.pop("reset", None)
            return "ok"
        if r["tries"] >= RESET_TRIES:
            u.pop("reset", None)
            return "expired"
        return "bad"
    return users_update(op)


def reset_set_pin(email, pin):
    """Replace the salted PIN hash, clear lockouts and sign every remembered device out."""
    salt = pysecrets.token_hex(16)
    h = hash_pin(pin, salt)

    def op(users):
        u = users.get(email)
        if not u:
            return False
        u.update(salt=salt, pin_hash=h, fails=0, locked_until=0, devices=[])
        u.pop("reset", None)
        return True
    return users_update(op)


# ---- the three steps -----------------------------------------------------------------------------------------
def cb_gate_lang():
    ss = st.session_state
    ss.gate_lang = ss.get("lang", "English")
    email = ss.get("auth_email")
    if email:
        lang = ss.gate_lang
        users_update(lambda users: users[email].update(lang=lang) if email in users else None)


def cb_gate_continue():
    ss = st.session_state
    ss.gate_lang = ss.get("lang", "English")      # "lang" is a widget key that only exists on Step 1
    ss.onboarding_step = 2
    ss.gate_view = "access"


def cb_gate_back():
    ss = st.session_state
    if ss.get("onboarding_step", 1) >= 3:
        ss.auth_email = None
        ss.onboarding_step = 2
    else:
        ss.onboarding_step = 1
    ss.gate_view = "access"


def cb_rec_open():
    ss = st.session_state
    ss.gate_view, ss.rec_stage = "recover", 1
    for k in ("rec_email", "rec_demo_code", "rec_verified"):
        ss.pop(k, None)


def cb_rec_close():
    ss = st.session_state
    ss.gate_view = "access"
    for k in ("rec_stage", "rec_email", "rec_demo_code", "rec_verified"):
        ss.pop(k, None)


def gate_step1():
    """STEP 1: the Language gate."""
    st.markdown('<div class="gate-h">' + html.escape(GATE_PINNED["lang_h"]) + '</div>'
                '<div class="gate-sub">' + html.escape(GATE_PINNED["lang_sub"]) + '</div>', unsafe_allow_html=True)
    st.selectbox(GATE_PINNED["lang_label"], LANGS, key="lang", on_change=cb_gate_lang)
    st.button(GATE_PINNED["lang_btn"], key="gate_next1", type="primary", on_click=cb_gate_continue,
              width='stretch')


def gate_recover():
    """Sub-view of Step 2: e-mail -> verification code -> new PIN."""
    ss = st.session_state
    st.markdown('<div class="gate-h">' + html.escape(gt("rec_h")) + '</div>'
                '<div class="gate-sub">' + html.escape(gt("rec_sub")) + '</div>', unsafe_allow_html=True)
    mode = recovery_mode()
    stage = ss.get("rec_stage", 1)
    if stage >= 2 and not ss.get("rec_email"):
        stage = ss.rec_stage = 1
    if stage == 3 and ss.get("rec_verified") != ss.get("rec_email"):
        stage = ss.rec_stage = 2
    if mode == "off":
        st.error(gt("err_off"))
    elif stage == 1:
        with st.form("gate_rec1"):
            email = st.text_input(gt("email"), key="rec_email_in")
            go = st.form_submit_button(gt("rec_send"), type="primary", width='stretch')
        if go:
            em = (email or "").strip().lower()
            if gate_throttled():
                st.error(gt("err_throttled"))
            elif not EMAIL_RX.match(em):
                st.error(gt("err_email"))
            else:
                gate_note_fail()                         # every request counts toward the throttle
                code = reset_request(em)
                if code is None:
                    st.error(gt("err_norec"))
                elif mode == "email" and not send_reset_email(em, code):
                    st.error(gt("err_send"))
                else:
                    ss.rec_email, ss.rec_stage = em, 2
                    if mode == "demo":
                        ss.rec_demo_code = code
                    st.rerun()
    elif stage == 2:
        if mode == "demo" and ss.get("rec_demo_code"):
            st.info(gt("rec_demo"))
            st.markdown('<div class="gate-code" translate="no">' + html.escape(ss.rec_demo_code) + '</div>',
                        unsafe_allow_html=True)
        else:
            st.info(gt("rec_sent"))
        with st.form("gate_rec2"):
            code_in = st.text_input(gt("rec_code"), max_chars=4, key="rec_code_in", placeholder="••••")
            go = st.form_submit_button(gt("rec_verify"), type="primary", width='stretch')
        if go:
            if gate_throttled():
                st.error(gt("err_throttled"))
            elif not PIN_RX.match((code_in or "").strip()):
                st.error(gt("err_code"))
            else:
                res = reset_verify(ss.rec_email, code_in.strip())
                if res == "ok":
                    ss.rec_verified, ss.rec_stage = ss.rec_email, 3
                    st.rerun()
                gate_note_fail()
                st.error(gt("err_expired") if res == "expired" else gt("err_code"))
        if st.button(gt("rec_resend"), key="gate_rec_resend", width='stretch'):
            if gate_throttled():
                st.error(gt("err_throttled"))
            else:
                gate_note_fail()
                code = reset_request(ss.rec_email)
                if code and mode == "email" and not send_reset_email(ss.rec_email, code):
                    st.error(gt("err_send"))
                elif code:
                    ss.rec_demo_code = code if mode == "demo" else None
                    st.rerun()
    else:
        with st.form("gate_rec3"):
            p1 = st.text_input(gt("rec_newpin"), type="password", max_chars=4, key="rec_pin1", placeholder="••••")
            p2 = st.text_input(gt("rec_newpin2"), type="password", max_chars=4, key="rec_pin2", placeholder="••••")
            go = st.form_submit_button(gt("rec_save"), type="primary", width='stretch')
        if go:
            if not PIN_RX.match(p1 or ""):
                st.error(gt("err_pin"))
            elif p1 != p2:
                st.error(gt("err_match"))
            elif reset_set_pin(ss.rec_email, p1):
                cb_rec_close()
                ss.gate_mode = "signin"
                ss.gate_notice = gt("rec_ok")
                st.rerun()
            else:
                st.error(gt("err_norec"))
    st.button(gt("rec_back"), key="gate_rec_back", on_click=cb_rec_close, width='stretch')


def gate_step2():
    """STEP 2: Concierge Access (sign in / create key / forgot PIN)."""
    ss = st.session_state
    if ss.get("gate_view") == "recover":
        gate_recover()
        return
    st.markdown('<div class="gate-h">' + html.escape(gt("header")) + '</div>'
                '<div class="gate-sub">' + html.escape(gt("subtitle")) + '</div>', unsafe_allow_html=True)
    notice = ss.pop("gate_notice", None)
    if notice:
        st.success(notice)
    mode = st.radio("Access", ["signin", "create"], horizontal=True, key="gate_mode", label_visibility="collapsed",
                    format_func=lambda m: gt("signin") if m == "signin" else gt("create"))
    with st.form("gate_access"):
        email = st.text_input(gt("email"), key="gate_email")
        pin = st.text_input(gt("pin"), type="password", max_chars=4, key="gate_pin", placeholder="••••")
        pin2 = (st.text_input(gt("pin2"), type="password", max_chars=4, key="gate_pin2", placeholder="••••")
                if mode == "create" else None)
        go = st.form_submit_button(gt("btn_create") if mode == "create" else gt("btn_signin"), type="primary",
                                   width='stretch')
    if mode == "signin":
        st.button(gt("forgot"), key="gate_forgot", on_click=cb_rec_open, width='stretch')
    if go:
        em = (email or "").strip().lower()
        if gate_throttled():
            st.error(gt("err_throttled"))
        elif not EMAIL_RX.match(em):
            st.error(gt("err_email"))
        elif not PIN_RX.match(pin or ""):
            st.error(gt("err_pin"))
        elif mode == "create":
            if pin != pin2:
                st.error(gt("err_match"))
            elif create_user(em, pin) == "exists":
                st.error(gt("err_exists"))
            else:
                ss.auth_email = em
                mark_active(em)
                ss.onboarding_step = 3
                st.rerun()
        else:
            res = verify_user(em, pin)
            if res == "ok":
                gate_enter(em)
                st.rerun()
            elif res == "locked":
                st.error(gt("err_locked"))
            else:
                gate_note_fail()
                st.error(gt("err_bad"))
    st.caption(gt("footer"))
    st.button(gt("back"), key="gate_back2", on_click=cb_gate_back, width='stretch')


def gate_step3():
    """STEP 3: Chrono & Biorhythm Calibration (Inner Voice profile)."""
    ss = st.session_state
    p = ss.get("profile") or {}
    dob0 = p.get("dob", date(1995, 1, 1))
    st.markdown('<div class="gate-h">' + html.escape(gt("cal_h")) + '</div>'
                '<div class="gate-sub">' + html.escape(gt("cal_sub")) + '</div>', unsafe_allow_html=True)
    with st.form("gate_calibration"):
        name = st.text_input(t("name"), value=p.get("name", ""), key="gate_name")
        st.markdown("**" + t("dob") + "**")
        d1, d2, d3 = st.columns(3)
        dday = d1.selectbox(t("day"), list(range(1, 32)), index=dob0.day - 1, key="gate_day")
        dmon = d2.selectbox(t("month"), list(range(1, 13)), index=dob0.month - 1, key="gate_mon",
                            format_func=lambda m: MONTHS[m - 1])
        dyear = d3.selectbox(t("year"), list(range(1940, 2041)), index=min(max(dob0.year, 1940), 2040) - 1940, key="gate_year")
        st.markdown("**" + t("tob") + "**")
        t1, t2, t3 = st.columns(3)
        hr = t1.selectbox(t("hour"), list(range(1, 13)), index=int(p.get("h", 6)) - 1, key="gate_h")
        mn = t2.selectbox(t("minute"), list(range(0, 60)), index=int(p.get("m", 0)), key="gate_m",
                          format_func=lambda x: str(x).zfill(2))
        ap = t3.selectbox("AM / PM", ["AM", "PM"], index=0 if p.get("ap", "AM") == "AM" else 1, key="gate_ap")
        pob = st.text_input(t("pob"), value=p.get("pob", ""), key="gate_pob")
        go = st.form_submit_button(gt("cal_btn"), type="primary", width='stretch')
    st.button(gt("back"), key="gate_back3", on_click=cb_gate_back, width='stretch')
    if go:
        if not name.strip() or not pob.strip():
            st.warning(t("need_fields"))
            return
        dob = date(dyear, dmon, min(dday, calendar.monthrange(dyear, dmon)[1]))
        prof = {"name": name.strip()[:80], "dob": dob, "pob": pob.strip()[:80],
                "tob": str(hr).zfill(2) + ":" + str(mn).zfill(2) + " " + ap, "h": hr, "m": mn, "ap": ap}
        email = ss.auth_email
        pj = profile_to_json(prof)
        users_update(lambda users: users[email].update(profile=pj, lang=ss.get("lang", "English")) if email in users else None)
        ss.profile = prof                       # same shape the dashboard's own profile form writes
        ss.editing, ss.chat, ss.chimed, ss.last_topic = False, [], False, None
        finish_login()                          # authenticated = True + device cookie token
        st.rerun()


def render_onboarding_gate():
    ss = st.session_state
    install_i18n()
    st.markdown(GATE_CSS, unsafe_allow_html=True)
    if is_light():
        st.markdown(light_dd_css(), unsafe_allow_html=True)      # FIX 3: gate dropdowns in the light palette
    ss.gate_lang = ss.get("lang", "English")                    # FIX 4: mirror the language on every gate run
    code = lang_code()
    if code and mt_available() and not ss.get("i18n_ok_" + code):
        with st.spinner(t("i18n_wait")):
            ss["i18n_ok_" + code] = bool(i18n_prefetch())
    if ss.get("clear_cookie_runs", 0) > 0:
        components.html(cookie_script("", clear=True), height=0)
        ss.clear_cookie_runs -= 1
    elif not ss.get("auth_email"):
        components.html(restore_script(), height=0)             # FIX 2: localStorage -> cookie -> auto sign-in
    step = ss.get("onboarding_step", 1)
    if step not in (1, 2, 3):
        step = ss.onboarding_step = 1
    if step == 3 and not ss.get("auth_email"):          # calibration only after a verified / new key
        step = ss.onboarding_step = 2
    _, mid, _ = st.columns([1, 1.55, 1])
    with mid:
        ta = " ta" if gate_lang() != "English" else ""
        st.markdown('<div class="gate-brand">✨ <span translate="no">AuraSync</span></div>'
                    '<div class="gate-tag' + ta + '">' + html.escape(gt("tagline")) + '</div>', unsafe_allow_html=True)
        st.markdown('<div class="gate-step' + ta + '">' + html.escape(gt("step_" + str(step))) + '</div><div class="gate-dots">' +
                    "".join('<span class="on"></span>' if i <= step else "<span></span>" for i in (1, 2, 3)) + "</div>",
                    unsafe_allow_html=True)
        try:
            card = st.container(key="gate_card")
        except TypeError:
            card = st.container()
        with card:
            {1: gate_step1, 2: gate_step2, 3: gate_step3}[step]()


# ---- wiring ---------------------------------------------------------------------------------------------------------
def init_gate_state():
    ss = st.session_state
    if "authenticated" not in ss:
        ss.authenticated = False
    if "onboarding_step" not in ss:
        ss.onboarding_step = 1
    if "auth_email" not in ss:
        ss.auth_email = None
    if "lang" not in ss:                         # survives the gate even though "lang" is a sidebar widget key
        g = ss.get("gate_lang")
        ss["lang"] = g if g in LANGS else "English"
    ss.selected_lang = ss["lang"] if ss.get("lang") in LANGS else "English"
    if ss.get("lang") in LANGS:                  # mirror so widget cleanup can never lose the chosen language
        ss.gate_lang = ss["lang"]


def is_automation_link():
    """?mode=...&token=... voice-automation links keep working exactly as before (the token is checked inside)."""
    try:
        return "mode" in st.query_params and "token" in st.query_params
    except Exception:
        return False


def gate_post_dashboard():
    ss = st.session_state
    if not ss.get("authenticated"):
        return
    with st.sidebar:
        st.divider()
        st.markdown('<div style="font-size:.74rem;opacity:.7;letter-spacing:.04em">🔐 <span translate="no">' +
                    html.escape(str(ss.get("auth_email") or "")) + "</span></div>", unsafe_allow_html=True)
        st.button("Sign Out / Switch Profile", key="aura_sign_out", on_click=do_sign_out, width='stretch')
        with st.expander("🗑 Delete my account"):
            st.caption("Permanently deletes your account: email, PIN, birth details and saved settings. This cannot be undone.")
            st.checkbox("I understand this cannot be undone", key="del_acct_ok")
            st.button("Delete my account permanently", key="del_acct_btn", on_click=do_delete_account,
                      disabled=not st.session_state.get("del_acct_ok"), width='stretch')
    sync_user_record()
    if ss.get("pending_cookie") and ss.get("pending_cookie_runs", 0) > 0:
        components.html(cookie_script(ss.pending_cookie), height=0)
        ss.pending_cookie_runs -= 1


def main():
    ss = st.session_state
    init_gate_state()
    if not ss.authenticated:
        try_cookie_login()
    if not ss.authenticated:
        try_auto_login()
    if ss.authenticated or is_automation_link():
        render_main_dashboard()
        gate_post_dashboard()
    else:
        render_onboarding_gate()


main()
