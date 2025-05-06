import os
from typing import List, Dict, Any, Optional
from langchain.agents import Tool, AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain.tools import BaseTool
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langdetect import detect

class TranslationTool(BaseTool):
    name = "translation_tool"
    description = "Useful for translating text from one language to another"
    
    def __init__(self, openai_api_key: str):
        super().__init__()
        self.api_key = openai_api_key
        self.llm = ChatOpenAI(
            model_name="gpt-3.5-turbo",
            temperature=0,
            openai_api_key=self.api_key
        )
    
    def _run(self, input_text: str, target_lang: str) -> str:
        try:
            source_lang = detect(input_text)
            messages = [
                SystemMessage(content=f"Translate the following text from {source_lang} to {target_lang}. Maintain the meaning and context."),
                HumanMessage(content=input_text)
            ]
            response = self.llm.predict_messages(messages)
            return response.content
        except Exception as e:
            return f"Translation failed: {str(e)}"

class LanguageDetectionTool(BaseTool):
    name = "language_detection_tool"
    description = "Detects the language of a given text"
    
    def _run(self, input_text: str) -> str:
        try:
            detected_lang = detect(input_text)
            return detected_lang
        except Exception as e:
            return f"Language detection failed: {str(e)}"

class TranslatorAgent:
    def __init__(self, openai_api_key: str):
        self.api_key = openai_api_key
        
        # Define tools
        self.translation_tool = TranslationTool(openai_api_key)
        self.language_detection_tool = LanguageDetectionTool()
        
        # Create tools list
        self.tools = [
            Tool(
                name="translation_tool",
                func=self.translation_tool._run,
                description="Translates text from one language to another. Input should be in format: 'text to translate | target_language_code'"
            ),
            Tool(
                name="language_detection_tool",
                func=self.language_detection_tool._run,
                description="Detects the language of a given text. Input should be the text to analyze."
            )
        ]
        
        # Create LLM for the agent
        self.llm = ChatOpenAI(
            model_name="gpt-3.5-turbo-16k",
            temperature=0,
            openai_api_key=self.api_key
        )
        
        # Create agent prompt
        self.prompt = PromptTemplate.from_template(
            """You are a translator agent that can detect languages and translate text.
            You have access to the following tools:
            
            {tools}
            
            Use the tools to fulfill the task at hand.
            
            For translation tasks:
            1. First detect the source language if not already known
            2. Then translate the text to the target language
            3. Return the translated text
            
            Use the appropriate tool based on the task.
            
            Human query: {input}
            
            {agent_scratchpad}
            """
        )
        
        # Create the agent
        self.agent = create_react_agent(self.llm, self.tools, self.prompt)
        self.agent_executor = AgentExecutor.from_agent_and_tools(
            agent=self.agent, 
            tools=self.tools, 
            verbose=True
        )

    async def process(self, text: str, target_lang: Optional[str] = None) -> Dict[str, Any]:
        """
        Process text through the agent to detect language and translate if needed
        
        Args:
            text: Text to process
            target_lang: Target language for translation (if None, will only detect language)
            
        Returns:
            Dict with results including detected language and translated text if applicable
        """
        if target_lang:
            task = f"Translate this text to {target_lang}: {text}"
        else:
            task = f"Detect the language of this text: {text}"
            
        result = await self.agent_executor.arun(task)
        return {
            "processed_text": result,
            "original_text": text,
            "target_language": target_lang
        }
