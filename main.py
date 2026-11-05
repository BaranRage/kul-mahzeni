#!/usr/bin/env python3
"""Kül Mahzeni — kasvetli 8-bit roguelike: Prenses Öykü'yü kurtar, bekçileri kes,
onun istediği eşyaları getir. Başta silah seçilir (Kılıç, Yay, Balyoz, Yumruk),
her silahın üç yeteneği vardır.

Kontroller (yalnızca klavye):
  WASD / ok tuşları : hareket (menülerde seçim)
  J / X             : saldır, seç, konuş
  K / L / I         : yetenekler (I: ulti)
  Boşluk            : atılma (atılırken hasar almazsın)
  Esc               : duraklatma menüsü
  M                 : sesi aç/kapat     F11: tam ekran
  R                 : ölünce silah seçimine dön
"""
import math
import os
import random
import sys
from array import array
from collections import deque

# Hyprland pencere kuralları için sınıf adı
os.environ.setdefault("SDL_VIDEO_WAYLAND_WMCLASS", "kul-mahzeni")
os.environ.setdefault("SDL_VIDEO_X11_WMCLASS", "kul-mahzeni")

import pygame

# --- Temel ayarlar -----------------------------------------------------------
W, H = 320, 180          # iç çözünürlük (8-bit görünüm için düşük)
TILE = 16
COLS, ROWS = 20, 10      # oda: 320x160, altta 20 px HUD
WORLD_H = ROWS * TILE
FPS = 60

PLAYER_SPEED = 78
PLAYER_HP = 5
DASH_SPEED = 250
DASH_TIME = 0.14
DASH_COOLDOWN = 0.55
ATTACK_TIME = 0.16
ATTACK_COOLDOWN = 0.30
INVULN_TIME = 1.0

GHOUL_SPEED = 32
LUNGE_SPEED = 150
WISP_SPEED = 30
BOLT_SPEED = 72

IRIS_TIME = 0.45

# Kat yapısı: 1-3 dövüş, 4 sunak, 5-6 dövüş, 7 bekçi; sonra Öykü'nün sığınağı
FLOOR_LEN = 7
REST_IDX = (4,)

# --- Hikâye: Prenses Öykü --------------------------------------------------------
OYKU_PAL = {
    "y": (250, 210, 90), "h": (150, 80, 50), "s": (250, 214, 186), "e": (50, 30, 50),
    "m": (220, 100, 120), "d": (214, 100, 150), "D": (250, 170, 205), "w": (255, 245, 250),
    "k": (70, 34, 48),
}
OYKU = [
    "....y.y.y...",
    "...kyyyyyk..",
    "..khhhhhhhk.",
    "..khssssshk.",
    "..khseseshk.",
    "..khssmsshk.",
    ".khhhssshhhk",
    ".khhDDDDDhhk",
    ".khdDwwDdhhk",
    "..kdDDDDDdk.",
    "..kddDDDddk.",
    ".kddddDdddk.",
    ".kdddDDDdddk",
    "kdddDDDDdddk",
    "kddddddddddk",
    "kDdDdDdDdDdk",
    ".kkkkkkkkkk.",
]

# Öykü'nün istediği eşyalar — her biri bir katın bekçisinde
ITEMS = [
    {"name": "Ay Çiçeği", "pal": {"w": (235, 240, 255), "b": (150, 170, 255), "g": (80, 160, 90),
                                  "y": (255, 230, 120)},
     "icon": ["...w.w...", "..wbwbw..", ".wbbybbw.", "..wbwbw..", "...wgw...",
              "....g....", "..g.g....", "...gg....", "....g...."]},
    {"name": "Gümüş Tarak", "pal": {"w": (240, 240, 250), "s": (170, 175, 190), "p": (220, 120, 170),
                                    "k": (60, 60, 70)},
     "icon": [".........", ".sssssss.", "swwpwwwws", "swwwwwwws", "sssssssss",
              "s.s.s.s.s", "s.s.s.s.s", "s.s.s.s.s", "........."]},
    {"name": "Yıldız Kutusu", "pal": {"y": (255, 220, 110), "o": (200, 130, 60), "b": (90, 70, 160),
                                      "w": (255, 255, 230)},
     "icon": ["....w....", "...wyw...", "....w....", ".ooooooo.", ".obbbbbo.",
              ".obwbybo.", ".obbbbbo.", ".ooooooo.", "........."]},
]

BOSS_NAMES = ["KÜL BEKÇİSİ", "KOR BEKÇİSİ", "GÖLGE BEKÇİSİ", "KALBİ SÖNMÜŞ BEKÇİ"]
BOSS_TINTS = [(0, 0, 0), (40, 0, -10), (-10, -6, 30), (30, -10, 20)]

DIALOG_RESCUE = [
    "Kim var orada?.. Bekçinin ayak sesleri sustu.",
    "Sen... beni kurtarmaya mı geldin? Adım Öykü.",
    "Yıllardır bu mahzenin kül kokusunu soluyorum.",
    "Burası, bana kalan son ışık. Burada güvendesin.",
    "Derinlerde karanlıkta parlayan bir Ay Çiçeği açarmış.",
    "Onu bana getirirsen bu yere biraz daha renk gelir. Lütfen...",
]
DIALOG_DELIVER = [
    ["Ay Çiçeği! Ne kadar güzel parlıyor...",
     "Al, bu kutsama yolunu aydınlatsın. (Can +1, yaraların sarıldı)",
     "Annemin Gümüş Tarağı da aşağıda bir yerde kaldı.",
     "Bir sonraki bekçi onu saklıyor. Bulur musun?"],
    ["Annemin tarağı... hâlâ ılık.",
     "Kutsamam seninle. (Can +1, yaraların sarıldı)",
     "Son bir şey kaldı: en dipte bir Yıldız Kutusu var.",
     "Çalınca gökyüzünü hatırlatırmış. Onu duymak istiyorum."],
    ["Bu melodi... gökyüzü! Gerçekten gökyüzü!",
     "Mahzenin laneti çözülüyor. Kül diniyor.",
     "Teşekkür ederim. Sen benim kahramanımsın."],
]
DIALOG_IDLE = [
    "Dikkatli ol, aşağısı daha da karanlık.",
    "Biraz dinlen. Yaralarını ben sararım.",
    "Bekçiler hep daha güçlü dönüyor... ama sen de öyle.",
    "Sen gidince burası çok sessiz oluyor. Çabuk dön.",
    "Getirdiklerine bakıyorum da, burası artık evime benziyor.",
    "Yolda bir tüccar görürsen ona güvenme. Ama külünü de esirgeme.",
]

# Kat ortasındaki anı odaları: Öykü'nün geçmişinden aydınlık bir görüntü ve bir seçim
MEMORIES = [
    {"title": "AY BAHÇESİ", "sub": "kime ait olduğunu bilmediğin bir anı", "speaker": "Bir yankı",
     "lines": ["Annem derdi ki: Ay Çiçeği yalnızca karanlıkta açar.",
               "O yüzden burayı seviyorum. Kimse bakmazken parlıyor.",
               "Sen gerçekten burada değilsin, değil mi? Yalnızca bir yankısın.",
               "Söyle bana, bu çiçeği ne yapayım?"],
     "choices": [("Toprağa dik, kök salsın", "kul_kalbi", "Kök salan kalır. Kalbin de öyle olsun."),
                 ("Bana ver, ben taşırım", "kul_ruzgari", "Hafif bir çiçek, hafif bir yol. Koş o halde.")]},
    {"title": "KULE ODASI", "sub": "kül yağmadan önceki son sabah", "speaker": "Küçük Öykü",
     "lines": ["Annem saçımı tarardı, ben de pencereden kapıyı izlerdim.",
               "Bir gün o kapı kapandı ve kül yağmaya başladı.",
               "Ona kızgın mıyım, onu özlüyor muyum, bilmiyorum.",
               "Sen olsan ne yapardın?"],
     "choices": [("Kapıyı kırardım", "kor_kilic", "Öfke de bir ateştir. Silahına yakışır."),
                 ("Beklerdim", "cevik_bilek", "Sabır da bir ustalık. Ellerin hızlansın.")]},
    {"title": "YILDIZ ÇATISI", "sub": "gökyüzünün son görüldüğü yer", "speaker": "Küçük Öykü",
     "lines": ["Çocukken buraya çıkar, yıldızları sayardım.",
               "Kutuyu kurunca gökyüzü küçülür, avucuma sığardı.",
               "Sonra gökyüzünü unuttum. Yalnızca adı kaldı.",
               "Sence hangisi daha çok acıtır: hatırlamak mı, unutmak mı?"],
     "choices": [("Hatırlamak", "kan_emen", "Acıyan yer canlıdır. Yaran sana güç versin."),
                 ("Unutmak", "golge_adim", "Unutmak gölgede yürümektir. Onların içinden geç.")]},
]

# Yolda duyulan sesler: (konuşan, satırlar)
VOICE_REST = ("Uzak bir ses", ["Biri mi var orada?.. Yoksa yine rüzgâr mı?",
                               "Bekçiyi geçebilen olursa... lütfen, aşağıdayım."])
VOICE_BOSS = {
    2: ("Öykü'nün sesi", ["Kor kokusu buraya kadar geliyor. Sakın yanma.",
                          "Tarağı getirmesen de olur. Sen dön, yeter."]),
    3: ("Öykü'nün sesi", ["Orası çok karanlık. Sesimi duyuyorsan yürümeye devam et.",
                          "Gölge senden korkuyor. Ben biliyorum."]),
}
GOD_MODE = os.environ.get("KUL_GOD") == "1"   # yalnızca otomatik test için

# Sınırlı, kasvetli palet
PAL = {
    "k": (10, 8, 14),      # kontur
    "c": (44, 38, 60),     # pelerin koyu
    "C": (76, 68, 98),     # pelerin açık
    "e": (240, 80, 60),    # kor gibi gözler
    "r": (112, 28, 40),    # kan kırmızısı kuşak
    "g": (58, 54, 62),     # kül grisi koyu
    "G": (96, 90, 100),    # kül grisi açık
}
FIRE_PAL = {
    "y": (150, 40, 30),
    "Y": (235, 110, 50),
    "O": (255, 205, 100),
    "W": (255, 245, 210),
    "k": (40, 8, 10),
}
ICON_PAL = {
    "w": (235, 230, 240), "y": (255, 200, 90), "o": (230, 110, 50), "r": (200, 40, 50),
    "R": (120, 20, 30), "g": (120, 112, 130), "b": (150, 140, 210), "k": (20, 16, 26),
}

PLAYER_BODY = [
    "....kkkk....",
    "...kCCCCk...",
    "..kCCccCCk..",
    "..kCkkkkCk..",
    "..kCkekeCk..",
    "..kCkkkkCk..",
    "..kcCCCCck..",
    ".kccCrrCcck.",
    "kcccCrrCccck",
    "kccCCCCCCcck",
    ".kcccccccck.",
    ".kcccccccck.",
]
PLAYER_LEGS = [
    ["..kck..kck..", "..kk....kk.."],
    ["...kck.kck..", "...kk...kk.."],
]

# Kül hortlağı: kambur, küllerden yoğrulmuş, kor gözlü
GHOUL_BODY = [
    "....kkkk....",
    "...kGGGGk...",
    "..kGGggGGk..",
    "..kgekkegk..",
    "..kgkkkkgk..",
    "...kgggGk...",
    "..kGgggGGk..",
    ".kGgkgggGgk.",
    "kGgk.kggkgGk",
    "kgk..kgggkgk",
    ".k...kgggk.k",
]
GHOUL_LEGS = [
    ["....kgkgk...", "....kk.kk..."],
    ["...kgk.kgk..", "...kk...kk.."],
]
GHOUL_EYES = [(4, 3), (7, 3)]

# Kor ruhu: havada süzülen, yüzü olan alev
WISP_FRAMES = [
    [
        "....y.....",
        "...yY.....",
        "...yYy....",
        "..yYOYy...",
        ".yYOOOYy..",
        ".yOWOWOy..",
        "yOkOOOkOy.",
        "yOOOOOOOy.",
        "yOOkkkOOy.",
        ".yOOOOOy..",
        "..yYOYy...",
        "...yyy....",
    ],
    [
        ".....y....",
        ".....Yy...",
        "....yYy...",
        "...yYOYy..",
        "..yYOOOYy.",
        ".yOWOWOOy.",
        "yOkOOOkOy.",
        "yOOOOOOOy.",
        "yOOkkkOOy.",
        ".yOOOOOy..",
        "..yYOYy...",
        "...yyy....",
    ],
]

HEART = [".kk.kk.", "krrkrrk", "krrrrrk", ".krrrk.", "..krk..", "...k..."]

# 4x4 Bayer matrisi — ışıkta 8-bit tarzı titreme deseni
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]

# --- Armağanlar ------------------------------------------------------------------
BOONS = {
    "kor_kilic": {
        "name": "Kor Çelik", "desc": ["Silah hasarı +1"], "max": 3,
        "icon": ["........w", ".......wy", "......wy.", ".....wy..", "o...wy...",
                 ".o.wy....", "..oy.....", ".ok.o....", "ok......."],
    },
    "cevik_bilek": {
        "name": "Çevik Bilek", "desc": ["Bekleme -%20,", "yetenekte -%12"], "max": 3,
        "icon": ["y...y....", ".y...y...", "..y...y..", "...y...y.", "....y...y",
                 "...y...y.", "..y...y..", ".y...y...", "y...y...."],
    },
    "genis_yay": {
        "name": "Geniş Erim", "desc": ["Saldırı menzili", "+%25"], "max": 2,
        "icon": ["...www...", ".ww...ww.", "w.......w", "w...y...w", "....y....",
                 "...yoy...", "....o....", "....o....", "....k...."],
    },
    "kul_kalbi": {
        "name": "Kül Kalbi", "desc": ["En yüksek can +1", "ve 1 can yenile"], "max": 4,
        "icon": [".rr...rr.", "rRRr.rRRr", "rRRRrRRRr", "rRRRRRRRr", ".rRRRRRr.",
                 "..rRRRr..", "...rRr...", "....r....", "........."],
    },
    "kan_emen": {
        "name": "Kan Emen Çelik", "desc": ["Öldürünce %25", "şansla 1 can"], "max": 3,
        "icon": ["....r....", "....r....", "...rRr...", "...rRr...", "..rRRRr..",
                 ".rRRRRRr.", ".rRwRRRr.", "..rRRRr..", "...rrr..."],
    },
    "golge_adim": {
        "name": "Gölge Adım", "desc": ["Atılırken içinden", "geçtiğini keser"], "max": 2,
        "icon": [".....bbb.", "....bwwb.", "....bwwb.", "g..bbbbb.", ".g.bbbbbb",
                 "g..bbbbb.", "..g.bbb..", "g...b.b..", "....b.b.."],
    },
    "kor_pelerin": {
        "name": "Kor Pelerin", "desc": ["Hasar alınca", "kor patlaması"], "max": 2,
        "icon": ["o...y...o", ".o..y..o.", "..o.o.o..", "...yoy...", "yyoo.ooyy",
                 "...yoy...", "..o.o.o..", ".o..y..o.", "o...y...o"],
    },
    "kul_ruzgari": {
        "name": "Kül Rüzgârı", "desc": ["Hız +%15, atılma", "beklemesi -%25"], "max": 3,
        "icon": ["gggggg...", "......g..", ".gggg..g.", "......g..", "wwwwwww..",
                 "........w", ".wwwww..w", ".......w.", "ggggg...."],
    },
    "t_kalp": {
        "name": "Tansi Kalbi", "desc": ["En yüksek can +2", "ve tam şifa"], "max": 2, "rare": True,
        "icon": [".yy...yy.", "yrRy.yrRy", "yrRRyRRry", "yrRRRRRry", ".yrRRRry.",
                 "..yrRry..", "...yry...", "....y....", "........."],
    },
    "t_guc": {
        "name": "Tansi Bileyi", "desc": ["Silah hasarı +2"], "max": 2, "rare": True,
        "icon": ["........y", ".......yw", "......yw.", ".....yw..", "y...yw...",
                 ".y.yw....", "..yw.....", ".yk.y....", "yk......."],
    },
    "t_hiz": {
        "name": "Tansi Çizmesi", "desc": ["Hız +%25, atılma", "beklemesi -%30"], "max": 2, "rare": True,
        "icon": ["...yyy...", "...yoy...", "...yoy...", "...yoy...", "...yooyy.",
                 "...yoooy.", "..yyyyyy.", "y.y.y....", "........."],
    },
    "t_kalkan": {
        "name": "Tansi Kalkanı", "desc": ["Her odaya 1 darbe", "emen kalkanla gir"], "max": 2, "rare": True,
        "icon": [".yyyyyyy.", "ygggggggy", "ygwggggy.", "ygwgggggy", "ygggggggy",
                 ".ygggggy.", "..ygggy..", "...ygy...", "....y...."],
    },
    "kanat_tozu": {
        "name": "Kanat Tozu", "desc": ["Hasar +1, hız +%10"], "max": 9, "rare": True,
        "icon": ["b.......b", "bb.....bb", "bwb.k.bwb", "bbbbkbbbb", ".bbbkbbb.",
                 "..bbkbb..", ".bb.k.bb.", ".b.....b.", "........."],
    },
    "boyut_kalbi": {
        "name": "Boyut Kalbi", "desc": ["En yüksek can +2", "ve tam şifa"], "max": 9, "rare": True,
        "icon": [".bb...bb.", "bwwb.bwwb", "bwwwbwwwb", "bwwwwwwwb", ".bwwwwwb.",
                 "..bwwwb..", "...bwb...", "....b....", "........."],
    },
    "kelebek_isini": {
        "name": "Kelebek Işını", "desc": ["Yeni yetenek: O tuşu", "delici ışın dizisi"], "max": 1, "rare": True,
        "icon": ["b.......b", "bb.....bb", "bbb.w.bbb", ".bbwwwbb.", "wwwwwwwww",
                 ".bbwwwbb.", "bbb.w.bbb", "bb.....bb", "b.......b"],
    },
    "boyut_ruhu": {
        "name": "Boyut Ruhu", "desc": ["Yetenek beklemeleri", "-%25"], "max": 9, "rare": True,
        "icon": ["..bbbbb..", ".b.....b.", "b..www..b", "b.w.b.w.b", "b.wbwbw.b",
                 "b.w.b.w.b", "b..www..b", ".b.....b.", "..bbbbb.."],
    },
    "sifa": {
        "name": "Kor Şifası", "desc": ["2 can yenile"], "max": 99,
        "icon": [".rr...rr.", "rRRr.rRRr", "rRRRwRRRr", "rRRwwwRRr", ".rRRwRRr.",
                 "..rRRRr..", "...rRr...", "....r....", "........."],
    },
}


# --- Ses: tamamen kodla üretilen 8-bit efektler ---------------------------------
def _tone(rate, dur, f0=0.0, f1=None, wave="sq", vol=0.4, noise=0.0, lp=(1.0, 1.0),
          decay=2.0, vib=0.0, attack=0.004):
    f1 = f0 if f1 is None else f1
    n = int(rate * dur)
    out, ph, y = [], 0.0, 0.0
    rnd = random.Random(int(f0 * 7 + dur * 1000))
    for i in range(n):
        p = i / n
        f = f0 + (f1 - f0) * p
        if vib:
            f *= 1 + 0.06 * math.sin(i / rate * math.tau * vib)
        ph = (ph + f / rate) % 1.0
        if wave == "sq":
            s = 1.0 if ph < 0.5 else -1.0
        elif wave == "tri":
            s = 4 * abs(ph - 0.5) - 1
        else:
            s = 0.0
        if noise:
            s = s * (1 - noise) + rnd.uniform(-1, 1) * noise
        a = lp[0] + (lp[1] - lp[0]) * p
        y += a * (s - y)
        env = (1 - p) ** decay * min(1.0, i / (rate * attack))
        out.append(y * env * vol)
    return out


def _music(rate):
    """8 sn'lik kesintisiz döngü: kasvetli drone + çan arpeji."""
    dur = 8
    n = rate * dur
    out = [0.0] * n
    tau = math.tau
    for i in range(n):
        t = i / rate
        a = (t * 55) % 1.0
        b = (t * 55.25) % 1.0
        c = (t * 82.5) % 1.0
        d = (4 * abs(a - 0.5) - 1) + (4 * abs(b - 0.5) - 1) + 0.5 * (4 * abs(c - 0.5) - 1)
        out[i] = 0.07 * d * (0.75 + 0.25 * math.sin(tau * t / 8))
    notes = [(0.0, 220.0), (1.0, 261.63), (2.0, 329.63), (3.0, 311.13),
             (4.0, 220.0), (5.0, 196.0), (6.0, 261.63), (7.0, 246.94)]
    for start, f in notes:
        s0 = int(start * rate)
        for j in range(int(rate * 1.4)):
            env = math.exp(-j / rate * 3.2)
            v = env * (0.075 * math.sin(tau * f * j / rate) + 0.025 * math.sin(tau * 2.01 * f * j / rate))
            out[(s0 + j) % n] += v
    return out


def _boss_music(rate):
    """4 sn'lik döngü, 120 vuruş: davul, kare dalga bas, gerilim."""
    n = rate * 4
    out = [0.0] * n
    tau = math.tau
    bass = [55, 55, 65.41, 55, 82.41, 55, 77.78, 73.42,
            55, 55, 65.41, 55, 98.0, 92.5, 82.41, 77.78]
    step = n // 16
    rnd = random.Random(3)
    for k, f in enumerate(bass):
        ph, y = 0.0, 0.0
        for j in range(step):
            ph = (ph + f / rate) % 1.0
            s = 1.0 if ph < 0.5 else -1.0
            y += 0.08 * (s - y)
            out[k * step + j] += 0.16 * y * (1 - j / step) ** 0.5
    for beat in range(8):  # davul
        s0 = beat * (n // 8)
        ph = 0.0
        for j in range(int(rate * 0.18)):
            f = 120 * math.exp(-j / rate * 18) + 40
            ph += f / rate
            out[(s0 + j) % n] += 0.35 * math.sin(tau * ph) * math.exp(-j / rate * 14)
        if beat % 2:  # trampet benzeri gürültü
            for j in range(int(rate * 0.1)):
                out[(s0 + j) % n] += 0.12 * rnd.uniform(-1, 1) * math.exp(-j / rate * 30)
    for i in range(n):  # yüksek, gergin drone
        t = i / rate
        out[i] += 0.03 * math.sin(tau * 220.0 * t) * (0.5 + 0.5 * math.sin(tau * t / 2))
        out[i] += 0.02 * math.sin(tau * 233.08 * t) * (0.5 - 0.5 * math.sin(tau * t / 2))
    return out


def _haven_music(rate):
    """8 sn'lik sıcak, majör bir döngü — Öykü'nün sığınağı."""
    n = rate * 8
    out = [0.0] * n
    tau = math.tau
    chords = [(261.63, 329.63, 392.0), (220.0, 261.63, 329.63),
              (174.61, 220.0, 261.63), (196.0, 246.94, 293.66)]
    for c, chord in enumerate(chords):
        base = c * (n // 4)
        for k in range(8):  # yumuşak arp
            f = chord[k % 3] * (2 if k >= 4 else 1)
            s0 = base + k * (n // 32)
            for j in range(int(rate * 0.6)):
                env = math.exp(-j / rate * 5)
                ph = (f * j / rate) % 1.0
                out[(s0 + j) % n] += 0.06 * env * (4 * abs(ph - 0.5) - 1)
        for j in range(n // 4):  # pad
            t = j / rate
            env = min(1.0, t * 4, (n // 4 - j) / rate * 4)
            out[base + j] += 0.025 * env * (math.sin(tau * chord[0] / 2 * t) + math.sin(tau * chord[2] / 2 * t))
    return out


class Sfx:
    def __init__(self):
        self.ok = False
        self.muted = False
        self.music_vol = 0.7
        self.sfx_vol = 0.8
        self.duck = False
        self.current = None
        self.sounds = {}
        self.music = None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 512)
            freq, fmt, ch = pygame.mixer.get_init()
            if fmt != -16:
                return
        except pygame.error:
            return
        self.ch = ch
        r = freq
        defs = {
            "slash": _tone(r, 0.13, noise=1.0, lp=(0.55, 0.06), vol=0.32, decay=1.4),
            "hit": _tone(r, 0.12, 170, 50, noise=0.4, lp=(0.5, 0.5), vol=0.45),
            "kill": _tone(r, 0.42, 220, 30, noise=0.6, lp=(0.45, 0.04), vol=0.45, decay=1.4),
            "hurt": _tone(r, 0.32, 420, 90, vib=30, lp=(0.6, 0.6), vol=0.4, decay=1.0),
            "dash": _tone(r, 0.16, noise=1.0, lp=(0.04, 0.5), vol=0.22, decay=1.0),
            "shoot": _tone(r, 0.2, 280, 700, wave="tri", noise=0.2, vol=0.28),
            "fizzle": _tone(r, 0.15, noise=1.0, lp=(0.25, 0.05), vol=0.2),
            "door": _tone(r, 0.75, 52, 36, noise=0.7, lp=(0.07, 0.05), vol=0.6, decay=0.8),
            "spawn": _tone(r, 0.45, 90, 40, noise=0.8, lp=(0.02, 0.15), vol=0.25, decay=0.6, attack=0.2),
            "select": _tone(r, 0.04, 880, wave="sq", lp=(0.4, 0.4), vol=0.12, decay=1.0),
            "pick": sum((_tone(r, 0.075, f, wave="sq", lp=(0.45, 0.45), vol=0.22, decay=1.0)
                         for f in (392, 523.25, 659.25, 783.99)), [])
            + _tone(r, 0.35, 1046.5, wave="tri", vol=0.25, decay=2.5),
            "heal": sum((_tone(r, 0.09, f, wave="tri", vol=0.3, decay=1.0)
                         for f in (523.25, 659.25, 783.99, 1046.5)), []),
            "dead": _tone(r, 1.4, 220, 40, wave="sq", noise=0.3, lp=(0.3, 0.03), vol=0.45, decay=1.0, vib=6),
            "roar": _tone(r, 1.3, 95, 55, wave="sq", noise=0.55, lp=(0.12, 0.05), vol=0.6, decay=0.9,
                          vib=11, attack=0.15),
            "slam": _tone(r, 0.6, 70, 25, wave="sq", noise=0.6, lp=(0.3, 0.03), vol=0.7, decay=1.3),
            "boom": _tone(r, 1.2, 60, 20, wave="sq", noise=0.8, lp=(0.4, 0.02), vol=0.75, decay=1.1),
            "scare": _tone(r, 1.1, 700, 2600, wave="sq", noise=0.85, lp=(0.9, 0.9), vol=0.95, decay=0.5) +
                     _tone(r, 1.1, 90, 60, wave="sq", noise=0.4, lp=(0.3, 0.3), vol=0.6, decay=0.4),
            "charge": _tone(r, 0.5, 120, 300, wave="sq", noise=0.5, lp=(0.1, 0.3), vol=0.35, decay=0.8),
            "talk": _tone(r, 0.03, 660, wave="tri", vol=0.12, decay=1.0),
            "bow": _tone(r, 0.14, 520, 180, wave="tri", noise=0.25, lp=(0.6, 0.2), vol=0.3, decay=2.2),
            "punch": _tone(r, 0.08, 140, 60, wave="sq", noise=0.6, lp=(0.35, 0.1), vol=0.4, decay=1.6),
            "item": sum((_tone(r, 0.1, f, wave="tri", vol=0.3, decay=0.8)
                         for f in (659.25, 783.99, 987.77, 1318.5)), [])
            + _tone(r, 0.6, 1567.98, wave="tri", vol=0.25, decay=2.0, vib=5),
        }
        for k, v in defs.items():
            self.sounds[k] = self._make(v)
        self.musics = {"calm": self._make(_music(r)), "boss": self._make(_boss_music(r)),
                       "haven": self._make(_haven_music(r))}
        self.current = None
        self.ok = True

    def _make(self, samples):
        buf = array("h", (int(max(-1.0, min(1.0, s)) * 32767) for s in samples))
        if self.ch == 2:
            st = array("h", [0]) * (len(buf) * 2)
            st[0::2] = buf
            st[1::2] = buf
            buf = st
        return pygame.mixer.Sound(buffer=buf.tobytes())

    def play(self, name, vol=1.0):
        if self.ok and not self.muted:
            s = self.sounds[name]
            s.set_volume(min(1.0, vol * self.sfx_vol))
            s.play()

    def start_music(self, name="calm"):
        if not self.ok or self.current == name:
            return
        if self.current:
            self.musics[self.current].fadeout(400)
        self.current = name
        if name:
            m = self.musics[name]
            m.set_volume(self.music_level())
            m.play(loops=-1, fade_ms=600)

    def toggle(self):
        self.muted = not self.muted
        if self.ok and self.current:
            self.musics[self.current].set_volume(self.music_level())

    def music_level(self):
        if self.muted:
            return 0.0
        return 0.55 * self.music_vol * (0.35 if self.duck else 1.0)

    def set_levels(self, music, sfx, duck=None):
        self.music_vol, self.sfx_vol = music / 10, sfx / 10
        if duck is not None:
            self.duck = duck
        if self.ok and self.current:
            self.musics[self.current].set_volume(self.music_level())


# --- Çizim yardımcıları ------------------------------------------------------
def sprite_from_rows(rows, pal=PAL):
    w = max(len(r) for r in rows)
    surf = pygame.Surface((w, len(rows)), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch in pal:
                surf.set_at((x, y), pal[ch])
    return surf


def build_frames(body_rows, legs_list, pal=PAL):
    body = sprite_from_rows(body_rows, pal)
    bh = len(body_rows)
    frames = []
    for legs in legs_list:
        s = pygame.Surface((12, bh + len(legs)), pygame.SRCALPHA)
        s.blit(body, (0, 0))
        s.blit(sprite_from_rows(legs, pal), (0, bh))
        frames.append(s)
    return frames


def white_of(img):
    return pygame.mask.from_surface(img).to_surface(setcolor=(255, 255, 255, 255),
                                                    unsetcolor=(0, 0, 0, 0))


def make_light(radius, color):
    size = radius * 2
    surf = pygame.Surface((size, size))
    surf.fill((0, 0, 0))
    steps = 5
    for y in range(size):
        for x in range(size):
            d = math.hypot(x - radius, y - radius) / radius
            if d >= 1:
                continue
            v = (1 - d) ** 1.4 * steps
            band = int(v)
            if (v - band) * 16 > BAYER[y % 4][x % 4]:
                band += 1
            k = min(band, steps) / steps
            surf.set_at((x, y), (int(color[0] * k), int(color[1] * k), int(color[2] * k)))
    return surf


# Lanetli sunağın akitleri: bedeli olan güçler
PACTS = {
    "kan_akdi": {
        "name": "Kan Akdi", "desc": ["En yüksek can -1", "silah hasarı +2"],
        "icon": ["....r....", "...rRr...", "...rRr...", "..rRRRr..", "..rRwRr..",
                 "..rRRRr..", "...rrr...", "....k....", "...kkk..."],
    },
    "kul_borcu": {
        "name": "Kül Borcu", "desc": ["Külün yarıya iner,", "2 armağan seç"],
        "icon": ["...yyy...", "..yoooy..", ".yogggoy.", ".yogkgoy.", ".yogggoy.",
                 "..yoooy..", "...yyy...", ".g.g.g.g.", "g.g.g.g.g"],
    },
    "kor_yemini": {
        "name": "Kor Yemini", "desc": ["Dalgaları yen,", "2 armağan seç"],
        "icon": ["....y....", "...yoy...", "..yooy...", "..yoooy..", ".yoowooy.",
                 ".yowwwoy.", "..owwwo..", "...ooo...", "..kkkkk.."],
    },
}
PACT_MIN_KUL = 15
SIEGE_TIME = 24.0


def common_boons():
    """Sıradan ödül havuzu: şifa ve özel armağanlar hariç."""
    return [k for k, b in BOONS.items() if k != "sifa" and not b.get("rare")]


def norm(x, y):
    d = math.hypot(x, y)
    return (x / d, y / d) if d > 1e-6 else (0.0, 0.0)


# --- Oda üretimi -------------------------------------------------------------------
LAYOUTS = [
    [(4, 3), (15, 3), (4, 6), (15, 6)],                                  # dört sütun
    [(9, 4), (10, 4), (9, 5), (10, 5)],                                  # merkez blok
    [(5, 3), (6, 3), (7, 3), (12, 6), (13, 6), (14, 6)],                 # çapraz duvarlar
    [(3, 3), (16, 3), (3, 6), (16, 6), (9, 4), (10, 5)],                 # dağınık
    [(6, 4), (6, 5), (13, 4), (13, 5)],                                  # iki direk
    [],                                                                   # açık arena
]
PIT_LAYOUTS = [  # uçurum odaları: (x, y, genişlik, yükseklik)
    [(7, 3, 6, 4)],                                  # ortada tek çukur
    [(3, 3, 4, 4), (13, 3, 4, 4)],                   # iki yan çukur
    [(3, 4, 6, 2), (11, 4, 6, 2)],                   # ortası köprülü yarık
    [(4, 2, 3, 2), (13, 2, 3, 2), (4, 6, 3, 2), (13, 6, 3, 2), (9, 4, 2, 2)],  # beş çukur
]
ROOM_VARIANTS = {
    "diken": "yerdeki deliklere dikkat",
    "ucurum": "zemin çökmüş, oklar geçer",
    "karanlik": "meşaleler sönmüş",
}
SPIKE_PERIOD = 2.8


class Room:
    def __init__(self, depth, entry_col, rng, kind="combat", floor=1, idx=1):
        self.depth = depth
        self.kind = kind
        self.floor = floor
        self.idx = idx
        self.entry_col = entry_col
        self.door_open = self.kind in ("rest", "dukkan", "lanet")
        self.item = None          # bekçinin düşürdüğü eşya (x, y, index)
        self.talked = False
        self.door_anim = 1.0 if self.door_open else 0.0
        self.altar = None
        self.altar_used = False
        self.decor = 0            # sığınağa taşınan eşya sayısı
        self.spikes = {}          # (tx, ty) -> grup
        self.chest = None
        self.took_hit = False     # bu odada can gitti mi?
        self.scare_checked = False
        self.tansi = False        # tüccar odasının sahibi Tansi mi?
        self.greeted = False
        self.shrine = None        # lanetli sunak
        self.pact_fight = False   # kor yemini dalgaları sürüyor
        self.variant = None
        if kind == "combat" and depth >= 2:
            self.variant = os.environ.get("KUL_VARIANT") or rng.choice((None, None, *ROOM_VARIANTS))
        for _ in range(40):
            self.door_col = rng.randrange(3, COLS - 3)
            grid = [["W"] * COLS for _ in range(ROWS)]
            for ty in range(1, ROWS - 1):
                for tx in range(1, COLS - 1):
                    grid[ty][tx] = "."
            if self.kind == "rest":
                self.altar = (9, 4)
                grid[4][9] = grid[4][10] = "A"
            elif self.kind == "boss":
                for tx, ty in ((3, 2), (16, 2), (3, 7), (16, 7)):
                    grid[ty][tx] = "P"
            elif self.kind == "haven":
                self.door_col = entry_col if 3 <= entry_col < COLS - 3 else COLS // 2
                for tx, ty in ((3, 3), (16, 3)):  # çiçekli saksılar / sütunlar
                    grid[ty][tx] = "P"
            elif self.kind == "hazine":
                grid[4][9] = "T"
                mimic = os.environ.get("KUL_MIMIC") == "1" or rng.random() < 0.25
                self.chest = {"x": 9 * TILE + 8, "y": 5 * TILE, "open": False, "mimic": mimic}
                for tx, ty in ((5, 2), (14, 2), (5, 7), (14, 7)):
                    grid[ty][tx] = "P"
            elif self.kind == "dukkan":
                for tx, ty in ((6, 3), (13, 3)):
                    grid[ty][tx] = "P"
            elif self.kind == "ani":
                pass
            elif self.kind == "lanet":
                grid[4][9] = grid[4][10] = "A"
                self.shrine = {"x": 160, "y": 80, "used": False}
                for tx, ty in ((4, 3), (15, 3), (4, 6), (15, 6)):
                    grid[ty][tx] = "P"
            else:
                cells = [] if self.variant == "ucurum" else list(rng.choice(LAYOUTS))
                if rng.random() < 0.5:  # rastgele simetrik sütunlar
                    for _ in range(rng.randint(1, 3)):
                        tx, ty = rng.randrange(2, 9), rng.randrange(2, 8)
                        cells += [(tx, ty), (COLS - 1 - tx, ty)]
                for tx, ty in cells:
                    if abs(tx - self.door_col) <= 1 and ty <= 2:
                        continue
                    if abs(tx - entry_col) <= 1 and ty >= ROWS - 3:
                        continue
                    grid[ty][tx] = "P"
                near = lambda tx, ty: (abs(tx - self.door_col) <= 1 and ty <= 2) or \
                    (abs(tx - entry_col) <= 1 and ty >= ROWS - 3)
                self.spikes = {}
                if self.variant == "ucurum":
                    for px, py, pw, ph in rng.choice(PIT_LAYOUTS):
                        for ty in range(py, py + ph):
                            for tx in range(px, px + pw):
                                if not near(tx, ty):
                                    grid[ty][tx] = "C"
                elif self.variant == "diken":
                    step, off = rng.choice((3, 4)), rng.randrange(2)
                    for ty in range(2, ROWS - 2):
                        for tx in range(2, COLS - 2):
                            if (tx + off) % step < 2 and grid[ty][tx] == "." and not near(tx, ty):
                                grid[ty][tx] = "S"
                                self.spikes[(tx, ty)] = ((tx + off) // step) % 2
            grid[0][self.door_col] = "D"
            grid[ROWS - 1][entry_col] = "E"
            self.grid = ["".join(r) for r in grid]
            if self._connected():
                break
        self.torches = []
        cols = [c for c in range(2, COLS - 2) if abs(c - self.door_col) > 1]
        rng.shuffle(cols)
        for c in sorted(cols[:rng.randint(2, 3)]):
            self.torches.append((c, 0))
        self.torches += [(0, rng.randrange(3, 7)), (COLS - 1, rng.randrange(3, 7))]
        if self.kind == "boss":
            self.torches = [(c, 0) for c in (2, 6, 13, 17) if abs(c - self.door_col) > 1]
            self.torches += [(0, 3), (0, 6), (COLS - 1, 3), (COLS - 1, 6)]
        if self.kind in ("haven", "ani") or self.variant == "karanlik":
            self.torches = []
        self.dark = 0.5 if self.variant == "karanlik" else 0.0
        self.chains = [c for c in cols[3:6]]
        self.ambient = (min(62, 44 + depth * 2), 36, max(40, 56 - depth))
        if self.kind == "boss":
            self.ambient = (56, 30, 40)
        if self.kind == "haven":
            self.ambient = (255, 248, 236)   # ışık hesabı neredeyse kapalı: her yer aydınlık
        if self.kind == "ani":
            self.ambient = (236, 236, 255)
        if self.kind == "lanet":
            self.ambient = (46, 30, 66)
        if self.kind == "kusatma":
            self.ambient = (70, 34, 34)
        self.bg = None
        # dövüş planı
        self.waves_left = 0 if self.kind != "combat" else (1 if depth <= 2 else 2 if depth <= 6 else 3)
        self.wave_index = 0
        self.cleared = self.kind in ("rest", "haven", "ani", "dukkan", "lanet")
        self.door_open = self.kind in ("rest", "dukkan", "lanet")

    def _connected(self):
        floor = {(x, y) for y in range(ROWS) for x in range(COLS) if self.grid[y][x] in ".DES"}
        start = (self.entry_col, ROWS - 2)
        seen, q = {start}, deque([start])
        while q:
            x, y = q.popleft()
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if (nx, ny) in floor and (nx, ny) not in seen:
                    seen.add((nx, ny))
                    q.append((nx, ny))
        return seen == floor

    def solid(self, tx, ty):
        if not (0 <= tx < COLS and 0 <= ty < ROWS):
            return True
        ch = self.grid[ty][tx]
        if ch == "D":
            return not self.door_open
        return ch in "WPAETC"

    def shot_solid(self, tx, ty):
        """Mermiler uçurumun üstünden geçer."""
        return self.solid(tx, ty) and not (0 <= tx < COLS and 0 <= ty < ROWS and self.grid[ty][tx] == "C")

    def clear_tile(self, tx, ty):
        row = self.grid[ty]
        self.grid[ty] = row[:tx] + "." + row[tx + 1:]

    def enemy_plan(self):
        d, i = self.depth, self.wave_index
        n = min(2 + d // 2 + i, 7)
        wisps = 0 if d < 2 else max(1, n // 3)
        return n - wisps, wisps


CUR = None  # aktif oda — çarpışma kontrolü buna bakar


def feet_blocked(x, y):
    r = pygame.Rect(int(x) - 4, int(y) - 5, 8, 5)
    for ty in range(r.top // TILE, (r.bottom - 1) // TILE + 1):
        for tx in range(r.left // TILE, (r.right - 1) // TILE + 1):
            if CUR.solid(tx, ty):
                return True
    return False


def _shade(c, d):
    return (max(0, min(255, c[0] + d)), max(0, min(255, c[1] + d)), max(0, min(255, c[2] + d)))


def make_floor_tile(rng, tint):
    """Kabartmalı taş levhalar: üst/sol kenar aydınlık, alt/sağ kenar gölgeli."""
    t = pygame.Surface((TILE, TILE))
    grout = (14, 11, 18)
    t.fill(grout)
    layout = rng.choice(["one", "two_h", "two_v", "four", "one", "two_h"])
    rects = {"one": [(0, 0, 16, 16)], "two_h": [(0, 0, 16, 8), (0, 8, 16, 8)],
             "two_v": [(0, 0, 8, 16), (8, 0, 8, 16)],
             "four": [(0, 0, 8, 8), (8, 0, 8, 8), (0, 8, 8, 8), (8, 8, 8, 8)]}[layout]
    for (x, y, w, h) in rects:
        v = rng.randint(-4, 4)
        base = (34 + tint + v, 30 + v, 42 + v)
        pygame.draw.rect(t, base, (x + 1, y + 1, w - 1, h - 1))
        pygame.draw.line(t, _shade(base, 12), (x + 1, y + 1), (x + w - 2, y + 1))
        pygame.draw.line(t, _shade(base, 7), (x + 1, y + 1), (x + 1, y + h - 2))
        pygame.draw.line(t, _shade(base, -10), (x + 2, y + h - 1), (x + w - 1, y + h - 1))
        pygame.draw.line(t, _shade(base, -8), (x + w - 1, y + 2), (x + w - 1, y + h - 1))
        for _ in range(w * h // 14):  # doku
            px, py = x + rng.randrange(2, w - 1), y + rng.randrange(2, h - 1)
            t.set_at((px, py), _shade(base, rng.choice((-6, -4, 5))))
    if rng.random() < 0.22:  # çatlak
        x, y = rng.randrange(3, 13), rng.randrange(2, 8)
        for _ in range(rng.randint(4, 7)):
            if 0 <= x < TILE and 0 <= y < TILE:
                t.set_at((x, y), (14, 11, 18))
                if x + 1 < TILE:
                    t.set_at((x + 1, y), (46 + tint, 42, 54))
            x += rng.choice([-1, 0, 1])
            y += 1
    if rng.random() < 0.12:  # yosun
        mx, my = rng.randrange(1, 12), rng.randrange(1, 12)
        for _ in range(6):
            t.set_at((mx + rng.randrange(4), my + rng.randrange(3)), rng.choice([(34, 52, 40), (44, 66, 46)]))
    return t


def make_wall_face(rng, top_cap=True):
    """Üst duvarın ön yüzü: tuğlalar, yukarıdan aşağı kararan gradyan."""
    t = pygame.Surface((TILE, TILE))
    for y in range(TILE):
        k = y / TILE
        pygame.draw.line(t, (int(62 - 22 * k), int(52 - 18 * k), int(70 - 22 * k)), (0, y), (TILE - 1, y))
    for row in range(4):
        y = row * 4
        pygame.draw.line(t, (20, 16, 24), (0, y), (TILE - 1, y))
        shift = 0 if row % 2 == 0 else 4
        for bx in range(shift, TILE, 8):
            pygame.draw.line(t, (20, 16, 24), (bx, y), (bx, y + 3))
            t.set_at((bx + 1, y + 1), (84 - row * 8, 74 - row * 8, 92 - row * 8))
    for _ in range(8):
        t.set_at((rng.randrange(TILE), rng.randrange(TILE)), (30, 25, 36))
    if top_cap:
        pygame.draw.rect(t, (24, 20, 30), (0, 0, TILE, 3))
        pygame.draw.line(t, (70, 62, 82), (0, 3), (TILE - 1, 3))
    if rng.random() < 0.25:  # sızıntı lekesi
        x = rng.randrange(2, 14)
        for y in range(4, rng.randrange(8, 16)):
            t.set_at((x, y), (36, 44, 40))
    return t


def make_wall_cap(rng):
    """Yandan/alttan görünen duvarın üstü: koyu, iri taşlı."""
    t = pygame.Surface((TILE, TILE))
    t.fill((26, 22, 32))
    for _ in range(3):
        x, y = rng.randrange(0, 12), rng.randrange(0, 12)
        w, h = rng.randint(4, 7), rng.randint(3, 6)
        pygame.draw.rect(t, (36, 31, 44), (x, y, w, h))
        pygame.draw.line(t, (46, 40, 56), (x, y), (x + w - 1, y))
    for _ in range(10):
        t.set_at((rng.randrange(TILE), rng.randrange(TILE)), (18, 15, 22))
    return t


def make_wall_tile(rng):
    return make_wall_face(rng)


def make_pillar_tile(rng):
    return make_wall_face(rng)


def draw_pillar(bg, tx, ty, rng):
    """Üç boyutlu sütun: gövde gölgelendirilmiş, başlığı karonun üstüne taşar."""
    x, y = tx * TILE, ty * TILE
    pygame.draw.ellipse(bg, (10, 8, 14), (x - 1, y + 10, 19, 7))          # zemin gölgesi
    body_top = y - 6
    cols = [(40, 34, 48), (58, 50, 68), (76, 68, 88), (88, 80, 100), (70, 62, 82), (52, 44, 62), (36, 30, 44)]
    for i in range(12):
        c = cols[min(len(cols) - 1, int(i * len(cols) / 12))]
        pygame.draw.line(bg, c, (x + 2 + i, body_top + 3), (x + 2 + i, y + 13))
    for yy in range(body_top + 7, y + 12, 5):  # taş halkaları
        pygame.draw.line(bg, (28, 24, 34), (x + 2, yy), (x + 13, yy))
    pygame.draw.rect(bg, (14, 11, 18), (x + 1, body_top + 3, 14, y + 11 - body_top), 1)
    pygame.draw.rect(bg, (60, 52, 70), (x, y + 11, 16, 4))                 # kaide
    pygame.draw.line(bg, (84, 76, 96), (x, y + 11), (x + 15, y + 11))
    pygame.draw.rect(bg, (14, 11, 18), (x, y + 11, 16, 5), 1)
    pygame.draw.rect(bg, (78, 70, 92), (x, body_top - 1, 16, 5))           # başlık
    pygame.draw.line(bg, (110, 100, 124), (x + 1, body_top - 1), (x + 14, body_top - 1))
    pygame.draw.rect(bg, (14, 11, 18), (x, body_top - 1, 16, 5), 1)
    if rng.random() < 0.5:  # çatlak
        cx = x + rng.randrange(5, 11)
        for yy in range(body_top + 5, body_top + 11):
            bg.set_at((cx + (yy % 2), yy), (20, 16, 24))


def build_vignette():
    """Kenarlara doğru kararan, Bayer desenli piksel vinyet (çarpma ile uygulanır)."""
    v = pygame.Surface((W, WORLD_H))
    cx, cy = W / 2, WORLD_H / 2
    for y in range(WORLD_H):
        for x in range(W):
            d = math.hypot((x - cx) / cx, (y - cy) / cy) / 1.25
            k = max(0.0, d - 0.55) / 0.45
            k = min(1.0, k) * 0.62
            lvl = k * 4
            band = int(lvl)
            if (lvl - band) * 16 > BAYER[y % 4][x % 4]:
                band += 1
            m = int(255 * (1 - band / 4 * 0.62 * 1.6))
            m = max(120, min(255, m))
            v.set_at((x, y), (m, m, m))
    return v


def draw_arch(bg, col, row):
    x, y = col * TILE, row * TILE
    pygame.draw.rect(bg, (78, 68, 88), (x + 1, y + 1, 14, 15))
    pygame.draw.rect(bg, (5, 4, 7), (x + 3, y + 3, 10, 13))
    pygame.draw.line(bg, (100, 90, 112), (x + 2, y + 1), (x + 13, y + 1))
    bg.set_at((x + 3, y + 3), (78, 68, 88))
    bg.set_at((x + 12, y + 3), (78, 68, 88))


def build_haven(room):
    """Öykü'nün sığınağı: mahzenin tek renkli, sıcak, aydınlık yeri."""
    rng = random.Random(room.depth)
    bg = pygame.Surface((W, WORLD_H))
    greens = [(96, 170, 84), (110, 186, 92), (84, 156, 76)]
    for ty, row in enumerate(room.grid):
        for tx, ch in enumerate(row):
            x, y = tx * TILE, ty * TILE
            if ch in "WDE":  # sıcak, sarmaşıklı taş
                pygame.draw.rect(bg, (196, 160, 128), (x, y, TILE, TILE))
                for r in range(4):
                    yy = y + r * 4
                    pygame.draw.line(bg, (150, 116, 92), (x, yy), (x + TILE - 1, yy))
                    for bx in range(0 if r % 2 == 0 else 4, TILE, 8):
                        pygame.draw.line(bg, (150, 116, 92), (x + bx, yy), (x + bx, yy + 3))
                    pygame.draw.line(bg, (226, 196, 160), (x, yy + 1), (x + TILE - 1, yy + 1))
                if rng.random() < 0.5:  # sarmaşık
                    vx = x + rng.randrange(2, 14)
                    for vy in range(y, y + rng.randrange(6, 16)):
                        bg.set_at((vx, vy), (70, 140, 70))
                        if vy % 3 == 0:
                            bg.set_at((vx + rng.choice((-1, 1)), vy), (110, 190, 100))
            elif ch == "P":  # çiçek saksısı
                pygame.draw.rect(bg, rng.choice(greens), (x, y, TILE, TILE))
                pygame.draw.rect(bg, (170, 90, 60), (x + 3, y + 7, 10, 8))
                pygame.draw.rect(bg, (200, 116, 80), (x + 2, y + 6, 12, 2))
                for i in range(5):
                    fx, fy = x + 3 + i * 2 + rng.randint(0, 1), y + 1 + rng.randint(0, 4)
                    bg.set_at((fx, fy), rng.choice([(255, 120, 160), (255, 220, 100), (255, 255, 255)]))
                    bg.set_at((fx, fy + 1), (70, 140, 70))
            else:  # çimen
                pygame.draw.rect(bg, greens[(tx + ty) % 2], (x, y, TILE, TILE))
                for _ in range(10):
                    gx, gy = x + rng.randrange(TILE), y + rng.randrange(TILE)
                    bg.set_at((gx, gy), rng.choice(greens))
                    bg.set_at((gx, gy - 1 if gy > y else gy), (130, 200, 110))
                if rng.random() < 0.35:  # çiçek
                    fx, fy = x + rng.randrange(2, 14), y + rng.randrange(2, 14)
                    c = rng.choice([(255, 130, 170), (255, 225, 110), (250, 250, 255), (180, 150, 255)])
                    for ddx, ddy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                        bg.set_at((fx + ddx, fy + ddy), c)
                    bg.set_at((fx, fy), (255, 200, 60))
    # taş patika: girişten Öykü'ye
    for ty in range(4, ROWS - 1):
        for i in range(2):
            px = room.entry_col * TILE + 3 + i * 6 + (ty % 2) * 2
            pygame.draw.ellipse(bg, (200, 190, 170), (px, ty * TILE + 4, 6, 4))
            pygame.draw.ellipse(bg, (170, 160, 140), (px, ty * TILE + 7, 6, 2))
    # getirilen eşyalar sığınağı değiştirir
    if room.decor >= 1:  # Ay Çiçeği tarhı
        pygame.draw.ellipse(bg, (70, 110, 150), (40, 92, 44, 22))
        for fx, fy in ((48, 100), (58, 96), (68, 102), (54, 106), (72, 96)):
            for ddx, ddy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                bg.set_at((fx + ddx, fy + ddy), (235, 240, 255))
            bg.set_at((fx, fy), (255, 230, 120))
    if room.decor >= 2:  # tarağın durduğu aynalı masa
        pygame.draw.rect(bg, (130, 80, 56), (236, 92, 40, 16))
        pygame.draw.rect(bg, (170, 112, 76), (236, 90, 40, 4))
        pygame.draw.ellipse(bg, (200, 220, 240), (248, 72, 16, 20))
        pygame.draw.ellipse(bg, (230, 190, 90), (248, 72, 16, 20), 1)
        pygame.draw.rect(bg, (240, 240, 250), (240, 87, 7, 3))
    # Öykü'nün halısı
    pygame.draw.rect(bg, (180, 60, 90), (132, 50, 56, 34))
    pygame.draw.rect(bg, (230, 190, 90), (132, 50, 56, 34), 1)
    pygame.draw.rect(bg, (210, 90, 120), (136, 54, 48, 26))
    for i in range(0, 48, 6):
        bg.set_at((136 + i + 3, 67), (240, 200, 110))
    draw_arch(bg, room.door_col, 0)
    draw_arch(bg, room.entry_col, ROWS - 1)
    return bg


def build_memory(room):
    """Anı odası: her katta Öykü'nün geçmişinden farklı, aydınlık bir yer."""
    rng = random.Random(room.floor * 31 + 7)
    theme = min(room.floor, len(MEMORIES)) - 1
    bg = pygame.Surface((W, WORLD_H))
    wall = [(62, 66, 120), (150, 104, 76), (24, 22, 62)][theme]
    wall_hi = [(96, 104, 170), (190, 140, 100), (44, 42, 100)][theme]
    for ty in range(ROWS):
        for tx in range(COLS):
            x, y = tx * TILE, ty * TILE
            if room.grid[ty][tx] in "WDE":
                pygame.draw.rect(bg, wall, (x, y, TILE, TILE))
                pygame.draw.line(bg, wall_hi, (x, y + 2), (x + TILE - 1, y + 2))
                pygame.draw.line(bg, wall_hi, (x + (tx % 2) * 8, y + 9), (x + (tx % 2) * 8 + 6, y + 9))
            elif theme == 0:  # ay ışığında bahçe
                g = ((60, 96, 130), (54, 88, 124))[(tx + ty) % 2]
                pygame.draw.rect(bg, g, (x, y, TILE, TILE))
                for _ in range(8):
                    bg.set_at((x + rng.randrange(TILE), y + rng.randrange(TILE)), (88, 130, 160))
            elif theme == 1:  # ahşap kule odası
                pygame.draw.rect(bg, (176, 124, 82), (x, y, TILE, TILE))
                for i in (0, 8):
                    pygame.draw.line(bg, (140, 94, 62), (x, y + i), (x + TILE - 1, y + i))
                bg.set_at((x + (ty % 2) * 8 + 3, y + 3), (120, 80, 54))
            else:  # gece çatısı
                pygame.draw.rect(bg, (34, 30, 84), (x, y, TILE, TILE))
                pygame.draw.line(bg, (48, 44, 110), (x, y + 15), (x + TILE - 1, y + 15))
                pygame.draw.line(bg, (48, 44, 110), (x + 15, y), (x + 15, y + TILE - 1))
    if theme == 0:
        pygame.draw.ellipse(bg, (30, 60, 110), (214, 88, 70, 34))  # ay göleti
        pygame.draw.ellipse(bg, (70, 110, 170), (222, 92, 54, 24))
        pygame.draw.circle(bg, (235, 240, 255), (248, 103), 6)
        for _ in range(26):
            fx, fy = rng.randrange(28, 200), rng.randrange(24, 140)
            for ddx, ddy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                bg.set_at((fx + ddx, fy + ddy), (225, 232, 255))
            bg.set_at((fx, fy), (255, 230, 120))
    elif theme == 1:
        for wx in (64, 224):  # pencereler ve yere düşen ışık
            pygame.draw.rect(bg, (250, 240, 200), (wx, 3, 28, 11))
            pygame.draw.rect(bg, (90, 60, 44), (wx, 3, 28, 11), 1)
            pygame.draw.line(bg, (90, 60, 44), (wx + 14, 3), (wx + 14, 13))
            pygame.draw.polygon(bg, (214, 164, 110), [(wx + 2, 16), (wx + 26, 16), (wx + 40, 74), (wx + 14, 74)])
        pygame.draw.rect(bg, (120, 50, 80), (112, 92, 96, 40))   # halı
        pygame.draw.rect(bg, (230, 190, 90), (112, 92, 96, 40), 1)
        pygame.draw.rect(bg, (90, 56, 44), (28, 96, 40, 30))     # yatak
        pygame.draw.rect(bg, (230, 200, 220), (31, 99, 34, 24))
        pygame.draw.rect(bg, (250, 245, 250), (31, 99, 12, 24))
    else:
        for _ in range(70):  # yerde bile yıldızlar
            sx, sy = rng.randrange(18, W - 18), rng.randrange(18, WORLD_H - 18)
            bg.set_at((sx, sy), rng.choice([(255, 255, 230), (200, 200, 255), (255, 220, 150)]))
        pts = [(60, 40), (84, 56), (112, 44), (136, 66), (196, 48), (226, 64), (258, 44)]
        pygame.draw.lines(bg, (120, 120, 200), False, pts)
        for p in pts:
            pygame.draw.circle(bg, (255, 250, 210), p, 1)
        pygame.draw.rect(bg, (130, 90, 60), (150, 92, 20, 12))   # yıldız kutusu
        pygame.draw.rect(bg, (200, 150, 90), (150, 90, 20, 3))
        bg.set_at((160, 97), (255, 240, 170))
    draw_arch(bg, room.door_col, 0)
    draw_arch(bg, room.entry_col, ROWS - 1)
    return bg


def draw_pit(bg, room, tx, ty, rng):
    x, y = tx * TILE, ty * TILE
    pygame.draw.rect(bg, (5, 3, 7), (x, y, TILE, TILE))
    for _ in range(3):
        bg.set_at((x + rng.randrange(TILE), y + rng.randrange(4, TILE)), rng.choice([(70, 22, 18), (120, 44, 24)]))
    if room.grid[ty - 1][tx] != "C":  # çukurun karşı duvarı
        pygame.draw.rect(bg, (44, 38, 52), (x, y, TILE, 5))
        pygame.draw.line(bg, (74, 66, 84), (x, y), (x + TILE - 1, y))
        for i in range(0, TILE, 4):
            bg.set_at((x + i + rng.randrange(3), y + 4), (20, 16, 24))
    if room.grid[ty + 1][tx] != "C":
        pygame.draw.line(bg, (84, 76, 92), (x, y + TILE - 1), (x + TILE - 1, y + TILE - 1))
    if room.grid[ty][tx - 1] != "C":
        pygame.draw.line(bg, (60, 54, 68), (x, y), (x, y + TILE - 1))
    if room.grid[ty][tx + 1] != "C":
        pygame.draw.line(bg, (60, 54, 68), (x + TILE - 1, y), (x + TILE - 1, y + TILE - 1))


def build_background(room, font):
    if room.kind == "haven":
        return build_haven(room)
    if room.kind == "ani":
        return build_memory(room)
    rng = random.Random(room.depth * 977 + room.door_col)
    tint = min(room.depth, 10)
    bg = pygame.Surface((W, WORLD_H))
    pillars = []
    for ty, row in enumerate(room.grid):
        for tx, ch in enumerate(row):
            if ch in "WDE":
                tile = make_wall_face(rng) if ty == 0 else make_wall_cap(rng)
            else:
                tile = make_floor_tile(rng, tint)
                if ch == "P":
                    pillars.append((tx, ty))
            bg.blit(tile, (tx * TILE, ty * TILE))
    # ortam gölgesi: duvar diplerinde zemin kararır
    shade = pygame.Surface((W, WORLD_H), pygame.SRCALPHA)
    for i, a in enumerate((150, 110, 75, 45, 20)):
        pygame.draw.line(shade, (0, 0, 0, a), (TILE, TILE + i), (W - TILE - 1, TILE + i))
    for i, a in enumerate((120, 70, 30)):
        pygame.draw.line(shade, (0, 0, 0, a), (TILE + i, TILE), (TILE + i, WORLD_H - TILE - 1))
        pygame.draw.line(shade, (0, 0, 0, a), (W - TILE - 1 - i, TILE), (W - TILE - 1 - i, WORLD_H - TILE - 1))
        pygame.draw.line(shade, (0, 0, 0, a), (TILE, WORLD_H - TILE - 1 - i), (W - TILE - 1, WORLD_H - TILE - 1 - i))
    bg.blit(shade, (0, 0))
    # yan duvarların iç kenarı
    for ty in range(1, ROWS - 1):
        pygame.draw.line(bg, (60, 52, 72), (TILE - 1, ty * TILE), (TILE - 1, ty * TILE + TILE - 1))
        pygame.draw.line(bg, (60, 52, 72), (W - TILE, ty * TILE), (W - TILE, ty * TILE + TILE - 1))
    pygame.draw.line(bg, (60, 52, 72), (TILE, WORLD_H - TILE), (W - TILE - 1, WORLD_H - TILE))

    floor = [(tx, ty) for ty in range(1, ROWS - 1) for tx in range(1, COLS - 1)
             if room.grid[ty][tx] == "."]
    # kan lekeleri
    for _ in range(rng.randint(2, 5)):
        tx, ty = rng.choice(floor)
        cx, cy = tx * TILE + rng.randrange(3, 13), ty * TILE + rng.randrange(3, 13)
        for _ in range(rng.randint(3, 6)):
            pygame.draw.circle(bg, (46 + tint, 12, 18), (cx + rng.randint(-4, 4), cy + rng.randint(-2, 2)),
                               rng.randint(1, 3))
    # kemikler ve kafatasları
    for _ in range(rng.randint(2, 5)):
        tx, ty = rng.choice(floor)
        x, y = tx * TILE + rng.randrange(2, 11), ty * TILE + rng.randrange(3, 12)
        bone = (118, 110, 104)
        if rng.random() < 0.4:
            pygame.draw.rect(bg, bone, (x, y, 4, 3))
            bg.set_at((x + 1, y + 1), (20, 16, 20))
            bg.set_at((x + 3, y + 1), (20, 16, 20))
            pygame.draw.line(bg, bone, (x + 1, y + 3), (x + 2, y + 3))
        else:
            pygame.draw.line(bg, bone, (x, y), (x + 4, y + rng.choice((-1, 0, 1))))
            bg.set_at((x - 1, y), bone)
            bg.set_at((x + 5, y), bone)
    # moloz
    for _ in range(rng.randint(6, 12)):
        tx, ty = rng.choice(floor)
        x, y = tx * TILE + rng.randrange(1, 14), ty * TILE + rng.randrange(1, 14)
        pygame.draw.rect(bg, (60, 54, 66), (x, y, 2, 1))
        bg.set_at((x, y + 1), (18, 15, 22))
    # örümcek ağları köşelerde
    web = (64, 62, 72)
    for cx, cy, sx, sy in ((TILE, TILE, 1, 1), (W - TILE - 1, TILE, -1, 1)):
        for i in range(7):
            bg.set_at((cx + sx * i, cy + sy * (6 - i)), web)
        for i in range(5):
            bg.set_at((cx + sx * i, cy), web)
            bg.set_at((cx, cy + sy * i), web)
        bg.set_at((cx + sx * 2, cy + sy * 2), web)
    # zincirler
    for c in room.chains:
        x = c * TILE + rng.randrange(4, 12)
        for y in range(2, 2 + rng.randrange(8, 14)):
            bg.set_at((x, y), (84, 78, 92) if y % 3 else (36, 32, 42))
    # kapılar
    draw_arch(bg, room.door_col, 0)
    draw_arch(bg, room.entry_col, ROWS - 1)
    ex = room.entry_col * TILE
    for bx in range(4, 13, 3):
        pygame.draw.line(bg, (66, 60, 74), (ex + bx, (ROWS - 1) * TILE + 3), (ex + bx, WORLD_H - 1))
    pygame.draw.line(bg, (66, 60, 74), (ex + 3, (ROWS - 1) * TILE + 8), (ex + 12, (ROWS - 1) * TILE + 8))
    # dinlenme sunağı
    if room.altar:
        ax, ay = room.altar[0] * TILE, room.altar[1] * TILE
        pygame.draw.rect(bg, (16, 12, 18), (ax, ay + 14, 32, 3))
        pygame.draw.rect(bg, (70, 60, 78), (ax + 2, ay + 4, 28, 11))
        pygame.draw.rect(bg, (96, 86, 104), (ax, ay + 2, 32, 3))
        pygame.draw.rect(bg, (40, 32, 44), (ax + 6, ay + 7, 20, 6))
        for i in range(3):
            pygame.draw.line(bg, (110, 30, 40), (ax + 9 + i * 6, ay + 8), (ax + 9 + i * 6, ay + 11))
    # uçurumlar ve diken delikleri
    for ty in range(1, ROWS - 1):
        for tx in range(1, COLS - 1):
            ch = room.grid[ty][tx]
            if ch == "C":
                draw_pit(bg, room, tx, ty, rng)
            elif ch == "S":
                x, y = tx * TILE, ty * TILE
                pygame.draw.rect(bg, (34, 30, 40), (x + 1, y + 1, 14, 14), 1)
                for hx, hy in ((4, 4), (11, 4), (4, 11), (11, 11), (7, 7)):
                    pygame.draw.rect(bg, (10, 8, 12), (x + hx, y + hy, 2, 2))
    if room.shrine:  # lanetli sunak: kara taş, kan oluğu, çevresinde çizilmiş halka
        pygame.draw.ellipse(bg, (70, 24, 60), (118, 50, 84, 50), 1)
        pygame.draw.ellipse(bg, (46, 18, 44), (124, 54, 72, 42), 1)
        ax, ay = 144, 64
        pygame.draw.rect(bg, (10, 8, 12), (ax, ay + 14, 32, 3))
        pygame.draw.rect(bg, (34, 28, 42), (ax + 2, ay + 4, 28, 11))
        pygame.draw.rect(bg, (58, 48, 70), (ax, ay + 2, 32, 3))
        pygame.draw.rect(bg, (90, 16, 30), (ax + 14, ay + 5, 4, 9))
        for i in (5, 24):  # boynuz gibi iki taş
            pygame.draw.polygon(bg, (58, 48, 70), [(ax + i, ay + 2), (ax + i + 3, ay + 2), (ax + i + 1, ay - 7)])
    if room.kind == "hazine":  # sandığın altındaki eski halı
        pygame.draw.rect(bg, (70, 30, 40), (120, 52, 64, 48))
        pygame.draw.rect(bg, (130, 96, 50), (120, 52, 64, 48), 1)
        pygame.draw.rect(bg, (92, 42, 50), (125, 57, 54, 38))
    if room.kind == "dukkan":  # tüccarın serdiği kilim ve mallar
        pygame.draw.rect(bg, (60, 44, 70), (128, 72, 64, 22))
        pygame.draw.rect(bg, (150, 110, 60), (128, 72, 64, 22), 1)
        for i, c in enumerate(((200, 60, 60), (90, 170, 220), (230, 190, 90))):
            pygame.draw.rect(bg, c, (138 + i * 17, 80, 5, 7))
            pygame.draw.rect(bg, (30, 24, 34), (138 + i * 17, 87, 5, 1))
    # ilk odada yere kazınmış talimat (yalnızca ışıkta okunur)
    if room.depth == 1:
        for i, text in enumerate(("J saldır   BOŞLUK atıl   ESC menü", "kapıya ulaş, derine in")):
            img = font.render(text, False, (78, 70, 92))
            bg.blit(img, ((W - img.get_width()) // 2, WORLD_H - 46 + i * 11))
    for tx, ty in sorted(pillars, key=lambda p: p[1]):
        draw_pillar(bg, tx, ty, rng)
    return bg


# --- Parçacıklar ---------------------------------------------------------------
class Particles:
    """Kıvılcımlar, kül patlamaları — ışık hesabından sonra çizilir, parlar."""

    def __init__(self):
        self.parts = []  # x, y, vx, vy, ömür, max ömür, renk, yerçekimi

    def burst(self, x, y, n, colors, speed=60, life=0.5, grav=0.0):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            s = random.uniform(speed * 0.3, speed)
            lf = random.uniform(life * 0.5, life)
            self.parts.append([x, y, math.cos(a) * s, math.sin(a) * s, lf, lf,
                               random.choice(colors), grav])

    def ring(self, x, y, n, color, speed, life):
        for i in range(n):
            a = math.tau * i / n
            self.parts.append([x, y, math.cos(a) * speed, math.sin(a) * speed, life, life, color, 0.0])

    def update(self, dt):
        for p in self.parts:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[2] *= 0.9
            p[3] = p[3] * 0.9 + p[7] * dt
            p[4] -= dt
        self.parts = [p for p in self.parts if p[4] > 0]

    def draw(self, surf):
        for x, y, _, _, life, mx, c, _ in self.parts:
            if 0 <= x < W and 0 <= y < WORLD_H:
                k = 0.4 + 0.6 * life / mx
                surf.set_at((int(x), int(y)), (int(c[0] * k), int(c[1] * k), int(c[2] * k)))


# --- Oyuncu ------------------------------------------------------------------------
# --- Silahlar ve yetenekler ------------------------------------------------------------
WEAPONS = {
    "kilic": {"name": "Kor Kılıç", "role": "Kül Şövalyesi", "time": 0.16, "cd": 0.30, "slow": 0.45,
              "stats": (3, 3, 2), "desc": "Dengeli yay savuruşu",
              "skills": [("girdap", "Kor Girdabı", 5.0), ("kesik", "Atılgan Kesik", 6.0),
                         ("hayalet", "Hayalet Kılıçlar", 22.0)]},
    "yay": {"name": "Kül Yayı", "role": "Kül Avcısı", "time": 0.14, "cd": 0.36, "slow": 0.7,
            "stats": (2, 3, 5), "desc": "Uzaktan delici oklar",
            "skills": [("uclu", "Üçlü Atış", 4.0), ("takla", "Geri Takla", 6.0), ("yagmur", "Ok Yağmuru", 20.0)]},
    "balyoz": {"name": "Taş Balyoz", "role": "Taş Kırıcı", "time": 0.34, "cd": 0.62, "slow": 0.25,
               "stats": (5, 1, 3), "desc": "Yavaş ama yıkıcı",
               "skills": [("fay", "Fay Hattı", 6.0), ("demir", "Demir Deri", 12.0), ("goktasi", "Göktaşı", 24.0)]},
    "yumruk": {"name": "Kor Eldiven", "role": "Kor Yumruk", "time": 0.09, "cd": 0.15, "slow": 0.85,
               "stats": (2, 5, 1), "desc": "Hızlı seri, 3. vuruş ağır",
               "skills": [("seri", "Kor Seri", 5.0), ("tekme", "Ejder Tekmesi", 7.0),
                          ("volkan", "Volkan Yumruğu", 24.0)]},
    "mizrak": {"name": "Kül Mızrağı", "role": "Mahzen Muhafızı", "time": 0.15, "cd": 0.38, "slow": 0.55,
               "stats": (3, 3, 4), "desc": "Uzun ve dar saplama",
               "skills": [("saplama", "Yıldırım Saplama", 5.0), ("donen", "Dönen Mızrak", 7.0),
                          ("kazik", "Kazık Ormanı", 22.0)]},
    "asa": {"name": "Kor Asası", "role": "Kül Büyücüsü", "time": 0.14, "cd": 0.5, "slow": 0.6,
            "stats": (4, 2, 4), "desc": "Patlayan kor küreleri",
            "skills": [("halka", "Alev Halkası", 6.0), ("isik", "Işık Adımı", 6.0), ("meteor", "Kor Yağmuru", 24.0)]},
}
WEAPON_ORDER = ["kilic", "yay", "balyoz", "yumruk", "mizrak", "asa"]

# Silah ruhu: oyun başında seçilir, her vuruşa bir etki ekler
SPIRITS = {
    "kor": {"name": "Kor Ruhu", "desc": ["Vuruşlar düşmanı", "tutuşturur"], "col": (255, 150, 60),
            "icon": ["....y....", "...yoy...", "..yooy...", "..yoooy..", ".yoowooy.",
                     ".yowwwoy.", "..owwwo..", "...ooo...", "........."]},
    "ayaz": {"name": "Ayaz Ruhu", "desc": ["Yavaşlatır, 5. vuruş", "dondurur"], "col": (140, 200, 255),
             "icon": ["....b....", ".b..b..b.", "..b.b.b..", "...bwb...", "bbbwwwbbb",
                      "...bwb...", "..b.b.b..", ".b..b..b.", "....b...."]},
    "simsek": {"name": "Şimşek Ruhu", "desc": ["Vuruş yakındakine", "sıçrayabilir"], "col": (255, 240, 130),
               "icon": ["....yy...", "...yy....", "..yy.....", ".yyyyy...", "....yy...",
                        "...yy....", "..yy.....", ".yy......", ".y......."]},
}
SPIRIT_ORDER = ["kor", "ayaz", "simsek"]
# Silah ustalığı: öldürdükçe açılır. 1: özel vuruş, 2: hasar +1, 3: özel vuruş sıklaşır ve saldırı hızlanır
MASTERY_KILLS = (15, 40, 80)
MASTERY_NAMES = {"kilic": "her 3. savuruş dalga yollar", "yay": "her 3. atış yan oklar ekler",
                 "balyoz": "her 3. vuruş şok halkası çıkarır", "yumruk": "her 3. vuruş şok dalgası yapar",
                 "mizrak": "her 3. saplama uç fırlatır", "asa": "her 3. atış ikinci küre yollar"}
SKILL_KEYS = ("K", "L", "I", "O")
BEAM_SKILL = ("isin", "Kelebek Işını", 9.0)
SKILL_DESC = {
    "girdap": "Dönerek çevreni biçer, kor toplarını söndürür",
    "kesik": "İleri atılır, yolundaki herkesi keser",
    "hayalet": "Her yöne delip geçen hayalet kılıçlar fırlatır",
    "uclu": "Delici üç ok birden",
    "takla": "Geri sıçrar, ardında kor tuzağı bırakır; sonraki ok güçlü",
    "yagmur": "İleride bir alana dalga dalga ok yağdırır",
    "fay": "Yerden ileri doğru kaya dikenleri fışkırtır, sersemletir",
    "demir": "4 sn boyunca 2 darbeyi emen demir kalkan",
    "goktasi": "Havaya sıçrar, büyük bir alana çakılır",
    "kor": "",
    "seri": "Önündekine hızlı altı yumruk",
    "tekme": "En yakın düşmana uçar, savuran bir tekme atar",
    "volkan": "Güç toplar, önüne volkanik şok dalgası salar",
    "isin": "Baktığın yöne delici ışın dizisi yollar",
    "saplama": "Şimşek gibi ileri saplanır, yoldakileri deler",
    "donen": "Mızrağı fırlatır, geri dönerken de keser",
    "kazik": "Çevrende halka halka kazıklar fışkırır",
    "halka": "Çevreni yakar, kor toplarını söndürür",
    "isik": "Baktığın yere ışınlanır, ardında patlama bırakır",
    "meteor": "Düşmanların üstüne kor göktaşları yağdırır",
}
SKILL_PAL = {
    "w": (240, 236, 250), "y": (255, 214, 110), "o": (240, 120, 50), "r": (200, 50, 50),
    "c": (150, 200, 255), "b": (110, 120, 220), "g": (150, 150, 170), "G": (96, 96, 112),
    "n": (140, 96, 60), "k": (20, 16, 26), "p": (220, 120, 200),
}
SKILL_ICONS = {
    "girdap": ["..ooooo..", ".o.....o.", "o..yyy..o", "o.y...y.o", "o.y.w.y.o",
               "o.y...y..", "o..yyy...", ".o.....o.", "..oooo..."],
    "kesik": ["........w", "......ww.", ".....ww..", "o..ww....", ".oww.....",
              "oww......", ".o.......", "o........", "........."],
    "hayalet": ["c...c...c", ".c..c..c.", "..c.c.c..", "...www...", "cccwwwccc",
                "...www...", "..c.c.c..", ".c..c..c.", "c...c...c"],
    "uclu": ["......w..", "....ww...", "nnnnnnww.", "......w..", "nnnnnnnww",
             "......w..", "nnnnnnww.", "....ww...", "......w.."],
    "takla": ["...w.....", "..w......", ".wwwwww..", "..w....w.", "...w...w.",
              ".......w.", "..o.o.ww.", "...o.....", "..o.o...."],
    "yagmur": ["w..w..w..", "n..n..n..", "n.wn.wn..", "n.n..n.w.", "..n.....n",
               ".....n..n", "rrrrrrrrr", ".rrrrrrr.", "........."],
    "fay": ["....g....", "...gGg...", "...gGg..g", ".g.gGg.gG", "gGggGgggG",
            "gGGgGgGGG", "nnnnnnnnn", "nnnnnnnnn", "........."],
    "demir": [".ggggggg.", "gGGGGGGGg", "gGwGGGGGg", "gGwGGGGGg", "gGGGGGGGg",
              ".gGGGGGg.", "..gGGGg..", "...gGg...", "....g...."],
    "goktasi": ["o........", ".oo......", "..ooyy...", "...yyyy..", "...yrry..",
                "....yy...", ".........", "g.g.g.g.g", "ggggggggg"],
    "seri": ["oo.oo.oo.", "oyoy.oyo.", "oooooooo.", ".........", "...oo.oo.",
             "..oyoyoyo", "..ooooooo", ".........", "........."],
    "tekme": ["......yy.", ".....yoy.", "....yoo..", "...yoo...", "..yoo....",
              "..oo.....", ".oo......", "oo.......", "o........"],
    "isin": ["p.......p", "pp.....pp", "ppp.w.ppp", ".ppwwwpp.", "wwwwwwwww",
             ".ppwwwpp.", "ppp.w.ppp", "pp.....pp", "p.......p"],
    "saplama": ["........w", ".......ww", "......wy.", ".....wy..", "....wy...",
                "...oy....", "..o......", ".o.......", "o........"],
    "donen": ["..wwww...", ".w....w..", "w......w.", "w..oo..w.", "w......w.",
              ".w....w..", "..www.w..", "......ww.", "......w.."],
    "kazik": ["....w....", "...wgw...", "w..wgw..w", "gw.wgw.wg", "gw.wgw.wg",
              "gw.wgw.wg", "nnnnnnnnn", "nnnnnnnnn", "........."],
    "halka": ["..ooooo..", ".oyyyyyo.", "oyy...yyo", "oy.....yo", "oy.....yo",
              "oy.....yo", "oyy...yyo", ".oyyyyyo.", "..ooooo.."],
    "isik": ["c.......c", ".c..w..c.", "..c.w.c..", "...cwc...", "wwwwwwwww",
             "...cwc...", "..c.w.c..", ".c..w..c.", "c.......c"],
    "meteor": ["o.....o..", ".oo....oo", "..yy....y", "...yr....", "o...o....",
               ".oo..oo..", "..yy..yy.", "...r...r.", "ggggggggg"],
    "volkan": ["...r.r...", "..r.o.r..", ".r.oyo.r.", "r.oyyyo.r", ".oyywyyo.",
               "oyywwwyyo", ".oyyyyyo.", "..ooooo..", "...rrr..."],
}

HERO_PAL = {
    "k": (12, 9, 16),
    "1": (30, 26, 46), "2": (52, 46, 76), "3": (82, 74, 116), "4": (124, 116, 158),
    "s": (16, 12, 22), "e": (255, 150, 80), "E": (255, 230, 170),
    "r": (110, 26, 40), "R": (176, 52, 60),
    "b": (44, 32, 30), "B": (78, 58, 48), "m": (170, 168, 186),
}
HERO_BODY = [
    "....kkkk....",
    "...k4433k...",
    "..k443332k..",
    "..k43ss32k..",
    ".k43sssss2k.",
    ".k3sEsEss2k.",
    ".k3sssss21k.",
    ".kkRRRRRrkk.",
    "k32rRRRr221k",
    "k3322m22211k",
    "k3322r22211k",
    ".k322r2211k.",
    ".k3222221k..",
]
HERO_LEGS = [
    ["..kbBk.kbk..", "..kBBk.kBBk.", "..kkk..kkk.."],
    ["..kbk.kbBk..", ".kBBk.kBBk..", ".kkk..kkk..."],
]
WPAL = {
    "k": (12, 9, 16), "w": (230, 232, 245), "s": (150, 156, 176), "d": (90, 94, 110),
    "g": (210, 160, 60), "G": (150, 100, 40), "o": (120, 78, 44), "O": (160, 108, 62),
    "t": (220, 210, 190), "i": (70, 72, 86), "I": (120, 124, 140), "f": (255, 140, 60),
    "F": (255, 220, 140), "r": (130, 40, 40),
}
WEAPON_SPRITES = {
    "kilic": [".w.", "kwk", "kwk", "kwk", "kwk", "kwk", "kwk", "GgG", ".o.", ".G."],
    "yay": ["kO..", "kOt.", ".kOt", ".kOt", ".kOt", ".kOt", ".kOt", "kOt.", "kO.."],
    "balyoz": ["kkkkkkk", "kIIIIdk", "kIssIdk", "kIIIIdk", "kkkokkk", "...o...", "...o...", "...O...",
               "...o...", "...o...", "...G..."],
    "yumruk": [".kkkk.", "kFffrk", "kffffk", "kfFfrk", ".kkkk."],
    "mizrak": [".w.", "wsw", "wsw", ".k.", ".o.", ".o.", ".o.", ".O.", ".o.", ".o.", ".o.", ".O.", ".o.", ".o."],
    "asa": [".f.", "fFf", ".f.", "kgk", ".o.", ".o.", ".O.", ".o.", ".o.", ".O.", ".o.", ".o."],
}


class Player:
    def __init__(self, x, y, weapon="kilic"):
        self.x, self.y = x, y          # ayak merkezi
        self.weapon = weapon
        self.wp = WEAPONS[weapon]
        self.face = 1
        self.aim = (1.0, 0.0)
        self.anim = 0.0
        self.moving = False
        self.dash_t = 0.0
        self.dash_total = DASH_TIME
        self.dash_speed = DASH_SPEED
        self.dash_cd = 0.0
        self.dash_dir = (1, 0)
        self.dash_hits = set()
        self.skill_dash_dmg = 0
        self.attack_t = 0.0
        self.attack_total = self.wp["time"]
        self.attack_cd = 0.0
        self.attack_aim = (1.0, 0.0)
        self.hit_set = set()
        self.combo = 0
        self.impact_done = True
        self.max_hp = PLAYER_HP
        self.hp = PLAYER_HP
        self.invuln = 0.0
        self.kb = [0.0, 0.0]
        self.trail = []                # (x, y, frame, face, ömür)
        self.frames = build_frames(HERO_BODY, HERO_LEGS, HERO_PAL)
        self.wimg = sprite_from_rows(WEAPON_SPRITES[weapon], WPAL)
        self.events = []
        # yetenekler
        self.skill_cd = [0.0, 0.0, 0.0, 0.0]   # sonuncusu kelebek ışını
        self.has_beam = False
        self.room_shield = 0
        self.mastery = 0            # silah ustalığı seviyesi
        self.mastery_kills = 0
        self.swings = 0
        self.crit = False           # kusursuz atılmanın ardından gelen vuruş
        self.perfect_cd = 0.0
        self.cdr = 1.0
        self.shield = 0
        self.shield_t = 0.0
        self.leap = None
        self.z = 0.0
        self.channel = 0.0
        self.empower = False
        # armağanlarla değişen nitelikler
        self.boons = {}
        self.dmg = 1
        self.atk_cd_mul = 1.0
        self.reach = 1.0
        self.lifesteal = 0.0
        self.dash_dmg = 0
        self.thorns = 0
        self.speed_mul = 1.0
        self.dash_cd_mul = 1.0

    def apply_boon(self, key):
        self.boons[key] = self.boons.get(key, 0) + 1
        if key == "kor_kilic":
            self.dmg += 1
        elif key == "cevik_bilek":
            self.atk_cd_mul *= 0.8
            self.cdr *= 0.88
        elif key == "genis_yay":
            self.reach += 0.25
        elif key == "kul_kalbi":
            self.max_hp += 1
            self.hp += 1
        elif key == "kan_emen":
            self.lifesteal += 0.25
        elif key == "golge_adim":
            self.dash_dmg += 1
        elif key == "kor_pelerin":
            self.thorns += 1
        elif key == "kul_ruzgari":
            self.speed_mul *= 1.15
            self.dash_cd_mul *= 0.75
        elif key == "sifa":
            self.hp = min(self.max_hp, self.hp + 2)
            self.boons.pop("sifa")
        elif key in ("t_kalp", "boyut_kalbi"):
            self.max_hp += 2
            self.hp = self.max_hp
        elif key == "t_guc":
            self.dmg += 2
        elif key == "t_hiz":
            self.speed_mul *= 1.25
            self.dash_cd_mul *= 0.7
        elif key == "t_kalkan":
            self.room_shield += 1
        elif key == "kanat_tozu":
            self.dmg += 1
            self.speed_mul *= 1.1
        elif key == "kelebek_isini":
            self.has_beam = True
        elif key == "boyut_ruhu":
            self.cdr *= 0.75

    def place(self, x, y):
        self.x, self.y = x, y
        self.kb = [0.0, 0.0]
        self.trail = []
        self.dash_t = self.attack_t = 0.0
        self.leap = None
        self.z = 0.0
        self.channel = 0.0

    def busy(self):
        return self.leap is not None or self.channel > 0

    def start_dash(self, d, speed, time, dmg=0):
        self.dash_dir = d
        self.dash_speed = speed
        self.dash_t = self.dash_total = time
        self.dash_hits = set()
        self.skill_dash_dmg = dmg

    def update(self, dt, keys, dash_pressed, attack_pressed, sfx):
        dx = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
        dy = (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP])
        if dx and dy:
            dx *= 0.7071
            dy *= 0.7071
        self.moving = bool(dx or dy) and not self.busy()
        if self.moving:
            self.aim = (dx, dy)
        if dx and self.attack_t == 0 and not self.busy():
            self.face = 1 if dx > 0 else -1

        self.dash_cd = max(0.0, self.dash_cd - dt)
        self.attack_cd = max(0.0, self.attack_cd - dt)
        self.invuln = max(0.0, self.invuln - dt)
        self.skill_cd = [max(0.0, c - dt) for c in self.skill_cd]
        self.perfect_cd = max(0.0, self.perfect_cd - dt)
        if self.shield_t > 0:
            self.shield_t -= dt
            if self.shield_t <= 0:
                self.shield = 0

        # göktaşı sıçrayışı: havadayken dokunulmaz
        if self.leap:
            lp = self.leap
            lp["t"] += dt
            k = min(1.0, lp["t"] / lp["total"])
            self.x = lp["sx"] + (lp["tx"] - lp["sx"]) * k
            self.y = lp["sy"] + (lp["ty"] - lp["sy"]) * k
            self.z = math.sin(k * math.pi) * 46
            if k >= 1:
                self.leap = None
                self.z = 0.0
                self.events.append("land")
            return
        if self.channel > 0:
            self.channel -= dt
            if self.channel <= 0:
                self.events.append("volkan")
            return

        if dash_pressed and self.dash_cd == 0 and self.dash_t == 0:
            self.start_dash((dx, dy) if (dx or dy) else (self.face, 0), DASH_SPEED, DASH_TIME)
            self.dash_cd = DASH_COOLDOWN * self.dash_cd_mul
            sfx.play("dash")

        wp = self.wp
        if attack_pressed and self.attack_cd == 0 and self.dash_t == 0:
            self.attack_t = self.attack_total = wp["time"]
            self.attack_cd = wp["cd"] * self.atk_cd_mul
            self.attack_aim = self.aim
            if self.attack_aim[0]:
                self.face = 1 if self.attack_aim[0] > 0 else -1
            self.hit_set = set()
            self.swings += 1
            if self.mastery and self.swings % (2 if self.mastery >= 3 else 3) == 0:
                self.events.append("special")
            if self.weapon == "asa":
                self.events.append("orb")
                sfx.play("shoot", 0.6)
            elif self.weapon == "yay":
                self.events.append("arrow")
                sfx.play("bow", 0.8)
            elif self.weapon == "balyoz":
                self.impact_done = False
                sfx.play("dash", 0.7)
            elif self.weapon == "yumruk":
                self.combo = (self.combo + 1) % 3
                sfx.play("punch", 0.8)
            else:
                sfx.play("slash", 0.8)
        if self.weapon == "balyoz" and not self.impact_done and self.attack_t <= self.attack_total * 0.45:
            self.impact_done = True
            self.events.append("impact")
        self.attack_t = max(0.0, self.attack_t - dt)

        if self.dash_t > 0:
            self.dash_t = max(0.0, self.dash_t - dt)
            vx, vy = self.dash_dir[0] * self.dash_speed, self.dash_dir[1] * self.dash_speed
            self.trail.append([self.x, self.y, self.frame_index(), self.face, 0.25])
            if self.dash_t == 0:
                self.skill_dash_dmg = 0
        else:
            slow = wp["slow"] if self.attack_t > 0 else 1.0
            sp = PLAYER_SPEED * self.speed_mul * slow
            vx, vy = dx * sp, dy * sp
        vx += self.kb[0]
        vy += self.kb[1]
        decay = math.exp(-12 * dt)
        self.kb = [self.kb[0] * decay, self.kb[1] * decay]

        nx = self.x + vx * dt
        if not feet_blocked(nx, self.y):
            self.x = nx
        ny = self.y + vy * dt
        if not feet_blocked(self.x, ny):
            self.y = ny

        if self.moving:
            self.anim += dt * 8 * self.speed_mul
        for t in self.trail:
            t[4] -= dt
        self.trail = [t for t in self.trail if t[4] > 0]

    def melee_active(self):
        return self.attack_t > 0 and self.weapon in ("kilic", "yumruk", "mizrak")

    def body_rect(self):
        return pygame.Rect(int(self.x) - 4, int(self.y) - 13, 8, 13)

    def slash_rect(self):
        ax, ay = self.attack_aim
        if self.weapon == "mizrak":  # uzun ve dar: baktığın yönde çizgi
            ln, wd = int(38 * self.reach), 10
            cx, cy = self.x + ax * 23 * self.reach, self.y - 7 + ay * 23 * self.reach
            if ax and ay:
                ln = wd = int(26 * self.reach)
            w, h = (ln, wd) if abs(ax) >= abs(ay) else (wd, ln)
            return pygame.Rect(int(cx) - w // 2, int(cy) - h // 2, w, h)
        if self.weapon == "yumruk":
            off, size = 10 * self.reach, int((18 if self.combo == 0 else 14) * self.reach)
        else:
            off, size = 13 * self.reach, int(22 * self.reach)
        cx, cy = self.x + ax * off, self.y - 7 + ay * off
        return pygame.Rect(int(cx) - size // 2, int(cy) - size // 2, size, size)

    def hurt(self, sx, sy):
        if self.dash_t > 0 and self.perfect_cd <= 0 and self.hp > 0:
            self.events.append("perfect")  # darbenin içinden atıldın
        if self.invuln > 0 or self.dash_t > 0 or self.hp <= 0 or self.leap:
            return False
        if self.shield > 0:  # demir deri darbeyi emer
            self.shield -= 1
            self.invuln = 0.4
            self.events.append("block")
            return False
        self.hp -= 1
        if GOD_MODE:
            self.hp = max(1, self.hp)
        self.invuln = INVULN_TIME
        nx, ny = norm(self.x - sx, self.y - sy)
        self.kb = [nx * 170, ny * 170]
        return True

    def frame_index(self):
        return int(self.anim) % 2 if self.moving else 0

    def draw(self, surf):
        for x, y, fi, face, life in self.trail:
            ghost = self.frames[fi].copy()
            if face < 0:
                ghost = pygame.transform.flip(ghost, True, False)
            tint = (40, 50, 140, 0) if (self.dash_dmg or self.skill_dash_dmg) else (120, 40, 60, 0)
            ghost.fill(tint, special_flags=pygame.BLEND_RGBA_ADD)
            ghost.set_alpha(int(255 * life / 0.25 * 0.6))
            surf.blit(ghost, (int(x) - 6, int(y) - 16))
        sw = 10 if self.z < 10 else 8 if self.z < 30 else 6
        pygame.draw.ellipse(surf, (8, 6, 10), (int(self.x) - sw // 2, int(self.y) - 2, sw, 3))
        if self.hp > 0 and self.invuln > 0 and int(self.invuln * 14) % 2:
            return  # hasar sonrası yanıp sönme
        img = self.frames[self.frame_index()]
        if self.face < 0:
            img = pygame.transform.flip(img, True, False)
        bob = 1 if self.moving and int(self.anim) % 2 else 0
        px, py = int(self.x), int(self.y - self.z)
        behind = self.weapon == "balyoz" and self.attack_t == 0
        if behind:
            self.draw_weapon(surf, px, py + bob)
        surf.blit(img, (px - 6, py - 16 + bob))
        if not behind:
            self.draw_weapon(surf, px, py + bob)

    def draw_weapon(self, surf, px, py):
        f = self.face
        if self.weapon == "kilic":
            if self.attack_t == 0:
                surf.blit(self.wimg, (px + f * 6 - 1, py - 15))
        elif self.weapon == "mizrak":
            if self.attack_t == 0:
                surf.blit(self.wimg, (px + f * 6 - 1, py - 20))
        elif self.weapon == "asa":
            surf.blit(self.wimg, (px + f * 6 - 1, py - 17))
        elif self.weapon == "yay":
            img = self.wimg if f > 0 else pygame.transform.flip(self.wimg, True, False)
            surf.blit(img, (px + (4 if f > 0 else -8), py - 13))
        elif self.weapon == "balyoz":
            if self.attack_t > 0:  # savuruş: baştan aşağıya yay çizer
                prog = 1 - self.attack_t / self.attack_total
                base = math.atan2(self.attack_aim[1], self.attack_aim[0])
                a = base - f * 1.6 + f * 1.9 * min(1.0, prog * 1.8)
                hx, hy = px + math.cos(a) * 13, py - 8 + math.sin(a) * 13
                pygame.draw.line(surf, (120, 78, 44), (px, py - 8), (int(hx), int(hy)), 2)
                pygame.draw.rect(surf, (12, 9, 16), (int(hx) - 4, int(hy) - 3, 9, 7))
                pygame.draw.rect(surf, (120, 124, 140), (int(hx) - 3, int(hy) - 2, 7, 5))
                pygame.draw.line(surf, (170, 174, 190), (int(hx) - 3, int(hy) - 2), (int(hx) + 3, int(hy) - 2))
            else:
                surf.blit(self.wimg, (px - f * 7 - 3, py - 21))
        else:  # yumruk: iki kor eldiven
            reach = 0
            if self.attack_t > 0:
                reach = int(8 * math.sin(math.pi * (1 - self.attack_t / self.attack_total)))
            ax, ay = self.attack_aim
            for side in (-1, 1):
                ext = reach if (side == f or self.combo == 0) else 0
                gx = px + side * 5 + int(ax * ext)
                gy = py - 8 + int(ay * ext)
                pygame.draw.rect(surf, (12, 9, 16), (gx - 2, gy - 2, 5, 5))
                pygame.draw.rect(surf, (230, 110, 50), (gx - 1, gy - 1, 3, 3))
                surf.set_at((gx, gy - 1), (255, 220, 140))

    def draw_attack(self, surf, t):
        """Saldırı izi ve yetenek auraları — ışıktan sonra çizilir, karanlıkta parlar."""
        if self.shield > 0:  # demir deri: dönen demir pullar
            for j in range(6 + 2 * self.shield):
                a = t * 4 + j * math.tau / (6 + 2 * self.shield)
                surf.set_at((int(self.x + math.cos(a) * 9), int(self.y - 7 + math.sin(a) * 11)), (190, 196, 220))
        if self.channel > 0:  # volkan: güç toplama
            k = 1 - self.channel / 0.5
            for j in range(10):
                a = j * math.tau / 10 + t * 3
                r = 20 * (1 - k) + 4
                surf.set_at((int(self.x + math.cos(a) * r), int(self.y - 7 + math.sin(a) * r)), (255, 200, 90))
            pygame.draw.circle(surf, (255, 120, 50), (int(self.x), int(self.y) - 7), int(2 + 4 * k), 1)
        if self.empower and int(t * 8) % 2:
            surf.set_at((int(self.x) + self.face * 6, int(self.y) - 12), (255, 220, 120))
        if self.attack_t <= 0:
            return
        prog = 1 - self.attack_t / self.attack_total
        base = math.atan2(self.attack_aim[1], self.attack_aim[0])
        cx, cy = self.x, self.y - 7
        if self.weapon == "kilic":
            lead = -1.3 + 2.6 * min(1.0, prog * 1.4)
            fire = self.dmg > 1
            r0 = int(10 * self.reach)
            for i in range(16):
                rel = lead - i * 0.09
                if rel < -1.3:
                    break
                a = base + rel
                if fire:
                    col = (255, 245, 200) if i < 3 else (255, 160, 60) if i < 8 else (160, 50, 30)
                else:
                    col = (255, 240, 220) if i < 3 else (230, 150, 140) if i < 8 else (140, 50, 70)
                for r in range(r0, r0 + 7 - i // 4):
                    px, py = int(cx + math.cos(a) * r), int(cy + math.sin(a) * r)
                    if 0 <= px < W and 0 <= py < WORLD_H:
                        surf.set_at((px, py), col)
        elif self.weapon == "yumruk":
            ax, ay = self.attack_aim
            ln = int((14 if self.combo == 0 else 9) * self.reach * min(1.0, prog * 2))
            for d in range(4, 4 + ln):
                for o in ((-1, 0), (0, 0), (1, 0)) if self.combo == 0 else ((0, 0),):
                    px = int(cx + ax * d - ay * o[0])
                    py = int(cy + ay * d + ax * o[0])
                    if 0 <= px < W and 0 <= py < WORLD_H:
                        surf.set_at((px, py), (255, 230, 150) if d > ln else (240, 120, 50))
            if self.combo == 0:  # ağır üçüncü vuruş: yay şeklinde şok
                ex, ey = cx + ax * (ln + 4), cy + ay * (ln + 4)
                for j in range(-4, 5):
                    a = base + j * 0.25
                    r = 4 + 3 * prog
                    surf.set_at((int(ex + math.cos(a) * r), int(ey + math.sin(a) * r)), (255, 200, 90))
        elif self.weapon == "mizrak":
            ax, ay = self.attack_aim
            ext = int(42 * self.reach * math.sin(math.pi * min(1.0, prog * 1.15)))
            for d in range(4, max(5, ext)):
                px, py = int(cx + ax * d), int(cy + ay * d)
                if 0 <= px < W and 0 <= py < WORLD_H:
                    surf.set_at((px, py), (250, 250, 255) if d > ext - 7 else (150, 104, 62))
        elif self.weapon == "balyoz" and prog < 0.55:
            a0 = base - self.face * 1.6
            for i in range(10):
                a = a0 + self.face * 1.9 * min(1.0, prog * 1.8) * (i / 10)
                px, py = int(cx + math.cos(a) * 15), int(cy + math.sin(a) * 15)
                if 0 <= px < W and 0 <= py < WORLD_H:
                    surf.set_at((px, py), (140, 130, 150))


# --- Düşmanlar -------------------------------------------------------------------
class Enemy:
    SPAWN_TIME = 0.7
    KUL = 1
    passive = False           # oda temizliğini engellemez
    burn = 0.0                # silah ruhu etkileri
    burn_tick = 0.0
    slow = 0.0
    frost = 0

    def __init__(self, x, y, hp):
        self.x, self.y = x, y
        self.hp = hp
        self.state = "spawn"
        self.timer = self.SPAWN_TIME
        self.face = -1
        self.anim = random.random() * 2
        self.kb = [0.0, 0.0]
        self.flash = 0.0
        self.dead = False
        self.stun = 0.0
        self.cooldown = random.uniform(0.6, 1.6)

    def active(self):
        return self.state != "spawn" and not self.dead

    def hit(self, dmg, aim, knock=190):
        self.hp -= dmg
        self.flash = 0.12
        self.kb = [aim[0] * knock, aim[1] * knock]
        if self.state in ("wind", "lunge", "charge"):  # vurulunca saldırısı bozulur
            self.state, self.timer = "recover", 0.35
        if self.hp <= 0:
            self.dead = True

    def move(self, vx, vy, dt):
        nx = self.x + vx * dt
        if not feet_blocked(nx, self.y):
            self.x = nx
        ny = self.y + vy * dt
        if not feet_blocked(self.x, ny):
            self.y = ny

    def physics(self, vx, vy, dt):
        vx += self.kb[0]
        vy += self.kb[1]
        decay = math.exp(-11 * dt)
        self.kb = [self.kb[0] * decay, self.kb[1] * decay]
        self.move(vx, vy, dt)

    def draw_lit(self, surf, t):
        pass

    def light(self):
        return None

    def touching(self):
        """Şu an değince can götürüyor mu?"""
        return False

    def on_touch(self):
        pass

    def blocks(self, aim, dmg):
        return False

    def tick(self, dt):
        self.flash = max(0.0, self.flash - dt)
        self.timer -= dt
        self.cooldown -= dt


class Ghoul(Enemy):
    """Yavaşça yaklaşır, gözleri sararınca (uyarı) ileri atılır."""

    FRAMES = None
    WHITE = None

    def __init__(self, x, y, hp):
        super().__init__(x, y, hp)
        if Ghoul.FRAMES is None:
            Ghoul.FRAMES = build_frames(GHOUL_BODY, GHOUL_LEGS)
            Ghoul.WHITE = [white_of(f) for f in Ghoul.FRAMES]
        self.lunge_dir = (0.0, 0.0)

    def body_rect(self):
        return pygame.Rect(int(self.x) - 5, int(self.y) - 11, 10, 11)

    def update(self, dt, player, game):
        self.flash = max(0.0, self.flash - dt)
        self.timer -= dt
        self.cooldown -= dt
        dx, dy = player.x - self.x, player.y - self.y
        dist = math.hypot(dx, dy)
        ux, uy = norm(dx, dy)
        vx = vy = 0.0

        if self.state == "spawn":
            if self.timer <= 0:
                self.state = "chase"
            return
        if self.state == "chase":
            if player.hp > 0:
                vx, vy = ux * GHOUL_SPEED, uy * GHOUL_SPEED
                if dx:
                    self.face = 1 if dx > 0 else -1
            self.anim += dt * 5
            if dist < 46 and self.cooldown <= 0 and player.hp > 0:
                self.state, self.timer = "wind", 0.45
        elif self.state == "wind":
            self.lunge_dir = (ux, uy)
            if self.timer <= 0:
                self.state, self.timer = "lunge", 0.24
        elif self.state == "lunge":
            vx, vy = self.lunge_dir[0] * LUNGE_SPEED, self.lunge_dir[1] * LUNGE_SPEED
            self.anim += dt * 12
            if self.timer <= 0:
                self.state, self.timer = "recover", 0.55
        elif self.state == "recover":
            if self.timer <= 0:
                self.state = "chase"
                self.cooldown = random.uniform(0.8, 1.6)
        self.physics(vx, vy, dt)

    def img(self):
        i = int(self.anim) % 2
        img = Ghoul.WHITE[i] if self.flash > 0 else Ghoul.FRAMES[i]
        if self.face < 0:
            img = pygame.transform.flip(img, True, False)
        return img

    def origin(self):
        jit = random.choice((-1, 1)) if self.state == "wind" else 0
        return int(self.x) - 6 + jit, int(self.y) - 13

    def draw(self, surf):
        pygame.draw.ellipse(surf, (8, 6, 10), (int(self.x) - 5, int(self.y) - 2, 10, 3))
        img = self.img()
        ox, oy = self.origin()
        if self.state == "spawn":  # külden yükselir
            h = max(1, int(img.get_height() * (1 - self.timer / self.SPAWN_TIME)))
            surf.blit(img, (ox, int(self.y) - h), (0, 0, img.get_width(), h))
        else:
            surf.blit(img, (ox, oy))

    def draw_lit(self, surf, t):
        """Gözler karanlıkta parlar; atılmadan önce sararır (uyarı)."""
        if self.state == "spawn" or self.flash > 0:
            return
        ox, oy = self.origin()
        col = (255, 230, 120) if self.state == "wind" else (230, 70, 50)
        for ex, ey in GHOUL_EYES:
            if self.face < 0:
                ex = 11 - ex
            surf.set_at((ox + ex, oy + ey), col)
            if self.state == "wind":
                surf.set_at((ox + ex, oy + ey - 1), (150, 70, 40))


class Wisp(Enemy):
    """Mesafeyi korur, parlayarak yüklenir ve kor topu fırlatır."""

    FRAMES = None
    WHITE = None
    HOVER = 13

    def __init__(self, x, y, hp):
        super().__init__(x, y, hp)
        if Wisp.FRAMES is None:
            Wisp.FRAMES = [sprite_from_rows(f, FIRE_PAL) for f in WISP_FRAMES]
            Wisp.WHITE = [white_of(f) for f in Wisp.FRAMES]
        self.cooldown = random.uniform(1.2, 2.2)
        self.strafe = random.choice((-1, 1))
        self.phase = random.random() * 6

    def head(self):
        return self.x, self.y - self.HOVER + math.sin(self.phase) * 2

    def body_rect(self):
        hx, hy = self.head()
        return pygame.Rect(int(hx) - 5, int(hy) - 6, 10, 11)

    def update(self, dt, player, game):
        self.flash = max(0.0, self.flash - dt)
        self.timer -= dt
        self.cooldown -= dt
        self.phase += dt * 3
        dx, dy = player.x - self.x, player.y - self.y
        dist = math.hypot(dx, dy)
        ux, uy = norm(dx, dy)
        vx = vy = 0.0
        if dx:
            self.face = 1 if dx > 0 else -1
        if self.state == "spawn":
            if self.timer <= 0:
                self.state = "drift"
            return
        if self.state == "drift":
            if dist < 60:
                vx, vy = -ux, -uy
            elif dist > 100:
                vx, vy = ux, uy
            vx += -uy * self.strafe * 0.8
            vy += ux * self.strafe * 0.8
            vx, vy = vx * WISP_SPEED, vy * WISP_SPEED
            if random.random() < dt * 0.4:
                self.strafe *= -1
            if self.cooldown <= 0 and dist < 160 and player.hp > 0:
                self.state, self.timer = "charge", 0.6
        elif self.state == "charge":
            if self.timer <= 0:
                hx, hy = self.head()
                tx, ty = norm(player.x - hx, player.y - 6 - hy)
                game.bolts.append(Bolt(hx, hy, tx * BOLT_SPEED, ty * BOLT_SPEED))
                game.sfx.play("shoot", 0.7)
                self.state = "drift"
                self.cooldown = random.uniform(1.8, 2.8)
        elif self.state == "recover":
            if self.timer <= 0:
                self.state = "drift"
        self.physics(vx, vy, dt)

    def draw(self, surf):
        if self.state != "spawn":
            pygame.draw.ellipse(surf, (8, 6, 10), (int(self.x) - 4, int(self.y) - 2, 8, 3))

    def draw_lit(self, surf, t):
        i = int(t * 8 + self.phase) % 2
        img = Wisp.WHITE[i] if self.flash > 0 else Wisp.FRAMES[i]
        if self.face < 0:
            img = pygame.transform.flip(img, True, False)
        hx, hy = self.head()
        jit = random.choice((-1, 0, 1)) if self.state == "charge" else 0
        if self.state == "spawn":
            img = img.copy()
            img.set_alpha(int(255 * (1 - self.timer / self.SPAWN_TIME)))
        surf.blit(img, (int(hx) - 5 + jit, int(hy) - 7))
        if self.state == "charge":  # yüklenirken çevresinde kıvılcım
            k = 1 - self.timer / 0.6
            for j in range(4):
                a = t * 9 + j * math.tau / 4
                r = 9 - 5 * k
                surf.set_at((int(hx + math.cos(a) * r), int(hy + math.sin(a) * r)), (255, 230, 150))

    def light(self):
        hx, hy = self.head()
        return ("wisp_big" if self.state == "charge" else "wisp", hx, hy)

    KUL = 2


class Bolt:
    def __init__(self, x, y, vx, vy, h=8):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.h = h
        self.life = 4.0
        self.trail = []
        self.dead = False

    def update(self, dt):
        self.trail.append((self.x, self.y))
        self.trail = self.trail[-6:]
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        # duvar kontrolü: topun yere düşen gölgesine göre
        if self.life <= 0 or CUR.shot_solid(int(self.x) // TILE, int(self.y + self.h) // TILE):
            self.dead = True

    def rect(self):
        return pygame.Rect(int(self.x) - 2, int(self.y) - 2, 5, 5)

    def draw(self, surf):
        for i, (x, y) in enumerate(self.trail):
            k = (i + 1) / len(self.trail)
            if 0 <= x < W and 0 <= y < WORLD_H:
                surf.set_at((int(x), int(y)), (int(200 * k), int(70 * k), int(30 * k)))
        pygame.draw.rect(surf, (235, 110, 50), (int(self.x) - 2, int(self.y) - 1, 5, 3))
        pygame.draw.rect(surf, (235, 110, 50), (int(self.x) - 1, int(self.y) - 2, 3, 5))
        pygame.draw.rect(surf, (255, 240, 180), (int(self.x) - 1, int(self.y) - 1, 3, 3))


def render_boss(arm, crouch, step, tint):
    """Bekçiyi parça parça çizer (kollar kalkabilir, çömelebilir), sonra kontur ekler."""
    S = pygame.Surface((48, 56), pygame.SRCALPHA)

    def c(col):
        return tuple(max(0, min(255, col[i] + tint[i])) for i in range(3))

    sd, sm, sl = c((46, 42, 52)), c((72, 66, 80)), c((104, 96, 112))
    bone = (138, 126, 112)
    ox, oy = 24, 14 + crouch
    # bacaklar
    for i, lx in enumerate((ox - 10, ox + 3)):
        lift = 2 if (step == 1 and i == 0) or (step == 2 and i == 1) else 0
        h = 14 - crouch - lift
        pygame.draw.rect(S, sd, (lx, oy + 26, 7, h))
        pygame.draw.rect(S, sm, (lx - 1, oy + 26 + h - 3, 9, 3))
    # gövde
    pygame.draw.polygon(S, sm, [(ox - 13, oy + 8), (ox + 13, oy + 8), (ox + 9, oy + 28), (ox - 9, oy + 28)])
    pygame.draw.line(S, sd, (ox - 12, oy + 13), (ox + 12, oy + 13))
    pygame.draw.line(S, sl, (ox - 11, oy + 9), (ox + 11, oy + 9))
    pygame.draw.rect(S, sd, (ox - 9, oy + 24, 18, 3))
    pygame.draw.rect(S, bone, (ox - 2, oy + 24, 4, 3))
    # göğüsteki kor çatlakları
    for ex, ey in ((-9, -5), (8, -6), (-7, 6), (7, 5)):
        pygame.draw.line(S, (150, 60, 30), (ox, oy + 17), (ox + ex, oy + 17 + ey))
    pygame.draw.circle(S, (40, 14, 10), (ox, oy + 17), 6)
    # kollar
    for side in (-1, 1):
        sx, sy = ox + side * 14, oy + 9
        hx = ox + side * (17 - 2 * arm)
        hy = oy + 28 - 40 * arm
        pygame.draw.line(S, sd, (sx, sy), (hx, hy), 5)
        pygame.draw.rect(S, sl, (hx - 4, hy - 4, 9, 8))
        pygame.draw.line(S, sd, (hx - 3, hy - 1), (hx + 3, hy - 1))
    # omuzluklar ve dikenler
    for side in (-1, 1):
        sx = ox + side * 14
        pygame.draw.circle(S, sl, (sx, oy + 9), 6)
        pygame.draw.line(S, sm, (sx - 5, oy + 11), (sx + 5, oy + 11))
        pygame.draw.polygon(S, bone, [(sx - 2, oy + 4), (sx + side * 3, oy - 3), (sx + 2, oy + 4)])
    # miğfer ve boynuzlar
    pygame.draw.rect(S, sm, (ox - 6, oy - 6, 12, 13))
    pygame.draw.rect(S, sm, (ox - 5, oy - 8, 10, 3))
    pygame.draw.line(S, sl, (ox - 5, oy - 7), (ox + 4, oy - 7))
    pygame.draw.rect(S, (8, 6, 10), (ox - 5, oy - 1, 10, 3))
    pygame.draw.line(S, sd, (ox, oy + 3), (ox, oy + 6))
    for side in (-1, 1):
        pts = [(ox + side * 6, oy - 3), (ox + side * 11, oy - 8), (ox + side * 13, oy - 14),
               (ox + side * 10, oy - 7), (ox + side * 5, oy - 6)]
        pygame.draw.polygon(S, bone, pts)
    sil = pygame.mask.from_surface(S).to_surface(setcolor=(10, 8, 14, 255), unsetcolor=(0, 0, 0, 0))
    out = pygame.Surface((50, 58), pygame.SRCALPHA)
    for o in ((0, 1), (2, 1), (1, 0), (1, 2)):
        out.blit(sil, o)
    out.blit(S, (1, 1))
    return out


class Boss(Enemy):
    """Kat bekçisi. İki evre: yarı canın altında öfkelenir, yeni saldırılar açar."""

    SPAWN_TIME = 1.8
    CACHE = {}

    def __init__(self, x, y, hp, floor):
        super().__init__(x, y, hp)
        self.max_hp = hp
        self.shown = float(hp)
        self.floor = floor
        self.tint = BOSS_TINTS[(floor - 1) % len(BOSS_TINTS)]
        self.name = BOSS_NAMES[(floor - 1) % len(BOSS_NAMES)]
        self.mul = 1 + 0.12 * (floor - 1)
        self.phase = 1
        self.z = 0.0
        self.arm = 0.0
        self.crouch = 0
        self.walk = 0.0
        self.invuln = 0.0
        self.last = None
        self.next_t = 1.0
        self.dir = (1.0, 0.0)
        self.start = self.target = (x, y)
        self.volleys = 0

    def body_rect(self):
        return pygame.Rect(int(self.x) - 11, int(self.y - self.z) - 34, 22, 34)

    def active(self):
        return self.state != "spawn" and not self.dead and self.z < 10

    def core(self):
        return self.x, self.y - self.z - 23 + self.crouch

    @staticmethod
    def clamp(x, y):
        return min(max(x, 36), W - 36), min(max(y, 50), WORLD_H - 22)

    def hit(self, dmg, aim, knock=0):
        if self.invuln > 0:
            return
        self.hp -= dmg
        self.flash = 0.06
        if self.hp <= 0:
            self.dead = True
        elif self.phase == 1 and self.hp <= self.max_hp / 2:
            self.phase = 2
            self.z = 0.0
            self.state, self.timer = "roar", 1.5
            self.invuln = 1.5
            self.enraged = True

    def to(self, state, t):
        self.state, self.timer = state, t

    def choose(self, game):
        opts = [("leap", 3), ("fan", 3), ("charge", 2)]
        if self.phase == 2:
            opts.append(("rain", 2))
            if sum(1 for e in game.enemies if isinstance(e, Ghoul)) < 2:
                opts.append(("summon", 1))
        opts = [o for o in opts if o[0] != self.last]
        pick = random.choices([o[0] for o in opts], [o[1] for o in opts])[0]
        self.last = pick
        if pick == "leap":
            self.to("leap_wind", 0.5)
        elif pick == "fan":
            self.volleys = 2 if self.phase == 2 else 1
            self.to("fan_wind", 0.65)
        elif pick == "charge":
            self.to("charge_wind", 0.8)
        elif pick == "rain":
            self.to("rain_wind", 0.6)
            game.sfx.play("roar", 0.5)
        else:
            self.to("summon_wind", 0.9)
            game.sfx.play("roar", 0.5)

    def update(self, dt, p, game):
        self.flash = max(0.0, self.flash - dt)
        self.invuln = max(0.0, self.invuln - dt)
        self.timer -= dt
        self.shown += (self.hp - self.shown) * min(1.0, dt * 2.5)
        sp = (1.35 if self.phase == 2 else 1.0) * self.mul
        dx, dy = p.x - self.x, p.y - self.y
        ux, uy = norm(dx, dy)
        arm_to = 0.0
        self.crouch = 0
        st = self.state
        ashc = [(80, 74, 86), (110, 102, 114), (60, 54, 66)]
        embers = [(255, 200, 90), (235, 110, 50)]

        if st == "spawn":
            if random.random() < 0.6:
                game.fx.burst(self.x + random.uniform(-16, 16), self.y - 2, 2, ashc, speed=30, life=0.9, grav=-30)
            game.shake = max(game.shake, 1.5)
            if self.timer <= 0:
                self.to("roar", 1.3)
                game.sfx.play("roar")
            return
        if st == "roar":
            arm_to = 1.0
            game.shake = max(game.shake, 2.5)
            if random.random() < 0.7:
                game.fx.burst(*self.core(), 3, embers, speed=90, life=0.6, grav=-20)
            if self.timer <= 0:
                self.to("walk", 0)
                self.next_t = 0.6
        elif st == "walk":
            self.move(ux * 24 * sp, uy * 24 * sp, dt)
            self.x, self.y = self.clamp(self.x, self.y)
            self.walk += dt * 4 * sp
            if dx:
                self.face = 1 if dx > 0 else -1
            self.next_t -= dt
            if self.next_t <= 0:
                self.choose(game)
        elif st == "leap_wind":
            self.crouch, arm_to = 3, 0.5
            if self.timer <= 0:
                self.start = (self.x, self.y)
                self.target = self.clamp(p.x, p.y)
                self.to("leap_air", 0.85)
                game.hazards.append(Hazard(self.target[0], self.target[1], 30, 0.85, "slam"))
                game.sfx.play("dash")
        elif st == "leap_air":
            k = 1 - max(0.0, self.timer) / 0.85
            self.x = self.start[0] + (self.target[0] - self.start[0]) * k
            self.y = self.start[1] + (self.target[1] - self.start[1]) * k
            self.z = math.sin(k * math.pi) * 70
            arm_to = 1.0
            if self.timer <= 0:
                self.z = 0.0
                self.x, self.y = self.target
                self.to("recover", 0.9 if self.phase == 1 else 0.6)
                if self.phase == 2:  # inişte halka halinde kor
                    for i in range(8 + 2 * (self.floor - 1)):
                        a = math.tau * i / (8 + 2 * (self.floor - 1))
                        game.bolts.append(Bolt(self.x, self.y - 6, math.cos(a) * BOLT_SPEED,
                                               math.sin(a) * BOLT_SPEED, h=5))
        elif st == "fan_wind":
            arm_to = 0.3
            if self.timer <= 0:
                hx, hy = self.core()
                n = (5 if self.phase == 1 else 7) + (self.floor - 1)
                base = math.atan2(p.y - 6 - hy, p.x - hx)
                for i in range(n):
                    a = base + (i - (n - 1) / 2) * (1.1 / (n - 1))
                    game.bolts.append(Bolt(hx, hy, math.cos(a) * BOLT_SPEED * 1.1,
                                           math.sin(a) * BOLT_SPEED * 1.1, h=23))
                game.sfx.play("shoot")
                self.volleys -= 1
                if self.volleys > 0:
                    self.to("fan_wind", 0.4)
                else:
                    self.to("recover", 0.7)
        elif st == "charge_wind":
            self.crouch, arm_to = 2, 0.2
            if self.timer > 0.25:
                self.dir = (ux, uy)
                if dx:
                    self.face = 1 if dx > 0 else -1
            if self.timer <= 0:
                self.to("charge", 1.4)
                game.sfx.play("charge")
        elif st == "charge":
            nx = self.x + self.dir[0] * 215 * sp * dt
            ny = self.y + self.dir[1] * 215 * sp * dt
            cx, cy = self.clamp(nx, ny)
            blocked = (abs(cx - nx) > 0.01 or abs(cy - ny) > 0.01) or feet_blocked(nx, ny)
            if blocked:
                self.to("stun", 1.6 if self.phase == 1 else 1.1)
                game.shake = 7
                game.sfx.play("slam")
                game.fx.burst(self.x + self.dir[0] * 12, self.y - 12, 24, ashc + embers, speed=90, life=0.7,
                              grav=60)
            elif self.timer <= 0:
                self.to("recover", 0.6)
            else:
                self.x, self.y = nx, ny
                self.walk += dt * 14
                if random.random() < 0.5:
                    game.fx.burst(self.x, self.y - 2, 2, ashc, speed=20, life=0.5)
            if self.body_rect().colliderect(p.body_rect()):
                game.player_hit(self.x, self.y)
        elif st == "stun":
            if random.random() < dt * 8:
                game.fx.burst(self.x, self.y - 40, 1, [(255, 240, 160)], speed=20, life=0.5)
            if self.timer <= 0:
                self.to("recover", 0.3)
        elif st == "rain_wind":
            arm_to = 1.0
            if self.timer <= 0:
                pts = [(p.x, p.y)]
                for _ in range(5 + self.floor):
                    for _try in range(10):
                        rx, ry = p.x + random.uniform(-80, 80), p.y + random.uniform(-50, 50)
                        rx, ry = self.clamp(rx, ry)
                        if not feet_blocked(rx, ry):
                            pts.append((rx, ry))
                            break
                for i, (rx, ry) in enumerate(pts):
                    game.hazards.append(Hazard(rx, ry, 13, 1.0 + i * 0.12, "ember"))
                self.to("recover", 0.8)
        elif st == "summon_wind":
            arm_to = 1.0
            if random.random() < 0.5:
                game.fx.burst(self.x, self.y - 4, 2, ashc, speed=50, life=0.6)
            if self.timer <= 0:
                for side in (-1, 1):
                    gx, gy = self.clamp(self.x + side * 34, self.y + 6)
                    if not feet_blocked(gx, gy):
                        game.spawn_queue.append(Ghoul(gx, gy, 3 + game.room.depth // 4))
                game.sfx.play("spawn")
                self.to("recover", 0.6)
        elif st == "recover":
            if self.timer <= 0:
                self.to("walk", 0)
                self.next_t = random.uniform(0.7, 1.2) / sp
        self.arm += (arm_to - self.arm) * min(1.0, dt * 10)

    def sprite(self):
        step = (int(self.walk) % 4 in (1, 3)) * (1 + int(self.walk) % 4 // 2) if self.state in ("walk", "charge") else 0
        key = (round(self.arm * 4), self.crouch, step, self.tint)
        if key not in Boss.CACHE:
            Boss.CACHE[key] = render_boss(key[0] / 4, self.crouch, step, self.tint)
        img = Boss.CACHE[key]
        if self.flash > 0 or (self.invuln > 0 and int(self.invuln * 12) % 2):
            img = img.copy()  # tamamen beyaz yerine parlama: şekli okunur kalsın
            img.fill((120, 100, 80, 0), special_flags=pygame.BLEND_RGBA_ADD)
        if self.face < 0:
            img = pygame.transform.flip(img, True, False)
        return img

    def origin(self):
        jit = random.choice((-1, 0, 1)) if self.state in ("roar", "charge_wind", "stun") else 0
        return int(self.x) - 25 + jit, int(self.y - self.z) - 55

    def draw(self, surf):
        sw = int(30 * max(0.4, 1 - self.z / 120))
        pygame.draw.ellipse(surf, (8, 6, 10), (int(self.x) - sw // 2, int(self.y) - 3, sw, 6))
        img = self.sprite()
        ox, oy = self.origin()
        if self.state == "spawn":
            h = max(1, int(img.get_height() * (1 - self.timer / self.SPAWN_TIME)))
            surf.blit(img, (ox, int(self.y) + 3 - h), (0, 0, img.get_width(), h))
        else:
            surf.blit(img, (ox, oy))

    def draw_lit(self, surf, t):
        if self.state == "spawn":
            return
        ox, oy = self.origin()
        cx, cy = ox + 25, oy + 32 + self.crouch
        hot = self.state in ("fan_wind", "roar") or self.phase == 2
        pulse = 1 if int(t * 10) % 2 else 0
        pygame.draw.circle(surf, (235, 110, 50), (cx, cy), 4 + (pulse if hot else 0))
        pygame.draw.circle(surf, (255, 205, 100), (cx, cy), 2 + (1 if hot else 0))
        surf.set_at((cx, cy), (255, 250, 220))
        stunned = self.state == "stun"
        ecol = (90, 40, 30) if stunned else (255, 230, 120) if self.state.endswith("wind") else (240, 70, 50)
        for ex in (-3, 2):
            surf.set_at((cx + ex, oy + 15 + self.crouch), ecol)
            surf.set_at((cx + ex + 1, oy + 15 + self.crouch), ecol)
        if stunned:  # başının etrafında dönen kıvılcımlar
            for j in range(3):
                a = t * 6 + j * math.tau / 3
                surf.set_at((int(cx + math.cos(a) * 9), int(oy + 4 + math.sin(a) * 3)), (255, 240, 160))
        if self.state == "charge_wind":  # hamle yönü uyarısı
            for d in range(14, 150, 6):
                px, py = int(self.x + self.dir[0] * d), int(self.y - 6 + self.dir[1] * d)
                if 0 <= px < W and 0 <= py < WORLD_H and int(t * 20 + d / 6) % 2:
                    surf.set_at((px, py), (230, 50, 40))

    def light(self):
        cx, cy = self.core()
        return ("boss", cx, cy)


class Hazard:
    """Yere düşen uyarı halkası; süre dolunca patlar."""

    def __init__(self, x, y, r, t, kind):
        self.x, self.y, self.r = x, y, r
        self.t = self.total = t
        self.kind = kind

    def draw(self, surf, tt):
        k = 1 - max(0.0, self.t) / self.total
        late = k > 0.7
        if self.kind == "reap":
            hot, cold, inner = (220, 200, 255), (130, 90, 220), (70, 50, 130)
        elif self.kind == "pillar":
            hot, cold, inner = (255, 200, 90), (220, 90, 30), (130, 40, 20)
        else:
            hot, cold, inner = (255, 90, 60), (190, 36, 40), (120, 24, 30)
        col = hot if late and int(tt * 20) % 2 else cold
        r = self.r
        pygame.draw.ellipse(surf, col, (int(self.x - r), int(self.y - r * 0.6), int(2 * r), int(1.2 * r)), 1)
        ri = max(1, int(r * k))
        pygame.draw.ellipse(surf, inner, (int(self.x - ri), int(self.y - ri * 0.6), 2 * ri,
                                                   max(1, int(1.2 * ri))), 1)
        if self.kind == "ember" and self.t < 0.4:  # gökten düşen kor
            fy = int(self.y - 120 * self.t / 0.4)
            pygame.draw.rect(surf, (235, 110, 50), (int(self.x) - 2, fy - 3, 5, 6))
            pygame.draw.rect(surf, (255, 240, 180), (int(self.x) - 1, fy - 1, 3, 3))
            for j in range(1, 5):
                if fy - 3 - j * 3 >= 0:
                    surf.set_at((int(self.x), fy - 3 - j * 3), (200, 70, 30))


# --- Yeni düşman türleri ----------------------------------------------------------
MOB_PAL = {
    "k": (14, 11, 16), "c": (70, 58, 62), "C": (104, 88, 86), "r": (200, 60, 40), "y": (255, 214, 110),
    "b": (92, 78, 96), "B": (128, 112, 124), "p": (150, 70, 80), "P": (206, 110, 96), "w": (232, 226, 214),
    "s": (64, 70, 92), "S": (108, 118, 144), "L": (168, 178, 204), "o": (96, 62, 38), "O": (150, 100, 56),
    "g": (222, 176, 80), "d": (36, 16, 22),
}
CRAWLER_FRAMES = [
    ["..k....k..", "...kCCk...", ".kCCCCCCk.", "kCcrCCrcCk", ".kcccccck.", "k.k.kk.k.k"],
    ["k..k..k..k", "...kCCk...", ".kCCCCCCk.", "kCcrCCrcCk", ".kcccccck.", ".k.k..k.k."],
]
BLOAT_ROWS = [
    "....kkkkkk....", "..kkBBBBBBkk..", ".kBBBpBBBBBBk.", ".kBBpPpBBBpBk.", "kBBBBpBBBpPpBk",
    "kBBBBBBBBBpBBk", "kBkkBBBBBkkBBk", "kBBBBBBBBBBBBk", "kBBBkkkkkkBBBk", "kbBBkwkwkkBBbk",
    ".kbBBkkkkBBbk.", ".kkbbbbbbbbkk.", "..kbk.kk.kbk..",
]
GUARD_ROWS = [
    "...kkkkkk...", "..kSSSSSSk..", "..kSkkkkSk..", "..kSrrrrSk..", "..ksSSSSsk..", ".kkkssssskk.",
    "kSSLSSSSLSSk", "ksSLSssSLSsk", "kkSSSSSSSSkk", ".kkssssssk..", "..ksSSSSsk..", "..kskkkksk..",
    "..ksk..ksk..", ".kSSk..kSSk.",
]
MIMIC_ROWS = [
    [".kkkkkkkkkkkkkk.", "kOOOOOOOOOOOOOOk", "kOooooooooooooOk", "kOooyoooooooyoOk", "kgggggggggggggGk",
     "kdwdwdwdwdwdwdwk", "kddddddddddddddk", "kwdwdwdwdwdwdwdk", "kggggggkkggggggk", "kOoooooggoooooOk",
     "kOooooooooooooOk", "kOOOOOOOOOOOOOOk", ".kkkkkkkkkkkkkk."],
    [".kkkkkkkkkkkkkk.", "kOOOOOOOOOOOOOOk", "kOoryoooooooryOk", "kgggggggggggggGk", "kdwdwdwdwdwdwdwk",
     "kddddddddddddddk", "kddddrrrrrrddddk", "kddddrrrrrrddddk", "kddddddddddddddk", "kwdwdwdwdwdwdwdk",
     "kggggggkkggggggk", "kOooooooooooooOk", ".kkkkkkkkkkkkkk."],
]
MOB_PAL["G"] = (180, 136, 60)


class Mob(Enemy):
    """Basit tek görselli düşmanların ortak çizimi."""

    def imgs(self):
        raise NotImplementedError

    def draw_img(self, surf, img, y_off=0):
        pygame.draw.ellipse(surf, (8, 6, 10), (int(self.x) - img.get_width() // 2, int(self.y) - 2,
                                               img.get_width(), 3))
        if self.flash > 0:
            img = white_of(img)
        if self.face < 0:
            img = pygame.transform.flip(img, True, False)
        x, y = int(self.x) - img.get_width() // 2, int(self.y) - img.get_height() - y_off
        if self.state == "spawn":  # külden yükselir
            h = max(1, int(img.get_height() * (1 - max(0.0, self.timer) / self.SPAWN_TIME)))
            surf.blit(img, (x, int(self.y) - h), (0, 0, img.get_width(), h))
        else:
            surf.blit(img, (x, y))


class Butterfly(Enemy):
    """Nadir kelebek: saldırmaz, kaçar. Vurulursa dünya başka bir boyuta açılır."""

    SPAWN_TIME = 0.4
    passive = True

    def __init__(self, x, y):
        super().__init__(x, y, 1)
        self.goal = (x, y)
        self.phase = random.random() * 6

    def head(self):
        return self.x, self.y - 14 + math.sin(self.phase * 0.7) * 3

    def body_rect(self):
        hx, hy = self.head()
        return pygame.Rect(int(hx) - 6, int(hy) - 5, 12, 11)

    def update(self, dt, player, game):
        self.tick(dt)
        self.phase += dt * 11
        if game.room.cleared:  # oda bitince uçup gider
            self.dead = True
            game.fx.burst(*self.head(), 12, [(230, 150, 255), (140, 220, 255)], speed=50, life=0.6, grav=-50)
            return
        if self.state == "spawn":
            if self.timer <= 0:
                self.state = "fly"
            return
        dx, dy = self.x - player.x, self.y - player.y
        near = math.hypot(dx, dy) < 44
        if near or self.cooldown <= 0 or math.hypot(self.goal[0] - self.x, self.goal[1] - self.y) < 8:
            self.cooldown = random.uniform(0.7, 1.5)
            ux, uy = norm(dx, dy)
            self.goal = (min(W - 28, max(28, self.x + (ux * 70 if near else 0) + random.uniform(-50, 50))),
                         min(WORLD_H - 28, max(32, self.y + (uy * 50 if near else 0) + random.uniform(-40, 40))))
        vx, vy = norm(self.goal[0] - self.x, self.goal[1] - self.y)
        self.face = 1 if vx > 0 else -1
        self.x += vx * 46 * dt   # uçar: engellere takılmaz
        self.y += vy * 46 * dt
        if random.random() < dt * 9:
            hx, hy = self.head()
            game.fx.burst(hx, hy, 1, [(230, 170, 255), (160, 230, 255)], speed=12, life=0.6, grav=20)

    def draw(self, surf):
        pygame.draw.ellipse(surf, (8, 6, 10), (int(self.x) - 3, int(self.y) - 1, 6, 2))

    def draw_lit(self, surf, t):
        hx, hy = (int(v) for v in self.head())
        w = 2 + int(abs(math.sin(self.phase)) * 4)   # kanat çırpışı
        white = self.flash > 0
        up, low = ((255, 255, 255),) * 2 if white else ((230, 130, 255), (120, 220, 255))
        for sx in (-1, 1):
            pygame.draw.polygon(surf, up, [(hx, hy), (hx + sx * w, hy - 4), (hx + sx * (w + 1), hy - 1)])
            pygame.draw.polygon(surf, low, [(hx, hy), (hx + sx * w, hy + 3), (hx + sx, hy + 3)])
        pygame.draw.line(surf, (255, 255, 230), (hx, hy - 2), (hx, hy + 2))

    def light(self):
        hx, hy = self.head()
        return ("ghost", hx, hy)


class Crawler(Mob):
    """Kül Böceği: tek vuruşluk, hızlı, sürü halinde zikzak çizer."""

    FRAMES = None

    def __init__(self, x, y, hp=1):
        super().__init__(x, y, hp)
        if Crawler.FRAMES is None:
            Crawler.FRAMES = [sprite_from_rows(f, MOB_PAL) for f in CRAWLER_FRAMES]
        self.zig = random.uniform(0, 6)
        self.speed = random.uniform(52, 66)

    def body_rect(self):
        return pygame.Rect(int(self.x) - 5, int(self.y) - 6, 10, 6)

    def touching(self):
        return self.state == "chase"

    def on_touch(self):
        self.state, self.timer = "recover", 0.9

    def update(self, dt, player, game):
        self.tick(dt)
        ux, uy = norm(player.x - self.x, player.y - self.y)
        vx = vy = 0.0
        if self.state == "spawn":
            if self.timer <= 0:
                self.state = "chase"
            return
        if self.state == "chase":
            self.zig += dt * 7
            side = math.sin(self.zig) * 0.9
            if player.hp > 0:
                vx, vy = (ux - uy * side) * self.speed, (uy + ux * side) * self.speed
            self.face = 1 if vx > 0 else -1
            self.anim += dt * 14
        elif self.state == "recover":
            vx, vy = -ux * 34, -uy * 34
            self.anim += dt * 8
            if self.timer <= 0:
                self.state = "chase"
        self.physics(vx, vy, dt)

    def draw(self, surf):
        self.draw_img(surf, Crawler.FRAMES[int(self.anim) % 2])


class Bloat(Mob):
    """Kül Şişkini: yavaş yürür, yanına gelince şişip patlar; patlaması düşmanları da yakar."""

    IMG = None
    KUL = 2
    BLAST_R = 30

    def __init__(self, x, y, hp):
        super().__init__(x, y, hp)
        if Bloat.IMG is None:
            Bloat.IMG = sprite_from_rows(BLOAT_ROWS, MOB_PAL)

    def body_rect(self):
        return pygame.Rect(int(self.x) - 7, int(self.y) - 13, 14, 13)

    def update(self, dt, player, game):
        self.tick(dt)
        dx, dy = player.x - self.x, player.y - self.y
        ux, uy = norm(dx, dy)
        vx = vy = 0.0
        if self.state == "spawn":
            if self.timer <= 0:
                self.state = "chase"
            return
        if self.state == "chase":
            if player.hp > 0:
                vx, vy = ux * 24, uy * 24
                if dx:
                    self.face = 1 if dx > 0 else -1
            self.anim += dt * 3
            if math.hypot(dx, dy) < 34 and player.hp > 0:
                self.state, self.timer = "swell", 0.85
                game.hazards.append(Hazard(self.x, self.y, self.BLAST_R, 0.85, "burst"))
                game.sfx.play("charge", 0.6)
        elif self.state == "swell":
            if self.timer <= 0:
                self.dead = True
        self.physics(vx, vy, dt)

    def draw(self, surf):
        img = Bloat.IMG
        if self.state == "swell":
            k = 1 + 0.5 * (1 - max(0.0, self.timer) / 0.85)
            img = pygame.transform.scale(img, (int(14 * k), int(13 * k)))
            if int(self.timer * 16) % 2:
                img = img.copy()
                img.fill((255, 120, 90, 255), special_flags=pygame.BLEND_RGBA_MULT)
        self.draw_img(surf, img, int(math.sin(self.anim * 2) * 1 + 1))


class Guard(Mob):
    """Kalkan Muhafızı: önünden gelen darbeyi keser, yavaş döner. Arkasından vur ya da hamlesini boşa çıkar."""

    IMG = None
    KUL = 3

    def __init__(self, x, y, hp):
        super().__init__(x, y, hp)
        if Guard.IMG is None:
            Guard.IMG = sprite_from_rows(GUARD_ROWS, MOB_PAL)
        self.angle = random.uniform(0, math.tau)
        self.bash_dir = (0.0, 0.0)
        self.cooldown = random.uniform(1.0, 2.0)

    def dir(self):
        return math.cos(self.angle), math.sin(self.angle)

    def body_rect(self):
        return pygame.Rect(int(self.x) - 6, int(self.y) - 14, 12, 14)

    def guarding(self):
        return self.state in ("chase", "wind") and self.stun <= 0

    def blocks(self, aim, dmg):
        if not self.guarding():
            return False
        dx, dy = self.dir()
        if aim[0] * dx + aim[1] * dy > -0.25:  # darbe arkadan ya da yandan geldi
            return False
        if dmg >= 5:  # ağır vuruş kalkanı savurur
            self.state, self.timer = "recover", 1.3
            return False
        return True

    def touching(self):
        return self.state == "bash"

    def on_touch(self):
        self.state, self.timer = "recover", 1.0

    def update(self, dt, player, game):
        self.tick(dt)
        dx, dy = player.x - self.x, player.y - self.y
        ux, uy = norm(dx, dy)
        vx = vy = 0.0
        if self.state == "spawn":
            if self.timer <= 0:
                self.state = "chase"
            return
        if self.state in ("chase", "wind"):  # kalkan oyuncuya yavaşça döner
            want = math.atan2(dy, dx)
            diff = (want - self.angle + math.pi) % math.tau - math.pi
            turn = 1.7 * dt
            self.angle += max(-turn, min(turn, diff))
        if self.state == "chase":
            if player.hp > 0:
                vx, vy = ux * 20, uy * 20
            self.anim += dt * 3
            if math.hypot(dx, dy) < 56 and self.cooldown <= 0 and player.hp > 0:
                self.state, self.timer = "wind", 0.55
        elif self.state == "wind":
            if self.timer <= 0:
                self.bash_dir = self.dir()
                self.state, self.timer = "bash", 0.34
                game.sfx.play("dash", 0.5)
        elif self.state == "bash":
            vx, vy = self.bash_dir[0] * 150, self.bash_dir[1] * 150
            if self.timer <= 0:
                self.state, self.timer = "recover", 1.0
        elif self.state == "recover":
            if self.timer <= 0:
                self.state = "chase"
                self.cooldown = random.uniform(1.2, 2.2)
        self.face = 1 if self.dir()[0] > 0 else -1
        self.physics(vx, vy, dt)

    def draw_shield(self, surf):
        dx, dy = self.dir()
        lowered = self.state == "recover"
        cx, cy = self.x + dx * (5 if lowered else 8), self.y - 7 + dy * 5 + (3 if lowered else 0)
        px, py = -dy, dx
        for i in range(-4, 5):
            for j in range(2):
                sx, sy = int(cx + px * i + dx * j), int(cy + py * i * 0.8 + dy * j)
                edge = abs(i) == 4
                col = (60, 56, 78) if lowered else (214, 220, 240) if edge else (120, 130, 164)
                if 0 <= sx < W and 0 <= sy < WORLD_H:
                    surf.set_at((sx, sy), col)

    def draw(self, surf):
        if self.state == "spawn":
            self.draw_img(surf, Guard.IMG)
            return
        back = self.dir()[1] < 0  # kalkan arkadaysa önce çizilir
        if back:
            self.draw_shield(surf)
        jit = random.choice((-1, 1)) if self.state == "wind" else 0
        self.x += jit
        self.draw_img(surf, Guard.IMG)
        self.x -= jit
        if not back:
            self.draw_shield(surf)

    def draw_lit(self, surf, t):
        if self.state == "spawn" or self.flash > 0:
            return
        col = (255, 230, 120) if self.state == "wind" else (230, 70, 50)
        pygame.draw.line(surf, col, (int(self.x) - 3, int(self.y) - 11), (int(self.x) + 2, int(self.y) - 11))


class Mimic(Mob):
    """Aç Sandık: hazine odasında sandık kılığında bekler, sıçrayarak saldırır."""

    FRAMES = None
    SPAWN_TIME = 0.5
    KUL = 14

    def __init__(self, x, y, hp):
        super().__init__(x, y, hp)
        if Mimic.FRAMES is None:
            Mimic.FRAMES = [sprite_from_rows(f, MOB_PAL) for f in MIMIC_ROWS]
        self.hop_dir = (0.0, 0.0)
        self.z = 0.0
        self.cooldown = 0.5

    def body_rect(self):
        return pygame.Rect(int(self.x) - 8, int(self.y - self.z) - 13, 16, 13)

    def touching(self):
        return self.state == "hop"

    def update(self, dt, player, game):
        self.tick(dt)
        vx = vy = 0.0
        if self.state == "spawn":
            if self.timer <= 0:
                self.state = "wait"
            return
        if self.state == "wait":
            self.z = 0.0
            if self.cooldown <= 0 and player.hp > 0:
                self.hop_dir = norm(player.x - self.x, player.y - self.y)
                self.face = 1 if self.hop_dir[0] > 0 else -1
                self.state, self.timer = "hop", 0.42
                game.sfx.play("dash", 0.4)
        elif self.state == "hop":
            k = max(0.0, self.timer) / 0.42
            self.z = math.sin(k * math.pi) * 15
            vx, vy = self.hop_dir[0] * 125, self.hop_dir[1] * 125
            if self.timer <= 0:
                self.z = 0.0
                self.state = "wait"
                self.cooldown = random.uniform(0.45, 0.8)
                game.sfx.play("slam", 0.3)
                game.shake = max(game.shake, 2)
                game.fx.burst(self.x, self.y - 1, 6, [(90, 84, 96), (60, 54, 66)], speed=40, life=0.3)
        elif self.state == "recover":
            if self.timer <= 0:
                self.state = "wait"
        self.physics(vx, vy, dt)

    def draw(self, surf):
        self.draw_img(surf, Mimic.FRAMES[1 if self.state == "hop" else 0], int(self.z))


# --- 2. ve 3. katın kendine özgü bekçileri ------------------------------------

def outline_sprite(S):
    """Sprite'a 1 piksellik koyu kontur ekler (boyut +2)."""
    sil = pygame.mask.from_surface(S).to_surface(setcolor=(10, 8, 14, 255), unsetcolor=(0, 0, 0, 0))
    out = pygame.Surface((S.get_width() + 2, S.get_height() + 2), pygame.SRCALPHA)
    for o in ((0, 1), (2, 1), (1, 0), (1, 2)):
        out.blit(sil, o)
    out.blit(S, (1, 1))
    return out


def _tinted(tint):
    return lambda col: tuple(max(0, min(255, col[i] + tint[i])) for i in range(3))


def render_pyre(arm, flame, tint):
    """Kor Bekçisi: bacaksız, süzülen, cüppeli bir ateş rahibi; başında alev tacı, yüzünde kemik maske."""
    S = pygame.Surface((48, 58), pygame.SRCALPHA)
    c = _tinted(tint)
    rd, rm, rl = c((58, 22, 20)), c((92, 36, 28)), c((130, 56, 36))
    bone = (196, 178, 150)
    ox, oy = 24, 18
    # alev tacı (3 kare titreşim)
    hts = [(9, 6, 11), (11, 8, 7), (7, 11, 9)][flame]
    for i, dx in enumerate((-5, 0, 5)):
        h = hts[i]
        pygame.draw.polygon(S, (200, 70, 30), [(ox + dx - 3, oy - 6), (ox + dx, oy - 6 - h), (ox + dx + 3, oy - 6)])
        pygame.draw.polygon(S, (255, 170, 70), [(ox + dx - 1, oy - 6), (ox + dx, oy - 4 - h // 2),
                                                (ox + dx + 1, oy - 6)])
    # cüppe: aşağıda yırtık, alt kenarı kor
    pygame.draw.polygon(S, rm, [(ox - 8, oy + 4), (ox + 8, oy + 4), (ox + 15, oy + 34), (ox - 15, oy + 34)])
    pygame.draw.polygon(S, rd, [(ox - 2, oy + 6), (ox + 2, oy + 6), (ox + 4, oy + 34), (ox - 4, oy + 34)])
    pygame.draw.line(S, rl, (ox - 7, oy + 5), (ox - 13, oy + 32))
    for i in range(-14, 15, 4):  # yırtık uç
        d = 3 + (i * 7 + flame * 3) % 4
        pygame.draw.line(S, rm, (ox + i, oy + 34), (ox + i + 1, oy + 34 + d), 2)
        S.set_at((ox + i + 1, oy + 34 + d), (235, 110, 50))
    pygame.draw.line(S, (150, 50, 26), (ox - 15, oy + 34), (ox + 15, oy + 34))
    # kemer ve sarkan zincir halkaları
    pygame.draw.rect(S, rd, (ox - 10, oy + 16, 20, 3))
    for k in range(3):
        pygame.draw.rect(S, (110, 104, 100), (ox - 1, oy + 19 + k * 3, 2, 2))
    # kollar: geniş yenler, avuçta kor
    for side in (-1, 1):
        sx, sy = ox + side * 8, oy + 7
        hx = ox + side * (15 + 4 * arm)
        hy = oy + 22 - 22 * arm
        pygame.draw.polygon(S, rm, [(sx, sy - 2), (sx, sy + 5), (hx + side * 2, hy + 3), (hx - side * 2, hy - 3)])
        pygame.draw.line(S, rl, (sx, sy - 2), (hx - side * 2, hy - 3))
        pygame.draw.circle(S, (40, 16, 12), (hx, hy), 3)
    # başlık ve kemik maske
    pygame.draw.polygon(S, rm, [(ox - 8, oy + 6), (ox - 7, oy - 4), (ox, oy - 8), (ox + 7, oy - 4), (ox + 8, oy + 6)])
    pygame.draw.polygon(S, rd, [(ox - 6, oy + 6), (ox - 5, oy - 2), (ox + 5, oy - 2), (ox + 6, oy + 6)])
    pygame.draw.polygon(S, bone, [(ox - 4, oy - 2), (ox + 4, oy - 2), (ox + 4, oy + 3), (ox, oy + 6), (ox - 4, oy + 3)])
    pygame.draw.rect(S, (20, 10, 10), (ox - 3, oy, 2, 2))
    pygame.draw.rect(S, (20, 10, 10), (ox + 1, oy, 2, 2))
    pygame.draw.line(S, (150, 130, 110), (ox, oy + 3), (ox, oy + 5))
    return outline_sprite(S)


def render_shade(pose, tint, ghost=False):
    """Gölge Bekçisi: uzun, ince, yırtık pelerinli bir avcı; elinde kavisli uzun bir orak."""
    S = pygame.Surface((56, 64), pygame.SRCALPHA)
    c = _tinted(tint)
    cd, cm, cl = c((22, 18, 34)), c((38, 32, 58)), c((62, 54, 90))
    if ghost:
        cd, cm, cl = (30, 24, 50), (52, 42, 84), (80, 66, 120)
    steel, steel_l = (120, 118, 140), (190, 190, 210)
    ox, oy = 28, 14
    # orak (gövdenin arkasında): poz 0 bekleme, 1 geriye kaldırılmış, 2 savrulmuş
    if pose == 0:
        p0, p1 = (ox + 10, oy + 40), (ox + 14, oy - 6)
    elif pose == 1:
        p0, p1 = (ox + 6, oy + 30), (ox - 12, oy - 10)
    else:
        p0, p1 = (ox - 4, oy + 24), (ox + 24, oy + 30)
    pygame.draw.line(S, (70, 56, 50), p0, p1, 2)
    bx, by = p1
    dxn, dyn = norm(p1[0] - p0[0], p1[1] - p0[1])
    px_, py_ = -dyn, dxn  # sapa dik yön: bıçak buraya kıvrılır
    blade = [(bx, by), (bx + px_ * 9 + dxn * 3, by + py_ * 9 + dyn * 3),
             (bx + px_ * 16 - dxn * 4, by + py_ * 16 - dyn * 4),
             (bx + px_ * 8 + dxn * 1, by + py_ * 8 + dyn * 1)]
    pygame.draw.polygon(S, steel, blade)
    pygame.draw.line(S, steel_l, blade[0], blade[2])
    # pelerin: ince ve uzun, alt kenar yırtık
    pygame.draw.polygon(S, cm, [(ox - 6, oy + 4), (ox + 6, oy + 4), (ox + 11, oy + 44), (ox - 11, oy + 44)])
    pygame.draw.polygon(S, cd, [(ox - 1, oy + 6), (ox + 2, oy + 6), (ox + 4, oy + 44), (ox - 3, oy + 44)])
    pygame.draw.line(S, cl, (ox - 5, oy + 5), (ox - 10, oy + 42))
    for i in range(-10, 11, 3):
        d = 2 + (i * 5) % 5
        pygame.draw.line(S, cm, (ox + i, oy + 44), (ox + i - 1, oy + 44 + d), 2)
    # omuz pelerini ve kollar
    pygame.draw.polygon(S, cl, [(ox - 9, oy + 9), (ox, oy + 2), (ox + 9, oy + 9), (ox + 6, oy + 14), (ox - 6, oy + 14)])
    hand = ((ox + 10, oy + 22), (ox + 2, oy + 20), (ox + 8, oy + 26))[pose]
    pygame.draw.line(S, cm, (ox + 6, oy + 10), hand, 3)
    pygame.draw.line(S, cm, (ox - 6, oy + 10), (ox - 9, oy + 26), 3)
    pygame.draw.rect(S, (150, 140, 160), (hand[0] - 1, hand[1] - 1, 3, 3))
    # sivri başlık; yüz boşluğu (gözler parıltıyla çizilir)
    pygame.draw.polygon(S, cm, [(ox - 6, oy + 6), (ox - 5, oy - 4), (ox + 3, oy - 12), (ox + 1, oy - 4), (ox + 6, oy + 6)])
    pygame.draw.line(S, cl, (ox - 5, oy - 3), (ox + 2, oy - 11))
    pygame.draw.polygon(S, (6, 4, 10), [(ox - 4, oy + 5), (ox - 3, oy - 1), (ox + 3, oy - 1), (ox + 4, oy + 5)])
    return outline_sprite(S)


class OrbitBolt(Bolt):
    """Bekçinin etrafında dönen kor; süresi dolunca dışarı savrulur."""

    def __init__(self, owner, ang, hold):
        cx, cy = owner.core()
        super().__init__(cx, cy, 0.0, 0.0, h=20)
        self.owner, self.ang, self.hold, self.r = owner, ang, hold, 10.0

    def update(self, dt):
        if self.hold > 0:
            self.hold -= dt
            self.trail.append((self.x, self.y))
            self.trail = self.trail[-6:]
            self.ang += 3.2 * dt
            self.r = min(self.r + 30 * dt, 44)
            cx, cy = self.owner.core()
            self.x, self.y = cx + math.cos(self.ang) * self.r, cy + math.sin(self.ang) * self.r * 0.8
            if self.hold <= 0:
                self.vx = math.cos(self.ang) * BOLT_SPEED * 1.2
                self.vy = math.sin(self.ang) * BOLT_SPEED * 1.2
            return
        super().update(dt)


class PyreBoss(Boss):
    """Kor Bekçisi: uzak durur; sarmal kor, ateş sütunu yürüyüşü, alevle ışınlanma; öfkede dönen korlar."""

    NAME = "KOR BEKÇİSİ"
    LIGHT = "pyre"

    def __init__(self, x, y, hp, floor):
        super().__init__(x, y, hp, floor)
        self.name = self.NAME
        self.tint = (0, 0, 0) if floor <= 3 else (-20, 10, 30)
        self.bob = 0.0
        self.spin = 0.0
        self.shots = 0
        self.fade = 1.0   # ışınlanırken görünürlük

    def body_rect(self):
        return pygame.Rect(int(self.x) - 9, int(self.y - self.hover()) - 40, 18, 38)

    def hover(self):
        return 8 + math.sin(self.bob) * 2

    def core(self):
        return self.x, self.y - self.hover() - 26

    def active(self):
        return self.state not in ("spawn", "blink_out") and not self.dead

    def choose(self, game):
        opts = [("spiral", 3), ("pillars", 3), ("blink", 2)]
        if self.phase == 2:
            opts.append(("orbs", 3))
            if sum(1 for e in game.enemies if isinstance(e, Wisp)) < 2:
                opts.append(("summon", 1))
        opts = [o for o in opts if o[0] != self.last]
        pick = random.choices([o[0] for o in opts], [o[1] for o in opts])[0]
        self.last = pick
        if pick == "spiral":
            self.to("spiral_wind", 0.6)
        elif pick == "pillars":
            self.to("pillar_wind", 0.7)
        elif pick == "blink":
            self.to("blink_out", 0.45)
            game.sfx.play("dash")
        elif pick == "orbs":
            self.to("orb_wind", 0.6)
            game.sfx.play("roar", 0.4)
        else:
            self.to("summon_wind", 0.9)
            game.sfx.play("roar", 0.5)

    def update(self, dt, p, game):
        self.flash = max(0.0, self.flash - dt)
        self.invuln = max(0.0, self.invuln - dt)
        self.timer -= dt
        self.bob += dt * 2.5
        self.shown += (self.hp - self.shown) * min(1.0, dt * 2.5)
        sp = (1.3 if self.phase == 2 else 1.0) * self.mul
        dx, dy = p.x - self.x, p.y - self.y
        dist = math.hypot(dx, dy)
        ux, uy = norm(dx, dy)
        if dx:
            self.face = 1 if dx > 0 else -1
        arm_to = 0.0
        st = self.state
        embers = [(255, 200, 90), (235, 110, 50), (150, 40, 30)]
        cx, cy = self.core()
        if random.random() < dt * 6 and st != "blink_out":  # cüppeden düşen korlar
            game.fx.burst(self.x + random.uniform(-10, 10), self.y - 6, 1, embers, speed=10, life=0.8, grav=-25)

        if st == "spawn":
            if random.random() < 0.6:
                game.fx.burst(self.x + random.uniform(-14, 14), self.y - 2, 2, embers, speed=40, life=0.8, grav=-60)
            game.shake = max(game.shake, 1.2)
            if self.timer <= 0:
                self.to("roar", 1.3)
                game.sfx.play("roar")
            return
        if st == "roar":
            arm_to = 1.0
            self.fade = 1.0
            game.shake = max(game.shake, 2.5)
            if random.random() < 0.8:
                game.fx.burst(cx, cy - 8, 3, embers, speed=100, life=0.6, grav=-40)
            if self.timer <= 0:
                self.to("walk", 0)
                self.next_t = 0.5
        elif st == "walk":  # orta mesafede süzülür, yana kayar
            want = -1 if dist < 70 else 1 if dist > 110 else 0
            vx = ux * want - uy * 0.7
            vy = uy * want + ux * 0.7
            self.move(vx * 30 * sp, vy * 30 * sp, dt)
            self.x, self.y = self.clamp(self.x, self.y)
            self.next_t -= dt
            if self.next_t <= 0:
                self.choose(game)
        elif st == "spiral_wind":
            arm_to = 1.0
            if self.timer <= 0:
                self.spin = math.atan2(dy, dx)
                self.shots = 0
                self.to("spiral", 1.8 if self.phase == 1 else 2.2)
        elif st == "spiral":
            arm_to = 1.0
            interval = 0.11 if self.phase == 1 else 0.09
            elapsed = (1.8 if self.phase == 1 else 2.2) - self.timer
            while self.shots * interval <= elapsed:
                arms = 2 if self.phase == 1 else 3
                for k in range(arms):
                    a = self.spin + self.shots * 0.32 + k * math.tau / arms
                    game.bolts.append(Bolt(cx, cy, math.cos(a) * BOLT_SPEED * 0.95,
                                           math.sin(a) * BOLT_SPEED * 0.95, h=26))
                self.shots += 1
                if self.shots % 3 == 0:
                    game.sfx.play("shoot", 0.4)
            if self.timer <= 0:
                self.to("recover", 0.8)
        elif st == "pillar_wind":
            arm_to = 0.6
            if self.timer <= 0:  # oyuncuya doğru yürüyen ateş sütunları
                lines = [math.atan2(dy, dx)]
                if self.phase == 2:
                    lines += [lines[0] - 0.5, lines[0] + 0.5]
                for la in lines:
                    for i in range(7 + self.floor // 2):
                        hx, hy = self.x + math.cos(la) * (22 + i * 18), self.y + math.sin(la) * (22 + i * 18)
                        if not (24 <= hx <= W - 24 and 40 <= hy <= WORLD_H - 14) or feet_blocked(hx, hy):
                            break
                        game.hazards.append(Hazard(hx, hy, 10, 0.55 + i * 0.09, "pillar"))
                game.sfx.play("charge", 0.6)
                self.to("recover", 0.9)
        elif st == "blink_out":  # alevlere karışıp kaybolur
            self.fade = max(0.0, self.timer / 0.45)
            if random.random() < 0.8:
                game.fx.burst(self.x + random.uniform(-8, 8), self.y - random.uniform(4, 36), 2, embers,
                              speed=50, life=0.5, grav=-80)
            if self.timer <= 0:
                for _try in range(20):  # oyuncudan uzak, yürünebilir bir yer
                    nx, ny = random.uniform(50, W - 50), random.uniform(56, WORLD_H - 30)
                    if math.hypot(nx - p.x, ny - p.y) > 80 and not feet_blocked(nx, ny):
                        self.x, self.y = nx, ny
                        break
                game.fx.ring(self.x, self.y - 20, 20, (255, 160, 60), 90, 0.4)
                self.to("blink_in", 0.35)
        elif st == "blink_in":
            self.fade = 1 - max(0.0, self.timer / 0.35)
            arm_to = 0.8
            if self.timer <= 0:
                self.fade = 1.0
                base = math.atan2(p.y - 6 - cy, p.x - cx)
                n = 3 if self.phase == 1 else 5
                for i in range(n):
                    a = base + (i - (n - 1) / 2) * 0.22
                    game.bolts.append(Bolt(cx, cy, math.cos(a) * BOLT_SPEED * 1.25,
                                           math.sin(a) * BOLT_SPEED * 1.25, h=26))
                game.sfx.play("shoot")
                self.to("recover", 0.7)
        elif st == "orb_wind":
            arm_to = 1.0
            if self.timer <= 0:
                n = 6 + self.floor // 2
                for i in range(n):
                    game.bolts.append(OrbitBolt(self, math.tau * i / n, 2.0))
                game.sfx.play("shoot", 0.6)
                self.to("recover", 1.2)
        elif st == "summon_wind":
            arm_to = 1.0
            if random.random() < 0.5:
                game.fx.burst(cx, cy, 2, embers, speed=60, life=0.6, grav=-40)
            if self.timer <= 0:
                for side in (-1, 1):
                    gx, gy = self.clamp(self.x + side * 40, self.y + 10)
                    if not feet_blocked(gx, gy):
                        game.spawn_queue.append(Wisp(gx, gy, 3 + game.room.depth // 5))
                game.sfx.play("spawn")
                self.to("recover", 0.6)
        elif st == "recover":
            if self.timer <= 0:
                self.to("walk", 0)
                self.next_t = random.uniform(0.6, 1.1) / sp
        self.arm += (arm_to - self.arm) * min(1.0, dt * 10)

    def sprite(self):
        flame = int(self.bob * 3) % 3
        key = ("pyre", round(self.arm * 4), flame, self.tint)
        if key not in Boss.CACHE:
            Boss.CACHE[key] = render_pyre(key[1] / 4, flame, self.tint)
        img = Boss.CACHE[key]
        if self.flash > 0 or (self.invuln > 0 and int(self.invuln * 12) % 2):
            img = img.copy()
            img.fill((120, 100, 80, 0), special_flags=pygame.BLEND_RGBA_ADD)
        if self.face < 0:
            img = pygame.transform.flip(img, True, False)
        if self.fade < 1:
            img = img.copy()
            img.set_alpha(int(255 * self.fade))
        return img

    def origin(self):
        jit = random.choice((-1, 0, 1)) if self.state in ("roar", "spiral_wind", "orb_wind") else 0
        return int(self.x) - 25 + jit, int(self.y - self.hover()) - 54

    def draw(self, surf):
        sw = 22 if self.state != "spawn" else 14
        pygame.draw.ellipse(surf, (8, 6, 10), (int(self.x) - sw // 2, int(self.y) - 3, sw, 5))
        if self.fade <= 0.02:
            return
        img = self.sprite()
        ox, oy = self.origin()
        if self.state == "spawn":  # yerden alev gibi yükselir
            h = max(1, int(img.get_height() * (1 - self.timer / self.SPAWN_TIME)))
            surf.blit(img, (ox, int(self.y) - 6 - h), (0, 0, img.get_width(), h))
        else:
            surf.blit(img, (ox, oy))

    def draw_lit(self, surf, t):
        if self.state == "spawn" or self.fade < 0.3:
            return
        ox, oy = self.origin()
        ex = ox + 25
        ey = oy + 19
        hot = self.state.endswith("wind") or self.state == "spiral"
        ecol = (255, 250, 200) if hot else (255, 190, 80)
        for d in (-3, 2):  # maskenin göz yarıkları
            surf.set_at((ex + d, ey), ecol)
            surf.set_at((ex + d + 1, ey), ecol)
        # avuçlardaki kor
        for side in (-1, 1):
            hx = ex + side * (15 + 4 * self.arm)
            hy = oy + 41 - 22 * self.arm
            r = 2 + (1 if hot and int(t * 12) % 2 else 0)
            pygame.draw.circle(surf, (235, 110, 50), (int(hx), int(hy)), r + 1)
            pygame.draw.circle(surf, (255, 230, 150), (int(hx), int(hy)), r - 1 if r > 1 else 1)
        if self.state in ("spiral_wind", "orb_wind"):  # toplanan kor halkası
            k = 1 - max(0.0, self.timer) / 0.6
            cx, cy = self.core()
            for j in range(8):
                a = t * 5 + j * math.tau / 8
                r = 26 - 18 * k
                surf.set_at((int(cx + math.cos(a) * r), int(cy + math.sin(a) * r * 0.8)), (255, 210, 120))

    def light(self):
        if self.fade < 0.3:
            return None
        cx, cy = self.core()
        return (self.LIGHT, cx, cy)


class ShadeClone(Enemy):
    """Gölge Bekçisi'nin yansıması: bir kez hedef alır, ileri atılır ve dağılır. Tek vuruşta söner."""

    SPAWN_TIME = 0.5

    def __init__(self, x, y, owner):
        super().__init__(x, y, 1)
        self.owner = owner
        self.dir = (1.0, 0.0)

    def body_rect(self):
        return pygame.Rect(int(self.x) - 6, int(self.y) - 34, 12, 34)

    def update(self, dt, p, game):
        self.flash = max(0.0, self.flash - dt)
        self.timer -= dt
        dx, dy = p.x - self.x, p.y - self.y
        if self.state == "spawn":
            if self.timer <= 0:
                self.state, self.timer = "aim", 0.6
            return
        if self.state == "aim":
            if self.timer > 0.15:
                self.dir = norm(dx, dy)
                if dx:
                    self.face = 1 if dx > 0 else -1
            if self.timer <= 0:
                self.state, self.timer = "dash", 0.45
                game.sfx.play("dash", 0.5)
        elif self.state == "dash":
            nx, ny = self.x + self.dir[0] * 240 * dt, self.y + self.dir[1] * 240 * dt
            if feet_blocked(nx, ny) or not (20 < nx < W - 20 and 30 < ny < WORLD_H - 10):
                self.timer = 0
            else:
                self.x, self.y = nx, ny
            if random.random() < 0.6:
                game.fx.burst(self.x, self.y - 14, 2, [(52, 42, 84), (30, 24, 50)], speed=20, life=0.4)
            if self.body_rect().colliderect(p.body_rect()):
                game.player_hit(self.x, self.y)
            if self.timer <= 0:
                self.dead = True
                game.fx.burst(self.x, self.y - 16, 16, [(52, 42, 84), (80, 66, 120), (20, 16, 30)],
                              speed=50, life=0.7, grav=-30)
        elif self.state == "recover":
            if self.timer <= 0:
                self.state, self.timer = "aim", 0.5

    def draw(self, surf):
        key = ("clone", self.state == "dash")
        if key not in Boss.CACHE:
            img = render_shade(2 if key[1] else 1, (0, 0, 0), ghost=True)
            img.set_alpha(170)
            Boss.CACHE[key] = img
        img = Boss.CACHE[key]
        if self.face < 0:
            img = pygame.transform.flip(img, True, False)
        if self.state == "spawn":
            img = img.copy()
            img.set_alpha(int(170 * (1 - self.timer / self.SPAWN_TIME)))
        surf.blit(img, (int(self.x) - 29, int(self.y) - 59))

    def draw_lit(self, surf, t):
        if self.state == "spawn":
            return
        ex = int(self.x) - 29 + (29 if self.face > 0 else 27)
        ey = int(self.y) - 59 + 17
        for d in (-2, 1):
            surf.set_at((ex + d * self.face, ey), (170, 150, 255))
        if self.state == "aim":
            for d in range(10, 110, 6):
                px, py = int(self.x + self.dir[0] * d), int(self.y - 6 + self.dir[1] * d)
                if 0 <= px < W and 0 <= py < WORLD_H and int(t * 20 + d / 6) % 2:
                    surf.set_at((px, py), (150, 110, 255))


class ShadeBoss(Boss):
    """Gölge Bekçisi: hızlı ve sinsi. Kaybolup arkandan biçer, art arda atılır; öfkede yansımalar çağırır
    ve odanın ışığını yutar."""

    NAME = "GÖLGE BEKÇİSİ"
    LIGHT = "shade"

    def __init__(self, x, y, hp, floor):
        super().__init__(x, y, hp, floor)
        self.name = self.NAME
        self.tint = (0, 0, 0) if floor <= 3 else (30, -6, -10)
        self.pose = 0
        self.fade = 1.0
        self.dashes = 0
        self.dash_t = 0.0

    def body_rect(self):
        return pygame.Rect(int(self.x) - 8, int(self.y) - 44, 16, 44)

    def core(self):
        return self.x, self.y - 26

    def active(self):
        return self.state not in ("spawn", "vanish", "lurk") and not self.dead

    def choose(self, game):
        opts = [("reap", 3), ("dash", 3), ("vanish", 3)]
        if self.phase == 2 and sum(1 for e in game.enemies if isinstance(e, ShadeClone)) == 0:
            opts.append(("clones", 2))
        opts = [o for o in opts if o[0] != self.last]
        pick = random.choices([o[0] for o in opts], [o[1] for o in opts])[0]
        self.last = pick
        if pick == "reap":
            self.to("approach", 1.4)
        elif pick == "dash":
            self.dashes = (2 if self.phase == 1 else 3) + (self.floor > 3)
            self.to("dash_wind", 0.65)
        elif pick == "vanish":
            self.to("vanish", 0.4)
            game.sfx.play("dash", 0.6)
        else:
            self.to("clone_wind", 0.8)
            game.sfx.play("roar", 0.4)

    def strike(self, game):
        """Orak savuruşu: önündeki yarım halkayı uyarıyla işaretler."""
        game.hazards.append(Hazard(self.x + self.face * 10, self.y, 30, 0.5 if self.phase == 1 else 0.38, "reap"))
        self.to("reap_wind", 0.5 if self.phase == 1 else 0.38)

    def update(self, dt, p, game):
        self.flash = max(0.0, self.flash - dt)
        self.invuln = max(0.0, self.invuln - dt)
        self.timer -= dt
        self.shown += (self.hp - self.shown) * min(1.0, dt * 2.5)
        sp = (1.25 if self.phase == 2 else 1.0) * self.mul
        dx, dy = p.x - self.x, p.y - self.y
        dist = math.hypot(dx, dy)
        ux, uy = norm(dx, dy)
        st = self.state
        shadow = [(52, 42, 84), (30, 24, 50), (80, 66, 120)]
        pose = 0
        # öfkede oda kararır
        want_dark = 0.6 if self.phase == 2 else 0.25
        game.darkness += (want_dark - game.darkness) * min(1.0, dt * 1.5)

        if st == "spawn":
            if random.random() < 0.6:
                game.fx.burst(self.x + random.uniform(-16, 16), self.y - 2, 2, shadow, speed=30, life=0.9, grav=-30)
            game.shake = max(game.shake, 1.2)
            if self.timer <= 0:
                self.to("roar", 1.2)
                game.sfx.play("roar")
            return
        if st == "roar":
            pose = 1
            self.fade = 1.0
            game.shake = max(game.shake, 2.5)
            if random.random() < 0.7:
                game.fx.burst(self.x, self.y - 30, 3, shadow, speed=90, life=0.6, grav=-20)
            if self.timer <= 0:
                self.to("walk", 0)
                self.next_t = 0.5
        elif st == "walk":  # ağır ağır yaklaşır, sonra seçer
            if dist > 40:
                self.move(ux * 34 * sp, uy * 34 * sp, dt)
                self.x, self.y = self.clamp(self.x, self.y)
            if dx:
                self.face = 1 if dx > 0 else -1
            self.next_t -= dt
            if self.next_t <= 0:
                self.choose(game)
        elif st == "approach":  # hızla yanaşıp biçer
            if dx:
                self.face = 1 if dx > 0 else -1
            self.move(ux * 90 * sp, uy * 90 * sp, dt)
            self.x, self.y = self.clamp(self.x, self.y)
            if random.random() < 0.4:
                game.fx.burst(self.x, self.y - 4, 1, shadow, speed=15, life=0.5)
            if dist < 30 or self.timer <= 0:
                self.strike(game)
        elif st == "reap_wind":
            pose = 1
            if self.timer <= 0:
                self.to("reap", 0.35)
                game.sfx.play("slash", 0.9)
                game.fx.burst(self.x + self.face * 18, self.y - 14, 14, [(190, 190, 210), (120, 110, 160)],
                              speed=110, life=0.3)
        elif st == "reap":
            pose = 2
            if self.timer <= 0:
                self.to("recover", 0.75 if self.phase == 1 else 0.5)
        elif st == "dash_wind":
            pose = 1
            if self.timer > 0.2:
                self.dir = (ux, uy)
                if dx:
                    self.face = 1 if dx > 0 else -1
            if self.timer <= 0:
                self.to("dash", 0.42)
                game.sfx.play("charge", 0.7)
        elif st == "dash":
            pose = 2
            nx = self.x + self.dir[0] * 260 * sp * dt
            ny = self.y + self.dir[1] * 260 * sp * dt
            cx, cy = self.clamp(nx, ny)
            if (abs(cx - nx) > 0.01 or abs(cy - ny) > 0.01) or feet_blocked(nx, ny):
                self.timer = 0
            else:
                self.x, self.y = nx, ny
            if random.random() < 0.8:
                game.fx.burst(self.x, self.y - 20, 2, shadow, speed=20, life=0.4)
            if self.body_rect().colliderect(p.body_rect()):
                game.player_hit(self.x, self.y)
            if self.timer <= 0:
                self.dashes -= 1
                self.to("dash_wind", 0.35) if self.dashes > 0 else self.to("recover", 0.9)
        elif st == "vanish":  # gölgeye erir
            self.fade = max(0.0, self.timer / 0.4)
            if random.random() < 0.8:
                game.fx.burst(self.x + random.uniform(-8, 8), self.y - random.uniform(4, 40), 2, shadow,
                              speed=40, life=0.5, grav=-50)
            if self.timer <= 0:
                self.fade = 0.0
                self.to("lurk", 0.8 if self.phase == 1 else 0.55)
        elif st == "lurk":  # görünmez; oyuncunun arkasına süzülür
            back = -p.face if p.face else 1
            tx, ty = self.clamp(p.x + back * 26, p.y)
            if feet_blocked(tx, ty):
                tx, ty = self.clamp(p.x - back * 26, p.y)
            self.x += (tx - self.x) * min(1.0, dt * 8)
            self.y += (ty - self.y) * min(1.0, dt * 8)
            if self.timer <= 0:
                self.face = 1 if p.x > self.x else -1
                self.fade = 1.0
                game.fx.burst(self.x, self.y - 22, 18, shadow, speed=60, life=0.5)
                game.sfx.play("spawn", 0.5)
                self.strike(game)
        elif st == "clone_wind":
            pose = 1
            if random.random() < 0.6:
                game.fx.burst(self.x, self.y - 20, 2, shadow, speed=50, life=0.6)
            if self.timer <= 0:
                n = 3 if self.floor > 3 else 2
                for i in range(n):
                    a = math.tau * i / n + random.uniform(0, 1)
                    gx, gy = self.clamp(p.x + math.cos(a) * 70, p.y + math.sin(a) * 50)
                    if not feet_blocked(gx, gy):
                        game.spawn_queue.append(ShadeClone(gx, gy, self))
                game.sfx.play("spawn")
                self.to("recover", 0.5)
        elif st == "recover":
            if self.timer <= 0:
                self.to("walk", 0)
                self.next_t = random.uniform(0.5, 1.0) / sp
        self.pose = pose

    def sprite(self):
        key = ("shade", self.pose, self.tint)
        if key not in Boss.CACHE:
            Boss.CACHE[key] = render_shade(self.pose, self.tint)
        img = Boss.CACHE[key]
        if self.flash > 0 or (self.invuln > 0 and int(self.invuln * 12) % 2):
            img = img.copy()
            img.fill((110, 100, 130, 0), special_flags=pygame.BLEND_RGBA_ADD)
        if self.face < 0:
            img = pygame.transform.flip(img, True, False)
        if self.fade < 1:
            img = img.copy()
            img.set_alpha(int(255 * self.fade))
        return img

    def origin(self):
        jit = random.choice((-1, 0, 1)) if self.state in ("roar", "dash_wind", "clone_wind") else 0
        return int(self.x) - 29 + jit, int(self.y) - 59

    def draw(self, surf):
        if self.state == "lurk":  # yalnızca yerde kayan bir gölge lekesi
            pygame.draw.ellipse(surf, (14, 10, 22), (int(self.x) - 9, int(self.y) - 3, 18, 5))
            return
        pygame.draw.ellipse(surf, (8, 6, 10), (int(self.x) - 10, int(self.y) - 3, 20, 6))
        if self.fade <= 0.02:
            return
        img = self.sprite()
        ox, oy = self.origin()
        if self.state == "spawn":
            h = max(1, int(img.get_height() * (1 - self.timer / self.SPAWN_TIME)))
            surf.blit(img, (ox, int(self.y) + 5 - h), (0, 0, img.get_width(), h))
        else:
            surf.blit(img, (ox, oy))

    def draw_lit(self, surf, t):
        if self.state == "spawn":
            return
        if self.state == "lurk":  # karanlıkta yalnızca gözler kayar
            if int(t * 6) % 3:
                for d in (-2, 1):
                    surf.set_at((int(self.x) + d, int(self.y) - 38), (120, 100, 200))
            return
        if self.fade < 0.3:
            return
        ox, oy = self.origin()
        ex, ey = ox + (30 if self.face > 0 else 27), oy + 17
        hot = self.state in ("reap_wind", "dash_wind", "clone_wind", "roar")
        ecol = (255, 255, 255) if hot else (190, 170, 255)
        for d in (-2, 1):
            surf.set_at((ex + d, ey), ecol)
            if hot:
                surf.set_at((ex + d, ey + 1), (120, 100, 220))
        if self.state == "dash_wind":  # atılma yönü uyarısı
            for d in range(14, 170, 6):
                px, py = int(self.x + self.dir[0] * d), int(self.y - 6 + self.dir[1] * d)
                if 0 <= px < W and 0 <= py < WORLD_H and int(t * 20 + d / 6) % 2:
                    surf.set_at((px, py), (160, 110, 255))
        if self.state == "reap":  # orağın bıraktığı ay biçimli iz
            k = 1 - max(0.0, self.timer) / 0.35
            r = 22 + 8 * k
            for j in range(16):
                a = -1.3 + 2.6 * j / 15
                px = int(self.x + self.face * math.cos(a) * r)
                py = int(self.y - 14 + math.sin(a) * r * 0.6)
                if 0 <= px < W and 0 <= py < WORLD_H:
                    surf.set_at((px, py), (230, 225, 255) if j % 2 else (140, 120, 220))

    def light(self):
        if self.state == "lurk" or self.fade < 0.3:
            return None
        return (self.LIGHT, self.x, self.y - 34)


BOSS_CLASSES = [Boss, PyreBoss, ShadeBoss]


def boss_info(floor):
    """Kata göre bekçi sınıfı ve adı. 4. kattan sonra üçü sırayla, 'kalbi sönmüş' olarak döner."""
    cls = BOSS_CLASSES[(floor - 1) % len(BOSS_CLASSES)]
    if floor <= len(BOSS_CLASSES):
        name = BOSS_NAMES[floor - 1]
    else:
        name = "SÖNMÜŞ " + BOSS_NAMES[(floor - 1) % len(BOSS_CLASSES)]
    return cls, name



class Oyku:
    """Prenses Öykü — mahzende renk kalan tek yerde bekler."""

    def __init__(self, x, y, ghost=False):
        self.x, self.y = x, y
        self.img = sprite_from_rows(OYKU, OYKU_PAL)
        self.face = 1
        self.ghost = ghost
        if ghost:  # anı odasında yarı saydam bir yankıdır
            self.img = self.img.copy()
            self.img.fill((205, 220, 255, 170), special_flags=pygame.BLEND_RGBA_MULT)

    def draw(self, surf, t, player):
        self.face = 1 if player.x > self.x else -1
        pygame.draw.ellipse(surf, (60, 110, 60), (int(self.x) - 6, int(self.y) - 2, 12, 4))
        img = self.img if self.face > 0 else pygame.transform.flip(self.img, True, False)
        bob = int(t * 2) % 2
        surf.blit(img, (int(self.x) - 6, int(self.y) - 17 + bob))
        if int(t * 3) % 4 == 0:  # tacında parıltı
            surf.set_at((int(self.x) - 2 + int(t * 3) % 3 * 2, int(self.y) - 18 + bob), (255, 255, 230))


MERCHANT_ROWS = [
    "....kkkk....", "...kppppk...", "..kppppppk..", "..kpkkkkpk..", "..kpkyykpk..", "..kppkkppk..",
    ".kppppppppk.", ".kpPppppPpk.", "kppPppppPppk", "kpppppppppyk", "kppPppppPkyk", ".kpPppppPpk.",
    ".kppppppppk.", ".kpPpPpPppk.", "kppppppppppk", ".kkkkkkkkkk.",
]
MERCHANT_PAL = {"k": (16, 12, 20), "p": (74, 56, 88), "P": (110, 84, 124), "y": (255, 210, 120)}


TANSI_ROWS = [  # uzun boylu, yapılı: güneş gözlüğü, deri ceket, beyaz tişört, kot, spor ayakkabı
    "....kkkkkkkk....", "...khhHHHhhhk...", "...khhhhhhhhk...", "...kssssssssk...", "...kggGgggGgk...",
    "...kssssssssk...", "...kssSSSSssk...", "....kssssssk....", ".....kSSSSk.....", "..kkkkwwwwkkkk..",
    ".kjjJjwcwwjJjjk.", "kjjJJjwwcwjJJjjk", "kjJJjjwwwwjjJJjk", "kjJjkjwwwwjkjJjk", "kjJjkjwwwwjkjJjk",
    "kjjjkjwwwwjkjjjk", "ksskkjjjjjjkkssk", ".kk.kddddddk.kk.", "....kdDddDdk....", "....kdDddDdk....",
    "....kdDkkDdk....", "....kdDkkDdk....", "....kdDkkDdk....", "....kdDkkDdk....", "....kddkkddk....",
    "...knnnkknnnk...", "...knnnkknnnk...", "...krrrkkrrrk...",
]
TANSI_PAL = {"k": (16, 12, 18), "h": (34, 26, 30), "H": (66, 50, 54), "s": (214, 160, 120), "S": (176, 120, 88),
             "g": (20, 20, 26), "G": (130, 210, 240), "j": (46, 52, 70), "J": (84, 94, 122), "w": (236, 236, 240),
             "c": (230, 190, 90), "d": (52, 84, 130), "D": (84, 120, 170), "n": (242, 242, 242), "r": (210, 60, 50)}
DOG_ROWS = [  # kahverengi Fransız bulldog: yarasa kulak, basık burun, tıknaz gövde
    ".kk..kk.......", ".kbk.kbk......", "kbBbkbBbk.....", "kBnBBBnBk.....", "kbBBBBBbkkkkk.",
    "kBwnnnwBbbbbbk", ".kkwwwkbBBBbbk", "..kbwbbBBBbbbk", "..kbwbbbbbbbbk", "..kbbkkkkkkbbk",
    "..kbk.....kbk.", "..kkk.....kkk.",
]
DOG_PAL = {"k": (22, 14, 12), "b": (138, 86, 48), "B": (178, 122, 74), "n": (14, 10, 10), "w": (232, 220, 204),
           "t": (240, 120, 130)}
TANSI_WARES = ["t_kalp", "t_guc", "t_hiz", "t_kalkan"]


class Merchant:
    """Kör Tüccar: kül karşılığı armağan satar. Tansi aynı tezgâhı kullanır."""

    def __init__(self, x, y, tansi=False):
        self.x, self.y = x, y
        self.img = sprite_from_rows(TANSI_ROWS, TANSI_PAL) if tansi else sprite_from_rows(MERCHANT_ROWS, MERCHANT_PAL)
        self.dog = sprite_from_rows(DOG_ROWS, DOG_PAL) if tansi else None

    def draw(self, surf, t, player):
        w, h = self.img.get_size()
        pygame.draw.ellipse(surf, (8, 6, 10), (int(self.x) - w // 2 - 1, int(self.y) - 2, w + 2, 4))
        surf.blit(self.img, (int(self.x) - w // 2, int(self.y) - h + int(t * 1.5) % 2))
        if self.dog:
            self.draw_dog(surf, t, player)

    def draw_dog(self, surf, t, player):
        x, y = int(self.x) + 13, int(self.y) + 1
        pygame.draw.ellipse(surf, (8, 6, 10), (x, y - 2, 14, 3))
        pant = int(t * 5) % 2
        wag = int(t * (12 if math.hypot(player.x - self.x, player.y - self.y) < 40 else 4)) % 2
        surf.blit(self.dog, (x, y - 12 + (0 if pant else 1) * 0))
        if pant:  # dil dışarıda
            surf.set_at((x + 4, y - 5), DOG_PAL["t"])
            surf.set_at((x + 4, y - 4), DOG_PAL["t"])
        surf.set_at((x + 14, y - 8 - wag), DOG_PAL["b"])  # kuyruk sallanır
        surf.set_at((x + 14, y - 7), DOG_PAL["k"])


def draw_chest(surf, room, t):
    c = room.chest
    if not c or c.get("gone"):
        return
    x, y = c["x"] - 8, c["y"] - 14
    body, lid, trim = (96, 62, 38), (150, 100, 56), (222, 176, 80)
    pygame.draw.ellipse(surf, (8, 6, 10), (x - 1, y + 11, 18, 4))
    pygame.draw.rect(surf, body, (x, y + 5, 16, 8))
    pygame.draw.rect(surf, (14, 11, 16), (x, y + 5, 16, 8), 1)
    if c["open"]:
        pygame.draw.rect(surf, (30, 16, 20), (x + 2, y + 5, 12, 3))
        pygame.draw.rect(surf, lid, (x, y - 2, 16, 5))
        pygame.draw.rect(surf, (14, 11, 16), (x, y - 2, 16, 5), 1)
    else:
        pygame.draw.rect(surf, lid, (x, y, 16, 6))
        pygame.draw.rect(surf, (14, 11, 16), (x, y, 16, 6), 1)
        pygame.draw.line(surf, trim, (x + 1, y + 5), (x + 14, y + 5))
        pygame.draw.rect(surf, trim, (x + 7, y + 4, 2, 4))


def draw_spikes(surf, game, t):
    """Işıktan sonra çizilir: karanlıkta bile tuzak okunabilsin."""
    room = game.room
    if room.cleared:
        return
    for (tx, ty), grp in room.spikes.items():
        st = game.spike_state(grp)
        x, y = tx * TILE, ty * TILE
        if st == 1:
            for hx, hy in ((4, 4), (11, 4), (4, 11), (11, 11), (7, 7)):
                surf.set_at((x + hx, y + hy), (255, 90, 50) if int(t * 14) % 2 else (150, 40, 30))
        elif st == 2:
            for hx, hy in ((4, 8), (11, 8), (7, 11), (4, 15), (11, 15)):
                pygame.draw.polygon(surf, (196, 190, 196), [(x + hx - 2, y + hy), (x + hx + 2, y + hy),
                                                             (x + hx, y + hy - 7)])
                surf.set_at((x + hx, y + hy - 6), (250, 245, 240))


class Ash:
    """Havada süzülen kül ve korlar — sığınakta ise yavaşça düşen çiçek yaprakları."""

    def __init__(self, rng):
        self.rng = rng
        self.parts = []
        self.haven = False

    def set_haven(self, on):
        if on != self.haven:
            self.haven = on
            self.parts = []

    def update(self, dt):
        rng = self.rng
        if self.haven:
            if rng.random() < 0.25:
                c = rng.choice([(255, 150, 190), (255, 255, 255), (255, 210, 120), (255, 180, 210)])
                self.parts.append([rng.uniform(0, W), 1.0, rng.uniform(4, 12), rng.uniform(8, 16),
                                   rng.uniform(8, 14), c])
        elif rng.random() < 0.35:
            ember = rng.random() < 0.18
            self.parts.append([
                rng.uniform(0, W), WORLD_H + 2,
                rng.uniform(-6, 6), rng.uniform(-18, -8),
                rng.uniform(4, 9), ember,
            ])
        for p in self.parts:
            p[0] += (p[2] + math.sin(p[1] * 0.05) * 6) * dt
            p[1] += p[3] * dt
            p[4] -= dt
        self.parts = [p for p in self.parts if p[4] > 0 and 0 <= p[1] < WORLD_H and 0 <= p[0] < W]

    def draw(self, surf):
        for x, y, _, _, life, kind in self.parts:
            if self.haven:
                surf.set_at((int(x), int(y)), kind)
                if int(y) % 6 < 3 and int(x) + 1 < W:
                    surf.set_at((int(x) + 1, int(y)), kind)
                continue
            if kind:
                c = (230, 110, 50) if life > 2 else (120, 50, 30)
            else:
                c = (70, 64, 76)
            surf.set_at((int(x), int(y)), c)


def draw_torch(surf, tx, ty, t):
    x, y = tx * TILE + 6, ty * TILE + 4
    pygame.draw.rect(surf, (40, 30, 26), (x + 1, y + 6, 2, 5))
    pygame.draw.rect(surf, (70, 50, 40), (x, y + 5, 4, 2))
    flick = int(t * 10) % 3
    pygame.draw.rect(surf, (220, 90, 40), (x, y + 2 - (flick == 1), 4, 4))
    pygame.draw.rect(surf, (255, 200, 90), (x + 1, y + 3, 2, 2))
    if flick == 2:
        surf.set_at((x + 1, y), (255, 160, 70))


def draw_door(surf, room, t):
    """Çıkış kapısının demir parmaklıkları; açılınca yukarı çekilir."""
    x = room.door_col * TILE
    drop = int(13 * (1 - room.door_anim))
    if room.door_anim > 0:  # ötesinden gelen soğuk ışıltı
        for i in range(3):
            yy = 4 + i * 4 + int(t * 6 + i) % 3
            surf.set_at((x + 5 + (i * 3) % 6, yy), (90, 80, 140))
    for bx in range(4, 13, 3):
        if drop > 0:
            pygame.draw.line(surf, (70, 64, 80), (x + bx, 3), (x + bx, 2 + drop))
            surf.set_at((x + bx, 2 + drop), (40, 36, 46))
    if drop > 4:
        pygame.draw.line(surf, (70, 64, 80), (x + 3, 2 + drop // 2), (x + 12, 2 + drop // 2))


def draw_altar_fire(surf, room, t):
    if not room.altar:
        return
    ax, ay = room.altar[0] * TILE, room.altar[1] * TILE
    cx = ax + 16
    if room.altar_used:
        pygame.draw.rect(surf, (90, 30, 20), (cx - 3, ay, 6, 2))
        return
    for i in range(7):
        h = 4 + int(3 * math.sin(t * 9 + i * 1.7)) + (3 - abs(i - 3))
        col = (255, 220, 120) if abs(i - 3) <= 1 else (235, 110, 50)
        pygame.draw.line(surf, col, (cx - 3 + i, ay + 1), (cx - 3 + i, ay + 1 - h))


# --- Piksel yazı tipi --------------------------------------------------------------
# Düşük çözünürlükte vektör yazı bulanıklaşıyor; harfler burada elle çizilmiş bitmap.
# Her harf: (üstten boşluk, satırlar). Hücre 11 satır: 0-1 şapka, 2-8 gövde, 9-10 kuyruk.
GLYPHS = {
    "A": (2, ".###./#...#/#...#/#####/#...#/#...#/#...#"), "B": (2, "####./#...#/#...#/####./#...#/#...#/####."),
    "C": (2, ".###./#...#/#..../#..../#..../#...#/.###."), "D": (2, "####./#...#/#...#/#...#/#...#/#...#/####."),
    "E": (2, "#####/#..../#..../####./#..../#..../#####"), "F": (2, "#####/#..../#..../####./#..../#..../#...."),
    "G": (2, ".###./#...#/#..../#.###/#...#/#...#/.###."), "H": (2, "#...#/#...#/#...#/#####/#...#/#...#/#...#"),
    "I": (2, "###/.#./.#./.#./.#./.#./###"), "J": (2, "..###/...#./...#./...#./...#./#..#./.##.."),
    "K": (2, "#...#/#..#./#.#../##.../#.#../#..#./#...#"), "L": (2, "#..../#..../#..../#..../#..../#..../#####"),
    "M": (2, "#...#/##.##/#.#.#/#.#.#/#...#/#...#/#...#"), "N": (2, "#...#/##..#/##..#/#.#.#/#..##/#..##/#...#"),
    "O": (2, ".###./#...#/#...#/#...#/#...#/#...#/.###."), "P": (2, "####./#...#/#...#/####./#..../#..../#...."),
    "Q": (2, ".###./#...#/#...#/#...#/#.#.#/#..#./.##.#"), "R": (2, "####./#...#/#...#/####./#.#../#..#./#...#"),
    "S": (2, ".####/#..../#..../.###./....#/....#/####."), "T": (2, "#####/..#../..#../..#../..#../..#../..#.."),
    "U": (2, "#...#/#...#/#...#/#...#/#...#/#...#/.###."), "V": (2, "#...#/#...#/#...#/#...#/#...#/.#.#./..#.."),
    "W": (2, "#...#/#...#/#...#/#.#.#/#.#.#/##.##/#...#"), "X": (2, "#...#/#...#/.#.#./..#../.#.#./#...#/#...#"),
    "Y": (2, "#...#/#...#/.#.#./..#../..#../..#../..#.."), "Z": (2, "#####/....#/...#./..#../.#.../#..../#####"),
    "a": (4, ".###./....#/.####/#...#/.####"), "b": (2, "#..../#..../####./#...#/#...#/#...#/####."),
    "c": (4, ".###/#.../#.../#.../.###"), "d": (2, "....#/....#/.####/#...#/#...#/#...#/.####"),
    "e": (4, ".###./#...#/#####/#..../.###."), "f": (2, "..##/.#../####/.#../.#../.#../.#.."),
    "g": (4, ".####/#...#/#...#/#...#/.####/....#/.###."), "h": (2, "#..../#..../####./#...#/#...#/#...#/#...#"),
    "i": (2, "#/./#/#/#/#/#"), "ı": (4, "#/#/#/#/#"), "j": (2, "..#/.../..#/..#/..#/..#/..#/#.#/.#."),
    "k": (2, "#.../#.../#..#/#.#./##../#.#./#..#"), "l": (2, "#./#./#./#./#./#./.#"),
    "m": (4, "####./#.#.#/#.#.#/#.#.#/#.#.#"), "n": (4, "####./#...#/#...#/#...#/#...#"),
    "o": (4, ".###./#...#/#...#/#...#/.###."), "p": (4, "####./#...#/#...#/#...#/####./#..../#...."),
    "q": (4, ".####/#...#/#...#/#...#/.####/....#/....#"), "r": (4, "#.##/##../#.../#.../#..."),
    "s": (4, ".####/#..../.###./....#/####."), "t": (2, ".#../.#../####/.#../.#../.#../..##"),
    "u": (4, "#...#/#...#/#...#/#...#/.####"), "v": (4, "#...#/#...#/#...#/.#.#./..#.."),
    "w": (4, "#...#/#...#/#.#.#/#.#.#/.#.#."), "x": (4, "#...#/.#.#./..#../.#.#./#...#"),
    "y": (4, "#...#/#...#/#...#/#...#/.####/....#/.###."), "z": (4, "#####/...#./..#../.#.../#####"),
    "0": (2, ".###./#...#/#..##/#.#.#/##..#/#...#/.###."), "1": (2, ".#./##./.#./.#./.#./.#./###"),
    "2": (2, ".###./#...#/....#/...#./..#../.#.../#####"), "3": (2, "####./....#/....#/.###./....#/....#/####."),
    "4": (2, "...#./..##./.#.#./#..#./#####/...#./...#."), "5": (2, "#####/#..../####./....#/....#/#...#/.###."),
    "6": (2, ".###./#..../#..../####./#...#/#...#/.###."), "7": (2, "#####/....#/...#./..#../..#../..#../..#.."),
    "8": (2, ".###./#...#/#...#/.###./#...#/#...#/.###."), "9": (2, ".###./#...#/#...#/.####/....#/....#/.###."),
    ".": (8, "#"), ",": (7, ".#/.#/#."), ":": (4, "#/./././#"), ";": (4, ".#/../../.#/.#/#."),
    "!": (2, "#/#/#/#/#/./#"), "?": (2, ".###./#...#/....#/...#./..#../...../..#.."),
    "'": (2, "#/#"), '"': (2, "#.#/#.#"), "-": (5, "###"), "+": (4, "..#../..#../#####/..#../..#.."),
    "=": (4, "####/..../####"), "/": (2, "....#/...#./...#./..#../.#.../.#.../#...."),
    "(": (2, ".#/#./#./#./#./#./.#"), ")": (2, "#./.#/.#/.#/.#/.#/#."),
    "%": (2, "##..#/##.#./...#./..#../.#.../.#.##/#..##"), ">": (3, "#.../.#../..#./...#/..#./.#../#..."),
    "<": (3, "...#/..#./.#../#.../.#../..#./...#"), "*": (3, "#.#/.#./#.#"), "_": (8, "####"),
    "·": (5, "##/##"), "—": (5, "#####"), "[": (2, "##/#./#./#./#./#./##"), "]": (2, "##/.#/.#/.#/.#/.#/##"),
}
_MARKS = {  # Türkçe harfler temel harfe işaret eklenerek türetilir: (satır, desen)
    "ö": ("o", [(2, ".#.#.")]), "ü": ("u", [(2, ".#.#.")]), "Ö": ("O", [(0, ".#.#.")]), "Ü": ("U", [(0, ".#.#.")]),
    "ç": ("c", [(9, ".#.."), (10, "##..")]), "ş": ("s", [(9, "..#.."), (10, ".##..")]),
    "Ç": ("C", [(9, "..#.."), (10, ".##..")]), "Ş": ("S", [(9, "..#.."), (10, ".##..")]),
    "ğ": ("g", [(2, "#...#"), (3, ".###.")]), "Ğ": ("G", [(0, "#...#"), (1, ".###.")]),
    "İ": ("I", [(0, ".#.")]), "â": ("a", [(2, "..#.."), (3, ".#.#.")]),
}


class PixelFont:
    """pygame.font.Font gibi kullanılır (render, size); her harf tam piksele oturur."""

    HEIGHT = 11
    CACHE_MAX = 1500

    def __init__(self, scale=1):
        self.scale = scale
        self.lift = 3 if scale > 1 else 0  # büyük yazıda şapka boşluğunu telafi eder
        self.cells = {}
        self.cache = {}
        for ch, (top, rows) in GLYPHS.items():
            self.cells[ch] = self._cell(top, rows.split("/"))
        for ch, (base, marks) in _MARKS.items():
            cell = [list(r) for r in self.cells[base]]
            for row, pat in marks:
                for i, c in enumerate(pat):
                    if c == "#" and i < len(cell[row]):
                        cell[row][i] = "#"
            self.cells[ch] = ["".join(r) for r in cell]
        self.space = 3

    def _cell(self, top, rows):
        w = max(len(r) for r in rows)
        cell = ["." * w for _ in range(self.HEIGHT)]
        for i, r in enumerate(rows):
            cell[top + i] = r.ljust(w, ".")
        return cell

    def size(self, s):
        w = 0
        for ch in s:
            cell = self.cells.get(ch)
            w += self.space + 1 if ch == " " or cell is None else len(cell[0]) + 1
        return max(0, w - 1) * self.scale, self.HEIGHT * self.scale

    def render(self, s, aa, col):
        key = (s, col)
        img = self.cache.get(key)
        if img is not None:
            return img
        w = self.size(s)[0] // self.scale
        img = pygame.Surface((max(1, w), self.HEIGHT), pygame.SRCALPHA)
        x = 0
        for ch in s:
            cell = self.cells.get(ch)
            if ch == " " or cell is None:
                x += self.space + 1
                continue
            for yy, row in enumerate(cell):
                for xx, c in enumerate(row):
                    if c == "#":
                        img.set_at((x + xx, yy), col)
            x += len(cell[0]) + 1
        if self.scale > 1:
            img = pygame.transform.scale(img, (img.get_width() * self.scale, self.HEIGHT * self.scale))
        if len(self.cache) >= self.CACHE_MAX:
            self.cache.clear()
        self.cache[key] = img
        return img


# --- Arayüz ------------------------------------------------------------------------
ICONS = {}


def icon(key):
    if key not in ICONS:
        ICONS[key] = sprite_from_rows((BOONS.get(key) or PACTS.get(key) or SPIRITS[key])["icon"], ICON_PAL)
    return ICONS[key]


def text(surf, font, s, x, y, col, center=False, shadow=True):
    img = font.render(s, False, col)
    y -= font.lift
    if center:
        x -= img.get_width() // 2
    if shadow:
        surf.blit(font.render(s, False, (0, 0, 0)), (x + 1, y + 1))
    surf.blit(img, (x, y))
    return img.get_width()


def draw_hud(surf, font, game):
    player = game.player
    top = WORLD_H
    pygame.draw.rect(surf, (8, 6, 12), (0, top, W, H - top))
    pygame.draw.line(surf, (44, 38, 60), (0, top), (W, top))
    x = 6
    for i in range(player.max_hp):
        full = i < player.hp
        for y, row in enumerate(HEART):
            for hx, ch in enumerate(row):
                if ch == ".":
                    continue
                c = (10, 8, 14) if ch == "k" else (200, 40, 50) if full else (40, 30, 44)
                surf.set_at((x + i * 8 + hx, top + 3 + y), c)
    ready = 1 - player.dash_cd / (DASH_COOLDOWN * player.dash_cd_mul)
    pygame.draw.rect(surf, (30, 24, 40), (6, top + 13, 30, 3))
    pygame.draw.rect(surf, (170, 160, 200) if ready >= 1 else (70, 64, 90), (6, top + 13, int(30 * ready), 3))
    if player.shield > 0:
        for j in range(player.shield):
            pygame.draw.rect(surf, (190, 196, 220), (40 + j * 5, top + 12, 4, 5))
    for j in range(3):  # ustalık seviyesi
        pygame.draw.rect(surf, (255, 200, 110) if j < player.mastery else (44, 36, 52), (40 + j * 5, top + 3, 4, 4))
    if game.spirit:
        pygame.draw.rect(surf, SPIRITS[game.spirit]["col"], (56, top + 3, 4, 4))
    if game.combo >= 5:
        col = (255, 120, 70) if game.combo >= 25 else (255, 200, 110) if game.combo >= 10 else (210, 200, 220)
        text(surf, font, f"KOMBO {game.combo}", 6, 6, col)
        if game.combo_bonus():
            text(surf, font, f"hasar +{game.combo_bonus()}", 6, 16, (240, 170, 110))
    sx = 100
    for j, (sk, name, cd) in enumerate(player.wp["skills"]):
        draw_skill_box(surf, sx + j * 17, top + 3, sk, SKILL_KEYS[j], player.skill_cd[j], cd * player.cdr, 0)
    x = sx + 3 * 17 + 6
    if player.has_beam:
        draw_skill_box(surf, sx + 3 * 17, top + 3, "isin", "O", player.skill_cd[3], BEAM_SKILL[2] * player.cdr, 0)
        x += 17
    for n, (key, lvl) in enumerate(player.boons.items()):
        if n >= 6:
            break
        surf.blit(icon(key), (x, top + 4))
        for j in range(lvl):
            surf.set_at((x + 1 + j * 2, top + 15), (230, 150, 80))
        x += 12
    room = game.room
    label = "TANSİ" if room.tansi else {"rest": "KOR SUNAĞI", "boss": "BEKÇİ", "haven": "SIĞINAK", "ani": "ANI", "dukkan": "TÜCCAR",
             "hazine": "HAZİNE", "lanet": "LANETLİ SUNAK", "kusatma": "KUŞATMA"}.get(room.kind, f"KAT {room.floor} · {room.idx}/{FLOOR_LEN}")
    img = font.render(label, False, (255, 150, 190) if room.kind in ("haven", "ani") else (180, 110, 90))
    surf.blit(img, (W - img.get_width() - 6, top + 5))
    # Öykü'nün isteği: elde değilse sönük, eldeyse parlak
    if game.quest is not None and game.quest < len(ITEMS) and not game.endless:
        ic = item_icon(game.quest)
        qx = W - img.get_width() - 20
        if game.carrying is None:
            ic = ic.copy()
            ic.fill((90, 90, 90, 255), special_flags=pygame.BLEND_RGBA_MULT)
        surf.blit(ic, (qx, top + 5))
        pygame.draw.rect(surf, (255, 150, 190) if game.carrying is not None else (60, 50, 70),
                         (qx - 2, top + 3, 13, 13), 1)
    kx = W - img.get_width() - (24 if game.quest is not None and game.quest < len(ITEMS) and not game.endless
                                 else 10)
    kw = draw_kul(surf, font, kx, top + 5, game.save["kul"], right=True)
    if game.sfx.muted:
        text(surf, font, "SES KAPALI", kx - kw - 52, top + 5, (90, 80, 100), shadow=False)


ITEM_ICONS = {}


def item_icon(i):
    if i not in ITEM_ICONS:
        ITEM_ICONS[i] = sprite_from_rows(ITEMS[i]["icon"], ITEMS[i]["pal"])
    return ITEM_ICONS[i]


def draw_boss_bar(surf, font, boss, t):
    text(surf, font, boss.name, W // 2, 18, (230, 90, 70) if boss.phase == 2 else (200, 180, 190), center=True)
    x, y, w = 80, 30, 160
    pygame.draw.rect(surf, (8, 6, 10), (x - 1, y - 1, w + 2, 6))
    pygame.draw.rect(surf, (40, 16, 20), (x, y, w, 4))
    pygame.draw.rect(surf, (230, 220, 200), (x, y, int(w * max(0.0, boss.shown) / boss.max_hp), 4))
    col = (255, 110, 50) if boss.phase == 2 and int(t * 6) % 2 else (190, 36, 44)
    pygame.draw.rect(surf, col, (x, y, int(w * max(0, boss.hp) / boss.max_hp), 4))
    surf.set_at((x + w // 2, y - 1), (255, 220, 140))  # öfke eşiği


def wrap(font, s, width):
    words, lines, cur = s.split(" "), [], ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        if font.size(trial)[0] <= width:
            cur = trial
        else:
            lines.append(cur)
            cur = wd
    lines.append(cur)
    return lines


PORTRAIT = None


def draw_dialog(surf, font, game, t):
    global PORTRAIT
    if PORTRAIT is None:
        PORTRAIT = {"Öykü": pygame.transform.scale(sprite_from_rows(OYKU[:9], OYKU_PAL), (36, 27)),
                    "Tansi": pygame.transform.scale(sprite_from_rows(TANSI_ROWS[:10], TANSI_PAL), (36, 23))}
    d = game.dialog
    line = d["lines"][d["i"]][:int(d["chars"])]
    x, y, w, h = 8, 104, W - 16, 52
    pygame.draw.rect(surf, (40, 20, 34), (x, y, w, h))
    pygame.draw.rect(surf, (255, 170, 205), (x, y, w, h), 1)
    pygame.draw.rect(surf, (120, 60, 90), (x + 2, y + 2, w - 4, h - 4), 1)
    pygame.draw.rect(surf, (255, 228, 236), (x + 6, y + 8, 40, 36))
    surf.blit(PORTRAIT["Tansi" if d.get("speaker") == "Tansi" else "Öykü"], (x + 8, y + 12))
    text(surf, font, d.get("speaker", "Öykü"), x + 54, y + 6, (255, 170, 205))
    if d.get("pick") is not None:  # iki seçenekli soru
        for i, (label, _, _) in enumerate(d["choices"]):
            sel = i == d["pick"]
            text(surf, font, ("> " if sel else "  ") + label, x + 54, y + 19 + i * 11,
                 (255, 210, 150) if sel else (170, 150, 165))
        text(surf, font, "A/D  J", x + w - 34, y + h - 13, (255, 170, 205), shadow=False)
        return
    for i, ln in enumerate(wrap(font, line, w - 64)[:3]):
        text(surf, font, ln, x + 54, y + 19 + i * 10, (250, 240, 245))
    if int(d["chars"]) >= len(d["lines"][d["i"]]) and int(t * 3) % 2:
        text(surf, font, "J", x + w - 12, y + h - 13, (255, 170, 205), shadow=False)


def draw_ending(surf, big, font, game, t):
    k = min(1.0, game.state_t / 1.5)
    shade = pygame.Surface((W, WORLD_H), pygame.SRCALPHA)
    shade.fill((255, 240, 245, int(140 * k)))
    surf.blit(shade, (0, 0))
    for i in range(3):
        surf.blit(pygame.transform.scale(item_icon(i), (18, 18)), (W // 2 - 40 + i * 28, 30))
    text(surf, big, "LANET ÇÖZÜLDÜ", W // 2, 56, (190, 60, 110), center=True)
    text(surf, font, "Öykü'nün istediği her şey artık onda.", W // 2, 78, (90, 50, 80), center=True)
    text(surf, font, f"{game.kills} hortlak susturuldu · {game.room.depth} oda", W // 2, 92, (110, 80, 100),
         center=True)
    if game.state_t > 3.0 and int(t * 2) % 2:
        text(surf, font, "J: sonsuz mahzene in", W // 2, 116, (150, 60, 100), center=True)


def draw_reward(surf, font, game, t):
    shade = pygame.Surface((W, WORLD_H), pygame.SRCALPHA)
    shade.fill((4, 2, 8, 170))
    surf.blit(shade, (0, 0))
    text(surf, font, "Kül bir armağan bırakıyor...", W // 2, 12, (220, 170, 130), center=True)
    x0 = (W - (CARD_W * 3 + CARD_GAP * 2)) // 2
    for i, key in enumerate(game.choices):
        sel = i == game.choice_i
        draw_boon_card(surf, font, game, key, x0 + i * (CARD_W + CARD_GAP), 32 - (3 if sel else 0), sel, t)
    text(surf, font, "A / D seç     J al", W // 2, 144, (110, 100, 130), center=True)


CARD_W, CARD_H, CARD_GAP = 94, 104, 8


def draw_boon_card(surf, font, game, key, x, y, sel, t):
    cw, ch = CARD_W, CARD_H
    b = BOONS.get(key) or PACTS[key]
    pygame.draw.rect(surf, (24, 18, 30) if sel else (16, 12, 20), (x, y, cw, ch))
    if sel:
        pulse = int(40 * (0.5 + 0.5 * math.sin(t * 6)))
        border = (215 + pulse // 2, 120 + pulse, 60)
    else:
        border = (56, 48, 70)
    pygame.draw.rect(surf, border, (x, y, cw, ch), 1)
    pygame.draw.rect(surf, (8, 6, 10), (x + 1, y + ch, cw, 2))
    # köşe süsleri
    for cx, cy in ((x + 2, y + 2), (x + cw - 3, y + 2), (x + 2, y + ch - 3), (x + cw - 3, y + ch - 3)):
        surf.set_at((cx, cy), border)
    ic = pygame.transform.scale(icon(key), (18, 18))
    pygame.draw.circle(surf, (40, 28, 36) if sel else (26, 20, 30), (x + cw // 2, y + 22), 14)
    surf.blit(ic, (x + cw // 2 - 9, y + 13))
    text(surf, font, b["name"], x + cw // 2, y + 42, (240, 200, 150) if sel else (170, 150, 140), center=True)
    lvl = game.player.boons.get(key, 0)
    if key in BOONS and key != "sifa":
        text(surf, font, f"Sv {lvl} > {lvl + 1}", x + cw // 2, y + 54, (130, 110, 150), center=True)
    for j, line in enumerate(b["desc"]):
        text(surf, font, line, x + cw // 2, y + 70 + j * 11, (200, 190, 210) if sel else (120, 112, 130),
             center=True)


def draw_pact(surf, font, game, t):
    shade = pygame.Surface((W, WORLD_H), pygame.SRCALPHA)
    shade.fill((14, 2, 16, 195))
    surf.blit(shade, (0, 0))
    text(surf, font, "Taş fısıldıyor: bir şey ver, bir şey al.", W // 2, 10, (210, 130, 170), center=True)
    x0 = (W - (CARD_W * 3 + CARD_GAP * 2)) // 2
    for i, key in enumerate(PACTS):
        sel = i == game.pact_i
        x, y = x0 + i * (CARD_W + CARD_GAP), 26 - (3 if sel else 0)
        draw_boon_card(surf, font, game, key, x, y, sel, t)
        if not game.pact_ok(key):
            veil = pygame.Surface((CARD_W, CARD_H), pygame.SRCALPHA)
            veil.fill((6, 4, 10, 190))
            surf.blit(veil, (x, y))
            text(surf, font, "BEDELİ YOK", x + CARD_W // 2, y + 46, (170, 90, 110), center=True)
    text(surf, font, "A / D seç   J akdet   BOŞLUK geri çekil", W // 2, 144, (150, 110, 150), center=True)


def draw_siege_bar(surf, font, game, t):
    k = max(0.0, game.siege_left) / SIEGE_TIME
    text(surf, font, f"DAYAN  {int(math.ceil(max(0.0, game.siege_left)))}", W // 2, 18, (240, 170, 110), center=True)
    x, y, w = 80, 30, 160
    pygame.draw.rect(surf, (8, 6, 10), (x - 1, y - 1, w + 2, 6))
    pygame.draw.rect(surf, (40, 16, 20), (x, y, w, 4))
    col = (255, 110, 50) if k < 0.25 and int(t * 6) % 2 else (230, 150, 70)
    pygame.draw.rect(surf, col, (x, y, int(w * k), 4))


def draw_shrine_fire(surf, room, t):
    sh = room.shrine
    if not sh or sh["used"]:
        return
    cx, top = sh["x"], 66
    for i in range(5):
        h = 3 + int(3 * math.sin(t * 7 + i * 1.9)) + (2 - abs(i - 2))
        col = (230, 170, 255) if abs(i - 2) <= 0 else (150, 70, 220)
        pygame.draw.line(surf, col, (cx - 2 + i, top), (cx - 2 + i, top - max(1, h)))


def draw_market(surf, font, game, t):
    shade = pygame.Surface((W, WORLD_H), pygame.SRCALPHA)
    shade.fill((4, 2, 8, 190))
    surf.blit(shade, (0, 0))
    m = game.market
    text(surf, font, f"\"{m['quote']}\"", W // 2, 10, (200, 170, 220), center=True)
    x0 = (W - (CARD_W * len(m["wares"]) + CARD_GAP * (len(m["wares"]) - 1))) // 2
    for i, w in enumerate(m["wares"]):
        sel = i == m["i"]
        x, y = x0 + i * (CARD_W + CARD_GAP), 26 - (3 if sel else 0)
        draw_boon_card(surf, font, game, w["key"], x, y, sel, t)
        if w["sold"]:
            veil = pygame.Surface((CARD_W, CARD_H), pygame.SRCALPHA)
            veil.fill((6, 4, 10, 200))
            surf.blit(veil, (x, y))
            text(surf, font, "SATILDI", x + CARD_W // 2, y + 46, (150, 130, 150), center=True)
        else:
            ok = game.save["kul"] >= w["price"]
            draw_kul(surf, font, x + CARD_W // 2 - 10, y + CARD_H - 11, w["price"],
                     (255, 210, 140) if ok else (170, 80, 70))
    draw_kul(surf, font, 12, 142, game.save["kul"])
    text(surf, font, "A / D seç   J satın al   BOŞLUK ayrıl", W // 2 + 16, 144, (130, 118, 150), center=True)


# --- Ayarlar ve duraklatma menüsü ---------------------------------------------------
SETTINGS_PATH = os.environ.get("KUL_SETTINGS") or os.path.expanduser("~/.config/kul-mahzeni/ayarlar.json")
DEFAULT_SETTINGS = {"music": 7, "sfx": 8, "shake": True, "fullscreen": False, "scare": True}


def load_settings():
    st = dict(DEFAULT_SETTINGS)
    try:
        import json
        with open(SETTINGS_PATH) as f:
            data = json.load(f)
        for k in st:
            if k in data and type(data[k]) is type(st[k]):
                st[k] = data[k]
    except (OSError, ValueError):
        pass
    return st


def save_settings(st):
    try:
        import json
        os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
        with open(SETTINGS_PATH, "w") as f:
            json.dump(st, f, indent=2)
    except OSError:
        pass


# --- Kalıcı ilerleme: kül, Kül Sunağı güçleri ve kayıt ------------------------------
SAVE_PATH = os.environ.get("KUL_SAVE") or os.path.expanduser("~/.config/kul-mahzeni/kayit.json")
DEFAULT_SAVE = {"kul": 0, "total_kul": 0, "perks": {}, "runs": 0, "wins": 0, "best_floor": 0,
                "checkpoint": None}

PERKS = [
    {"key": "can", "name": "Taş Yürek", "desc": "Her oyuna +1 canla başla", "costs": [25, 55, 100],
     "icon": "kul_kalbi"},
    {"key": "atilma", "name": "Hafif Adım", "desc": "Atılma beklemesi -%15", "costs": [30, 70],
     "icon": "kul_ruzgari"},
    {"key": "miknatis", "name": "Kül Toplayıcı", "desc": "Toplanan kül +%25", "costs": [40, 90],
     "icon": "cevik_bilek"},
    {"key": "miras", "name": "Kor Mirası", "desc": "Rastgele armağanla başla", "costs": [80],
     "icon": "kor_pelerin"},
    {"key": "guc", "name": "Bilenmiş Kor", "desc": "Silah hasarı +1", "costs": [140],
     "icon": "kor_kilic"},
    {"key": "dirilis", "name": "Son Kor", "desc": "Oyunda bir kez diril", "costs": [180],
     "icon": "sifa"},
]
PERK_BY_KEY = {pk["key"]: pk for pk in PERKS}


def load_save():
    import copy
    import json
    sv = copy.deepcopy(DEFAULT_SAVE)
    try:
        with open(SAVE_PATH) as f:
            data = json.load(f)
        for k in sv:
            if k in data and (sv[k] is None or type(data[k]) is type(sv[k])):
                sv[k] = data[k]
    except (OSError, ValueError):
        pass
    sv["perks"] = {k: v for k, v in sv["perks"].items() if k in PERK_BY_KEY and isinstance(v, int)}
    return sv


def write_save(sv):
    import json
    try:
        os.makedirs(os.path.dirname(SAVE_PATH), exist_ok=True)
        tmp = SAVE_PATH + ".tmp"
        with open(tmp, "w") as f:
            json.dump(sv, f, indent=2, ensure_ascii=False)
        os.replace(tmp, SAVE_PATH)  # yarım yazılmış kayıt kalmasın
    except OSError:
        pass


def perk_level(sv, key):
    return sv["perks"].get(key, 0)


def perk_cost(sv, key):
    pk = PERK_BY_KEY[key]
    lvl = perk_level(sv, key)
    return pk["costs"][lvl] if lvl < len(pk["costs"]) else None


KUL_ICON = None


def kul_icon():
    """Küçük kor kırıntısı simgesi."""
    global KUL_ICON
    if KUL_ICON is None:
        KUL_ICON = sprite_from_rows(["..k..", ".kyk.", "kywok", ".kok.", "..k.."], ICON_PAL)
    return KUL_ICON


def draw_kul(surf, font, x, y, amount, col=(255, 210, 140), right=False):
    img = font.render(str(amount), False, col)
    w = img.get_width() + 8
    if right:
        x -= w
    surf.blit(kul_icon(), (x, y + 1))
    surf.blit(font.render(str(amount), False, (10, 8, 14)), (x + 8, y + 1))
    surf.blit(img, (x + 7, y))
    return w


class PerkShop:
    """Başlangıç ekranındaki Kül Sunağı: ölünce de kalan küllerle kalıcı güçler alınır."""

    def __init__(self, save):
        self.save = save
        self.sel = 0
        self.open = False
        self.t = 0.0
        self.flash = 0.0
        self.msg = ""

    def handle(self, key, sfx):
        if key in (pygame.K_w, pygame.K_UP):
            self.sel = (self.sel - 1) % len(PERKS)
            sfx.play("select")
        elif key in (pygame.K_s, pygame.K_DOWN):
            self.sel = (self.sel + 1) % len(PERKS)
            sfx.play("select")
        elif key in (pygame.K_j, pygame.K_x, pygame.K_RETURN, pygame.K_SPACE):
            pk = PERKS[self.sel]
            cost = perk_cost(self.save, pk["key"])
            if cost is None:
                self.msg = "zaten en üst seviyede"
                sfx.play("fizzle")
            elif self.save["kul"] < cost:
                self.msg = f"{cost - self.save['kul']} kül daha gerek"
                sfx.play("fizzle")
            else:
                self.save["kul"] -= cost
                self.save["perks"][pk["key"]] = perk_level(self.save, pk["key"]) + 1
                write_save(self.save)
                self.flash = 0.5
                self.msg = f"{pk['name']} kalıcı oldu"
                sfx.play("item")
        elif key in (pygame.K_ESCAPE, pygame.K_k, pygame.K_BACKSPACE):
            self.open = False
            sfx.play("select")

    def draw(self, surf, font, big, t):
        self.t += 1 / 60
        self.flash = max(0.0, self.flash - 1 / 60)
        shade = pygame.Surface((W, H), pygame.SRCALPHA)
        shade.fill((4, 2, 8, 215))
        surf.blit(shade, (0, 0))
        draw_logo(surf, big, "KÜL SUNAĞI", W // 2, 4)
        text(surf, font, "ölünce de kalan küllerini kalıcı güce dök", W // 2, 25, (190, 160, 170), center=True)
        draw_kul(surf, font, W - 8, 6, self.save["kul"], right=True)
        x, y0, rw, rh = 14, 38, W - 28, 18
        for i, pk in enumerate(PERKS):
            sel = i == self.sel
            y = y0 + i * rh
            lvl = perk_level(self.save, pk["key"])
            cost = perk_cost(self.save, pk["key"])
            bg = (30, 20, 30) if sel else (14, 10, 18)
            if sel and self.flash > 0:
                bg = (70, 44, 34)
            pygame.draw.rect(surf, bg, (x, y, rw, rh - 2))
            if sel:
                pulse = int(40 * (0.5 + 0.5 * math.sin(t * 6)))
                pygame.draw.rect(surf, (215 + pulse // 2, 120 + pulse, 60), (x, y, rw, rh - 2), 1)
            surf.blit(icon(pk["icon"]), (x + 4, y + 3))
            text(surf, font, pk["name"], x + 18, y + 1, (250, 210, 160) if sel else (170, 150, 150))
            text(surf, font, pk["desc"], x + 98, y + 1, (200, 190, 210) if sel else (110, 100, 120), shadow=False)
            # seviye çentikleri
            for j in range(len(pk["costs"])):
                c = (235, 120, 50) if j < lvl else (44, 34, 50)
                pygame.draw.rect(surf, c, (x + 18 + j * 6, y + 12, 4, 2))
            if cost is None:
                text(surf, font, "TAMAM", x + rw - 4 - font.size("TAMAM")[0], y + 1, (150, 200, 140), shadow=False)
            else:
                ok = self.save["kul"] >= cost
                draw_kul(surf, font, x + rw - 4, y + 1, cost, (255, 210, 140) if ok else (120, 90, 90), right=True)
        if self.msg:
            text(surf, font, self.msg, W // 2, 148, (255, 200, 140), center=True)
        s = self.save
        text(surf, font, f"oyun {s['runs']} · zafer {s['wins']} · en derin {s['best_floor']}. kat",
             W // 2, 157, (110, 100, 130), center=True, shadow=False)
        text(surf, font, "W / S seç   ·   J al   ·   ESC geri", W // 2, 168, (130, 115, 140), center=True)


CONTROLS = [
    (["W", "A", "S", "D"], "Hareket (oklar da olur)"),
    (["J", "X"], "Saldır · seç · konuş"),
    (["K", "L", "I"], "Yetenekler (I: ulti, O: ışın)"),
    (["BOŞLUK"], "Atıl (atılırken hasar almazsın)"),
    (["ESC"], "Duraklat · geri dön"),
    (["M"], "Sesi aç / kapat"),
    (["F11"], "Tam ekran"),
    (["R"], "Ölünce yeniden uyan"),
]


class PauseMenu:
    MAIN = ["Devam Et", "Ayarlar", "Kontroller", "Yeniden Başla", "Oyundan Çık"]
    SETTINGS = [("Müzik", "music"), ("Efektler", "sfx"), ("Ekran sarsıntısı", "shake"),
                ("Tam ekran", "fullscreen"), ("Korku anları", "scare"), ("Geri", None)]

    def __init__(self, settings, sfx):
        self.settings = settings
        self.sfx = sfx
        self.open = False
        self.page = "main"
        self.i = 0
        self.confirm = None
        self.t = 0.0

    def show(self):
        self.open, self.page, self.i, self.confirm, self.t = True, "main", 0, None, 0.0
        self.sfx.set_levels(self.settings["music"], self.settings["sfx"], duck=True)
        self.sfx.play("select")

    def close(self):
        self.open = False
        self.sfx.set_levels(self.settings["music"], self.settings["sfx"], duck=False)
        save_settings(self.settings)

    def rows(self):
        return len(self.MAIN) if self.page == "main" else len(self.SETTINGS) if self.page == "settings" else 1

    def handle(self, key):
        """Tuşu işler; ana döngünün yapması gereken bir şey varsa onu döndürür."""
        up = key in (pygame.K_w, pygame.K_UP)
        down = key in (pygame.K_s, pygame.K_DOWN)
        left = key in (pygame.K_a, pygame.K_LEFT)
        right = key in (pygame.K_d, pygame.K_RIGHT)
        ok = key in (pygame.K_j, pygame.K_x, pygame.K_RETURN, pygame.K_SPACE)
        back = key == pygame.K_ESCAPE
        if up or down:
            self.i = (self.i + (1 if down else -1)) % self.rows()
            self.confirm = None
            self.sfx.play("select")
            return None
        if self.page == "main":
            if back:
                self.close()
                return "resume"
            if ok:
                item = self.MAIN[self.i]
                if item == "Devam Et":
                    self.close()
                    return "resume"
                if item in ("Ayarlar", "Kontroller"):
                    self.page = "settings" if item == "Ayarlar" else "controls"
                    self.i = 0
                    self.sfx.play("select")
                    return None
                if self.confirm != item:  # tehlikeli seçenekler iki kez onay ister
                    self.confirm = item
                    self.sfx.play("hurt", 0.4)
                    return None
                self.close()
                return "restart" if item == "Yeniden Başla" else "quit"
            return None
        if self.page == "controls":
            if back or ok:
                self.page, self.i = "main", 2
                self.sfx.play("select")
            return None
        # ayarlar sayfası
        label, key_name = self.SETTINGS[self.i]
        if back or (ok and key_name is None):
            self.page, self.i = "main", 1
            save_settings(self.settings)
            self.sfx.play("select")
            return None
        st = self.settings
        if key_name in ("music", "sfx") and (left or right or ok):
            step = -1 if left else 1
            st[key_name] = max(0, min(10, st[key_name] + step)) if not ok else (st[key_name] + 1) % 11
            self.sfx.set_levels(st["music"], st["sfx"], duck=True)
            self.sfx.play("hit" if key_name == "sfx" else "select")
        elif key_name in ("shake", "fullscreen", "scare") and (left or right or ok):
            st[key_name] = not st[key_name]
            self.sfx.play("select")
            if key_name == "fullscreen":
                return "fullscreen"
        return None


def draw_flame(surf, x, y, t):
    h = 3 + int(t * 12) % 2
    pygame.draw.line(surf, (235, 110, 50), (x, y), (x, y - h))
    pygame.draw.line(surf, (235, 110, 50), (x + 1, y), (x + 1, y - h + 1))
    surf.set_at((x, y - 1), (255, 220, 120))
    surf.set_at((x + 1, y - 1), (255, 220, 120))


def draw_keycap(surf, font, x, y, label):
    w = font.size(label)[0] + 7
    pygame.draw.rect(surf, (12, 9, 16), (x, y + 1, w, 12))
    pygame.draw.rect(surf, (58, 50, 72), (x, y, w, 11))
    pygame.draw.line(surf, (96, 86, 112), (x + 1, y), (x + w - 2, y))
    pygame.draw.rect(surf, (30, 24, 40), (x, y, w, 12), 1)
    surf.blit(font.render(label, False, (235, 225, 240)), (x + 4, y + 1))
    return w


def draw_panel(surf, x, y, w, h, t):
    pygame.draw.rect(surf, (6, 4, 8), (x + 3, y + 3, w, h))          # gölge
    pygame.draw.rect(surf, (16, 11, 20), (x, y, w, h))
    pulse = int(30 * (0.5 + 0.5 * math.sin(t * 3)))
    pygame.draw.rect(surf, (170 + pulse, 70 + pulse // 2, 40), (x, y, w, h), 1)
    pygame.draw.rect(surf, (60, 34, 44), (x + 2, y + 2, w - 4, h - 4), 1)
    for cx, cy in ((x, y), (x + w - 3, y), (x, y + h - 3), (x + w - 3, y + h - 3)):  # köşe perçinleri
        pygame.draw.rect(surf, (230, 150, 80), (cx, cy, 3, 3))
    # panelin içinden yükselen birkaç kor
    for j in range(6):
        px = x + 8 + (j * 37 + int(t * 7) * 3) % (w - 16)
        py = y + h - 4 - int((t * 14 + j * 23) % (h - 10))
        surf.set_at((px, py), (150, 60, 30) if j % 2 else (230, 120, 50))


def draw_menu(surf, font, big, menu, game, t):
    shade = pygame.Surface((W, H), pygame.SRCALPHA)
    shade.fill((4, 2, 8, 175))
    surf.blit(shade, (0, 0))
    for yy in range(0, H, 2):  # tarama çizgileri
        pygame.draw.line(surf, (0, 0, 0), (0, yy), (W, yy))
    if menu.page == "main":
        x, y, w, h = 80, 14, 160, 150
        draw_panel(surf, x, y, w, h, t)
        text(surf, big, "DURAKLATILDI", W // 2, y + 8, (240, 150, 90), center=True)
        pygame.draw.line(surf, (90, 50, 50), (x + 16, y + 26), (x + w - 16, y + 26))
        for n, item in enumerate(menu.MAIN):
            iy = y + 34 + n * 15
            sel = n == menu.i
            label = item
            col = (150, 135, 160)
            if sel:
                pygame.draw.rect(surf, (50, 22, 26), (x + 12, iy - 2, w - 24, 13))
                col = (255, 214, 150)
                if menu.confirm == item:
                    label, col = "Emin misin? J", (255, 110, 90)
                draw_flame(surf, x + 18, iy + 8, t)
                draw_flame(surf, x + w - 20, iy + 8, t + 0.3)
            text(surf, font, label, W // 2, iy, col, center=True)
        # alt bilgi: ilerleme ve Öykü'nün isteği
        room = game.room
        info = f"Kat {room.floor} · {game.kills} hortlak"
        text(surf, font, info, W // 2, y + 112, (120, 105, 130), center=True, shadow=False)
        if game.quest is not None and game.quest < len(ITEMS) and not game.endless:
            q = f"Öykü istiyor: {ITEMS[game.quest]['name']}"
            qw = font.size(q)[0]
            surf.blit(item_icon(game.quest), (W // 2 - qw // 2 - 12, y + 124))
            text(surf, font, q, W // 2 + 2, y + 123, (255, 150, 190), center=True, shadow=False)
        elif not game.rescued:
            text(surf, font, "Öykü hâlâ zindanda...", W // 2, y + 123, (200, 110, 140), center=True, shadow=False)
        text(surf, font, "W/S seç  ·  J onayla  ·  ESC devam", W // 2, H - 12, (110, 100, 130), center=True)
    elif menu.page == "settings":
        x, y, w, h = 50, 22, 220, 128
        draw_panel(surf, x, y, w, h, t)
        text(surf, big, "AYARLAR", W // 2, y + 8, (240, 150, 90), center=True)
        pygame.draw.line(surf, (90, 50, 50), (x + 16, y + 26), (x + w - 16, y + 26))
        st = menu.settings
        for n, (label, key) in enumerate(menu.SETTINGS):
            iy = y + 34 + n * 17
            sel = n == menu.i
            if sel:
                pygame.draw.rect(surf, (50, 22, 26), (x + 10, iy - 3, w - 20, 15))
                draw_flame(surf, x + 15, iy + 8, t)
            col = (255, 214, 150) if sel else (160, 145, 170)
            if key is None:
                text(surf, font, label, W // 2, iy, col, center=True)
                continue
            text(surf, font, label, x + 22, iy, col)
            vx = x + 120
            if key in ("music", "sfx"):
                for b in range(10):
                    on = b < st[key]
                    c = (235, 110, 50) if on and b >= 7 else (220, 170, 90) if on else (40, 32, 48)
                    pygame.draw.rect(surf, c, (vx + b * 7, iy + 1, 5, 7))
                text(surf, font, str(st[key]), vx + 74, iy, col, shadow=False)
            else:
                on = st[key]
                text(surf, font, "AÇIK" if on else "KAPALI", vx + 34, iy, (140, 220, 120) if on else (200, 90, 90),
                     center=True)
            if sel:
                bob = int(t * 4) % 2
                text(surf, font, "<", vx - 9 - bob, iy, (255, 200, 120), shadow=False)
                text(surf, font, ">", vx + 84 + bob, iy, (255, 200, 120), shadow=False)
        text(surf, font, "W/S seç  ·  A/D değiştir  ·  ESC geri", W // 2, H - 12, (110, 100, 130), center=True)
    else:
        x, y, w, h = 18, 10, 284, 156
        draw_panel(surf, x, y, w, h, t)
        text(surf, big, "KONTROLLER", W // 2, y + 8, (240, 150, 90), center=True)
        pygame.draw.line(surf, (90, 50, 50), (x + 16, y + 26), (x + w - 16, y + 26))
        for n, (keys, desc) in enumerate(CONTROLS):
            iy = y + 30 + n * 14
            kx = x + 14
            for j, k in enumerate(keys):
                if j and len(keys) == 2:  # WASD / KLI grup: araya eğik çizgi koyma
                    text(surf, font, "/", kx + 1, iy, (90, 80, 100), shadow=False)
                    kx += 8
                kx += draw_keycap(surf, font, kx, iy, k) + 2
            text(surf, font, desc, x + 102, iy + 1, (200, 190, 210))
        text(surf, font, "J veya ESC: geri", W // 2, H - 12, (110, 100, 130), center=True)


# --- Oyuncu mermileri, yetenek efektleri, hasar sayıları -------------------------------
class PShot:
    def __init__(self, x, y, vx, vy, dmg, pierce=1, kind="arrow", life=1.2, h=8):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.dmg, self.pierce, self.kind, self.life, self.h = dmg, pierce, kind, life, h
        self.hits = set()
        self.dead = False
        self.trail = []

    def update(self, dt):
        self.trail.append((self.x, self.y))
        self.trail = self.trail[-5:]
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        if self.life <= 0 or CUR.shot_solid(int(self.x) // TILE, int(self.y + self.h) // TILE):
            self.dead = True

    def rect(self):
        s = 7 if self.kind != "arrow" else 5
        return pygame.Rect(int(self.x) - s // 2, int(self.y) - s // 2, s, s)

    def draw(self, surf):
        ux, uy = norm(self.vx, self.vy)
        x, y = self.x, self.y
        if self.kind == "orb":  # kor küresi
            for i, (tx, ty) in enumerate(self.trail):
                if 0 <= tx < W and 0 <= ty < WORLD_H:
                    surf.set_at((int(tx), int(ty)), (220, 90, 40))
            pygame.draw.circle(surf, (235, 110, 50), (int(x), int(y)), 4)
            pygame.draw.circle(surf, (255, 235, 170), (int(x), int(y)), 2)
            return
        if self.kind == "ghost":  # hayalet kılıç
            for i, (tx, ty) in enumerate(self.trail):
                if 0 <= tx < W and 0 <= ty < WORLD_H:
                    surf.set_at((int(tx), int(ty)), (60, 90, 160))
            for d in range(-5, 4):
                px, py = int(x + ux * d), int(y + uy * d)
                if 0 <= px < W and 0 <= py < WORLD_H:
                    surf.set_at((px, py), (230, 245, 255) if d > -2 else (140, 190, 255))
            hx, hy = int(x - ux * 2), int(y - uy * 2)
            for o in (-2, -1, 1, 2):
                px, py = int(hx - uy * o), int(hy + ux * o)
                if 0 <= px < W and 0 <= py < WORLD_H:
                    surf.set_at((px, py), (120, 160, 240))
            return
        big = self.kind == "big"
        for i, (tx, ty) in enumerate(self.trail):
            if 0 <= tx < W and 0 <= ty < WORLD_H:
                surf.set_at((int(tx), int(ty)), (200, 90, 40) if big else (90, 80, 100))
        for d in range(-6, 1):  # gövde
            px, py = int(x + ux * d), int(y + uy * d)
            if 0 <= px < W and 0 <= py < WORLD_H:
                surf.set_at((px, py), (255, 200, 90) if big else (190, 150, 100))
        for o in (-1, 1):  # tüyler
            px, py = int(x - ux * 6 - uy * o), int(y - uy * 6 + ux * o)
            if 0 <= px < W and 0 <= py < WORLD_H:
                surf.set_at((px, py), (200, 60, 60))
        hx, hy = int(x + ux), int(y + uy)
        if 0 <= hx < W and 0 <= hy < WORLD_H:
            surf.set_at((hx, hy), (255, 255, 255) if big else (230, 230, 245))


DIGITS = {
    "0": ["111", "101", "101", "101", "111"], "1": ["010", "110", "010", "010", "111"],
    "2": ["111", "001", "111", "100", "111"], "3": ["111", "001", "011", "001", "111"],
    "4": ["101", "101", "111", "001", "001"], "5": ["111", "100", "111", "001", "111"],
    "6": ["111", "100", "111", "101", "111"], "7": ["111", "001", "010", "010", "010"],
    "8": ["111", "101", "111", "101", "111"], "9": ["111", "101", "111", "001", "111"],
}


def draw_number(surf, value, x, y, col, lim=WORLD_H):
    s = str(value)
    x -= len(s) * 2
    for ch in s:
        rows = DIGITS[ch]
        for yy, row in enumerate(rows):  # kontur
            for xx, b in enumerate(row):
                if b == "1":
                    for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        px, py = x + xx + ox, y + yy + oy
                        if 0 <= px < W and 0 <= py < lim:
                            surf.set_at((px, py), (10, 6, 10))
        for yy, row in enumerate(rows):
            for xx, b in enumerate(row):
                px, py = x + xx, y + yy
                if b == "1" and 0 <= px < W and 0 <= py < lim:
                    surf.set_at((px, py), col)
        x += 4


def draw_effect(surf, e, t):
    if e["kind"] == "zap":  # şimşek ruhu sıçraması
        x, y = e["x"], e["y"]
        for i in range(1, 7):
            k = i / 6
            nx = e["x"] + (e["x2"] - e["x"]) * k + random.randint(-3, 3)
            ny = e["y"] + (e["y2"] - e["y"]) * k + random.randint(-3, 3)
            pygame.draw.line(surf, (255, 245, 170), (int(x), int(y)), (int(nx), int(ny)))
            x, y = nx, ny
        return
    """Yetenek görselleri (ışıktan sonra, parlak)."""
    k = 1 - max(0.0, e["t"]) / e["total"]
    x, y = e["x"], e["y"]
    kind = e["kind"]
    if kind == "spin":
        r = int(10 + 26 * k)
        for j in range(28):
            a = j * math.tau / 28 + k * 9
            if j % 4 == 0:
                continue
            col = (255, 240, 210) if j % 3 else (255, 150, 60)
            surf.set_at((int(x + math.cos(a) * r), int(y + math.sin(a) * r * 0.8)), col)
            surf.set_at((int(x + math.cos(a) * (r - 2)), int(y + math.sin(a) * (r - 2) * 0.8)), (200, 80, 40))
    elif kind in ("target", "rain"):
        r = e["r"]
        col = (120, 200, 255) if int(t * 10) % 2 else (70, 130, 200)
        pygame.draw.ellipse(surf, col, (int(x - r), int(y - r * 0.6), int(2 * r), int(1.2 * r)), 1)
        if kind == "rain":
            rnd = random.Random(int(t * 30))
            for _ in range(10):
                ax, ay = x + rnd.uniform(-r, r), y + rnd.uniform(-r * 0.5, r * 0.5)
                fy = ay - rnd.uniform(0, 30)
                pygame.draw.line(surf, (200, 180, 140), (int(ax), int(fy - 5)), (int(ax), int(fy)))
                surf.set_at((int(ax), int(fy) + 1), (240, 240, 255))
    elif kind == "spike":  # yerden fışkıran kaya dikeni
        h = int(12 * math.sin(min(1.0, k * 1.4) * math.pi))
        if h > 0:
            pts = [(x - 5, y), (x - 2, y - h), (x, y - h // 2), (x + 2, y - h - 2), (x + 5, y)]
            pygame.draw.polygon(surf, (96, 86, 104), pts)
            pygame.draw.polygon(surf, (20, 16, 24), pts, 1)
            pygame.draw.line(surf, (255, 150, 60), (int(x), int(y - 1)), (int(x), int(y - h // 2)))
    elif kind == "mine":
        col = (255, 120, 50) if int(t * 12) % 2 else (150, 50, 30)
        pygame.draw.circle(surf, col, (int(x), int(y)), 3)
        surf.set_at((int(x), int(y)), (255, 230, 150))
    elif kind == "crater":
        r = e["r"]
        a = int(255 * (1 - k))
        if a > 0:
            pygame.draw.ellipse(surf, (255, 140, 60), (int(x - r), int(y - r * 0.6), int(2 * r), int(1.2 * r)), 1)
            r2 = r * (0.5 + 0.5 * k)
            pygame.draw.ellipse(surf, (255, 220, 140), (int(x - r2), int(y - r2 * 0.6), int(2 * r2), int(1.2 * r2)), 1)
    elif kind == "jab":
        ux, uy = e["d"]
        for d in range(0, 12):
            px, py = int(x + ux * d + random.randint(-1, 1)), int(y + uy * d)
            if 0 <= px < W and 0 <= py < WORLD_H:
                surf.set_at((px, py), (255, 220, 140) if d > 8 else (240, 110, 50))
    elif kind == "wave":  # volkan şok dalgası
        r = e["r"] * (0.4 + 0.6 * k)
        pygame.draw.ellipse(surf, (255, 200, 90), (int(x - r), int(y - r * 0.6), int(2 * r), int(1.2 * r)), 2)
        pygame.draw.ellipse(surf, (255, 90, 40), (int(x - r * 0.7), int(y - r * 0.42), int(1.4 * r),
                                                  max(1, int(0.84 * r))), 1)


# --- Başlangıç ekranı: silah seçimi -----------------------------------------------------
LETTERS = {"O": ["111", "101", "101", "101", "111"], "K": ["101", "101", "110", "101", "101"], "L": ["100", "100", "100", "100", "111"],
           "I": ["111", "010", "010", "010", "111"]}
SKILL_ICON_CACHE = {}


def skill_icon(key):
    if key not in SKILL_ICON_CACHE:
        SKILL_ICON_CACHE[key] = sprite_from_rows(SKILL_ICONS[key], SKILL_PAL)
    return SKILL_ICON_CACHE[key]


def draw_glyph(surf, rows, x, y, col):
    for yy, row in enumerate(rows):
        for xx, b in enumerate(row):
            if b == "1":
                for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    surf.set_at((x + xx + ox, y + yy + oy), (10, 6, 10))
    for yy, row in enumerate(rows):
        for xx, b in enumerate(row):
            if b == "1":
                surf.set_at((x + xx, y + yy), col)


def draw_skill_box(surf, x, y, key, letter, cd, total, t, ready_flash=False):
    ready = cd <= 0
    pygame.draw.rect(surf, (6, 4, 8), (x + 1, y + 1, 14, 14))
    pygame.draw.rect(surf, (28, 22, 36), (x, y, 14, 14))
    surf.blit(skill_icon(key), (x + 2, y + 2))
    if not ready:
        h = int(14 * cd / total)
        shade = pygame.Surface((14, h), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 170))
        surf.blit(shade, (x, y))
        secs = int(math.ceil(cd))
        s = str(secs)
        nx = x + 7 - len(s) * 2
        for ch in s:
            draw_glyph(surf, DIGITS[ch], nx, y + 4, (230, 220, 235))
            nx += 4
    border = (230, 150, 70) if ready else (60, 50, 70)
    if ready and ready_flash:
        border = (255, 240, 200)
    pygame.draw.rect(surf, border, (x, y, 14, 14), 1)
    draw_glyph(surf, LETTERS[letter], x + 11, y + 11, (255, 230, 170) if ready else (140, 130, 150))


LOGO_CACHE = {}


def draw_logo(surf, font, s, cx, y):
    if s not in LOGO_CACHE:
        white = font.render(s, False, (255, 255, 255))
        w, h = white.get_size()
        grad = pygame.Surface((w, h), pygame.SRCALPHA)
        for yy in range(h):
            k = yy / max(1, h - 1)
            c = (255, int(230 - 150 * k), int(150 - 120 * k), 255)
            pygame.draw.line(grad, c, (0, yy), (w, yy))
        txt = white.copy()
        txt.blit(grad, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        out = pygame.Surface((w + 4, h + 4), pygame.SRCALPHA)
        dark = font.render(s, False, (20, 6, 8))
        for ox in range(0, 5):
            for oy in range(0, 5):
                if (ox, oy) != (2, 2):
                    out.blit(dark, (ox, oy))
        red = font.render(s, False, (120, 30, 20))
        out.blit(red, (2, 3))
        out.blit(txt, (2, 2))
        LOGO_CACHE[s] = out
    img = LOGO_CACHE[s]
    surf.blit(img, (cx - img.get_width() // 2, y - font.lift))


class TitleScreen:
    def __init__(self, save):
        global CUR
        self.save = save
        self.shop = PerkShop(save)
        self.sel = 0
        self.stage = "weapon"       # weapon -> spirit
        self.spirit_i = 0
        self.t = 0.0
        self.room = Room(5, COLS // 2, random.Random(11), "combat", 1, 1)
        CUR = self.room
        self.frames = build_frames(HERO_BODY, HERO_LEGS, HERO_PAL)
        self.wimgs = {k: sprite_from_rows(v, WPAL) for k, v in WEAPON_SPRITES.items()}

    def ensure_bg(self, font):
        if self.room.bg is None:
            self.room.bg = build_background(self.room, font)

    def handle(self, key, sfx):
        if self.shop.open:
            self.shop.handle(key, sfx)
            return None
        if self.stage == "spirit":
            if key in (pygame.K_a, pygame.K_LEFT):
                self.spirit_i = (self.spirit_i - 1) % len(SPIRIT_ORDER)
                sfx.play("select")
            elif key in (pygame.K_d, pygame.K_RIGHT):
                self.spirit_i = (self.spirit_i + 1) % len(SPIRIT_ORDER)
                sfx.play("select")
            elif key in (pygame.K_j, pygame.K_x, pygame.K_RETURN, pygame.K_SPACE):
                self.stage = "weapon"
                sfx.play("pick")
                return "start"
            elif key == pygame.K_ESCAPE:
                self.stage = "weapon"
                sfx.play("select")
            return None
        if key == pygame.K_k:
            self.shop.open, self.shop.msg = True, ""
            sfx.play("select")
            return None
        if key == pygame.K_c and self.save.get("checkpoint"):
            sfx.play("pick")
            return "continue"
        if key in (pygame.K_a, pygame.K_LEFT):
            self.sel = (self.sel - 1) % len(WEAPON_ORDER)
            sfx.play("select")
        elif key in (pygame.K_d, pygame.K_RIGHT):
            self.sel = (self.sel + 1) % len(WEAPON_ORDER)
            sfx.play("select")
        elif key in (pygame.K_j, pygame.K_x, pygame.K_RETURN, pygame.K_SPACE):
            self.stage = "spirit"
            sfx.play("pick")
        elif key == pygame.K_ESCAPE:
            return "quit"
        return None

    def draw_spirits(self, canvas, font, big, t):
        shade = pygame.Surface((W, H), pygame.SRCALPHA)
        shade.fill((6, 4, 10, 215))
        canvas.blit(shade, (0, 0))
        wp = WEAPONS[WEAPON_ORDER[self.sel]]
        text(canvas, big, "SİLAH RUHU", W // 2, 14, (240, 150, 90), center=True)
        text(canvas, font, f"{wp['name']} hangi ruhla yansın?", W // 2, 34, (200, 180, 190), center=True)
        cw, ch, gap = 94, 92, 8
        x0 = (W - (cw * 3 + gap * 2)) // 2
        for i, key in enumerate(SPIRIT_ORDER):
            sp = SPIRITS[key]
            sel = i == self.spirit_i
            x, y = x0 + i * (cw + gap), 52 - (3 if sel else 0)
            pygame.draw.rect(canvas, (24, 18, 30) if sel else (14, 10, 18), (x, y, cw, ch))
            pygame.draw.rect(canvas, sp["col"] if sel else (56, 46, 70), (x, y, cw, ch), 1)
            canvas.blit(pygame.transform.scale(icon(key), (27, 27)), (x + cw // 2 - 13, y + 8))
            text(canvas, font, sp["name"], x + cw // 2, y + 40, sp["col"] if sel else (170, 150, 150), center=True)
            for j, ln in enumerate(sp["desc"]):
                text(canvas, font, ln, x + cw // 2, y + 56 + j * 11, (205, 195, 215) if sel else (120, 112, 130),
                     center=True)
        text(canvas, font, "A / D seç  ·  J başla  ·  ESC geri", W // 2, 152, (130, 118, 150), center=True)

    def hero_card(self, weapon, scale):
        """Kahramanı seçilen silahla birlikte çizer."""
        s = pygame.Surface((24, 22), pygame.SRCALPHA)
        hero = self.frames[int(self.t * 3) % 2 if weapon == WEAPON_ORDER[self.sel] else 0]
        w = self.wimgs[weapon]
        if weapon == "balyoz":
            s.blit(w, (2, 0))
            s.blit(hero, (6, 5))
        else:
            s.blit(hero, (6, 5))
            if weapon in ("kilic", "mizrak", "asa"):
                s.blit(w, (17, 6 if weapon == "kilic" else 2))
            elif weapon == "yay":
                s.blit(w, (16, 8))
            else:
                for gx in (6, 17):
                    pygame.draw.rect(s, (12, 9, 16), (gx - 2, 13, 5, 5))
                    pygame.draw.rect(s, (230, 110, 50), (gx - 1, 14, 3, 3))
        return pygame.transform.scale(s, (24 * scale, 22 * scale))

    def draw(self, canvas, world, lightmap, lights, ash, font, big, vignette):
        self.t += 1 / 60
        t = self.t
        room = self.room
        world.blit(room.bg, (0, 0))
        for tx, ty in room.torches:
            draw_torch(world, tx, ty, t + tx)
        lightmap.fill((22, 16, 30))
        for i, (tx, ty) in enumerate(room.torches):
            lt = lights["torch"][int(t * 9 + i * 2) % 3]
            r = lt.get_width() // 2
            lightmap.blit(lt, (tx * TILE + 8 - r, ty * TILE + 8 - r), special_flags=pygame.BLEND_RGB_ADD)
        pl = lights["boss"]
        lightmap.blit(pl, (W // 2 - 58, 92 - 58), special_flags=pygame.BLEND_RGB_ADD)
        world.blit(lightmap, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        world.blit(vignette, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        ash.draw(world)
        canvas.fill((6, 4, 8))
        canvas.blit(world, (0, 0))
        if self.shop.open:
            self.shop.draw(canvas, font, big, t)
            return

        draw_logo(canvas, big, "KÜL MAHZENİ", W // 2, 4)
        text(canvas, font, "Prenses Öykü'yü kurtar · silahını seç", W // 2, 27, (200, 170, 180), center=True)

        cw, ch, gap = 72, 92, 4
        x0 = (W - (cw * 4 + gap * 3)) // 2
        first = max(0, min(self.sel - 1, len(WEAPON_ORDER) - 4))  # dört kart görünür, seçim kaydırır
        if first > 0:
            text(canvas, font, "<", 3, 80, (255, 200, 120))
        if first + 4 < len(WEAPON_ORDER):
            text(canvas, font, ">", W - 8, 80, (255, 200, 120))
        for i, key in enumerate(WEAPON_ORDER):
            if not first <= i < first + 4:
                continue
            wp = WEAPONS[key]
            sel = i == self.sel
            x, y = x0 + (i - first) * (cw + gap), 40 - (3 if sel else 0)
            panel = pygame.Surface((cw, ch), pygame.SRCALPHA)
            panel.fill((14, 10, 18, 230) if sel else (10, 8, 14, 200))
            canvas.blit(panel, (x, y))
            if sel:
                pulse = int(40 * (0.5 + 0.5 * math.sin(t * 5)))
                border = (215 + pulse // 2, 120 + pulse, 60)
                glow = pygame.Surface((cw, 30), pygame.SRCALPHA)
                for yy in range(30):
                    pygame.draw.line(glow, (255, 120, 50, int(50 * (1 - yy / 30))), (0, 29 - yy), (cw, 29 - yy))
                canvas.blit(glow, (x, y + 8))
            else:
                border = (56, 46, 70)
            pygame.draw.rect(canvas, border, (x, y, cw, ch), 1)
            for cx, cy in ((x, y), (x + cw - 2, y), (x, y + ch - 2), (x + cw - 2, y + ch - 2)):
                pygame.draw.rect(canvas, border, (cx, cy, 2, 2))
            card = self.hero_card(key, 2)
            canvas.blit(card, (x + cw // 2 - card.get_width() // 2, y + 2))
            text(canvas, font, wp["name"], x + cw // 2, y + 43, (250, 210, 160) if sel else (170, 150, 150),
                 center=True)
            text(canvas, font, wp["role"], x + cw // 2, y + 53, (150, 120, 160) if sel else (100, 90, 110),
                 center=True, shadow=False)
            for j, (lbl, val) in enumerate(zip(("GÜÇ", "HIZ", "ERİM"), wp["stats"])):
                sy = y + 65 + j * 9
                for b in range(5):
                    c = ((235, 120, 50) if b < val else (36, 28, 42)) if sel else \
                        ((150, 90, 50) if b < val else (30, 24, 36))
                    pygame.draw.rect(canvas, c, (x + 34 + b * 6, sy + 2, 5, 4))
                text(canvas, font, lbl, x + 5, sy - 1, (150, 132, 160) if sel else (100, 90, 110), shadow=False)
        # seçili silahın yetenekleri
        wp = WEAPONS[WEAPON_ORDER[self.sel]]
        pygame.draw.rect(canvas, (12, 8, 16), (8, 136, W - 16, 27))
        pygame.draw.rect(canvas, (70, 44, 50), (8, 136, W - 16, 27), 1)
        text(canvas, font, wp["desc"], W // 2, 136, (220, 190, 170), center=True, shadow=False)
        for j, (sk, name, cd) in enumerate(wp["skills"]):
            bx = 14 + j * 102
            draw_skill_box(canvas, bx, 147, sk, SKILL_KEYS[j], 0, 1, t)
            text(canvas, font, name, bx + 18, 149, (255, 200, 140) if j == 2 else (200, 190, 210), shadow=False)
        text(canvas, font, "A / D seç  ·  J başla  ·  K kül sunağı  ·  ESC çık", W // 2, 167, (130, 115, 140),
             center=True)
        draw_kul(canvas, font, W - 6, 4, self.save["kul"], right=True)
        ck = self.save.get("checkpoint")
        if ck:
            pulse = int(50 * (0.5 + 0.5 * math.sin(t * 4)))
            text(canvas, font, f"C devam: {ck['floor']}. kat", 6, 4, (200 + pulse, 150 + pulse, 110))
            text(canvas, font, WEAPONS[ck["weapon"]]["name"], 6, 13, (130, 110, 130), shadow=False)
        if self.stage == "spirit":
            self.draw_spirits(canvas, font, big, t)


# --- Oyun durumu ---------------------------------------------------------------
class Game:
    def __init__(self, sfx, font, weapon="kilic", save=None, resume=None, spirit=None):
        self.sfx = sfx
        self.spirit = resume.get("spirit") if resume else spirit
        self.combo, self.combo_t, self.slowmo = 0, 0.0, 0.0
        self.scare_on = True
        self.scare_wait = 2          # art arda iki korku anı olmasın
        self.scare_t = 0.0
        self.save = save if save is not None else load_save()
        self.shards = []            # yerdeki kor kırıntıları [x, y, vx, vy, yaş, değer]
        self.kul_run = 0            # bu oyunda toplanan kül
        self.kul_frac = 0.0
        self.font = font
        self.weapon = weapon
        self.player = Player(0, 0, weapon)
        self.pshots, self.sched, self.effects, self.numbers = [], [], [], []
        self.flash = 0.0
        self.skill_uses = {}
        self.fx = Particles()
        self.bolts = []
        self.enemies = []
        self.hazards = []
        self.spawn_queue = []
        self.darkness = 0.0         # gölge bekçisi odanın ışığını yutar
        self.hitstop = 0.0
        self.shake = 0.0
        self.state = "in"           # in / play / reward / out / dead / ending
        self.state_t = 0.0
        self.choices = []
        self.choice_i = 0
        self.title_t = 0.0
        self.title = ("", "", (220, 130, 90))
        self.wave_t = 0.0
        self.reward_t = 0.0
        self.kills = 0
        self.log = []
        self.room = None
        # hikâye
        self.rescued = False
        self.quest = None           # Öykü'nün istediği eşyanın sırası
        self.carrying = None        # elimizdeki eşya
        self.endless = False
        self.dialog = None
        self.delivered = 0          # teslim edilen eşya sayısı (her biri +1 en yüksek can)
        self.oyku = None
        self.npc = None             # kör tüccar
        self.market = None
        self.fps = None             # kelebek boyutu
        self.butterflies = set()    # kelebek çıkmış katlar
        self.plans = {}             # kat -> özel oda planı
        self.spike_t = 0.0
        self.pact_i = 0
        self.blood_pacts = 0        # kan akdi sayısı (kayda geçer)
        self.extra_rewards = 0      # art arda seçilecek ek armağan
        self.siege_left = 0.0
        self.siege_spawn = 0.0
        self.boss_spawned = False
        self.boss_dying = None
        self.apply_perks(fresh=resume is None)
        test_boss = int(os.environ.get("KUL_BOSS", "0"))  # yalnızca test: doğrudan N. katın bekçisi
        if resume:
            self.restore(resume)
        elif test_boss:
            self.rescued = test_boss > 1
            self.quest = test_boss - 2 if test_boss > 1 else None
            self.enter_room(COLS // 2, "boss", test_boss * (FLOOR_LEN + 1) - 1, test_boss, FLOOR_LEN)
        elif os.environ.get("KUL_ROOM"):  # yalnızca test: doğrudan bir oda türüyle başla
            f = int(os.environ.get("KUL_FLOOR", "1"))
            self.enter_room(COLS // 2, os.environ["KUL_ROOM"], f * 8 - 3, f, 3)
        else:
            self.save["runs"] += 1
            self.save["checkpoint"] = None  # yeni yolculuk eski kaydın yerini alır
            self.enter_room(COLS // 2, "combat", 1, 1, 1)

    # --- kalıcı ilerleme ---------------------------------------------------------
    def apply_perks(self, fresh=True):
        p, sv = self.player, self.save
        lv = lambda k: perk_level(sv, k)
        p.max_hp += lv("can")
        p.hp = p.max_hp
        p.dmg += lv("guc")
        p.dash_cd_mul *= 0.85 ** lv("atilma")
        self.kul_mul = 1 + 0.25 * lv("miknatis")
        self.revives = lv("dirilis")
        if fresh and lv("miras"):
            key = random.choice(common_boons())
            p.apply_boon(key)
            self.log.append(f"miras {key}")

    def checkpoint(self):
        """Sığınaktan çıkarken kaydeder; devam edilince bir sonraki katın başından sürer."""
        p, r = self.player, self.room
        self.save["checkpoint"] = {
            "weapon": p.weapon, "hp": p.hp, "boons": dict(p.boons), "floor": r.floor + 1, "depth": r.depth + 1,
            "quest": self.quest, "rescued": self.rescued, "endless": self.endless,
            "delivered": self.delivered, "blood": self.blood_pacts, "spirit": self.spirit,
            "mastery": p.mastery_kills, "revives": self.revives, "kills": self.kills, "kul_run": self.kul_run,
        }
        write_save(self.save)

    def restore(self, c):
        p = self.player
        for key, lvl in c["boons"].items():
            if key in BOONS:
                for _ in range(lvl):
                    p.apply_boon(key)
        self.delivered = c.get("delivered", 0)
        self.blood_pacts = c.get("blood", 0)
        self.gain_mastery(c.get("mastery", 0), quiet=True)
        p.max_hp += self.delivered - self.blood_pacts
        p.dmg += 2 * self.blood_pacts
        p.hp = max(1, min(p.max_hp, c["hp"]))
        self.quest, self.rescued, self.endless = c["quest"], c["rescued"], c["endless"]
        self.revives = min(self.revives, c.get("revives", 0))
        self.kills, self.kul_run = c.get("kills", 0), c.get("kul_run", 0)
        self.log.append(f"devam {c['floor']}. kat")
        self.enter_room(COLS // 2, "combat", c["depth"], c["floor"], 1)

    def drop_kul(self, x, y, value):
        n = min(value, 24)
        for i in range(n):
            a = random.uniform(0, math.tau)
            sp = random.uniform(30, 80)
            worth = value // n + (1 if i < value % n else 0)
            self.shards.append([x, y, math.cos(a) * sp, math.sin(a) * sp - 20, 0.0, worth])

    def add_kul(self, value):
        self.kul_frac += value * self.kul_mul
        whole = int(self.kul_frac)
        self.kul_frac -= whole
        self.kul_run += whole
        self.save["kul"] += whole
        self.save["total_kul"] += whole

    def update_shards(self, dt):
        p = self.player
        keep = []
        for s in self.shards:
            s[4] += dt
            if s[4] < 0.35 or p.hp <= 0:  # önce saçılır
                s[2] *= math.exp(-5 * dt)
                s[3] = s[3] * math.exp(-5 * dt) + 60 * dt
            else:  # sonra oyuncuya çekilir
                dx, dy = p.x - s[0], p.y - 6 - s[1]
                d = math.hypot(dx, dy) or 1
                if d < 6:
                    self.add_kul(s[5])
                    if random.random() < 0.5:
                        self.sfx.play("pick", 0.25)
                    continue
                pull = 260 + s[4] * 300
                s[2] += dx / d * pull * dt
                s[3] += dy / d * pull * dt
                sp = math.hypot(s[2], s[3])
                if sp > 220:
                    s[2], s[3] = s[2] / sp * 220, s[3] / sp * 220
            s[0] += s[2] * dt
            s[1] += s[3] * dt
            keep.append(s)
        self.shards = keep

    # --- oda geçişleri ---------------------------------------------------------
    def next_room(self):
        r = self.room
        if r.kind == "boss":
            if r.item:  # yerde bırakılan eşyayı otomatik al
                self.pick_item()
            self.enter_room(r.door_col, "haven", r.depth, r.floor, r.idx + 1)
        elif r.kind == "haven":
            self.checkpoint()
            self.enter_room(r.door_col, "combat", r.depth + 1, r.floor + 1, 1)
        else:
            idx = r.idx + 1
            self.enter_room(r.door_col, self.room_kind(r.floor, idx), r.depth + 1, r.floor, idx)

    def room_kind(self, floor, idx):
        if idx == FLOOR_LEN:
            return "boss"
        if idx in REST_IDX:
            return "rest"
        if floor not in self.plans:  # her katta bir hazine/tüccar, hikâye katlarında bir de anı
            first = random.choice(("hazine", "dukkan"))
            other = "dukkan" if first == "hazine" else "hazine"
            late = "ani" if floor <= len(MEMORIES) and not self.endless else random.choice((other, "combat"))
            a, b = random.choice((2, 3)), random.choice((5, 6))
            self.plans[floor] = {a: "tansi" if floor >= 3 else first, b: late}
            # kalan iki odadan biri kesin, öteki bazen olay odası olur
            events = random.sample(("lanet", "kusatma"), 2)
            rest = [5 - a, 11 - b]
            random.shuffle(rest)
            self.plans[floor][rest[0]] = events[0]
            if random.random() < 0.4:
                self.plans[floor][rest[1]] = events[1]
        return self.plans[floor].get(idx, "combat")

    def enter_room(self, entry_col, kind, depth, floor, idx):
        global CUR
        for s in self.shards:  # odada kalan küller kendiliğinden toplanır
            self.add_kul(s[5])
        self.shards = []
        if floor > self.save["best_floor"]:
            self.save["best_floor"] = floor
        write_save(self.save)
        tansi = kind == "tansi"
        if tansi:
            kind = "dukkan"
        self.room = Room(depth, entry_col, random.Random(), kind, floor, idx)
        self.room.tansi = tansi
        self.scare_wait = max(0, self.scare_wait - 1)
        self.room.decor = self.delivered
        CUR = self.room
        self.room.bg = build_background(self.room, self.font)
        self.player.place(entry_col * TILE + 8, (ROWS - 2) * TILE + 12)
        self.player.face = 1
        self.enemies, self.bolts, self.hazards, self.spawn_queue = [], [], [], []
        self.pshots, self.sched, self.effects, self.numbers = [], [], [], []
        self.state, self.state_t = "in", 0.0
        self.title_t = 2.4
        self.wave_t = 1.0
        self.reward_t = 0.0
        self.boss_spawned = False
        self.darkness = self.room.dark
        self.spike_t = 0.0
        self.market = None
        self.siege_left, self.siege_spawn = SIEGE_TIME, 1.2
        self.oyku = Oyku(160, 76) if kind == "haven" else Oyku(160, 70, ghost=True) if kind == "ani" else None
        self.npc = Merchant(160, 70, tansi) if kind == "dukkan" else None
        p = self.player
        if p.room_shield:
            p.shield, p.shield_t = max(p.shield, p.room_shield), 60.0
        if kind == "combat" and floor not in self.butterflies and \
                (os.environ.get("KUL_BUTTERFLY") or random.random() < BUTTERFLY_CHANCE):
            self.butterflies.add(floor)  # bir katta en fazla bir kez
            self.log.append("kelebek cikti")
            self.enemies.append(Butterfly(random.randint(60, 260), random.randint(40, 110)))
        self.log.append(f"{floor}-{idx} {kind}")
        if kind == "combat":
            sub = ROOM_VARIANTS.get(self.room.variant, "küllerden doğanlar")
            self.title = (f"ODA {idx}", f"{floor}. kat · {sub}", (220, 130, 90))
        elif kind == "rest":
            self.title = ("KOR SUNAĞI", "dinlen, yaralarını sar", (220, 130, 90))
        elif kind == "hazine":
            self.title = ("GÖMÜLÜ SANDIK", "kilidi paslı, biri onu burada unutmuş", (230, 190, 100))
        elif tansi:
            self.title = ("TANSİ", "kül karşılığı gerçek güç", (255, 170, 90))
        elif kind == "dukkan":
            self.title = ("KÖR TÜCCAR", "külünü duyuyor", (190, 150, 220))
        elif kind == "ani":
            m = self.memory()
            self.title = (m["title"], m["sub"], (190, 200, 255))
        elif kind == "lanet":
            self.title = ("LANETLİ SUNAK", "dokunmadan da geçebilirsin", (200, 110, 220))
        elif kind == "kusatma":
            self.title = ("KUŞATMA", "kapı kilitli, küller durmuyor", (240, 130, 80))
        elif kind == "boss":
            name = boss_info(floor)[1]
            if self.quest is not None and self.quest < len(ITEMS) and not self.endless:
                sub = f"{ITEMS[self.quest]['name']} onun elinde"
            elif not self.rescued:
                sub = "Öykü'nün zindanını o bekliyor"
            else:
                sub = "kapının sahibi uyanıyor"
            self.title = (name, sub, (230, 70, 60))
        else:
            self.title = ("ÖYKÜ'NÜN SIĞINAĞI", "mahzende renk kalan tek yer", (255, 150, 190))
        self.sfx.start_music({"boss": "boss", "haven": "haven", "ani": "haven"}.get(kind, "calm"))

    def try_scare(self):
        """Hasar almadan bitirilen oda bazen bunu ödüllendirir. Ödülü korku takip eder."""
        room = self.room
        if room.scare_checked or not self.scare_on:
            return False
        room.scare_checked = True
        force = os.environ.get("KUL_SCARE")
        if room.kind not in ("combat", "boss", "kusatma") or (room.took_hit and force != "2"):
            return False
        if not force and (self.scare_wait > 0 or random.random() >= SCARE_CHANCE):
            return False
        self.scare_wait = 3
        self.state, self.state_t = "scare", 0.0
        self.sfx.start_music(None)
        self.log.append("korku")
        return True

    def update_scare(self):
        if self.state_t < SCARE_TIME:
            if self.state_t > 0.2 and not self.scare_t:
                self.scare_t = 1.0
                self.sfx.play("scare")
            return
        self.scare_t = 0.0
        bonus = 5 * self.room.floor
        self.add_kul(bonus)
        self.state, self.state_t = "play", 0.0
        self.title = ("HÂLÂ BURADASIN", f"cesaretin için +{bonus} kül", (220, 210, 210))
        self.title_t = 2.2
        self.sfx.start_music("boss" if self.room.kind == "boss" and not self.room.cleared else "calm")

    def start_fps(self):
        self.fps = FpsMode(self)
        self.state, self.state_t = "fps", 0.0
        self.sfx.play("roar", 0.5)
        self.sfx.start_music("boss")

    def end_fps(self):
        self.log.append(f"boyut {self.fps.kills}")
        self.fps = None
        self.state, self.state_t = "play", 0.0
        self.player.invuln = 1.5
        self.flash = 0.1
        self.sfx.start_music("calm")

    def memory(self):
        return MEMORIES[min(self.room.floor, len(MEMORIES)) - 1]

    def spike_state(self, grp):
        """0 kapalı, 1 uyarı, 2 açık; iki grup sırayla çıkar."""
        ph = (self.spike_t + grp * SPIKE_PERIOD / 2) % SPIKE_PERIOD
        return 2 if ph >= SPIKE_PERIOD * 0.75 else 1 if ph >= SPIKE_PERIOD * 0.5 else 0

    def say(self, speaker, lines):
        self.dialog = {"lines": lines, "i": 0, "chars": 0.0, "after": None, "blip": 0, "speaker": speaker}

    def open_chest(self):
        room = self.room
        c = room.chest
        c["open"] = True
        self.wave_t = 0.6
        self.log.append("sandik " + ("mimic" if c["mimic"] else "acik"))
        if c["mimic"]:
            c["gone"] = True
            room.clear_tile(c["x"] // TILE, 4)
            self.enemies.append(Mimic(c["x"], c["y"] - 2, 9 + room.depth))
            self.title = ("AÇ SANDIK", "seni bekliyormuş", (230, 90, 70))
            self.title_t = 2.0
            self.sfx.play("roar", 0.6)
            self.shake = 4
            return
        self.sfx.play("item")
        self.drop_kul(c["x"], c["y"] - 12, 8 + 3 * room.floor)
        self.fx.burst(c["x"], c["y"] - 12, 24, [(255, 230, 140), (255, 190, 80), (255, 250, 220)], speed=70,
                      life=0.8, grav=-30)

    def pact_ok(self, key):
        if key == "kan_akdi":
            return self.player.max_hp >= 3
        if key == "kul_borcu":
            return self.save["kul"] >= PACT_MIN_KUL
        return True

    def open_pact(self):
        self.pact_i = 0
        self.title_t = 0.0
        self.state, self.state_t = "pact", 0.0

    def update_pact(self, nav, attack_pressed, dash_pressed):
        if nav:
            self.pact_i = (self.pact_i + nav) % len(PACTS)
            self.sfx.play("select")
        if dash_pressed:
            self.state, self.state_t = "play", 0.0
            return
        if not attack_pressed or self.state_t < 0.2:
            return
        key = list(PACTS)[self.pact_i]
        if not self.pact_ok(key):
            self.sfx.play("fizzle")
            return
        room, p = self.room, self.player
        room.shrine["used"] = True
        self.log.append(f"akit {key}")
        self.state, self.state_t = "play", 0.0
        self.sfx.play("roar", 0.5)
        self.shake = 5
        self.fx.burst(room.shrine["x"], 66, 40, [(230, 170, 255), (150, 70, 220), (70, 24, 60)], speed=90, life=0.9,
                      grav=-30)
        if key == "kan_akdi":
            self.blood_pacts += 1
            p.max_hp -= 1
            p.hp = min(p.hp, p.max_hp)
            p.dmg += 2
            self.title = ("KAN AKDİ", "silahın senden içti", (230, 70, 90))
            self.title_t = 2.0
        elif key == "kul_borcu":
            self.save["kul"] -= self.save["kul"] // 2
            write_save(self.save)
            self.extra_rewards = 1
            self.offer_rewards()
        else:
            room.cleared, room.door_open, room.door_anim = False, False, 0.0
            room.pact_fight = True
            room.waves_left, room.wave_index = 2, 2
            self.wave_t = 0.8
            self.extra_rewards = 1
            self.sfx.play("door", 0.8)
            self.title = ("KOR YEMİNİ", "kapı kapandı", (255, 150, 70))
            self.title_t = 2.0

    def update_siege(self, dt):
        room = self.room
        self.siege_left -= dt
        if self.siege_left <= 0:
            room.cleared = True
            self.reward_t = 0.9
            self.bolts, self.hazards = [], []
            for e in self.enemies:
                e.dead = True
                self.fx.burst(e.x, e.y - 6, 14, [(80, 74, 86), (110, 102, 114)], speed=60, life=0.8, grav=-30)
            self.drop_kul(self.player.x, self.player.y - 20, 10 + 3 * room.floor)
            self.title = ("DAYANDIN", "küller çekiliyor", (255, 200, 120))
            self.title_t = 2.0
            self.sfx.play("boom", 0.5)
            self.log.append("kusatma bitti")
            return
        self.siege_spawn -= dt
        if self.siege_spawn <= 0 and len(self.enemies) < 8:
            room.wave_index = 0  # her dalga aynı büyüklükte kalsın
            self.spawn_wave()
            self.siege_spawn = 4.5

    def open_market(self):
        p, f = self.player, self.room.floor
        if not self.market:
            if self.room.tansi:  # Tansi yalnızca kendi güçlerini satar
                pool = [k for k in TANSI_WARES if p.boons.get(k, 0) < BOONS[k]["max"]]
                random.shuffle(pool)
                wares = [{"key": k, "price": 45 + 10 * (f - 3) + 25 * p.boons.get(k, 0), "sold": False}
                         for k in pool[:3]] or [{"key": "sifa", "price": 10, "sold": False}]
                self.market = {"wares": wares, "i": 0, "quote": "Kestiklerinin külü burada para eder!"}
            else:
                pool = [k for k in common_boons() if p.boons.get(k, 0) < BOONS[k]["max"]]
                random.shuffle(pool)
                wares = [{"key": k, "price": 18 + 7 * (f - 1), "sold": False} for k in pool[:2]]
                wares.append({"key": "sifa", "price": 8 + 3 * (f - 1), "sold": False})
                self.market = {"wares": wares, "i": 0, "quote": "Külün kokusunu alırım, göze ihtiyacım yok."}
        self.title_t = 0.0
        self.state, self.state_t = "market", 0.0
        self.log.append("tuccar")

    def update_market(self, nav, attack_pressed, dash_pressed):
        m = self.market
        if nav:
            m["i"] = (m["i"] + nav) % len(m["wares"])
            self.sfx.play("select")
        if dash_pressed:
            self.state, self.state_t = "play", 0.0
            return
        if attack_pressed and self.state_t > 0.2:
            w = m["wares"][m["i"]]
            if w["sold"] or self.save["kul"] < w["price"]:
                self.sfx.play("fizzle")
                return
            self.save["kul"] -= w["price"]
            write_save(self.save)
            w["sold"] = True
            self.player.apply_boon(w["key"])
            self.log.append(f"satin {w['key']}")
            self.sfx.play("pick")

    # --- dövüş ---------------------------------------------------------------------
    def spawn_wave(self):
        room = self.room
        n_ghoul, n_wisp = room.enemy_plan()
        room.wave_index += 1
        room.waves_left -= 1
        hp_g = 3 + room.depth // 4
        hp_w = 2 + room.depth // 5
        free = [(tx, ty) for ty in range(1, ROWS - 2) for tx in range(1, COLS - 1)
                if not room.solid(tx, ty)]
        random.shuffle(free)
        kinds = ["w"] * n_wisp
        for _ in range(n_ghoul):  # derine indikçe hortlakların yerini başkaları alır
            r = random.random()
            if room.depth >= 2 and r < 0.25:
                kinds += ["c", "c"]
            elif room.depth >= 3 and r < 0.42:
                kinds.append("b")
            elif room.depth >= 5 and r < 0.58:
                kinds.append("s")
            else:
                kinds.append("g")
        force = os.environ.get("KUL_ENEMY")  # yalnızca test
        if force:
            kinds = [force] * len(kinds)
        hp_b, hp_s = 3 + room.depth // 4, 5 + room.depth // 4
        make = {"g": lambda x, y: Ghoul(x, y, hp_g), "w": lambda x, y: Wisp(x, y, hp_w),
                "c": lambda x, y: Crawler(x, y), "b": lambda x, y: Bloat(x, y, hp_b),
                "s": lambda x, y: Guard(x, y, hp_s)}
        for tx, ty in free:
            if not kinds:
                break
            x, y = tx * TILE + 8, ty * TILE + 12
            if math.hypot(x - self.player.x, y - self.player.y) > 72:
                k = kinds.pop()
                self.enemies.append(make[k](x, y))
                self.fx.burst(x, y - 2, 8, [(70, 64, 76), (110, 100, 110)], speed=25, life=0.7)
        self.sfx.play("spawn")

    def spawn_boss(self):
        f = self.room.floor
        cls, name = boss_info(f)
        b = cls(W // 2, 66, 30 + 14 * (f - 1), f)
        b.name = name
        self.enemies.append(b)
        self.boss_spawned = True
        self.sfx.play("spawn")
        self.log.append(f"bekci {b.name}")

    def boss(self):
        for e in self.enemies:
            if isinstance(e, Boss):
                return e
        return None

    def offer_rewards(self):
        p = self.player
        pool = [k for k in common_boons() if p.boons.get(k, 0) < BOONS[k]["max"]]
        random.shuffle(pool)
        self.choices = pool[:3]
        if not self.choices:  # her armağan en üst seviyede: yalnızca şifa kalır
            self.choices = ["sifa"]
        elif p.hp < p.max_hp and random.random() < 0.6:
            self.choices[-1] = "sifa"
        self.choice_i = 1
        self.state, self.state_t = "reward", 0.0

    def combo_bonus(self):
        return 2 if self.combo >= 25 else 1 if self.combo >= 10 else 0

    def damage_enemy(self, e, dmg, aim, knock=190, stun=0.0, pure=False):
        """pure: yanma ve sıçrama gibi ikincil hasar; kombo ve ruh tetiklemez."""
        if getattr(e, "invuln", 0) > 0 or e.dead:
            return
        if e.blocks(aim, dmg):  # kalkana çarptı
            e.kb = [aim[0] * 50, aim[1] * 50]
            bx, by = e.body_rect().center
            self.fx.burst(bx - aim[0] * 8, by - aim[1] * 6, 7, [(240, 240, 255), (170, 180, 210)], speed=70,
                          life=0.2)
            self.sfx.play("door", 0.35)
            self.hitstop = max(self.hitstop, 0.03)
            return
        p0 = self.player
        if not pure:
            dmg += self.combo_bonus()
            if p0.crit:
                p0.crit = False
                dmg = dmg * 2 + 1
                self.fx.ring(e.x, e.y - 8, 16, (190, 235, 255), 80, 0.25)
            self.combo += 1
            self.combo_t = 2.6
        e.hit(dmg, aim, knock)
        if isinstance(e, Butterfly):
            self.log.append("kelebek")
            self.start_fps()
            return
        if not pure and self.spirit and not e.dead:
            self.apply_spirit(e, dmg)
        if stun and not isinstance(e, Boss):
            e.stun = max(e.stun, stun)
        bx0, by0 = e.body_rect().midtop
        self.numbers.append([bx0 + random.randint(-3, 3), by0 - 2, 0.7, dmg])
        self.hitstop = max(self.hitstop, 0.05)
        self.shake = max(self.shake, 2)
        bx, by = e.body_rect().center
        self.fx.burst(bx, by, 6, [(255, 230, 200), (240, 120, 60)], speed=90, life=0.25)
        if isinstance(e, Boss) and getattr(e, "enraged", False):
            e.enraged = False  # ikinci evre: öfke kükremesi
            self.sfx.play("roar")
            self.shake = 8
            self.fx.ring(bx, by, 40, (255, 120, 50), 130, 0.5)
            self.fx.ring(bx, by, 24, (255, 230, 150), 80, 0.4)
            self.title = ("ÖFKELENDİ", "", (255, 90, 60))
            self.title_t = 1.4
        if e.dead:
            self.gain_mastery(6 if isinstance(e, Boss) else 1)
        if e.dead and isinstance(e, Boss):
            self.kills += 1
            self.boss_dying = {"boss": e, "t": 0.0, "tick": 0.0}
            for m in self.enemies:
                if m is not e and not m.dead:
                    m.dead = True
                    self.fx.burst(m.x, m.y - 6, 16, [(80, 74, 86), (110, 102, 114)], speed=60, life=0.8, grav=-30)
            self.bolts, self.hazards = [], []
            self.hitstop = 0.3
            self.shake = 6
            self.sfx.play("roar")
            self.sfx.start_music(None)
            return
        if e.dead:
            self.kills += 1
            self.hitstop = 0.08
            self.shake = 3
            self.sfx.play("kill")
            ashc = [(80, 74, 86), (110, 102, 114), (60, 54, 66)]
            if isinstance(e, Wisp):
                ashc = [(255, 200, 90), (235, 110, 50), (150, 40, 30)]
            if not isinstance(e, ShadeClone):
                self.drop_kul(bx, by, e.KUL)
            if isinstance(e, Bloat) and e.state != "swell":  # ölürken de patlar, kısa fitille
                self.hazards.append(Hazard(e.x, e.y, Bloat.BLAST_R, 0.4, "burst"))
            self.fx.burst(bx, by, 26, ashc, speed=70, life=0.9, grav=-30)
            self.fx.burst(bx, by, 8, [(240, 110, 50), (255, 180, 80)], speed=50, life=0.8, grav=-40)
            p = self.player
            if p.lifesteal and p.hp < p.max_hp and random.random() < p.lifesteal:
                p.hp += 1
                self.sfx.play("heal", 0.6)
                self.fx.burst(p.x, p.y - 8, 10, [(220, 50, 60), (255, 120, 120)], speed=30, life=0.7, grav=-50)
        else:
            self.sfx.play("hit", 0.7 if isinstance(e, Boss) else 1.0)

    def player_hit(self, sx, sy):
        p = self.player
        if not p.hurt(sx, sy):
            return
        self.room.took_hit = True
        self.combo = 0
        self.hitstop = 0.1
        self.shake = 5
        self.sfx.play("hurt")
        self.fx.burst(p.x, p.y - 6, 14, [(200, 40, 50), (120, 20, 30)], speed=80, life=0.5, grav=120)
        if p.thorns:  # kor pelerin: çevreye patlama
            self.fx.ring(p.x, p.y - 6, 28, (255, 160, 60), 110, 0.35)
            self.fx.ring(p.x, p.y - 6, 18, (255, 230, 150), 70, 0.3)
            for e in list(self.enemies):
                if e.active() and math.hypot(e.x - p.x, e.y - p.y) < 40:
                    self.damage_enemy(e, p.thorns * 2, norm(e.x - p.x, e.y - p.y))
        if p.hp <= 0 and self.revives > 0:  # Son Kor: bir kez diril
            self.revives -= 1
            p.hp = min(2, p.max_hp)
            p.invuln = 2.5
            self.bolts = []
            self.hitstop = 0.35
            self.shake = 8
            self.sfx.play("heal")
            self.fx.ring(p.x, p.y - 6, 40, (255, 200, 110), 140, 0.6)
            self.fx.burst(p.x, p.y - 6, 40, [(255, 240, 200), (255, 180, 80), (235, 110, 50)], speed=90,
                          life=1.0, grav=-60)
            self.title = ("SON KOR", "küllerinden yeniden yandın", (255, 190, 100))
            self.title_t = 2.0
            self.log.append("dirilis")
            return
        if p.hp <= 0:
            self.save["checkpoint"] = None
            write_save(self.save)
            self.sfx.play("dead")
            self.sfx.start_music(None)
            self.fx.burst(p.x, p.y - 6, 40, [(76, 68, 98), (44, 38, 60), (240, 80, 60)],
                          speed=80, life=1.2, grav=-25)
            self.state, self.state_t = "dead", 0.0

    def explode(self, h):
        p = self.player
        if ((p.x - h.x) / h.r) ** 2 + ((p.y - h.y) / (h.r * 0.6)) ** 2 <= 1.15:
            self.player_hit(h.x, h.y)
        if h.kind == "burst":  # kül şişkini: yakındaki düşmanları da yakar
            self.area_damage(h.x, h.y, h.r, 2, knock=170)
            self.fx.ring(h.x, h.y - 2, h.r, (240, 140, 80), 100, 0.3)
        if h.kind == "pillar":  # yerden fışkıran ateş sütunu
            self.shake = max(self.shake, 2)
            self.sfx.play("boom", 0.25)
            self.fx.burst(h.x, h.y - 4, 16, [(255, 230, 140), (255, 160, 60), (220, 70, 30)], speed=40,
                          life=0.6, grav=-160)
            return
        if h.kind == "reap":  # orak darbesi
            self.shake = max(self.shake, 4)
            self.fx.burst(h.x, h.y - 10, 18, [(220, 210, 255), (130, 100, 220), (40, 30, 70)], speed=100,
                          life=0.35)
            return
        if h.kind == "slam":
            self.shake = max(self.shake, 7)
            self.sfx.play("slam")
            self.fx.ring(h.x, h.y - 2, 30, (130, 120, 130), 95, 0.45)
            self.fx.burst(h.x, h.y - 2, 20, [(255, 200, 90), (235, 110, 50), (90, 84, 96)], speed=80, life=0.6,
                          grav=40)
        else:
            self.shake = max(self.shake, 3)
            self.sfx.play("boom", 0.35)
            self.fx.burst(h.x, h.y - 2, 18, [(255, 220, 120), (235, 110, 50), (150, 40, 30)], speed=70,
                          life=0.5, grav=-20)

    def update_boss_death(self, dt):
        d = self.boss_dying
        b = d["boss"]
        d["t"] += dt
        d["tick"] -= dt
        b.flash = 0.05 if int(d["t"] * 12) % 2 else 0.0
        self.shake = max(self.shake, 2 + d["t"] * 2)
        if d["tick"] <= 0:
            d["tick"] = 0.14
            ox, oy = b.x + random.uniform(-14, 14), b.y - random.uniform(6, 44)
            self.fx.burst(ox, oy, 14, [(255, 220, 120), (235, 110, 50), (90, 84, 96)], speed=80, life=0.6)
            self.sfx.play("hit", 0.6)
        if d["t"] >= 2.2:
            self.fx.burst(b.x, b.y - 24, 90, [(255, 240, 200), (255, 200, 90), (235, 110, 50), (100, 92, 108)],
                          speed=150, life=1.4, grav=-20)
            self.fx.ring(b.x, b.y - 24, 48, (255, 230, 150), 170, 0.6)
            self.shake = 10
            self.sfx.play("boom")
            self.boss_dying = None
            room = self.room
            room.cleared = True
            self.reward_t = 2.2
            self.drop_kul(b.x, b.y - 20, 15 + 8 * b.floor)
            self.title = ("BEKÇİ DÜŞTÜ", f"{b.name.lower()} küle döndü", (255, 200, 120))
            self.title_t = 2.4
            if self.quest is not None and self.quest < len(ITEMS) and not self.endless:
                room.item = [b.x, b.y - 4, self.quest]
            self.sfx.start_music("calm")

    def pick_item(self):
        room = self.room
        idx = room.item[2]
        self.carrying = idx
        self.fx.burst(room.item[0], room.item[1] - 6, 30, [(255, 255, 230), (255, 220, 120), (180, 200, 255)],
                      speed=70, life=1.0, grav=-40)
        room.item = None
        self.sfx.play("item")
        self.title = (f"{ITEMS[idx]['name'].upper()} BULUNDU", "Öykü'ye götür", (255, 220, 140))
        self.title_t = 2.4
        self.log.append(f"esya {ITEMS[idx]['name']}")

    # --- yetenekler ------------------------------------------------------------------
    def schedule(self, delay, fn):
        self.sched.append([delay, fn])

    def effect(self, kind, x, y, total, **kw):
        e = {"kind": kind, "x": x, "y": y, "t": total, "total": total}
        e.update(kw)
        self.effects.append(e)
        return e

    def area_damage(self, x, y, r, dmg, knock=150, stun=0.0, bolts=False):
        n = 0
        for e in list(self.enemies):
            if not e.active():
                continue
            rr = r + (10 if isinstance(e, Boss) else 0)
            if ((e.x - x) / rr) ** 2 + ((e.y - y) / (rr * 0.7)) ** 2 <= 1.0:
                self.damage_enemy(e, dmg, norm(e.x - x, e.y - y), knock=knock, stun=stun)
                n += 1
        if bolts:
            for b in self.bolts:
                if math.hypot(b.x - x, b.y + b.h - y) < r:
                    b.dead = True
                    self.fx.burst(b.x, b.y, 6, [(255, 230, 150), (235, 110, 50)], speed=50, life=0.3)
        return n

    @staticmethod
    def clamp_point(x, y):
        return min(max(x, 24), W - 24), min(max(y, 26), WORLD_H - 20)

    def use_skill(self, slot):
        p = self.player
        if p.skill_cd[slot] > 0 or p.busy() or p.hp <= 0:
            return
        if slot == 3 and not p.has_beam:
            return
        key, name, cd = BEAM_SKILL if slot == 3 else p.wp["skills"][slot]
        p.skill_cd[slot] = cd * p.cdr
        self.skill_uses[key] = self.skill_uses.get(key, 0) + 1
        d = p.dmg
        ax, ay = p.aim
        x, y = p.x, p.y
        sfx = self.sfx
        if key == "saplama":
            p.start_dash((ax, ay), 390, 0.2, 3 * d + 1)
            sfx.play("charge", 0.7)
        elif key == "donen":
            self.pshots.append(PShot(x, y - 8, ax * 240, ay * 240, 2 + d, pierce=99, kind="ghost", life=0.4))

            def back(ex=x + ax * 96, ey=y - 8 + ay * 96):
                ux, uy = norm(p.x - ex, p.y - 8 - ey)
                self.pshots.append(PShot(ex, ey, ux * 260, uy * 260, 2 + d, pierce=99, kind="ghost", life=0.5))
            self.schedule(0.42, back)
            sfx.play("dash", 0.8)
        elif key == "kazik":
            for ring, r in enumerate((26, 46, 66)):
                def spikes(r=r, n=6 + ring * 3):
                    for i in range(n):
                        a = i * math.tau / n
                        sx, sy = p.x + math.cos(a) * r, p.y + math.sin(a) * r * 0.75
                        if not CUR.solid(int(sx) // TILE, int(sy) // TILE):
                            self.area_damage(sx, sy, 16, 2 * d + 1, knock=120, stun=0.6)
                            self.effect("spike", sx, sy, 0.45)
                    self.shake = max(self.shake, 4)
                    sfx.play("slam", 0.5)
                self.schedule(ring * 0.14, spikes)
        elif key == "halka":
            self.area_damage(x, y - 2, 46, 2 + 2 * d, knock=240, bolts=True)
            self.fx.ring(x, y - 4, 42, (255, 170, 70), 160, 0.4)
            self.fx.ring(x, y - 4, 26, (255, 230, 150), 100, 0.35)
            sfx.play("boom", 0.5)
            self.shake = max(self.shake, 4)
        elif key == "isik":
            dist = 84
            while dist > 0:
                tx, ty = self.clamp_point(x + ax * dist, y + ay * dist)
                if not feet_blocked(tx, ty):
                    break
                dist -= 8
            else:
                tx, ty = x, y
            self.area_damage(x, y, 30, 2 + d, knock=180)
            self.fx.burst(x, y - 6, 24, [(200, 230, 255), (255, 200, 120)], speed=90, life=0.45)
            p.x, p.y = tx, ty
            p.invuln = max(p.invuln, 0.35)
            self.fx.ring(tx, ty - 6, 20, (220, 235, 255), 90, 0.3)
            sfx.play("item", 0.5)
        elif key == "meteor":
            targets = [(e.x, e.y) for e in self.enemies if e.active() and not e.passive]
            for i in range(7):
                if targets:
                    gx, gy = random.choice(targets)
                    gx, gy = gx + random.uniform(-14, 14), gy + random.uniform(-10, 10)
                else:
                    gx, gy = x + random.uniform(-70, 70), y + random.uniform(-50, 50)
                gx, gy = self.clamp_point(gx, gy)

                def strike(gx=gx, gy=gy):
                    self.area_damage(gx, gy, 26, 3 + 2 * d, knock=170, bolts=True)
                    self.effect("crater", gx, gy, 0.5, r=20)
                    self.fx.burst(gx, gy - 4, 20, [(255, 230, 150), (255, 140, 60), (150, 40, 30)], speed=90, life=0.5)
                    self.shake = max(self.shake, 4)
                    sfx.play("boom", 0.4)
                self.effect("target", gx, gy, 0.3 + i * 0.16, r=20)
                self.schedule(0.3 + i * 0.16, strike)
            sfx.play("charge")
        elif key == "isin":
            for i in range(7):
                def beam(i=i, ax=ax, ay=ay):
                    self.pshots.append(PShot(p.x, p.y - 8, ax * 300, ay * 300, 2 + 2 * d, pierce=99, kind="ghost",
                                             life=1.0))
                self.schedule(i * 0.05, beam)
            sfx.play("charge")
            self.fx.ring(x, y - 8, 24, (230, 150, 255), 90, 0.35)
            self.shake = max(self.shake, 3)
        elif key == "girdap":
            self.area_damage(x, y - 2, 34 * p.reach, 2 * d, knock=240, bolts=True)
            self.effect("spin", x, y - 7, 0.3)
            sfx.play("slash")
            sfx.play("boom", 0.25)
            self.shake = max(self.shake, 3)
        elif key == "kesik":
            p.start_dash((ax, ay), 330, 0.22, 2 * d + 1)
            sfx.play("charge", 0.7)
        elif key == "hayalet":
            for i in range(10):
                a = i * math.tau / 10

                def fire(a=a):
                    self.pshots.append(PShot(p.x, p.y - 8, math.cos(a) * 170, math.sin(a) * 170, 2 + d,
                                             pierce=99, kind="ghost", life=0.9))
                self.schedule(i * 0.025, fire)
            sfx.play("charge")
            sfx.play("item", 0.4)
            self.shake = max(self.shake, 4)
            self.fx.ring(x, y - 8, 30, (150, 200, 255), 90, 0.4)
        elif key == "uclu":
            base = math.atan2(ay, ax)
            for off in (-0.22, 0.0, 0.22):
                a = base + off
                self.pshots.append(PShot(x, y - 8, math.cos(a) * 230, math.sin(a) * 230, d + 1, pierce=2))
            sfx.play("bow")
            sfx.play("bow", 0.6)
        elif key == "takla":
            p.start_dash((-ax, -ay), 300, 0.2)
            p.empower = True
            mx, my = x, y
            self.effect("mine", mx, my - 2, 0.4)

            def boom():
                self.area_damage(mx, my, 26, 2 + d, knock=200, stun=0.6)
                self.fx.burst(mx, my - 4, 26, [(255, 220, 120), (235, 110, 50), (150, 40, 30)], speed=90, life=0.5)
                self.fx.ring(mx, my - 2, 20, (255, 160, 60), 80, 0.3)
                sfx.play("boom", 0.4)
                self.shake = max(self.shake, 3)
            self.schedule(0.4, boom)
            sfx.play("dash")
        elif key == "yagmur":
            tx, ty = self.clamp_point(x + ax * 80, y + ay * 80)
            self.effect("rain", tx, ty, 1.6, r=36)
            for w in (0.5, 0.8, 1.1, 1.4):
                def wave(tx=tx, ty=ty):
                    self.area_damage(tx, ty, 36, 1 + d, knock=60)
                    self.fx.burst(tx, ty - 2, 10, [(200, 180, 140), (240, 240, 255)], speed=50, life=0.3)
                    sfx.play("bow", 0.5)
                self.schedule(w, wave)
            sfx.play("shoot")
        elif key == "fay":
            for i in range(6):
                def spike(i=i, ax=ax, ay=ay, x=x, y=y):
                    sx, sy = x + ax * (16 + i * 16), y + ay * (16 + i * 16)
                    if CUR.solid(int(sx) // TILE, int(sy) // TILE):
                        return
                    self.area_damage(sx, sy, 17, 2 * d + 1, knock=140, stun=0.7)
                    self.effect("spike", sx, sy, 0.45)
                    self.fx.burst(sx, sy - 3, 8, [(96, 86, 104), (140, 130, 150), (255, 150, 60)], speed=60,
                                  life=0.4, grav=120)
                    self.shake = max(self.shake, 3)
                    sfx.play("slam", 0.45)
                self.schedule(i * 0.07, spike)
        elif key == "demir":
            p.shield = 2
            p.shield_t = 4.0
            self.fx.ring(x, y - 7, 24, (190, 196, 220), 60, 0.4)
            sfx.play("door", 0.5)
            sfx.play("heal", 0.4)
        elif key == "goktasi":
            dist = 90
            while dist > 0:
                tx, ty = self.clamp_point(x + ax * dist, y + ay * dist)
                if not feet_blocked(tx, ty):
                    break
                dist -= 10
            else:
                tx, ty = x, y
            p.leap = {"sx": x, "sy": y, "tx": tx, "ty": ty, "t": 0.0, "total": 0.7}
            self.effect("target", tx, ty, 0.7, r=50)
            sfx.play("dash")
            sfx.play("charge", 0.5)
        elif key == "seri":
            for i in range(6):
                def jab(i=i):
                    jx, jy = p.x + p.aim[0] * 12, p.y - 2 + p.aim[1] * 12
                    self.area_damage(jx, jy, 16 * p.reach, d, knock=70)
                    self.effect("jab", p.x + random.randint(-3, 3), p.y - 8 + random.randint(-3, 3), 0.1,
                                d=p.aim)
                    sfx.play("punch", 0.5)
                self.schedule(i * 0.08, jab)
        elif key == "tekme":
            best, bd = None, 130
            for e in self.enemies:
                if not e.active():
                    continue
                dx, dy = e.x - x, e.y - y
                dd = math.hypot(dx, dy)
                if dd < bd and (dd < 30 or (dx * ax + dy * ay) / max(dd, 1) > 0.2):
                    best, bd = e, dd
            if best:
                dirv = norm(best.x - x, best.y - y)
                travel = max(0.05, min(0.32, (bd - 10) / 360))
            else:
                dirv, travel = (ax, ay), 0.2
            p.start_dash(dirv, 360, travel)
            sfx.play("dash")

            def kick(dirv=dirv, best=best):
                kx, ky = p.x + dirv[0] * 10, p.y + dirv[1] * 10
                hit = 0
                if best and best.active() and math.hypot(best.x - kx, best.y - ky) < 26:
                    self.damage_enemy(best, 3 + d, dirv, knock=380, stun=0.8)
                    hit = 1
                hit += self.area_damage(kx, ky, 14, 1 + d, knock=200)
                self.fx.burst(kx, ky - 6, 18, [(255, 220, 140), (240, 110, 50)], speed=100, life=0.35)
                self.shake = max(self.shake, 5 if hit else 2)
                sfx.play("slam", 0.6)
            self.schedule(travel, kick)
        elif key == "volkan":
            p.channel = 0.5
            sfx.play("charge")

    def mastery_strike(self):
        """Ustalıkla açılan özel vuruş."""
        p = self.player
        d = p.dmg
        ax, ay = p.attack_aim
        w = p.weapon
        if w == "kilic":
            self.pshots.append(PShot(p.x, p.y - 8, ax * 230, ay * 230, 1 + d, pierce=99, kind="ghost", life=0.55))
        elif w == "yay":
            base = math.atan2(ay, ax)
            for off in (-0.2, 0.2):
                a = base + off
                self.pshots.append(PShot(p.x, p.y - 8, math.cos(a) * 240, math.sin(a) * 240, d, pierce=2))
        elif w == "balyoz":
            self.area_damage(p.x + ax * 15, p.y + ay * 12, 42, 1 + d, knock=220, stun=0.4, bolts=True)
            self.fx.ring(p.x + ax * 15, p.y + ay * 12 - 2, 38, (255, 200, 120), 130, 0.4)
        elif w == "yumruk":
            self.area_damage(p.x + ax * 16, p.y + ay * 14, 24, 1 + d, knock=280)
            self.fx.ring(p.x + ax * 16, p.y + ay * 14 - 6, 18, (255, 170, 80), 100, 0.3)
        elif w == "mizrak":
            self.pshots.append(PShot(p.x, p.y - 8, ax * 280, ay * 280, 1 + d, pierce=3, kind="big"))
        elif w == "asa":
            base = math.atan2(ay, ax) + 0.28
            self.pshots.append(PShot(p.x, p.y - 8, math.cos(base) * 170, math.sin(base) * 170, 1 + d, kind="orb", life=0.9))

    def gain_mastery(self, n=1, quiet=False):
        p = self.player
        p.mastery_kills += n
        while p.mastery < len(MASTERY_KILLS) and p.mastery_kills >= MASTERY_KILLS[p.mastery]:
            p.mastery += 1
            if p.mastery == 2:
                p.dmg += 1
            elif p.mastery == 3:
                p.atk_cd_mul *= 0.85
            if quiet:
                continue
            sub = {1: MASTERY_NAMES[p.weapon], 2: "silah hasarı +1", 3: "özel vuruş sıklaştı, saldırı hızlandı"}[p.mastery]
            self.title = (f"USTALIK {p.mastery}", sub, (255, 210, 120))
            self.title_t = 2.2
            self.sfx.play("item", 0.7)
            self.log.append(f"ustalik {p.mastery}")

    def apply_spirit(self, e, dmg):
        kind = self.spirit
        if kind == "kor":
            e.burn = 2.6
        elif kind == "ayaz":
            e.slow = 1.6
            e.frost += 1
            if e.frost >= 5 and not isinstance(e, Boss):
                e.frost = 0
                e.stun = max(e.stun, 1.2)
                self.fx.burst(e.x, e.y - 8, 10, [(190, 230, 255), (255, 255, 255)], speed=50, life=0.4)
        elif kind == "simsek" and random.random() < 0.3:
            near = [m for m in self.enemies if m is not e and m.active() and not m.passive and
                    math.hypot(m.x - e.x, m.y - e.y) < 60]
            if near:
                m = min(near, key=lambda m: math.hypot(m.x - e.x, m.y - e.y))
                self.effect("zap", e.x, e.y - 8, 0.14, x2=m.x, y2=m.y - 8)
                self.damage_enemy(m, max(1, (dmg + 1) // 2), norm(m.x - e.x, m.y - e.y), knock=60, pure=True)

    def process_player_events(self):
        p = self.player
        d = p.dmg
        for ev in p.events:
            if ev == "perfect":
                p.perfect_cd = 1.2
                p.crit = True
                p.dash_cd = 0.0
                self.slowmo = 0.55
                self.title = ("KUSURSUZ", "sonraki vuruş ikiye katlanır", (170, 230, 255))
                self.title_t = 1.2
                self.fx.ring(p.x, p.y - 7, 30, (190, 235, 255), 120, 0.4)
                self.sfx.play("item", 0.7)
                self.log.append("kusursuz")
            elif ev == "orb":
                ax, ay = p.attack_aim
                self.pshots.append(PShot(p.x, p.y - 8, ax * 170, ay * 170, 1 + d, kind="orb", life=0.9))
            elif ev == "special":
                self.mastery_strike()
            elif ev == "arrow":
                ax, ay = p.attack_aim
                pierce = 1 + int((p.reach - 1) * 4)
                if p.empower:
                    p.empower = False
                    self.pshots.append(PShot(p.x, p.y - 8, ax * 280, ay * 280, 3 * d + 1, pierce=5, kind="big"))
                    self.fx.burst(p.x + ax * 8, p.y - 8, 8, [(255, 220, 120), (235, 110, 50)], speed=60, life=0.3)
                else:
                    self.pshots.append(PShot(p.x, p.y - 8, ax * 240, ay * 240, d, pierce=pierce))
            elif ev == "impact":  # balyoz yere iner
                ax, ay = p.attack_aim
                cx, cy = p.x + ax * 15, p.y + ay * 12
                r = 24 * p.reach
                n = self.area_damage(cx, cy, r, 2 * d + 1, knock=260, stun=0.3, bolts=True)
                self.fx.ring(cx, cy - 2, 22, (130, 120, 140), 80, 0.35)
                self.fx.burst(cx, cy - 2, 12, [(96, 86, 104), (140, 130, 150), (255, 160, 60)], speed=70,
                              life=0.4, grav=120)
                self.effect("crater", cx, cy, 0.35, r=r * 0.7)
                self.shake = max(self.shake, 4 if n else 3)
                self.sfx.play("slam", 0.7)
            elif ev == "land":  # göktaşı
                r = 50
                self.area_damage(p.x, p.y, r, 5 + 2 * d, knock=280, stun=1.5, bolts=True)
                self.effect("crater", p.x, p.y, 1.0, r=r)
                self.fx.ring(p.x, p.y - 2, 48, (255, 200, 120), 170, 0.5)
                self.fx.burst(p.x, p.y - 4, 50, [(96, 86, 104), (140, 130, 150), (255, 160, 60), (255, 230, 150)],
                              speed=130, life=0.8, grav=140)
                self.shake = 10
                self.flash = 0.08
                self.sfx.play("boom")
                p.invuln = max(p.invuln, 0.3)
            elif ev == "volkan":
                ax, ay = p.aim
                for i in range(5):
                    cx, cy = p.x + ax * (14 + i * 15), p.y + ay * (14 + i * 15)
                    r = 13 + i * 4
                    self.area_damage(cx, cy, r, 6 + 2 * d, knock=320)
                    self.effect("wave", cx, cy, 0.35 + i * 0.05, r=r)
                    self.fx.burst(cx, cy - 4, 12, [(255, 230, 150), (255, 140, 60), (200, 50, 30)], speed=90,
                                  life=0.5, grav=-30)
                self.shake = 9
                self.flash = 0.1
                self.sfx.play("boom")
                self.sfx.play("slam", 0.6)
            elif ev == "block":
                self.fx.ring(p.x, p.y - 7, 18, (220, 225, 240), 70, 0.3)
                self.sfx.play("door", 0.4)
        p.events = []

    # --- Öykü ve diyalog -------------------------------------------------------------
    def start_talk(self):
        room, p = self.room, self.player
        if room.kind == "ani":
            m = self.memory()
            self.say(m["speaker"], m["lines"])
            self.dialog["choices"], self.dialog["pick"] = m["choices"], None
            return
        if room.talked:
            lines, after = [random.choice(DIALOG_IDLE)], None
        elif not self.rescued:
            lines, after = DIALOG_RESCUE, "rescue"
        elif self.carrying is not None:
            lines, after = DIALOG_DELIVER[self.carrying], "deliver"
        else:
            lines, after = [random.choice(DIALOG_IDLE)], "heal"
        self.dialog = {"lines": lines, "i": 0, "chars": 0.0, "after": after, "blip": 0}

    def finish_talk(self):
        after = self.dialog["after"]
        self.dialog = None
        room, p = self.room, self.player
        if after is None:
            return
        room.talked = True
        if after == "memory":
            key = self.memory_gift
            p = self.player
            p.apply_boon(key if p.boons.get(key, 0) < BOONS[key]["max"] else "sifa")
            self.log.append(f"ani {key}")
            self.sfx.play("item")
            self.fx.burst(p.x, p.y - 8, 30, [(190, 200, 255), (255, 255, 255), (255, 230, 150)], speed=50,
                          life=1.2, grav=-40)
            self.oyku = None  # yankı dağılır
            room.door_open = True
            self.sfx.play("door", 0.6)
            return
        if after == "rescue":
            self.rescued = True
            self.quest = 0
            self.log.append("oyku kurtarildi")
        elif after == "deliver":
            p.max_hp += 1
            self.delivered += 1
            self.quest = self.carrying + 1
            self.log.append(f"teslim {ITEMS[self.carrying]['name']}")
            self.carrying = None
        p.hp = p.max_hp
        self.sfx.play("heal")
        self.fx.burst(p.x, p.y - 8, 30, [(255, 150, 190), (255, 255, 255), (255, 220, 120)], speed=50, life=1.2,
                      grav=-40)
        if self.quest is not None and self.quest >= len(ITEMS) and not self.endless:
            self.state, self.state_t = "ending", 0.0
            self.save["wins"] += 1
            write_save(self.save)
            self.log.append("SON")
            return
        room.door_open = True
        self.sfx.play("door", 0.6)
        if self.quest is not None and self.quest < len(ITEMS):
            self.title = ("YENİ İSTEK", ITEMS[self.quest]["name"], (255, 150, 190))
            self.title_t = 2.4

    def update_dialog(self, dt, attack_pressed, nav=0):
        d = self.dialog
        if d.get("pick") is not None:  # soru ekranı
            if nav:
                d["pick"] = (d["pick"] + nav) % len(d["choices"])
                self.sfx.play("select")
            if attack_pressed:
                _, self.memory_gift, reply = d["choices"][d["pick"]]
                d.update(lines=[reply], i=0, chars=0.0, choices=None, pick=None, after="memory")
            return
        line = d["lines"][d["i"]]
        before = int(d["chars"])
        d["chars"] = min(len(line), d["chars"] + dt * 40)
        if int(d["chars"]) != before and int(d["chars"]) % 3 == 0 and line[int(d["chars"]) - 1] != " ":
            self.sfx.play("talk", 0.5)
        if attack_pressed:
            if d["chars"] < len(line):
                d["chars"] = len(line)
            elif d["i"] + 1 < len(d["lines"]):
                d["i"] += 1
                d["chars"] = 0.0
            elif d.get("choices"):
                d["pick"] = 0
            else:
                self.finish_talk()

    # --- ana güncelleme --------------------------------------------------------------
    def update(self, dt, keys, dash_pressed, attack_pressed, nav, skill=None):
        if self.slowmo > 0:  # kusursuz atılma: zaman ağırlaşır
            self.slowmo -= dt
            dt *= 0.35
        if self.combo_t > 0:
            self.combo_t -= dt
            if self.combo_t <= 0:
                self.combo = 0
        self.shake = max(0.0, self.shake - dt * 20)
        self.update_shards(dt)
        self.flash = max(0.0, self.flash - dt)
        self.fx.update(dt)
        for n in self.numbers:
            n[1] -= dt * 18
            n[2] -= dt
        self.numbers = [n for n in self.numbers if n[2] > 0]
        for e in self.effects:
            e["t"] -= dt
        self.effects = [e for e in self.effects if e["t"] > 0]
        self.state_t += dt
        self.title_t = max(0.0, self.title_t - dt)
        room, p = self.room, self.player

        if self.state == "fps":
            self.fps.update(dt, keys, attack_pressed, dash_pressed)
            return
        if self.state == "scare":
            self.update_scare()
            return
        if self.state == "in":
            if self.state_t >= IRIS_TIME:
                self.state, self.state_t = "play", 0.0
            return
        if self.state == "out":
            if self.state_t >= IRIS_TIME:
                self.next_room()
            return
        if self.state == "ending":
            if attack_pressed and self.state_t > 3.0:
                self.endless = True
                self.state, self.state_t = "play", 0.0
                room.door_open = True
                self.sfx.play("door", 0.6)
                self.title = ("SONSUZ MAHZEN", "bekçiler hep geri döner", (220, 130, 90))
                self.title_t = 2.4
            return
        if self.state == "reward":
            if nav:
                self.choice_i = (self.choice_i + nav) % len(self.choices)
                self.sfx.play("select")
            if attack_pressed and self.state_t > 0.3:
                key = self.choices[self.choice_i]
                p.apply_boon(key)
                self.log.append(f"armagan {key}")
                self.sfx.play("pick")
                self.fx.burst(p.x, p.y - 8, 24, [(255, 200, 90), (235, 110, 50), (255, 245, 210)],
                              speed=60, life=0.9, grav=-40)
                if self.extra_rewards > 0:  # akit: bir armağan daha
                    self.extra_rewards -= 1
                    self.offer_rewards()
                    return
                self.state, self.state_t = "play", 0.0
                room.door_open = True
                self.sfx.play("door", 0.8)
                self.shake = 3
            return
        if self.state == "market":
            self.update_market(nav, attack_pressed, dash_pressed)
            return
        if self.state == "pact":
            self.update_pact(nav, attack_pressed, dash_pressed)
            return
        if self.state == "dead":
            for e in self.enemies:
                e.update(dt, p, self)
            return
        if self.dialog:
            self.update_dialog(dt, attack_pressed, nav)
            return

        if self.hitstop > 0:          # vuruşta kısa donma — darbe hissi
            self.hitstop -= dt
            return
        if self.boss_dying:
            self.update_boss_death(dt)
            p.update(dt, keys, False, False, self.sfx)
            return

        # sığınakta Öykü ile konuş (kılıç savurmadan)
        if self.oyku and attack_pressed and math.hypot(p.x - self.oyku.x, p.y - self.oyku.y) < 28:
            self.start_talk()
            return
        if self.npc and attack_pressed and math.hypot(p.x - self.npc.x, p.y - self.npc.y) < 28:
            self.open_market()
            return
        chest = room.chest
        if chest and not chest["open"] and attack_pressed and math.hypot(p.x - chest["x"], p.y - chest["y"]) < 24:
            self.open_chest()
            return
        sh = room.shrine
        if sh and not sh["used"] and attack_pressed and math.hypot(p.x - sh["x"], p.y - sh["y"]) < 30:
            self.open_pact()
            return
        if room.tansi and not room.greeted and self.state_t > 0.4:
            room.greeted = True
            self.title_t = 0.0
            self.say("Tansi", ["Hey, buraya kadar inebilen olmamıştı!", "Ben Tansi. Canavarların külünü ben alırım.",
                               "Bu da köpeğim. Kokunu aldı, seni sevdi bile.",
                               "Sen de karşılığında işe yarar bir şeyler alırsın. Yanıma gel."])
            return
        # yolda duyulan sesler
        if not room.talked and self.state_t > 0.4 and not self.endless:
            voice = None
            if room.kind == "rest" and room.floor == 1 and not self.rescued:
                voice = VOICE_REST
            elif room.kind == "boss" and self.rescued and not self.boss_spawned:
                voice = VOICE_BOSS.get(room.floor)
            if voice:
                room.talked = True
                self.say(*voice)
                return

        calm = room.kind in ("haven", "ani")
        p.update(dt, keys, dash_pressed, attack_pressed and not calm, self.sfx)
        if skill is not None and not calm:
            self.use_skill(skill)
        self.process_player_events()
        # zamanlanmış yetenek adımları
        due = [s for s in self.sched if s[0] - dt <= 0]
        for s in self.sched:
            s[0] -= dt
        self.sched = [s for s in self.sched if s[0] > 0]
        for s in due:
            s[1]()
        if room.kind == "boss" and not self.boss_spawned and self.state_t > 0.5:
            self.spawn_boss()
        goal = 0.0 if room.cleared else room.dark
        if self.darkness > goal and not any(isinstance(e, ShadeBoss) for e in self.enemies):
            self.darkness = max(goal, self.darkness - dt * 0.4)
        if room.spikes and not room.cleared:
            self.spike_t += dt
            grp = room.spikes.get((int(p.x) // TILE, int(p.y - 3) // TILE))
            if grp is not None and self.spike_state(grp) == 2 and not p.z:
                self.player_hit(p.x, p.y + 6)
        for e in self.enemies:
            if e.burn > 0:
                e.burn -= dt
                e.burn_tick -= dt
                if e.burn_tick <= 0:
                    e.burn_tick = 0.7
                    self.damage_enemy(e, 1, (0.0, 0.0), knock=0, pure=True)
            if e.stun > 0 and not isinstance(e, Boss):
                e.stun -= dt
                e.flash = max(0.0, e.flash - dt)
                e.physics(0, 0, dt)
                continue
            e.slow = max(0.0, e.slow - dt)
            e.update(dt * 0.55 if e.slow > 0 else dt, p, self)
        # oyuncu mermileri
        for sh in self.pshots:
            sh.update(dt)
            if sh.dead:
                continue
            r = sh.rect()
            for e in list(self.enemies):
                if e.active() and id(e) not in sh.hits and r.colliderect(e.body_rect()):
                    sh.hits.add(id(e))
                    self.damage_enemy(e, sh.dmg, norm(sh.vx, sh.vy), knock=110 if sh.kind == "arrow" else 200)
                    sh.pierce -= 1
                    if sh.pierce <= 0:
                        sh.dead = True
                        break
            if sh.kind != "arrow":  # güçlü oklar ve hayalet kılıçlar kor toplarını da keser
                for b in self.bolts:
                    if r.colliderect(b.rect()):
                        b.dead = True
            if sh.dead:
                self.fx.burst(sh.x, sh.y, 5, [(200, 190, 210), (255, 200, 120)], speed=40, life=0.2)
        for sh in self.pshots:
            if sh.dead and sh.kind == "orb":  # kor küresi patlar
                self.area_damage(sh.x, sh.y + 8, 22, sh.dmg, knock=150)
                self.fx.burst(sh.x, sh.y, 16, [(255, 220, 120), (235, 110, 50), (150, 40, 30)], speed=70, life=0.4)
                self.fx.ring(sh.x, sh.y, 18, (255, 160, 60), 80, 0.25)
                self.sfx.play("boom", 0.3)
        self.pshots = [sh for sh in self.pshots if not sh.dead]
        if self.spawn_queue:
            for e in self.spawn_queue:
                self.enemies.append(e)
                self.fx.burst(e.x, e.y - 2, 8, [(70, 64, 76), (110, 100, 110)], speed=25, life=0.7)
            self.spawn_queue = []

        # birbirlerinin içine girmesinler (bekçi hariç)
        small = [e for e in self.enemies if not isinstance(e, Boss)]
        for i, a in enumerate(small):
            for b in small[i + 1:]:
                dx, dy = b.x - a.x, b.y - a.y
                d = math.hypot(dx, dy)
                if 0 < d < 11:
                    push = (11 - d) * 0.5
                    ux, uy = dx / d, dy / d
                    a.move(-ux * push, -uy * push, 1)
                    b.move(ux * push, uy * push, 1)

        # yakın dövüş: düşmanlar ve kor topları
        if p.melee_active():
            sr = p.slash_rect()
            for e in list(self.enemies):
                if e.active() and id(e) not in p.hit_set and sr.colliderect(e.body_rect()):
                    p.hit_set.add(id(e))
                    heavy = p.weapon == "yumruk" and p.combo == 0
                    self.damage_enemy(e, p.dmg + (1 if heavy else 0), p.attack_aim, knock=300 if heavy else 190)
            for b in self.bolts:
                if sr.colliderect(b.rect()):
                    b.dead = True
                    self.sfx.play("fizzle")
                    self.fx.burst(b.x, b.y, 10, [(255, 230, 150), (235, 110, 50)], speed=70, life=0.3)
        # gölge adım: atılırken değdiğini keser
        if p.dash_t > 0 and (p.dash_dmg or p.skill_dash_dmg):
            br = p.body_rect().inflate(10, 10)
            for e in list(self.enemies):
                if e.active() and id(e) not in p.dash_hits and br.colliderect(e.body_rect()):
                    p.dash_hits.add(id(e))
                    self.damage_enemy(e, p.skill_dash_dmg or p.dash_dmg * 2, p.dash_dir)

        # hortlak atılması oyuncuya değerse
        for e in self.enemies:
            if isinstance(e, Ghoul) and e.state == "lunge" and e.body_rect().colliderect(p.body_rect()):
                self.player_hit(e.x, e.y)
                if p.invuln == INVULN_TIME:
                    e.state, e.timer = "recover", 0.6
            elif e.touching() and e.body_rect().colliderect(p.body_rect()):
                self.player_hit(e.x, e.y)
                if p.invuln == INVULN_TIME:
                    e.on_touch()
        # kor topları
        for b in self.bolts:
            b.update(dt)
            if b.dead:
                self.fx.burst(b.x, b.y, 6, [(235, 110, 50), (150, 40, 30)], speed=40, life=0.3)
            elif b.rect().colliderect(p.body_rect()) and p.dash_t > 0:
                p.hurt(b.x, b.y)  # atılırken geçilen top: kusursuz atılma
            elif b.rect().colliderect(p.body_rect()) and p.invuln == 0:
                b.dead = True
                self.player_hit(b.x - b.vx, b.y - b.vy)
        self.bolts = [b for b in self.bolts if not b.dead]
        # yer tehlikeleri
        for h in self.hazards:
            h.t -= dt
            if h.t <= 0:
                self.explode(h)
        self.hazards = [h for h in self.hazards if h.t > 0]
        self.enemies = [e for e in self.enemies if not e.dead]
        if self.state == "dead":
            return

        # dalgalar ve oda temizliği
        if room.kind == "kusatma" and not room.cleared and self.state_t > 1.0:
            self.update_siege(dt)
        fight = room.kind == "combat" or room.pact_fight or (room.chest and room.chest["open"])
        if fight and not room.cleared and all(e.passive for e in self.enemies):
            self.wave_t -= dt
            if self.wave_t <= 0:
                if room.waves_left > 0:
                    self.spawn_wave()
                    self.wave_t = 1.2
                else:
                    room.cleared = True
                    self.reward_t = 0.9
                    self.bolts = []
        if room.cleared and not room.door_open and room.kind not in ("haven", "ani"):
            self.reward_t -= dt
            if self.reward_t <= 0:
                if self.try_scare():
                    return
                self.offer_rewards()

        # bekçinin düşürdüğü eşya
        if room.item and math.hypot(p.x - room.item[0], p.y - room.item[1]) < 12:
            self.pick_item()

        # dinlenme sunağı
        if room.altar and not room.altar_used and attack_pressed:
            ax, ay = room.altar[0] * TILE + 16, room.altar[1] * TILE + 10
            if math.hypot(p.x - ax, p.y - ay) < 30:
                room.altar_used = True
                heal = min(3, p.max_hp - p.hp)
                p.hp += heal
                self.log.append(f"sunak +{heal}")
                self.sfx.play("heal")
                self.fx.burst(ax, ay - 6, 40, [(255, 200, 90), (235, 110, 50), (255, 245, 210)],
                              speed=70, life=1.0, grav=-50)
                self.fx.burst(p.x, p.y - 8, 16, [(220, 50, 60), (255, 120, 120)], speed=30, life=0.8, grav=-50)

        # kapı
        if room.door_open:
            room.door_anim = min(1.0, room.door_anim + dt * 2)
            if p.y < 14 and int(p.x) // TILE == room.door_col:
                self.state, self.state_t = "out", 0.0

    def iris_radius(self):
        maxr = 360
        if self.state == "in":
            return int(maxr * min(1.0, self.state_t / IRIS_TIME) ** 2)
        if self.state == "out":
            return int(maxr * (1 - min(1.0, self.state_t / IRIS_TIME)) ** 2)
        return None


# --- Korku anı ---------------------------------------------------------------------
SCARE_CHANCE = 0.35
SCARE_TIME = 1.7
SCARE_FACES = []


def build_scare_faces():
    """İki kareli, elle üretilmiş yüz: boş göz çukurları ve yırtık ağız."""
    for mouth in (30, 44):
        rng = random.Random(13)
        w, h = W // 2, H // 2
        f = pygame.Surface((w, h))
        f.fill((255, 255, 255))
        cx, cy = w // 2, h // 2 + 2
        pygame.draw.ellipse(f, (214, 208, 200), (cx - 44, cy - 50, 88, 104))
        for _ in range(900):  # kirli deri
            a, r = rng.uniform(0, math.tau), rng.uniform(0, 1) ** 0.5
            f.set_at((int(cx + math.cos(a) * 42 * r) % w, int(cy + math.sin(a) * 50 * r) % h),
                     rng.choice([(150, 140, 136), (120, 104, 104), (236, 230, 224)]))
        for sx in (-1, 1):  # göz çukurları
            ex = cx + sx * 19
            pygame.draw.ellipse(f, (8, 4, 6), (ex - 13, cy - 30, 26, 24))
            pygame.draw.polygon(f, (8, 4, 6), [(ex - sx * 12, cy - 24), (ex + sx * 12, cy - 34), (ex + sx * 8, cy - 18)])
            pygame.draw.circle(f, (255, 30, 30), (ex + sx, cy - 17), 2)
            f.set_at((ex + sx, cy - 17), (255, 255, 255))
            for i in range(4):  # kanlı gözyaşı
                pygame.draw.line(f, (120, 10, 16), (ex - 6 + i * 4, cy - 8), (ex - 6 + i * 4, cy + rng.randrange(0, 18)))
        pygame.draw.polygon(f, (20, 12, 14), [(cx - 3, cy - 6), (cx + 3, cy - 6), (cx, cy + 4)])
        top = cy + 8
        pygame.draw.ellipse(f, (6, 2, 4), (cx - 26, top, 52, mouth))
        for i in range(-24, 25, 6):  # dişler
            pygame.draw.polygon(f, (236, 226, 200), [(cx + i - 3, top + 3), (cx + i + 3, top + 3), (cx + i, top + 12)])
            pygame.draw.polygon(f, (236, 226, 200), [(cx + i - 3, top + mouth - 3), (cx + i + 3, top + mouth - 3),
                                                     (cx + i, top + mouth - 11)])
        for _ in range(9):  # çatlaklar
            x, y = cx + rng.randint(-40, 40), cy + rng.randint(-48, 20)
            for _ in range(8):
                nx, ny = x + rng.randint(-5, 5), y + rng.randint(1, 6)
                pygame.draw.line(f, (40, 26, 30), (x, y), (nx, ny))
                x, y = nx, ny
        SCARE_FACES.append(pygame.transform.scale(f, (W, H)))


def draw_scare(canvas, game):
    """Önce bembeyaz ekran, sonra yüz. Yanıp sönmez: tek beyaz, tek yüz, kararma."""
    t = game.state_t
    if not SCARE_FACES:
        build_scare_faces()
    if t < 0.2:
        canvas.fill((255, 255, 255))
        return
    k = min(1.0, (t - 0.2) / 1.1)
    img = SCARE_FACES[0 if t < 0.34 else 1]
    zw, zh = int(W * (1.0 + 0.45 * k)), int(H * (1.0 + 0.45 * k))
    big_img = pygame.transform.scale(img, (zw, zh))
    canvas.fill((255, 255, 255))
    canvas.blit(big_img, ((W - zw) // 2 + random.randint(-4, 4), (H - zh) // 2 + random.randint(-4, 4)))
    if t > 1.3:
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((0, 0, 0, min(255, int((t - 1.3) / 0.4 * 255))))
        canvas.blit(veil, (0, 0))


# --- Kelebek boyutu: birinci şahıs nişancı modu --------------------------------------
FPS_TIME = 30.0
BUTTERFLY_CHANCE = 0.5   # test için yüksek; oyun bitince 0.1'e dönecek
FPS_TIERS = [(8, "kanat_tozu"), (20, "boyut_kalbi"), (35, "kelebek_isini"), (55, "boyut_ruhu")]
FPS_GUNS = [
    {"name": "IŞIN", "cd": 0.17, "pellets": 1, "spread": 0.0, "col": (120, 230, 240)},
    {"name": "SAÇMA", "cd": 0.6, "pellets": 6, "spread": 0.09, "col": (255, 190, 90)},
    {"name": "ROKET", "cd": 0.95, "pellets": 0, "spread": 0.0, "col": (255, 90, 90)},
]
FPS_N = 25          # harita kenarı
FPS_TEX_H = 32
FPS_ASSETS = {}
FPS_WALLS = {"#": ((76, 44, 130), (140, 90, 220)), "A": ((24, 110, 120), (120, 240, 230)),
             "B": ((130, 40, 90), (240, 110, 170)), "C": ((130, 96, 30), (250, 210, 100)),
             "P": ((60, 66, 96), (210, 225, 255))}
FPS_PICK_ROWS = {
    "time": ["...cc...", "..cwwc..", ".cwccwc.", "cwccccwc", "cwccccwc", ".cwccwc.", "..cwwc..", "...cc..."],
    "sacma": ["oooooooo", "oyyyyyyo", "oyrryrro", "oyrryrro", "oyrryrro", "oyyyyyyo", "oooooooo", "kkkkkkkk"],
    "roket": ["..rrrr..", ".rwwwwr.", ".rrrrrr.", ".rrrrrr.", ".rrrrrr.", ".oyyyyo.", "oo.yy.oo", "o..yy..o"],
    "cift": ["pppppppp", "p.wwww.p", "p....w.p", "p.wwww.p", "p.w....p", "p.wwww.p", "p......p", "pppppppp"],
}
FPS_PICK_PAL = {"c": (90, 230, 255), "w": (255, 255, 255), "o": (150, 100, 50), "y": (255, 210, 90), "r": (220, 60, 60),
                "k": (20, 16, 26), "p": (230, 120, 255)}


def fps_assets():
    """Duvar dokuları ve yaratıklar bir kez üretilir."""
    if FPS_ASSETS:
        return FPS_ASSETS
    rng = random.Random(5)
    tex = {}
    for ch, (base, line) in FPS_WALLS.items():
        levels = []
        for lv in range(10):  # 5 uzaklık x 2 yüzey yönü: uzak duvar sisin içinde kaybolur
            k = (1.0 - (lv // 2) * 0.19) * (0.72 if lv % 2 else 1.0)
            cols = []
            for tx in range(16):
                col = pygame.Surface((1, FPS_TEX_H))
                for ty in range(FPS_TEX_H):
                    c = base
                    if ty % 8 == 0 or (tx + (ty // 8) % 2 * 8) % 16 == 0:
                        c = line
                    elif (tx * 7 + ty * 13) % 11 == 0:
                        c = tuple(min(255, v + 18) for v in base)
                    col.set_at((0, ty), tuple(int(v * k) for v in c))
                cols.append(col)
            levels.append(cols)
        tex[ch] = levels
    sky = pygame.Surface((W, H))
    for y in range(H // 2):  # bantlı gök ve zemin: 8-bit gradyan
        k = (y // 6 * 6) / (H / 2)
        pygame.draw.line(sky, (int(20 + 60 * k), int(8 + 14 * k), int(50 + 70 * k)), (0, y), (W, y))
    for y in range(H // 2, H):
        k = ((y - H // 2) // 5 * 5) / (H / 2)
        pygame.draw.line(sky, (int(14 + 34 * k), int(30 + 60 * k), int(44 + 66 * k)), (0, y), (W, y))
    for _ in range(50):
        sky.set_at((rng.randrange(W), rng.randrange(H // 2 - 8)), rng.choice([(255, 255, 255), (170, 240, 255)]))

    def tint(img, c):
        img = img.copy()
        img.fill(c, special_flags=pygame.BLEND_RGBA_MULT)
        return img
    ghoul = [tint(f, (130, 255, 235, 255)) for f in build_frames(GHOUL_BODY, GHOUL_LEGS)]
    wisp = [tint(sprite_from_rows(f, FIRE_PAL), (210, 150, 255, 255)) for f in WISP_FRAMES]
    bloat = [tint(sprite_from_rows(BLOAT_ROWS, MOB_PAL), (255, 170, 230, 255))]
    crawl = [tint(sprite_from_rows(f, MOB_PAL), (255, 230, 120, 255)) for f in CRAWLER_FRAMES]
    orb = pygame.Surface((9, 9), pygame.SRCALPHA)
    pygame.draw.circle(orb, (255, 80, 200), (4, 4), 4)
    pygame.draw.circle(orb, (255, 240, 255), (4, 4), 2)
    rocket = pygame.Surface((9, 9), pygame.SRCALPHA)
    pygame.draw.circle(rocket, (255, 140, 60), (4, 4), 4)
    pygame.draw.circle(rocket, (255, 250, 200), (4, 4), 2)
    portal = []
    for i in range(2):
        p = pygame.Surface((16, 24), pygame.SRCALPHA)
        pygame.draw.ellipse(p, (120, 240, 255), (1, 1, 14, 22), 2)
        pygame.draw.ellipse(p, (240, 140, 255), (3 + i, 4, 10 - i * 2, 16), 1)
        portal.append(p)
    FPS_ASSETS.update(tex=tex, sky=sky, orb=orb, rocket=rocket, portal=portal,
                      picks={k: sprite_from_rows(v, FPS_PICK_PAL) for k, v in FPS_PICK_ROWS.items()}, mobs={
        "g": {"imgs": ghoul, "hp": 1, "speed": 1.3, "size": 0.8, "lift": 0.0, "value": 1},
        "w": {"imgs": wisp, "hp": 1, "speed": 1.5, "size": 0.55, "lift": 0.28, "value": 1},
        "b": {"imgs": bloat, "hp": 4, "speed": 0.9, "size": 1.0, "lift": 0.0, "value": 3},
        "c": {"imgs": crawl, "hp": 1, "speed": 1.5, "size": 0.42, "lift": 0.0, "value": 2},
    })
    return FPS_ASSETS


def fps_generate(rng):
    """3x3 odalı rastgele kat: oda, koridor, sütun ve bölge renkleri."""
    g = [["#"] * FPS_N for _ in range(FPS_N)]
    rooms = []
    for cy in range(3):
        for cx in range(3):
            w, h = rng.randint(5, 7), rng.randint(5, 7)
            x, y = 1 + cx * 8 + rng.randint(0, 7 - w), 1 + cy * 8 + rng.randint(0, 7 - h)
            rooms.append((x, y, w, h))
            for yy in range(y, y + h):
                for xx in range(x, x + w):
                    g[yy][xx] = "."

    def center(i):
        x, y, w, h = rooms[i]
        return x + w // 2, y + h // 2

    def carve(a, b):
        (x0, y0), (x1, y1) = center(a), center(b)
        for x in range(min(x0, x1), max(x0, x1) + 1):
            g[y0][x] = g[y0 + 1][x] = "."
        for y in range(min(y0, y1), max(y0, y1) + 2):
            g[y][x1] = g[y][x1 + 1] = "."
    seen, edges = {4}, []
    while len(seen) < 9:  # ortadan başlayan rastgele ağaç: her oda ulaşılır
        a = rng.choice(sorted(seen))
        nb = [a + d for d, ok in ((1, a % 3 < 2), (-1, a % 3 > 0), (3, a < 6), (-3, a > 2)) if ok]
        b = rng.choice(nb)
        if b not in seen:
            seen.add(b)
            edges.append((a, b))
    for a, b in edges:
        carve(a, b)
    for _ in range(3):  # döngüler: kaçacak yol kalsın
        a = rng.randrange(9)
        nb = [a + d for d, ok in ((1, a % 3 < 2), (3, a < 6)) if ok]
        if nb:
            carve(a, rng.choice(nb))
    for x, y, w, h in rooms:  # her odanın duvar rengi ayrı
        theme = rng.choice("#ABC")
        for yy in range(max(0, y - 1), min(FPS_N, y + h + 1)):
            for xx in range(max(0, x - 1), min(FPS_N, x + w + 1)):
                if g[yy][xx] != ".":
                    g[yy][xx] = theme
        if w >= 6 and h >= 6:  # büyük odada siper sütunları
            for px, py in ((x + 1, y + 1), (x + w - 2, y + 1), (x + 1, y + h - 2), (x + w - 2, y + h - 2)):
                g[py][px] = "P"
    return ["".join(r) for r in g], [center(i) for i in range(9)]


class FpsMode:
    """Kelebek boyutu: süre dolana kadar vurduğun her canavar ödülü büyütür. Burada can gitmez, süre gider."""

    def __init__(self, game):
        self.game = game
        self.a = fps_assets()
        self.map, self.centers = fps_generate(random.Random())
        self.phase, self.t = "in", 0.0
        self.left = FPS_TIME
        self.kills = 0
        cx, cy = self.centers[4]
        self.px, self.py, self.ang = cx + 0.5, cy + 0.5, 0.0
        self.mobs, self.bolts, self.rockets, self.booms = [], [], [], []
        self.spawn = 0.4
        self.fire_cd = 0.0
        self.recoil = 0.0
        self.muzzle = 0.0
        self.hurt = 0.0
        self.bob = 0.0
        self.travel = 0.0
        self.dash_cd = 0.0
        self.gun = 0
        self.ammo = [999, 12, 3]
        self.chain, self.chain_t = 0, 0.0      # art arda vuruş çarpanı
        self.double = 0.0
        self.tp_cd = 0.0
        self.zbuf = [99.0] * (W // 2)
        self.snapshot = None
        self.earned = []
        self.pop = 0.0
        self.flow, self.flow_t = {}, 0.0
        self.seen = set()
        self.minimap = pygame.Surface((FPS_N * 2, FPS_N * 2), pygame.SRCALPHA)
        rooms = list(self.centers)
        random.shuffle(rooms)
        self.portals = [(rooms[0], rooms[1]), (rooms[2], rooms[3])]  # iki eş kapı
        self.picks = []
        self.pick_t = 5.0
        for _ in range(7):
            self.add_pick()

    def wall(self, x, y):
        return self.map[int(y)][int(x)] != "."

    def add_pick(self):
        cx, cy = random.choice(self.centers)
        spots = [(x, y) for y in range(cy - 2, cy + 3) for x in range(cx - 2, cx + 3)
                 if 0 < x < FPS_N - 1 and 0 < y < FPS_N - 1 and self.map[y][x] == "."]
        if spots and len(self.picks) < 9:
            x, y = random.choice(spots)
            kind = random.choices(("time", "sacma", "roket", "cift"), (4, 4, 3, 2))[0]
            self.picks.append({"x": x + 0.5, "y": y + 0.5, "kind": kind})

    def goal(self):
        for need, _ in FPS_TIERS:
            if self.kills < need:
                return need
        return None

    def walk(self, ex, ey, dx, dy, r=0.24):
        nx = ex + dx
        if not self.wall(nx + (r if dx > 0 else -r), ey):
            ex = nx
        ny = ey + dy
        if not self.wall(ex, ny + (r if dy > 0 else -r)):
            ey = ny
        return ex, ey

    def cast(self, ang, x=None, y=None):
        """Düz ışın: duvara uzaklık."""
        x = self.px if x is None else x
        y = self.py if y is None else y
        dx, dy = math.cos(ang), math.sin(ang)
        d = 0.0
        while d < 30:
            d += 0.08
            if self.wall(x + dx * d, y + dy * d):
                return d
        return d

    def sees(self, m):
        ang = math.atan2(self.py - m["y"], self.px - m["x"])
        return self.cast(ang, m["x"], m["y"]) >= math.hypot(self.px - m["x"], self.py - m["y"])

    def update_flow(self):
        """Oyuncudan yayılan mesafe haritası: yaratıklar köşe dönebilsin."""
        start = (int(self.px), int(self.py))
        dist = {start: 0}
        q = deque([start])
        while q:
            x, y = q.popleft()
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if (nx, ny) not in dist and self.map[ny][nx] == ".":
                    dist[(nx, ny)] = dist[(x, y)] + 1
                    q.append((nx, ny))
        self.flow = dist

    def spawn_mob(self):
        cells = [c for c, d in self.flow.items() if 6 <= d <= 14]
        if not cells:
            return
        x, y = random.choice(cells)
        kind = random.choices("gwbc", (6, 3, 1 + self.kills // 12, 3))[0]
        self.mobs.append({"x": x + 0.5, "y": y + 0.5, "kind": kind, "hp": self.a["mobs"][kind]["hp"], "flash": 0.0,
                          "anim": random.random() * 4, "rise": 0.0, "cd": random.uniform(1.0, 2.4), "rush": 0.0})

    def score(self, m):
        val = self.a["mobs"][m["kind"]]["value"]
        self.chain += 1
        self.chain_t = 2.4
        before = self.goal()
        self.kills += val * self.mult() * (2 if self.double > 0 else 1)
        self.pop = 0.35
        self.game.sfx.play("kill", 0.7)
        if before is not None and self.kills >= before:
            self.game.sfx.play("item", 0.8)  # yeni ödül eşiği aşıldı

    def mult(self):
        return 1 + min(2, self.chain // 5)

    def hit_mob(self, m, dmg=1):
        if m not in self.mobs:
            return
        m["hp"] -= dmg
        m["flash"] = 0.1
        if m["hp"] <= 0:
            self.mobs.remove(m)
            self.score(m)
        else:
            self.game.sfx.play("hit", 0.5)

    def shoot_ray(self, ang):
        wall = self.cast(ang)
        best, bd = None, wall
        for m in self.mobs:
            dx, dy = m["x"] - self.px, m["y"] - self.py
            d = math.hypot(dx, dy)
            diff = abs((math.atan2(dy, dx) - ang + math.pi) % math.tau - math.pi)
            if d < bd and diff < math.atan(0.4 / max(d, 0.3)) + 0.02:
                best, bd = m, d
        if best:
            self.hit_mob(best)

    def fire(self):
        sfx = self.game.sfx
        gun = FPS_GUNS[self.gun]
        if self.gun and self.ammo[self.gun] <= 0:
            self.gun = 0
            gun = FPS_GUNS[0]
        self.fire_cd, self.recoil, self.muzzle = gun["cd"], 1.0, 0.06
        if self.gun:
            self.ammo[self.gun] -= 1
        if self.gun == 2:
            self.rockets.append({"x": self.px, "y": self.py, "a": self.ang})
            sfx.play("charge", 0.5)
            return
        sfx.play("slam" if self.gun == 1 else "shoot", 0.5)
        for i in range(gun["pellets"]):
            off = (i - (gun["pellets"] - 1) / 2) * gun["spread"]
            self.shoot_ray(self.ang + off)

    def lose_time(self, secs):
        self.left = max(0.0, self.left - secs)
        self.hurt = 0.3
        self.chain = 0
        self.game.sfx.play("hurt", 0.6)

    def update(self, dt, keys, attack_pressed, dash_pressed):
        K = pygame
        self.t += dt
        self.hurt = max(0.0, self.hurt - dt)
        self.muzzle = max(0.0, self.muzzle - dt)
        self.recoil = max(0.0, self.recoil - dt * 6)
        self.pop = max(0.0, self.pop - dt)
        if self.phase == "in":
            if self.t >= 1.3:
                self.phase, self.t = "play", 0.0
                self.update_flow()
            return
        if self.phase == "out":
            if self.t >= 1.6:
                self.finish()
            return
        if self.phase == "result":
            if attack_pressed and self.t > 0.8:
                self.game.end_fps()
            return
        self.left -= dt
        if self.left <= 0:
            self.left = 0.0
            self.phase, self.t = "out", 0.0
            self.game.sfx.play("charge")
            return
        for i, key in enumerate((K.K_1, K.K_2, K.K_3)):
            if keys[key] and (i == 0 or self.ammo[i] > 0):
                self.gun = i
        self.ang += ((keys[K.K_RIGHT] or keys[K.K_e]) - (keys[K.K_LEFT] or keys[K.K_q])) * 2.7 * dt
        fwd = (keys[K.K_w] or keys[K.K_UP]) - (keys[K.K_s] or keys[K.K_DOWN])
        side = keys[K.K_d] - keys[K.K_a]
        ca, sa = math.cos(self.ang), math.sin(self.ang)
        self.dash_cd -= dt
        if dash_pressed and self.dash_cd <= 0:  # ileri fırlama
            self.dash_cd = 1.2
            self.game.sfx.play("dash", 0.6)
            for _ in range(10):
                self.px, self.py = self.walk(self.px, self.py, ca * 0.16, sa * 0.16)
        if fwd or side:
            sp = 3.2 * dt
            self.px, self.py = self.walk(self.px, self.py, (ca * fwd - sa * side) * sp, (sa * fwd + ca * side) * sp)
            self.bob += dt * 11
            self.travel += fwd * sp
        # keşif: haritada gördüğün yerler açılır
        cx, cy = int(self.px), int(self.py)
        for yy in range(max(0, cy - 3), min(FPS_N, cy + 4)):
            for xx in range(max(0, cx - 3), min(FPS_N, cx + 4)):
                if (xx, yy) not in self.seen:
                    self.seen.add((xx, yy))
                    c = (40, 30, 70, 230) if self.map[yy][xx] == "." else (170, 130, 230, 255)
                    pygame.draw.rect(self.minimap, c, (xx * 2, yy * 2, 2, 2))
        self.fire_cd -= dt
        if (keys[K.K_j] or keys[K.K_x]) and self.fire_cd <= 0:
            self.fire()
        self.double = max(0.0, self.double - dt)
        self.chain_t -= dt
        if self.chain_t <= 0:
            self.chain = 0
        # kapılar ve toplananlar
        self.tp_cd -= dt
        if self.tp_cd <= 0:
            for a, b in self.portals:
                for src, dst in ((a, b), (b, a)):
                    if math.hypot(self.px - src[0] - 0.5, self.py - src[1] - 0.5) < 0.6:
                        self.px, self.py = dst[0] + 0.5, dst[1] + 0.5
                        self.tp_cd, self.hurt = 1.4, 0.0
                        self.game.flash = 0.1
                        self.game.sfx.play("item", 0.6)
        for pk in self.picks[:]:
            if math.hypot(self.px - pk["x"], self.py - pk["y"]) < 0.6:
                self.picks.remove(pk)
                if pk["kind"] == "time":
                    self.left = min(FPS_TIME, self.left + 3)
                elif pk["kind"] == "sacma":
                    self.ammo[1] += 8
                elif pk["kind"] == "roket":
                    self.ammo[2] += 2
                else:
                    self.double = 6.0
                self.game.sfx.play("pick")
        self.pick_t -= dt
        if self.pick_t <= 0:
            self.pick_t = 3.5
            self.add_pick()
        # yaratıklar
        self.flow_t -= dt
        if self.flow_t <= 0:
            self.flow_t = 0.25
            self.update_flow()
        self.spawn -= dt
        if self.spawn <= 0 and len(self.mobs) < 12:
            self.spawn_mob()
            self.spawn = max(0.45, 1.25 - (FPS_TIME - self.left) * 0.03)
        for m in self.mobs:
            self.move_mob(m, dt)
        self.mobs = [m for m in self.mobs if not m.get("dead")]
        # mermiler
        for b in self.bolts:
            b["x"] += b["vx"] * dt
            b["y"] += b["vy"] * dt
            if self.wall(b["x"], b["y"]):
                b["dead"] = True
            elif math.hypot(self.px - b["x"], self.py - b["y"]) < 0.35:
                b["dead"] = True
                self.lose_time(2.0)
        self.bolts = [b for b in self.bolts if not b.get("dead")]
        for r in self.rockets:
            r["x"] += math.cos(r["a"]) * 9 * dt
            r["y"] += math.sin(r["a"]) * 9 * dt
            hit = self.wall(r["x"], r["y"]) or any(math.hypot(m["x"] - r["x"], m["y"] - r["y"]) < 0.5 for m in self.mobs)
            if hit:
                r["dead"] = True
                self.booms.append({"x": r["x"], "y": r["y"], "t": 0.35})
                self.game.sfx.play("boom", 0.6)
                for m in self.mobs[:]:
                    if math.hypot(m["x"] - r["x"], m["y"] - r["y"]) < 2.4:
                        self.hit_mob(m, 4)
        self.rockets = [r for r in self.rockets if not r.get("dead")]
        for b in self.booms:
            b["t"] -= dt
        self.booms = [b for b in self.booms if b["t"] > 0]

    def move_mob(self, m, dt):
        info = self.a["mobs"][m["kind"]]
        m["flash"] = max(0.0, m["flash"] - dt)
        m["anim"] += dt * 6
        m["rise"] = min(1.0, m["rise"] + dt * 2)
        m["cd"] -= dt
        dist = math.hypot(self.px - m["x"], self.py - m["y"])
        see = dist < 9 and self.sees(m)
        speed = info["speed"]
        if m["kind"] == "w":  # uzaktan ateş eder, yaklaşmaz
            if see and m["cd"] <= 0:
                m["cd"] = random.uniform(1.8, 2.8)
                ux, uy = norm(self.px - m["x"], self.py - m["y"])
                self.bolts.append({"x": m["x"], "y": m["y"], "vx": ux * 4.2, "vy": uy * 4.2})
                self.game.sfx.play("shoot", 0.4)
            if see and dist < 4.5:
                speed = 0
        if m["kind"] == "c":  # durur, sonra hızla atılır
            if m["rush"] > 0:
                m["rush"] -= dt
                speed = 5.0
            elif see and m["cd"] <= 0 and dist < 7:
                m["cd"], m["rush"] = 3.0, 0.8
                self.game.sfx.play("dash", 0.4)
        if see or dist < 1.2:
            ux, uy = norm(self.px - m["x"], self.py - m["y"])
        else:
            cx, cy = int(m["x"]), int(m["y"])
            best = min(((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)),
                       key=lambda c: self.flow.get(c, 999))
            ux, uy = norm(best[0] + 0.5 - m["x"], best[1] + 0.5 - m["y"])
        m["x"], m["y"] = self.walk(m["x"], m["y"], ux * speed * dt, uy * speed * dt, 0.2)
        if dist < 0.5:
            self.lose_time(2.0)  # temas zaman çalar
            m["dead"] = True

    def finish(self):
        g = self.game
        p = g.player
        g.add_kul(self.kills * 3)
        for need, key in FPS_TIERS:
            if self.kills >= need:
                got = key if p.boons.get(key, 0) < BOONS[key]["max"] else "boyut_kalbi"
                p.apply_boon(got)
                self.earned.append(got)
        write_save(g.save)
        self.phase, self.t = "result", 0.0
        g.sfx.play("item")

    # --- çizim
    def bill(self, out, img, wx, wy, size, lift, dx, dy, plx, ply, inv):
        """Dünyadaki bir görseli derinliğe göre, duvar arkasını keserek çizer."""
        ox, oy = wx - self.px, wy - self.py
        tx = inv * (dy * ox - dx * oy)
        ty = inv * (-ply * ox + plx * oy)
        if ty < 0.2:
            return
        sh = min(260, int(H / ty * size))
        if sh < 2:
            return
        sw = max(2, int(sh * img.get_width() / img.get_height()))
        big_img = pygame.transform.scale(img, (sw, sh))
        cx = int(W / 2 * (1 - tx / ty))
        top = int(H / 2 + H / (2 * ty) - sh - lift * H / ty)
        x0 = cx - sw // 2
        for c in range(0, sw, 2):
            sx_ = x0 + c
            if 0 <= sx_ < W and self.zbuf[sx_ // 2] > ty:
                out.blit(big_img, (sx_, top), (c, 0, 2, sh))

    def render(self, out, t):
        tex = self.a["tex"]
        out.blit(self.a["sky"], (0, 0))
        # yerdeki bantlar yürüdükçe akar: hız hissi
        for y in range(H // 2 + 3, H, 2):
            d = H / (2.0 * y - H)
            if int((d + self.travel) * 1.4) % 2:
                pygame.draw.line(out, (16, 40, 56), (0, y), (W, y))
        dx, dy = math.cos(self.ang), math.sin(self.ang)
        plx, ply = -dy * 0.66, dx * 0.66
        px, py = self.px, self.py
        scale = pygame.transform.scale
        grid = self.map
        for i in range(W // 2):
            cam = 4 * i / W - 1
            rx, ry = dx + plx * cam, dy + ply * cam
            mx, my = int(px), int(py)
            ddx = abs(1 / rx) if rx else 1e9
            ddy = abs(1 / ry) if ry else 1e9
            sx = 1 if rx > 0 else -1
            sy = 1 if ry > 0 else -1
            nx = (mx + 1 - px if rx > 0 else px - mx) * ddx
            ny = (my + 1 - py if ry > 0 else py - my) * ddy
            side = 0
            while True:
                if nx < ny:
                    nx += ddx
                    mx += sx
                    side = 0
                else:
                    ny += ddy
                    my += sy
                    side = 1
                ch = grid[my][mx]
                if ch != ".":
                    break
            perp = max(0.05, (nx - ddx) if side == 0 else (ny - ddy))
            self.zbuf[i] = perp
            wx = (py + perp * ry) if side == 0 else (px + perp * rx)
            col = tex[ch][min(4, int(perp / 2.5)) * 2 + side][int((wx - math.floor(wx)) * 16)]
            h = int(H / perp)
            if h <= H:
                out.blit(scale(col, (2, max(1, h))), (i * 2, (H - h) // 2))
            else:
                vis = max(1, int(FPS_TEX_H * H / h))
                out.blit(scale(col.subsurface((0, (FPS_TEX_H - vis) // 2, 1, vis)), (2, H)), (i * 2, 0))
        inv = 1.0 / (plx * dy - dx * ply)
        things = []
        for m in self.mobs:
            info = self.a["mobs"][m["kind"]]
            img = info["imgs"][int(m["anim"]) % len(info["imgs"])]
            things.append((m["x"], m["y"], white_of(img) if m["flash"] > 0 else img,
                           info["size"] * (0.3 + 0.7 * m["rise"]), info["lift"]))
        for pk in self.picks:
            things.append((pk["x"], pk["y"], self.a["picks"][pk["kind"]], 0.32, 0.08 + 0.03 * math.sin(t * 4 + pk["x"])))
        for a, b in self.portals:
            for c in (a, b):
                things.append((c[0] + 0.5, c[1] + 0.5, self.a["portal"][int(t * 5) % 2], 0.95, 0.0))
        for b in self.bolts:
            things.append((b["x"], b["y"], self.a["orb"], 0.22, 0.32))
        for r in self.rockets:
            things.append((r["x"], r["y"], self.a["rocket"], 0.2, 0.34))
        for b in self.booms:
            things.append((b["x"], b["y"], self.a["rocket"], 1.6 * (1 - b["t"] / 0.35) + 0.3, 0.0))
        things.sort(key=lambda o: -((o[0] - px) ** 2 + (o[1] - py) ** 2))
        for wx_, wy_, img, size, lift in things:
            self.bill(out, img, wx_, wy_, size, lift, dx, dy, plx, ply, inv)

    def draw_gun(self, out, t):
        cx = W // 2 + int(math.sin(self.bob) * 4)
        y = H - 34 + int(abs(math.cos(self.bob)) * 3) + int(self.recoil * (8 + self.gun * 5))
        col = FPS_GUNS[self.gun]["col"]
        if self.muzzle > 0:
            pygame.draw.circle(out, (255, 240, 255), (cx, y - 12), 9 + self.gun * 3)
            pygame.draw.circle(out, col, (cx, y - 12), 14 + self.gun * 3, 2)
        wide = 18 + self.gun * 6
        pygame.draw.polygon(out, (40, 34, 70), [(cx - wide, H), (cx - 8, y + 6), (cx + 8, y + 6), (cx + wide, H)])
        pygame.draw.polygon(out, (74, 62, 120), [(cx - wide + 6, H), (cx - 6, y + 6), (cx + 2, y + 6), (cx + 2, H)])
        pygame.draw.rect(out, col, (cx - 4 - self.gun, y - 4, 8 + self.gun * 2, 12))
        pygame.draw.rect(out, (230, 150, 255), (cx - 2, y - 8, 4, 6))
        if self.gun == 0:
            for sx in (-1, 1):  # kanat kanatçıkları
                pygame.draw.polygon(out, (210, 120, 255), [(cx + sx * 4, y + 6), (cx + sx * 20, y - 6), (cx + sx * 16, y + 12)])
        elif self.gun == 1:  # çift namlu
            pygame.draw.rect(out, (30, 26, 50), (cx - 7, y - 10, 5, 16))
            pygame.draw.rect(out, (30, 26, 50), (cx + 2, y - 10, 5, 16))
        else:  # roket borusu
            pygame.draw.rect(out, (70, 40, 44), (cx - 9, y - 14, 18, 22))
            pygame.draw.circle(out, (10, 8, 14), (cx, y - 12), 6)

    def draw_hud(self, out, font, big, t):
        k = 1 - self.left / FPS_TIME          # sayaç dolar
        pygame.draw.rect(out, (10, 6, 22), (5, 5, 104, 39))
        pygame.draw.rect(out, (200, 130, 255), (5, 5, 104, 39), 1)
        secs = int(math.ceil(self.left))
        text(out, font, f"SÜRE {secs}", 10, 6, (255, 110, 120) if secs <= 5 and int(t * 6) % 2 else (230, 220, 255))
        pygame.draw.rect(out, (40, 26, 70), (10, 18, 94, 5))
        pygame.draw.rect(out, (120, 230, 240), (10, 18, int(94 * k), 5))
        col = (255, 240, 170) if self.pop > 0 else (230, 180, 255)
        m = self.mult() * (2 if self.double > 0 else 1)
        text(out, font, f"VURUŞ {self.kills}" + (f"  x{m}" if m > 1 else ""), 10, 22, col)
        need = self.goal()
        text(out, font, f"ödül: {need}" if need else "en üst ödül!", 10, 31, (150, 220, 230))
        # küçük harita
        mx, my = W - FPS_N * 2 - 5, 5
        pygame.draw.rect(out, (10, 6, 22), (mx - 1, my - 1, FPS_N * 2 + 2, FPS_N * 2 + 2))
        out.blit(self.minimap, (mx, my))
        for mob in self.mobs:
            if (int(mob["x"]), int(mob["y"])) in self.seen:
                out.set_at((mx + int(mob["x"] * 2), my + int(mob["y"] * 2)), (255, 70, 70))
        for pk in self.picks:
            if (int(pk["x"]), int(pk["y"])) in self.seen:
                out.set_at((mx + int(pk["x"] * 2), my + int(pk["y"] * 2)), (120, 255, 200))
        for a, b in self.portals:
            for c in (a, b):
                if tuple(c) in self.seen:
                    pygame.draw.rect(out, (120, 240, 255), (mx + c[0] * 2, my + c[1] * 2, 2, 2))
        pygame.draw.rect(out, (255, 255, 255), (mx + int(self.px * 2) - 1, my + int(self.py * 2) - 1, 2, 2))
        ex, ey = mx + self.px * 2 + math.cos(self.ang) * 4, my + self.py * 2 + math.sin(self.ang) * 4
        pygame.draw.line(out, (255, 240, 170), (mx + int(self.px * 2), my + int(self.py * 2)), (int(ex), int(ey)))
        # silahlar
        for i, gun in enumerate(FPS_GUNS):
            sel = i == self.gun
            label = f"{i + 1} {gun['name']}" + ("" if i == 0 else f" {self.ammo[i]}")
            text(out, font, label, 8, H - 40 + i * 11, gun["col"] if sel else (120, 110, 140))
        if self.double > 0:
            text(out, font, f"ÇİFT VURUŞ {int(math.ceil(self.double))}", W - 8 - font.size("ÇİFT VURUŞ 6")[0], H - 18,
                 (230, 130, 255))
        for dx_, dy_ in ((-5, 0), (2, 0)):
            pygame.draw.line(out, (255, 255, 255), (W // 2 + dx_, H // 2), (W // 2 + dx_ + 3, H // 2))
        for dx_, dy_ in ((0, -5), (0, 2)):
            pygame.draw.line(out, (255, 255, 255), (W // 2, H // 2 + dy_), (W // 2, H // 2 + dy_ + 3))
        if FPS_TIME - self.left < 4:
            text(out, font, "W/A/S/D yürü · ok tuşları dön · J ateş · 1 2 3 silah", W // 2, H - 58, (230, 230, 255),
                 center=True)

    @staticmethod
    def warp(out, k):
        """Görüntüyü piksellere ayırır ve mora boyar (k: 0 temiz, 1 tam yırtık)."""
        n = max(1, int(1 + k * 18))
        small = pygame.transform.scale(out, (max(1, W // n), max(1, H // n)))
        out.blit(pygame.transform.scale(small, (W, H)), (0, 0))
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((190, 90, 255, int(210 * k)))
        out.blit(veil, (0, 0))

    def draw(self, canvas, font, big, t):
        if self.snapshot is None:
            self.snapshot = canvas.copy()
        if self.phase == "in" and self.t < 0.65:   # dünya çözülür
            canvas.blit(self.snapshot, (0, 0))
            self.warp(canvas, self.t / 0.65)
            cx, cy = W // 2, H // 2
            for i in range(4):  # kanat gibi açılan halkalar
                r = int((self.t / 0.65) * (40 + i * 44))
                pygame.draw.ellipse(canvas, (255, 240, 255), (cx - r, cy - r // 2, r * 2, r), 1)
            return
        self.render(canvas, t)
        if self.phase in ("in", "play"):
            self.draw_gun(canvas, t)
        self.draw_hud(canvas, font, big, t)
        if self.hurt > 0:
            veil = pygame.Surface((W, H), pygame.SRCALPHA)
            veil.fill((255, 40, 80, int(240 * self.hurt)))
            canvas.blit(veil, (0, 0))
        if self.phase == "in":
            self.warp(canvas, 1 - (self.t - 0.65) / 0.65)
            text(canvas, big, "ÖTE BOYUT", W // 2, 72, (255, 240, 255), center=True)
        elif self.phase == "out":                  # sayaç doldu, dünya geri geliyor
            k = min(1.0, self.t / 1.6)
            self.warp(canvas, k)
            cx, cy = W // 2, H // 2
            for i in range(5):
                r = int((1 - k) * 200) + i * 14
                pygame.draw.circle(canvas, (255, 255, 255), (cx, cy), r, 1)
            text(canvas, big, "SAYAÇ DOLDU", W // 2, 72, (255, 255, 255), center=True)
        elif self.phase == "result":
            canvas.fill((16, 8, 34))
            pygame.draw.rect(canvas, (200, 130, 255), (20, 10, W - 40, H - 20), 1)
            text(canvas, big, "BOYUT KAPANDI", W // 2, 20, (230, 180, 255), center=True)
            text(canvas, font, f"{self.kills} vuruş  ·  +{self.kills * 3} kül", W // 2, 38, (255, 220, 150), center=True)
            if self.earned:
                for i, key in enumerate(self.earned):
                    y = 54 + i * 24
                    canvas.blit(pygame.transform.scale(icon(key), (18, 18)), (54, y))
                    text(canvas, font, BOONS[key]["name"], 80, y - 2, (240, 220, 255))
                    text(canvas, font, " ".join(BOONS[key]["desc"]), 80, y + 8, (170, 160, 200))
            else:
                text(canvas, font, f"Kelebek hiçbir şey bırakmadı. {FPS_TIERS[0][0]} vuruş gerekiyordu.", W // 2, 80,
                     (170, 160, 200), center=True)
            if self.t > 0.8 and int(t * 2) % 2:
                text(canvas, font, "J: mahzene dön", W // 2, H - 24, (200, 240, 250), center=True)


# --- Otomatik test pilotu --------------------------------------------------------
class AutoKeys:
    def __init__(self, dx, dy):
        self.m = {pygame.K_d: dx > 0.3, pygame.K_a: dx < -0.3, pygame.K_s: dy > 0.3, pygame.K_w: dy < -0.3}

    def __getitem__(self, k):
        return self.m.get(k, False)


def path_step(px, py, gx, gy):
    """Karo ızgarasında BFS ile hedefe giden bir sonraki adımın yönü."""
    start, goal = (int(px) // TILE, int(py - 3) // TILE), (int(gx) // TILE, int(gy) // TILE)
    if start == goal:
        return norm(gx - px, gy - py)
    dist = {goal: 0}
    q = deque([goal])
    while q:
        x, y = q.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) not in dist and not CUR.solid(nx, ny):
                dist[(nx, ny)] = dist[(x, y)] + 1
                q.append((nx, ny))
    best = None
    for nx, ny in ((start[0] + 1, start[1]), (start[0] - 1, start[1]), (start[0], start[1] + 1),
                   (start[0], start[1] - 1)):
        if (nx, ny) in dist and (best is None or dist[(nx, ny)] < dist[best]):
            best = (nx, ny)
    if best is None:
        return norm(gx - px, gy - py)
    return norm(best[0] * TILE + 8 - px, best[1] * TILE + 11 - py)


def autopilot(game, frame):
    p, room = game.player, game.room
    attack = frame % 14 == 0
    dash = frame % 90 == 0
    target = None
    if game.state == "reward":
        return AutoKeys(0, 0), False, game.state_t > 0.6, (1 if frame % 25 == 0 else 0), None
    if game.state == "fps":  # en yakına döner, ateş eder; kimse yoksa yürür
        f = game.fps
        ak = AutoKeys(0, 0)
        if f.mobs:
            m = min(f.mobs, key=lambda m: math.hypot(m["x"] - f.px, m["y"] - f.py))
            diff = (math.atan2(m["y"] - f.py, m["x"] - f.px) - f.ang + math.pi) % math.tau - math.pi
            ak.m[pygame.K_RIGHT], ak.m[pygame.K_LEFT] = diff > 0.05, diff < -0.05
            ak.m[pygame.K_j] = abs(diff) < 0.2
            ak.m[pygame.K_w] = frame % 240 < 80
            ak.m[pygame.K_2] = frame % 400 < 5
            ak.m[pygame.K_3] = 200 <= frame % 400 < 205
        return ak, frame % 300 == 0, frame % 20 == 0, 0, None
    if game.dialog or game.state == "ending":
        return AutoKeys(0, 0), False, frame % 20 == 0, (1 if frame % 50 == 0 else 0), None
    if game.state == "pact":  # yalnızca test: KUL_PACT sıradaki akdi seçer
        game.pact_i = int(os.environ.get("KUL_PACT", "0"))
        return AutoKeys(0, 0), False, game.state_t > 0.5, 0, None
    if game.state == "market":  # alabildiğini alır, sonra ayrılır
        room.talked = True
        leave = game.state_t > 1.5
        return AutoKeys(0, 0), leave, frame % 20 == 0, (1 if frame % 30 == 0 else 0), None
    act = [e for e in game.enemies if e.active()]
    if game.oyku and not room.talked:
        target = (game.oyku.x, game.oyku.y + 14)
        attack = math.hypot(p.x - target[0], p.y - target[1]) < 12 and frame % 10 == 0
    elif room.item:
        target = (room.item[0], room.item[1])
    elif room.shrine and not room.shrine["used"]:
        target = (room.shrine["x"], room.shrine["y"] + 12)
        attack = math.hypot(p.x - target[0], p.y - target[1]) < 12 and frame % 10 == 0
    elif game.npc and not room.talked:
        target = (game.npc.x, game.npc.y + 14)
        attack = math.hypot(p.x - target[0], p.y - target[1]) < 12 and frame % 10 == 0
    elif room.chest and not room.chest["open"]:
        target = (room.chest["x"], room.chest["y"] + 12)
        attack = math.hypot(p.x - target[0], p.y - target[1]) < 12 and frame % 10 == 0
    elif room.altar and not room.altar_used:
        target = (room.altar[0] * TILE + 16, room.altar[1] * TILE + 26)
        attack = math.hypot(p.x - target[0], p.y - target[1]) < 10 and frame % 10 == 0
    elif act:
        e = min(act, key=lambda e: math.hypot(e.x - p.x, e.y - p.y))
        target = (e.x, e.y)
        dist = math.hypot(e.x - p.x, e.y - p.y)
        skill = None
        if dist < 80 and frame % 25 == 0:
            ready = [i for i in range(4 if p.has_beam else 3) if p.skill_cd[i] <= 0]
            if ready:
                skill = random.choice(ready)
        keep = 60 if p.weapon in ("yay", "asa") else 14
        if dist < keep:
            d = norm(e.x - p.x, e.y - p.y)
            if p.weapon == "yay" and frame % 6:
                p.aim = d  # okçu: yerinde durup nişan alır
                return AutoKeys(0, 0), dash, attack, 0, skill
            return AutoKeys(*d), dash, attack, 0, skill
        dd = path_step(p.x, p.y, *target)
        return AutoKeys(*dd), dash, attack, 0, skill
    elif room.door_open:
        target = (room.door_col * TILE + 8, 6)
    if target is None:
        return AutoKeys(0, 0), False, False, 0, None
    d = path_step(p.x, p.y, *target)
    return AutoKeys(*d), dash, attack, 0, None


# --- Ana döngü ---------------------------------------------------------------
def main():
    pygame.mixer.pre_init(22050, -16, 1, 512)
    pygame.init()
    pygame.display.set_caption("Kül Mahzeni")
    settings = load_settings()

    def open_window():
        if settings["fullscreen"]:
            return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        return pygame.display.set_mode((W * 4, H * 4), pygame.RESIZABLE)

    window = open_window()
    canvas = pygame.Surface((W, H))
    world = pygame.Surface((W, WORLD_H))
    iris = pygame.Surface((W, WORLD_H))
    iris.set_colorkey((255, 0, 255))
    clock = pygame.time.Clock()
    font = PixelFont()
    big = PixelFont(2)
    logo_font = PixelFont(2)

    sfx = Sfx()
    sfx.set_levels(settings["music"], settings["sfx"])
    sfx.start_music()
    menu = PauseMenu(settings, sfx)
    lights = {
        "player": [make_light(r, (200, 186, 220)) for r in (74, 76)],
        "torch": [make_light(r, (255, 156, 84)) for r in (76, 80, 84)],
        "wisp": make_light(30, (255, 120, 50)),
        "wisp_big": make_light(40, (255, 150, 70)),
        "bolt": make_light(16, (255, 140, 60)),
        "door": [make_light(r, (110, 90, 170)) for r in (36, 40)],
        "altar": [make_light(r, (255, 150, 80)) for r in (82, 86)],
        "altar_low": make_light(40, (160, 70, 40)),
        "boss": make_light(58, (255, 130, 60)),
        "pyre": make_light(66, (255, 110, 40)),
        "shade": make_light(38, (120, 100, 210)),
        "item": make_light(34, (200, 210, 255)),
        "shot": make_light(18, (200, 170, 130)),
        "ghost": make_light(22, (120, 160, 255)),
        "fx": make_light(40, (255, 160, 80)),
    }
    glows = {  # ışıktan sonra eklenen parıltılar (bloom hissi)
        "torch": [make_light(r, (150, 70, 24)) for r in (9, 10, 11)],
        "bolt": make_light(7, (160, 70, 30)),
        "shot": make_light(5, (90, 70, 50)),
        "ghost": make_light(7, (50, 80, 160)),
        "eye": make_light(4, (120, 40, 20)),
    }
    vignette = build_vignette()
    lightmap = pygame.Surface((W, WORLD_H))
    hurt_overlay = pygame.Surface((W, WORLD_H), pygame.SRCALPHA)
    for y in range(WORLD_H):  # kenarlarda kızaran hasar çerçevesi
        for x in range(0, W, 1):
            d = max(abs(x - W / 2) / (W / 2), abs(y - WORLD_H / 2) / (WORLD_H / 2))
            if d > 0.75 and (x + y) % 2 == 0:
                hurt_overlay.set_at((x, y), (200, 20, 30, int(160 * (d - 0.75) / 0.25)))
    ash = Ash(random.Random())
    t = 0.0
    max_frames = int(os.environ.get("KUL_TEST_FRAMES", "0"))  # otomatik test için
    shot_dir = os.environ.get("KUL_SHOT_DIR")
    shot_at = {int(v) for v in os.environ.get("KUL_SHOT_AT", "").split(",") if v}
    frame = 0
    save = load_save()
    title = TitleScreen(save)
    title.ensure_bg(font)
    scene = "title"
    game = None
    test_weapon = os.environ.get("KUL_WEAPON", "kilic")
    title_frames = int(os.environ.get("KUL_TITLE_FRAMES", "0"))
    shop_test = {}
    if os.environ.get("KUL_SHOP_TEST"):
        K = pygame
        shop_test = {20: K.K_k, 40: K.K_j, 60: K.K_j, 80: K.K_s, 90: K.K_j, 100: K.K_s, 110: K.K_s,
                     120: K.K_s, 130: K.K_j, 150: K.K_s, 160: K.K_j, 190: K.K_ESCAPE}
    # menü testi: belirli karelerde tuşa basılmış gibi yap
    menu_script = {}
    if os.environ.get("KUL_MENU_TEST"):
        K = pygame
        menu_script = {100: "open", 160: K.K_s, 170: K.K_j, 200: K.K_d, 210: K.K_s, 220: K.K_a,
                       230: K.K_s, 240: K.K_j, 260: K.K_ESCAPE, 270: K.K_s, 280: K.K_j, 320: K.K_ESCAPE,
                       330: K.K_s, 340: K.K_j, 370: K.K_ESCAPE}

    def add_light(img, x, y):
        r = img.get_width() // 2
        lightmap.blit(img, (int(x) - r, int(y) - r), special_flags=pygame.BLEND_RGB_ADD)

    def add_glow(img, x, y):
        r = img.get_width() // 2
        world.blit(img, (int(x) - r, int(y) - r), special_flags=pygame.BLEND_RGB_ADD)

    def start_game(weapon, resume=None, spirit=None):
        nonlocal game, scene
        game = Game(sfx, font, weapon, save, resume, spirit)
        scene = "game"

    def to_title():
        nonlocal scene
        global CUR
        write_save(save)
        scene = "title"
        CUR = title.room
        sfx.start_music("calm")

    def present():
        ww, wh = window.get_size()
        s = max(1, min(ww // W, wh // H))
        scaled = pygame.transform.scale(canvas, (W * s, H * s))
        window.fill((0, 0, 0))
        window.blit(scaled, ((ww - W * s) // 2, (wh - H * s) // 2))
        pygame.display.flip()

    while True:
        if max_frames:
            clock.tick(0)
            dt = 1 / 60
        else:
            dt = min(clock.tick(FPS) / 1000, 1 / 30)
        t += dt
        frame += 1
        dash_pressed = attack_pressed = False
        nav = 0
        skill = None
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                save_settings(settings)
                write_save(save)
                return
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_F11:
                settings["fullscreen"] = not settings["fullscreen"]
                window = open_window()
                save_settings(settings)
                continue
            if scene == "title":
                if ev.type == pygame.KEYDOWN:
                    act = title.handle(ev.key, sfx)
                    if act == "quit":
                        write_save(save)
                        return
                    if act == "start":
                        start_game(WEAPON_ORDER[title.sel], spirit=SPIRIT_ORDER[title.spirit_i])
                    if act == "continue":
                        ck = save["checkpoint"]
                        start_game(ck["weapon"], resume=ck)
                continue
            if ev.type == pygame.WINDOWFOCUSLOST and not menu.open and game.state == "play" and not max_frames:
                menu.show()  # başka pencereye geçince oyun kendiliğinden durur
            if ev.type == pygame.KEYDOWN and menu.open:
                act = menu.handle(ev.key)
                if act == "quit":
                    write_save(save)
                    return
                if act == "restart":
                    to_title()
                if act == "fullscreen":
                    window = open_window()
                continue
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    if game.state != "dead":
                        menu.show()
                    else:
                        to_title()
                    continue
                if ev.key == pygame.K_SPACE:
                    dash_pressed = True
                if ev.key in (pygame.K_j, pygame.K_x, pygame.K_RETURN):
                    attack_pressed = True
                if ev.key == pygame.K_k:
                    skill = 0
                if ev.key == pygame.K_l:
                    skill = 1
                if ev.key in (pygame.K_i, pygame.K_u):
                    skill = 2
                if ev.key == pygame.K_o:
                    skill = 3
                if ev.key in (pygame.K_a, pygame.K_LEFT):
                    nav = -1
                if ev.key in (pygame.K_d, pygame.K_RIGHT):
                    nav = 1
                if ev.key == pygame.K_m:
                    sfx.toggle()
                if ev.key == pygame.K_r and game.state == "dead" and game.state_t > 1.0:
                    to_title()
                if ev.key == pygame.K_k and game.state == "dead" and game.state_t > 1.0:
                    to_title()
                    title.shop.open, title.shop.msg = True, ""

        # --- başlangıç ekranı ---
        if scene == "title":
            if max_frames:
                if shop_test and frame < 200:  # kül sunağını gez, alabildiğini al
                    if frame in shop_test:
                        title.handle(shop_test[frame], sfx)
                elif os.environ.get("KUL_CONTINUE") and save.get("checkpoint"):
                    ck = save["checkpoint"]
                    start_game(ck["weapon"], resume=ck)
                elif title_frames and frame < title_frames:
                    if frame % 30 == 0:
                        title.handle(pygame.K_d, sfx)
                else:
                    title.sel = WEAPON_ORDER.index(test_weapon)
                    start_game(test_weapon, spirit=os.environ.get("KUL_SPIRIT"))
            ash.set_haven(False)
            ash.update(dt)
            if scene == "title":
                title.draw(canvas, world, lightmap, lights, ash, font, logo_font, vignette)
                if shot_dir and frame in shot_at:
                    pygame.image.save(pygame.transform.scale(canvas, (W * 3, H * 3)),
                                      os.path.join(shot_dir, f"f{frame}.png"))
                present()
                continue

        keys = pygame.key.get_pressed()
        if frame in menu_script:
            k = menu_script[frame]
            if k == "open":
                menu.show()
            elif menu.open:
                menu.handle(k)
        if max_frames and not menu.open:
            keys, dash_pressed, attack_pressed, nav, skill = autopilot(game, frame)
        if max_frames and frame >= max_frames:
            p = game.player
            print("test:", " | ".join(game.log))
            print(f"test: silah={p.weapon} oda={game.room.depth} can={p.hp}/{p.max_hp} oldurme={game.kills} "
                  f"durum={game.state} istek={game.quest} elde={game.carrying} armagan={p.boons}")
            print(f"test: yetenekler={game.skill_uses}")
            print(f"test: kul={save['kul']} bu_oyun={game.kul_run} guc={save['perks']} oyun={save['runs']} "
                  f"en_derin={save['best_floor']} kayit={'var' if save['checkpoint'] else 'yok'}")
            return

        if menu.open:
            menu.t += dt
        else:
            game.update(dt, keys, dash_pressed, attack_pressed, nav, skill)
        if scene != "game":
            continue
        game.scare_on = settings["scare"]
        if game.state == "scare":
            draw_scare(canvas, game)
            if shot_dir and frame in shot_at:
                pygame.image.save(pygame.transform.scale(canvas, (W * 3, H * 3)),
                                  os.path.join(shot_dir, f"f{frame}.png"))
            present()
            continue
        if game.state == "fps":  # kelebek boyutu kendi ekranını çizer
            game.fps.draw(canvas, font, big, t)
            if menu.open:
                draw_menu(canvas, font, big, menu, game, t)
            if shot_dir and frame in shot_at:
                pygame.image.save(pygame.transform.scale(canvas, (W * 3, H * 3)),
                                  os.path.join(shot_dir, f"f{frame}.png"))
            present()
            continue
        ash.set_haven(game.room.kind in ("haven", "ani"))
        ash.update(dt)
        room, player = game.room, game.player
        haven = room.kind in ("haven", "ani")

        # sahne (y'ye göre sıralı)
        world.blit(room.bg, (0, 0))
        for tx, ty in room.torches:
            draw_torch(world, tx, ty, t + tx)
        draw_door(world, room, t)
        draw_chest(world, room, t)
        actors = list(game.enemies)
        if game.boss_dying:
            actors.append(game.boss_dying["boss"])
        if player.hp > 0:
            actors.append(player)
        if game.oyku:
            actors.append(game.oyku)
        if game.npc:
            actors.append(game.npc)
        for a in sorted(actors, key=lambda a: a.y):
            if a is game.oyku or a is game.npc:
                a.draw(world, t, player)
            else:
                a.draw(world)

        # ışık haritası: ortam + meşaleler + oyuncu feneri, sahneyle çarpılır
        dk = 1 - game.darkness
        lightmap.fill(tuple(int(v * dk) for v in room.ambient))
        for i, (tx, ty) in enumerate(room.torches):
            lt = lights["torch"][int(t * 9 + i * 2) % 3]
            add_light(lt, tx * TILE + 8, ty * TILE + 8)
        if room.door_open:
            add_light(lights["door"][int(t * 3) % 2], room.door_col * TILE + 8, 12)
        if room.altar:
            ax, ay = room.altar[0] * TILE + 16, room.altar[1] * TILE
            add_light(lights["altar_low"] if room.altar_used else lights["altar"][int(t * 7) % 2], ax, ay)
        if player.hp > 0:
            add_light(lights["player"][int(t * 4) % 2], player.x, player.y - 8 - player.z)
        for e in game.enemies:
            lt = e.light()
            if lt:
                add_light(lights[lt[0]], lt[1], lt[2])
        for b in game.bolts:
            add_light(lights["bolt"], b.x, b.y)
        for sh in game.pshots:
            add_light(lights["ghost" if sh.kind == "ghost" else "shot"], sh.x, sh.y)
        for e in game.effects:
            if e["kind"] in ("crater", "wave", "spin"):
                add_light(lights["fx"], e["x"], e["y"])
        if game.boss_dying:
            bd = game.boss_dying["boss"]
            add_light(lights[getattr(bd, "LIGHT", "boss")], *bd.core())
        if room.item:
            add_light(lights["item"], room.item[0], room.item[1] - 8)
        if game.npc:  # tüccarın feneri
            add_light(lights["altar"][int(t * 7) % 2], game.npc.x + 5, game.npc.y - 8)
        if room.chest and not room.chest.get("gone"):
            add_light(lights["item"], room.chest["x"], room.chest["y"] - 8)
        if room.shrine and not room.shrine["used"]:
            add_light(lights["item"], room.shrine["x"], 62)
        world.blit(lightmap, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        if not haven:
            world.blit(vignette, (0, 0), special_flags=pygame.BLEND_RGB_MULT)

        # parıltılar ve kendi ışığıyla parlayanlar
        for i, (tx, ty) in enumerate(room.torches):
            add_glow(glows["torch"][int(t * 9 + i) % 3], tx * TILE + 8, ty * TILE + 8)
        for b in game.bolts:
            add_glow(glows["bolt"], b.x, b.y)
        for sh in game.pshots:
            add_glow(glows["ghost" if sh.kind == "ghost" else "shot"], sh.x, sh.y)
        draw_altar_fire(world, room, t)
        draw_shrine_fire(world, room, t)
        draw_spikes(world, game, t)
        for h in game.hazards:
            h.draw(world, t)
        for e in game.effects:
            draw_effect(world, e, t)
        for e in game.enemies:
            e.draw_lit(world, t)
            if e.active() and (e.burn > 0 or e.slow > 0):  # ruh etkileri
                br = e.body_rect()
                c = (255, 150, 60) if e.burn > 0 else (150, 210, 255)
                for j in range(3):
                    wx = br.left + (j * 5 + int(t * 9)) % max(1, br.width)
                    wy = br.bottom - 1 - (int(t * 24) + j * 5) % max(1, br.height)
                    if 0 <= wx < W and 0 <= wy < WORLD_H:
                        world.set_at((wx, wy), c)
            if e.stun > 0 and e.active():  # sersemleme yıldızları
                top = e.body_rect().top - 3
                for j in range(2):
                    a = t * 7 + j * math.pi
                    world.set_at((int(e.x + math.cos(a) * 5), int(top + math.sin(a) * 1.5)), (255, 240, 140))
        if game.boss_dying:
            game.boss_dying["boss"].draw_lit(world, t)
        for s in game.shards:  # kor kırıntıları
            sx_, sy_ = int(s[0]), int(s[1])
            add_glow(glows["shot"], sx_, sy_)
            if 0 <= sx_ < W and 0 <= sy_ < WORLD_H:
                tw = int(t * 12 + s[4] * 7) % 3
                c = (255, 240, 200) if tw == 0 else (255, 190, 100)
                pygame.draw.rect(world, (235, 110, 50), (sx_ - 1, sy_, 3, 1))
                pygame.draw.rect(world, (235, 110, 50), (sx_, sy_ - 1, 1, 3))
                world.set_at((sx_, sy_), c)
        if room.item:  # bekçinin düşürdüğü eşya: süzülür ve parlar
            ix, iy = int(room.item[0]), int(room.item[1] - 12 + math.sin(t * 3) * 2)
            pygame.draw.ellipse(world, (20, 18, 30), (ix - 5, int(room.item[1]) - 2, 10, 3))
            world.blit(item_icon(room.item[2]), (ix - 4, iy - 4))
            for j in range(3):
                a = t * 2 + j * math.tau / 3
                world.set_at((int(ix + math.cos(a) * 9), int(iy + math.sin(a) * 6)), (255, 255, 230))
        if player.hp > 0:
            player.draw_attack(world, t)
        for sh in game.pshots:
            sh.draw(world)
        for b in game.bolts:
            b.draw(world)
        game.fx.draw(world)
        ash.draw(world)
        for nx, ny, life, val in game.numbers:
            col = (255, 160, 60) if val >= 5 else (255, 240, 200) if val >= 3 else (230, 225, 235)
            draw_number(world, val, int(nx), int(ny), col)

        if room.altar and not room.altar_used and game.state == "play":
            ax, ay = room.altar[0] * TILE + 16, room.altar[1] * TILE + 10
            if math.hypot(player.x - ax, player.y - ay) < 30:
                text(world, font, "J: kora dokun", ax, ay - 22, (255, 200, 120), center=True)
        if game.npc and game.state == "play" and math.hypot(player.x - game.npc.x, player.y - game.npc.y) < 28:
            text(world, font, "J: pazarlık", int(game.npc.x), int(game.npc.y) - game.npc.img.get_height() - 11, (220, 190, 240), center=True)
        sh = room.shrine
        if sh and not sh["used"] and game.state == "play" and math.hypot(player.x - sh["x"], player.y - sh["y"]) < 30:
            text(world, font, "J: taşa dokun", sh["x"], 44, (220, 150, 240), center=True)
        ch = room.chest
        if ch and not ch["open"] and game.state == "play" and math.hypot(player.x - ch["x"], player.y - ch["y"]) < 24:
            text(world, font, "J: sandığı aç", ch["x"], ch["y"] - 26, (255, 220, 140), center=True)
        if game.oyku and not game.dialog and game.state == "play":
            if math.hypot(player.x - game.oyku.x, player.y - game.oyku.y) < 28:
                text(world, font, "J: konuş", int(game.oyku.x), int(game.oyku.y) - 30, (150, 50, 90), center=True)
            elif not room.talked and int(t * 2) % 2:
                text(world, font, "!", int(game.oyku.x), int(game.oyku.y) - 30, (220, 60, 110), center=True)

        if player.hp > 0 and player.invuln > INVULN_TIME - 0.3:
            world.blit(hurt_overlay, (0, 0))
        if game.flash > 0:
            fl = pygame.Surface((W, WORLD_H))
            fl.fill((255, 240, 220))
            fl.set_alpha(int(110 * game.flash / 0.1))
            world.blit(fl, (0, 0))

        r = game.iris_radius()
        if r is not None:  # oda geçişi: oyuncunun etrafında daralan/açılan çember
            iris.fill((0, 0, 0))
            if r > 0:
                pygame.draw.circle(iris, (255, 0, 255), (int(player.x), int(player.y) - 8), r)
            world.blit(iris, (0, 0))

        if game.title_t > 0 and game.state != "out":
            a = min(1.0, game.title_t / 0.6, (2.2 - game.title_t) / 0.4)
            k = max(0.0, a)
            ttl, sub, col = game.title
            ty = 92 if room.kind == "haven" else 46 if room.kind == "boss" else 34
            text(world, big, ttl, W // 2, ty, (int(col[0] * k), int(col[1] * k), int(col[2] * k)), center=True)
            if sub:
                text(world, font, sub, W // 2, ty + 18, (int(170 * k), int(150 * k), int(170 * k)), center=True)
        boss = game.boss()
        if boss and boss.state != "spawn" and game.state == "play":
            draw_boss_bar(world, font, boss, t)
        if room.kind == "kusatma" and not room.cleared and game.state == "play":
            draw_siege_bar(world, font, game, t)

        canvas.fill((0, 0, 0))
        sx = sy = 0
        if game.shake > 0 and settings["shake"]:
            m = int(math.ceil(game.shake))
            sx, sy = random.randint(-m, m), random.randint(-m, m)
        canvas.blit(world, (sx, sy))

        if game.dialog:
            draw_dialog(canvas, font, game, t)
        if game.state == "ending":
            draw_ending(canvas, big, font, game, t)
        if game.state == "reward":
            draw_reward(canvas, font, game, t)
        if game.state == "market":
            draw_market(canvas, font, game, t)
        if game.state == "pact":
            draw_pact(canvas, font, game, t)
        if game.state == "dead" and game.state_t > 1.0:
            shade = pygame.Surface((W, WORLD_H), pygame.SRCALPHA)
            shade.fill((0, 0, 0, min(160, int((game.state_t - 1) * 200))))
            canvas.blit(shade, (0, 0))
            text(canvas, big, "KÜLE DÖNDÜN", W // 2, 50, (200, 60, 60), center=True)
            text(canvas, font, f"{room.floor}. katta düştün, {game.kills} hortlak susturdun",
                 W // 2, 74, (150, 140, 160), center=True)
            kw = font.size(f"bu yolculukta {game.kul_run} kül topladın, külün seninle kalır")[0]
            text(canvas, font, f"bu yolculukta {game.kul_run} kül topladın, külün seninle kalır",
                 W // 2, 86, (255, 200, 140), center=True)
            canvas.blit(kul_icon(), (W // 2 - kw // 2 - 9, 88))
            text(canvas, font, "R: silah seç ve yeniden uyan  ·  K: kül sunağı", W // 2, 104, (110, 100, 130),
                 center=True)
        draw_hud(canvas, font, game)
        if menu.open:
            draw_menu(canvas, font, big, menu, game, t)

        if shot_dir and os.environ.get("KUL_SHOT_EVENTS") and frame % 45 == 0:
            tag = None
            if game.boss() and game.boss().state != "spawn":
                tag = f"boss{game.room.floor}_p{game.boss().phase}"
            elif game.boss_dying:
                tag = "bossdeath"
            elif game.dialog:
                tag = f"dialog{game.room.floor}_{game.dialog['i']}"
            elif game.state == "ending":
                tag = "ending"
            elif room.item:
                tag = "item"
            elif haven:
                tag = "haven"
            elif game.state == "market":
                tag = "market"
            elif room.kind in ("hazine", "dukkan") or room.variant:
                tag = room.variant or room.kind
            elif game.effects:
                tag = "skill_" + "_".join(sorted({e["kind"] for e in game.effects}))
            if tag:
                pygame.image.save(pygame.transform.scale(canvas, (W * 3, H * 3)),
                                  os.path.join(shot_dir, f"{tag}_{frame}.png"))
        if shot_dir and frame in shot_at:
            pygame.image.save(pygame.transform.scale(canvas, (W * 3, H * 3)),
                              os.path.join(shot_dir, f"f{frame}.png"))
        present()


if __name__ == "__main__":
    main()
    pygame.quit()
    sys.exit()
