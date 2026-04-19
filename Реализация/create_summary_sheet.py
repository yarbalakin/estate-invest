"""
Создаёт новый лист "Сводка помещений" в Google таблице КУ Нытва
с формулами, которые тянут данные из существующих листов 2 и 3 этажа.
"""
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
KEY_FILE = '/Users/yaroslavbalakin/Downloads/powerful-hall-488221-t2-b83babe8f926.json'
SPREADSHEET_ID = '1tRyxLafi1lPF-RRH_NP0Cfoj_gZlJja2_ppDmSHYE5E'

# Названия листов-источников (как в таблице)
SHEET_2 = 'Нытва 2 эт.'
SHEET_3 = 'Нытва 3 эт.'

creds = Credentials.from_service_account_file(KEY_FILE, scopes=SCOPES)
service = build('sheets', 'v4', credentials=creds)
sheets = service.spreadsheets()

# --- 1. Проверить существующие листы ---
meta = sheets.get(spreadsheetId=SPREADSHEET_ID).execute()
existing = [s['properties']['title'] for s in meta['sheets']]
print(f"Существующие листы: {existing}")

SUMMARY_TITLE = 'Сводка помещений'

# Удалить старый лист если есть
for s in meta['sheets']:
    if s['properties']['title'] == SUMMARY_TITLE:
        sheets.batchUpdate(spreadsheetId=SPREADSHEET_ID, body={
            'requests': [{'deleteSheet': {'sheetId': s['properties']['sheetId']}}]
        }).execute()
        print(f"Удалён старый лист '{SUMMARY_TITLE}'")

# --- 2. Создать новый лист ---
resp = sheets.batchUpdate(spreadsheetId=SPREADSHEET_ID, body={
    'requests': [{
        'addSheet': {
            'properties': {
                'title': SUMMARY_TITLE,
                'gridProperties': {'rowCount': 30, 'columnCount': 10}
            }
        }
    }]
}).execute()
new_sheet_id = resp['replies'][0]['addSheet']['properties']['sheetId']
print(f"Создан лист '{SUMMARY_TITLE}' (id={new_sheet_id})")

# --- 3. Заполнить данные ---
# Структура 2 этажа: C=помещение, J=площадь, D=цена аренды, K=цена за м2, L=статус, I=контакты
# Строки 2-15 (14 помещений), строка 1 = заголовок
# Структура 3 этажа: B=помещение, G=площадь, C=цена аренды, H=цена за м2, I=статус, F=контакты
# Строки 2-10 (9 помещений)

rows = []

# Заголовок
rows.append([
    'Этаж', '№ помещения', 'Площадь, м²', 'Арендатор / Контакт',
    'Статус', 'Стоимость аренды, руб.', 'Цена за м², руб.',
    'Вознаграждение агента, руб.', 'Комментарии агента'
])

# 2 этаж — 14 помещений (строки 2..15 в исходном листе)
for i in range(2, 16):
    rows.append([
        '2 этаж',
        f"='{SHEET_2}'!C{i}",  # № помещения
        f"='{SHEET_2}'!J{i}",  # Площадь
        f"='{SHEET_2}'!I{i}",  # Контакты
        f"='{SHEET_2}'!L{i}",  # Статус
        f"='{SHEET_2}'!D{i}",  # Цена аренды
        f"='{SHEET_2}'!K{i}",  # Цена за м²
        '',  # Вознаграждение агента — заполняется вручную
        '',  # Комментарии агента — заполняются вручную
    ])

# 3 этаж — 9 помещений (строки 2..10)
for i in range(2, 11):
    rows.append([
        '3 этаж',
        f"='{SHEET_3}'!B{i}",  # № помещения
        f"='{SHEET_3}'!G{i}",  # Площадь
        f"='{SHEET_3}'!F{i}",  # Контакты
        f"='{SHEET_3}'!I{i}",  # Статус
        f"='{SHEET_3}'!C{i}",  # Цена аренды
        f"='{SHEET_3}'!H{i}",  # Цена за м²
        '',
        '',
    ])

# Итоговая строка
total_row = len(rows)  # следующая строка (1-indexed будет total_row+1)
rows.append([
    'ИТОГО', '', f'=SUM(C2:C{total_row})', '',
    f'=COUNTIF(E2:E{total_row},"Сдано")&" из "&COUNTA(E2:E{total_row})&" сдано"',
    f'=SUM(F2:F{total_row})', '', f'=SUM(H2:H{total_row})', ''
])

# Записать данные
sheets.values().update(
    spreadsheetId=SPREADSHEET_ID,
    range=f"'{SUMMARY_TITLE}'!A1",
    valueInputOption='USER_ENTERED',
    body={'values': rows}
).execute()
print(f"Записано {len(rows)} строк")

# --- 4. Форматирование ---
requests = []

# Жирный заголовок
requests.append({
    'repeatCell': {
        'range': {'sheetId': new_sheet_id, 'startRowIndex': 0, 'endRowIndex': 1},
        'cell': {
            'userEnteredFormat': {
                'textFormat': {'bold': True},
                'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.95},
                'horizontalAlignment': 'CENTER'
            }
        },
        'fields': 'userEnteredFormat(textFormat,backgroundColor,horizontalAlignment)'
    }
})

# Жирная итоговая строка
requests.append({
    'repeatCell': {
        'range': {'sheetId': new_sheet_id, 'startRowIndex': total_row, 'endRowIndex': total_row + 1},
        'cell': {
            'userEnteredFormat': {
                'textFormat': {'bold': True},
                'backgroundColor': {'red': 0.95, 'green': 0.95, 'blue': 0.85}
            }
        },
        'fields': 'userEnteredFormat(textFormat,backgroundColor)'
    }
})

# Зелёный фон для "Сдано" — условное форматирование
requests.append({
    'addConditionalFormatRule': {
        'rule': {
            'ranges': [{'sheetId': new_sheet_id, 'startRowIndex': 1, 'endRowIndex': total_row,
                        'startColumnIndex': 4, 'endColumnIndex': 5}],
            'booleanRule': {
                'condition': {'type': 'TEXT_EQ', 'values': [{'userEnteredValue': 'Сдано'}]},
                'format': {
                    'backgroundColor': {'red': 0.85, 'green': 0.95, 'blue': 0.85},
                    'textFormat': {'foregroundColor': {'red': 0.1, 'green': 0.5, 'blue': 0.1}}
                }
            }
        },
        'index': 0
    }
})

# Серый фон для "Свободно"
requests.append({
    'addConditionalFormatRule': {
        'rule': {
            'ranges': [{'sheetId': new_sheet_id, 'startRowIndex': 1, 'endRowIndex': total_row,
                        'startColumnIndex': 4, 'endColumnIndex': 5}],
            'booleanRule': {
                'condition': {'type': 'TEXT_EQ', 'values': [{'userEnteredValue': 'Свободно'}]},
                'format': {
                    'backgroundColor': {'red': 0.93, 'green': 0.93, 'blue': 0.93},
                    'textFormat': {'foregroundColor': {'red': 0.5, 'green': 0.5, 'blue': 0.5}}
                }
            }
        },
        'index': 1
    }
})

# Авторазмер колонок
requests.append({
    'autoResizeDimensions': {
        'dimensions': {'sheetId': new_sheet_id, 'dimension': 'COLUMNS', 'startIndex': 0, 'endIndex': 9}
    }
})

# Заморозить заголовок
requests.append({
    'updateSheetProperties': {
        'properties': {
            'sheetId': new_sheet_id,
            'gridProperties': {'frozenRowCount': 1}
        },
        'fields': 'gridProperties.frozenRowCount'
    }
})

sheets.batchUpdate(spreadsheetId=SPREADSHEET_ID, body={'requests': requests}).execute()
print("Форматирование применено")

print(f"\nГотово! Откройте таблицу:")
print(f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit#gid={new_sheet_id}")
