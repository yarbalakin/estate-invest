/**
 * Автопарсинг лотов торгов — Google Apps Script
 *
 * Вставляешь URL (tbankrot.ru) в колонку A листа "Торги" → данные заполняются автоматически.
 *
 * УСТАНОВКА:
 * 1. Открыть таблицу → Расширения → Apps Script
 * 2. Вставить этот код
 * 3. Запустить функцию setupTrigger() один раз
 * 4. Подтвердить разрешения Google
 */

// ============================================================
// НАСТРОЙКИ
// ============================================================

var CONFIG = {
  sheetName: 'Торги',        // Название листа
  headerRows: 2,             // Количество строк заголовков (пропускаем)
  urlColumn: 1,              // Колонка с URL (A = 1)
  nameColumn: 2,             // Наименование лота (B)
  cityColumn: 3,             // Город (C)
  statusColumn: 4,           // Статус (D)
  auctionTypeColumn: 7,      // Тип торгов (G)
  applicationDeadlineColumn: 8,  // Окончание подачи заявок (H)
  auctionDateColumn: 9,      // Дата торгов (I)
  depositDatesColumn: 10,    // Даты задатков (J)
  depositColumn: 11,         // Задатки — сумма (K)
  paymentDeadlineColumn: 12, // Срок оплаты (L)
  buyMinColumn: 13,          // Покупка Min (M)
  stepColumn: 29,            // Ставка / шаг аукциона (AC)

  // Авторизация tbankrot.ru
  tbankrotEmail: 'estatetorgi@yandex.ru',
  tbankrotPassword: 'agent2025'
};

// Кэш сессии (в рамках одного выполнения скрипта)
var _sessionCookies = null;

// ============================================================
// УСТАНОВКА ТРИГГЕРА
// ============================================================

function setupTrigger() {
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === 'onUrlPasted') {
      ScriptApp.deleteTrigger(triggers[i]);
    }
  }
  ScriptApp.newTrigger('onUrlPasted')
    .forSpreadsheet(SpreadsheetApp.getActive())
    .onEdit()
    .create();

  // Форматируем колонку A как "Обычный текст" (@)
  // Это нужно чтобы гиперссылки с числовым текстом (напр. "5499435")
  // сохраняли RichText данные и extractUrlFromCell мог прочитать URL
  var sheet = SpreadsheetApp.getActive().getSheetByName(CONFIG.sheetName);
  if (sheet) {
    sheet.getRange('A:A').setNumberFormat('@');
  }

  SpreadsheetApp.getUi().alert('Триггер установлен! Колонка A отформатирована как текст. Вставляйте URL в колонку A листа "' + CONFIG.sheetName + '"');
}

// ============================================================
// МЕНЮ
// ============================================================

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('Торги')
    .addItem('Парсить все новые URL', 'parseAllNewUrls')
    .addItem('Парсить текущую строку', 'parseCurrentRow')
    .addSeparator()
    .addItem('Установить триггер', 'setupTrigger')
    .addToUi();
}

// ============================================================
// ОБРАБОТЧИК РЕДАКТИРОВАНИЯ
// ============================================================

function onUrlPasted(e) {
  try {
    var sheet = e.source.getActiveSheet();
    if (sheet.getName() !== CONFIG.sheetName) return;

    var range = e.range;
    var col = range.getColumn();

    // Реагируем на: колонку A (вставка URL) или колонку B (очистка наименования)
    if (col !== CONFIG.urlColumn && col !== CONFIG.nameColumn) return;

    var startRow = range.getRow();
    var numRows = range.getNumRows();

    // Небольшая пауза чтобы Google Sheets успел записать гиперссылку/RichText
    Utilities.sleep(500);

    for (var i = 0; i < numRows; i++) {
      var row = startRow + i;
      if (row <= CONFIG.headerRows) continue;

      var urlCell = sheet.getRange(row, CONFIG.urlColumn);

      // Если ячейка числовая — форматируем как текст, чтобы RichText работал
      var cellValue = urlCell.getValue();
      if (typeof cellValue === 'number') {
        urlCell.setNumberFormat('@');
        urlCell.setValue(cellValue.toString());
        Utilities.sleep(300);
      }

      var url = extractUrlFromCell(urlCell);
      if (!url || !url.match(/^https?:\/\//)) continue;

      var nameVal = sheet.getRange(row, CONFIG.nameColumn).getValue();
      if (nameVal !== '' && nameVal !== null) continue;

      processUrl(sheet, row, url);
    }
  } catch (err) {
    Logger.log('onUrlPasted error: ' + err.message);
  }
}

// ============================================================
// ПАКЕТНАЯ ОБРАБОТКА
// ============================================================

function parseAllNewUrls() {
  var sheet = SpreadsheetApp.getActive().getSheetByName(CONFIG.sheetName);
  if (!sheet) {
    SpreadsheetApp.getUi().alert('Лист "' + CONFIG.sheetName + '" не найден');
    return;
  }

  var lastRow = sheet.getLastRow();
  if (lastRow <= CONFIG.headerRows) {
    SpreadsheetApp.getUi().alert('Нет данных для обработки');
    return;
  }

  var dataRows = lastRow - CONFIG.headerRows;
  var names = sheet.getRange(CONFIG.headerRows + 1, CONFIG.nameColumn, dataRows).getValues();

  // Извлекаем URL из каждой ячейки (поддержка гиперссылок)
  var resolvedUrls = [];
  for (var k = 0; k < dataRows; k++) {
    var cell = sheet.getRange(CONFIG.headerRows + 1 + k, CONFIG.urlColumn);
    resolvedUrls.push(extractUrlFromCell(cell));
  }

  var processed = 0;
  var errors = 0;
  var ss = sheet.getParent();

  // Считаем сколько строк нужно обработать
  var total = 0;
  for (var j = 0; j < resolvedUrls.length; j++) {
    if (resolvedUrls[j] && resolvedUrls[j].match(/^https?:\/\//) && (!names[j][0] || names[j][0] === '')) total++;
  }

  if (total === 0) {
    SpreadsheetApp.getUi().alert('Нет новых URL для обработки');
    return;
  }

  for (var i = 0; i < resolvedUrls.length; i++) {
    var url = resolvedUrls[i];
    var name = names[i][0];

    if (url && url.match(/^https?:\/\//) && (!name || name === '')) {
      var row = CONFIG.headerRows + 1 + i;
      ss.toast('Обработка ' + (processed + errors + 1) + ' из ' + total + '...', '⏳ Пакетный парсинг', -1);
      try {
        processUrl(sheet, row, url);
        processed++;
        Utilities.sleep(1000);
      } catch (err) {
        sheet.getRange(row, CONFIG.statusColumn).setValue('Ошибка: ' + err.message);
        errors++;
      }
    }
  }

  SpreadsheetApp.getUi().alert('Готово!\nОбработано: ' + processed + '\nОшибок: ' + errors);
}

function parseCurrentRow() {
  var sheet = SpreadsheetApp.getActive().getActiveSheet();
  if (sheet.getName() !== CONFIG.sheetName) {
    SpreadsheetApp.getUi().alert('Перейдите на лист "' + CONFIG.sheetName + '"');
    return;
  }

  var row = SpreadsheetApp.getActive().getActiveCell().getRow();
  if (row <= CONFIG.headerRows) {
    SpreadsheetApp.getUi().alert('Выберите строку с данными (ниже заголовков)');
    return;
  }

  var urlCell = sheet.getRange(row, CONFIG.urlColumn);
  var url = extractUrlFromCell(urlCell);
  if (!url || !url.match(/^https?:\/\//)) {
    SpreadsheetApp.getUi().alert('В колонке A этой строки нет URL');
    return;
  }

  try {
    processUrl(sheet, row, url);
    SpreadsheetApp.getUi().alert('Строка ' + row + ' заполнена.');
  } catch (err) {
    SpreadsheetApp.getUi().alert('Ошибка: ' + err.message);
  }
}

// ============================================================
// ОСНОВНАЯ ЛОГИКА
// ============================================================

function processUrl(sheet, row, url) {
  var ss = sheet.getParent();
  ss.toast('Строка ' + row + ': загружаю данные...', '⏳ Парсинг', -1);

  var data = parseLotUrl(url);
  if (data) {
    fillRow(sheet, row, data);
    ss.toast('Строка ' + row + ': ' + (data.name || 'готово').substring(0, 50), '✅ Заполнено', 5);
  } else {
    ss.toast('Строка ' + row + ': не удалось извлечь данные', '⚠️ Пусто', 5);
  }
}

function parseLotUrl(url) {
  if (url.indexOf('tbankrot.ru') !== -1) {
    return parseTbankrot(url);
  }
  if (url.indexOf('m-ets.ru') !== -1) {
    return parseMets(url);
  }
  if (url.indexOf('bankrot.fedresurs.ru') !== -1) {
    return parseFedresurs(url);
  }
  throw new Error('Неизвестный источник. Поддерживаются: tbankrot.ru, m-ets.ru');
}

// ============================================================
// АВТОРИЗАЦИЯ tbankrot.ru
// ============================================================

/**
 * Логин на tbankrot.ru, возвращает строку cookies для последующих запросов.
 * Кэширует в Script Properties на 24 часа.
 */
function getTbankrotCookies() {
  // Проверяем кэш в памяти (в рамках одного выполнения)
  if (_sessionCookies) return _sessionCookies;

  // Проверяем кэш в Script Properties
  var props = PropertiesService.getScriptProperties();
  var cached = props.getProperty('tb_cookies');
  var cachedTime = props.getProperty('tb_cookies_time');

  if (cached && cachedTime) {
    var age = Date.now() - parseInt(cachedTime);
    if (age < 24 * 60 * 60 * 1000) { // 24 часа
      _sessionCookies = cached;
      return cached;
    }
  }

  // Логинимся
  var loginResponse = UrlFetchApp.fetch('https://tbankrot.ru/script/submit.php', {
    method: 'post',
    payload: {
      key: 'login',
      mail: CONFIG.tbankrotEmail,
      pas: CONFIG.tbankrotPassword
    },
    headers: {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
      'Referer': 'https://tbankrot.ru/login'
    },
    followRedirects: false,
    muteHttpExceptions: true
  });

  // Собираем cookies из Set-Cookie заголовков
  var setCookieHeaders = loginResponse.getAllHeaders()['Set-Cookie'] || [];
  if (typeof setCookieHeaders === 'string') {
    setCookieHeaders = [setCookieHeaders];
  }

  var cookies = [];
  for (var i = 0; i < setCookieHeaders.length; i++) {
    var cookiePart = setCookieHeaders[i].split(';')[0];
    cookies.push(cookiePart);
  }

  var cookieString = cookies.join('; ');

  // Сохраняем в кэш
  _sessionCookies = cookieString;
  props.setProperty('tb_cookies', cookieString);
  props.setProperty('tb_cookies_time', Date.now().toString());

  return cookieString;
}

// ============================================================
// ПАРСЕР: tbankrot.ru
// ============================================================

function parseTbankrot(url) {
  var cookies = getTbankrotCookies();
  var html = fetchPageWithCookies(url, cookies);

  // Если страница содержит барьер авторизации — перелогиниваемся
  if (html.indexOf('free_activation_field') !== -1 && html.indexOf('Для просмотра полной информации') !== -1) {
    // Сброс кэша cookies
    var props = PropertiesService.getScriptProperties();
    props.deleteProperty('tb_cookies');
    props.deleteProperty('tb_cookies_time');
    _sessionCookies = null;

    cookies = getTbankrotCookies();
    html = fetchPageWithCookies(url, cookies);
  }

  var data = {};

  // --- Заголовок ---
  var h1Match = html.match(/<h1[^>]*>([\s\S]*?)<\/h1>/);
  var h1Text = h1Match ? stripTags(h1Match[1]).trim().replace(/\s+/g, ' ') : '';

  // Если h1 = "Торги должника: ФИО" — это не название лота, берём из описания
  if (/^Торги должника/i.test(h1Text)) {
    // Ищем описание лота (первое предложение до "Вид имущества" или первая точка)
    var lotDescMatch = html.match(/<div class="lot_text">([\s\S]*?)<\/div>/) ||
                       html.match(/lot_description[^>]*>([\s\S]*?)<\//) ||
                       html.match(/<p[^>]*>\s*(?:<[^>]+>\s*)*([А-Яа-яA-Za-z][^<]{3,})/);
    if (lotDescMatch) {
      var descText = stripTags(lotDescMatch[1]).trim().replace(/\s+/g, ' ');
      // Берём текст до "Вид имущества" или до первой точки
      var nameEnd = descText.match(/^([\s\S]*?)(?:\.\s*Вид имущества|\.\s*Тип собственности)/i);
      if (nameEnd) {
        data.name = nameEnd[1].trim();
      } else {
        // Берём первое предложение
        var firstSentence = descText.split('.')[0].trim();
        data.name = firstSentence.length > 3 ? firstSentence : descText.substring(0, 100);
      }
    } else {
      data.name = h1Text;
    }
  } else {
    data.name = h1Text;
  }

  // --- Кадастровый номер ---
  var kadMatch = html.match(/\b(\d{2}:\d{2}:\d{5,8}:\d{1,6})\b/);
  if (kadMatch) {
    data.cadastral = kadMatch[1];
    if (data.name) {
      data.name = data.name + ' (' + data.cadastral + ')';
    }
  }

  // --- Номер торгов (официальный, из другого места) ---
  var numMatch = html.match(/Торги\s*№\s*([\w-]+)/);
  if (numMatch) {
    data.auctionNumber = numMatch[1];
  }

  // --- Точный адрес (для наименования) ---
  var fullAddress = '';

  // 1. Из блока "Адрес (местоположение):" в HTML
  var preciseAddr = html.match(/Адрес\s*\(местоположение\)\s*:[\s\S]*?<span[^>]*>\s*([\s\S]*?)<\/span>/i);
  if (preciseAddr) {
    var addr = stripTags(preciseAddr[1]).trim().replace(/\s+/g, ' ');
    if (addr.length > 3) fullAddress = addr;
  }

  // 2. Из textarea lot_name (Местоположение ... :)
  if (!fullAddress) {
    var lotNameArea = html.match(/<textarea[^>]*id="lot_name"[^>]*>([\s\S]*?)<\/textarea>/i);
    if (lotNameArea) {
      var lotNameText = stripTags(lotNameArea[1]).trim();
      var locMatch = lotNameText.match(/Местоположение[^:]*:\s*([^\n.;]{5,200})/i);
      if (locMatch) fullAddress = locMatch[1].trim().replace(/\s+/g, ' ');
    }
  }

  // 3. Из полнотекстового поиска по странице
  if (!fullAddress) {
    var fullText = stripTags(html);
    var addrPatterns = [
      /Местоположение[^:;,.]*?[:\-]\s*([^\n;]{5,150})/i,
      /Местонахождение[^:;,.]*?[:\-]\s*([^\n;]{5,150})/i,
      /[Аа]дрес[^:;,.]*?[:\-]\s*([^\n;]{5,150})/i,
      /[Рр]асположен[а-я]*\s+(?:по адресу[:\s]*)([^\n;]{5,150})/i,
      /[Нн]аходи[тв][а-я]*\s+(?:по адресу[:\s]*)([^\n;]{5,150})/i,
      /по адресу[:\s]+([^\n;]{5,150})/i
    ];
    for (var p = 0; p < addrPatterns.length; p++) {
      var addrMatch = fullText.match(addrPatterns[p]);
      if (addrMatch) {
        fullAddress = addrMatch[1].trim().replace(/\s+/g, ' ');
        if (fullAddress) break;
      }
    }
  }

  // Дописать полный адрес к наименованию
  if (fullAddress && data.name) {
    data.name = data.name + ', ' + fullAddress;
  }

  // --- Город (короткий) ---
  if (fullAddress) {
    data.city = extractCityFromText(fullAddress);
  }
  if (!data.city && data.name) {
    data.city = extractCityFromText(data.name);
  }

  // --- Тип торгов ---
  var typeMatch = html.match(/<img\s+title="([^"]+)"\s+src="\/img\/a_(up|down)\.png"/);
  if (typeMatch) {
    data.auctionType = typeMatch[1];
  }
  if (!data.auctionType) {
    var lotTypeMatch = html.match(/<span class="lot_type">\s*\(([^)]+)\)\s*<\/span>/);
    if (lotTypeMatch) {
      data.auctionType = lotTypeMatch[1].trim();
    }
  }

  // --- Начальная цена ---
  var priceMatch = html.match(/<span class="sum[^"]*">([\d\s,]+)<\/span>/);
  if (priceMatch) {
    data.startPrice = parseRussianNumber(priceMatch[1]);
  }

  // --- Шаг аукциона ---
  var stepMatch = html.match(/<p class="h6">Шаг аукциона<\/p>\s*<p[^>]*>([\d\s,]+)\s*руб/i);
  if (stepMatch) {
    data.step = parseRussianNumber(stepMatch[1]);
  }

  // --- Задаток ---
  var depositMatch = html.match(/<p class="h6">Задаток<\/p>\s*<p[^>]*>([\d\s,]+)\s*руб/i);
  if (depositMatch) {
    data.deposit = parseRussianNumber(depositMatch[1]);
  }

  // --- Текущая цена (ПП) ---
  var curPriceMatch = html.match(/<p class="h6">текущая цена<\/p>\s*<p[^>]*>([\d\s,]+)\s*руб/i);
  if (curPriceMatch) {
    data.currentPrice = parseRussianNumber(curPriceMatch[1]);
  }

  // --- Минимальная цена (ПП) ---
  var minPriceMatch = html.match(/<p class="h6">минимальная цена<\/p>\s*<p[^>]*>([\d\s,]+)\s*руб/i);
  if (minPriceMatch) {
    data.minPrice = parseRussianNumber(minPriceMatch[1]);
  }

  // Статус не парсим — это внутренний статус компании, ставится вручную

  // ===== ДАННЫЕ ДОСТУПНЫЕ ТОЛЬКО С АВТОРИЗАЦИЕЙ =====

  // --- Прием заявок (даты) ---
  // Формат: <span class="gray">Прием заявок:</span> с <span class="date">29/01/2026</span> <span class="time">07:00</span> до <span class="date">17/02/2026</span>
  var zayavkiMatch = html.match(/Прием заявок:[\s\S]*?<span class="date">(\d{2}\/\d{2}\/\d{4})<\/span>[\s\S]*?до\s*<span class="date">(\d{2}\/\d{2}\/\d{4})<\/span>/i);
  if (zayavkiMatch) {
    data.applicationStart = convertDate(zayavkiMatch[1]);
    data.applicationEnd = convertDate(zayavkiMatch[2]);
  }

  // --- Проведение торгов (дата начала) ---
  var torgiMatch = html.match(/Проведение торгов:[\s\S]*?<span class="date">(\d{2}\/\d{2}\/\d{4})<\/span>/i);
  if (torgiMatch) {
    data.auctionDate = convertDate(torgiMatch[1]);
  }

  // --- Организатор ---
  var orgMatch = html.match(/Организатор:[\s\S]*?<\/span>([\s\S]*?)(?:<span class="gray">|<\/td>)/i);
  if (orgMatch) {
    var orgText = stripTags(orgMatch[1]).trim();
    // Берём первую строку (имя/название)
    var orgName = orgText.split(/\d/)[0].trim();
    if (orgName.length > 3) {
      data.organizer = orgName;
    }
  }

  // --- ЭТП (ссылка на площадку) ---
  var etpMatch = html.match(/etp_url[^"]*"[^>]*href="([^"]+)"/);
  if (!etpMatch) {
    etpMatch = html.match(/href="([^"]+)"[^>]*etp_url/);
  }
  if (etpMatch) {
    data.etpUrl = etpMatch[1];
  }

  // --- Должник ---
  var debtor = html.match(/Должник:[\s\S]*?<\/span>([\s\S]*?)(?:<span class="gray">|Дело|ИНН|\[)/i);
  if (debtor) {
    var debtorName = stripTags(debtor[1]).trim();
    if (debtorName.length > 2) {
      data.debtor = debtorName.substring(0, 100);
    }
  }

  // --- Номер дела ---
  var deloMatch = html.match(/Дело\s*№\s*([\wА-Яа-я\d\/-]+)/);
  if (deloMatch) {
    data.caseNumber = deloMatch[1];
  }

  return data;
}

// ============================================================
// ПАРСЕР: m-ets.ru (заготовка)
// ============================================================

function parseMets(url) {
  var html;
  try {
    html = fetchPage(url);
  } catch (e) {
    throw new Error('m-ets.ru недоступен (' + e.message + '). Используйте ссылку с tbankrot.ru');
  }

  var data = {};

  var titleMatch = html.match(/<h1[^>]*>([\s\S]*?)<\/h1>/);
  if (titleMatch) {
    data.name = stripTags(titleMatch[1]).trim();
  }

  var priceMatch = html.match(/[Нн]ачальная\s*цена[^<]*?(\d[\d\s,\.]+)/);
  if (priceMatch) {
    data.startPrice = parseRussianNumber(priceMatch[1]);
  }

  if (data.name) {
    data.city = extractCityFromText(data.name);
  }

  return data;
}

// ============================================================
// ПАРСЕР: bankrot.fedresurs.ru (заготовка)
// ============================================================

function parseFedresurs(url) {
  throw new Error('bankrot.fedresurs.ru пока не поддерживается. Используйте tbankrot.ru');
}

// ============================================================
// ЗАПОЛНЕНИЕ СТРОКИ
// ============================================================

function fillRow(sheet, row, data) {
  // B — Наименование лота
  if (data.name) {
    sheet.getRange(row, CONFIG.nameColumn).setValue(data.name);
  }

  // C — Город
  if (data.city) {
    sheet.getRange(row, CONFIG.cityColumn).setValue(data.city);
  }

  // D — Статус: всегда ставим "Осмотр" при парсинге
  sheet.getRange(row, CONFIG.statusColumn).setValue('Осмотр');

  // G — Тип торгов (оа / пп)
  if (data.auctionType) {
    var typeShort = data.auctionType;
    if (/открыт/i.test(data.auctionType) || /аукцион/i.test(data.auctionType)) {
      typeShort = 'оа';
    } else if (/публичн/i.test(data.auctionType) || /предложен/i.test(data.auctionType)) {
      typeShort = 'пп';
    }
    sheet.getRange(row, CONFIG.auctionTypeColumn).setValue(typeShort);
  }

  // H — Окончание подачи заявок
  if (data.applicationEnd) {
    sheet.getRange(row, CONFIG.applicationDeadlineColumn).setValue(data.applicationEnd);
  }

  // I — Дата торгов
  if (data.auctionDate) {
    sheet.getRange(row, CONFIG.auctionDateColumn).setValue(data.auctionDate);
  }

  // J — Даты задатков: не заполняем

  // K — Задатки (сумма)
  if (data.deposit) {
    sheet.getRange(row, CONFIG.depositColumn).setValue(data.deposit);
  }

  // M — Покупка Min (начальная цена)
  if (data.startPrice) {
    sheet.getRange(row, CONFIG.buyMinColumn).setValue(data.startPrice);
  }

  // N, O — Покупка Med/Max: не трогаем, заполняется вручную

  // AC — Ставка (шаг аукциона)
  if (data.step) {
    sheet.getRange(row, CONFIG.stepColumn).setValue(data.step);
  }
}

// ============================================================
// УТИЛИТЫ
// ============================================================

/**
 * Загрузить страницу БЕЗ авторизации.
 */
function fetchPage(url) {
  var response = UrlFetchApp.fetch(url, {
    muteHttpExceptions: true,
    followRedirects: true,
    headers: {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.3'
    }
  });

  if (response.getResponseCode() !== 200) {
    throw new Error('HTTP ' + response.getResponseCode());
  }

  return response.getContentText('UTF-8');
}

/**
 * Загрузить страницу С cookie авторизации.
 */
function fetchPageWithCookies(url, cookies) {
  var response = UrlFetchApp.fetch(url, {
    muteHttpExceptions: true,
    followRedirects: true,
    headers: {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.3',
      'Cookie': cookies
    }
  });

  if (response.getResponseCode() !== 200) {
    throw new Error('HTTP ' + response.getResponseCode());
  }

  return response.getContentText('UTF-8');
}

/**
 * Извлечь URL из ячейки (гиперссылка, формула HYPERLINK, или просто текст).
 */
function extractUrlFromCell(cell) {
  // 1. Проверяем формулу =HYPERLINK("url", "text")
  var formula = cell.getFormula();
  if (formula) {
    var hrefMatch = formula.match(/HYPERLINK\s*\(\s*"([^"]+)"/i);
    if (hrefMatch) return hrefMatch[1].trim();
  }

  // 2. Проверяем RichText ссылку (вставленная гиперссылка)
  var richText = cell.getRichTextValue();
  if (richText) {
    var linkUrl = richText.getLinkUrl();
    if (linkUrl) return linkUrl.trim();

    // Может быть ссылка на части текста — берём первую
    var runs = richText.getRuns();
    for (var i = 0; i < runs.length; i++) {
      var runUrl = runs[i].getLinkUrl();
      if (runUrl) return runUrl.trim();
    }
  }

  // 3. Просто текст
  return cell.getValue().toString().trim();
}

/**
 * Убрать HTML-теги.
 */
function stripTags(html) {
  return html.replace(/<br\s*\/?>/gi, ' ').replace(/<[^>]+>/g, '').replace(/\s+/g, ' ');
}

/**
 * Парсинг русского числа: "713 156,00" → 713156
 */
function parseRussianNumber(text) {
  var clean = text.replace(/\s/g, '').replace(',', '.');
  var num = parseFloat(clean);
  return isNaN(num) ? '' : Math.round(num);
}

/**
 * Конвертация даты: "29/01/2026" → "29.01.2026"
 */
function convertDate(dateStr) {
  return dateStr.replace(/\//g, '.');
}

/**
 * Извлечь город/регион из текста.
 */
function extractCityFromText(text) {
  var cityMatch = text.match(/г\.\s*([А-Яа-яЁё-]+)/);
  if (cityMatch) return 'г. ' + cityMatch[1];

  // Пермский край / Пермская область → Пермь
  if (/Пермск(ий|ой|ого)\s+кра[йяю]/i.test(text) || /Пермск(ая|ой|ую)\s+обл/i.test(text)) {
    return 'Пермь';
  }

  var regionMatch = text.match(/([\wА-Яа-яЁё-]+\s+(?:край|область|республика))/i);
  if (regionMatch) {
    var settlementMatch = text.match(/(?:д\.|с\.|пос\.|п\.|дер\.)\s*([А-Яа-яЁё-]+)/);
    if (settlementMatch) {
      return regionMatch[1] + ', ' + settlementMatch[0];
    }
    return regionMatch[1];
  }

  var knownCities = ['Москва', 'Санкт-Петербург', 'Пермь', 'Самара', 'Казань',
    'Екатеринбург', 'Новосибирск', 'Краснодар', 'Калининград', 'Нижний Новгород',
    'Челябинск', 'Омск', 'Ростов-на-Дону', 'Уфа', 'Воронеж', 'Красноярск',
    'Волгоград', 'Тюмень', 'Саратов', 'Тольятти', 'Ижевск', 'Барнаул',
    'Ульяновск', 'Иркутск', 'Хабаровск', 'Ярославль', 'Владивосток',
    'Махачкала', 'Томск', 'Оренбург', 'Кемерово', 'Рязань', 'Пенза',
    'Набережные Челны', 'Астрахань', 'Липецк', 'Киров', 'Тула', 'Чебоксары',
    'Курск', 'Брянск', 'Иваново', 'Сочи', 'Тверь', 'Белгород', 'Сургут',
    'Краснокамск', 'Нытва'];

  for (var i = 0; i < knownCities.length; i++) {
    if (text.indexOf(knownCities[i]) !== -1) {
      return knownCities[i];
    }
  }

  return '';
}
