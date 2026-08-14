import os
import pandas as pd
import requests
import chromadb
import zipfile
import xml.etree.ElementTree as ET
import sqlite3

EXCEL_PATH = '/Users/sarathkumar/christu-chatbot-docs/output/christ_university_chatbot_knowledge.xlsx'
CHROMA_DIR = '/Users/sarathkumar/.gemini/antigravity-ide/scratch/college-chatbot/data/chroma_db'
DB_PATH = '/Users/sarathkumar/.gemini/antigravity-ide/scratch/college-chatbot/db/grievances.db'
OLLAMA_EMBED_URL = 'http://localhost:11434/api/embed'
MODEL_NAME = 'nomic-embed-text'

def extract_docx_text(docx_path):
    if not os.path.exists(docx_path):
        return ""
    try:
        with zipfile.ZipFile(docx_path) as z:
            xml_content = z.read('word/document.xml')
            root = ET.fromstring(xml_content)
            texts = []
            for elem in root.iter():
                if elem.tag.endswith('t'):
                    if elem.text:
                        texts.append(elem.text)
            return " ".join(texts)
    except Exception as e:
        print(f"Error reading docx {docx_path}: {e}")
        return ""

def get_embeddings(texts):
    try:
        res = requests.post(OLLAMA_EMBED_URL, json={
            "model": MODEL_NAME,
            "input": texts
        }, timeout=60)
        res.raise_for_status()
        return res.json()["embeddings"]
    except Exception as e:
        print(f"Error calling Ollama embedding API: {e}")
        return None

def main():
    print("Initializing ChromaDB at:", CHROMA_DIR)
    chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
    
    # Reset or get collection
    try:
        chroma_client.delete_collection("christ_university_knowledge")
    except Exception:
        pass
    collection = chroma_client.create_collection("christ_university_knowledge")
    
    # We will also insert files in sqlite source_documents
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    documents_to_add = []
    
    # 1. Campuses
    print("Processing Campuses...")
    df_campuses = pd.read_excel(EXCEL_PATH, sheet_name='Campuses')
    for idx, row in df_campuses.iterrows():
        campus = str(row.get('campus', '')).strip()
        url = str(row.get('url', '')).strip()
        emails = str(row.get('emails', '')).strip()
        phones = str(row.get('phones', '')).strip()
        addresses = str(row.get('addresses', '')).strip()
        summary = str(row.get('summary', '')).strip()
        
        text = f"Campus Name: {campus}\nURL: {url}\nEmails: {emails}\nPhones: {phones}\nAddress: {addresses}\nSummary: {summary}"
        doc_id = f"campus_{idx}"
        
        metadata = {
            "source_url": url,
            "campus": campus,
            "category": "general",
            "doc_type": "campus_info"
        }
        documents_to_add.append((doc_id, text, metadata))
        
        # Save to SQLite source_documents
        try:
            cursor.execute("INSERT OR REPLACE INTO source_documents (url, category, campus) VALUES (?, ?, ?)", (url, "general", campus))
        except Exception:
            pass

    # 2. Departments
    print("Processing Departments...")
    df_depts = pd.read_excel(EXCEL_PATH, sheet_name='Departments')
    for idx, row in df_depts.iterrows():
        title = str(row.get('title', '')).strip()
        url = str(row.get('url', '')).strip()
        dept_id = str(row.get('dept_id', '')).strip()
        division_id = str(row.get('division_id', '')).strip()
        
        # Deduce campus from URL if possible
        campus = "all"
        if "bangalore-central" in url or "central-campus" in url:
            campus = "Bangalore Central Campus"
        elif "bannerghatta" in url:
            campus = "Bangalore Bannerghatta Road Campus"
        elif "kengeri" in url:
            campus = "Bangalore Kengeri Campus"
        elif "yeshwanthpur" in url:
            campus = "Bangalore Yeshwanthpur Campus"
        elif "ncr" in url:
            campus = "Delhi NCR Campus"
        elif "lavasa" in url:
            campus = "Pune Lavasa Campus"
            
        text = f"Department Name: {title}\nURL: {url}\nDepartment ID: {dept_id}\nDivision ID: {division_id}"
        doc_id = f"dept_{idx}"
        
        metadata = {
            "source_url": url,
            "campus": campus,
            "category": "academic",
            "doc_type": "department_info"
        }
        documents_to_add.append((doc_id, text, metadata))
        
        try:
            cursor.execute("INSERT OR REPLACE INTO source_documents (url, category, campus) VALUES (?, ?, ?)", (url, "academic", campus))
        except Exception:
            pass

    # 3. Faculty
    print("Processing Faculty...")
    df_faculty = pd.read_excel(EXCEL_PATH, sheet_name='Faculty')
    for idx, row in df_faculty.iterrows():
        name = str(row.get('name', '')).strip()
        dept = str(row.get('department', '')).strip()
        spec = str(row.get('specialization', '')).strip()
        email = str(row.get('email', '')).strip()
        all_emails = str(row.get('all_emails', '')).strip()
        phone = str(row.get('phone', '')).strip()
        desig = str(row.get('designation', '')).strip()
        qual = str(row.get('qualification', '')).strip()
        area_spec = str(row.get('area_of_specialisation', '')).strip()
        profile_url = str(row.get('profile_url', '')).strip()
        dept_id = str(row.get('dept_id', '')).strip()
        
        text = f"Faculty Member Name: {name}\nDesignation: {desig}\nDepartment: {dept} (Dept ID: {dept_id})\nQualification: {qual}\nSpecialization: {spec}\nArea of Specialisation: {area_spec}\nEmail: {email} (Alternative: {all_emails})\nPhone: {phone}\nProfile Link: {profile_url}"
        doc_id = f"faculty_{idx}"
        
        # Deduce campus from specialization or department name if possible
        campus = "all"
        
        metadata = {
            "source_url": profile_url,
            "campus": campus,
            "category": "faculty",
            "doc_type": "faculty_profile"
        }
        documents_to_add.append((doc_id, text, metadata))

    # 4. Grievance_References
    print("Processing Grievance References...")
    df_grievances = pd.read_excel(EXCEL_PATH, sheet_name='Grievance_References')
    for idx, row in df_grievances.iterrows():
        cat = str(row.get('category', '')).strip()
        label = str(row.get('label', '')).strip()
        url = str(row.get('url', '')).strip()
        fmt = str(row.get('format', '')).strip()
        src_page = str(row.get('source_page', '')).strip()
        notes = str(row.get('notes', '')).strip()
        
        text = f"Grievance Category: {cat}\nTopic: {label}\nFormat: {fmt}\nReference URL: {url}\nSource Page: {src_page}\nNotes: {notes}"
        doc_id = f"grievance_ref_{idx}"
        
        metadata = {
            "source_url": url or src_page,
            "campus": "all",
            "category": "grievance_policy",
            "doc_type": "grievance_reference"
        }
        documents_to_add.append((doc_id, text, metadata))
        
        try:
            cursor.execute("INSERT OR REPLACE INTO source_documents (url, category, campus) VALUES (?, ?, ?)", (url or src_page, "grievance_policy", "all"))
        except Exception:
            pass

    # 5. Native Docx files
    print("Processing Native Docx files...")
    df_docx = pd.read_excel(EXCEL_PATH, sheet_name='Native_Docx_Xlsx')
    for idx, row in df_docx.iterrows():
        label = str(row.get('label', '')).strip()
        url = str(row.get('url', '')).strip()
        local_path = str(row.get('local_path', '')).strip()
        
        extracted = extract_docx_text(local_path)
        if extracted:
            text = f"Document Title: {label}\nSource URL: {url}\nFile Content:\n{extracted}"
            # Chunk it if it's too long
            chunk_size = 1500
            for c_idx in range(0, len(text), chunk_size):
                chunk_text = text[c_idx:c_idx+chunk_size]
                doc_id = f"native_docx_{idx}_{c_idx}"
                metadata = {
                    "source_url": url,
                    "campus": "all",
                    "category": "grievance_policy",
                    "doc_type": "handbook"
                }
                documents_to_add.append((doc_id, chunk_text, metadata))
        else:
            text = f"Document Metadata: {label}\nSource URL: {url}"
            doc_id = f"native_docx_{idx}"
            metadata = {
                "source_url": url,
                "campus": "all",
                "category": "grievance_policy",
                "doc_type": "handbook"
            }
            documents_to_add.append((doc_id, text, metadata))

    # Commit SQLite source documents
    conn.commit()
    conn.close()

    # Now batch insert into Chroma
    print(f"Embedding and storing {len(documents_to_add)} documents in Chroma DB...")
    
    batch_size = 100
    for i in range(0, len(documents_to_add), batch_size):
        batch = documents_to_add[i:i+batch_size]
        ids = [item[0] for item in batch]
        texts = [item[1] for item in batch]
        metadatas = [item[2] for item in batch]
        
        embeddings = get_embeddings(texts)
        if embeddings is None:
            print(f"Skipping batch {i} to {i+len(batch)} due to embedding failure")
            continue
            
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )
        print(f"Stored batch {i + len(batch)} / {len(documents_to_add)}")
        
    print("Ingestion complete!")

if __name__ == "__main__":
    main()
