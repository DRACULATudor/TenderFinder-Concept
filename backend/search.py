import tantivy
from tantivy import Document
import sys
import string
import os
import numpy as np 
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from parser.parser import Parser
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from search_config import schema, INDEX_PATH
import langchain
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import ResponseSchema
from langchain.output_parsers import StructuredOutputParser


index = tantivy.Index(schema, path=INDEX_PATH)


def safe_join_str(data_list : list):
    
    if data_list is None:
        return ""

    return " ".join(str(item) for item in data_list if item)
    

def index_tenders(cache_tenders : dict, detailed_view_cache : dict):
    writer = index.writer()
    writer.delete_all_documents()
    for tender_id, tender_data in cache_tenders.items():
        detaild_dict = detailed_view_cache.get(tender_id, {})

        id = tender_data.get("id")
        pub_id = tender_data.get("publication_id")
        
        metadata = tender_data.get("metadata", {})
        title = metadata.get("tender_title", "")
        category = metadata.get("category", "")
        main_cpv_code = metadata.get("main_cpv_code", "")
        main_label = metadata.get("main_label", "")
        
        additional_cpv_code = safe_join_str(metadata.get("additional_cpv_code", []))
        additional_labels = safe_join_str(metadata.get("additional_labels", []))


        bkp_codes = safe_join_str(metadata.get("bkp_codes", []))
        bkp_labels = safe_join_str(metadata.get("bkp_labels", []))



        full_text_parts = [
            id,
            pub_id,
            title,
            category, 
            main_cpv_code,
            main_label,
            additional_cpv_code,
            additional_labels,
            bkp_codes,
            bkp_labels
            ]
        
        


        if detaild_dict:
            #add detailed terms to improve search efficiency
            offer_info = Parser.extract_best_language_text(detaild_dict.get("offer_information", {}).get("offer_specific_note", {}))
            if offer_info:
                full_text_parts.append(offer_info)
            
            offer_info = Parser.extract_best_language_text(detaild_dict.get("offer_information", {}).get("offer_oppening_notes", {}))
            if offer_info:
                full_text_parts.append(offer_info)
            
            offer_info = Parser.extract_best_language_text(detaild_dict.get("offer_information", {}).get("remarks", {}))
            if offer_info:
                full_text_parts.append(offer_info)
            
            
            procurement_info = Parser.extract_best_language_text(detaild_dict.get("procurement", {}).get("order_desciption", {}).get("order", {}))
            if procurement_info:
                full_text_parts.append(procurement_info)

            procurement_info = Parser.extract_best_language_text(detaild_dict.get("procurement", {}).get("execution_notes_and_variants_part_off", {}).get("execution_note", {}))
            if procurement_info:
                full_text_parts.append(procurement_info)
            
            procurement_info = Parser.extract_best_language_text(detaild_dict.get("procurement", {}).get("execution_notes_and_variants_part_off", {}).get("variants_note", {}))
            if procurement_info:
                full_text_parts.append(procurement_info)

            procurement_info = Parser.extract_best_language_text(detaild_dict.get("procurement", {}).get("execution_notes_and_variants_part_off", {}).get("partial_offer_note", {}))
            if procurement_info:
                full_text_parts.append(procurement_info)
            
            procurement_info = Parser.extract_best_language_text(detaild_dict.get("procurement", {}).get("execution_notes_and_variants_part_off", {}).get("options_note", {}))
            if procurement_info:
                full_text_parts.append(procurement_info)




            detailed_qual_crit_list = detaild_dict.get("qualification_criteria")
            if detailed_qual_crit_list:
                for items in detailed_qual_crit_list:
                    crit_titles = Parser.extract_best_language_text(items.get("criteria_titles", {}))
                    if crit_titles:
                        full_text_parts.append(crit_titles)

                    crit_ver = Parser.extract_best_language_text(items.get("criteria_verification", {}))
                    if crit_ver:
                        full_text_parts.append(crit_ver)

                    crit_desc = Parser.extract_best_language_text(items.get("criteria_description", {}))
                    if crit_desc:
                        full_text_parts.append(crit_desc)



            detailed_award_lst = detaild_dict.get("award_criteria")
            if detailed_award_lst:
                for items in detailed_award_lst:
                    award_sbt = Parser.extract_best_language_text(items.get("award_subtitle", {}))
                    if award_sbt:
                        full_text_parts.append(award_sbt)

                    award_desc = Parser.extract_best_language_text(items.get("award_description", {}))
                    if award_desc:
                        full_text_parts.append(award_desc)

                    award_ver = Parser.extract_best_language_text(items.get("award_verification", {}))
                    if award_ver:
                        full_text_parts.append(award_ver)


            #TODO also add terms and conditions

        full_text = " ".join(str(part) for part in full_text_parts if part)
        
        
        doc = Document()
        doc.add_text("id", str(id) if id is not None else "")
        doc.add_text("pub_id", str(pub_id) if pub_id is not None else "")
        doc.add_text("title", title if title is not None else "")
        doc.add_text("category", category if category is not None else "")
        doc.add_text("main_cpv_code", main_cpv_code if main_cpv_code is not None else "")
        doc.add_text("main_label", main_label if main_label is not None else "")
        doc.add_text("additional_cpv_code", additional_cpv_code if additional_cpv_code is not None else "")
        doc.add_text("additional_labels", additional_labels if additional_labels is not None else "")
        doc.add_text("bkp_codes", bkp_codes if bkp_codes is not None else "")
        doc.add_text("bkp_labels", bkp_labels if bkp_labels is not None else "")
        doc.add_text("full_text", full_text)
        
        writer.add_document(doc)  # Don't forget to add the document!




    writer.commit()




def perform_multiple_search(query : str):
    possible_languages = {
        # ADMINISTRATION / OFFICE
        "office": ["75000000", "79100000"],
        "bureau": ["75000000", "79100000"],
        "büro": ["75000000", "79100000"],
        "ufficio": ["75000000", "79100000"],

        "administration": ["75110000", "75111000", "75112000", "75120000"],
        "verwaltung": ["75110000", "75111000", "75112000", "75120000"],
        "amministrazione": ["75110000", "75111000", "75112000", "75120000"],

        # CONSTRUCTION & CIVIL ENGINEERING
        "construction": ["45000000", "45200000", "45300000", "45400000", "45500000"],
        "bau": ["45000000", "45200000", "45300000", "45400000", "45500000"],
        "costruzione": ["45000000", "45200000", "45300000", "45400000", "45500000"],

        "infrastructure": ["45000000", "45200000", "45230000", "45231000", "45232000"],
        "infrastruktur": ["45000000", "45200000", "45230000", "45231000", "45232000"],
        "infrastruttura": ["45000000", "45200000", "45230000", "45231000", "45232000"],

        "road": ["45233000", "45233100", "45233200", "45233140", "45233150"],
        "route": ["45233000", "45233100", "45233200", "45233140", "45233150"],
        "straße": ["45233000", "45233100", "45233200", "45233140", "45233150"],
        "strada": ["45233000", "45233100", "45233200", "45233140", "45233150"],

        "highway": ["45233200", "45233300", "45233250"],
        "autoroute": ["45233200", "45233300", "45233250"],
        "autobahn": ["45233200", "45233300", "45233250"],
        "autostrada": ["45233200", "45233300", "45233250"],

        "bridge": ["45221000", "45221100", "45221200"],
        "pont": ["45221000", "45221100", "45221200"],
        "brücke": ["45221000", "45221100", "45221200"],
        "ponte": ["45221000", "45221100", "45221200"],

        "railway": ["45234000", "45234100", "45234200", "45234300"],
        "chemin de fer": ["45234000", "45234100", "45234200", "45234300"],
        "eisenbahn": ["45234000", "45234100", "45234200", "45234300"],
        "ferrovia": ["45234000", "45234100", "45234200", "45234300"],

        "tunnel": ["45223000", "45223100", "45223200"],
        "galleria": ["45223000", "45223100", "45223200"],

        # BUILDINGS
        "building": ["45200000", "45210000", "45220000", "45260000"],
        "bâtiment": ["45200000", "45210000", "45220000", "45260000"],
        "gebäude": ["45200000", "45210000", "45220000", "45260000"],
        "edificio": ["45200000", "45210000", "45220000", "45260000"],

        "housing": ["45211000", "45211100", "45211200", "45211300"],
        "logement": ["45211000", "45211100", "45211200", "45211300"],
        "wohnen": ["45211000", "45211100", "45211200", "45211300"],
        "abitazione": ["45211000", "45211100", "45211200", "45211300"],

        "school": ["45214000", "45214100", "45214200"],
        "école": ["45214000", "45214100", "45214200"],
        "schule": ["45214000", "45214100", "45214200"],
        "scuola": ["45214000", "45214100", "45214200"],

        "hospital": ["45215000", "45215100", "45215200", "85000000", "85100000"],
        "hôpital": ["45215000", "45215100", "45215200", "85000000", "85100000"],
        "krankenhaus": ["45215000", "45215100", "45215200", "85000000", "85100000"],
        "ospedale": ["45215000", "45215100", "45215200", "85000000", "85100000"],

        "university": ["45214200", "80000000", "80300000", "80400000"],
        "université": ["45214200", "80000000", "80300000", "80400000"],
        "universität": ["45214200", "80000000", "80300000", "80400000"],
        "università": ["45214200", "80000000", "80300000", "80400000"],

        "airport": ["45216000", "60400000", "63500000", "63520000"],
        "aéroport": ["45216000", "60400000", "63500000", "63520000"],
        "flughafen": ["45216000", "60400000", "63500000", "63520000"],
        "aeroporto": ["45216000", "60400000", "63500000", "63520000"],

        "port": ["45240000", "63600000", "63610000"],
        "hafen": ["45240000", "63600000", "63610000"],
        "porto": ["45240000", "63600000", "63610000"],

        # ENERGY & UTILITIES
        "energy": ["09300000", "31600000", "65000000", "65100000", "65200000"],
        "énergie": ["09300000", "31600000", "65000000", "65100000", "65200000"],
        "energie": ["09300000", "31600000", "65000000", "65100000", "65200000"],
        "energia": ["09300000", "31600000", "65000000", "65100000", "65200000"],

        "electricity": ["31681000", "31682000", "65310000", "45310000", "45317000"],
        "électricité": ["31681000", "31682000", "65310000", "45310000", "45317000"],
        "elektrizität": ["31681000", "31682000", "65310000", "45310000", "45317000"],
        "elettricità": ["31681000", "31682000", "65310000", "45310000", "45317000"],

        "gas": ["09100000", "65200000", "45331000", "45332000"],
        "gaz": ["09100000", "65200000", "45331000", "45332000"],

        "water": ["65100000", "45332000", "77300000", "45333000"],
        "eau": ["65100000", "45332000", "77300000", "45333000"],
        "wasser": ["65100000", "45332000", "77300000", "45333000"],
        "acqua": ["65100000", "45332000", "77300000", "45333000"],

        "waste": ["90500000", "90511000", "90512000", "90513000", "90520000"],
        "déchets": ["90500000", "90511000", "90512000", "90513000", "90520000"],
        "abfall": ["90500000", "90511000", "90512000", "90513000", "90520000"],
        "rifiuti": ["90500000", "90511000", "90512000", "90513000", "90520000"],

        # HEALTH & SOCIAL
        "health": ["85000000", "85100000", "85110000", "33000000", "33600000"],
        "santé": ["85000000", "85100000", "85110000", "33000000", "33600000"],
        "gesundheit": ["85000000", "85100000", "85110000", "33000000", "33600000"],
        "salute": ["85000000", "85100000", "85110000", "33000000", "33600000"],

        "social": ["85300000", "85320000", "85321000", "85322000"],
        "sozial": ["85300000", "85320000", "85321000", "85322000"],
        "sociale": ["85300000", "85320000", "85321000", "85322000"],

        "care": ["85100000", "85300000", "85310000", "85311000"],
        "soin": ["85100000", "85300000", "85310000", "85311000"],
        "pflege": ["85100000", "85300000", "85310000", "85311000"],
        "cura": ["85100000", "85300000", "85310000", "85311000"],

        # INFORMATION TECHNOLOGY
        "software": ["72000000", "72200000", "72210000", "72220000", "72230000", "72240000", "72250000", "72260000", "72268000", "48000000", "48100000", "48200000", "48300000", "48400000", "48500000", "48600000", "48700000", "48800000"],
        "logiciel": ["72000000", "72200000", "72210000", "72220000", "72230000", "72240000", "72250000", "72260000", "72268000", "48000000", "48100000", "48200000", "48300000", "48400000", "48500000", "48600000", "48700000", "48800000"],

        "hardware": ["30200000", "30230000", "30231000", "30232000", "72100000"],
        "matériel": ["30200000", "30230000", "30231000", "30232000", "72100000"],

        "computer": ["30200000", "30230000", "72000000", "72600000"],
        "ordinateur": ["30200000", "30230000", "72000000", "72600000"],

        "network": ["32400000", "32420000", "32500000", "32510000", "48700000", "72400000"],
        "réseau": ["32400000", "32420000", "32500000", "32510000", "48700000", "72400000"],
        "netzwerk": ["32400000", "32420000", "32500000", "32510000", "48700000", "72400000"],
        "rete": ["32400000", "32420000", "32500000", "32510000", "48700000", "72400000"],

        "it services": ["72000000", "72100000", "72200000", "72210000", "72220000", "72230000", "72240000", "72250000", "72260000", "72268000", "72300000", "72400000", "72500000", "72600000", "79620000"],
        "services informatiques": ["72000000", "72100000", "72200000", "72210000", "72220000", "72230000", "72240000", "72250000", "72260000", "72268000", "72300000", "72400000", "72500000", "72600000", "79620000"],
        "it-dienstleistungen": ["72000000", "72100000", "72200000", "72210000", "72220000", "72230000", "72240000", "72250000", "72260000", "72268000", "72300000", "72400000", "72500000", "72600000", "79620000"],
        "servizi it": ["72000000", "72100000", "72200000", "72210000", "72220000", "72230000", "72240000", "72250000", "72260000", "72268000", "72300000", "72400000", "72500000", "72600000", "79620000"],

        "cybersecurity": ["79714000", "79715000", "72000000", "35113000"],
        "cybersécurité": ["79714000", "79715000", "72000000", "35113000"],
        "cybersicherheit": ["79714000", "79715000", "72000000", "35113000"],
        "cybersicurezza": ["79714000", "79715000", "72000000", "35113000"],

        "it": ["72000000", "72100000", "72200000", "72300000", "72400000", "72500000", "72600000", "79620000"],
        "informatique": ["72000000", "72100000", "72200000", "72300000", "72400000", "72500000", "72600000", "79620000"],
        "informatik": ["72000000", "72100000", "72200000", "72300000", "72400000", "72500000", "72600000", "79620000"],
        "informatica": ["72000000", "72100000", "72200000", "72300000", "72400000", "72500000", "72600000", "79620000"],

        "programming": ["72200000", "72210000", "72220000", "72230000", "72240000"],
        "programmation": ["72200000", "72210000", "72220000", "72230000", "72240000"],
        "programmierung": ["72200000", "72210000", "72220000", "72230000", "72240000"],
        "programmazione": ["72200000", "72210000", "72220000", "72230000", "72240000"],

        "database": ["72300000", "48600000", "48610000"],
        "base de données": ["72300000", "48600000", "48610000"],
        "datenbank": ["72300000", "48600000", "48610000"],

        "microsoft": ["72268000", "48000000", "48100000"],
        "cisco": ["32500000", "32510000", "48700000", "72000000"],
        "sap": ["72260000", "48100000", "48110000"],
        "linux": ["48000000", "72000000", "79620000"],

        # TELECOMMUNICATIONS
        "telecommunications": ["32400000", "32420000", "32500000", "64200000", "64210000", "64220000"],
        "télécommunications": ["32400000", "32420000", "32500000", "64200000", "64210000", "64220000"],
        "telekommunikation": ["32400000", "32420000", "32500000", "64200000", "64210000", "64220000"],
        "telecomunicazioni": ["32400000", "32420000", "32500000", "64200000", "64210000", "64220000"],

        # DEFENSE & SECURITY
        "defense": ["35800000", "79700000", "79710000"],
        "défense": ["35800000", "79700000", "79710000"],
        "verteidigung": ["35800000", "79700000", "79710000"],
        "difesa": ["35800000", "79700000", "79710000"],

        "security": ["79714000", "79715000", "35113000", "35114000", "79713000"],
        "sécurité": ["79714000", "79715000", "35113000", "35114000", "79713000"],
        "sicherheit": ["79714000", "79715000", "35113000", "35114000", "79713000"],
        "sicurezza": ["79714000", "79715000", "35113000", "35114000", "79713000"],

        "police": ["79700000", "79710000", "79711000"],
        "polizei": ["79700000", "79710000", "79711000"],
        "polizia": ["79700000", "79710000", "79711000"],

        "fire": ["50410000", "79720000", "79721000"],
        "incendie": ["50410000", "79720000", "79721000"],
        "feuerwehr": ["50410000", "79720000", "79721000"],
        "vigili del fuoco": ["50410000", "79720000", "79721000"],

        # CLEANING & FACILITY MANAGEMENT
        "cleaning": ["90900000", "90910000", "90920000", "90919000"],
        "nettoyage": ["90900000", "90910000", "90920000", "90919000"],
        "reinigung": ["90900000", "90910000", "90920000", "90919000"],
        "pulizia": ["90900000", "90910000", "90920000", "90919000"],

        "maintenance": ["50700000", "50800000", "71000000", "50710000", "50730000"],
        "wartung": ["50700000", "50800000", "71000000", "50710000", "50730000"],
        "manutenzione": ["50700000", "50800000", "71000000", "50710000", "50730000"],

        "facility": ["70300000", "77300000", "90900000", "70320000"],
        "installation": ["70300000", "77300000", "90900000", "70320000"],
        "anlage": ["70300000", "77300000", "90900000", "70320000"],
        "impianto": ["70300000", "77300000", "90900000", "70320000"],

        # CONSULTING & SERVICES
        "consulting": ["73000000", "73100000", "73200000", "79400000", "79500000"],
        "conseil": ["73000000", "73100000", "73200000", "79400000", "79500000"],
        "beratung": ["73000000", "73100000", "73200000", "79400000", "79500000"],
        "consulenza": ["73000000", "73100000", "73200000", "79400000", "79500000"],

        "audit": ["79212000", "79413000", "79414000"],
        "prüfung": ["79212000", "79413000", "79414000"],
        "revisione": ["79212000", "79413000", "79414000"],

        "training": ["80000000", "80500000", "80600000", "80510000", "80520000"],
        "formation": ["80000000", "80500000", "80600000", "80510000", "80520000"],
        "ausbildung": ["80000000", "80500000", "80600000", "80510000", "80520000"],
        "formazione": ["80000000", "80500000", "80600000", "80510000", "80520000"],

        # TRANSPORT & LOGISTICS
        "transport": ["60000000", "60100000", "60200000", "60300000", "60400000"],
        "trasporto": ["60000000", "60100000", "60200000", "60300000", "60400000"],

        "logistics": ["63000000", "60600000", "63100000", "63110000"],
        "logistique": ["63000000", "60600000", "63100000", "63110000"],
        "logistik": ["63000000", "60600000", "63100000", "63110000"],
        "logistica": ["63000000", "60600000", "63100000", "63110000"],

        "shipping": ["63100000", "64110000", "63110000"],
        "expédition": ["63100000", "64110000", "63110000"],
        "versand": ["63100000", "64110000", "63110000"],
        "spedizione": ["63100000", "64110000", "63110000"],

        "freight": ["63100000", "60100000", "60110000"],
        "fret": ["63100000", "60100000", "60110000"],
        "fracht": ["63100000", "60100000", "60110000"],
        "carico": ["63100000", "60100000", "60110000"],

        # MATERIALS & SUPPLIES
        "materials": ["44000000", "14000000", "16000000", "44100000", "44200000"],
        "matériaux": ["44000000", "14000000", "16000000", "44100000", "44200000"],
        "materialien": ["44000000", "14000000", "16000000", "44100000", "44200000"],
        "materiali": ["44000000", "14000000", "16000000", "44100000", "44200000"],

        "concrete": ["44300000", "44310000", "44320000"],
        "béton": ["44300000", "44310000", "44320000"],
        "beton": ["44300000", "44310000", "44320000"],
        "cemento": ["44300000", "44310000", "44320000"],

        "steel": ["14200000", "44200000", "44210000", "44220000"],
        "acier": ["14200000", "44200000", "44210000", "44220000"],
        "stahl": ["14200000", "44200000", "44210000", "44220000"],
        "acciaio": ["14200000", "44200000", "44210000", "44220000"],

        # MEDICAL & PHARMACEUTICAL
        "medical": ["33000000", "33100000", "33600000", "33700000", "85000000"],
        "médical": ["33000000", "33100000", "33600000", "33700000", "85000000"],
        "medizinisch": ["33000000", "33100000", "33600000", "33700000", "85000000"],
        "medico": ["33000000", "33100000", "33600000", "33700000", "85000000"],

        "pharmaceutical": ["33600000", "33610000", "33690000"],
        "pharmaceutique": ["33600000", "33610000", "33690000"],
        "pharmazeutisch": ["33600000", "33610000", "33690000"],
        "farmaceutico": ["33600000", "33610000", "33690000"],

        # FOOD & CATERING
        "food": ["15000000", "15100000", "15800000", "55500000"],
        "nourriture": ["15000000", "15100000", "15800000", "55500000"],
        "lebensmittel": ["15000000", "15100000", "15800000", "55500000"],
        "cibo": ["15000000", "15100000", "15800000", "55500000"],

        "catering": ["55500000", "55510000", "55520000"],
        "restauration": ["55500000", "55510000", "55520000"],
        "verpflegung": ["55500000", "55510000", "55520000"],
        "ristorazione": ["55500000", "55510000", "55520000"],

        # LEGAL & FINANCIAL
        "legal": ["79100000", "79110000", "79120000"],
        "juridique": ["79100000", "79110000", "79120000"],
        "rechtlich": ["79100000", "79110000", "79120000"],
        "legale": ["79100000", "79110000", "79120000"],

        "financial": ["66000000", "66100000", "66500000", "79200000"],
        "financier": ["66000000", "66100000", "66500000", "79200000"],
        "finanziell": ["66000000", "66100000", "66500000", "79200000"],
        "finanziario": ["66000000", "66100000", "66500000", "79200000"],

        "insurance": ["66500000", "66510000", "66520000"],
        "assurance": ["66500000", "66510000", "66520000"],
        "versicherung": ["66500000", "66510000", "66520000"],
        "assicurazione": ["66500000", "66510000", "66520000"],
    }
    query_lower = query.lower().strip()
    searchable_list = []
    if query_lower in possible_languages :
        searchable_list.extend(possible_languages[query_lower])
    

    query_words = query_lower.split()
    for words in query_words:
        if words in possible_languages:
            searchable_list.extend(possible_languages[words])
    
    if query not in possible_languages:
        searchable_list.append(query)
    

    dup = set()
    unique = []
    for term in searchable_list:
        if term not in dup:
            dup.add(term)
            unique.append(term)

    return unique

try :
    doc_embeds_cache = {}
    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

except Exception as e:
    print(f"Couldn't initalize embedding model {e}")


#pass a seacrher to look tourgh docs
def embed_index_search():
    
    searcher = index.searcher()

    #parse all docks
    all_docs_query = index.parse_query("*", ["full_text"])
    #search trough all
    search_res = searcher.search(all_docs_query, 10000)
    #encode all, add to dict key is id val is encoded vals
    for score, doc_adress in search_res.hits:
        doc = searcher.doc(doc_adress)
        doc_id = doc.get_first('id')
        doc_text = doc.get_first('full_text')
        if doc_id and doc_text:
            embeddings = model.encode([doc_text])[0]
            doc_embeds_cache[doc_id] = embeddings
        else:
            print("no docs to encode")

def embed_user_query(query : str):
    if not query: 
        return []
    embeds = model.encode([query])[0]
    return embeds


def perform_semantic_search(embeded_query : np.ndarray):
    rez = []
    for doc_id, embeds, in doc_embeds_cache.items():
        sims = cosine_similarity([embeded_query],[embeds])[0][0]
        rez.append({
            'doc_id' : doc_id,
            'similarities': sims
        })
    return rez


def normalize_trad_score(score, max_score=20.0):
    return min(score/max_score, 1.0)

def norm_semantic_score(score):
    return max(0.0, min(score, 1.0))

def final_score_calculus(search_type, trad_score, sem_score):
    norm_trad = normalize_trad_score(trad_score)
    norm_sem = norm_semantic_score(sem_score)

    if search_type == 'hybrid':
        final_score_calculus = norm_sem + norm_trad 
    
    elif search_type == 'semantic':
        final_score_calculus = norm_sem
    
    else:
        final_score_calculus = norm_trad + 1.0

    return final_score_calculus



"""def gemini_results_ranker(results : list, query : str):
    
    task_instructions = '''\
    You are an expert procurement analyst specializing in Swiss public tenders.
    Query: {query}

    Based on the Query you need to ANALYZE these Tenders: {results}

    CONSIDER Semantic relevance, CPV codes, and all other context you find helpful

    RETURN only a JSON with the same Tenders but RANKED in the most RELEVANT order based on the Query

    Return JSON: {{"tender_id": "Tender"}}
    '''

    prompt_template = ChatPromptTemplate.from_template(template=task_instructions)
    mssg =  prompt_template.format_messages(query=query, results=results)
    response = chat.invoke(mssg)
    print(response.content)

    return"""


def search_index(query : str, limit : int, is_pdf : bool):
    if not query or not query.strip():
        return []
    try:
        
        from main import tenders_manager
        multi_lang_query = perform_multiple_search(query)
        embeded_query = embed_user_query(query)
        similarities_list = []
        similarities_list = perform_semantic_search(embeded_query)
        similarities_list.sort(key=lambda x : x['similarities'], reverse=True)
        searcher = index.searcher()
        semantic_results = {}



        for sim in similarities_list:
            if sim['similarities'] > 0.3:
                id_doc = sim["doc_id"]
                if id_doc in tenders_manager.cache_tenders:
                    tender_copy = tenders_manager.cache_tenders[id_doc].copy()
                    tender_copy['semantic_score'] = float(sim['similarities'])
                    tender_copy['search_type'] = 'semantic'
                    semantic_results[id_doc] = tender_copy
        #return semantic_results[:limit]
        
        all_hits = {}
        
        # Get searcher from the index
        # Create query parser for the full_text field
        for individual_quer in multi_lang_query:

            query_parser = index.parse_query(individual_quer, ["full_text"])

            # Execute the search
            search_results = searcher.search(query_parser, limit)
            
            hits = search_results.hits
            # Convert results to a list of dictionaries
            for score, doc_address in hits:
                # Retrieve the document
                doc = searcher.doc(doc_address)
                doc_id = doc.get_first('id')
                # Extract field values from the document
                if doc_id in semantic_results:

                    semantic_score = semantic_results[doc_id]['semantic_score']
                    final_score = final_score_calculus('hybrid', float(score), semantic_score)
                    all_hits[doc_id] = {
                        'id': doc.get_first('id'),
                        'pub_id': doc.get_first('pub_id'),
                        'title': doc.get_first('title'),
                        'category': doc.get_first('category'),
                        'main_cpv_code': doc.get_first('main_cpv_code'),
                        'main_label': doc.get_first('main_label'),
                        'full_text' : doc.get_first('full_text'),
                        'trad_score': float(score),
                        'semantic_socre' : semantic_score,
                        'score' : final_score,
                        'search_type' : 'hybrid'      # Relevance score (higher = better match)
                    }

                elif doc_id not in all_hits or float(score) > 0.5:
                    final_sco = final_score_calculus('traditdional', float(score), 0)
                    all_hits[doc_id] = {
                        'id': doc.get_first('id'),
                        'pub_id': doc.get_first('pub_id'),
                        'title': doc.get_first('title'),
                        'category': doc.get_first('category'),
                        'main_cpv_code': doc.get_first('main_cpv_code'),
                        'main_label': doc.get_first('main_label'),
                        'full_text' : doc.get_first('full_text'),
                        'score': final_sco,
                        'search_type' : 'traditdional'    # Relevance score (higher = better match)
                    }
        
        for doc_id, semantic_result in semantic_results.items(): 
            if doc_id not in all_hits:
                sem_score = semantic_result['semantic_score']
                final_sc = final_score_calculus('semantic', 0, sem_score)
                all_hits[doc_id] = {
                    'id': semantic_result.get('id'),
                    'pub_id': semantic_result.get('publication_id'),
                    'title': semantic_result.get('metadata', {}).get('tender_title', ''),
                    'category': semantic_result.get('metadata', {}).get('category', ''),
                    'main_cpv_code': semantic_result.get('metadata', {}).get('main_cpv_code', ''),
                    'main_label': semantic_result.get('metadata', {}).get('main_label', ''), 
                    'score': final_sc,
                    'search_type': 'semantic'
                }


        results = list(all_hits.values())

        #sort rez
        results.sort(key=lambda x:x['score'], reverse=True)
        if is_pdf is False:
            return results[:limit]
        else:
            return results[:3]
        
    except Exception as e:
        print(f"Search error: {e}")
        return []


