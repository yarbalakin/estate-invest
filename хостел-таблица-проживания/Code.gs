// ================================================================
// ХОСТЕЛ — Автогенерация таблицы проживания
// ================================================================

var SPREADSHEET_ID = '1sWT0ADxpyRPHOIeeClddBOl914bdaoheMVDqzGZUmnA';
var LOCATION       = 'г. Краснокамск';
var HOST_NAME      = 'ИП Мудров И.Ю.';

// Листы
var SHEET_BASE      = 'Общая база';
var SHEET_COMPANIES = 'Компании';
var OUTPUT_PREFIX   = 'Таблица — ';

// Колонки "Общая база" (0-indexed)
var COL_FIO      = 1; // B
var COL_COMPANY  = 2; // C
var COL_ROOM     = 3; // D
var COL_CHECKIN  = 4; // E — строка "DD.MM.YYYY"
var COL_CHECKOUT = 5; // F — строка "DD.MM.YYYY", может быть пустой

// Колонки "Компании" (0-indexed)
var COL_CO_NAME  = 1; // B
var COL_CO_PRICE = 2; // C

// ================================================================
// WEB APP — Deploy → New deployment → Web App
// Execute as: Me | Who has access: Anyone
// ================================================================
function doGet(e) {
  var action   = (e && e.parameter && e.parameter.action)   || 'companies';
  var callback = (e && e.parameter && e.parameter.callback) || null;
  var result;
  try {
    if (action === 'companies') {
      result = { ok: true, companies: getCompanyList_() };
    } else if (action === 'residents') {
      result = getResidentsData_(
        e.parameter.company,
        e.parameter.dateFrom,
        e.parameter.dateTo
      );
    } else {
      result = { ok: false, error: 'Unknown action: ' + action };
    }
  } catch (err) {
    result = { ok: false, error: err.message };
  }
  var json = JSON.stringify(result);
  if (callback) {
    return ContentService.createTextOutput(callback + '(' + json + ')')
      .setMimeType(ContentService.MimeType.JAVASCRIPT);
  }
  return ContentService.createTextOutput(json).setMimeType(ContentService.MimeType.JSON);
}

// Список компаний из листа "Компании" (колонка B, непустые)
function getCompanyList_() {
  var ss   = SpreadsheetApp.openById(SPREADSHEET_ID);
  var ws   = ss.getSheetByName(SHEET_COMPANIES);
  var data = ws.getDataRange().getValues();
  var list = [];
  for (var i = 1; i < data.length; i++) {
    var name = data[i][COL_CO_NAME];
    if (name && typeof name === 'string' && name.trim()) {
      list.push(name.trim());
    }
  }
  return list.sort(function(a, b) { return a.localeCompare(b, 'ru'); });
}

// Цена за день для компании (из листа "Компании")
function getCompanyPrice_(companyName) {
  var ss   = SpreadsheetApp.openById(SPREADSHEET_ID);
  var ws   = ss.getSheetByName(SHEET_COMPANIES);
  var data = ws.getDataRange().getValues();
  for (var i = 1; i < data.length; i++) {
    var name = data[i][COL_CO_NAME];
    if (name && name.toString().toLowerCase() === companyName.toLowerCase()) {
      var price = data[i][COL_CO_PRICE];
      return (typeof price === 'number' && price > 0) ? price : parseFloat(price) || 0;
    }
  }
  return 0;
}

// Парсинг даты — принимает и строку "DD.MM.YYYY", и Date-объект (Apps Script возвращает оба)
function parseDate_(s) {
  if (!s) return null;
  if (s instanceof Date) {
    var copy = new Date(s); copy.setHours(0, 0, 0, 0);
    return isNaN(copy.getTime()) ? null : copy;
  }
  var str = s.toString().trim();
  if (!str) return null;
  var parts = str.split('.');
  if (parts.length !== 3) return null;
  var d = new Date(parseInt(parts[2], 10), parseInt(parts[1], 10) - 1, parseInt(parts[0], 10));
  d.setHours(0, 0, 0, 0);
  return isNaN(d.getTime()) ? null : d;
}

// Данные для Web App — жители за компанию и диапазон дат
// dateFrom, dateTo — строки "YYYY-MM-DD"
function getResidentsData_(company, dateFrom, dateTo) {
  var ss    = SpreadsheetApp.openById(SPREADSHEET_ID);
  var ws    = ss.getSheetByName(SHEET_BASE);
  var data  = ws.getDataRange().getValues();
  var price = getCompanyPrice_(company);

  var rangeStart = parseDateISO_(dateFrom);
  var rangeEnd   = parseDateISO_(dateTo);
  if (!rangeStart || !rangeEnd) {
    return { ok: false, error: 'Неверный формат дат: ' + dateFrom + ' / ' + dateTo };
  }

  // Строим массив дат диапазона
  var rangeDays = [];
  for (var cur = new Date(rangeStart); cur <= rangeEnd; cur.setDate(cur.getDate() + 1)) {
    rangeDays.push(new Date(cur));
  }
  var totalDays = rangeDays.length;

  var residents = [];

  for (var i = 1; i < data.length; i++) {
    var row        = data[i];
    var fio        = row[COL_FIO];
    var companyVal = row[COL_COMPANY];
    var room       = row[COL_ROOM];
    var checkInStr = row[COL_CHECKIN];
    var checkOutStr= row[COL_CHECKOUT];

    if (!fio || typeof fio !== 'string' || !fio.trim()) continue;
    if (!companyVal || companyVal.toString().toLowerCase() !== company.toLowerCase()) continue;

    var stayStart = parseDate_(checkInStr);
    if (!stayStart) continue;

    // Выезд: если пустой — живёт до конца диапазона (по dateTo)
    var stayEnd = parseDate_(checkOutStr);
    if (!stayEnd) stayEnd = new Date(rangeEnd);

    // Нет пересечения с диапазоном
    if (stayEnd < rangeStart || stayStart > rangeEnd) continue;

    // Индексы дней внутри диапазона (1-based)
    var presentIdxs = [];
    for (var d = 0; d < rangeDays.length; d++) {
      var day = rangeDays[d];
      if (day >= stayStart && day <= stayEnd) presentIdxs.push(d + 1);
    }
    if (presentIdxs.length === 0) continue;

    residents.push({
      fio:       fio.trim(),
      room:      room ? room.toString() : '',
      days:      presentIdxs,       // порядковые номера внутри диапазона (1-based)
      daysCount: presentIdxs.length,
      price:     price,
      total:     presentIdxs.length * price
    });
  }

  if (residents.length === 0) {
    return { ok: false, error: 'Нет данных для "' + company + '" за период ' + dateFrom + ' — ' + dateTo };
  }

  residents.sort(function(a, b) {
    var r = a.room.localeCompare(b.room, 'ru', { numeric: true });
    return r !== 0 ? r : a.fio.localeCompare(b.fio, 'ru');
  });

  // Заголовки колонок: числа месяца (или "DD.MM" если диапазон охватывает несколько месяцев)
  var multiMonth = rangeStart.getMonth() !== rangeEnd.getMonth() ||
                   rangeStart.getFullYear() !== rangeEnd.getFullYear();
  var colHeaders = rangeDays.map(function(d) {
    return multiMonth
      ? (String(d.getDate()).padStart(2,'0') + '.' + String(d.getMonth()+1).padStart(2,'0'))
      : d.getDate();
  });

  return {
    ok: true, company: company,
    dateFrom: dateFrom, dateTo: dateTo,
    totalDays: totalDays, colHeaders: colHeaders,
    location: LOCATION, hostName: HOST_NAME,
    price: price, residents: residents
  };
}

// Парсинг "YYYY-MM-DD"
function parseDateISO_(s) {
  if (!s) return null;
  var parts = s.toString().trim().split('-');
  if (parts.length !== 3) return null;
  var d = new Date(parseInt(parts[0],10), parseInt(parts[1],10)-1, parseInt(parts[2],10));
  d.setHours(0,0,0,0);
  return isNaN(d.getTime()) ? null : d;
}

// ================================================================
// МЕНЮ В GOOGLE SHEETS
// ================================================================
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('Хостел')
    .addItem('Сформировать таблицу проживания', 'showDialog')
    .addToUi();
}

function showDialog() {
  var companies = getCompanyList_();
  var now       = new Date();
  var template  = HtmlService.createTemplateFromFile('Dialog');
  template.companies    = companies;
  template.currentMonth = now.getMonth() + 1;
  template.currentYear  = now.getFullYear();
  SpreadsheetApp.getUi().showModalDialog(
    template.evaluate().setWidth(460).setHeight(370), 'Таблица проживания'
  );
}

function generateTable(company, dateFrom, dateTo) {
  try {
    var data = getResidentsData_(company, dateFrom, dateTo);
    if (!data.ok) return { success: false, error: data.error };
    var ss = SpreadsheetApp.openById(SPREADSHEET_ID);
    return buildSheet_(ss, data);
  } catch (e) {
    return { success: false, error: e.message };
  }
}

// ================================================================
// ГЕНЕРАЦИЯ ЛИСТА
// ================================================================
function buildSheet_(ss, data) {
  var MONTH_NAMES = ['Январь','Февраль','Март','Апрель','Май','Июнь',
                     'Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'];

  var company     = data.company;
  var daysInMonth = data.totalDays;   // теперь это длина диапазона
  var colHeaders  = data.colHeaders;  // заголовки колонок дней
  var residents   = data.residents;

  var periodLabel = data.dateFrom + ' — ' + data.dateTo;
  var sheetTitle  = OUTPUT_PREFIX + periodLabel + ' — ' + company;
  if (sheetTitle.length > 100) sheetTitle = sheetTitle.substring(0, 100);

  var existing = ss.getSheetByName(sheetTitle);
  if (existing) ss.deleteSheet(existing);
  var ws = ss.insertSheet(sheetTitle);

  // Колонки выходного листа
  var C_NUM  = 1; // №
  var C_FIO  = 2; // ФИО
  var C_ROOM = 3; // Комната
  var C_D1   = 4; // Первый день
  var C_DN   = C_D1 + daysInMonth - 1;
  var C_DAYS = C_DN + 1; // Итого дней
  var C_SUM  = C_DAYS + 1; // Сумма
  var NCOLS  = C_SUM;

  var row = 1;

  // Заголовок
  ws.getRange(row, 1, 1, NCOLS).merge();
  ws.getRange(row, 1).setValue('Таблица проживания сотрудников за период ' + periodLabel)
    .setFontWeight('bold').setFontSize(13).setHorizontalAlignment('center');
  row++;
  ws.getRange(row, 1, 1, NCOLS).merge();
  ws.getRange(row, 1).setValue('Контрагент: ' + company)
    .setFontWeight('bold').setHorizontalAlignment('center');
  row++;
  ws.getRange(row, 1, 1, NCOLS).merge();
  ws.getRange(row, 1).setValue('Объект: ' + LOCATION + '   |   Цена: ' + data.price + ' руб./сут.')
    .setHorizontalAlignment('center');
  row += 2;

  // Шапка таблицы
  var headerRow = row;
  ws.getRange(row, C_NUM).setValue('№');
  ws.getRange(row, C_FIO).setValue('ФИО');
  ws.getRange(row, C_ROOM).setValue('Ком.');
  for (var d = 0; d < daysInMonth; d++) ws.getRange(row, C_D1 + d).setValue(colHeaders[d]);
  ws.getRange(row, C_DAYS).setValue('Дней');
  ws.getRange(row, C_SUM).setValue('Сумма');
  ws.getRange(row, 1, 1, NCOLS)
    .setFontWeight('bold').setBackground('#dce6f1').setHorizontalAlignment('center');
  row++;

  // Данные
  var totalDays = 0, totalAmount = 0, dataStartRow = row;
  residents.forEach(function(res, idx) {
    ws.getRange(row, C_NUM).setValue(idx + 1);
    ws.getRange(row, C_FIO).setValue(res.fio);
    ws.getRange(row, C_ROOM).setValue(res.room).setHorizontalAlignment('center');

    // В каждой ячейке дня — цена (как в эталонном файле ГеоИнвест)
    res.days.forEach(function(d) {
      ws.getRange(row, C_D1 + d - 1).setValue(res.price)
        .setHorizontalAlignment('center').setFontColor('#1a5276');
    });

    ws.getRange(row, C_DAYS).setValue(res.daysCount).setHorizontalAlignment('center');
    ws.getRange(row, C_SUM).setValue(res.total).setHorizontalAlignment('right');

    if (idx % 2 === 1) ws.getRange(row, 1, 1, NCOLS).setBackground('#f4f8fd');
    totalDays   += res.daysCount;
    totalAmount += res.total;
    row++;
  });

  // Итого — сумма по каждому дню + общие итоги
  row++;
  ws.getRange(row, C_FIO).setValue('Всего проживают:').setFontWeight('bold');
  ws.getRange(row, C_DAYS).setValue(totalDays).setFontWeight('bold').setHorizontalAlignment('center');
  ws.getRange(row, C_SUM).setValue(totalAmount).setFontWeight('bold').setHorizontalAlignment('right');

  // Подписи
  row += 3;
  ws.getRange(row, 1).setValue('Представитель ' + company + ': ________________________________');
  ws.getRange(row + 2, 1).setValue(HOST_NAME + ':  ________________________________');

  // Форматирование
  ws.getRange(headerRow, 1, residents.length + 1, NCOLS)
    .setBorder(true, true, true, true, true, true, '#aaaaaa', SpreadsheetApp.BorderStyle.SOLID);
  ws.setColumnWidth(C_NUM, 35);
  ws.setColumnWidth(C_FIO, 220);
  ws.setColumnWidth(C_ROOM, 50);
  for (var d = 1; d <= daysInMonth; d++) ws.setColumnWidth(C_D1 + d - 1, 22);
  ws.setColumnWidth(C_DAYS, 55);
  ws.setColumnWidth(C_SUM, 80);
  ws.setRowHeightsForced(dataStartRow, residents.length, 20);
  ws.getRange(headerRow, C_D1, residents.length + 1, daysInMonth).setFontSize(9);
  ss.setActiveSheet(ws);

  return { success: true, sheetName: sheetTitle, count: residents.length, totalDays: totalDays, totalAmount: totalAmount };
}
