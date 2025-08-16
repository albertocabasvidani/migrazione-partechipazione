import csv
import os
import re

def estrai_provincia_da_nome_file(nome_file):
    """Estrae il nome della provincia dal nome del file CSV"""
    nome = nome_file.replace('.csv', '').replace('_', ' ')
    
    mapping_nomi = {
        'COMUNE DI BELLUNO': 'Belluno',
        'Contatti Comune Asti': 'Asti',
        'Contatti Comune Cuneo': 'Cuneo',
        'Contatti Comune Novara': 'Novara',
        'Contatti Comune Vercelli': 'Vercelli',
        'Contatti Comune verbano cusio ossola': 'Verbano-Cusio-Ossola',
        'Contatti Comuni Alessandria': 'Alessandria',
        'Contatti Comuni Bergamo': 'Bergamo',
        'Contatti Comuni Biella Copia di Foglio1': 'Biella',
        'Contatti Comuni Biella Foglio1': 'Biella',
        'Contatti Comuni Brescia': 'Brescia',
        'Contatti Comuni Como': 'Como',
        'Contatti Comuni Cremona': 'Cremona',
        'Contatti Comuni Lecco': 'Lecco',
        'Contatti Comuni Lodi': 'Lodi',
        'Contatti Comuni Milano': 'Milano',
        'Contatti Comuni Monza e Brianza': 'Monza e Brianza',
        'Contatti Comuni Pavia': 'Pavia',
        'Contatti Comuni Sondrio': 'Sondrio',
        'Contatti Comuni Varese': 'Varese',
        'Contatti comune Torino': 'Torino',
        'comune di padova': 'Padova',
        'comune di rovigo': 'Rovigo',
        'comune di treviso': 'Treviso'
    }
    
    nome_clean = nome.replace('.csv', '')
    return mapping_nomi.get(nome_clean, nome_clean)

def ha_anno_in_intestazione(nome_colonna):
    """Verifica se il nome della colonna contiene un anno (2020-2029)"""
    return bool(re.search(r'202[0-9]', nome_colonna.lower()))

def è_colonna_provincia(nome_colonna):
    """Verifica se è una colonna relativa alla provincia"""
    nome_upper = nome_colonna.strip().upper()
    return nome_upper in ['PR', 'CR', '6', ''] or nome_upper == 'CONTEGGIO'

def è_colonna_email(nome_colonna):
    """Verifica se è una colonna email valida"""
    nome_lower = nome_colonna.lower()
    keywords = ['mail', 'email', 'pec']
    return any(keyword in nome_lower for keyword in keywords) and not ha_anno_in_intestazione(nome_colonna)

def normalizza_tipo_email(nome_colonna):
    """Categorizza il tipo di email"""
    nome_lower = nome_colonna.lower()
    
    if 'generic' in nome_lower or 'segreteria' in nome_lower or 'protocollo' in nome_lower or 'sindaco' in nome_lower or 'info' in nome_lower:
        return 'generica'
    elif 'biblioteca' in nome_lower or 'biblio' in nome_lower:
        return 'biblioteca'
    elif 'cultur' in nome_lower or 'turism' in nome_lower or 'scuola' in nome_lower or 'sport' in nome_lower or 'tempo' in nome_lower or 'specific' in nome_lower or 'eventi' in nome_lower:
        return 'specifica'
    elif "chi e'" in nome_lower:
        return 'skip'
    elif 'altro' in nome_lower or nome_lower == 'mail':
        return 'altro'
    else:
        return 'altro'

def pulisci_email(email):
    """Pulisce e valida un indirizzo email"""
    if not email:
        return ''
    email = email.strip()
    if '@' in email:
        return email
    return ''

def ottieni_email_prioritarie(emails_dict, max_emails=3):
    """Seleziona fino a 3 email con priorità: generica, biblioteca, specifica, altro"""
    result = []
    
    priorita = ['generica', 'biblioteca', 'specifica', 'altro']
    
    for tipo in priorita:
        if tipo in emails_dict and emails_dict[tipo]:
            for email in emails_dict[tipo]:
                if email and email not in result:
                    result.append(email)
                    if len(result) >= max_emails:
                        return result
    
    return result

csv_files = [f for f in os.listdir('.') if f.endswith('.csv') and f not in ['analizza_colonne.py', 'unifica_csv.py']]

all_records = []

for file in csv_files:
    provincia = estrai_provincia_da_nome_file(file)
    print(f"Processando {file} (Provincia: {provincia})")
    
    duplicati_check = set()
    
    with open(file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            comune = None
            emails_by_type = {}
            
            for col_name, value in row.items():
                if not col_name or not value:
                    continue
                    
                col_clean = col_name.strip()
                
                if è_colonna_provincia(col_clean):
                    continue
                
                if 'COMUNE' in col_clean.upper():
                    comune = value.strip()
                elif è_colonna_email(col_clean):
                    tipo = normalizza_tipo_email(col_clean)
                    if tipo != 'skip':
                        email_clean = pulisci_email(value)
                        if email_clean:
                            if tipo not in emails_by_type:
                                emails_by_type[tipo] = []
                            if email_clean not in emails_by_type[tipo]:
                                emails_by_type[tipo].append(email_clean)
            
            if comune:
                chiave = f"{provincia}_{comune}"
                if chiave not in duplicati_check:
                    duplicati_check.add(chiave)
                    
                    email_list = ottieni_email_prioritarie(emails_by_type)
                    
                    email1 = email_list[0] if len(email_list) > 0 else ''
                    email2 = email_list[1] if len(email_list) > 1 else ''
                    email3 = email_list[2] if len(email_list) > 2 else ''
                    
                    all_records.append({
                        'provincia': provincia,
                        'comune': comune,
                        'email_1': email1,
                        'email_2': email2,
                        'email_3': email3
                    })

all_records.sort(key=lambda x: (x['provincia'], x['comune']))

output_file = 'contatti_unificati.csv'
with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
    fieldnames = ['provincia', 'comune', 'email_1', 'email_2', 'email_3']
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(all_records)

print(f"\n✓ File unificato creato: {output_file}")
print(f"  Totale record: {len(all_records)}")

provincia_count = {}
for record in all_records:
    prov = record['provincia']
    provincia_count[prov] = provincia_count.get(prov, 0) + 1

print("\nRecord per provincia:")
for prov in sorted(provincia_count.keys()):
    print(f"  {prov}: {provincia_count[prov]} comuni")