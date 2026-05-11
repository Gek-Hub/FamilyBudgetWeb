import json
import re
import requests
from django.conf import settings
from django.utils import timezone

def _strip_json_text(text: str) -> str:
    text = text.strip()

    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()

    start = text.find("{")
    end = text.rfind("}")

    if start >= 0 and end >= 0:
        return text[start:end + 1]

    return text

def normalize_amount(value) -> str:
    """
    Приводит сумму к нормальному виду:
    2500 -> 2500
    2.500 -> 2500
    2,500 -> 2500
    2 500 -> 2500
    2500.50 -> 2500.50
    2500,50 -> 2500.50
    """
    text = str(value).strip().lower()
    text = text.replace("рублей", "").replace("рубля", "").replace("руб", "").replace("₽", "")
    text = text.replace(" ", "")

    # Оставляем только цифры, точку и запятую
    text = re.sub(r"[^0-9.,]", "", text)

    if not text:
        return "0"

    # Если есть и точка, и запятая, считаем последнюю разделителем копеек, остальные — тысячами
    if "." in text and "," in text:
        last_dot = text.rfind(".")
        last_comma = text.rfind(",")

        if last_dot > last_comma:
            decimal_sep = "."
            thousand_sep = ","
        else:
            decimal_sep = ","
            thousand_sep = "."

        text = text.replace(thousand_sep, "")
        text = text.replace(decimal_sep, ".")
        return text

    # Если есть только точка
    if "." in text and "," not in text:
        parts = text.split(".")

        # 2.500 или 12.000 — это тысячи
        if len(parts) == 2 and len(parts[1]) == 3:
            return parts[0] + parts[1]

        # 2.500.000 — это тысячи
        if len(parts) > 2:
            return "".join(parts)

        return text

    # Если есть только запятая
    if "," in text and "." not in text:
        parts = text.split(",")

        # 2,500 или 12,000 — это тысячи
        if len(parts) == 2 and len(parts[1]) == 3:
            return parts[0] + parts[1]

        # 2,500,000 — это тысячи
        if len(parts) > 2:
            return "".join(parts)

        # 2500,50 — это копейки
        return text.replace(",", ".")

    return text

def _find_category_in_text(command: str, category_names: list[str]) -> str | None:
    text = command.lower()

    # Сначала точное вхождение названия категории
    for name in category_names:
        if name.lower() in text:
            return name

    # Потом простые формы слов
    aliases = {
        "Еда": ["еда", "еду", "продукты", "кафе", "обед", "ужин"],
        "Транспорт": ["транспорт", "такси", "метро", "автобус", "проезд", "бензин"],
        "Коммунальные услуги": ["коммунальные", "коммуналка", "жкх", "квартплата"],
        "Развлечения": ["развлечения", "кино", "игры", "отдых"],
        "Здоровье": ["здоровье", "аптека", "лекарства", "врач"],
        "Одежда": ["одежда", "одежду", "кроссовки", "куртка"],
        "Спорт": ["спорт", "спорту", "тренировка", "зал", "фитнес", "баскетбол"],
        "Зарплата": ["зарплата", "аванс"],
        "Подработка": ["подработка", "фриланс"],
        "Подарки": ["подарок", "подарили"],
    }

    for real_name in category_names:
        words = aliases.get(real_name, [])
        if any(word in text for word in words):
            return real_name

    return None

def _local_fallback_parse(command: str, category_names=None, wallet_names=None, member_names=None) -> dict:
    category_names = category_names or []
    text = command.lower().strip()

    operation_type = "Доход" if any(word in text for word in ["доход", "зарплата", "получил", "поступление", "аванс"]) else "Расход"

    category = _find_category_in_text(command, category_names)

    if not category:
        category = "Зарплата" if operation_type == "Доход" and "Зарплата" in category_names else None

    if not category:
        category = "Еда" if "Еда" in category_names else (category_names[0] if category_names else "Еда")

    if category in ["Зарплата", "Подработка", "Подарки"]:
        operation_type = "Доход"

    numbers = re.findall(r"\d+(?:[.,\s]\d{3})*(?:[.,]\d{1,2})?|\d+", command)
    amount = normalize_amount(numbers[0]) if numbers else "0"

    date = "today"

    if "вчера" in text:
        date = str(timezone.now().date() - timezone.timedelta(days=1))
    elif "завтра" in text:
        date = str(timezone.now().date() + timezone.timedelta(days=1))

    return {
        "type": operation_type,
        "category": category,
        "amount": amount,
        "date": date,
        "comment": f"Добавлено через AI-команду: {command}",
    }

def parse_voice_command(command: str, category_names=None, wallet_names=None, member_names=None) -> dict:
    if not command or not command.strip():
        raise ValueError("Команда пустая.")

    category_names = category_names or []
    wallet_names = wallet_names or []
    member_names = member_names or []

    api_key = getattr(settings, "DEEPSEEK_API_KEY", "")

    # Если ключа нет, используем локальный разбор с учетом реальных категорий
    if not api_key:
        return _local_fallback_parse(command, category_names, wallet_names, member_names)

    categories_text = ", ".join(category_names) if category_names else "Еда, Транспорт, Коммунальные услуги"
    wallets_text = ", ".join(wallet_names) if wallet_names else "Карта RUB"
    members_text = ", ".join(member_names) if member_names else "текущий пользователь"

    system_prompt = f"""
Ты помощник приложения для учета семейного бюджета.
Преобразуй русскую команду пользователя в строгий JSON.

Очень важно:
- выбирай категорию ТОЛЬКО из списка доступных категорий;
- если пользователь сказал категорию, которая есть в списке, используй именно ее;
- если пользователь сказал Категория, а в списке есть "Категория", верни "Категория";
- если категория не найдена, выбери ближайшую по смыслу из списка;
- сумму "2.500" или "2,500" считай как 2500, если это похоже на разделение тысяч;
- верни только JSON без markdown и пояснений;

Доступные категории:
{categories_text}

Доступные счета:
{wallets_text}

Доступные члены семьи:
{members_text}

Формат:
{{
  "type": "Расход" или "Доход",
  "category": "одна категория из списка доступных категорий",
  "amount": число без пробелов и без разделителей тысяч,
  "date": "today" или дата в формате YYYY-MM-DD,
  "comment": "короткий комментарий"
}}

Правила:
- если тип не указан, это расход;
- если дата не указана или сказано "сегодня", используй "today";
- если сказано "зарплата", тип "Доход";
- сумма должна быть числом без валюты, например 2500, а не 2.500.
"""

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": command},
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }

    try:
        response = requests.post(
            getattr(settings, "DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )

        response.raise_for_status()

        content = response.json()["choices"][0]["message"]["content"]
        parsed = json.loads(_strip_json_text(content))

        # Дополнительная страховка: если в самой команде явно есть категория из базы,
        # то берем ее, даже если модель выбрала другое.
        explicit_category = _find_category_in_text(command, category_names)
        category = explicit_category or parsed.get("category", "")

        if category not in category_names and category_names:
            fallback_category = _find_category_in_text(category, category_names)
            category = fallback_category or category_names[0]

        return {
            "type": parsed.get("type", "Расход"),
            "category": category or "Еда",
            "amount": normalize_amount(parsed.get("amount", 0)),
            "date": parsed.get("date", "today"),
            "comment": parsed.get("comment", f"Добавлено через AI-команду: {command}"),
        }

    except Exception:
        return _local_fallback_parse(command, category_names, wallet_names, member_names)
