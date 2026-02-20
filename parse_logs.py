import json

with open('cloud.logs/downloaded-logs-20260221-020016.json', 'r', encoding='utf-8') as f:
    logs = json.load(f)

errors = []
warnings = []

for log in logs:
    severity = log.get('severity', '')
    text = log.get('textPayload', '')
    if not text and 'jsonPayload' in log:
        text = str(log.get('jsonPayload', ''))
        
    if not text and 'httpRequest' in log:
         status = log.get('httpRequest', {}).get('status', 200)
         if status >= 500:
              errors.append(f"HTTP {status} - {log.get('httpRequest', {}).get('requestUrl', '')}")
              continue
         elif status >= 400:
              warnings.append(f"HTTP {status} - {log.get('httpRequest', {}).get('requestUrl', '')}")
              continue

    upper_text = text.upper()
    if severity == 'ERROR' or 'ERROR' in upper_text or 'EXCEPTION' in upper_text or 'TRACEBACK' in upper_text or 'TIMEOUT' in upper_text:
        errors.append(text)
    elif severity == 'WARNING' or 'WARNING' in upper_text:
        warnings.append(text)

with open('extracted_errors.log', 'w', encoding='utf-8') as out:
    out.write(f"Total Logs: {len(logs)}\n")
    out.write(f"Errors found: {len(errors)}\n")
    out.write(f"Warnings found: {len(warnings)}\n")
    
    out.write("\n--- ALL UNIQUE ERRORS ---\n")
    seen = set()
    for e in errors:
        if e not in seen:
            seen.add(e)
            out.write(e.strip() + "\n\n")
            
    out.write("\n--- ALL UNIQUE WARNINGS ---\n")
    seen_w = set()
    for w in warnings:
        if w not in seen_w:
            seen_w.add(w)
            out.write(w.strip() + "\n\n")

print("Finished saving to extracted_errors.log")
