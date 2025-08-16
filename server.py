#!/usr/bin/env python3
"""
Server per importazione CSV in Notion - VERSIONE FINALE CORRETTA
Gestisce upload, parsing, mapping, correzione comuni e import massivo
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse
import csv
import io
import base64
import time
import re
from difflib import SequenceMatcher
import traceback
from datetime import datetime
import os

# Configurazione - Leggi da variabili di ambiente
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
CONTATTI_DB_ID = os.environ.get("CONTATTI_DB_ID")
COMUNI_DB_ID = os.environ.get("COMUNI_DB_ID")

# OpenAI API Key - opzionale
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Cache per i comuni
COMUNI_CACHE = {}

# Tracking correzioni AI
AI_CORRECTIONS = []

class CSVImportHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        """Override per logging più pulito"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] {format % args}")
    
    def end_headers(self):
        """Override per aggiungere sempre headers CORS"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Accept')
        super().end_headers()
    
    def do_OPTIONS(self):
        """Gestisce preflight CORS"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
    
    def do_GET(self):
        """Gestisce richieste GET"""
        if self.path == '/':
            try:
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                
                with open('index.html', 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.wfile.write(content.encode('utf-8'))
                    
            except FileNotFoundError:
                self.send_error(404, "File index.html non trovato")
                
        elif self.path == '/favicon.ico':
            self.send_response(204)  # No Content
            self.end_headers()
            
        else:
            self.send_error(404, "Pagina non trovata")
    
    def do_POST(self):
        """Gestisce richieste POST"""
        try:
            print(f"[POST] Richiesta a: {self.path}")
            
            # Leggi il body
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length) if content_length > 0 else b''
            
            # Parse JSON
            data = {}
            if post_data:
                try:
                    data = json.loads(post_data.decode('utf-8'))
                except json.JSONDecodeError as e:
                    print(f"[ERROR] JSON decode: {e}")
                    self.send_json_error("Invalid JSON", 400)
                    return
            
            # Router
            if self.path == '/test-connection':
                self.handle_test_connection()
            elif self.path == '/parse-and-import':
                self.handle_parse_and_import(data)
            else:
                self.send_json_error(f"Endpoint '{self.path}' non trovato", 404)
                
        except Exception as e:
            print(f"[ERROR] Errore POST: {str(e)}")
            traceback.print_exc()
            self.send_json_error(f"Errore server: {str(e)}", 500)
    
    def handle_test_connection(self):
        """Test connessione Notion"""
        print("[TEST] Test connessione Notion...")
        
        try:
            headers = {
                'Authorization': f'Bearer {NOTION_TOKEN}',
                'Notion-Version': '2022-06-28'
            }
            
            req = urllib.request.Request(
                'https://api.notion.com/v1/users/me',
                headers=headers
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                
                user_name = data.get('name', 'Utente sconosciuto')
                user_type = data.get('type', 'Unknown')
                
                print(f"[TEST] ✅ Connessione OK - Utente: {user_name}")
                
                self.send_json_response({
                    'success': True,
                    'user': user_name,
                    'type': user_type
                })
                
        except Exception as e:
            error_msg = f"Errore connessione Notion: {str(e)}"
            print(f"[TEST] ❌ {error_msg}")
            self.send_json_error(error_msg, 500)
    
    def handle_parse_and_import(self, data):
        """Parse CSV e importa contatti"""
        global COMUNI_CACHE, AI_CORRECTIONS
        
        try:
            print("[IMPORT] === INIZIO IMPORTAZIONE ===")
            
            # Validazione input
            if not data.get('content'):
                raise ValueError("Content CSV mancante")
                
            if not data.get('mapping'):
                raise ValueError("Mapping mancante")
                
            mapping = data['mapping']
            if not mapping.get('email'):
                raise ValueError("Mapping email primaria mancante")
            
            print(f"[IMPORT] Mapping: {mapping}")
            
            # Decodifica CSV
            try:
                csv_content = base64.b64decode(data['content'])
                print(f"[IMPORT] CSV decodificato: {len(csv_content)} bytes")
            except Exception as e:
                raise ValueError(f"Errore decodifica base64: {str(e)}")
            
            # Prova encoding
            text_content = None
            for enc in ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']:
                try:
                    text_content = csv_content.decode(enc)
                    print(f"[IMPORT] Encoding: {enc}")
                    break
                except UnicodeDecodeError:
                    continue
            
            if not text_content:
                raise ValueError("Impossibile decodificare CSV")
            
            # Parse CSV
            text_content = text_content.replace('\r\n', '\n').replace('\r', '\n')
            reader = csv.DictReader(io.StringIO(text_content))
            rows = list(reader)
            
            if not rows:
                raise ValueError("CSV vuoto")
                
            print(f"[IMPORT] Righe da importare: {len(rows)}")
            
            # Reset cache e tracking
            COMUNI_CACHE = {}
            AI_CORRECTIONS = []
            
            # Risultati
            results = {
                'success': 0,
                'errors': [],
                'comuni_corretti': [],
                'comuni_non_trovati': [],
                'contatti_non_importati': []  # Nuova lista per contatti completi non importati
            }
            
            # Import batch
            batch_size = 5
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i+batch_size]
                batch_num = i // batch_size + 1
                
                print(f"[IMPORT] Batch {batch_num}: righe {i+1}-{min(i+batch_size, len(rows))}")
                
                for idx, row in enumerate(batch):
                    row_num = i + idx + 1
                    
                    try:
                        if row_num % 10 == 0:
                            print(f"[IMPORT] Riga {row_num}/{len(rows)}")
                        
                        result = self.create_contact(row, mapping)
                        
                        if result.get('success'):
                            results['success'] += 1
                            
                            if result.get('comune_corretto'):
                                results['comuni_corretti'].append({
                                    'originale': result['comune_originale'],
                                    'corretto': result['comune_corretto']
                                })
                            elif result.get('comune_non_trovato'):
                                if result['comune_non_trovato'] not in results['comuni_non_trovati']:
                                    results['comuni_non_trovati'].append(result['comune_non_trovato'])
                                
                                # Aggiungi il contatto completo non importato
                                contact_data = {}
                                for field, column in mapping.items():
                                    if column in row:
                                        contact_data[field] = row[column].strip()
                                contact_data['_comune_non_trovato'] = result['comune_non_trovato']
                                contact_data['_row_number'] = row_num
                                results['contatti_non_importati'].append(contact_data)
                        else:
                            results['errors'].append({
                                'row': row_num,
                                'error': result.get('error', 'Errore sconosciuto')
                            })
                            
                            # Aggiungi anche agli errori il contatto completo
                            contact_data = {}
                            for field, column in mapping.items():
                                if column in row:
                                    contact_data[field] = row[column].strip()
                            contact_data['_error'] = result.get('error', 'Errore sconosciuto')
                            contact_data['_row_number'] = row_num
                            if contact_data not in results['contatti_non_importati']:
                                results['contatti_non_importati'].append(contact_data)
                            
                    except Exception as e:
                        print(f"[IMPORT] Errore riga {row_num}: {e}")
                        results['errors'].append({
                            'row': row_num,
                            'error': str(e)
                        })
                
                # Pausa tra batch
                if i + batch_size < len(rows):
                    time.sleep(2)
            
            print(f"[IMPORT] === COMPLETATO ===")
            print(f"[IMPORT] Successi: {results['success']}")
            print(f"[IMPORT] Errori: {len(results['errors'])}")
            
            # Aggiungi correzioni AI ai risultati
            if AI_CORRECTIONS:
                print(f"\n[AI] === CORREZIONI CON INTELLIGENZA ARTIFICIALE ===")
                print(f"[AI] Totale correzioni: {len(AI_CORRECTIONS)}")
                for corr in AI_CORRECTIONS:
                    print(f"[AI] {corr['timestamp']} - '{corr['originale']}' → '{corr['corretto']}'")
                results['ai_corrections'] = AI_CORRECTIONS
            
            self.send_json_response({
                'success': True,
                'results': results
            })
            
        except Exception as e:
            error_msg = str(e)
            print(f"[IMPORT] ❌ Errore: {error_msg}")
            traceback.print_exc()
            self.send_json_error(error_msg, 500)
    
    def extract_comune_from_email(self, email):
        """Estrae il possibile nome del comune dall'email"""
        if not email:
            return None
            
        email_lower = email.lower()
        
        # Pattern comuni per email istituzionali
        patterns = [
            r'@comune\.([^.]+)\.',  # @comune.barzano.lc.it
            r'@comunedi([^.@]+)\.',  # @comunedibarzano.it
            r'@comune-([^.]+)\.',    # @comune-barzano.it
            r'comune\.([^.@]+)@',    # comune.barzano@...
            r'@([^.]+)\.gov\.it',    # @barzano.gov.it
        ]
        
        for pattern in patterns:
            match = re.search(pattern, email_lower)
            if match:
                comune = match.group(1)
                # Rimuovi caratteri speciali e capitalizza
                comune = comune.replace('-', ' ').replace('_', ' ')
                comune = ' '.join(word.capitalize() for word in comune.split())
                print(f"[EMAIL] Estratto comune dall'email: {comune}")
                return comune
                
        return None
    
    def search_comune_with_openai(self, nome_originale, email_hint=None):
        """Usa OpenAI per trovare varianti del nome comune"""
        if not OPENAI_API_KEY or not OPENAI_API_KEY.startswith('sk-'):
            return None
            
        # Prima prova a estrarre il comune dall'email
        if email_hint:
            extracted_comune = self.extract_comune_from_email(email_hint)
            if extracted_comune:
                print(f"[OPENAI] Provo prima con comune estratto dall'email: {extracted_comune}")
                # Verifica se il comune estratto esiste
                test_result = self.search_comune_on_notion_direct(extracted_comune)
                if test_result:
                    print(f"[OPENAI] Comune trovato dall'email: {extracted_comune}")
                    AI_CORRECTIONS.append({
                        'originale': nome_originale,
                        'corretto': extracted_comune,
                        'timestamp': datetime.now().strftime('%H:%M:%S'),
                        'metodo': 'email'
                    })
                    return extracted_comune
        
        try:
            headers = {
                'Authorization': f'Bearer {OPENAI_API_KEY}',
                'Content-Type': 'application/json'
            }
            
            # Aggiungi hint dall'email se disponibile
            email_info = ""
            if email_hint:
                email_info = f"\nEmail associata (potrebbe contenere il nome del comune): {email_hint}"
            
            prompt = f"""Il seguente nome di comune italiano potrebbe avere errori di battitura, abbreviazioni o varianti.
Fornisci SOLO il nome corretto del comune italiano, senza spiegazioni aggiuntive.
Se non è un comune italiano valido, rispondi solo con "NON_TROVATO".

Nome da correggere: {nome_originale}{email_info}

Esempi di correzioni:
- "S. Giovanni" → "San Giovanni"
- "Barzano'" → "Barzanò"
- "Male'" → "Malè"
- "Baselga Di Pine'" → "Baselga di Pinè"

Se l'email contiene "comune.barzano" o simili, il comune è probabilmente "Barzanò".

Risposta:"""
            
            body = {
                'model': 'gpt-4o-mini',  # Cambiato a modello esistente
                'messages': [
                    {'role': 'system', 'content': 'Sei un esperto di geografia italiana. Rispondi SOLO con il nome corretto del comune o "NON_TROVATO".'},
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': 0.1,
                'max_tokens': 50
            }
            
            req = urllib.request.Request(
                'https://api.openai.com/v1/chat/completions',
                data=json.dumps(body).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                suggested_name = data['choices'][0]['message']['content'].strip()
                
                if suggested_name and suggested_name != 'NON_TROVATO':
                    print(f"[OPENAI] Suggerimento per '{nome_originale}': '{suggested_name}'")
                    # Registra la correzione
                    AI_CORRECTIONS.append({
                        'originale': nome_originale,
                        'corretto': suggested_name,
                        'timestamp': datetime.now().strftime('%H:%M:%S')
                    })
                    return suggested_name
                    
            return None
            
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8') if e.read() else 'No error body'
            print(f"[OPENAI] Errore HTTP {e.code}: {e.reason}")
            print(f"[OPENAI] Dettagli: {error_body}")
            
            # Se il problema è il modello, suggerisci alternative
            if 'model' in error_body.lower():
                print("[OPENAI] Nota: Il modello potrebbe non essere disponibile. Modelli validi: gpt-4o-mini, gpt-4o, gpt-3.5-turbo")
            return None
        except Exception as e:
            print(f"[OPENAI] Errore generico: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def search_comune_on_notion(self, nome, email_hint=None):
        """Cerca comune su Notion"""
        global COMUNI_CACHE
        
        if not nome or not nome.strip():
            return None
            
        nome = nome.strip()
        nome_lower = nome.lower()
        
        # Cache check
        if nome_lower in COMUNI_CACHE:
            return COMUNI_CACHE[nome_lower]
        
        try:
            headers = {
                'Authorization': f'Bearer {NOTION_TOKEN}',
                'Notion-Version': '2022-06-28',
                'Content-Type': 'application/json'
            }
            
            # Ricerca esatta
            body = {
                'filter': {
                    'property': 'Name',
                    'title': {'equals': nome}
                },
                'page_size': 1
            }
            
            req = urllib.request.Request(
                f'https://api.notion.com/v1/databases/{COMUNI_DB_ID}/query',
                data=json.dumps(body).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                if data['results']:
                    comune_id = data['results'][0]['id']
                    comune_nome = data['results'][0]['properties']['Name']['title'][0]['plain_text']
                    COMUNI_CACHE[nome_lower] = {'id': comune_id, 'nome': comune_nome}
                    print(f"[COMUNE] ✓ Trovato: {comune_nome}")
                    return {'id': comune_id, 'nome': comune_nome}
            
            # Ricerca fuzzy
            body = {
                'filter': {
                    'property': 'Name',
                    'title': {'contains': nome}
                },
                'page_size': 10
            }
            
            req = urllib.request.Request(
                f'https://api.notion.com/v1/databases/{COMUNI_DB_ID}/query',
                data=json.dumps(body).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                
                # Match case-insensitive
                for result in data['results']:
                    comune_nome = result['properties']['Name']['title'][0]['plain_text']
                    if comune_nome.lower() == nome_lower:
                        comune_id = result['id']
                        COMUNI_CACHE[nome_lower] = {'id': comune_id, 'nome': comune_nome}
                        print(f"[COMUNE] ✓ Trovato (fuzzy): {comune_nome}")
                        return {'id': comune_id, 'nome': comune_nome}
                
                # Best match
                if len(data['results']) == 1:
                    result = data['results'][0]
                    comune_id = result['id']
                    comune_nome = result['properties']['Name']['title'][0]['plain_text']
                    COMUNI_CACHE[nome_lower] = {'id': comune_id, 'nome': comune_nome}
                    print(f"[COMUNE] ✓ Trovato (unico): {comune_nome}")
                    return {'id': comune_id, 'nome': comune_nome}
            
            # Se non trovato, prova con OpenAI per trovare varianti
            print(f"[COMUNE] Non trovato direttamente, provo con OpenAI: {nome}")
            if email_hint:
                print(f"[COMUNE] Email hint: {email_hint}")
            suggested_name = self.search_comune_with_openai(nome, email_hint)
            
            if suggested_name:
                # Riprova la ricerca con il nome suggerito
                print(f"[COMUNE] Riprovo con nome suggerito: {suggested_name}")
                suggested_result = self.search_comune_on_notion_direct(suggested_name)
                if suggested_result:
                    COMUNI_CACHE[nome_lower] = suggested_result
                    return suggested_result
            
            print(f"[COMUNE] ✗ Non trovato: {nome}")
            COMUNI_CACHE[nome_lower] = None
            return None
            
        except Exception as e:
            print(f"[COMUNE] Errore: {e}")
            return None
    
    def search_comune_on_notion_direct(self, nome):
        """Ricerca diretta su Notion senza cache o OpenAI"""
        try:
            headers = {
                'Authorization': f'Bearer {NOTION_TOKEN}',
                'Notion-Version': '2022-06-28',
                'Content-Type': 'application/json'
            }
            
            # Ricerca esatta
            body = {
                'filter': {
                    'property': 'Name',
                    'title': {'equals': nome}
                },
                'page_size': 1
            }
            
            req = urllib.request.Request(
                f'https://api.notion.com/v1/databases/{COMUNI_DB_ID}/query',
                data=json.dumps(body).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                if data['results']:
                    comune_id = data['results'][0]['id']
                    comune_nome = data['results'][0]['properties']['Name']['title'][0]['plain_text']
                    print(f"[COMUNE] ✓ Trovato con OpenAI: {nome} → {comune_nome}")
                    return {'id': comune_id, 'nome': comune_nome}
            
            return None
            
        except Exception as e:
            print(f"[COMUNE] Errore ricerca diretta: {e}")
            return None

    def create_contact(self, row, mapping):
        """Crea contatto in Notion"""
        try:
            # Email obbligatoria
            email_column = mapping.get('email', '')
            email = row.get(email_column, '').strip() if email_column else ''
            
            if not email:
                return {'success': False, 'error': f'Email mancante'}
            
            # Proprietà base
            properties = {
                'Email primaria': {
                    'title': [{'text': {'content': email}}]
                }
            }
            
            # Altri campi
            field_mapping = {
                'nome': ('Nome e cognome', 'rich_text'),
                'carica': ('Carica', 'rich_text'),
                'indirizzo': ('Indirizzo', 'rich_text'),
                'email2': ('Email 2', 'email'),
                'email3': ('Email 3', 'email'),
                'telefono': ('Telefono', 'phone_number'),
                'cellulare': ('Cellulare', 'phone_number'),
                'sito': ('Sito web', 'url'),
            }
            
            for field, (notion_field, field_type) in field_mapping.items():
                if field in mapping and mapping[field] in row:
                    value = row[mapping[field]].strip()
                    if value:
                        if field_type == 'rich_text':
                            properties[notion_field] = {
                                'rich_text': [{'text': {'content': value}}]
                            }
                        elif field_type == 'email' and '@' in value:
                            properties[notion_field] = {'email': value}
                        elif field_type == 'phone_number':
                            properties[notion_field] = {'phone_number': value}
                        elif field_type == 'url':
                            if not value.startswith(('http://', 'https://')):
                                value = 'https://' + value
                            properties[notion_field] = {'url': value}
            
            # Tipo di contatto
            if 'tipo' in mapping and mapping['tipo'] in row:
                tipo = row[mapping['tipo']].strip()
                if tipo:
                    properties['Tipo di contatto'] = {
                        'select': {'name': tipo}
                    }
            
            # Status default
            properties['Status'] = {
                'select': {'name': 'Contatto'}
            }
            
            # Comune - passa l'email come hint per l'AI
            result_info = {'success': False}
            if 'comune' in mapping and mapping['comune'] in row:
                comune = row[mapping['comune']].strip()
                if comune:
                    # Passa l'email come hint per aiutare l'AI
                    comune_result = self.search_comune_on_notion(comune, email_hint=email)
                    
                    if comune_result:
                        properties['Comune'] = {
                            'relation': [{'id': comune_result['id']}]
                        }
                        if comune_result['nome'] != comune:
                            result_info['comune_originale'] = comune
                            result_info['comune_corretto'] = comune_result['nome']
                    else:
                        result_info['comune_non_trovato'] = comune
            
            # Crea in Notion
            headers = {
                'Authorization': f'Bearer {NOTION_TOKEN}',
                'Notion-Version': '2022-06-28',
                'Content-Type': 'application/json'
            }
            
            body = {
                'parent': {'database_id': CONTATTI_DB_ID},
                'properties': properties
            }
            
            req = urllib.request.Request(
                'https://api.notion.com/v1/pages',
                data=json.dumps(body).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                if response.status == 200:
                    notion_result = json.loads(response.read().decode('utf-8'))
                    result_info['success'] = True
                    result_info['id'] = notion_result['id']
                    return result_info
                else:
                    error_text = response.read().decode('utf-8')
                    return {'success': False, 'error': f'HTTP {response.status}'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def send_json_response(self, data):
        """Invia risposta JSON"""
        try:
            response_json = json.dumps(data, ensure_ascii=False)
            response_bytes = response_json.encode('utf-8')
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(response_bytes)))
            self.end_headers()
            
            self.wfile.write(response_bytes)
            
        except Exception as e:
            print(f"[ERROR] Errore invio response: {e}")
    
    def send_json_error(self, error_msg, status_code=500):
        """Invia errore JSON"""
        try:
            data = {
                'success': False,
                'error': error_msg
            }
            
            response_json = json.dumps(data, ensure_ascii=False)
            response_bytes = response_json.encode('utf-8')
            
            self.send_response(status_code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(response_bytes)))
            self.end_headers()
            
            self.wfile.write(response_bytes)
            
        except Exception as e:
            print(f"[ERROR] Errore invio errore: {e}")

def main():
    """Avvia il server"""
    # Verifica configurazione
    if not NOTION_TOKEN:
        print("❌ ERRORE: NOTION_TOKEN non configurato!")
        return
    
    if not os.path.exists('index.html'):
        print("❌ ERRORE: File index.html non trovato!")
        return
    
    print(f"✅ Notion Token: {NOTION_TOKEN[:10]}...")
    
    if OPENAI_API_KEY and OPENAI_API_KEY.startswith('sk-'):
        print(f"✅ OpenAI Key: {OPENAI_API_KEY[:10]}...")
    else:
        print("ℹ️  OpenAI non configurato (opzionale)")
    
    # Avvia server
    port = 8000
    server = HTTPServer(('localhost', port), CSVImportHandler)
    
    print('=' * 60)
    print('🚀 CSV Import Server - VERSIONE FINALE')
    print(f'📍 URL: http://localhost:{port}')
    print('📊 Database Contatti pronto')
    print('🔧 Headers HTTP corretti')
    print('⌨️  Premi Ctrl+C per fermare')
    print('=' * 60)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n👋 Server fermato')
        server.shutdown()

if __name__ == '__main__':
    main()