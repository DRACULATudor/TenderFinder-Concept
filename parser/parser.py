import requests
import pprint
import pandas as pd
import time
import copy
import psycopg2
from psycopg2.extras import Json
from bs4 import BeautifulSoup



"""
In case the abandoned tenders are requires it can be also done 
abandon_base = item.get('abandonment', {})
reasons = abandon_base
if is_abandonment is True:
    abandonment_details = {
        #for reasons io ll have to implement a logic of obtaining all(not now later on keep in mind)
        
        'reasons' : abandon_base.get('reasons', {})
        .get('0', None),
        'remedies_notices' : {
            'DE' : abandon_base.get('remediesNotice', {}).get('de', None),
            'EN' : abandon_base.get('remediesNotice', {}).get('en', None),
            'FR' : abandon_base.get('remediesNotice', {}).get('fr', None),
            'IT' : abandon_base.get('remediesNotice', {}).get('it', '-
        },
        'other_reasons' : {
            'DE' : abandon_base.get('otherReason', {}).get('de', None),
            'EN' : abandon_base.get('otherReason', {}).get('en', None),
            'FR' : abandon_base.get('otherReason', {}).get('fr', None),
            'IT' : abandon_base.get('otherReason', {}).get('it', None)
        },
        'remarks' : {
            'DE' : abandon_base.get('remarks', {}).get('de', None),
            'EN' : abandon_base.get('remarks', {}).get('en', None),
            'FR' : abandon_base.get('remarks', {}).get('fr', None),
            'IT' : abandon_base.get('remarks', {}).get('it', None)
        }
    }"""
#TODO implement cronfor fresh updates

#TODO add type hints everywhere(clearer what fctions expect as params/return) also for FastAPI, Auto-generates API docs from type hints basically smart comments for certain tools
#fastapi built to work with pydantic (used for data validation at runtime (basically imo python with types))
#metadata used for fastApi (This metadata helps you:Know how fresh your data is, Debug extraction problems, Monitor API performance, Ensure data quality)

'https://www.simap.ch/api/' '+' 'publications/v1/project/' '+' 'a625664d-a542-4883-b366-ee0546722d0f/' '+' 'publication-details/' '+' 'ac8f0efc-ae18-4ff3-be67-6377d62ad878'

class Parser:
    
    @staticmethod
    def strip_html_text(htmltext):
        if not htmltext:
            return None
        soup = BeautifulSoup(htmltext, 'lxml')
        clean_text = soup.get_text(' ' ,strip=True)
        return clean_text if clean_text.strip() else None

    @staticmethod
    def multi_languages(data, field, languages=['en','de','fr','it']):
        if not data or not data.get(field):
            return None
        for lng in languages:
            val = data[field].get(lng,'')
            if val:
                return val
        return None
    
    @staticmethod
    def safe_html_extractor(base_dict, field_name):
        field_data = base_dict.get(field_name)
        if field_data is None:
            field_data = {}
        return {
            'DE': Parser.strip_html_text(field_data.get('de')) if field_data.get('de') else None,
            'EN': Parser.strip_html_text(field_data.get('en')) if field_data.get('en') else None,
            'FR': Parser.strip_html_text(field_data.get('fr')) if field_data.get('fr') else None,
            'IT': Parser.strip_html_text(field_data.get('it')) if field_data.get('it') else None
        }
    
    @staticmethod
    def extract_best_language_text(multilingual_dict):
        """Extract the best available language from safe_html_extractor output"""
        if not multilingual_dict or not isinstance(multilingual_dict, dict):
            return ""

        # Priority: EN > DE > FR > IT
        for lang in ['EN', 'DE', 'FR', 'IT']:
            text = multilingual_dict.get(lang)
            if text:
                return Parser.strip_html_text(text)

        return ""
    
    @staticmethod
    def parse_json(reponse):
        tender_dictio = {}
        for item in reponse['projects']:
            #need to check for abandoment also
            if  item.get('pubType') == 'award' or  item.get('pubType') == 'abandonment' or item.get('processType', None) != 'open':
                continue
            tender_id = item['id']
            project_type = item['projectType']
            project_category = item['projectSubType']
            project_date = item['publicationDate']
            project_title = Parser.multi_languages(item, 'title')
            publication_id = item['publicationId']
            if not item.get('publicationNumber'):
                publication_number = None
            else:
                publication_number = item['publicationNumber']
            if not item.get('orderAddress'):
                city = None
            else :
                city =  Parser.multi_languages(item.get('orderAddress'), 'city')
            if not item.get('orderAddress'):
                postal_code = None
            else:
                postal_code = (item.get('orderAddress')).get('postalCode', None)
            if postal_code is None or postal_code == '':
                postal_code = None
            if not item.get('processType'):
                project_state = None
            else:
                project_state = item['processType']
            tender_dictio[tender_id] = {
            'id'    : tender_id,
            'publication_id' : publication_id,
            'search_index' : publication_number,
            'title' : project_title,
            'type' : project_type,
            'category' : project_category,
            'date' : project_date,
            'city' : city,
            'postal_code' : postal_code,
            'status' : project_state
        }
        return tender_dictio
    
    @staticmethod
    def parse_each_detailed_tender(detailed_resp_list):
        dict_of_detailed_tenders = {}
        chunks_for_embeding = []
        for item in detailed_resp_list:
            
            if item.get('base', {}).get('award', None) or item.get('base',{}).get('processType',None) != 'open' or item.get('base',{}).get('type',None) == 'abandonment':
                continue

            base_data = item.get('base', {})
            tender_title  = Parser.safe_html_extractor(base_data, 'title')
            tender_id = base_data.get('projectId')
            tender_cattegory = base_data.get('orderType', None)
            tender_type = base_data.get('type', None)
            pub_base = item.get('id')
            
            #CPV CODES
            cpv_base = item.get('procurement', {}).get('cpvCode', {})
            cpvs_list = []


            cpv_and_labels = {
                'cpv_code' : cpv_base.get('code', None),
                'cpv_labels' :  Parser.extract_best_language_text(cpv_base.get('label'))
            }
            cpvs_list.append(cpv_and_labels)
            
            #FOR CHUNKING
            main_cpv_code = cpvs_list[0]['cpv_code'] if cpvs_list else None
            main_cpv_label = cpvs_list[0]['cpv_labels'] if cpvs_list else None



            additional_cpv_base = item.get('procurement', {}).get('additionalCpvCodes', [])
            add_cpv = []
            if additional_cpv_base :
                for details in additional_cpv_base:
                    additional_cpvs = {
                        'additional_cpv_base' : details.get('code', None),
                        'additional_cpvs_labels' : Parser.extract_best_language_text(details.get('label'))
                    }
                    add_cpv.append(additional_cpvs)
                    cpvs_list.append(additional_cpvs)

            #FOR CHUNKING METADATA
            additional_cpv = [add_cpvs['additional_cpv_base'] for add_cpvs in add_cpv]
            additional_label = [add_cpvs['additional_cpvs_labels'] for add_cpvs in add_cpv]

            #BKP CODES
            bkp_list = []
            codes_base = item.get('procurement')
            bkp_base = codes_base.get('bkpCodes', []) if codes_base else []
            if bkp_base:
                for details in bkp_base:
                    bkp_codes = {
                        'bkp_code' : details.get('code', None),
                        'bkp_labels' : Parser.extract_best_language_text(details.get('label'))
                    }
                    bkp_list.append(bkp_codes)

                    
            #FOR CHUNKING METADATA
            bkp_only_list = [bkp['bkp_code'] for bkp in bkp_list]
            bkp_only_labels = [bkp['bkp_labels'] for bkp in bkp_list]

            dates_base = item.get('dates', {})
            date_rangez = (dates_base.get('documentsAvailable') or {}).get('dateRange', [])
            deadlinez = []
            if date_rangez :
                for i in range(0, len(date_rangez), 2):
                    if i < len(date_rangez):
                        deadliness = {
                            'Available from: ' : date_rangez[i],
                            'Ends on: ' : date_rangez[i + 1] if (i + 1) < len(date_rangez) else None
                        }
                        deadlinez.append(deadliness)
            else:
                deadlinez = None
            #DATES INFORMATION AND OFFER
            dates = {
                'publication_date': dates_base.get('publicationDate', None),
                'inital_publication_date' : dates_base.get('initialPublicationDate', None),
                'specific_dead_lines_and_formal_requirements' : Parser.safe_html_extractor(dates_base, 'specificDeadlinesAndFormalRequirements'),
            }

            #TERMS AND CONDITTIONS
            terms_and_conditions_base = item.get('terms', {})
            terms = None
            if terms_and_conditions_base:
                terms = {
                    'consortium_allowed' : terms_and_conditions_base.get('consortiumAllowed', None),
                    'consortium_multi_application_allowed' : terms_and_conditions_base.get('consortiumMultiApplicationAllowed', None),
                    'sub_contractor_allowed' : terms_and_conditions_base.get('subContractorAllowed', None),
                    'sub_contractor_multi_application_allowed' : terms_and_conditions_base.get('subContractorMultiApplicationAllowed', None),
                    'pre_involved_vendor' : Parser.safe_html_extractor(terms_and_conditions_base, 'preInvolvedVendor'),
                    'terms_of_business' : Parser.safe_html_extractor(terms_and_conditions_base, 'termsOfBusiness'),
                    'terms_of_payment' : Parser.safe_html_extractor(terms_and_conditions_base, 'termsOfPayment'),
                    'included_costs' : Parser.safe_html_extractor(terms_and_conditions_base, 'includedCosts'),
                    'security_deposits' : Parser.safe_html_extractor(terms_and_conditions_base, 'securityDeposits'),
                    'non_WTO_requirements' : Parser.safe_html_extractor(terms_and_conditions_base, 'nonWTORequirements'),
                    'walk_through_notes' : Parser.safe_html_extractor(terms_and_conditions_base, 'walkThroughNotes'),
                    'terms_note' : Parser.safe_html_extractor(terms_and_conditions_base, 'termsNote'),
                    'other_requirements' : Parser.safe_html_extractor(terms_and_conditions_base, 'otherRequirements'),
                    'consortium_Note' : Parser.safe_html_extractor(terms_and_conditions_base, 'consortiumNote'),
                    'sub_contractor_note' : Parser.safe_html_extractor(terms_and_conditions_base, 'subContractorNote'),
                    'remediesNotice' : Parser.safe_html_extractor(terms_and_conditions_base, 'remediesNotice')
                }
            #CHUNK TERMS AND CONDINTIONS=============================================================================
            terms_content_parts = []
            
            if terms:
                if terms.get('consortium_allowed'):
                    terms_content_parts.append(f"Consortium Allowed: {terms['consortium_allowed']}")
                
                if terms.get('consortium_multi_application_allowed'):
                    terms_content_parts.append(f"Consortium Multi-Application Allowed: {terms['consortium_multi_application_allowed']}")
                
                if terms.get('sub_contractor_allowed'):
                    terms_content_parts.append(f"Subcontractor Allowed: {terms['sub_contractor_allowed']}")

                if terms.get('sub_contractor_multi_application_allowed'):
                    terms_content_parts.append(f"Subcontractor Multi-Application Allowed: {terms['sub_contractor_multi_application_allowed']}")
                
                if terms.get('pre_involved_vendor'):
                    pre_vendor = Parser.extract_best_language_text(terms['pre_involved_vendor'])
                    if pre_vendor:
                        terms_content_parts.append(f"Pre-Involved Vendor: {pre_vendor}")
                
                if terms.get('terms_of_business'):
                    business = Parser.extract_best_language_text(terms['terms_of_business'])
                    if business:
                        terms_content_parts.append(f"Terms of Business: {business}")
                
                if terms.get('terms_of_payment'):
                    payment = Parser.extract_best_language_text(terms['terms_of_payment'])
                    if payment:
                        terms_content_parts.append(f"Terms of Payment: {payment}")
                
                if terms.get('included_costs'):
                    included_costs = Parser.extract_best_language_text(terms['included_costs'])
                    if included_costs:
                        terms_content_parts.append(f"Included Costs: {included_costs}")
                
                if terms.get('security_deposits'):
                    deposits = Parser.extract_best_language_text(terms['security_deposits'])
                    if deposits:
                        terms_content_parts.append(f"Security Deposits: {deposits}")
                
                if terms.get('non_WTO_requirements'):
                    non_wto = Parser.extract_best_language_text(terms['non_WTO_requirements'])
                    if non_wto:
                        terms_content_parts.append(f"Non-WTO Requirements: {non_wto}")
                
                if terms.get('walk_through_notes'):
                    walk_notes = Parser.extract_best_language_text(terms['walk_through_notes'])
                    if walk_notes:
                        terms_content_parts.append(f"Walk-Through Notes: {walk_notes}")
                
                if terms.get('terms_note'):
                    terms_note = Parser.extract_best_language_text(terms['terms_note'])
                    if terms_note:
                        terms_content_parts.append(f"Terms Note: {terms_note}")
                
                if terms.get('other_requirements'):
                    other_req = Parser.extract_best_language_text(terms['other_requirements'])
                    if other_req:
                        terms_content_parts.append(f"Other Requirements: {other_req}")
                
                if terms.get('consortium_Note'):
                    consortium_note = Parser.extract_best_language_text(terms['consortium_Note'])
                    if consortium_note:
                        terms_content_parts.append(f"Consortium Note: {consortium_note}")
                
                if terms.get('sub_contractor_note'):
                    sub_contractor_note = Parser.extract_best_language_text(terms['sub_contractor_note'])
                    if sub_contractor_note:
                        terms_content_parts.append(f"Subcontractor Note: {sub_contractor_note}")
                
                if terms.get('remediesNotice'):
                    remedies = Parser.extract_best_language_text(terms['remediesNotice'])
                    if remedies:
                        terms_content_parts.append(f"Remedies Notice: {remedies}")
            
            if terms_content_parts:
                terms_chunk = {
                    'chunk_id': f"{tender_id}_terms_and_conditions",
                    'tender_id': tender_id,
                    'content': "\n".join(terms_content_parts),
                    'chunk_type': 'terms_and_conditions',
                    'metadata': {
                        'tender_title': Parser.extract_best_language_text(tender_title),
                        'category': tender_cattegory,
                        'publication_id': pub_base,
                        'main_cpv_code': main_cpv_code,
                        'main_label': main_cpv_label,

                        'additional_cpv_code' : additional_cpv,
                        'additional_labels' : additional_label,
                        'bkp_codes' : bkp_only_list,
                        'bkp_labels' : bkp_only_labels,

                        'consortium_allowed': terms.get('consortium_allowed') if terms else None,
                        'sub_contractor_allowed': terms.get('sub_contractor_allowed') if terms else None,
                    }
                }
                chunks_for_embeding.append(terms_chunk)
            #========================================================================================================

            #TODO maybe also add the qnas
            #PROCUREMENT INFO
            proc_office_base = item.get('project-info', {}).get('procOfficeAddress', {})
            proc_recipent_base = item.get('project-info', {}).get('procurementRecipientAddress', {})

            procurement_info = {
                'procurement_office_details'  : {
                    #extract proc off info
                    'name' : Parser.multi_languages(proc_office_base, 'name'),
                    'contact_person' : Parser.multi_languages(proc_office_base, 'contactPerson'),
                    'phone' : proc_office_base.get('phone', None),
                    'email' : proc_office_base.get('email', None),
                    'url' : Parser.multi_languages(proc_office_base, 'url'),
                    'country_id' : proc_office_base.get('countryId', None),
                    'canton_id' : proc_office_base.get('cantonId', None),
                    'city' : Parser.multi_languages(proc_office_base, 'city'),
                    'street' : Parser.multi_languages(proc_office_base, 'street'),
                    'postal_code' : proc_office_base.get('postalCode', None)
                },
                'procurement_recipient_details' : {
                    #extract proc recip details
                    'name' : Parser.multi_languages(proc_recipent_base, 'name'),
                    'contact_person' : Parser.multi_languages(proc_recipent_base, 'contactPerson'),
                    'phone' : proc_recipent_base.get('phone', None),
                    'email' : proc_recipent_base.get('email', None),
                    'url' : Parser.multi_languages(proc_recipent_base, 'url'),
                    'country_id' : proc_recipent_base.get('countryId', None),
                    'canton_id' : proc_recipent_base.get('cantonId',None),
                    'city' : Parser.multi_languages(proc_recipent_base, 'city'),
                    'street' : Parser.multi_languages(proc_recipent_base, 'street'),
                    'postal_code' : proc_recipent_base.get('postalCode', None),
                }
            }
            # PROCUREMENT OFFICE AND RECIPIENT CHUNKING ===================================

            procurement_info_content_parts = []

            # Procurement Office Details
            proc_office = procurement_info.get('procurement_office_details', {})
            if proc_office:
                # Office name
                if proc_office.get('name'):
                    office_name = Parser.extract_best_language_text(proc_office['name'])
                    if office_name:
                        procurement_info_content_parts.append(f"Procurement Office Name: {office_name}")

                # Contact person
                if proc_office.get('contact_person'):
                    contact_person = Parser.extract_best_language_text(proc_office['contact_person'])
                    if contact_person:
                        procurement_info_content_parts.append(f"Procurement Office Contact Person: {contact_person}")

                # Phone
                if proc_office.get('phone'):
                    procurement_info_content_parts.append(f"Procurement Office Phone: {proc_office['phone']}")

                # Email
                if proc_office.get('email'):
                    procurement_info_content_parts.append(f"Procurement Office Email: {proc_office['email']}")

                # URL
                if proc_office.get('url'):
                    url = Parser.extract_best_language_text(proc_office['url'])
                    if url:
                        procurement_info_content_parts.append(f"Procurement Office URL: {url}")

                # Office address
                office_address_parts = []
                if proc_office.get('street'):
                    street = Parser.extract_best_language_text(proc_office['street'])
                    if street:
                        office_address_parts.append(street)
                if proc_office.get('city'):
                    city = Parser.extract_best_language_text(proc_office['city'])
                    if city:
                        office_address_parts.append(city)
                if proc_office.get('postal_code'):
                    office_address_parts.append(str(proc_office['postal_code']))
                if proc_office.get('canton_id'):
                    office_address_parts.append(f"Canton: {proc_office['canton_id']}")
                if proc_office.get('country_id'):
                    office_address_parts.append(f"Country: {proc_office['country_id']}")

                if office_address_parts:
                    procurement_info_content_parts.append(f"Procurement Office Address: {', '.join(office_address_parts)}")

            # Procurement Recipient Details
            proc_recipient = procurement_info.get('procurement_recipient_details', {})
            if proc_recipient:
                # Recipient name
                if proc_recipient.get('name'):
                    recipient_name = Parser.extract_best_language_text(proc_recipient['name'])
                    if recipient_name:
                        procurement_info_content_parts.append(f"Procurement Recipient Name: {recipient_name}")

                # Contact person
                if proc_recipient.get('contact_person'):
                    contact_person = Parser.extract_best_language_text(proc_recipient['contact_person'])
                    if contact_person:
                        procurement_info_content_parts.append(f"Procurement Recipient Contact Person: {contact_person}")

                # Phone
                if proc_recipient.get('phone'):
                    procurement_info_content_parts.append(f"Procurement Recipient Phone: {proc_recipient['phone']}")

                # Email
                if proc_recipient.get('email'):
                    procurement_info_content_parts.append(f"Procurement Recipient Email: {proc_recipient['email']}")

                # URL
                if proc_recipient.get('url'):
                    url = Parser.extract_best_language_text(proc_recipient['url'])
                    if url:
                        procurement_info_content_parts.append(f"Procurement Recipient URL: {url}")

                # Recipient address
                recipient_address_parts = []
                if proc_recipient.get('street'):
                    street = Parser.extract_best_language_text(proc_recipient['street'])
                    if street:
                        recipient_address_parts.append(street)
                if proc_recipient.get('city'):
                    city = Parser.extract_best_language_text(proc_recipient['city'])
                    if city:
                        recipient_address_parts.append(city)
                if proc_recipient.get('postal_code'):
                    recipient_address_parts.append(str(proc_recipient['postal_code']))
                if proc_recipient.get('canton_id'):
                    recipient_address_parts.append(f"Canton: {proc_recipient['canton_id']}")
                if proc_recipient.get('country_id'):
                    recipient_address_parts.append(f"Country: {proc_recipient['country_id']}")
                if recipient_address_parts:
                    procurement_info_content_parts.append(f"Procurement Recipient Address: {', '.join(recipient_address_parts)}")

            # THE_ACTUAL_CHUNK
            if procurement_info_content_parts:
                procurement_info_chunk = {
                    'chunk_id': f"{tender_id}_procurement_info",
                    'tender_id': tender_id,
                    'content': "\n".join(procurement_info_content_parts),
                    'chunk_type': 'procurement_info',
                    'metadata': {
                        'tender_title': Parser.extract_best_language_text(tender_title),
                        'category': tender_cattegory,
                        'publication_id': pub_base,
                        'main_cpv_code': main_cpv_code,
                        'main_label': main_cpv_label,

                        'additional_cpv_code' : additional_cpv,
                        'additional_labels' : additional_label,
                        'bkp_codes' : bkp_only_list,
                        'bkp_labels' : bkp_only_labels,

                        # Office metadata
                        'office_name': Parser.extract_best_language_text(proc_office.get('name')) if proc_office.get('name') else None,
                        'office_contact_person': Parser.extract_best_language_text(proc_office.get('contact_person')) if proc_office.get('contact_person') else None,
                        'office_phone': proc_office.get('phone'),
                        'office_email': proc_office.get('email'),
                        'office_country_id': proc_office.get('country_id'),
                        'office_canton_id': proc_office.get('canton_id'),
                        'office_city': Parser.extract_best_language_text(proc_office.get('city')) if proc_office.get('city') else None,
                        'office_postal_code': proc_office.get('postal_code'),

                        # recipient metadata
                        'recipient_name': Parser.extract_best_language_text(proc_recipient.get('name')) if proc_recipient.get('name') else None,
                        'recipient_contact_person': Parser.extract_best_language_text(proc_recipient.get('contact_person')) if proc_recipient.get('contact_person') else None,
                        'recipient_phone': proc_recipient.get('phone'),
                        'recipient_email': proc_recipient.get('email'),
                        'recipient_country_id': proc_recipient.get('country_id'),
                        'recipient_canton_id': proc_recipient.get('canton_id'),
                        'recipient_city': Parser.extract_best_language_text(proc_recipient.get('city')) if proc_recipient.get('city') else None,
                        'recipient_postal_code': proc_recipient.get('postal_code'),
                    }
                }
                chunks_for_embeding.append(procurement_info_chunk)

            #====================================================================



            order_base = item.get('procurement', {})

            date_range = (order_base.get ('executionPeriod') or {}).get('dateRange', [])
            deadlines = []
            if date_range:
                for i in range(0, len(date_range), 2):
                    if i < len(date_range):
                        deadline = {
                            'Starts on: ' : date_range[i],
                            'Ends on' : date_range[i + 1] if (i + 1) < len(date_range) else None
                        }
                        deadlines.append(deadline)
            else:
                deadline = None

            adress_base = order_base.get('orderAddress', {})
            if adress_base is None:
                adress_base = {}
            procurement = {
                'supply_type' : order_base.get('supplyType', None),
                'order_desciption' : {
                    'order' : Parser.safe_html_extractor(order_base, 'orderDescription'),
                    'order_address_description' : Parser.safe_html_extractor(order_base, 'orderAddressDescription'),
                    'order_address' : {
                        'country_id' : adress_base.get('countryId', None),
                        'canton_id' : adress_base.get('cantonId', None),
                        'city' : Parser.safe_html_extractor(adress_base, 'city'),
                        'postal_code' : adress_base.get('postalCode', None)
                    },
                },
                'execution_notes_and_variants_part_off' : {
                    'execution_note' : Parser.safe_html_extractor(order_base, 'executionNote'),
                    'execution_period' : deadlines,
                    'variants_note' : Parser.safe_html_extractor(order_base, 'variantsNote'),
                    'partial_offer_note' : Parser.safe_html_extractor(order_base, 'partialOffersNote')
                },
                'contract_deadline_type' : order_base.get('contractDeadlineType', None),
                'contract_period' : order_base.get('contractPeriod', None),
                'contract_days' : order_base.get('contractDays', None),
                'can_contract_be_extendedNote' : Parser.safe_html_extractor(order_base, 'canContractBeExtendedNote'),
                'options_note' : Parser.safe_html_extractor(order_base, 'optionsNote')
            }
            #PROCUREMENT CHUNKS===================================================

            procurement_content_parts = []

            # Supply type
            if procurement.get('supply_type'):
                procurement_content_parts.append(f"Supply Type: {procurement['supply_type']}")

            # Order description
            if procurement.get('order_desciption', {}).get('order'):
                order_desc = Parser.extract_best_language_text(procurement['order_desciption']['order'])
                if order_desc:
                    procurement_content_parts.append(f"Order Description: {order_desc}")

            # Order address description
            if procurement.get('order_desciption', {}).get('order_address_description'):
                addr_desc = Parser.extract_best_language_text(procurement['order_desciption']['order_address_description'])
                if addr_desc:
                    procurement_content_parts.append(f"Order Address Description: {addr_desc}")

            order_address = procurement.get('order_desciption', {}).get('order_address', {})
            if order_address:
                address_parts = []
                if order_address.get('city'):
                    city = Parser.extract_best_language_text(order_address['city'])
                    if city:
                        address_parts.append(city)
                if order_address.get('postal_code'):
                    address_parts.append(str(order_address['postal_code']))
                if order_address.get('canton_id'):
                    address_parts.append(f"Canton: {order_address['canton_id']}")
                if order_address.get('country_id'):
                    address_parts.append(f"Country: {order_address['country_id']}")

                if address_parts:
                    procurement_content_parts.append(f"Order Address: {', '.join(address_parts)}")

            exec_variants = procurement.get('execution_notes_and_variants_part_off', {})

            if exec_variants.get('execution_note'):
                exec_note = Parser.extract_best_language_text(exec_variants['execution_note'])
                if exec_note:
                    procurement_content_parts.append(f"Execution Note: {exec_note}")

            if exec_variants.get('variants_note'):
                variants_note = Parser.extract_best_language_text(exec_variants['variants_note'])
                if variants_note:
                    procurement_content_parts.append(f"Variants Note: {variants_note}")

            if exec_variants.get('partial_offer_note'):
                partial_note = Parser.extract_best_language_text(exec_variants['partial_offer_note'])
                if partial_note:
                    procurement_content_parts.append(f"Partial Offers Note: {partial_note}")

            if procurement.get('contract_deadline_type'):
                procurement_content_parts.append(f"Contract Deadline Type: {procurement['contract_deadline_type']}")

            if procurement.get('contract_period'):
                procurement_content_parts.append(f"Contract Period: {procurement['contract_period']}")

            if procurement.get('contract_days'):
                procurement_content_parts.append(f"Contract Days: {procurement['contract_days']}")

            if procurement.get('can_contract_be_extendedNote'):
                extended_note = Parser.extract_best_language_text(procurement['can_contract_be_extendedNote'])
                if extended_note:
                    procurement_content_parts.append(f"Contract Extension Note: {extended_note}")

            if procurement.get('options_note'):
                options_note = Parser.extract_best_language_text(procurement['options_note'])
                if options_note:
                    procurement_content_parts.append(f"Options Note: {options_note}")


            #THE_ACTUAL_CHUNK
            if procurement_content_parts:
                procurement_chunk = {
                    'chunk_id': f"{tender_id}_procurement",
                    'tender_id': tender_id,
                    'content': "\n".join(procurement_content_parts),
                    'chunk_type': 'procurement',
                    'metadata': {
                        'tender_title': Parser.extract_best_language_text(tender_title),
                        'category': tender_cattegory,
                        'publication_id': pub_base,
                        'main_cpv_code': main_cpv_code,
                        'main_label': main_cpv_label,

                        'additional_cpv_code' : additional_cpv,
                        'additional_labels' : additional_label,
                        'bkp_codes' : bkp_only_list,
                        'bkp_labels' : bkp_only_labels,

                        'supply_type': procurement.get('supply_type'),
                        'contract_deadline_type': procurement.get('contract_deadline_type'),
                        'contract_period': procurement.get('contract_period'),
                        'contract_days': procurement.get('contract_days'),
                        'has_execution_periods': bool(exec_variants.get('execution_period')),
                        'execution_deadline': deadlines,

                        'order_city': Parser.extract_best_language_text(order_address.get('city')) if order_address.get('city') else None,
                        'order_canton': order_address.get('canton_id'),
                        'order_country': order_address.get('country_id'),
                        'order_postal_code': order_address.get('postal_code'),
                    }
                }
                chunks_for_embeding.append(procurement_chunk)
            #===============================================================


            #LOTS AND DOCUMENTS INFO
            project_info_base = item.get('project-info', {})
            lots_info_and_document_info = {
                'documents_costs' : {
                    'docs_price' : project_info_base.get('documentsCosts', {}).get('price', None),
                    'docs_currency' : project_info_base.get('documentsCosts', {}).get('currency', None)
                }, 
                'documents_costs_note' : Parser.safe_html_extractor(project_info_base, 'documentsCostsNote'),
                'document_source' : Parser.safe_html_extractor(project_info_base, 'documentsSourceAddress'),
                'documents_available_date' : deadlinez,
                'lots_limitation_note' : Parser.safe_html_extractor(project_info_base, 'participantLotsLimitationNote')
            }


            #LOTS + DOCUMENTS CHUNKING=========================================================================
            docs_content_parts = []

            #for metadata
            docs_price = lots_info_and_document_info.get('documents_costs', {}).get('docs_price')
            docs_currency = lots_info_and_document_info.get('documents_costs', {}).get('docs_currency')

            if lots_info_and_document_info.get('documents_costs_note'):
                costs_note = Parser.extract_best_language_text(lots_info_and_document_info['documents_costs_note'])
                if costs_note:
                    docs_content_parts.append(f"Documents Costs Note: {costs_note}")

            if lots_info_and_document_info.get('document_source'):
                source = Parser.extract_best_language_text(lots_info_and_document_info['document_source'])
                if source:
                    docs_content_parts.append(f"Documents Source Address: {source}")

            if lots_info_and_document_info.get('lots_limitation_note'):
                lots_note = Parser.extract_best_language_text(lots_info_and_document_info['lots_limitation_note'])
                if lots_note:
                    docs_content_parts.append(f"Lots Limitation Note: {lots_note}")

            # Create single chunk for all documents & lots information
            if docs_content_parts:
                docs_chunk = {
                    'chunk_id': f"{tender_id}_documents_lots",
                    'tender_id': tender_id,
                    'content': "\n".join(docs_content_parts),
                    'chunk_type': 'documents_lots',
                    'metadata': {
                        'tender_title': Parser.extract_best_language_text(tender_title),
                        'category': tender_cattegory,
                        'publication_id': pub_base,
                        'main_cpv_code': main_cpv_code,
                        'main_cpv_label': main_cpv_label,
                        'documents_price': docs_price,
                        'documents_currency': docs_currency,
                        'documents_available_from' : deadlinez
                    }
                }
                chunks_for_embeding.append(docs_chunk)

            #==================================================================================================


            #OFFER INFORMATION
            add_base = item.get('correction', {})
            offer_information = {

                'offer_specific_note' :  Parser.safe_html_extractor(project_info_base, 'offerSpecificNote'),
                'offer_deadline' : dates_base.get('offerDeadline', None),	#Needs to be converted into nice format
                'offer_validity_deadline_date' : dates_base.get('offerValidityDeadlineDate', None),
                'offer_oppening_notes' : Parser.safe_html_extractor(dates_base, 'offerOpeningNotes'),
                'offer_opening' : (dates_base.get('offerOpening') or {}).get('dateTime', None),
                'offer_oppening_postal_code' :  dates_base.get('offerOpeningPostalCode', None),
                'offer_oppening_city' : Parser.safe_html_extractor(dates_base, 'offerOpeningCity'),
                'remarks' : Parser.safe_html_extractor(add_base, 'remarks') if add_base else None , 
            }

            #OFFER INFORMATION CHUNKING======================================================================
            offer_content_parts = []

            if offer_information.get('offer_specific_note'):
                note = Parser.extract_best_language_text(offer_information['offer_specific_note'])
                if note:
                    offer_content_parts.append(f"Offer Specific Note: {note}")

            if offer_information.get('offer_deadline'):
                offer_content_parts.append(f"Offer Deadline: {offer_information['offer_deadline']}")

            if offer_information.get('offer_validity_deadline_date'):
                offer_content_parts.append(f"Offer Validity Deadline: {offer_information['offer_validity_deadline_date']}")

            if offer_information.get('offer_oppening_notes'):
                opening_notes = Parser.extract_best_language_text(offer_information['offer_oppening_notes'])
                if opening_notes:
                    offer_content_parts.append(f"Offer Opening Notes: {opening_notes}")

            if offer_information.get('offer_opening'):
                offer_content_parts.append(f"Offer Opening: {offer_information['offer_opening']}")

            if offer_information.get('offer_oppening_city'):
                city = Parser.extract_best_language_text(offer_information['offer_oppening_city'])
                if city:
                    offer_content_parts.append(f"Offer Opening City: {city}")

            if offer_information.get('remarks'):
                remarks = Parser.extract_best_language_text(offer_information['remarks'])
                if remarks:
                    offer_content_parts.append(f"Offer Remarks: {remarks}")

            if offer_content_parts:
                offer_chunk = {
                    'chunk_id': f"{tender_id}_offer_information",
                    'tender_id': tender_id,
                    'content': "\n".join(offer_content_parts),
                    'chunk_type': 'offer_information',
                    'metadata': {
                        'tender_title': Parser.extract_best_language_text(tender_title),
                        'category': tender_cattegory,
                        'publication_id': pub_base,
                        'main_cpv_code': main_cpv_code,
                        'main_label': main_cpv_label,

                        'additional_cpv_code' : additional_cpv,
                        'additional_labels' : additional_label,
                        'bkp_codes' : bkp_only_list,
                        'bkp_labels' : bkp_only_labels,

                        'offer_deadline': offer_information.get('offer_deadline'),
                        'offer_opening': offer_information.get('offer_opening')
                    }
                }
                chunks_for_embeding.append(offer_chunk)

            #================================================================================================


            #QUALIFICATIONS CRITERIA
            criteria_base = item.get('criteria', {})
            if criteria_base is None:
                criteria_base = {}

            criteria_base_list = criteria_base.get('qualificationCriteria', [])
            qualifications_criteria_list = []
            for index ,detailed in enumerate(criteria_base_list):
                qualifications_criteras_dict = {
                    'criteria_titles' : Parser.safe_html_extractor(detailed, 'title'),
                    'criteria_verification' : Parser.safe_html_extractor(detailed, 'verification'),
                    'criteria_description' : Parser.safe_html_extractor(detailed, 'description')
                }
                qualifications_criteria_list.append(qualifications_criteras_dict)


                #QUALIFICATIONS CHUNKING=====================================================================
                qualifications_content = Parser.parse_chunk_qualif(qualifications_criteras_dict)
                if qualifications_content:
                    chunk = {
                            'chunk_id': f"{tender_id}_qualification_criteria_{index:02d}",
                            'tender_id': tender_id,
                            'content': qualifications_content,
                            'chunk_type': 'qualification_criteria',
                            'metadata': {
                                'tender_title': Parser.extract_best_language_text(tender_title),
                                'category': tender_cattegory,
                                'publication_id': pub_base,
                                'main_cpv_code' : main_cpv_code,
                                'main_label' : main_cpv_label,

                                'additional_cpv_code' : additional_cpv,
                                'additional_labels' : additional_label,
                                'bkp_codes' : bkp_only_list,
                                'bkp_labels' : bkp_only_labels,

                                'qualification_criteria_index' : index,
                                'proejct_publication_date' : dates.get('publication_date'),
                                'initial_publication_date' : dates.get('inital_publication_date'),
                            }
                    }
                    chunks_for_embeding.append(chunk)
                #============================================================================================

            additional_crit_note = Parser.safe_html_extractor(criteria_base,'qualificationCriteriaNote')
            qualifications_criteria_list.append(additional_crit_note)


            #QUALIFICATION NOTE CHUNKING =========================
            additional_criteria_chunk = Parser.extract_best_language_text(additional_crit_note)
            if additional_criteria_chunk:
                note_chunk = {
                    'chunk_id': f"{tender_id}_qualification_criteria_notes",
                    'tender_id': tender_id,
                    'content': f"Additional_qualification_criteria_notes: {additional_criteria_chunk}",
                    'chunk_type': 'qualification_criteria',
                    'metadata': {
                        'tender_title': Parser.extract_best_language_text(tender_title),
                        'category': tender_cattegory,
                        'publication_id': pub_base,
                        'main_cpv_code': main_cpv_code,
                        'main_label': main_cpv_label,

                        'additional_cpv_code' : additional_cpv,
                        'additional_labels' : additional_label,
                        'bkp_codes' : bkp_only_list,
                        'bkp_labels' : bkp_only_labels,
                    }
                }
                chunks_for_embeding.append(note_chunk)
            #=======================================================
            

            #AWARD
            award_base_list = criteria_base.get('awardCriteria',[])
            award_obtaining_list = []
            for index, detail in enumerate(award_base_list):
                award_dict = {
                    'award_subtitle' : Parser.safe_html_extractor(detail, 'title'),
                    'award_description' : Parser.safe_html_extractor(detail, 'description'),
                    'award_verification' : Parser.safe_html_extractor(detail, 'verification'),
                    'price_criterion' : detail.get('isPriceCriterion', None),
                    'weighting' : detail.get('weighting', None),
                }
                award_obtaining_list.append(award_dict)
                #parse for ontents of chunks



                #AWARD CHUNKING=====================================================
                award_content = Parser.parse_for_chunk_award(award_dict)
                if award_content:
                    chunk = {
                            'chunk_id': f"{tender_id}_award_{index:02d}",
                            'tender_id': tender_id,
                            'content': award_content,
                            'chunk_type': 'award',
                            'metadata': {
                                'tender_title': Parser.extract_best_language_text(tender_title),
                                'category': tender_cattegory,
                                'publication_id': pub_base,
                                'main_cpv_code' : main_cpv_code,
                                'main_label' : main_cpv_label,

                                'additional_cpv_code' : additional_cpv,
                                'additional_labels' : additional_label,
                                'bkp_codes' : bkp_only_list,
                                'bkp_labels' : bkp_only_labels,

                                'award_index' : index,
                                'weighting' : award_dict.get('weighting'),
                                'proejct_publication_date' : dates.get('publication_date'),
                                'initial_publication_date' : dates.get('inital_publication_date'),
                            }
                    }
                    chunks_for_embeding.append(chunk)
                #===================================================================
        


            award_additional_note = Parser.safe_html_extractor(criteria_base, 'awardCriteriaNote')
            if award_additional_note:
                award_obtaining_list.append(award_additional_note)
            #AWARD NOTE CHUNKING======================================================    
            award_chk_note = Parser.extract_best_language_text(award_additional_note)
            if award_chk_note:
                note_chunk = {
                    'chunk_id': f"{tender_id}_award_notes",
                    'tender_id': tender_id,
                    'content': f"Additional_award_notes: {award_chk_note}",
                    'chunk_type': 'award_notes',
                    'metadata': {
                        'tender_title': Parser.extract_best_language_text(tender_title),
                        'category': tender_cattegory,
                        'publication_id': pub_base,
                        'main_cpv_code': main_cpv_code,
                        'main_label': main_cpv_label,
                        'additional_cpv_code' : additional_cpv,
                        'additional_labels' : additional_label,
                        'bkp_codes' : bkp_only_list,
                        'bkp_labels' : bkp_only_labels,
                    }
                }
                chunks_for_embeding.append(note_chunk)
            #==========================================================================

            #TODO  continute after criteria
            #only for award so far working well #still need to add other fields for abadonment
        
            dict_of_detailed_tenders[tender_id] = {
                'pub_id' : pub_base,	
                'id' : tender_id,
                'title' : tender_title,
                'type' : tender_type,
                'category' : tender_cattegory,
                'project_publication_date' : dates,
                'cpv_and_labels' : cpvs_list,
                'bkp_details' : bkp_list,
                'offer_information' : offer_information,
                'procurement' : procurement,
                'procurement_information' : procurement_info,
                'qualification_criteria' : qualifications_criteria_list,
                'award_criteria' : award_obtaining_list,
                'lots_and_documents_info' : lots_info_and_document_info,
                'terms_and_conditions' : terms,
                 'metadata': {
                        'tender_title': Parser.extract_best_language_text(tender_title),
                        'category': tender_cattegory,
                        'publication_id': pub_base,
                        'main_cpv_code': main_cpv_code,
                        'main_label': main_cpv_label,

                        'additional_cpv_code' : additional_cpv,
                        'additional_labels' : additional_label,
                        'bkp_codes' : bkp_only_list,
                        'bkp_labels' : bkp_only_labels,
                 }
            }
        return dict_of_detailed_tenders
    
    @staticmethod
    def parse_for_chunk_award(to_parse_award):
        chunk_data = []
        if to_parse_award['award_subtitle']:
            sub_title = Parser.extract_best_language_text(to_parse_award['award_subtitle'])
            if sub_title:
                chunk_data.append(f"Award Sub Titles: {sub_title}")
        
        if to_parse_award['award_description']:
            description =  Parser.extract_best_language_text(to_parse_award['award_description'])
            if description:
                chunk_data.append(f"Award Description: {description} ")

        if to_parse_award['award_verification']:
            award_verification = Parser.extract_best_language_text(to_parse_award['award_verification'])
            if award_verification:
                chunk_data.append(f"Award Verifications: {award_verification}")

        if to_parse_award['price_criterion']:
            price_criterion = to_parse_award['price_criterion']
            if price_criterion:
                chunk_data.append(f"Award Price Criterion: {price_criterion}")
        
        if to_parse_award['weighting']:
            award_weighting = to_parse_award['weighting']
            if award_weighting:
                chunk_data.append(f"Award Weighting: {award_weighting}")
            
        return "\n".join(chunk_data)
    

    @staticmethod
    def parse_chunk_qualif(to_parse_qualif):
        chunk_data = []
        if to_parse_qualif['criteria_titles']:
            criteria_titles = to_parse_qualif['criteria_titles']
            if criteria_titles:
                chunk_data.append(f"Qualificatoins Criteria Title: {criteria_titles}")

        if to_parse_qualif['criteria_verification']:
            crit_verif =  to_parse_qualif['criteria_verification']
            if crit_verif:
                chunk_data.append(f"Qualificatoins Criteria Verification: {crit_verif}")
        
        if to_parse_qualif['criteria_description']:
            crit_descrpit = to_parse_qualif['criteria_description']
            if crit_descrpit:
                chunk_data.append(f"Qualificatoins Criteria Description: {crit_descrpit}")
        
        return "\n".join(chunk_data)


        

class requests_simap:
    simap_base_url = 'https://www.simap.ch/api/'
    simap_url_proj_publication = 'https://www.simap.ch/api/publications/v1/project/'
    simap_url_proj_publication_details = '/publication-details/'
    @staticmethod
    def  fetch_all_tenders_rqst(all_tenders_endpoint):
        full_url = requests_simap.simap_base_url + all_tenders_endpoint
        req = None
        while req is None:
            try:
                req = requests.get(full_url)
            except requests.HTTPError as e:
                print(f'[!] Exception caught {e}')
                time.sleep(10)
        return req.json()
    
    @staticmethod
    def fetch_detailed_view_rqst(ids_list, pubs_ids_list):
        detailed_resp_list = []
        for individual_id, individual_pubs_id in zip(ids_list, pubs_ids_list):
            #print(requests_simap.simap_url_proj_publication + individual_id + requests_simap.simap_url_proj_publication_details + individual_pubs_id)
            detailed_resp = requests.get(requests_simap.simap_url_proj_publication + individual_id + requests_simap.simap_url_proj_publication_details + individual_pubs_id)
            detailed_resp_list.append(detailed_resp.json())
        
        #TODO here need to improve the lgic a bit 
        return detailed_resp_list


#function to parse the json file and add it into dict


class ExtractTendersData:
    @staticmethod
    def all_pages_and_load(base_endpoint):
        all_tenders_dct = {}
        last_item = None
        page_count = 1
        while (page_count < 5):

            curr_endpoint = base_endpoint
            #getting the curr endpoint of the new page
            if last_item:
                curr_endpoint += f"&lastItem={last_item}"
            #end of page reached

            print(f"current page being fetched: {page_count}")
            #sending new req for the new api endpoint
            resp = requests_simap.fetch_all_tenders_rqst(curr_endpoint)
            #loading it into my parser
            page_tenders = Parser.parse_json(resp)
            #updating the dictionary which is holding all tenders 
            all_tenders_dct.update(page_tenders)

            pagination = resp.get('pagination', {})
            #checking the curr page info so we enusre the end of json hase been reached
            last_item = pagination.get('lastItem')
            #checking for the items on page to be == 20
            items_per_page = pagination.get('itemsPerPage', 20)
            #checin how many tenders we got
            curr_page_count = len(resp.get('projects', []))
            print(f'Page {page_count} : curr page is {curr_page_count} with the last item being {last_item}')
            #check if end of page achived so we stop looking for items

            if not last_item or curr_page_count < items_per_page:
                break
            page_count += 1
        return all_tenders_dct

class   Converter:
    
    @staticmethod
    def merge_dictionaries(all_tenders_dict, detailed_tenders_dict):
        completed_tenders_dict = copy.deepcopy(all_tenders_dict)

        #checking for mathcking keys if so we add to the merged dict
        for item in all_tenders_dict:
            if item in detailed_tenders_dict and 'metadata' in detailed_tenders_dict[item]:
                completed_tenders_dict[item]['metadata'] = detailed_tenders_dict[item]['metadata']
            else: 
                completed_tenders_dict[item]['metadata'] = {}
    
        return completed_tenders_dict

            

    @staticmethod
    def list_converter(tenders_dict):
        tenders_lst = [value for _, value in tenders_dict.items() if value['type'] == 'tender']
        return tenders_lst
    
    def list_converter_d(tenders_dict):
        tenders_lst = [value for _, value in tenders_dict.items()]
        return tenders_lst
    
    @staticmethod
    def to_list_pub_ids(tenders_dict):
        pub_id_list = [value['publication_id'] for _, value in tenders_dict.items() if value['type'] == 'tender']
        return pub_id_list
    
    @staticmethod
    def to_list_ids(tenders_dict):
        id_list = [value['id'] for _, value in tenders_dict.items() if value['type'] == 'tender']
        return id_list


#implementing connection with the db

def connect_to_db(tenders_only_list, list_of_details):
    #acrually connecting
    try:
        conn = psycopg2.connect(
            dbname="tenderdb",
            user="tender_usr",
            password="$teMP@Pass@word!",
            host="localhost"
        )
        if conn.closed == 0:
            print("Connection with the DataBase has been succsefull !")
        else:
            print("Failed to connect")
    except Exception as e:
        return (print(f"Error while trying to connect {e}"))
    
    #define a currsor to be used for operating in the db
    curr = conn.cursor()
    for tender in tenders_only_list:
        #here we insert into the db (INSERT == )
        curr.execute("INSERT INTO tender_general_info (id, publication_id, search_index, title, " \
        "type, category, date, city, postal_code, status, metadata) VALUES "
        "(%s,%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) " \
        "ON CONFLICT (id) DO NOTHING",(
            tender.get('id'),
            tender.get('publication_id'),
            tender.get('search_index'),
            tender.get('title'),
            tender.get('type'),
            tender.get('category'),
            tender.get('date'),
            tender.get('city'),
            tender.get('postal_code'),
            tender.get('status'),
            Json(tender.get('metadata'))
        ))
    for detailed_tender in list_of_details:
        curr.execute("INSERT INTO tender_detailed_view (pub_id, uniq_id, title, type, category, " \
        "project_publication_date, cpv_and_labels, bkp_details, offer_information, " \
        "procurement, procurement_information, qualification_criteria, award_criteria, " \
        "lots_and_documents_info, terms_and_conditions, metadata) " \
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) " \
        "ON CONFLICT (pub_id) DO NOTHING" ,(
            detailed_tender.get('pub_id'),
            detailed_tender.get('id'),
            Json(detailed_tender.get('title')),
            detailed_tender.get('type'),
            detailed_tender.get('category'),
            Json(detailed_tender.get('project_publication_date')),
            Json(detailed_tender.get('cpv_and_labels')),
            Json(detailed_tender.get('bkp_details')),
            Json(detailed_tender.get('offer_information')),
            Json(detailed_tender.get('procurement')),
            Json(detailed_tender.get('procurement_information')),
            Json(detailed_tender.get('qualification_criteria')),
            Json(detailed_tender.get('award_criteria')),
            Json(detailed_tender.get('lots_and_documents_info')),
            Json(detailed_tender.get('terms_and_conditions')),
            Json(detailed_tender.get('metadata'))
        ))


    conn.commit()
    curr.close()
    conn.close()
    #for tender in 



def main():
    all_tenders_endpoint = 'publications/v2/project/project-search?search=all'
    #individual_tenders_endpoint = 'publications/v1/project'


    all_tenders = ExtractTendersData.all_pages_and_load(all_tenders_endpoint)
    #pprint.pprint(pubs_ids_list)

    print()

    #pprint.pprint(ids_list)


    #TODO I have an api issue when trying to reach tyhe next endpoint of it... I don t know if i should switch to fastapi first or fix ??


    #TODO
    #detailed_dict = get_detailed_view(all_tenders)


    pubs_ids_list = Converter.to_list_pub_ids(all_tenders)
    ids_list = Converter.to_list_ids(all_tenders)
    response = requests_simap.fetch_detailed_view_rqst(ids_list, pubs_ids_list)
    detailes_of_tenders = Parser.parse_each_detailed_tender(response)  
    completed_tender_dictionary = Converter.merge_dictionaries(all_tenders, detailes_of_tenders)

    tenders_only_list = Converter.list_converter(completed_tender_dictionary)
    list_of_details = Converter.list_converter_d(detailes_of_tenders)
    connect_to_db(tenders_only_list, list_of_details)
    
    
    

if __name__ == "__main__":
    main()

    '''df = pd.DataFrame(tenders_only_list)
    df.to_csv('Tenders.csv', index=False)'''
''' df = pd.DataFrame(list_of_details)
 df.to_csv('DetailedTenders.csv', index=False)'''
'''
    Checks if the Python file is being run directly (not imported)
    Only executes the code inside the if block when the script is the main program
    It's how Python is saying "only run this code if I'm the main program."
'''