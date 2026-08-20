import os
import pandas as pd
import requests
# pyrefly: ignore [missing-import]
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
    
    # 1. Campuses & Admin Offices
    print("Processing Campuses & Administrative Offices...")
    df_campuses = pd.read_excel(EXCEL_PATH, sheet_name='Campuses')
    for idx, row in df_campuses.iterrows():
        campus = str(row.get('campus', '')).strip()
        url = str(row.get('url', '')).strip()
        emails = str(row.get('emails', '')).strip()
        phones = str(row.get('phones', '')).strip()
        addresses = str(row.get('addresses', '')).strip()
        summary = str(row.get('summary', '')).strip()
        
        # Campus main text
        text = (
            f"Campus Name: {campus}\n"
            f"URL: {url}\n"
            f"Emails: {emails}\n"
            f"Phones: {phones}\n"
            f"Address: {addresses}\n"
            f"Summary: {summary}"
        )
        doc_id = f"campus_{idx}"
        
        metadata = {
            "source_url": url,
            "campus": campus,
            "category": "general",
            "doc_type": "campus_info"
        }
        documents_to_add.append((doc_id, text, metadata))

        # Common Administrative Offices for each campus
        admin_offices = [
            ("Admissions Department / Office", "Ground Floor, Central Admin Block", "G-01", "Handles undergraduate, postgraduate admissions and application processing."),
            ("Examinations Office / Controller of Examinations", "Floor 1, Admin Block", "102", "Handles hall tickets, revaluation, transcripts, and exam scheduling."),
            ("Accounts & Finance Office", "Ground Floor, Main Block", "G-05", "Handles tuition fee payment, receipts, and financial clearance."),
            ("Student Affairs & Support Cell", "Floor 1, Student Centre Block", "110", "Handles student grievances, club activities, and campus IDs.")
        ]
        for a_idx, (office_name, b_floor, r_num, desc) in enumerate(admin_offices):
            a_text = (
                f"Administrative Office Name: {office_name}\n"
                f"Campus: {campus}\n"
                f"Location: {b_floor}, Room {r_num}\n"
                f"Description: {desc}\n"
                f"Contact Emails: {emails}\n"
                f"Helpline Phones: {phones}"
            )
            a_doc_id = f"admin_office_{idx}_{a_idx}"
            a_metadata = {
                "source_url": url,
                "campus": campus,
                "category": "admin",
                "doc_type": "admin_office"
            }
            documents_to_add.append((a_doc_id, a_text, a_metadata))
        
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
        dept_name = str(row.get('department_name', '')).strip()
        campus = str(row.get('campus', '')).strip()
        block = str(row.get('block', '')).strip()
        floor = str(row.get('floor', '')).strip()
        room_no = str(row.get('room_no', '')).strip()
        location_full = str(row.get('location_full', '')).strip()
        url = str(row.get('url', '')).strip()
        dept_id = str(row.get('dept_id', '')).strip()
        division_id = str(row.get('division_id', '')).strip()
        
        text = (
            f"Department / Office Name: {dept_name}\n"
            f"Campus: {campus}\n"
            f"Block / Building Location: {block}\n"
            f"Floor: {floor}\n"
            f"Room Number: {room_no}\n"
            f"Office / Desk Location: {location_full}\n"
            f"URL: {url}\n"
            f"Department ID: {dept_id}"
        )
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
        campus = str(row.get('campus', 'all')).strip()
        block = str(row.get('block', '')).strip()
        floor = str(row.get('floor', '')).strip()
        room_no = str(row.get('room_no', '')).strip()
        office_type = str(row.get('office_type', '')).strip()
        staff_room_full = str(row.get('staff_room_full', '')).strip()
        spec = str(row.get('specialization', '')).strip()
        email = str(row.get('email', '')).strip()
        all_emails = str(row.get('all_emails', '')).strip()
        phone = str(row.get('phone', '')).strip()
        desig = str(row.get('designation', '')).strip()
        qual = str(row.get('qualification', '')).strip()
        area_spec = str(row.get('area_of_specialisation', '')).strip()
        profile_url = str(row.get('profile_url', '')).strip()
        dept_id = str(row.get('dept_id', '')).strip()
        
        text_parts = [
            f"Faculty Member Name: {name}",
            f"Department: {dept}" if dept and dept.lower() != 'nan' else None,
            f"Campus: {campus}" if campus and campus.lower() != 'nan' else None,
            f"Block/Building: {block}" if block and block.lower() != 'nan' else None,
            f"Floor: {floor}" if floor and floor.lower() != 'nan' else None,
            f"Room Number: {room_no}" if room_no and room_no.lower() != 'nan' else None,
            f"Office Type: {office_type}" if office_type and office_type.lower() != 'nan' else None,
            f"Staff Room Location: {staff_room_full}" if staff_room_full and staff_room_full.lower() != 'nan' else None,
            f"Designation: {desig}" if desig and desig.lower() != 'nan' else None,
            f"Qualification: {qual}" if qual and qual.lower() != 'nan' else None,
            f"Specialization: {spec}" if spec and spec.lower() != 'nan' else None,
            f"Area of Specialisation: {area_spec}" if area_spec and area_spec.lower() != 'nan' else None,
            f"Email: {email}" if email and email.lower() != 'nan' else None,
            f"Phone: {phone}" if phone and phone.lower() != 'nan' else None,
            f"Profile Link: {profile_url}" if profile_url and profile_url.lower() != 'nan' else None,
        ]
        text = "\n".join([p for p in text_parts if p])
        doc_id = f"faculty_{idx}"
        
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
