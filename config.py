# =====================  SOURCES  =====================
# "filter": True  -> for general Persian sports sites: only post items that
# mention a top-league club/league/known player (so Iranian-league news is skipped).
NEWS_FEEDS = [
    # English / international
    {"name": "BBC Sport", "url": "https://feeds.bbci.co.uk/sport/football/rss.xml"},
    {"name": "The Guardian", "url": "https://www.theguardian.com/football/rss"},
    {"name": "Sky Sports", "url": "https://www.skysports.com/rss/12040"},
    {"name": "ESPN FC", "url": "https://www.espn.com/espn/rss/soccer/news"},
    {"name": "Football Italia", "url": "https://football-italia.net/feed/"},
    # Persian (not verified from my side - open each URL in a browser once.
    # Iranian sites sometimes block foreign servers like GitHub's; if so, remove them.)
    {"name": "ورزش سه", "url": "https://www.varzesh3.com/rss/all", "filter": True},
    {"name": "خبر ورزشی", "url": "https://www.khabarvarzeshi.com/rss", "filter": True},
]

# Journalists on X (handle without @)
X_ACCOUNTS = [
    "FabrizioRomano",
    "David_Ornstein",
    "MatteMoretto",
    "Plettigoal",
    "JacobsBen",
    "gerardromero",
]

# Nitter mirrors used to read X as RSS. Free but unreliable, and GitHub's servers
# are often blocked by them. Add working instances here (tried in order).
NITTER_INSTANCES = [
    "https://nitter.net",
]

# =====================  RUN BEHAVIOUR  =====================
MAX_AGE_HOURS = 6            # ignore items older than this
MAX_POSTS_PER_RUN = 8        # posts per hourly run
POST_GAP_SECONDS = (20, 45)  # random pause between posts (looks natural, spreads the run)
RUN_BUDGET_SECONDS = 360     # hard stop for posting after ~6 minutes
IMAGE_PROBABILITY = 0.3      # share of news posts that get a picture (if one exists)

# =====================  MORNING DIGEST  =====================
TIMEZONE = "Asia/Tehran"          # times shown in the digest
TIMEZONE_LABEL = "به وقت تهران"
# ESPN league codes (unofficial, no API key). Add/remove as you like.
LEAGUES = [
    # (code, Persian name, emoji, hashtag)
    ("eng.1", "لیگ برتر انگلیس", "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "#لیگ_برتر_انگلیس"),
    ("esp.1", "لالیگا", "🇪🇸", "#لالیگا"),
    ("ita.1", "سری آ", "🇮🇹", "#سری_آ"),
    ("ger.1", "بوندسلیگا", "🇩🇪", "#بوندسلیگا"),
    ("fra.1", "لوشامپیونه", "🇫🇷", "#لوشامپیونه"),
    ("uefa.champions", "لیگ قهرمانان اروپا", "🏆", "#لیگ_قهرمانان_اروپا"),
    ("uefa.europa", "لیگ اروپا", "🏆", "#لیگ_اروپا"),
    ("fifa.world", "جام جهانی", "🌍", "#جام_جهانی"),
]

# Fixed Persian names for clubs (anything missing is auto-translated).
TEAM_FA = {
    "Manchester United": "منچستر یونایتد", "Manchester City": "منچستر سیتی",
    "Liverpool": "لیورپول", "Arsenal": "آرسنال", "Chelsea": "چلسی",
    "Tottenham Hotspur": "تاتنهام", "Newcastle United": "نیوکاسل",
    "Aston Villa": "استون ویلا", "West Ham United": "وست هام",
    "Real Madrid": "رئال مادرید", "Barcelona": "بارسلونا",
    "Atlético Madrid": "اتلتیکو مادرید", "Athletic Club": "اتلتیک بیلبائو",
    "Sevilla": "سویا", "Villarreal": "ویارئال", "Real Sociedad": "رئال سوسیداد",
    "Bayern Munich": "بایرن مونیخ", "Borussia Dortmund": "دورتموند",
    "Bayer Leverkusen": "لورکوزن", "RB Leipzig": "لایپزیگ",
    "Juventus": "یوونتوس", "Inter Milan": "اینتر", "AC Milan": "میلان",
    "Napoli": "ناپولی", "AS Roma": "رم", "Lazio": "لاتزیو", "Atalanta": "آتالانتا",
    "Paris Saint-Germain": "پاری سن ژرمن", "Marseille": "مارسی",
    "Monaco": "موناکو", "Lyon": "لیون", "Lille": "لیل",
    "Benfica": "بنفیکا", "Porto": "پورتو", "Ajax": "آژاکس",
}

# =====================  HASHTAGS  =====================
# (regex matched against original + translated text, hashtag)
TEAM_TAGS = [
    (r"\bReal Madrid\b|رئال مادرید", "#رئال_مادرید"),
    (r"\bBarcelona\b|\bBarça\b|بارسلونا", "#بارسلونا"),
    (r"\bAtl[eé]tico\b|اتلتیکو", "#اتلتیکو_مادرید"),
    (r"\bMan(?:chester)? (?:United|Utd)\b|منچستر یونایتد", "#منچستر_یونایتد"),
    (r"\bMan(?:chester)? City\b|منچستر سیتی", "#منچستر_سیتی"),
    (r"\bLiverpool\b|لیورپول", "#لیورپول"),
    (r"\bArsenal\b|آرسنال", "#آرسنال"),
    (r"\bChelsea\b|چلسی", "#چلسی"),
    (r"\bTottenham\b|\bSpurs\b|تاتنهام", "#تاتنهام"),
    (r"\bNewcastle\b|نیوکاسل", "#نیوکاسل"),
    (r"\bAston Villa\b|استون ویلا", "#استون_ویلا"),
    (r"\bBayern\b|بایرن", "#بایرن_مونیخ"),
    (r"\bDortmund\b|دورتموند", "#دورتموند"),
    (r"\bLeverkusen\b|لورکوزن", "#لورکوزن"),
    (r"\bJuventus\b|\bJuve\b|یوونتوس", "#یوونتوس"),
    (r"\bInter\b(?! Miami)|اینتر", "#اینتر"),
    (r"\bAC Milan\b|(?<!Inter )\bMilan\b|آث میلان", "#میلان"),
    (r"\bNapoli\b|ناپولی", "#ناپولی"),
    (r"\bAS Roma\b|\bRoma\b", "#رم"),
    (r"\bPSG\b|\bParis Saint-Germain\b|پاری سن ژرمن", "#پاری_سن_ژرمن"),
    (r"\bMessi\b|مسی", "#مسی"),
    (r"\bRonaldo\b|رونالدو", "#رونالدو"),
    (r"\bMbapp[eé]\b|امباپه", "#امباپه"),
    (r"\bHaaland\b|هالند", "#هالند"),
    (r"\bSalah\b|محمد صلاح", "#صلاح"),
    (r"\bYamal\b|یامال", "#یامال"),
    (r"\bBellingham\b|بلینگهام", "#بلینگهام"),
    (r"\bVin[ií]cius\b|وینیسیوس", "#وینیسیوس"),
    (r"\bTaremi\b|طارمی", "#طارمی"),
    (r"\bAzmoun\b|آزمون", "#آزمون"),
]
LEAGUE_TAGS = [
    (r"\bPremier League\b|لیگ برتر انگلیس", "#لیگ_برتر_انگلیس"),
    (r"\bLa Liga\b|لالیگا", "#لالیگا"),
    (r"\bSerie A\b|سری ?آ", "#سری_آ"),
    (r"\bBundesliga\b|بوندسلیگا", "#بوندسلیگا"),
    (r"\bLigue 1\b|لوشامپیونه", "#لوشامپیونه"),
    (r"\bChampions League\b|لیگ قهرمانان", "#لیگ_قهرمانان_اروپا"),
    (r"\bEuropa League\b|لیگ اروپا", "#لیگ_اروپا"),
    (r"\bWorld Cup\b|جام جهانی", "#جام_جهانی"),
]
TOPIC_TAGS = [
    (r"\b(transfer|signing|bid for|loan deal|release clause|here we go|medical)\b|نقل و انتقالات", "#نقل_و_انتقالات"),
    (r"\b(rumou?rs?|reportedly|linked with|interested in)\b|شایعه", "#شایعه"),
    (r"\b(injur(?:y|ed)|ruled out)\b|مصدومیت", "#مصدومیت"),
]
