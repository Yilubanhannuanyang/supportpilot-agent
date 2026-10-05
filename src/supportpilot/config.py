import os

from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents import OpenAIChatCompletionsModel, set_tracing_disabled

# 从项目根目录的 .env 读取配置（DEEPSEEK_API_KEY / DEEPSEEK_BASE_URL / DEEPSEEK_MODEL）
load_dotenv()

# 关闭 SDK 内置的 OpenAI 追踪上报：本项目改用 DeepSeek 端点，且不上报外部遥测
set_tracing_disabled(True)


def create_model():
    """构造指向 DeepSeek 的 OpenAI 兼容模型实例。

    DeepSeek 提供 OpenAI 兼容接口，因此复用 SDK 的 OpenAIChatCompletionsModel，
    只把 base_url 与 api_key 换成 DeepSeek 的即可。
    """

    api_key = os.getenv("DEEPSEEK_API_KEY")
    base_url = os.getenv("DEEPSEEK_BASE_URL")
    model_name = os.getenv("DEEPSEEK_MODEL")

    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
    )

    return OpenAIChatCompletionsModel(
        model=model_name,
        openai_client=client,
    )
