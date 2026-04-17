from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    uis_sip_host: str = "sip.uiscom.ru"
    uis_sip_user: str = ""
    uis_sip_password: str = ""
    uis_caller_id: str = ""

    openai_api_key: str
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4.1-mini"

    elevenlabs_api_key: str
    elevenlabs_voice_id: str
    elevenlabs_model: str = "eleven_v3"

    deepgram_api_key: str

    audiosocket_host: str = "0.0.0.0"
    audiosocket_port: int = 4444

    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
