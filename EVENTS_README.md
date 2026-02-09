1. Ключова ідея (головне правило)

👉 Усі події в системі зберігаються в ОДНІЙ таблиці events,
незалежно від того:

створені вони на платформі
чи зібрані зі сторонніх сайтів
Різниця — у джерелі та статусі, а не в структурі.

2. Високорівнева архітектура
┌────────────┐        ┌──────────────────┐
│ Scraper    │  --->  │ Event Ingest API │
│ (Python)   │        │ (FastAPI/Nest)   │
└────────────┘        └─────────┬────────┘
                                 │
                         ┌───────▼────────┐
                         │   PostgreSQL    │
                         │ events, cities  │
                         └───────┬────────┘
                                 │
                    ┌────────────▼────────────┐
                    │ Background Workers       │
                    │ (Celery / Bull / APS)    │
                    └────────────┬────────────┘
                                 │
                         ┌───────▼────────┐
                         │ Notifications  │
                         │ / Cache        │
                         └────────────────┘


📌 Чому це важливо:

Додати властивості до події
source_type ENUM('INTERNAL', 'EXTERNAL'),
  source_name TEXT,              -- ticketmaster, concert.ua, etc
  source_event_id TEXT,          -- id з зовнішнього сайту
  source_url TEXT,

  status ENUM('ACTIVE', 'CANCELLED', 'DRAFT'),
  is_verified BOOLEAN,

  created_at TIMESTAMP,
  updated_at TIMESTAMP,


UNIQUE(source_name, source_event_id) → дедуплікація

внутрішні події просто мають source_type = INTERNAL

🔹 cities
cities (
  id UUID PK,
  name TEXT,
  country TEXT
)

🔹 user_city_subscriptions
user_city_subscriptions (
  user_id UUID,
  city_id UUID,
  created_at TIMESTAMP,
  PRIMARY KEY (user_id, city_id)
)

4. Як працює скрапер (external events)
🔄 Скрапер (окремий сервер)

Раз на добу (cron / celery beat):

парсить події з сайтів

Для кожної події:

нормалізує дані (дата, місто, назва)

Надсилає payload у бекенд:

POST /api/events/import
{
  "source_name": "concert.ua",
  "source_event_id": "12345",
  "title": "Imagine Dragons",
  "city": "Kyiv",
  "start_datetime": "...",
  "url": "..."
}

🔹 Ingest API (бекенд)
if (source_name + source_event_id exists):
    update event
else:
    create new event


📌 Скрапер НІКОЛИ не пише напряму в БД

5. Background workers — де і навіщо
🧵 Типи воркерів
1️⃣ Scraping workers (зовнішні)

живуть у scraper-сервісі

відповідають ТІЛЬКИ за збір даних

2️⃣ Backend workers (основні)
🔹 Worker: sync_events

Запуск:

раз на добу

або після імпорту великого пакету

Робить:

чистку старих подій

оновлення статусів

кешування popular events

🔹 Worker: city_subscription_handler

Тригер:

користувач обрав нове місто

або підписався на місто

Робить:

перевіряє, чи є події в цьому місті

якщо мало → ставить таску для скрапера

готує персональні рекомендації

🔹 Worker: notifications

Тригер:

нова подія у місті користувача

IF event.city_id IN user_subscribed_cities:
   notify user

6. Сценарії (дуже важливо)
🟢 Користувач вибрав нове місто

POST /user/cities

запис у user_city_subscriptions

enqueue job:

check_city_events(city_id)

якщо подій мало:

ставимо флаг needs_refresh

скрапер отримує задачу

🟢 Скрапер знайшов нові події

Ingest API зберігає/оновлює події

enqueue job:

notify_users(city_id)

користувачі отримують оновлення

7. Internal events (створені на платформі)

Вони:

проходять той самий pipeline

але:

source_type = INTERNAL
source_name = platform


Можна додати:

created_by_user_id

moderation_status

8. Моноліт vs мікросервіси (коротко)
Для диплома 💯

✅ Модульний моноліт

API

workers

auth

events

users

❌ мікросервіси — overkill

9. Резюме (коротко)

одна таблиця events

різниця тільки в source_type

скрапер → API → DB

background workers:

sync

notifications

city refresh

реакція на дії користувача (місто) через таски