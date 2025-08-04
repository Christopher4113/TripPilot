from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

from dotenv import load_dotenv

load_dotenv()
import os

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro",
    temperature=0.2,
    max_output_tokens=1024,
    api_key=GOOGLE_API_KEY
)

prompt = PromptTemplate(
    input_variables=["user_id", "username", "text"],
    template="Explain the concept of {text} in simple terms."
)

chain = LLMChain(llm=llm, prompt=prompt)

output = chain.run("12345", "john_doe", "quantum computing")
print(output)