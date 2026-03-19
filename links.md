# Estate Invest — Ссылки и ресурсы

## Сайт
- **Личный кабинет инвестора**: https://estateinvest.online
- **Вход**: https://estateinvest.online/sign-in
- **Все объекты**: https://estateinvest.online/dashboard/all-properties
- **Новости**: https://estateinvest.online/dashboard/news
- **FAQ**: https://estateinvest.online/dashboard/faq (SPA, требует JS)
- **Портфель**: https://estateinvest.online/dashboard#portfolio
- **Операции**: https://estateinvest.online/dashboard#txs
- **Реферальная система**: https://estateinvest.online/dashboard#referral

## Учёт и финансы (Google Sheets)
- **Основная таблица учёта**: https://docs.google.com/spreadsheets/d/1dWTjYF8sEc20SKeyl-e6PomBFq3VlfX-m8K2ZRopZJ0/edit
  - Общая база (gid=2024918270) — все транзакции
  - Свод объекты+инвесторы (gid=498186989)
  - Объекты (gid=1464507984) — справочник объектов
  - Свод инвесторы (gid=1231813197)
  - Свод объекты (gid=1989607622)
  - Инвесторы (gid=2121197329) — справочник инвесторов
  - Справочник (gid=703112305)
  - Инструкция (gid=233535053)
  - FAQ (gid=1873208250)
  - Новости (gid=527357395)
  - Архив (gid=1029269575)
- **Касса компании**: https://docs.google.com/spreadsheets/d/1aRi5YLORBWDY5oU7hNo1XAWUoIvAM3ArxX7L2dbJHEc/edit
  - Движение денежных средств (закрытый доступ, требует авторизации)

## Статистика и аналитика
- **Статистика продаж**: https://docs.google.com/spreadsheets/d/18S6crJXwHXCh1FKEzgc4444yn4T1KQd30ycpvmVx2Mk/edit
  - 7 листов: 2025, объекты, люди, доход инвесторов, доходы авто, Лист6, Общий портфель за все время
  - Лист "2025" (публичный): 34 проданных объекта, ROI, выплаты инвесторам, кол-во инвесторов, среднее вложение
  - Остальные листы — закрытый доступ

## Монитор объектов (отдел Реализации)
- **Монитор объектов**: https://docs.google.com/spreadsheets/d/1oTRqpqS5GIunhi26TO8X6quWR5wWIWoTe0LzFqEGrDs/edit
  - 118 ИП (ИП №1 — ИП №118), колонки: покупка, продажа, ROI, сроки, ссылки на Авито
  - Колонка B — гиперссылки на **117 индивидуальных касс** (каждая = отдельная Google Sheets)
  - Колонки Q-V — ссылки на объявления Авито (46 ссылок)
  - **Apps Script автопарсер** встроен (Code.gs): вставка URL tbankrot.ru → автозаполнение данных лота
- **Таблица торгов** (лист "Торги" внутри монитора): парсинг лотов с tbankrot.ru, m-ets.ru

## Торги (отдельная таблица)
- **Таблица торгов**: https://docs.google.com/spreadsheets/d/1Ulf_odOSRFcs4Ihi3waCo1Py_a0SgI3-FHlIKdCQvSU/edit?gid=1389523539
  - Колонки: Номер торгов, Наименование лота, Город, Статус, Проверка документов, Комментарий риелтора, Тип торгов, Окончание подачи заявок, Дата торгов, Даты задатков, Задатки, Срок оплаты, Покупка Min/Med/Max, Продажа Min/Med/Max, Срок Min/Med/Max, Расходы
  - Используется для отслеживания аукционных лотов перед выкупом

## Прочие таблицы (закрытый доступ)
- **Таблица (неизвестное назначение)**: https://docs.google.com/spreadsheets/d/1DCxgwIKwJHSa5RwrCrqLUmb8ZCAFOnaHijtEfqXEiQA/edit (закрытый доступ, требует авторизации)

## GitHub Pages (публичные страницы)
- **Главная**: https://yarbalakin.github.io/estate-invest-academy/
- **ИП31 Соликамская — Итоги проекта**: https://yarbalakin.github.io/estate-invest-academy/ip31-solikamskaya.html
- **AI-аналитика**: https://yarbalakin.github.io/estate-invest-academy/ai-analytics.html
- **Реализация — сводка**: https://yarbalakin.github.io/estate-invest-academy/реализация-сводка.html
- **Карта объектов**: https://yarbalakin.github.io/estate-invest-academy/objects-map.html
- **AI-трансформация — дорожная карта**: https://yarbalakin.github.io/estate-invest-academy/ai-transformation.html
- Репо: `yarbalakin/estate-invest-academy` (публичный)

## Контент-план (отдел Контент — Глеб)
- **Контент-план**: https://docs.google.com/spreadsheets/d/1lV3gZiWGX8IxsMbKHyMYCAfJB5BeGa33raIFqMLtthk/edit
  - 10 листов-календарей по каналам:
  - **Паблик Доход 2025** — посты в публичный канал "Доход от недвижимости" (еженедельные отчёты, новости сборов, выплаты)
  - **Паблик Доход 2024** — архив 2024
  - **Практикум 2025** — контент курсов ФГ (задания, эфиры, рассылки)
  - **Практикум 2026** — план на 2026 (бот, оплата, таргет, рассылки)
  - **Дни практикума** — подробная программа по дням (книга, задания, эфиры)
  - **Закрытый канал инвесторов 2024/2025** — посты для действующих инвесторов (опросы, кейсы, лицензия ЦБ)
  - **Идеи для постов/рилс** — банк идей (reels, аудиоподкасты, кейсы с видео)
  - **Беспл Простая Истина** — контент для бесплатного канала
  - **Паблик "Доход от недвижимости"** — основной паблик

## Юридические документы и шаблоны
- **Инвестиционный договор**: https://docs.google.com/document/d/1M8nbyRvb7nEPgKUl9D4RYdkTXQQCA9gj/edit
- **Политика конфиденциальности**: https://estateinvest.online/docs/terms
- **Заявление на вывод на чужие реквизиты**: https://docs.google.com/document/d/1t-NLglsvON2JobBdKO-07JA-m13_3nt5InMIxfMEl-8/edit
- **Шаблоны писем**: https://docs.google.com/spreadsheets/d/1odfnhaeg6HWRgiMu0ASuMPXTgSx673t6BUUoVh7JIts/edit
  - Шаблоны email-сообщений: отправка инвестиционного договора (через SignEasy), welcome-письма, уведомления

## Соцсети и паблики
- **Аккаунты соцсетей**: https://docs.google.com/spreadsheets/d/1nwaS6lhg5SycS5B8gPQl3F-5qx6NuBeexnP782Nx_to/edit
  - Список VK-пабликов и аккаунтов (Глеб, Ярослав, другие), стратегия ведения

## Notion (страницы объектов)
- **База Notion**: https://estateinvest.notion.site
- Каждый объект: `estateinvest.notion.site/<номер>-<slug>`
- Примеры:
  - ИП №31 (Соликамская): https://estateinvest.notion.site/31-319-6d3e10d0f33f4d6fa4c63a0e2c10018c
  - ИП №70 (Партнёрское): https://estateinvest.notion.site/70-Estate-Invest-1146bbb019e080d99fe2e04b74ca895a
- **Прочие страницы Notion** (требуют JS, содержимое недоступно извне):
  - https://www.notion.so/estateinvest/69ac3149a05d459093ac29d36a70ef14
  - https://www.notion.so/estateinvest/7bede50b0965467d924160965e6dacf7
  - https://estateinvest.notion.site/c1d80f3c94734f559ce6eba984b56ebf

## Telegram
- **Публичный канал**: https://t.me/russianestateincome
- **Сообщество ФГ (Практикум)**: https://t.me/+FtOHpdRQfPJmOWQy (закрытая группа, практикум по финансовой грамотности, велся целый год)
- **Закрытый канал инвесторов**: https://t.me/+TOpOcVlVmJwxMWRj
- **Канал торгов**: https://t.me/torgiigrot
- **Бот поддержки**: @Estate_invest_RF_bot (Salebot, 2,127 клиентов, с марта 2023)

## Salebot (API)
- **API endpoint**: `chatter.salebot.pro/api/<api_key>/<action>`
- **Project ID**: 214444
- **Основные endpoints**: get_clients, get_messages, get_variables
- **Переменные клиента**: balanceTextInfo, freeBalanceTextInfo, referralsTextInfo, email, password
- **CRM-состояния**: Бронирование:Обработали

## Прочие ссылки из бота
- **Результаты проекта**: https://estateinvest.online/result
- **Настройка бота в ЛК**: https://estateinvest.online/dashboard/setup-bot
- **VK**: https://vk.com/estateinvest.online
- **VK Глеб**: https://vk.com/gleb_khrianin / https://vk.com/realtwingleb
- **VK Иван**: https://vk.com/ivanmudrov
- **Дзен**: https://dzen.ru/estateinvest
- **Telegra.ph (результаты)**: https://telegra.ph/Nashi-rezultaty-04-17-2

## Google Drive (общая папка компании)
- **Корневая папка**: https://drive.google.com/drive/folders/1d69F1D8WuCw1fZhs4fwBQ1KrOrLIlzaW
  - 12 подпапок:
  - Estate Invest презентация
  - Академия риелторов
  - Аналитика Авито
  - Для презентации
  - Живые встречи
  - ЗАПУСК ФГ
  - Маркетинг
  - Объекты
  - Отдел Кадров
  - Отдел Поддержки
  - Практикум по финансам и целям
  - Юр. отдел
  - Файлы в корне: АКЦИЯ - 1000 руб. за друга (Sheets), КОНТЕНТ ESTATE INVEST (Sheets), Иван.jpg

## Dropbox Paper (регламенты и документы)
- **Папка 1**: https://paper.dropbox.com/folder/show/e.1gg8YzoPEhbTkrhvQwJ2zzS47SQVXjvWUXGBiQ74dgLIrYsdok1K (требует авторизации)
- **Папка 2**: https://paper.dropbox.com/folder/show/e.1gg8YzoPEhbTkrhvQwJ2zzS1LMypdXBND6bQu2RxvilXOz5MKbpP (требует авторизации)
- **Salebot (документация)**: https://paper.dropbox.com/doc/Salebot--B4H7VZz5w3UGcDAzsP2SktZhAg-OW03bNWBmjZecI8Z3LPJj (требует авторизации)
- **Документ 3**: https://paper.dropbox.com/doc/--B9t0F9UHrKIY6jylmidOkn8jAg-OIema5FjZX1HWfkeDbZO5 (требует авторизации)
- **Документ 4**: https://paper.dropbox.com/doc/--CBAQXvG3tIfM6vBl3~6sXCJNAg-86hNbznxxd4rqGEwoOnOR (требует авторизации)

## Реферальные ссылки (формат)
- https://estateinvest.online/?r=<КОД>

## Инструкция по установке ЛК на смартфон
- https://clck.ru/34ciFz
