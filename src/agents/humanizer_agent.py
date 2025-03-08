"""Humanizer agent that makes content more engaging and natural."""

from typing import Dict, List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

class HumanizerAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4")
        self.humanize_prompt = PromptTemplate.from_template("""
            As an expert content humanizer, transform the following technical content into engaging, 
            conversational prose while maintaining accuracy and professionalism.
            
            Original content:
            {content}
            
            Brand voice guidelines:
            {brand_voice}
            
            Target audience:
            {target_audience}
            
            Follow these rules:
            1. Use active voice and direct language
            2. Add relevant analogies and examples
            3. Include conversational transitions
            4. Maintain technical accuracy
            5. Keep the brand voice consistent
            6. Optimize for readability
            
            Transformed content:
        """)
        
    def humanize_content(self, content: str, brand_voice: str, target_audience: str) -> str:
        """
        Transform content to be more human and engaging.
        
        Args:
            content: The technical content to humanize
            brand_voice: Guidelines for brand voice
            target_audience: Description of target audience
            
        Returns:
            Humanized content
        """
        chain = self.humanize_prompt | self.llm | StrOutputParser()
        
        try:
            return chain.invoke({
                "content": content,
                "brand_voice": brand_voice,
                "target_audience": target_audience
            })
        except Exception as e:
            print(f"Error during content humanization: {str(e)}")
            return content
            
    def add_storytelling_elements(self, content: str) -> str:
        """Add storytelling elements to make content more engaging."""
        storytelling_prompt = PromptTemplate.from_template("""
            Enhance this content with storytelling elements:
            1. Add a compelling hook
            2. Include relevant anecdotes
            3. Create narrative flow
            4. Add emotional resonance
            5. Maintain professional tone
            
            Content:
            {content}
            
            Enhanced content with storytelling:
        """)
        
        chain = storytelling_prompt | self.llm | StrOutputParser()
        
        try:
            return chain.invoke({"content": content})
        except Exception as e:
            print(f"Error adding storytelling elements: {str(e)}")
            return content
            
    def optimize_tone(self, content: str, target_tone: str) -> str:
        """
        Adjust content tone while maintaining message.
        
        Args:
            content: Content to adjust
            target_tone: Desired tone (e.g., "professional", "friendly", "technical")
            
        Returns:
            Content with adjusted tone
        """
        tone_prompt = PromptTemplate.from_template("""
            Adjust the tone of this content to be {target_tone} while 
            maintaining the core message and technical accuracy.
            
            Content:
            {content}
            
            Adjusted content:
        """)
        
        chain = tone_prompt | self.llm | StrOutputParser()
        
        try:
            return chain.invoke({
                "content": content,
                "target_tone": target_tone
            })
        except Exception as e:
            print(f"Error optimizing tone: {str(e)}")
            return content
            
    def add_engagement_elements(self, content: str) -> str:
        """Add elements to increase reader engagement."""
        elements = [
            self._add_questions(),
            self._add_callouts(),
            self._add_examples(),
            self._add_transitions()
        ]
        
        enhanced_content = content
        for element in elements:
            try:
                enhanced_content = element(enhanced_content)
            except Exception as e:
                print(f"Error adding engagement element: {str(e)}")
                
        return enhanced_content
        
    def _add_questions(self):
        """Add rhetorical questions to engage readers."""
        def add(content: str) -> str:
            prompt = PromptTemplate.from_template("""
                Add relevant rhetorical questions to engage readers:
                {content}
            """)
            chain = prompt | self.llm | StrOutputParser()
            return chain.invoke({"content": content})
        return add
        
    def _add_callouts(self):
        """Add important callouts and highlights."""
        def add(content: str) -> str:
            prompt = PromptTemplate.from_template("""
                Add important callouts and highlights using markdown:
                {content}
            """)
            chain = prompt | self.llm | StrOutputParser()
            return chain.invoke({"content": content})
        return add
        
    def _add_examples(self):
        """Add relevant real-world examples."""
        def add(content: str) -> str:
            prompt = PromptTemplate.from_template("""
                Add relevant real-world examples to illustrate points:
                {content}
            """)
            chain = prompt | self.llm | StrOutputParser()
            return chain.invoke({"content": content})
        return add
        
    def _add_transitions(self):
        """Add natural transitions between sections."""
        def add(content: str) -> str:
            prompt = PromptTemplate.from_template("""
                Add natural transitions between sections:
                {content}
            """)
            chain = prompt | self.llm | StrOutputParser()
            return chain.invoke({"content": content})
        return add
