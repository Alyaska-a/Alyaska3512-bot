# Locked Quantum Bot — V3 (Max Power, Owner-Only)
Приватный Telegram-бот c максимальными возможностями, защищён для одного владельца.

## Возможности
- 🔒 Безопасность: доступ только по `OWNER_ID`; двойная авторизация `/login <логин>` + `/pass <пароль>`; авторазлогин; смена логина/пароля командами.
- 🌐 Интернет: Google Custom Search → Bing → fallback DuckDuckGo + Wikipedia. Отдельные команды `/google`, `/bing`, `/wiki`, универсальный `/web`.
- ⚛️ Квантовые: Qiskit Aer (локально), IBM Quantum (по токену), AWS Braket (по AWS ключам). Пресеты и запуск OpenQASM 3.0. `/quantum devices` показывает доступные бэкенды.
- 🤖 LLM: OpenAI GPT-4o (по умолчанию) или Anthropic Claude 3.5 (переключаемо). Одноразовые ответы `/ask` и режим чата `/chat` + `/reset`.
- 🧩 Готов к деплою (Procfile, requirements, .env.example).

## Быстрый старт
1) Создай бота у @BotFather и получи `BOT_TOKEN`.
2) Узнай свой числовой `OWNER_ID` у @userinfobot.
3) На платформе деплоя (Railway/Render/Heroku) добавь переменные окружения из `.env.example`.
4) Запуск: `python main.py` (Procfile уже есть).

> **Важно:** никому не передавайте `BOT_TOKEN`, ключи API и пароли. Храните их только в переменных окружения.

## Команды
- `/start` — помощь.
- `/login <логин>` → `/pass <пароль>` — вход (двухшаговая).
- `/logout` — завершить сессию.
- `/changelogin <новый>` / `/changepass <новый>` — смена реквизитов (только при активной сессии).
- `/status` — состояние интеграций.
- `/ask <вопрос>` — запрос к LLM.
- `/chat <сообщение>` — диалог; `/reset` — очистить память.
- `/web <запрос>` — гибридный поиск.
- `/google <запрос>` — Google CSE (если настроен).
- `/bing <запрос>` — Bing (если настроен).
- `/wiki <термин>` — краткая справка из Википедии.
- `/quantum devices` — список доступных квантовых бэкендов.
- `/quantum preset <bell|ghz|qft> [qubits]` — пресеты.
- `/quantum run <openqasm 3.0>` — запуск QASM.

## Переменные окружения (.env.example)
См. файл `.env.example` — заполните **OWNER_ID** и секреты.
