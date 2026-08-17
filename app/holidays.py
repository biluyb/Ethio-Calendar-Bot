"""
Ethiopian Public Holidays and Key Dates Database
Supports fixed Ethiopian holidays, fixed Gregorian holidays (e.g. May Day),
and moveable Christian/Islamic holidays for 10+ years.
Includes detailed historical & cultural descriptions in Amharic & English.
"""

from app.utils import eth_to_greg, greg_to_eth

# Shared Descriptions Dictionary
HOLIDAY_DESCRIPTIONS = {
    "enkutatash": {
        "am": "እንቁጣጣሽ (አዲስ ዓመት) የኢትዮጵያ የዘመን መለወጫ በዓል መስከረም 1 ቀን ይከበራል። በዓሉ የክረምቱ ዝናብ አልፎ አበቦች የሚያብቡበት፣ ተስፋና አዲስ ጅምር የሚበሰርበት ታላቅ ህዝባዊ በዓል ነው።",
        "en": "Enkutatash (Ethiopian New Year) marks the beginning of the Ethiopian calendar on Meskerem 1. It celebrates the end of the rainy season, the blooming of yellow Adey Abeba flowers, and new beginnings."
    },
    "demera": {
        "am": "ደመራ የመስቀል በዓል ዋዜማ መስከረም 16 ቀን የሚከበር ሲሆን፣ ንግሥት እሌኒ የእውነተኛውን ክርስቶስ መስቀል ለማግኘት የደመራ ጭስ የተከተለችበትን ታሪካዊ ክስተት ለማስታወስ የእንጨት ደመራ ተደምሮ በእሳት ይቃጠላል።",
        "en": "Demera is celebrated on the eve of Meskel (Meskerem 16). A large bonfire is built and burned to commemorate Empress Helena's discovery of the True Cross guided by smoke."
    },
    "meskel": {
        "am": "መስቀል (የቅዱስ መስቀል መገኘት) መስከረም 17 ቀን የሚከበር ሀገራዊና ሃይማኖታዊ በዓል ነው። በዩኔስኮ በማይጨበጥ የዓለም ባህላዊ ቅርሶች ዝርዝር ውስጥ የተመዘገበ ታላቅ በዓል ነው።",
        "en": "Meskel commemorates the 4th-century discovery of the True Cross by Empress Helena. Recognized by UNESCO as an Intangible Cultural Heritage of Humanity."
    },
    "national_unity": {
        "am": "የብሔር ብሔረሰቦች ቀን ኅዳር 20 ቀን የሚከበር ሲሆን የኢትዮጵያ ብሔሮች፣ ብሔረሰቦችና ሕዝቦች እኩልነት፣ አንድነትና ባህላዊ ብዝሃነት የሚከበርበት በዓል ነው።",
        "en": "Ethiopian National Unity Day (Nations, Nationalities and Peoples' Day) celebrated on Hidar 20 to honor the diversity, equality, and unity of Ethiopia's cultural ethnic groups."
    },
    "hidar_tsion": {
        "am": "ሕዳር ጽዮን ታቦተ ጽዮን ወደ ኢትዮጵያ የመጣችበትንና በአክሱም ጽዮን ማርያም ቤተክርስቲያን የገባችበትን ታሪካዊና ሃይማኖታዊ ክስተት በማሰብ ኅዳር 21 ቀን የሚከበር ታላቅ በዓል ነው።",
        "en": "Hidar Tsion is celebrated on Hidar 21 to honor Saint Mary of Zion in Axum, commemorating the arrival of the Ark of the Covenant in Ethiopia."
    },
    "gena_eve": {
        "am": "የገና ዋዜማ (ታኅሣሥ 28/29) የኢትዮጵያ ክርስቶስ ልደት በዓል ዋዜማ ሲሆን፣ ምእመናን በጾምና በጸሎት የሚያሳልፉበት ቀን ነው።",
        "en": "Ethiopian Christmas Eve observed with prayer, fasting, and preparations for Christmas Day."
    },
    "gena": {
        "am": "ገና (የክርስቶስ ልደት በዓል) ታኅሣሥ 29/ጥር 1 ቀን የሚከበር ሲሆን፣ የኢየሱስ ክርስቶስን ልደት በማሰብ ባህላዊ የገና ጨዋታ እየተጨወተና ባህላዊ உணவுகள் እየተዘጋጁ ይከበራል።",
        "en": "Gena (Ethiopian Christmas) celebrates the birth of Jesus Christ. Marked by traditional Genna sports games, family feasts, and church ceremonies."
    },
    "timkat": {
        "am": "ጥምቀት ጥር 11 ቀን የሚከበር ታላቅ በዓል ሲሆን፣ የኢየሱስ ክርስቶስ በዮርዳኖስ ወንዝ መጠመቅ የሚታሰብበትና ታቦታት ወደ ጥምቀተ ባሕር ወርደው በባህላዊና ሃይማኖታዊ ስነ-ስርዓት የሚከበር በዓል ነው።",
        "en": "Timkat (Ethiopian Epiphany) celebrates the baptism of Jesus in the Jordan River. Sacred Tabots are carried to water bodies amidst vibrant processions (UNESCO Intangible Cultural Heritage)."
    },
    "kana_galila": {
        "am": "ቃና ዘገሊላ ጥር 12 ቀን የሚከበር ሲሆን ኢየሱስ ክርስቶስ በቃና ዘገሊላ ሰርግ ላይ ውሃውን ወደ ወይን ጠጅ የለወጠበት የመጀመሪያው ተአምር የሚታሰብበት በዓል ነው።",
        "en": "Kana ZeGalila (Jan 19/20) commemorates Jesus' first miracle of turning water into wine at the Wedding in Cana."
    },
    "yekatit_12": {
        "am": "የሰማዕታት ቀን (የካቲት 12) በ1929 ዓ.ም በፋሺስት ጣሊያን በግራዚያኒ አዛዥነት በአዲስ አበባ የተጨፈጨፉትን ከ30,000 በላይ ንጹሃን ኢትዮጵያውያን ሰማዕታትን ለማሰብ የሚከበር የሀዘንና የማስታወሻ ቀን ነው።",
        "en": "Ethiopian Martyrs' Day (Yekatit 12) commemorates over 30,000 innocent Ethiopians massacred in Addis Ababa in 1937 by Fascist Italian forces following an attempt on General Graziani."
    },
    "adwa": {
        "am": "የዓድዋ ድል በዓል የካቲት 23 ቀን 1888 ዓ.ም ኢትዮጵያውያን በአጼ ምኒልክና እቴጌ ጣይቱ መሪነት የጣሊያንን ዘመናዊ ወራሪ ጦር በዓድዋ ተራሮች ላይ አሸንፈው የሀገራቸውን ነጻነት ያስከበሩበት ታሪካዊ በዓል ነው።",
        "en": "Victory of Adwa Day celebrates the historic 1896 battle where Ethiopian forces led by Emperor Menelik II defeated invading Italian troops, securing sovereignty and inspiring Pan-African freedom."
    },
    "patriots_day": {
        "am": "የአርበኞች (የድል) ቀን ሚያዝያ 27 ቀን የሚከበር ሲሆን፣ በ1933 ዓ.ም ጀግኖች አርበኞች የ5 ዓመቱን የፋሺስት ጣሊያን ወረራ አሸንፈው አጼ ኃይለሥላሴ አዲስ አበባ የገቡበት የድል ቀን ነው።",
        "en": "Patriots' Victory Day (Miyazia 27) marks the 1941 liberation of Ethiopia from the 5-year Italian Fascist occupation and Emperor Haile Selassie's return to the capital."
    },
    "derg_downfall": {
        "am": "ግንቦት 20 (የደርግ የወደቀበት ቀን) በ1983 ዓ.ም ወታደራዊው የደርግ ዛንግ ተሸንፎ የነበረበትን ታሪካዊ ለውጥ ለማሰብ የሚከበር የህዝብ በዓል ነው።",
        "en": "Downfall of the Derg Regime (Ginbot 20) marks the May 28, 1991 end of the military Derg dictatorship in Ethiopia."
    },
    "workers_day": {
        "am": "የዓለም ሠራተኞች (የላብ አደሮች) ቀን (May Day) በየዓመቱ ሜይ 1 ቀን የሚከበር ዓለም አቀፍ የሠራተኞች መብትና አስተዋጽኦ መታሰቢያ በዓል ነው።",
        "en": "International Workers' Day (May Day) honors the contributions, historical struggles, and rights of workers worldwide."
    },
    "siklet": {
        "am": "ስቅለት (መልካም ዓርብ) የኢየሱስ ክርስቶስ ስቀለትና ሞት የሚታሰብበት፣ ምእመናን ሙሉ ቀን በስግደትና በጾም የሚያሳልፉበት ቅዱስ ቀን ነው።",
        "en": "Ethiopian Good Friday (Siklet) commemorates the passion and crucifixion of Jesus Christ, observed with strict fasting and prostrations."
    },
    "fasika": {
        "am": "ፋሲካ (የክርስቶስ ትንሣኤ በዓል) የኢየሱስ ክርስቶስ ከሙታን ተለይቶ መነሳት የሚከበርበት ታላቅ የትልቅ ጾም ፍጻሜና የደስታ በዓል ነው።",
        "en": "Ethiopian Easter (Fasika) celebrates the Resurrection of Jesus Christ following the 55-day Great Lent (Abiy Tsom)."
    },
    "mawlid": {
        "am": "መውሊድ የነቢዩ ሙሐመድ (ሶ.ዐ.ወ) ልደት የሚከበርበት ታላቅ እስላማዊ በዓል ሲሆን፣ በመንዙማ፣ በሶለዋትና በምግብ ዝግጅት በደስታ ይከበራል።",
        "en": "Mawlid an-Nabi celebrates the birth of the Prophet Muhammad (PBUH) with prayers, religious recitations (Menzuma), and charitable feasts."
    },
    "eid_fitr": {
        "am": "ዒድ አል ፊጥር የረመዳን ወር ጾም መጠናቀቅን ተከትሎ የሚከበር ታላቅ የእስልምና በዓል ሲሆን፣ በሰላት፣ በዘካተል ፊጥርና በቤተሰብ ደስታ ይከበራል።",
        "en": "Eid al-Fitr marks the end of the holy month of Ramadan, celebrated with communal morning prayers, charity, and festive family meals."
    },
    "eid_adha": {
        "am": "ዒድ አል አድሃ (አረፋ) ነቢዩ ኢብራሂም ልጃቸውን ለመሥዋዕትነት ለማቅረብ ያሳዩትን መታዘዝ ለማሰብ የሚከበር የእስልምና በዓል ነው።",
        "en": "Eid al-Adha (Feast of Sacrifice) honors Prophet Ibrahim's willingness to sacrifice his son in obedience to God, marked by Qurbani (charitable meat distribution)."
    },
    "pagume": {
        "am": "ጳጉሜ 13ኛው የኢትዮጵያ ወር ሲሆን፣ 5 ወይም 6 (በዘመነ ሉቃስ) ቀናት ያሉት የዓመት መሸጋገሪያ ልዩ ወር ነው።",
        "en": "Pagume is the 13th month of the Ethiopian Calendar, consisting of 5 days (6 days in leap years)."
    }
}


# Fixed Ethiopian Holidays: (eth_month, eth_day) -> info dict
FIXED_ETHIOPIAN_HOLIDAYS = {
    # ══ መስከረም / Meskerem ══
    (1, 1):   {"en": "Ethiopian New Year (Enkutatash)", "am": "አዲስ ዓመት (እንቁጣጣሽ)", "type": "holiday", "key": "enkutatash"},
    (1, 16):  {"en": "Demera (Cross Eve)", "am": "ደመራ (መስቀል ዋዜማ)", "type": "special", "key": "demera"},
    (1, 17):  {"en": "Finding of the True Cross (Meskel)", "am": "መስቀል", "type": "holiday", "key": "meskel"},

    # ══ ኅዳር / Hidar ══
    (3, 20):  {"en": "Ethiopian National Unity Day", "am": "የብሔር ብሔረሰቦች ቀን", "type": "holiday", "key": "national_unity"},
    (3, 21):  {"en": "Hidar Tsion (Celebration of Mary)", "am": "ሕዳር ጽዮን", "type": "special", "key": "hidar_tsion"},

    # ══ ታኅሣሥ / Tahsas ══
    (4, 28):  {"en": "Ethiopian Christmas Eve (Leap Year)", "am": "የገና ዋዜማ (ዘመነ ሉቃስ)", "type": "closure", "key": "gena_eve"},
    (4, 29):  {"en": "Ethiopian Christmas / Gena", "am": "ገና / ልደት", "type": "holiday", "key": "gena"},

    # ══ ጥር / Tir ══
    (5, 1):   {"en": "Ethiopian Christmas Day (Tir 1)", "am": "ልደት (ጥር 1)", "type": "holiday", "key": "gena"},
    (5, 11):  {"en": "Ethiopian Epiphany (Timkat)", "am": "ጥምቀት", "type": "holiday", "key": "timkat"},
    (5, 12):  {"en": "Epiphany 2nd Day (Kana ZeGalila)", "am": "ቃና ዘገሊላ (ጥምቀት 2ኛ ቀን)", "type": "special", "key": "kana_galila"},

    # ══ የካቲት / Yekatit ══
    (6, 12):  {"en": "Ethiopian Martyrs' Day (Yekatit 12)", "am": "የሰማዕታት ቀን (የካቲት 12)", "type": "holiday", "key": "yekatit_12"},
    (6, 23):  {"en": "Victory of Adwa Day", "am": "የዓድዋ ድል በዓል", "type": "holiday", "key": "adwa"},

    # ══ ሚያዝያ / Miyazia ══
    (8, 27):  {"en": "Patriots' Victory Day", "am": "የአርበኞች (የድል) ቀን", "type": "holiday", "key": "patriots_day"},

    # ══ ግንቦት / Ginbot ══
    (9, 20):  {"en": "Downfall of Derg Regime", "am": "የደርግ የወደቀበት ቀን (ግንቦት 20)", "type": "holiday", "key": "derg_downfall"},

    # ══ ጳጉሜ / Pagume ══
    (13, 1):  {"en": "Pagume Start", "am": "ጳጉሜ ይጀምራል", "type": "special", "key": "pagume"},
    (13, 5):  {"en": "Pagume 5 (End of Year)", "am": "ጳጉሜ 5", "type": "special", "key": "pagume"},
    (13, 6):  {"en": "Pagume 6 (Leap Year)", "am": "ጳጉሜ 6 (ዘመነ ሉቃስ)", "type": "special", "key": "pagume"},
}


# Moveable holidays mapped by (eth_year, eth_month, eth_day)
MOVEABLE_HOLIDAYS = {
    # ── 2015 EC (2022/2023 GC) ──
    (2015, 1, 16):  {"en": "Mawlid", "am": "መውሊድ", "type": "holiday", "key": "mawlid"},
    (2015, 8, 6):   {"en": "Ethiopian Good Friday (Siklet)", "am": "ስቅለት", "type": "holiday", "key": "siklet"},
    (2015, 8, 8):   {"en": "Ethiopian Easter (Fasika)", "am": "ፋሲካ", "type": "holiday", "key": "fasika"},
    (2015, 8, 13):  {"en": "Eid al-Fitr", "am": "ዒድ አል ፊጥር", "type": "holiday", "key": "eid_fitr"},
    (2015, 10, 21): {"en": "Eid al-Adha", "am": "ዒድ አል አድሃ", "type": "holiday", "key": "eid_adha"},

    # ── 2016 EC (2023/2024 GC) ──
    (2016, 1, 16):  {"en": "Mawlid", "am": "መውሊድ", "type": "holiday", "key": "mawlid"},
    (2016, 8, 2):   {"en": "Eid al-Fitr", "am": "ዒድ አል ፊጥር", "type": "holiday", "key": "eid_fitr"},
    (2016, 8, 25):  {"en": "Ethiopian Good Friday (Siklet)", "am": "ስቅለት", "type": "holiday", "key": "siklet"},
    (2016, 8, 27):  {"en": "Ethiopian Easter (Fasika)", "am": "ፋሲካ", "type": "holiday", "key": "fasika"},
    (2016, 10, 9):  {"en": "Eid al-Adha", "am": "ዒድ አል አድሃ", "type": "holiday", "key": "eid_adha"},

    # ── 2017 EC (2024/2025 GC) ──
    (2017, 1, 5):   {"en": "Mawlid", "am": "መውሊድ", "type": "holiday", "key": "mawlid"},
    (2017, 7, 21):  {"en": "Eid al-Fitr", "am": "ዒድ አል ፊጥር", "type": "holiday", "key": "eid_fitr"},
    (2017, 8, 10):  {"en": "Ethiopian Good Friday (Siklet)", "am": "ስቅለት", "type": "holiday", "key": "siklet"},
    (2017, 8, 12):  {"en": "Ethiopian Easter (Fasika)", "am": "ፋሲካ", "type": "holiday", "key": "fasika"},
    (2017, 9, 29):  {"en": "Eid al-Adha", "am": "ዒድ አል አድሃ", "type": "holiday", "key": "eid_adha"},
    (2017, 12, 29): {"en": "Mawlid", "am": "መውሊድ", "type": "holiday", "key": "mawlid"},

    # ── 2018 EC (2025/2026 GC) ──
    (2018, 7, 11):  {"en": "Eid al-Fitr", "am": "ዒድ አል ፊጥር", "type": "holiday", "key": "eid_fitr"},
    (2018, 8, 2):   {"en": "Ethiopian Good Friday (Siklet)", "am": "ስቅለት", "type": "holiday", "key": "siklet"},
    (2018, 8, 4):   {"en": "Ethiopian Easter (Fasika)", "am": "ፋሲካ", "type": "holiday", "key": "fasika"},
    (2018, 9, 19):  {"en": "Eid al-Adha", "am": "ዒድ አል አድሃ", "type": "holiday", "key": "eid_adha"},
    (2018, 12, 20): {"en": "Mawlid", "am": "መውሊድ", "type": "holiday", "key": "mawlid"},

    # ── 2019 EC (2026/2027 GC) ──
    (2019, 6, 30):  {"en": "Eid al-Fitr", "am": "ዒድ አል ፊጥር", "type": "holiday", "key": "eid_fitr"},
    (2019, 8, 22):  {"en": "Ethiopian Good Friday (Siklet)", "am": "ስቅለት", "type": "holiday", "key": "siklet"},
    (2019, 8, 24):  {"en": "Ethiopian Easter (Fasika)", "am": "ፋሲካ", "type": "holiday", "key": "fasika"},
    (2019, 9, 9):   {"en": "Eid al-Adha", "am": "ዒድ አል አድሃ", "type": "holiday", "key": "eid_adha"},
    (2019, 12, 9):  {"en": "Mawlid", "am": "መውሊድ", "type": "holiday", "key": "mawlid"},

    # ── 2020 EC (2027/2028 GC) ──
    (2020, 6, 18):  {"en": "Eid al-Fitr", "am": "ዒድ አል ፊጥር", "type": "holiday", "key": "eid_fitr"},
    (2020, 8, 6):   {"en": "Ethiopian Good Friday (Siklet)", "am": "ስቅለት", "type": "holiday", "key": "siklet"},
    (2020, 8, 8):   {"en": "Ethiopian Easter (Fasika)", "am": "ፋሲካ", "type": "holiday", "key": "fasika"},
    (2020, 8, 27):  {"en": "Eid al-Adha", "am": "ዒድ አል አድሃ", "type": "holiday", "key": "eid_adha"},
    (2020, 11, 27): {"en": "Mawlid", "am": "መውሊድ", "type": "holiday", "key": "mawlid"},

    # ── 2021 EC (2028/2029 GC) ──
    (2021, 6, 8):   {"en": "Eid al-Fitr", "am": "ዒድ አል ፊጥር", "type": "holiday", "key": "eid_fitr"},
    (2021, 7, 28):  {"en": "Ethiopian Good Friday (Siklet)", "am": "ስቅለት", "type": "holiday", "key": "siklet"},
    (2021, 7, 30):  {"en": "Ethiopian Easter (Fasika)", "am": "ፋሲካ", "type": "holiday", "key": "fasika"},
    (2021, 8, 16):  {"en": "Eid al-Adha", "am": "ዒድ አል አድሃ", "type": "holiday", "key": "eid_adha"},
    (2021, 11, 17): {"en": "Mawlid", "am": "መውሊድ", "type": "holiday", "key": "mawlid"},

    # ── 2022 EC (2029/2030 GC) ──
    (2022, 5, 27):  {"en": "Eid al-Fitr", "am": "ዒድ አል ፊጥር", "type": "holiday", "key": "eid_fitr"},
    (2022, 8, 5):   {"en": "Eid al-Adha", "am": "ዒድ አል አድሃ", "type": "holiday", "key": "eid_adha"},
    (2022, 8, 18):  {"en": "Ethiopian Good Friday (Siklet)", "am": "ስቅለት", "type": "holiday", "key": "siklet"},
    (2022, 8, 20):  {"en": "Ethiopian Easter (Fasika)", "am": "ፋሲካ", "type": "holiday", "key": "fasika"},
    (2022, 11, 6):  {"en": "Mawlid", "am": "መውሊድ", "type": "holiday", "key": "mawlid"},

    # ── 2023 EC (2030/2031 GC) ──
    (2023, 5, 16):  {"en": "Eid al-Fitr", "am": "ዒድ አል ፊጥር", "type": "holiday", "key": "eid_fitr"},
    (2023, 7, 25):  {"en": "Eid al-Adha", "am": "ዒድ አል አድሃ", "type": "holiday", "key": "eid_adha"},
    (2023, 8, 3):   {"en": "Ethiopian Good Friday (Siklet)", "am": "ስቅለት", "type": "holiday", "key": "siklet"},
    (2023, 8, 5):   {"en": "Ethiopian Easter (Fasika)", "am": "ፋሲካ", "type": "holiday", "key": "fasika"},
    (2023, 10, 26): {"en": "Mawlid", "am": "መውሊድ", "type": "holiday", "key": "mawlid"},

    # ── 2024 EC (2031/2032 GC) ──
    (2024, 5, 5):   {"en": "Eid al-Fitr", "am": "ዒድ አል ፊጥር", "type": "holiday", "key": "eid_fitr"},
    (2024, 7, 14):  {"en": "Eid al-Adha", "am": "ዒድ አል አድሃ", "type": "holiday", "key": "eid_adha"},
    (2024, 8, 22):  {"en": "Ethiopian Good Friday (Siklet)", "am": "ስቅለት", "type": "holiday", "key": "siklet"},
    (2024, 8, 24):  {"en": "Ethiopian Easter (Fasika)", "am": "ፋሲካ", "type": "holiday", "key": "fasika"},
    (2024, 10, 15): {"en": "Mawlid", "am": "መውሊድ", "type": "holiday", "key": "mawlid"},
}


def get_holiday_description(info_dict: dict, lang: str = "am") -> str:
    """Returns historical/cultural description for a holiday info dictionary."""
    if not info_dict:
        return ""
    key = info_dict.get("key")
    if key and key in HOLIDAY_DESCRIPTIONS:
        return HOLIDAY_DESCRIPTIONS[key].get(lang, "")
    return ""


def get_month_holidays(eth_month: int, eth_year: int = None) -> dict:
    """Returns all holidays for an Ethiopian month as {day: info_dict}."""
    holidays = {}

    # 1. Fixed Ethiopian Holidays
    for (m, d), info in FIXED_ETHIOPIAN_HOLIDAYS.items():
        if m == eth_month:
            info_copy = dict(info)
            info_copy["desc_am"] = get_holiday_description(info, "am")
            info_copy["desc_en"] = get_holiday_description(info, "en")
            holidays[d] = info_copy

    # 2. Fixed Gregorian Holiday: May 1 (Workers' Day)
    if eth_year:
        try:
            gd1, gm1, gy1 = eth_to_greg(1, eth_month, eth_year)
            w_d, w_m, w_y = greg_to_eth(1, 5, gy1)
            if w_m == eth_month:
                info_copy = {
                    "en": "International Workers' Day",
                    "am": "የዓለም ሠራተኞች (የላብ አደሮች) ቀን",
                    "type": "holiday",
                    "key": "workers_day"
                }
                info_copy["desc_am"] = get_holiday_description(info_copy, "am")
                info_copy["desc_en"] = get_holiday_description(info_copy, "en")
                holidays[w_d] = info_copy
        except Exception:
            pass

    # 3. Moveable Holidays
    if eth_year:
        for (y, m, d), info in MOVEABLE_HOLIDAYS.items():
            if y == eth_year and m == eth_month:
                info_copy = dict(info)
                info_copy["desc_am"] = get_holiday_description(info, "am")
                info_copy["desc_en"] = get_holiday_description(info, "en")
                holidays[d] = info_copy

    return holidays


def get_day_type(eth_month: int, eth_day: int, eth_year: int = None) -> dict | None:
    """Returns holiday info dict for a specific Ethiopian date, or None."""
    month_hols = get_month_holidays(eth_month, eth_year)
    return month_hols.get(eth_day)


# Emoji mapping by holiday type
TYPE_EMOJI = {
    "holiday": "🔴",  # Public Holiday (Offices closed)
    "closure": "🟠",  # Early closure or half-day
    "special": "🟢",  # Special religious / national observance
}

TYPE_LABEL = {
    "en": {
        "holiday": "Public Holiday",
        "closure": "Office Closure",
        "special": "Special Observance",
    },
    "am": {
        "holiday": "የህዝብ በዓል",
        "closure": "ቢሮ ዝጋ",
        "special": "ልዩ ቀን",
    }
}
