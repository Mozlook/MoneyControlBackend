# MoneyControl – Backlog (MVP)

## Overview

Aplikacja finansowa do śledzenia wydatków:

- Frontend: React + Vite + Tailwind + React Query.
- Backend: Python + FastAPI + SQLAlchemy + Alembic.
- Baza: PostgreSQL (Docker).
- Auth: logowanie tylko przez Google OAuth, backend wystawia własne JWT.
- Funkcje: wiele portfeli na użytkownika, współdzielenie portfela, kategorie/produkty, transakcje, stałe koszty, prosty dashboard, eksport.

---

## Aktualny stan backendu

### Zrobione

- Repo backendu z FastAPI (`app/main.py`).
- Dockerowy Postgres w docker-compose.
- Konfiguracja aplikacji (`config.py`) + `.env`.
- SQLAlchemy + `SessionLocal` + `get_db`.
- Modele ORM dla:
  - `User`, `UserSettings`, `UserOauth`
  - `Wallet`, `WalletUser`
  - `Category`, `Product`
  - `Transaction`, `RecurringTransaction`
- Alembic:
  - skonfigurowany `alembic/env.py` z `Base.metadata`,
  - wygenerowana initial migracja,
  - migracje odpalone na bazie.
- Auth:
  - moduł `auth/jwt.py` (JWT: `create_access_token`, `decode_access_token`, `InvalidTokenError`),
  - moduł `auth/google.py` (weryfikacja `id_token`, `InvalidGoogleTokenError`),
  - Pydantic schematy:
    - `GoogleAuthRequest`, `TokenResponse`,
    - `UserRead`,
  - `get_current_user` w `deps.py` (Annotated + OAuth2PasswordBearer),
  - router `/auth/google` tworzący / wyszukujący usera + zwracający JWT,
  - router `/users/me` zwracający aktualnie zalogowanego usera.
- `main.py`:
  - wpięte routery `auth` i `users`,
  - endpointy `/health` i `/db-check`,
  - możliwość odpalania serwera przez Uvicorn (wpięty `uvicorn.run` w `if __name__ == "__main__"`).

---

## E0 – Setup i fundamenty projektu

- [x] **E0.1** – Repo backendu + venv + skeleton FastAPI
- [x] **E0.2** – Docker + Postgres (kontener `finapp-db`)
- [x] **E0.3** – `config.py` + `.env` (DATABASE_URL, JWT_SECRET, GOOGLE_CLIENT_ID)
- [x] **E0.4** – `database.py` + SQLAlchemy engine + SessionLocal + `get_db`
- [x] **E0.5** – Endpointy `/health` i `/db-check`

---

## E1 – Model danych & migracje

- [x] **E1.1** – Zaprojektowanie schematu tabel:
  - `users`, `user_settings`, `user_oauth`
  - `wallets`, `wallet_users`
  - `categories`, `products`
  - `transactions`, `recurring_transactions`
- [x] **E1.2** – Implementacja modeli SQLAlchemy (`models.py`)
- [x] **E1.3** – Konfiguracja Alembica (`alembic init`, `env.py` z `Base.metadata`)
- [x] **E1.4** – `alembic revision --autogenerate -m "initial schema"`
- [x] **E1.5** – `alembic upgrade head` – migracje odpalone na bazie

---

## E2 – Autoryzacja: Google OAuth + JWT

- [x] **E2.1** – Moduł `auth/jwt.py`:
  - `create_access_token(user_id: UUID) -> str`
  - `decode_access_token(token: str) -> UUID`
  - wyjątek `InvalidTokenError`
- [x] **E2.2** – Moduł `auth/google.py`:
  - `verify_google_id_token(token: str) -> dict[str, object]`
  - wyjątek `InvalidGoogleTokenError`
- [x] **E2.3** – Schematy w `schemas/auth.py`:
  - `GoogleAuthRequest`
  - `TokenResponse`
- [x] **E2.4** – Schemat w `schemas/user.py`:
  - `UserRead` (id, email, display_name, created_at, `model_config = ConfigDict(from_attributes=True)`)
- [x] **E2.5** – Dependency `get_current_user` w `deps.py`:
  - używa `OAuth2PasswordBearer` i `decode_access_token`
  - ładuje `User` z DB
  - rzuca `HTTPException(401)` przy błędnym tokenie / braku usera
- [x] **E2.6** – Router `routers/auth.py`:
  - `POST /auth/google`
    - przyjmuje `GoogleAuthRequest`
    - weryfikuje `id_token` (`verify_google_id_token`)
    - znajduje lub tworzy:
      - `User`
      - `UserOauth` (provider="google", provider_sub=sub)
      - `UserSettings` (domyślne: `language="pl"`, `currency="PLN"`, `billing_day=1`, `timezone="Europe/Warsaw"`)
    - generuje JWT (`create_access_token`)
    - zwraca `TokenResponse`
- [x] **E2.7** – Router `routers/users.py`:
  - `GET /users/me`
  - zależny od `get_current_user`
  - zwraca `UserRead`
- [x] **E2.8** – Wpięcie routerów w `app/main.py`:
  - `app.include_router(auth.router)`
  - `app.include_router(users.router)`
- [x] **E2.9** – Uproszczone odpalanie backendu:
  - blok `if __name__ == "__main__": uvicorn.run("app.main:app", ...)`

---

## E3 – Portfele (wallets) & współdzielenie

**Następny duży blok do zrobienia.**

- [ ] **E3.1** – Schematy Pydantic:
  - `WalletCreate` (name, currency opcjonalnie)
  - `WalletRead` (id, name, currency, created_at, role użytkownika)
- [ ] **E3.2** – `POST /wallets`
  - tworzy portfel
  - `owner_id = current_user.id`
  - domyślna waluta portfela = user currency (UserSettings) albo podana w body
  - dodaje rekord `WalletUser` z rolą `owner`
- [ ] **E3.3** – `GET /wallets`
  - lista portfeli, w których user jest członkiem (`wallet_users.user_id = current_user.id`)
- [ ] **E3.4** – `GET /wallets/{wallet_id}`
  - szczegóły jednego portfela (tylko jeśli user jest członkiem)
- [ ] **E3.5** – `POST /wallets/{wallet_id}/members`
  - dodanie usera po emailu / user_id
  - tworzy `WalletUser` z rolą `"editor"`
  - tylko owner może dodać członka
- [ ] **E3.6** – `GET /wallets/{wallet_id}/members`
  - lista członków portfela (rola, email, display_name)
- [ ] **E3.7** – Helpery:
  - `ensure_wallet_member(wallet_id, current_user)`
  - `ensure_wallet_owner(wallet_id, current_user)`

---

## E4 – Kategorie i produkty

- [ ] **E4.1** – Schematy:
  - `CategoryCreate`, `CategoryRead`
  - `ProductCreate`, `ProductRead`
- [ ] **E4.2** – `POST /wallets/{wallet_id}/categories`
  - tworzy kategorię (unikalna `name` w ramach portfela)
- [ ] **E4.3** – `GET /wallets/{wallet_id}/categories`
  - lista kategorii bez soft-deleted (lub z opcją flagi)
- [ ] **E4.4** – `POST /wallets/{wallet_id}/products`
  - tworzy produkt/podkategorię (name, category_id, importance)
- [ ] **E4.5** – `GET /wallets/{wallet_id}/products`
  - lista produktów z kategoriami
- [ ] **E4.6** – Soft-delete:
  - `DELETE /categories/{id}` → ustawia `deleted_at`
  - `DELETE /products/{id}`:
    - ustawia `deleted_at`
    - aktualizuje transakcje tak, by `product_id` mogło być `NULL`

---

## E5 – Transakcje (wydatki)

- [ ] **E5.1** – Schematy:
  - `TransactionCreate`
  - `TransactionRead`
- [ ] **E5.2** – `POST /wallets/{wallet_id}/transactions`
  - dodaje wydatek:
    - `amount_base`, `currency_base` (waluta portfela)
    - opcjonalnie `amount_original`, `currency_original`, `fx_rate`
    - `category_id`, opcjonalnie `product_id`
    - `occurred_at` (data z klienta)
    - `user_id = current_user.id`
- [ ] **E5.3** – `GET /wallets/{wallet_id}/transactions`
  - filtrowanie po:
    - zakresie dat,
    - obecnym okresie rozliczeniowym,
    - kategorii / produkcie
- [ ] **E5.4** – Refund:
  - `POST /transactions/{id}/refund`
  - tworzy nową transakcję:
    - kwota ujemna,
    - `refund_of_transaction_id` = id oryginalnej transakcji
- [ ] **E5.5** – Soft delete transakcji:
  - `DELETE /transactions/{id}` ustawia `deleted_at`

---

## E6 – Stałe koszty (`recurring_transactions`)

- [ ] **E6.1** – Schematy:
  - `RecurringTransactionCreate`
  - `RecurringTransactionRead`
- [ ] **E6.2** – `POST /wallets/{wallet_id}/recurring`
  - dodanie stałego kosztu (np. rata)
- [ ] **E6.3** – `GET /wallets/{wallet_id}/recurring`
  - lista stałych kosztów w portfelu
- [ ] **E6.4** – Mechanizm „apply recurring”:
  - MVP: endpoint `POST /wallets/{wallet_id}/recurring/apply`
  - generuje transakcje na podstawie `recurring_transactions`
- [ ] **E6.5** – Aktualizacja / deaktywacja:
  - `PUT /recurring/{id}`
  - `DELETE /recurring/{id}` / zmiana `active=False`

---

## E7 – Ustawienia użytkownika

- [ ] **E7.1** – `GET /users/me/settings`
  - odczyt `UserSettings`
- [ ] **E7.2** – `PUT /users/me/settings`
  - zmiana:
    - `language`
    - `currency`
    - `billing_day`
    - `timezone`

---

## E8 – Dashboard / agregacje (MVP)

- [ ] **E8.1** – `GET /wallets/{wallet_id}/summary/current-period`
  - suma wydatków w bieżącym okresie rozliczeniowym
  - sumy po kategoriach
- [ ] **E8.2** – `GET /wallets/{wallet_id}/history`
  - prosta historia:
    - per okres (miesiąc rozliczeniowy) → suma wydatków

---

## E9 – Export

- [ ] **E9.1** – `GET /wallets/{wallet_id}/transactions/export?format=csv`
  - eksport transakcji z zakresu dat do CSV

---

## E10 – Frontend (MVP)

- [ ] **F0.1** – Setup frontend:
  - Vite + React + TypeScript
  - Tailwind CSS
  - React Query
- [ ] **F1.1** – Integracja z Google Identity na froncie:
  - pobranie `id_token`
  - wysłanie do `POST /auth/google`
- [ ] **F1.2** – Trzymanie `access_token` (localStorage / cookie)
- [ ] **F1.3** – Wyświetlanie danych z `GET /users/me`
- [ ] **F2** – UI do portfeli:
  - lista portfeli
  - przełączanie portfela
- [ ] **F3** – UI do kategorii/produktów i transakcji (MVP):
  - lista transakcji w bieżącym okresie
  - formularz dodawania wydatku

---

## E11 – Testy backendu

- [ ] **T1** – Setup pytest:
  - testowa baza (np. in-memory / osobny Postgres)
  - fixture z `Session` per test
- [ ] **T2** – Testy auth:
  - `decode_access_token`
  - `/auth/google` (mock Google)
  - `get_current_user`
- [ ] **T3** – Testy wallets:
  - tworzenie portfela
  - dostęp tylko dla członków

---

## E12 – Deploy (późniejszy etap)

- [ ] **D1** – Dockerfile backendu
- [ ] **D2** – docker-compose dla prod (backend + db + reverse proxy)
- [ ] **D3** – Reverse proxy (nginx/traefik) + HTTPS
- [ ] **D4** – Deploy backendu na VPS / chmurę
- [ ] **D5** – Frontend na Netlify / innym hostingu statycznym
- [ ] **D6** – Strategia migracji DB w deployu (alembic upgrade)
