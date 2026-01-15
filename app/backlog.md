# MoneyControl – Backlog (MVP)

## Overview

Aplikacja finansowa do śledzenia wydatków:

- Frontend: React + Vite + Tailwind + React Query.
- Backend: Python + FastAPI + SQLAlchemy + Alembic.
- Baza: PostgreSQL (Docker).
- Auth: logowanie tylko przez Google OAuth, backend wystawia własne JWT.
- Funkcje: wiele portfeli na użytkownika, współdzielenie portfela, kategorie/produkty, transakcje, stałe koszty, dashboard (agregacje), eksport.

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
- Wallets + współdzielenie:
  - router `/wallets` (create/list/get),
  - routery `/wallets/{wallet_id}/members` (add/list),
  - helpery `ensure_wallet_member`, `ensure_wallet_owner`.
- Kategorie / produkty:
  - routery `/wallets/{wallet_id}/categories`, `/wallets/{wallet_id}/products`,
  - soft-delete + hard-delete.
- Transakcje:
  - router `/wallets/{wallet_id}/transactions` (create/list/refund/soft-delete),
  - FX (opcjonalny zestaw pól) + refundy.
- Stałe koszty:
  - router `/wallets/{wallet_id}/recurring` (create/list/update/deactivate),
  - endpoint `/wallets/{wallet_id}/recurring/apply` (generuje transakcje raz na okres rozliczeniowy).
- Ustawienia:
  - `/users/me/settings` GET/PUT.

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
- [x] **E2.8** – Wpięcie routerów w `app/main.py`
- [x] **E2.9** – Uproszczone odpalanie backendu (`uvicorn.run`)

---

## E3 – Portfele (wallets) & współdzielenie

- [x] **E3.1** – Schematy Pydantic:
  - `WalletCreate` (name, currency opcjonalnie)
  - `WalletRead` (id, name, currency, created_at, role użytkownika)
- [x] **E3.2** – `POST /wallets`
  - tworzy portfel
  - `owner_id = current_user.id`
  - domyślna waluta portfela = user currency (UserSettings) albo podana w body
  - dodaje rekord `WalletUser` z rolą `owner`
- [x] **E3.3** – `GET /wallets`
  - lista portfeli, w których user jest członkiem
- [x] **E3.4** – `GET /wallets/{wallet_id}`
  - szczegóły jednego portfela (tylko jeśli user jest członkiem)
- [x] **E3.5** – `POST /wallets/{wallet_id}/members`
  - dodanie usera po emailu / user_id
  - tworzy `WalletUser` z rolą `"editor"`
  - tylko owner może dodać członka
- [x] **E3.6** – `GET /wallets/{wallet_id}/members`
  - lista członków portfela (rola, email, display_name)
- [x] **E3.7** – Helpery:
  - `ensure_wallet_member(wallet_id, current_user)`
  - `ensure_wallet_owner(wallet_id, current_user)`

---

## E4 – Kategorie i produkty

- [x] **E4.1** – Schematy:
  - `CategoryCreate`, `CategoryRead`
  - `ProductCreate`, `ProductRead`
- [x] **E4.2** – `POST /wallets/{wallet_id}/categories`
  - tworzy kategorię (unikalna `name` w ramach portfela)
- [x] **E4.3** – `GET /wallets/{wallet_id}/categories`
  - lista kategorii bez soft-deleted (MVP)
- [x] **E4.4** – `POST /wallets/{wallet_id}/products`
  - tworzy produkt (name, category_id, importance)
- [x] **E4.5** – `GET /wallets/{wallet_id}/products`
  - lista produktów (opcjonalnie `?category_id=...`)
- [x] **E4.6** – Soft-delete:
  - `DELETE /wallets/{wallet_id}/categories/{category_id}` → ustawia `deleted_at`
  - `DELETE /wallets/{wallet_id}/products/{product_id}`:
    - ustawia `deleted_at`
    - aktualizuje transakcje i recurring tak, by `product_id` mogło być `NULL`
- [x] **E4.7** – Hard-delete (sprzątanie, tylko gdy brak referencji):
  - `DELETE /wallets/{wallet_id}/categories/{category_id}/hard`
    - wymaga wcześniejszego soft-delete
    - blokuje, jeśli istnieją powiązane `transactions`/`recurring_transactions`
  - `DELETE /wallets/{wallet_id}/products/{product_id}/hard`
    - wymaga wcześniejszego soft-delete
    - blokuje, jeśli istnieją powiązane `transactions`/`recurring_transactions`

---

## E5 – Transakcje (wydatki)

- [x] **E5.1** – Schematy:
  - `TransactionCreate`
  - `TransactionRead` (+ `ProductInTransactionRead`)
- [x] **E5.2** – `POST /wallets/{wallet_id}/transactions`
  - dodaje wydatek:
    - `amount_base`, `currency_base` (waluta portfela)
    - opcjonalnie `amount_original`, `currency_original`, `fx_rate` (walidacja: 0 albo 3 pola)
    - `category_id`, opcjonalnie `product_id`
    - `occurred_at` (data z klienta)
    - `user_id = current_user.id`
- [x] **E5.3** – `GET /wallets/{wallet_id}/transactions`
  - filtrowanie po:
    - zakresie dat (`from_date`, `to_date`)
    - obecnym okresie rozliczeniowym (`current_period=true`)
    - kategorii / produkcie
- [x] **E5.4** – Refund:
  - `POST /wallets/{wallet_id}/transactions/{transaction_id}/refund`
  - tworzy nową transakcję:
    - kwota ujemna,
    - `refund_of_transaction_id` = id oryginalnej transakcji
    - blokuje refund refundu / blokuje drugi refund
- [x] **E5.5** – Soft delete transakcji:
  - `DELETE /wallets/{wallet_id}/transactions/{transaction_id}`:
    - ustawia `deleted_at`
    - blokuje, jeśli transakcja ma refundy

---

## E6 – Stałe koszty (`recurring_transactions`)

- [x] **E6.1** – Schematy:
  - `RecurringTransactionCreate`
  - `RecurringTransactionRead`
- [x] **E6.2** – `POST /wallets/{wallet_id}/recurring`
  - dodanie stałego kosztu (np. rata)
- [x] **E6.3** – `GET /wallets/{wallet_id}/recurring`
  - lista stałych kosztów w portfelu (opcjonalnie `?active=true/false`)
- [x] **E6.4** – Mechanizm „apply recurring”:
  - `POST /wallets/{wallet_id}/recurring/apply`
  - generuje transakcje na podstawie `recurring_transactions`:
    - tylko aktywne
    - tylko te, które nie były zastosowane w bieżącym okresie rozliczeniowym (`last_applied_at < period_start`)
    - aktualizuje `last_applied_at` i `updated_at`
- [x] **E6.5** – Aktualizacja / deaktywacja:
  - `PUT /wallets/{wallet_id}/recurring/{recurring_id}` (update pól, bez zmiany `active`)
  - `DELETE /wallets/{wallet_id}/recurring/{recurring_id}` (ustawia `active=False`)

---

## E7 – Ustawienia użytkownika

- [x] **E7.1** – `GET /users/me/settings`
  - odczyt `UserSettings`
- [x] **E7.2** – `PUT /users/me/settings`
  - zmiana (partial update):
    - `language` (len=2, lower, strip)
    - `currency` (len=3, upper, strip)
    - `billing_day` (1..28)
    - `timezone` (walidacja IANA przez ZoneInfo)

---

## E8 – Dashboard / agregacje (MVP – rozszerzone)

> Wspólny standard okresu (dla endpointów summary):
>
> - `current_period=true` (domyślnie) → okres rozliczeniowy z `billing_day` + `timezone`
> - `current_period=false` + `from_date`/`to_date` → zakres ręczny

- [x] **E8.1** – Kategorie + produkty + sumy w okresie
  - `GET /wallets/{wallet_id}/summary/categories-products`
  - zwraca:
    - listę kategorii (pola kategorii)
    - `category_sum` (SUM amount_base w okresie)
    - `no_product_sum` (SUM dla `product_id=NULL`)
    - listę produktów w kategorii:
      - pola produktu
      - `product_sum` (SUM amount_base w okresie dla produktu)
  - query params:
    - `current_period: bool = True`
    - `from_date: date | None`
    - `to_date: date | None`
    - (opcjonalnie) `include_empty: bool = False`
- [x] **E8.2** – Wydatki wg ważności produktu
  - `GET /wallets/{wallet_id}/summary/by-importance`
  - grupuje transakcje w okresie po `Product.importance` i sumuje `amount_base`
  - zwraca obiekt typu:
    - `{ necessary: X, important: Y, unnecessary: Z, unassigned: U }`
  - query params:
    - `current_period: bool = True`
    - `from_date: date | None`
    - `to_date: date | None`
- [x] **E8.3** – Historia wydatków za ostatnie N okresów rozliczeniowych
  - `GET /wallets/{wallet_id}/history/last-periods?periods=6`
  - zwraca listę:
    - `{ period_start, period_end, total }`
  - `periods` domyślnie 6

---

## E9 – Export

- [x] **E9.1** – `GET /wallets/{wallet_id}/transactions/export?format=csv`
  - eksport transakcji z zakresu dat do CSV

---

## E10 – Frontend (MVP) – rozbudowane sprinty

### Architektura (konwencje projektu)

- Metody w modułach API: `getAll`, `getById`, `create`, `update`, `delete` (+ akcje domenowe: `refund`, `apply`, `exportCsv`).
- Endpointy trzymamy w **`apiPaths`** (single source of truth).
- `ApiClient` (Axios) jako klasa + `ApiError`, interceptory, token z storage.
- Routing: `/app/w/:walletId/...` (deep-linking).
- Server-state: React Query; minimalny client-state (token, last wallet).

---

### Sprint FE-01 — Setup + fundamenty (DX, config, API skeleton)

**Cel sprintu:** uruchomienie projektu front, przygotowanie infrastruktury (config, apiPaths, ApiClient, layout, routing).

- [x] **FE-01.1** – Init projektu
  - Vite + React + TypeScript
  - Tailwind CSS
  - React Router
  - React Query
- [x] **FE-01.2** – Standardy repo (DX)
  - ESLint + Prettier
  - aliasy importów (np. `@/`)
  - konwencje: nazwy plików, struktura folderów
- [x] **FE-01.3** – ENV/config (dev/prod)
  - `.env.development` / `.env.production`
  - `settings` wybierane na podstawie env (`VITE_ENVIRONMENT` lub `MODE`)
  - `API_BASE_URL`, `API_PREFIX`, `TIMEOUT_MS`, `LOG_LEVEL`, `AUTH_TOKEN_KEY`
  - (opcjonalnie) Vite proxy w dev
- [x] **FE-01.4** – `apiPaths` (single source of truth)
  - `auth`, `users`, `wallets`, `categories`, `products`, `transactions`, `recurring`, `summary`, `history`
  - ścieżki dynamiczne jako funkcje (np. `wallet(walletId)`, `refund(walletId, transactionId)`)
- [x] **FE-01.5** – `ApiError` + `ApiClient` (Axios)
  - interceptors: token w request + mapowanie błędów
  - standard zwracania `.data` w helperach (`get/post/put/patch/delete/download`)
  - globalne zachowanie dla `401` (logout event)
- [x] **FE-01.6** – Skeleton modułów API
  - `authApi`, `usersApi`, `walletsApi`, `walletMembersApi`, `categoriesApi`, `productsApi`, `transactionsApi`, `recurringApi`, `summaryApi`, `historyApi`
  - konwencja metod: `getAll`, `getById`, `create`, `update`, `delete`, `download`, akcje domenowe
- [x] **FE-01.7** – UI baza (minimalny kit)
  - Button, Input, Select, Modal, Spinner, EmptyState, Toast/Notifications
- [x] **FE-01.8** – Routing skeleton (puste strony)
  - `/login`
  - `/app/wallets`
  - `/app/w/:walletId/dashboard`
  - `/app/w/:walletId/transactions`
  - `/app/w/:walletId/catalog`
  - `/app/w/:walletId/recurring`
  - `/app/w/:walletId/members`
  - `/app/settings`
- [x] **FE-01.9** – Layout skeleton
  - `AppLayout` (shell: sidebar/topbar + outlet)
  - placeholder nav

**DoD (FE-01):** projekt się buduje i odpala, routing działa, istnieje `apiPaths` + `ApiClient` + podstawowy layout.

---

### Sprint FE-02 — Auth + sesja + ochrona routingu

**Cel sprintu:** działające logowanie przez Google + sesja + ochrona ekranów.

- [x] **FE-02.1** – `/login` – integracja z Google Identity
  - pobranie `id_token`
  - call `authApi.loginWithGoogle(id_token)` → JWT
- [x] **FE-02.2** – Token storage
  - zapis/odczyt/clear `access_token` w localStorage (`AUTH_TOKEN_KEY`)
- [x] **FE-02.3** – `ProtectedRoute`
  - blokuje `/app/*` bez tokena
  - redirect do `/login`
- [x] **FE-02.4** – Pobranie usera
  - `usersApi.getMe()` (React Query)
  - pokaz w topbar (display_name/email)
- [x] **FE-02.5** – Obsługa 401
  - event z `ApiClient` → logout + redirect + toast
- [x] **FE-02.6** – Logout w UI

**DoD (FE-02):** login działa end-to-end, bez tokena nie wejdziesz do app, a 401 kończy sesję.

---

### Sprint FE-03 — Portfele: lista, tworzenie, przełączanie, wallet layout

**Cel sprintu:** użytkownik zarządza portfelami i porusza się w kontekście `walletId`.

- [x] **FE-03.1** – `/app/wallets` – lista portfeli
  - `walletsApi.getAll()`
- [x] **FE-03.2** – Tworzenie portfela
  - `walletsApi.create()`
- [x] **FE-03.3** – Wallet switcher w layout
  - zapamiętywanie “last wallet” (localStorage)
- [x] **FE-03.4** – `WalletLayout` dla `/app/w/:walletId/*`
  - ładuje `walletsApi.getById(walletId)`
  - pokazuje nazwę/walutę, role badge
- [x] **FE-03.5** – Obsługa błędów dostępu do walleta
  - 403/404 → komunikat + link do listy portfeli

**DoD (FE-03):** użytkownik ma płynny wybór portfela, URL z `walletId` jest źródłem prawdy.

---

### Sprint FE-04 — Members (współdzielenie portfela)

**Cel sprintu:** owner zarządza członkami portfela.

- [x] **FE-04.1** – Lista członków
  - `walletMembersApi.getAll(walletId)`
- [x] **FE-04.2** – Dodanie członka (owner-only)
  - `walletMembersApi.create(walletId, data)` (email/user_id)
- [x] **FE-04.3** – Role-based UI
  - editor nie widzi akcji admina
- [x] **FE-04.4** – UX: empty state + sensowne błędy

**DoD (FE-04):** owner dodaje usera do portfela, widoczność akcji zależna od roli.

---

### Sprint FE-05 — Katalog: kategorie + produkty (CRUD MVP)

**Cel sprintu:** utrzymanie katalogu pod transakcje i recurring.

- [x] **FE-05.1** – Kategorie: lista + create
  - `categoriesApi.getAll(walletId)`
  - `categoriesApi.create(walletId, ...)`
- [x] **FE-05.2** – Produkty: lista + create
  - `productsApi.getAll(walletId, { category_id? })`
  - `productsApi.create(walletId, ...)` (importance)
- [x] **FE-05.3** – Soft delete
  - `categoriesApi.delete(walletId, categoryId)`
  - `productsApi.delete(walletId, productId)`
- [x] **FE-05.4** – (Opcjonalnie MVP+) Hard delete flow
  - `categoriesApi.hardDelete(...)`, `productsApi.hardDelete(...)`
  - UX: tylko gdy spełnia warunki (soft-delete wcześniej + brak referencji)
- [x] **FE-05.5** – Formularze + walidacje
  - podstawowa walidacja pól
  - komunikaty z API (unikalność name)

**DoD (FE-05):** katalog działa w pełnym MVP (co najmniej create + list + soft-delete).

---

### Sprint FE-06 — Transakcje (core MVP) + refund + export CSV

**Cel sprintu:** pełna obsługa transakcji w bieżącym okresie + filtry + refund + export.

- [x] **FE-06.1** – Lista transakcji
  - `transactionsApi.getAll(walletId, filters)`
  - domyślnie: `current_period=true`
- [x] **FE-06.2** – Filtry
  - date range
  - category/product
  - przełącznik “current period” vs zakres ręczny
- [ ] **FE-06.3** – Dodanie transakcji (formularz)
  - amount_base + occurred_at + category/product
  - tryb FX (opcjonalny): amount_original + currency_original + fx_rate
- [ ] **FE-06.4** – Refund
  - `transactionsApi.refund(walletId, transactionId)`
- [ ] **FE-06.5** – Soft delete
  - `transactionsApi.delete(walletId, transactionId)`
- [ ] **FE-06.6** – Export CSV
  - `transactionsApi.exportCsv(walletId, filters)` (download Blob)
  - poprawna nazwa pliku
- [ ] **FE-06.7** – UX
  - loading states, empty states, toasty
  - invalidacje query po mutacjach

**DoD (FE-06):** użytkownik prowadzi wydatki i potrafi eksportować historię.

---

### Sprint FE-07 — Stałe koszty (recurring) + Apply

**Cel sprintu:** pełna obsługa recurring i generowanie transakcji na okres.

- [ ] **FE-07.1** – Lista recurring
  - `recurringApi.getAll(walletId, { active? })`
- [ ] **FE-07.2** – Dodanie recurring
  - `recurringApi.create(walletId, ...)`
- [ ] **FE-07.3** – Edycja recurring
  - `recurringApi.update(walletId, recurringId, ...)`
- [ ] **FE-07.4** – Deaktywacja
  - `recurringApi.delete(walletId, recurringId)` (active=false)
- [ ] **FE-07.5** – Apply recurring
  - `recurringApi.apply(walletId)`
  - UX: confirm modal + komunikat sukcesu
- [ ] **FE-07.6** – Spójność danych
  - invalidacje: transactions + summary + history

**DoD (FE-07):** recurring działa end-to-end, a apply wpływa na listy i dashboard.

---

### Sprint FE-08 — Dashboard + Ustawienia użytkownika + final polish (MVP domknięcie)

**Cel sprintu:** dashboard i settings oraz dopięcie jakości i spójności UX.

#### Dashboard

- [ ] **FE-08.1** – By-importance
  - `summaryApi.byImportance(walletId, range)`
- [ ] **FE-08.2** – Categories-products
  - `summaryApi.categoriesProducts(walletId, range)`
  - widok drzewka: kategorie → produkty, sumy + no-product
- [ ] **FE-08.3** – Historia N okresów
  - `historyApi.lastPeriods(walletId, periods)`
  - MVP: tabela (opcjonalnie wykres jako upgrade)

#### Ustawienia usera

- [ ] **FE-08.4** – `/app/settings` – settings read + update
  - `usersApi.getSettings()`
  - `usersApi.updateSettings()`
- [ ] **FE-08.5** – Reakcja na zmianę settings
  - odświeżenie danych zależnych od billing day/timezone

#### Polish

- [ ] **FE-08.6** – Spójne komunikaty błędów (ApiError → UI)
- [ ] **FE-08.7** – Skeletony i empty states na wszystkich ekranach
- [ ] **FE-08.8** – Role-based UI (owner/editor) wszędzie gdzie potrzeba
- [ ] **FE-08.9** – Responsywność
- [ ] **FE-08.10** – README (runbook)
  - uruchomienie dev
  - konfiguracja env
  - opis architektury API (`apiPaths`, `ApiClient`, moduły)

**DoD (FE-08):** dashboard i settings działają, MVP gotowe do release.

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
