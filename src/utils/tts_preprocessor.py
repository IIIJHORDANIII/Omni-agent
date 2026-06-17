import re

TTS_PRONUNCIATION_MAP = {
    "API": "ÊI-PÍ-ÁI",
    "JSON": "DJÊI-SÃN",
    "URL": "ÊU-ÁR-ÉL",
    "HTTP": "ÊITCH-TÍ-PÍ",
    "HTTPS": "ÊITCH-TÍ-PÍ-ÉS",
    "SQL": "ÉS-QUÊ-ÉL",
    "CSS": "SÍ-ÉS-ÉS",
    "HTML": "ÊITCH-TÍ-ÉM-ÉL",
    "CPU": "SÍ-PÍ-ÊU",
    "RAM": "RÉM",
    "GPU": "GÍ-PÍ-ÊU",
    "SSD": "ÉS-ÉS-DÍ",
    "HDD": "ÊITCH-DÍ-DÍ",
    "IDE": "ÁI-DÍ-Í",
    "CLI": "SÍ-ÉL-ÁI",
    "CRUD": "CRÚD",
    "REST": "RÉST",
    "SSH": "ÉS-ÉS-ÊITSH",
    "VPN": "VÊ-PÍ-ÉN",
    "IP": "Í-PÍ",
    "DNS": "DÍ-ÉN-ÉS",
    "LLM": "ÉL-ÉL-ÉM",
    "GPT": "GÍ-PÍ-TÍ",
    "PDF": "PÍ-DÍ-ÉF",
    "SDK": "ÉS-DÍ-KÊI",
    "OAUTH": "OUÁUT",
    "JWT": "DJÊI-DÁBUL-TÍ",
    "UUID": "ÊU-ÊU-Í-DÍ",
    "IoT": "ÁI-Ó-TÍ",
    "ML": "ÉM-ÉL",
    "AI": "ÊI-ÁI",
    "VR": "VÍ-ÁR",
    "AR": "ÊI-ÁR",
    "auth": "ÓT",
    "devops": "DÉVÓPS",
    "CI/CD": "SÍ-Í-CÍ-DÍ",
    "VS Code": "VÍ-ÉS CÓDE",
    "GitHub": "GÍT-HÃB",
    "GitLab": "GÍT-LÉB",
    "Git": "GÍTI",
    "Docker": "DÓQUER",
    "TypeScript": "TÁIP-SCRIPT",
    "JavaScript": "DJÁVA-SCRIPT",
    "Python": "PÁITON",
    "Node.js": "NÓDE DJÉIS",
    "React": "RÍ-ÉCT",
    "Vue.js": "VÍU DJÉIS",
    "Angular": "ÉNGULAR",
    "Webhook": "WÉBHÚK",
    "Framework": "FRÉIMUÓRK",
    "Backend": "BÉKEND",
    "Frontend": "FRÓNTEND",
    "Fullstack": "FÚLSTÉCK",
    "Deploy": "DEPLOY",
    "Commit": "COMMIT",
    "Merge": "MERGE",
    "Push": "PÚSH",
    "Pull": "PÚL",
    "Cache": "CÊSH",
    "Token": "TÔKEN",
    "Debug": "DÍBÁGUI",
    "Branch": "BRÉNTCH",
    "Sprint": "SPRÍNT",
    "Scrum": "SCRUM",
    "Kanban": "KÁNBAN",
    "Agile": "ÉDJAIL",
    "Staging": "STÉIGING",
    "Production": "PRODÁKSHON",
    "Cluster": "CLÁSTER",
    "Container": "CONTÊINER",
    "Microservice": "MÁICRO-SERVICE",
    "Endpoint": "ÉNDPOINT",
    "Database": "DÉITABÉIS",
    "Middleware": "MÍDOLUÉR",
    "Webhook": "WÉBHÚK",
    "Runtime": "RÚNTAIME",
    "Compiler": "COMPÁILER",
    "Interpreter": "INTERPRÉTER",
    "Callback": "CÓLBÉCK",
    "Promise": "PRÓMISE",
    "Async": "ÉISÍNC",
    "Await": "EUÉIT",
    "Thread": "THRÉD",
    "Daemon": "DÍMON",
    "Socket": "SÓQUET",
    "Buffer": "BÁFER",
    "Stream": "STRÍM",
    "Payload": "PÉILOUDE",
    "Benchmark": "BÉNTCHMÁRC",
    "Profiler": "PROFÁILER",
    "Template": "TÉMPLÉIT",
    "Snippet": "SNÍPPET",
    "Overlay": "OUVERLÉI",
    "Widget": "WÍDJET",
    "Layout": "LÉIAUT",
    "Router": "RÁUTER",
    "Builder": "BÍLDER",
    "Factory": "FÉCTORÍ",
    "Wrapper": "RÉPER",
    "Parser": "PÁRZER",
    "Mapper": "MÉPER",
    "Handler": "HÉNDLER",
    "Emitter": "IMITER",
    "Listener": "LÍSTENER",
    "Observer": "OBSÉRVER",
    "Singleton": "SÍNGLETON",
    "Pipeline": "PÁIPLÁINE",
    "Anders": "ÊNDERS",
    "Pull Request": "PÚL RI-QUÉST",
    "PR": "PÍ-ÁR",
    "Issue": "ÍCHIU",
    "Code Review": "CÓDE RI-VÍU",
    "Merge Request": "MÊRDJ RI-QUÉST",
    "Feature": "FÍ-TCHUR",
    "Bug": "BÃGUI",
    "Hotfix": "RÓT-FÍKS",
    "Deploy": "DI-PLÓI",
    "Build": "BÍLD",
    "Docker": "DÓ-QUER",
    "Cloud": "CLÁUDE",
    "Serverless": "SÉRVER-LÉSS",
    "Framework": "FRÊI-MUÓRK",
    "Library": "LÁI-BRERÍ",
    "Script": "SCRÍPTI",
    "App": "ÉP",
    "Software": "SÓFT-UÉR",
    "Hardware": "RÁRD-UÉR",
    "Developer": "DI-VÉ-LO-PER",
    "Dev": "DÉV",
    "Senior": "SÍ-NIOR",
    "Junior": "DJÚ-NIOR",
    "Pleno": "PLÊ-NU",
    "Refactor": "RI-FÉC-TOR",
    "Task": "TÉSKI",
    "Sprint": "SPRÍNTI",
    "Backlog": "BÉQUI-LÓGUI",
    "Layout": "LÊI-ÁUT",
    "UI": "I-Ú-ÁI",
    "UX": "I-Ú-ÉKS",
}


def preprocess_for_tts(text: str) -> str:
    if not text:
        return text

    result = text

    # Remove emojis (Unicode ranges for emojis)
    result = re.sub(r'[\U00010000-\U0010ffff]', '', result)
    
    result = re.sub(r'[*#_`~]', '', result)
    result = re.sub(r'\[.*?\]', '', result)
    result = re.sub(r'<(think|reasoning)>.*?</\1>', '', result, flags=re.DOTALL | re.IGNORECASE)

    sorted_terms = sorted(TTS_PRONUNCIATION_MAP.keys(), key=len, reverse=True)
    pattern = re.compile(
        r'\b(' + '|'.join(re.escape(term) for term in sorted_terms) + r')\b',
        re.IGNORECASE
    )

    def _replace(match):
        original = match.group(0)
        key = original.upper() if original.isupper() else original.title()
        if key in TTS_PRONUNCIATION_MAP:
            return TTS_PRONUNCIATION_MAP[key]
        if original.upper() in TTS_PRONUNCIATION_MAP:
            return TTS_PRONUNCIATION_MAP[original.upper()]
        return original

    result = pattern.sub(_replace, result)

    result = re.sub(r'\s{2,}', ' ', result)
    return result.strip()