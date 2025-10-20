import os
from dotenv import load_dotenv, find_dotenv
from fastapi import APIRouter, HTTPException
import tabula
import langchain
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import ResponseSchema
from langchain.output_parsers import StructuredOutputParser
from json import loads, dumps
import json
from bs4 import BeautifulSoup
import pandas as pd
import glob

_ = load_dotenv(find_dotenv())



def get_latest_pdf():
    """Get the most recent PDF file (excluding example.pdf)"""
    all_pdfs = glob.glob("*.pdf")
    # Filter out example.pdf and get newest
    user_pdfs = [pdf for pdf in all_pdfs]
    
    if user_pdfs:
        # Get the most recently modified PDF
        latest_pdf = max(user_pdfs, key=os.path.getmtime)
        print(f"Processing latest PDF: {latest_pdf}")
        return latest_pdf
    else:
        # Fallback to example.pdf if no user PDFs found
        print("No user PDFs found, using example.pdf")
        return "example.pdf"

pdf_path = get_latest_pdf()

chat = ChatGoogleGenerativeAI(
    model = "gemini-2.5-flash",
    google_api_key=os.environ['PATH_TO_GEMINI'],
    temperature=0.0,
)


def strip_html_text(htmltext):
        if not htmltext:
            return None
        soup = BeautifulSoup(htmltext, 'lxml')
        clean_text = soup.get_text(' ' ,strip=True)
        return clean_text if clean_text.strip() else None

def work_pdf():
    # Get the latest PDF each time this function is called
    current_pdf = get_latest_pdf()
    DataFrame = tabula.read_pdf(current_pdf, lattice=True)
    
    if DataFrame:
        combine_df = pd.concat(DataFrame, ignore_index=True)
        result = strip_html_text(combine_df.to_string())
        
        return result
    
def gemini_queries():
    table_instructions = '''\
    You are an expert procurement analyst specializing in Swiss public tenders. 
    Analyze the following table data and generate 5 highly targeted search queries
    that would find matching tenders on the Swiss public procurement platform.

    *REQUIREMENTS:*
    1. Generate exactly 5 short, focused queries (max 10 words for each)
    2. Focus on WHAT services/products would be procured, not individual line items
    3. Include relevant CPV codes when identifiable
    4. Think about tender categories that would require these materials/services
    5. Use Swiss procurement terminology

    *ANALYSIS FOCUS*:
    - What type of organization would procure these items?
    - What broader project/service do these items support?
    - What CPV categories do these items fall under?

    **OUTPUT FORMAT** - Return ONLY this JSON structure:
    ***JSON***
    {{
            "q1": "your_first_query_here",
            "q2": "your_second_query_here", 
            "q3": "your_third_query_here",
            "q4": "your_fourth_query_here",
            "q5": "your_fifth_query_here"
    }}

    *EXAMPLE GOOD QUERIES*:
    - "IT services 72000000 software licenses"
    - "office furniture 39100000 workplace equipment"
    - "construction materials 44000000 building supplies"

    **PDF TABLE DATA:**
    {DataFrame}

    Generate 5 targeted queries that would find tenders requiring these items:

    '''

    query_dict = {}
    data = work_pdf()

    prompt_template = ChatPromptTemplate.from_template(template=table_instructions)

    schemas = [ResponseSchema(name="q1", description="First query"),
               ResponseSchema(name="q2", description="Second query"),
               ResponseSchema(name="q3", description="Third query"),
               ResponseSchema(name="q4", description="Forth query"),
               ResponseSchema(name="q5", description="Fifth query")]

    parser = StructuredOutputParser.from_response_schemas(schemas)

    mssg =  prompt_template.format_messages(DataFrame=data)

    response = chat.invoke(mssg)
    query_dict = parser.parse(response.content)

    return query_dict


def pdf_matching():
    queri_dct = gemini_queries()
    return queri_dct


'''try :
    query_dict = json.loads(response.content)
except json.JSONDecodeError:
    print("No Json Values")
'''