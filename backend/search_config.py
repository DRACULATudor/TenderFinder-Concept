import os
import tantivy


INDEX_PATH = "search_index"
if not os.path.exists(INDEX_PATH):
    os.makedirs(INDEX_PATH)

#define schema(blueprint)
schemabuilder = tantivy.SchemaBuilder()


#first get id for fast lookup in cache, we retireve it now
#tokenizer set to raw so nothing gets parsed
schemabuilder.add_text_field("id", stored=True, tokenizer_name="raw")
schemabuilder.add_text_field("pub_id", stored=True, tokenizer_name="raw")
schemabuilder.add_text_field("main_cpv_code", stored=True, tokenizer_name="raw")
schemabuilder.add_text_field("additional_cpv_code", stored=True, tokenizer_name="raw")
schemabuilder.add_text_field("bkp_codes", stored=True, tokenizer_name="raw")


#same approach for title, but no more need to tokenize, we can rely
#on the default tokniser, added muti val since both add_lables are lists
schemabuilder.add_text_field("title", stored=True)
schemabuilder.add_text_field("category", stored=True)
schemabuilder.add_text_field("main_label", stored=True)
schemabuilder.add_text_field("additional_labels", stored=True)
schemabuilder.add_text_field("bkp_labels", stored=True)



schemabuilder.add_text_field("full_text", stored=True)

schema = schemabuilder.build()

