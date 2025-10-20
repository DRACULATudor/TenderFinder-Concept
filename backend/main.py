from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi import routing, Depends
from typing import List, Dict, Any, Optional, TYPE_CHECKING
import pandas as pd
import json
import os
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel
import math
import ast
import psycopg2 
from psycopg2.extras import Json, RealDictCursor
from psycopg2.pool import SimpleConnectionPool
import tantivy
import search
import tabula
from pdf_extractor import work_pdf, pdf_matching
import pdf_extractor
from search import search_index

#from auth import get_fb_user_base_on_token
@asynccontextmanager
async def lifespan(app: FastAPI):
    load_cache()
    from search import index_tenders, embed_index_search
    embed_index_search()
    index_tenders(tenders_manager.cache_tenders, tenders_manager.detailed_view_cache)
    yield 

app = FastAPI(title="TenderFinder API", description="API for SIMAP tender data", version="1.0.0", lifespan=lifespan)


#CORS middleware allows incoming request from the desired client(Front end locacl server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200"],  # Angular dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Tenders_cache:
    def __init__(self):
        self.cache_tenders : dict[str, Any] = {}
        self.detailed_view_cache : dict[str, dict] = {}
        self.last_update : Optional[datetime] = None
        self.currently_updating : bool = False

tenders_manager = Tenders_cache()




#SMPLE CONNECITON POOL IS THE sioimplest connection which is nmice and easy to use, can be scalabke, and i f anything will be switincg
#to a thread pool

# Pool for connections = Pre-borrowing space where connections are already made

conn_pool : SimpleConnectionPool = psycopg2.pool.SimpleConnectionPool (
    1, 20, #the numb of min and max connection for my api calls
    dbname="tenderdb",
    user="tender_usr",
    password="$teMP@Pass@word!",
    host="localhost"
)

def load_cache():

    conn = conn_pool.getconn()
    try :
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('SELECT * FROM tender_general_info')
        rows = cursor.fetchall()
        tenders_manager.cache_tenders = { row['id'] :dict(row) for row in rows }

        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('SELECT * FROM tender_detailed_view')
        rows = cursor.fetchall()

        tenders_manager.detailed_view_cache = {row['uniq_id']: dict(row) for row in rows}
        tenders_manager.last_update = datetime.now()
    except Exception as e:
        print(f'Exception caught: {e}')
    finally:
        conn_pool.putconn(conn)

@app.get("/")
async def root():
    return {
        
        "message": "TenderFinder API with SIMAP data", 
        "total_tenders": len(tenders_manager.cache_tenders),
        "last_update": tenders_manager.last_update.strftime("%b %d, %Y %I:%M %p"),
        "is_updating": tenders_manager.currently_updating
    }

@app.get("/tenders/welcome")
async def welcome_tenders():
    tender_list = list(tenders_manager.cache_tenders.values())
    welcome_only_tenders = tender_list[:20]
    return welcome_only_tenders

@app.get("/tenders/detailed_view/{tender_id}")
async def detailed_view(tender_id: str):
    """Get detailed tender information by tender ID"""
    try:
        # First try to get from cache
        if tender_id in tenders_manager.detailed_view_cache:
            return tenders_manager.detailed_view_cache[tender_id]
        

        #FALL BACK LOGIC
        # If not in cache, query database directly
        conn = conn_pool.getconn()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Based on the parser code, the mapping is:
            # - pub_id = publication_id from SIMAP
            # - uniq_id = tender_id from SIMAP
            
            # Try to find by uniq_id (which should match the tender_id)
            cursor.execute('SELECT * FROM tender_detailed_view WHERE uniq_id = %s', (tender_id,))
            detailed_row = cursor.fetchone()
            
            if detailed_row:
                detailed_data = dict(detailed_row)
                # Update cache for future requests
                tenders_manager.detailed_view_cache[tender_id] = detailed_data
                print(f"Found detailed data for tender_id {tender_id}: {list(detailed_data.keys())}")
                return detailed_data
            
            # If not found, return 404
            raise HTTPException(status_code=404, detail="Detailed view not found")
            
        finally:
            conn_pool.putconn(conn)
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in detailed_view: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching detailed view: {str(e)}")

@app.get("/tenders/pages/{page_num}")
async def get_all_tenders(page_num : int):
    """Get all tenders"""

    if not tenders_manager.cache_tenders:
        raise HTTPException(status_code=503, detail="Unable to load tender data")
    
    total_page_elements = len(tenders_manager.cache_tenders.values())

    #ceil rounds up to the nearest int  
    total_page_number = math.ceil(total_page_elements / 20)
    
    if page_num <= 0 or page_num > total_page_number:
        raise HTTPException(status_code=400, detail="Page is out of bounds !")
        
    #pagination logicJ
    print(total_page_number)
    #from where we end loading from the cache list
    extracting_end = page_num * 20

    #from where we begin loading in the cache list
    extracting_start = extracting_end - 20


    tender_list = list(tenders_manager.cache_tenders.values())
    tender_page = tender_list[extracting_start : extracting_end]

    # Convert dictionary valueshave to list
    # Filter only actual tenders (not other project types)
    #tender_list = [t for t in tender_list if t.get('type') == 'tender']
    
    return tender_page

@app.get("/tenders/type/{tender_type}")
async def get_tenders_by_type(tender_type: str):
    """Get tenders by type"""
    filtered_tenders = [
        tender for tender in tenders_manager.cache_tenders.values() 
        if tender.get('type', '').lower() == tender_type.lower()
    ]
    return filtered_tenders

@app.get("/tenders/category/{category}")
async def get_tenders_by_category(category: str):
    """Get tenders by category"""
    filtered_tenders = [
        tender for tender in tenders_manager.cache_tenders.values() 
        if tender.get('category', '').lower() == category.lower()
    ]
    return filtered_tenders

#TODO implement some nice serching feature if wanted ...  


@app.get("/filter")
async def filter_tenders(
    type: Optional[str] = None,
    category: Optional[str] = None,
    city: Optional[str] = None,
    status: Optional[str] = None,
    main_cpv_code: Optional[str] = None,
    main_label: Optional[str] = None, 
    additional_cpv_codes: Optional[str] = None,
    additional_labels: Optional[str] = None,
    bkp_codes : Optional[str] = None,
    bkp_labels : Optional[str] = None,
):
    filtered_tenders = list(tenders_manager.cache_tenders.values())
    
    if type:
        filtered_tenders = [t for t in filtered_tenders if t.get('type', '').lower() == type.lower() ]
    if category:
        filtered_tenders = [t for t in filtered_tenders if t.get('category', '').lower() == category.lower() or match_metadata(t, 'category', category)]
    if city:
        filtered_tenders = [t for t in filtered_tenders if str(t.get('city', '')).lower() == city.lower()]
    if status:
        filtered_tenders = [t for t in filtered_tenders if str(t.get('status', '')).lower() == status.lower()]
    if main_cpv_code:
        filtered_tenders = [t for t in filtered_tenders if match_metadata(t, 'main_cpv_code', main_cpv_code)]
    if main_label:
        filtered_tenders = [t for t in filtered_tenders if match_metadata(t, 'main_label', main_label)]
    if additional_cpv_codes:
        filtered_tenders = [t for t in filtered_tenders if match_metadata(t, 'additional_cpv_code', additional_cpv_codes)]
    if additional_labels:
        filtered_tenders = [t for t in filtered_tenders if match_metadata(t, 'additional_labels', additional_labels)]
    if bkp_codes:
        filtered_tenders = [t for t in filtered_tenders if match_metadata(t, 'bkp_codes', bkp_codes)]
    if bkp_labels:
        filtered_tenders = [t for t in filtered_tenders if match_metadata(t, 'bkp_labels', bkp_labels)]

    
    return filtered_tenders


@app.get("/check-pdf")
async def check_for_new_pdfs():
    try:
        # Get all PDF files in the backend directory
        from mail_extractor import pdf_extractor
        max_atempts = 5
        ex_success = False
        attempts = 0
        while not ex_success and attempts <= max_atempts: 
            try:
                attempts +=1
                is_pdf = pdf_extractor()
                if is_pdf is True:
                    is_pdf = False
                    ex_success = True
                else:
                    print("Retrying...")
                    await asyncio.sleep(2)
            except Exception as e:
                await asyncio.sleep(2)
            
        backend_dir = "/home/tdoor/PvtProj/TenderFinder/backend"
        pdf_files = [f for f in os.listdir(backend_dir) if f.lower().endswith('.pdf')]
        
        new_pdfs = [f for f in pdf_files]
        
        has_new_pdf = len(new_pdfs) > 0
        
        return {
            "hasPdf": has_new_pdf,
            "pdf_count": len(new_pdfs),
            "pdf_files": new_pdfs,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"Error checking for PDFs: {e}")
        return {
            "hasPdf": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/pdf_match")
async def pdf_handle():
    is_pdf = True
    pdf_results = []
    queries_dict = pdf_matching()
    for query in queries_dict.values():
        pdf_results.append(search_index(query, 5, is_pdf))

    return pdf_results
    

'''/search?query=office&search_type=hybrid&limit=25'''
@app.get("/search")
async def search_tenders(
    query: Optional[str],
    limit: int = 25
):
    try:
        if query:
            is_pdf = False
            search_result = search_index(query, limit, is_pdf)
            if search_result:
                return search_result  # Return results directly as array
            else:
                return []  # Return empty array instead of message
        else:
            return {"error": "Query parameter is required"}
    except Exception as e:
        print(f"error finding documents {e}")
        raise HTTPException(status_code=500, detail=f"Error when searching documents: {str(e)}")


    #this will be the filtering logic
    


def match_metadata(tender, key, value):
    meta = tender.get('metadata', {})
    if not meta:
        return False
    field = meta.get(key)
    if isinstance(field, list):
        return any(value.lower() in str(item).lower() for item in field)
    return value.lower() in str(field).lower() if field else False

@app.get("/stats")
async def get_stats():
    """Get statistics about tenders"""
    total = len(tenders_manager.cache_tenders)
    types = {}
    categories = {}
    statuses = {}
    cities = {}
    
    for tender in tenders_manager.cache_tenders.values():
        # Count by type
        tender_type = tender.get('type', 'Unknown')
        types[tender_type] = types.get(tender_type, 0) + 1
        
        # Count by category
        category = tender.get('category', 'Unknown')
        categories[category] = categories.get(category, 0) + 1
        
        # Count by status
        status = tender.get('status', 'Unknown')
        statuses[status] = statuses.get(status, 0) + 1
        
        # Count by city
        city = tender.get('city', 'Unknown')
        cities[city] = cities.get(city, 0) + 1
    
    return {
        "total_tenders": total,
        "by_type": types,
        "by_category": categories,
        "by_status": statuses,
        "by_city": dict(list(cities.items())[:10]),  # Top 10 cities
        "last_update": tenders_manager.last_update.strftime("%b %d, %Y %I:%M %p")
    }



@app.post("/refresh-data")
async def refresh_tender_data(background_tasks: BackgroundTasks):
    """Refresh tender data from SIMAP API"""
    """if tenders_manager.currently_updating:
        return {"message": "Data refresh already in progress"}
    """
    try:
        load_cache()
        tenders_manager.last_update = datetime.now()
    except Exception as e:
        print("Error refresing data: {e}")
    
    background_tasks.add_task()
    return {"message": "Data refresh started in background"}

@app.get("/data-status")
async def get_data_status():
    """Get information about data freshness and status"""
    return {
        "total_tenders": len(tenders_manager.cache_tenders),
        "last_update": tenders_manager.last_update.isoformat() if tenders_manager.last_update else None,
        "is_updating": tenders_manager.currently_updating,
        "has_data": len(tenders_manager.cache_tenders) > 0
    }


#TOKEN VALIDATION LOGIC
'''@app.get("/user/me/{token_id}")
async def get_user_details(user : Dict=Depends(get_fb_user_base_on_token)):
    return { 
        "connection autohorized" : True,
        "user" : user}
'''

    #implement cleanup here


if __name__=="__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=4002, reload=True)