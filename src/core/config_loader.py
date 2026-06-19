import os

def load_user_config():
    """Load user-specific configuration.

    This placeholder ensures required environment variables have defaults.
    Expand as needed.
    """
    required_keys = {
        "DEEPGRAM_API_KEY": "",
        "DEEPSEEK_API_KEY": "",
        "GITHUB_TOKEN": "",
        "LINEAR_API_KEY": "",
    }
    for key, default in required_keys.items():
        os.environ.setdefault(key, default)
