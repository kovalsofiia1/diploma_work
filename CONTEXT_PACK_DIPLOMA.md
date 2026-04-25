# КОНТЕКСТ ПРОЄКТУ ДЛЯ НАПИСАННЯ ДИПЛОМА (v1.0)

## 1. Назва та коротка суть
Тема: Розробка системи агрегування подій та валідації електронних квитків із використанням блокчейн-технологій.

Суть проєкту:
Розроблено клієнт-серверну систему, де користувачі переглядають події, бронюють квитки та проходять check-in за QR. 
Основна бізнес-логіка виконується на бекенді (FastAPI + PostgreSQL), а блокчейн (Polygon) використовується як шар аудиту незмінності критичних дій.

Ключова архітектурна ідея:
Backend-first + async blockchain writes.
Тобто бекенд є джерелом істини, а записи в блокчейн відправляються асинхронно без блокування HTTP-запитів.

---

## 2. Мета, об’єкт, предмет, завдання
Мета:
Підвищити надійність і безпеку сервісу електронних квитків за рахунок гібридної архітектури, де перевірка квитка швидка (по БД), а блокчейн забезпечує аудит.

Об’єкт дослідження:
Інформаційні системи онлайн-квиткування подій.

Предмет дослідження:
Методи та засоби побудови веб-системи квиткування з інтеграцією блокчейн-реєстру.

Основні завдання:
1) Реалізувати модуль керування подіями та квитками.
2) Реалізувати JWT-автентифікацію користувачів.
3) Реалізувати QR-перевірку квитків на основі підписаного JWT.
4) Реалізувати check-in із захистом від повторного використання.
5) Інтегрувати блокчейн Polygon як аудит-шар для mint/markUsed.
6) Забезпечити асинхронну відправку блокчейн-транзакцій.
7) Підготувати систему до деплою в тестову/продуктивну мережу Polygon.

---

## 3. Технологічний стек
Frontend:
- Ionic + Angular (буде деплоїтись як веб, то описуємо як просто Ангуляр)
- RxJS
- QR scanner модулі

Backend:
- Python 3.11
- FastAPI
- SQLAlchemy
- Pydantic / pydantic-settings
- JWT (auth + QR token)

База даних:
- PostgreSQL

Blockchain:
- Solidity smart contract (TicketRegistry)
- Hardhat
- web3.py
- Polygon PoS (testnet Amoy, mainnet Polygon)

Інші сервіси:
- Alchemy RPC (рекомендований провайдер)
- Cloudinary (медіа)

---

## 4. Архітектура системи
Система складається з таких підсистем:
1) Frontend (клієнтська частина)
2) Backend API (бізнес-логіка)
3) PostgreSQL (зберігання даних)
4) Blockchain layer (аудит транзакцій)
5) Parser-service (імпорт/агрегація зовнішніх подій)

Архітектурний принцип:
- Router -> Service -> Model/DB
- Роутери не виконують прямих блокчейн-викликів
- Блокчейн-виклики інкапсульовано в сервісному/блокчейн-шарі

---

## 5. Основний функціонал
### 5.1 Авторизація та профіль
- Реєстрація користувача
- Вхід (JWT access token)
- Отримання профілю
- Оновлення профілю

### 5.2 Події
- Перегляд списку подій
- Пошук/фільтрація
- Деталі події
- Внутрішні та зовнішні (агреговані) події

### 5.3 Бронювання квитка
- Створення запису квитка у БД
- Генерація QR-токена (JWT)
- Асинхронний запит на mint в блокчейн

### 5.4 Перевірка квитка
- Валідація QR JWT
- Перевірка в БД: існує/не використаний/статус
- Без прямого blockchain-read у request cycle

### 5.5 Check-in
- Валідація QR JWT
- Помітка `used=true` в БД
- Асинхронний blockchain markUsed

---

## 6. Модель даних (ключові сутності)
### User
- id
- email
- hashed_password
- full_name
- role/status
- profile fields

### Event
- id
- name/title
- city/location
- startDate
- source_type (INTERNAL/EXTERNAL)
- status

### Ticket
- id (внутрішній PK)
- ticket_id (публічний ідентифікатор)
- code
- event_id
- user_id
- token_id (ідентифікатор для smart contract)
- ticket_hash
- tx_hash
- used (bool)
- status

Статуси Ticket:
- reserved
- pending_onchain
- confirmed_onchain
- failed_onchain
- used

### Checkin
- id
- ticket_id (FK)
- scanned_at
- staff_user_id

Інваріанти:
1) Квиток не може бути використаний двічі (`used=true` блокує повторний check-in).
2) Для check-in потрібен валідний, підписаний, не прострочений QR JWT.
3) Бекенд є source of truth для валідації.
4) Blockchain використовується для аудиту критичних змін, а не для кожного запиту читання.

---

## 7. Ключові бізнес-флови
### 7.1 Booking flow
1) Клієнт надсилає запит бронювання.
2) Backend перевіряє подію/місця.
3) Створюється Ticket у БД зі статусом `pending_onchain`.
4) Генерується QR JWT (`ticket_id`, `event_id`, `exp`).
5) Клієнт отримує відповідь одразу.
6) У background виконується `mint_ticket`.
7) При успіху -> `confirmed_onchain`, при помилці -> `failed_onchain`.

### 7.2 Verify flow
1) Сканується QR.
2) Backend декодує і валідує JWT.
3) Пошук квитка в БД за `ticket_id/event_id`.
4) Перевірка: існує, не used, статус допустимий.
5) Повернення `VALID` або `INVALID`.

### 7.3 Check-in flow
1) Отримання `qr_token`.
2) JWT валідація + перевірка в БД.
3) Встановлення `used=true`, статус `used`.
4) Запис у таблицю `checkins`.
5) Асинхронний виклик `mark_used` у блокчейн.

---

## 8. Смартконтракт і блокчейн-інтеграція
Смартконтракт TicketRegistry:
- mintTicket(...)
- markUsed(...)
- (read methods можуть існувати, але не використовуються у критичному request cycle)

Мережі:
- Polygon Amoy (testnet)
- Polygon PoS (mainnet)

Hardhat:
- окремі конфіги мереж
- deploy script з виводом contract address + ABI artifact

Роль блокчейну:
- незмінний журнал ключових дій із квитком
- доказ аудиту (audit trail)

---

## 9. Безпека
1) Авторизація:
- JWT для доступу до API

2) QR безпека:
- QR містить підписаний JWT, а не простий hash
- payload: `ticket_id`, `event_id`, `exp`

3) Секрети:
- ключі зберігаються в `.env`
- приватні ключі не зберігаються в коді/репозиторії

4) Захист від зловживань:
- контроль повторного check-in через `used`
- перевірка строку дії токена (`exp`)
- розмежування доступів на рівні API

---

## 10. Рішення та мотивація (ADR-lite)
Рішення 1: Відмова від синхронного mint у booking endpoint.
Причина: зменшення latency та залежності від RPC.
Компроміс: можливий тимчасовий стан `pending_onchain`.

Рішення 2: DB-first verify/check-in.
Причина: стабільність, швидкодія, передбачуваність UX.
Компроміс: потрібна узгоджена синхронізація статусів з audit layer.

Рішення 3: JWT QR замість hash-QR.
Причина: підпис + строк дії + складніше підробити.
Компроміс: потрібна ротація секретів і політика TTL.

---

## 11. Нефункціональні вимоги
- Продуктивність: швидка валідація квитків без blockchain-read у запиті
- Масштабованість: асинхронні задачі для blockchain writes
- Надійність: чіткі статуси життєвого циклу квитка
- Безпека: секрети в env, токени з exp, контроль доступу
- Підтримуваність: модульна архітектура, розділення router/service/blockchain

---

## 12. Середовища виконання
Local:
- backend: FastAPI
- frontend: Ionic/Angular
- db: PostgreSQL
- optional local hardhat

Testnet:
- Polygon Amoy RPC
- тестовий деплой контракту

Prod target:
- Polygon PoS mainnet
- RPC провайдер (Alchemy)
- окремі production secrets

---

## 13. Відомі обмеження і подальший розвиток
Обмеження:
- BackgroundTasks підходить для MVP, але не гарантує надійний retry як окремий worker+queue.
- Потрібний розширений моніторинг транзакцій та алертинг.
- Потрібні формалізовані навантажувальні тести.

Подальший розвиток:
1) Перехід на outbox pattern / чергу (Celery/RQ/Kafka).
2) Retry policy і DLQ для blockchain-операцій.
3) Розширена аналітика check-in.
4) Повний CI/CD pipeline з безпековими перевірками.
5) Rotation policy для JWT/TICKET secrets.

---

## 14. Терміни
- Backend-first: підхід, де логіка та валідація виконуються в бекенді.
- Audit layer: шар незмінного логування дій.
- pending_onchain: квиток створено в БД, транзакція ще не підтверджена.
- confirmed_onchain: транзакція mint підтверджена.
- failed_onchain: помилка blockchain-операції.
- check-in: процедура факту використання квитка на вході.

---

## 15. Повна функціональна карта системи (по модулях)
### 15.1 Backend API (FastAPI)
Auth модуль:
- `POST /auth/register` — реєстрація користувача.
- `POST /auth/login` — вхід (OAuth2 form), видача JWT access token.
- `GET /auth/me` — поточний профіль.
- `PATCH /auth/me` — редагування профілю.
- `POST /auth/me/image` — завантаження аватара (Cloudinary).
- `GET /auth/me/cities` — міста користувача.
- `POST /auth/me/cities` — оновлення підписки на міста.
- `GET /auth/me/stats` — агрегована статистика профілю.
- `POST /auth/logout` — симетричний endpoint для клієнта (JWT stateless).
- `GET /auth/google/start`, `GET /auth/google/callback` — Google OAuth flow.

Events модуль:
- `GET /cities` — список міст із локальної таблиці.
- `POST /cities/sync` — синхронізація довідника міст з parser-service + INTERNAL events.
- `POST /events` — створення внутрішньої події.
- `PUT /events/{event_id}` — редагування внутрішньої події.
- `DELETE /events/{event_id}` — видалення внутрішньої події.
- `GET /events/all` — уніфікований каталог INTERNAL+EXTERNAL (фільтри, пошук, пагінація).
- `GET /events/lookup/{uid}` — детальний пошук події за `uid`.
- `GET /events/me/favorites`, `POST /events/me/favorites/{uid}`, `DELETE /events/me/favorites/{uid}` — вибране.
- `GET /events/me/assigned` — події, де користувач організатор/сканер.
- `POST /events/{uid}/members`, `GET /events/{uid}/members`, `DELETE /events/{uid}/members/{member_user_id}` — керування ролями в події.
- `POST /events/scrape` — ініціація імпорту зовнішніх подій у БД (upsert).

Tickets/Booking/Check-in модулі:
- `POST /book` — компактний booking endpoint (legacy-сумісність).
- `POST /tickets/book` — бронювання одиночного квитка.
- `POST /tickets/book/batch` — пакетне бронювання.
- `GET /tickets/me` — список квитків користувача з QR token.
- `POST /tickets/verify` — DB-first валідація QR JWT.
- `POST /checkin` — check-in за QR JWT, зміна статусу на `used`.

### 15.2 Frontend (Ionic/Angular)
- Екрани auth (login/register/profile).
- Каталог подій із пошуком/фільтрами.
- Екран деталей події.
- Бронювання (одиночне/пакетне).
- «Мої квитки» з QR.
- Сканер для verify/check-in (камера + файл).

### 15.3 Parser-service
- `GET /health` — health-check.
- `GET /cities` — live-отримання міст із concert.ua/karabas + fallback до кеш-індексу.
- `POST /scrape/events` — повне скраплення з батч-відповіддю.
- `POST /scrape/events/stream` — NDJSON-стрім батчів для довгих операцій.
- `POST /scrape/dou` — окремий скрапер dou.ua.

---

## 16. Агрегація даних: pipeline і нормалізація
### 16.1 Джерела
- `concert.ua`
- `karabas.com`
- `dou.ua`

### 16.2 Конвеєр агрегації
1) Клієнт/бекенд формує `ScrapeEventsRequest` (міста, джерела, concurrency, batch size).
2) Parser-service запускає асинхронні задачі по містах та джерелах.
3) Для `concert.ua` і `karabas.com` виконується listing-парсинг + (опційно) detail enrichment.
4) Для `dou.ua` запускається окремий глобальний парсер.
5) Події приводяться до `NormalizedEvent` (уніфікована схема).
6) Результат повертається як:
   - повний JSON (`/scrape/events`) або
   - NDJSON потік батчів (`/scrape/events/stream`).
7) Backend endpoint `/events/scrape` виконує upsert зовнішніх подій у таблицю `events`:
   - нові записи створюються як `source_type=EXTERNAL`;
   - існуючі оновлюються при зміні полів;
   - формуються стабільні `uid` для зовнішніх сутностей.

### 16.3 Нормалізовані поля події
- `name`, `type`, `url`, `order_url`
- `startDate`, `endDate`
- `location_name`, `city`
- `price_low`, `price_high`, `price_currency`
- `image`
- `source`
- `description` (якщо доступний details parsing)

### 16.4 Синхронізація довідника міст
`POST /cities/sync`:
- бере список міст із parser-service (`/cities`);
- об’єднує з містами INTERNAL-подій;
- перевписує локальну таблицю `cities`;
- зберігає також англомовні/slug-представлення (`name_en`) для коректного скрапінгу.

---

## 17. Воркери та фонові задачі (фактична реалізація)
### 17.1 Що вже реалізовано
1) HTTP-level background tasks у Backend:
- `mint_ticket_async(ticket_id)`:
  - викликається після booking;
  - виконує blockchain `mint_ticket`;
  - оновлює `status` (`confirmed_onchain` або `failed_onchain`) і `tx_hash`.
- `mark_ticket_used_async(ticket_id)`:
  - викликається після успішного check-in;
  - виконує blockchain `mark_used`;
  - фіксує `tx_hash`.

2) Parser async workers (в межах процесу parser-service):
- паралельні задачі по містах через `asyncio` + semaphore;
- керована конкуренція через параметр `concurrency`;
- batch/stream режими видачі, щоб уникати блокуючих довгих відповідей.

### 17.2 Що поки НЕ реалізовано (але рекомендовано)
- Окремий брокер черг (RabbitMQ/Redis/Kafka).
- Стійкі воркери (Celery/RQ/Arq) з retry/backoff/DLQ.
- Outbox pattern для гарантованої доставки blockchain-транзакцій.
- Планувальник (cron/APScheduler) для періодичного авто-скрапінгу.

---

## 18. Повний перелік фловів системи
1) User registration/login/logout.
2) Google OAuth login.
3) Profile management + avatar upload.
4) User city subscriptions.
5) Internal event CRUD.
6) Event roles (organizer/scanner) and member management.
7) Unified event feed with favorites/assigned filters.
8) External data ingestion via parser-service and upsert to DB.
9) Ticket booking (single/batch) with DB-first lifecycle.
10) QR generation with signed JWT payload.
11) DB-only ticket verification.
12) Check-in with anti-reuse (`used=true`) and checkin log.
13) Async blockchain audit writes (mint, markUsed).
14) Polygon deploy workflow (Hardhat -> contract address + ABI artifact).