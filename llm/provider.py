from typing import Dict, Any, AsyncGenerator, List
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from config.settings import OPENAI_API_KEY, DEFAULT_MODEL
from langchain.llms import OpenAI
# Updated language-specific system prompts
LANGUAGE_PROMPTS = {
    "en": (
        "You are a precise assistant answering questions strictly based on the content of the YouTube video transcript provided. "
        "If the answer is not clearly stated in the transcript, say you cannot find the answer. "
        "Do not guess or add unrelated information. Only use the transcript to answer. Stay on-topic, concise, and evidence-based."
    ),
    "ar": (
        "أنت مساعد دقيق تجيب على الأسئلة فقط بناءً على محتوى نص الفيديو من يوتيوب. "
        "إذا لم يكن الجواب مذكورًا بوضوح في النص، قل أنك لا تستطيع العثور عليه. "
        "لا تخمن أو تضف معلومات غير متعلقة. استخدم النص فقط للإجابة وكن دقيقًا."
    ),
    "es": (
        "Eres un asistente preciso que responde estrictamente con base en el contenido del video de YouTube. "
        "Si la respuesta no está claramente indicada en la transcripción, di que no puedes encontrarla. "
        "No inventes información ni salgas del tema. Usa solo la transcripción."
    ),
    "it": (
        "Sei un assistente preciso che risponde solo in base al contenuto del video YouTube. "
        "Se la risposta non è chiaramente indicata nella trascrizione, dichiara di non poterla trovare. "
        "Non indovinare né aggiungere informazioni non pertinenti. Usa solo la trascrizione."
    ),
    "sv": (
        "Du är en noggrann assistent som bara svarar baserat på innehållet i YouTube-videons transkript. "
        "Om svaret inte tydligt framgår, säg att du inte kan hitta det. Gissa inte och håll dig till ämnet."
    ),
}

class LLMProvider:
    def __init__(self):
        self.api_key = OPENAI_API_KEY

    def _get_model(self, temperature: float, model: str, streaming: bool = False):
        if "instruct" in model:
            return OpenAI(
            model_name=model,
            temperature=temperature,
            openai_api_key=self.api_key,
        )
        else:
            return ChatOpenAI(
            model_name=model,
            temperature=temperature,
            openai_api_key=self.api_key,
            streaming=streaming
         )

    async def generate(
        self,
        prompt: str,
        context_data: List[Dict[str, Any]],
        video_id: str = "",
        model: str = DEFAULT_MODEL,
        max_tokens: int = 400,
        temperature: float = 0.2
    ) -> Dict[str, Any]:
        context_text = "\n\n".join([item["content"] for item in context_data])
        lang = context_data[0].get("language", "en") if context_data else "en"
        system_message = LANGUAGE_PROMPTS.get(lang, LANGUAGE_PROMPTS["en"])

        messages = [
            SystemMessage(content=system_message),
            HumanMessage(content=f"{prompt}\n\nTranscript:\n{context_text}")
        ]

        llm = self._get_model(temperature=temperature, model=model, streaming=False)
        response = await llm.apredict_messages(messages)

        return {"response": response.content}

    async def stream_response(
        self,
        prompt: str,
        context_data: List[Dict[str, Any]],
        video_id: str = "",
        model: str = DEFAULT_MODEL,
        max_tokens: int = 800,
        temperature: float = 0.2
    ) -> AsyncGenerator[Dict[str, Any], None]:
        context_text = "\n\n".join([item["content"] for item in context_data])
        lang = context_data[0].get("language", "en") if context_data else "en"
        system_message = LANGUAGE_PROMPTS.get(lang, LANGUAGE_PROMPTS["en"])

        messages = [
            SystemMessage(content=system_message),
            HumanMessage(content=f"{prompt}\n\nTranscript:\n{context_text}")
        ]

        llm = self._get_model(temperature=temperature, model=model, streaming=True)
        full_response = ""

        async for chunk in llm.astream(messages):
            if isinstance(chunk, AIMessage):
                full_response += chunk.content
                yield {
                    "token": chunk.content,
                    "is_complete": False
                }

        yield {
            "token": "",
            "is_complete": True,
            "processed_response": full_response
        }

    async def summarize(
        self,
        content: str,
        length: str = "medium",
        model: str = DEFAULT_MODEL
    ) -> str:
        max_tokens_map = {
            "short": 100,
            "medium": 250,
            "detailed": 500
        }

        instructions_map = {
            "short": {
                "en": "Summarize the video briefly in 2-3 sentences.",
                "ar": "لخص محتوى الفيديو بإيجاز في جملتين أو ثلاث.",
                "es": "Resume el contenido del video en 2 o 3 frases.",
                "it": "Riassumi brevemente il contenuto del video in 2 o 3 frasi.",
                "sv": "Sammanfatta videons innehåll kortfattat i 2–3 meningar."
            },
            "medium": {
                "en": "Summarize the main points of the video.",
                "ar": "لخص النقاط الرئيسية في الفيديو.",
                "es": "Resume los puntos principales del video.",
                "it": "Riassumi i punti principali del video.",
                "sv": "Sammanfatta huvudpunkterna i videon."
            },
            "detailed": {
                "en": "Write a detailed summary of the video content.",
                "ar": "اكتب ملخصًا مفصلًا لمحتوى الفيديو.",
                "es": "Escribe un resumen detallado del contenido del video.",
                "it": "Scrivi un riassunto dettagliato del contenuto del video.",
                "sv": "Skriv en detaljerad sammanfattning av videons innehåll."
            }
        }

        lang = "en"
        if "ال" in content: lang = "ar"
        elif " el " in content or " la " in content: lang = "es"
        elif " il " in content or " lo " in content: lang = "it"
        elif " och " in content or " att " in content: lang = "sv"

        instruction = instructions_map.get(length, instructions_map["medium"]).get(lang, instructions_map["medium"]["en"])
        max_tokens = max_tokens_map.get(length, 250)

        messages = [
            SystemMessage(content=instruction),
            HumanMessage(content=f"Transcript:\n{content}")
        ]

        llm = self._get_model(temperature=0.3, model=model, streaming=False)
        response = await llm.apredict_messages(messages)
        return response.content.strip()

    async def answer(
        self,
        question: str,
        context: str,
        model: str = DEFAULT_MODEL
    ) -> str:
        lang = "en"
        system_message = LANGUAGE_PROMPTS.get(lang, LANGUAGE_PROMPTS["en"])

        messages = [
            SystemMessage(content=system_message),
            HumanMessage(content=f"Question: {question}\n\nTranscript:\n{context}")
        ]

        llm = self._get_model(temperature=0.2, model=model, streaming=False)
        response = await llm.apredict_messages(messages)
        return response.content.strip()
    
    async def translate(self, text: str, target_lang: str) -> str:
        prompt = f"Translate the following text to {target_lang}:\n\n{text}"
        try:
            return await self.generate_raw(prompt=prompt, model="gpt-3.5-turbo", max_tokens=400)
        except Exception as e:
            print(f"[translate] Error: {e}")
            return text

    async def generate_raw(self, prompt: str, model: str = DEFAULT_MODEL, max_tokens: int = 400) -> str:
        llm = ChatOpenAI(
            model_name=model,
            temperature=0,
            openai_api_key=self.api_key
        )
        return await llm.apredict(prompt)