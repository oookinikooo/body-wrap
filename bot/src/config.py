from dotenv import find_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=find_dotenv(),
                                      env_file_encoding="utf-8",
                                      extra="ignore")

    token: str = Field(validation_alias="TOKEN")
    admin_ids_str: str = Field(validation_alias="ADMIN_IDS")
    master_key: str = Field(default='', validation_alias="MASTER_KEY")

    @property
    def admin_ids(self):
        return [int(i) for i in self.admin_ids_str.split(",") if i and i.isdigit()]


config = Config()
