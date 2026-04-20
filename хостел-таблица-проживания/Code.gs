// ================================================================
// ХОСТЕЛ — Автогенерация таблицы проживания
// Вставить в Apps Script: Extensions → Apps Script
// ================================================================

var SPREADSHEET_ID = '1D7fujy57l_GXUzQ-mF9JWz2LkuAr5jET'; // ID таблицы хостела
var LOCATION       = 'г. Краснокамск';
var HOST_NAME      = 'ИП Мудров И.Ю.';

// Колонки в исходных листах (0-indexed, т.е. A=0, B=1, ...)
var COL_FIO     = 1; // B — ФИО проживающего
var COL_COMPANY = 2; // C — Название компании, номер комнаты
var COL_CHECKIN = 3; // D — Заезд
var COL_CHECKOUT= 4; // E — Выезд
var COL_PRICE   = 7; // H — Цена/день

// Префикс создаваемых листов (чтобы не путать с исходными)
var OUTPUT_PREFIX = 'Таблица — ';

// ================================================================
// WEB APP API — вызывается с внешней страницы через JSONP
// Задеплоить: Deploy → New deployment → Web App
//   Execute as: Me | Who has access: Anyone
// ================================================================
function doGet(e) {
  var action   = (e && e.parameter && e.parameter.action)   || 'companies';
  var callback = (e && e.parameter && e.parameter.callback) || null;

  var result;
  try {
    if (action === 'companies') {
      result = { ok: true, companies: getUniqueCompanies_() };
    } else if (action === 'residents') {
      var company = e.parameter.company;
      var month   = parseInt(e.parameter.month, 10);
      var year    = parseInt(e.parameter.year,  10);
      result = getResidentsData_(company, month, year);
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
  return ContentService.createTextOutput(json)
    .setMimeType(ContentService.MimeType.JSON);
}

// Собирает уникальные значения из колонки "Компания" по всем листам
// Использует openById — работает как из Web App, так и из меню Sheets
function getUniqueCompanies_() {
  var ss     = SpreadsheetApp.openById(SPREADSHEET_ID);
  var sheets = ss.getSheets();
  var seen   = {};

  sheets.forEach(function(sheet) {
    if (sheet.getName().indexOf(OUTPUT_PREFIX) === 0) return;
    var lastRow = sheet.getLastRow();
    if (lastRow < 2) return;

    var values = sheet.getRange(2, COL_COMPANY + 1, lastRow - 1, 1).getValues();
    values.forEach(function(row) {
      var val = row[0];
      if (val && typeof val === 'string' && val.trim().length > 0) {
        seen[val.trim()] = true;
      }
    });
  });

  return Object.keys(seen).sort(function(a, b) {
    return a.localeCompare(b, 'ru');
  });
}

// Возвращает данные для Web App (без создания листа в таблице)
function getResidentsData_(company, month, year) {
  var ss     = SpreadsheetApp.openById(SPREADSHEET_ID);
  var sheets = ss.getSheets();

  var monthStart = new Date(year, month - 1, 1);
  monthStart.setHours(0, 0, 0, 0);
  var monthEnd = new Date(year, month, 0);
  monthEnd.setHours(23, 59, 59, 999);
  var daysInMonth = monthEnd.getDate();

  var residents = [];

  sheets.forEach(function(sheet) {
    if (sheet.getName().indexOf(OUTPUT_PREFIX) === 0) return;
    var lastRow = sheet.getLastRow();
    if (lastRow < 2) return;

    var data = sheet.getRange(2, 1, lastRow - 1, 9).getValues();
    data.forEach(function(row) {
      var fio         = row[COL_FIO];
      var companyRoom = row[COL_COMPANY];
      var checkIn     = row[COL_CHECKIN];
      var checkOut    = row[COL_CHECKOUT];
      var price       = row[COL_PRICE];

      if (!fio || typeof fio !== 'string' || !fio.trim()) return;
      if (!companyRoom || typeof companyRoom !== 'string') return;
      if (companyRoom.toLowerCase().indexOf(company.toLowerCase()) === -1) return;
      if (!(checkIn instanceof Date) || !(checkOut instanceof Date)) return;

      var stayStart = new Date(checkIn); stayStart.setHours(0, 0, 0, 0);
      var stayEnd   = new Date(checkOut); stayEnd.setHours(0, 0, 0, 0);
      if (stayEnd <= monthStart || stayStart > monthEnd) return;

      var presentDays = [];
      for (var d = 1; d <= daysInMonth; d++) {
        var day = new Date(year, month - 1, d);
        if (day >= stayStart && day < stayEnd) presentDays.push(d);
      }
      if (presentDays.length === 0) return;

      var roomMatch = companyRoom.match(/[,\s]+(\d+)\s*$/);
      var priceNum  = (typeof price === 'number' && price > 0) ? price : 0;

      residents.push({
        fio:       fio.trim(),
        room:      roomMatch ? roomMatch[1] : '',
        days:      presentDays,
        daysCount: presentDays.length,
        price:     priceNum,
        total:     presentDays.length * priceNum
      });
    });
  });

  if (residents.length === 0) {
    return { ok: false, error: 'Нет данных для "' + company + '" за выбранный период.' };
  }

  residents.sort(function(a, b) {
    var r = a.room.localeCompare(b.room, 'ru', { numeric: true });
    return r !== 0 ? r : a.fio.localeCompare(b.fio, 'ru');
  });

  return {
    ok: true, company: company, month: month, year: year,
    daysInMonth: daysInMonth, location: LOCATION, hostName: HOST_NAME,
    residents: residents
  };
}

// ================================================================
// МЕНЮ В GOOGLE SHEETS — кнопка для генерации листа внутри таблицы
// ================================================================
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('Хостел')
    .addItem('Сформировать таблицу проживания', 'showDialog')
    .addToUi();
}

function showDialog() {
  var companies = getUniqueCompanies_();
  var now       = new Date();

  var template = HtmlService.createTemplateFromFile('Dialog');
  template.companies    = companies;
  template.currentMonth = now.getMonth() + 1;
  template.currentYear  = now.getFullYear();

  var html = template.evaluate().setWidth(460).setHeight(370);
  SpreadsheetApp.getUi().showModalDialog(html, 'Таблица проживания');
}

// Вызывается из Dialog.html — создаёт лист прямо в таблице
function generateTable(company, month, year) {
  try {
    var ss     = SpreadsheetApp.openById(SPREADSHEET_ID);
    var sheets = ss.getSheets();

    var monthStart = new Date(year, month - 1, 1);
    monthStart.setHours(0, 0, 0, 0);
    var monthEnd = new Date(year, month, 0);
    monthEnd.setHours(23, 59, 59, 999);
    var daysInMonth = monthEnd.getDate();

    var residents = [];

    sheets.forEach(function(sheet) {
      if (sheet.getName().indexOf(OUTPUT_PREFIX) === 0) return;
      var lastRow = sheet.getLastRow();
      if (lastRow < 2) return;

      var data = sheet.getRange(2, 1, lastRow - 1, 9).getValues();
      data.forEach(function(row) {
        var fio         = row[COL_FIO];
        var companyRoom = row[COL_COMPANY];
        var checkIn     = row[COL_CHECKIN];
        var checkOut    = row[COL_CHECKOUT];
        var price       = row[COL_PRICE];

        if (!fio || typeof fio !== 'string' || !fio.trim()) return;
        if (!companyRoom || typeof companyRoom !== 'string') return;
        if (companyRoom.toLowerCase().indexOf(company.toLowerCase()) === -1) return;
        if (!(checkIn instanceof Date) || !(checkOut instanceof Date)) return;

        var stayStart = new Date(checkIn); stayStart.setHours(0, 0, 0, 0);
        var stayEnd   = new Date(checkOut); stayEnd.setHours(0, 0, 0, 0);
        if (stayEnd <= monthStart || stayStart > monthEnd) return;

        var presentDays = [];
        for (var d = 1; d <= daysInMonth; d++) {
          var day = new Date(year, month - 1, d);
          if (day >= stayStart && day < stayEnd) presentDays.push(d);
        }
        if (presentDays.length === 0) return;

        var roomMatch = companyRoom.match(/[,\s]+(\d+)\s*$/);
        var priceNum  = (typeof price === 'number' && price > 0) ? price : 0;

        residents.push({
          fio: fio.trim(), room: roomMatch ? roomMatch[1] : '',
          days: presentDays, daysCount: presentDays.length,
          price: priceNum, total: presentDays.length * priceNum
        });
      });
    });

    if (residents.length === 0) {
      return { success: false, error: 'Нет данных для "' + company + '" за выбранный период.' };
    }

    residents.sort(function(a, b) {
      var r = a.room.localeCompare(b.room, 'ru', { numeric: true });
      return r !== 0 ? r : a.fio.localeCompare(b.fio, 'ru');
    });

    return buildSheet_(ss, company, month, year, daysInMonth, residents);

  } catch (e) {
    return { success: false, error: e.message };
  }
}

function buildSheet_(ss, company, month, year, daysInMonth, residents) {
  var MONTH_NAMES = ['Январь','Февраль','Март','Апрель','Май','Июнь',
                     'Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'];

  var sheetTitle = OUTPUT_PREFIX + MONTH_NAMES[month-1] + ' ' + year + ' — ' + company;
  if (sheetTitle.length > 100) sheetTitle = sheetTitle.substring(0, 100);

  var existing = ss.getSheetByName(sheetTitle);
  if (existing) ss.deleteSheet(existing);
  var ws = ss.insertSheet(sheetTitle);

  var C_NUM = 1, C_FIO = 2, C_ROOM = 3, C_D1 = 4;
  var C_DN = C_D1 + daysInMonth - 1;
  var C_DAYS = C_DN + 1, C_PRICE = C_DAYS + 1, C_SUM = C_PRICE + 1;
  var NCOLS = C_SUM;
  var row = 1;

  ws.getRange(row, 1, 1, NCOLS).merge();
  ws.getRange(row, 1).setValue('Таблица проживания сотрудников за ' + MONTH_NAMES[month-1] + ' ' + year + ' г.')
    .setFontWeight('bold').setFontSize(13).setHorizontalAlignment('center');
  row++;
  ws.getRange(row, 1, 1, NCOLS).merge();
  ws.getRange(row, 1).setValue('Контрагент: ' + company).setFontWeight('bold').setHorizontalAlignment('center');
  row++;
  ws.getRange(row, 1, 1, NCOLS).merge();
  ws.getRange(row, 1).setValue('Объект: ' + LOCATION).setHorizontalAlignment('center');
  row += 2;

  var headerRow = row;
  ws.getRange(row, C_NUM).setValue('№');
  ws.getRange(row, C_FIO).setValue('ФИО');
  ws.getRange(row, C_ROOM).setValue('Ком.');
  for (var d = 1; d <= daysInMonth; d++) ws.getRange(row, C_D1 + d - 1).setValue(d);
  ws.getRange(row, C_DAYS).setValue('Дней');
  ws.getRange(row, C_PRICE).setValue('Цена');
  ws.getRange(row, C_SUM).setValue('Сумма');
  ws.getRange(row, 1, 1, NCOLS).setFontWeight('bold').setBackground('#dce6f1').setHorizontalAlignment('center');
  row++;

  var totalDays = 0, totalAmount = 0, dataStartRow = row;
  residents.forEach(function(res, idx) {
    ws.getRange(row, C_NUM).setValue(idx + 1);
    ws.getRange(row, C_FIO).setValue(res.fio);
    ws.getRange(row, C_ROOM).setValue(res.room).setHorizontalAlignment('center');
    res.days.forEach(function(d) {
      ws.getRange(row, C_D1 + d - 1).setValue(1).setHorizontalAlignment('center').setFontColor('#1a5276');
    });
    ws.getRange(row, C_DAYS).setValue(res.daysCount).setHorizontalAlignment('center');
    if (res.price > 0) {
      ws.getRange(row, C_PRICE).setValue(res.price);
      ws.getRange(row, C_SUM).setValue(res.total);
    }
    if (idx % 2 === 1) ws.getRange(row, 1, 1, NCOLS).setBackground('#f4f8fd');
    totalDays += res.daysCount; totalAmount += res.total; row++;
  });

  row++;
  ws.getRange(row, C_FIO).setValue('ИТОГО:').setFontWeight('bold');
  ws.getRange(row, C_DAYS).setValue(totalDays).setFontWeight('bold');
  if (totalAmount > 0) ws.getRange(row, C_SUM).setValue(totalAmount).setFontWeight('bold');

  row += 3;
  ws.getRange(row, 1).setValue('Представитель заказчика: ________________________________  (' + company + ')');
  ws.getRange(row + 2, 1).setValue(HOST_NAME + ':  ________________________________');

  ws.getRange(headerRow, 1, residents.length + 1, NCOLS)
    .setBorder(true, true, true, true, true, true, '#aaaaaa', SpreadsheetApp.BorderStyle.SOLID);
  ws.setColumnWidth(C_NUM, 35); ws.setColumnWidth(C_FIO, 210); ws.setColumnWidth(C_ROOM, 50);
  for (var d = 1; d <= daysInMonth; d++) ws.setColumnWidth(C_D1 + d - 1, 22);
  ws.setColumnWidth(C_DAYS, 50); ws.setColumnWidth(C_PRICE, 65); ws.setColumnWidth(C_SUM, 80);
  ws.setRowHeightsForced(dataStartRow, residents.length, 20);
  ws.getRange(headerRow, C_D1, residents.length + 1, daysInMonth).setFontSize(9);
  ss.setActiveSheet(ws);

  return { success: true, sheetName: sheetTitle, count: residents.length, totalDays: totalDays, totalAmount: totalAmount };
}
