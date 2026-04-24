"""Seed the system food catalog with category, brand, and alias coverage.

Idempotent: keyed by (name, brand). Existing rows are left untouched except
for category backfill (by keyword) and alias normalization — so this can be
run after the older scripts/seed_products.py on the same DB.

Covers the categories required for the "search product" UX:
  крупы, мясо, рыба, яйца, молочка, овощи, фрукты, хлеб,
  сладкое, снеки, напитки, готовая еда, соусы.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from bot.config import settings
from bot.models.base import create_db_engine, create_session_factory
from bot.models.product import Product, ProductAlias, ProductSource
from bot.repositories.product import normalize_product_text


class Row(NamedTuple):
    name: str
    category: str
    kcal: float
    protein: float
    fat: float
    carbs: float
    brand: str | None = None
    default_unit: str = "g"
    source: ProductSource = ProductSource.system
    is_verified: bool = True
    confidence: float = 1.0
    aliases: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Generic products — confidence 1.0, verified, source=system.
# BЖУ from standard Russian reference tables (per 100g or 100ml).
# ---------------------------------------------------------------------------
GRAINS: list[Row] = [
    Row("Гречка варёная", "крупы", 132, 4.5, 1.4, 25.8, aliases=("греча", "гречневая каша")),
    Row("Гречка сухая", "крупы", 343, 12.6, 3.3, 62.1, aliases=("гречневая крупа",)),
    Row("Рис белый варёный", "крупы", 116, 2.7, 0.3, 25.0, aliases=("рис отварной",)),
    Row("Рис бурый варёный", "крупы", 110, 2.6, 0.9, 22.8, aliases=("бурый рис",)),
    Row("Овсянка на воде", "крупы", 88, 3.0, 1.7, 15.0, aliases=("геркулес", "овсяная каша")),
    Row("Овсяные хлопья сухие", "крупы", 352, 12.3, 6.2, 61.8, aliases=("овсянка сухая", "хлопья овсяные")),
    Row("Макароны варёные", "крупы", 112, 3.5, 0.4, 23.2, aliases=("паста варёная", "макароны")),
    Row("Макароны из твёрдых сортов сухие", "крупы", 344, 12.0, 1.4, 71.5, aliases=("спагетти сухие",)),
    Row("Булгур сухой", "крупы", 342, 12.3, 1.3, 75.9),
    Row("Киноа сухая", "крупы", 368, 14.1, 6.1, 57.2, aliases=("quinoa",)),
    Row("Перловка варёная", "крупы", 121, 3.1, 0.4, 24.9),
    Row("Пшено варёное", "крупы", 118, 3.0, 0.7, 24.5, aliases=("пшённая каша",)),
    Row("Манка варёная на воде", "крупы", 80, 2.5, 0.2, 16.8, aliases=("манная каша",)),
    Row("Картофельное пюре на молоке", "крупы", 88, 2.1, 2.8, 13.7, aliases=("пюре",)),
]

MEAT_FISH_EGGS: list[Row] = [
    Row("Куриная грудка отварная", "мясо", 137, 29.8, 1.8, 0.5, aliases=("куриная грудка", "курогрудка", "курогрудь", "куриное филе варёное")),
    Row("Куриная грудка жареная", "мясо", 164, 30.0, 4.8, 0.5),
    Row("Куриное филе сырое", "мясо", 113, 23.6, 1.9, 0.4, aliases=("куриное филе",)),
    Row("Куриное бедро без кожи", "мясо", 185, 21.3, 11.0, 0.0, aliases=("куриные бёдра",)),
    Row("Куриные крылья", "мясо", 210, 18.3, 15.0, 0.0),
    Row("Говядина тушёная", "мясо", 232, 16.8, 18.3, 0.0, aliases=("тушёная говядина",)),
    Row("Говядина варёная", "мясо", 254, 25.8, 16.8, 0.0),
    Row("Свинина жареная", "мясо", 489, 11.4, 49.3, 0.0),
    Row("Свинина тушёная", "мясо", 235, 22.6, 16.1, 0.0),
    Row("Фарш говяжий", "мясо", 254, 17.2, 20.0, 0.0, aliases=("говяжий фарш",)),
    Row("Фарш куриный", "мясо", 143, 17.4, 8.1, 0.0, aliases=("куриный фарш",)),
    Row("Индейка грудка", "мясо", 114, 23.5, 1.5, 0.0, aliases=("индюшка грудка",)),
    Row("Индейка бедро", "мясо", 210, 18.0, 14.0, 0.0),
    Row("Ветчина варёная", "мясо", 278, 22.6, 20.9, 0.0),
    Row("Бекон", "мясо", 500, 23.0, 45.0, 0.0, aliases=("грудинка копчёная",)),
    Row("Лосось запечённый", "рыба", 208, 22.1, 13.4, 0.0, aliases=("сёмга запечённая",)),
    Row("Лосось сырой", "рыба", 142, 19.8, 6.3, 0.0, aliases=("лосось свежий", "сёмга сырая")),
    Row("Тунец консервированный в собственном соку", "рыба", 96, 21.5, 0.7, 0.0, aliases=("тунец консервы",)),
    Row("Минтай отварной", "рыба", 79, 17.6, 1.0, 0.0),
    Row("Треска отварная", "рыба", 78, 17.8, 0.7, 0.0),
    Row("Сельдь солёная", "рыба", 217, 17.0, 16.5, 0.0, aliases=("селёдка",)),
    Row("Скумбрия копчёная", "рыба", 221, 20.7, 15.5, 0.0),
    Row("Куриное яйцо варёное", "яйца", 155, 12.7, 10.6, 0.7, aliases=("яйцо варёное", "варёное яйцо")),
    Row("Куриное яйцо сырое", "яйца", 157, 12.7, 10.9, 0.7, aliases=("яйцо сырое",)),
    Row("Яичница из 1 яйца", "яйца", 196, 13.9, 15.3, 0.9, aliases=("яичница",)),
    Row("Омлет с молоком", "яйца", 184, 10.4, 15.0, 1.9, aliases=("омлет",)),
    Row("Перепелиное яйцо", "яйца", 168, 11.9, 13.1, 0.6),
]

DAIRY: list[Row] = [
    Row("Молоко 1.5%", "молочка", 44, 2.8, 1.5, 4.7, default_unit="ml", aliases=("молоко 1,5%",)),
    Row("Молоко 2.5%", "молочка", 52, 2.8, 2.5, 4.7, default_unit="ml", aliases=("молоко 2,5%",)),
    Row("Молоко 3.2%", "молочка", 59, 2.9, 3.2, 4.7, default_unit="ml", aliases=("молоко 3,2%",)),
    Row("Кефир 1%", "молочка", 40, 2.8, 1.0, 4.0, default_unit="ml"),
    Row("Кефир 2.5%", "молочка", 53, 2.9, 2.5, 4.0, default_unit="ml", aliases=("кефир 2,5%",)),
    Row("Ряженка 2.5%", "молочка", 54, 2.9, 2.5, 4.2, default_unit="ml"),
    Row("Йогурт натуральный 2%", "молочка", 60, 4.3, 2.0, 6.2, aliases=("йогурт натуральный",)),
    Row("Йогурт греческий 2%", "молочка", 66, 9.0, 2.0, 3.6, aliases=("греческий йогурт",)),
    Row("Сметана 15%", "молочка", 158, 2.6, 15.0, 3.0),
    Row("Сметана 20%", "молочка", 206, 2.8, 20.0, 3.2),
    Row("Творог 0%", "молочка", 71, 16.5, 0.1, 1.3, aliases=("творог обезжиренный",)),
    Row("Творог 5%", "молочка", 121, 17.2, 5.0, 1.8, aliases=("творог 5",)),
    Row("Творог 9%", "молочка", 159, 16.7, 9.0, 2.0, aliases=("творог 9",)),
    Row("Сыр твёрдый (ассорти)", "молочка", 356, 24.1, 29.5, 0.3, aliases=("сыр российский", "сыр голландский")),
    Row("Сыр Моцарелла", "молочка", 280, 22.2, 22.3, 2.2, aliases=("mozzarella",)),
    Row("Сыр Фета", "молочка", 264, 17.0, 24.0, 0.0, aliases=("feta",)),
    Row("Сыр плавленый", "молочка", 226, 16.5, 14.3, 8.4, aliases=("плавленый сыр",)),
    Row("Масло сливочное 72.5%", "молочка", 661, 0.8, 72.5, 1.3, aliases=("масло сливочное",)),
    Row("Сливки 10%", "молочка", 118, 3.0, 10.0, 4.0, default_unit="ml"),
    Row("Сливки 20%", "молочка", 205, 2.8, 20.0, 3.7, default_unit="ml"),
]

VEG_FRUIT: list[Row] = [
    Row("Огурец свежий", "овощи", 15, 0.8, 0.1, 2.8, aliases=("огурец",)),
    Row("Помидор свежий", "овощи", 20, 1.1, 0.2, 3.7, aliases=("помидор", "томат")),
    Row("Перец болгарский", "овощи", 27, 1.3, 0.1, 5.3, aliases=("перец сладкий", "болгарский перец")),
    Row("Капуста белокочанная", "овощи", 28, 1.8, 0.1, 4.7, aliases=("капуста",)),
    Row("Капуста пекинская", "овощи", 16, 1.2, 0.2, 2.0, aliases=("пекинская капуста",)),
    Row("Морковь сырая", "овощи", 35, 1.3, 0.1, 6.9, aliases=("морковь",)),
    Row("Картофель отварной", "овощи", 82, 2.0, 0.4, 16.7, aliases=("картошка отварная",)),
    Row("Картофель жареный", "овощи", 192, 2.8, 9.5, 23.4, aliases=("жареная картошка",)),
    Row("Лук репчатый", "овощи", 41, 1.4, 0.0, 8.2, aliases=("лук",)),
    Row("Чеснок", "овощи", 143, 6.5, 0.5, 29.9),
    Row("Свёкла варёная", "овощи", 49, 1.8, 0.0, 10.8, aliases=("свекла варёная",)),
    Row("Брокколи", "овощи", 28, 3.0, 0.4, 5.2),
    Row("Цветная капуста", "овощи", 30, 2.5, 0.3, 4.2),
    Row("Кабачок", "овощи", 24, 0.6, 0.3, 4.6),
    Row("Баклажан", "овощи", 24, 1.2, 0.1, 4.5),
    Row("Салат листовой", "овощи", 12, 1.5, 0.2, 1.3, aliases=("листовой салат", "руккола")),
    Row("Тыква", "овощи", 22, 1.0, 0.1, 4.4),
    Row("Кукуруза консервированная", "овощи", 58, 2.2, 0.4, 11.2),
    Row("Зелёный горошек консервированный", "овощи", 55, 3.6, 0.1, 9.8, aliases=("зелёный горошек",)),
    Row("Банан", "фрукты", 89, 1.1, 0.3, 22.8),
    Row("Яблоко", "фрукты", 52, 0.4, 0.4, 9.8),
    Row("Груша", "фрукты", 47, 0.4, 0.3, 10.3),
    Row("Апельсин", "фрукты", 36, 0.9, 0.2, 8.1),
    Row("Мандарин", "фрукты", 38, 0.8, 0.2, 7.5),
    Row("Виноград", "фрукты", 65, 0.6, 0.2, 16.8),
    Row("Клубника", "фрукты", 41, 0.8, 0.4, 7.5, aliases=("земляника",)),
    Row("Малина", "фрукты", 46, 0.8, 0.5, 8.3),
    Row("Черника", "фрукты", 44, 1.1, 0.4, 7.6),
    Row("Арбуз", "фрукты", 25, 0.6, 0.1, 5.8),
    Row("Дыня", "фрукты", 33, 0.6, 0.3, 7.4),
    Row("Ананас", "фрукты", 49, 0.4, 0.2, 10.6),
    Row("Хурма", "фрукты", 66, 0.5, 0.4, 15.3),
    Row("Киви", "фрукты", 47, 0.8, 0.4, 8.1),
    Row("Персик", "фрукты", 45, 0.9, 0.1, 9.5),
    Row("Слива", "фрукты", 42, 0.8, 0.3, 9.6),
    Row("Авокадо", "фрукты", 160, 2.0, 14.7, 1.8),
    Row("Лимон", "фрукты", 16, 0.9, 0.1, 3.0),
]

BREAD: list[Row] = [
    Row("Хлеб белый", "хлеб", 242, 7.6, 2.5, 48.4, aliases=("белый хлеб", "пшеничный хлеб")),
    Row("Хлеб чёрный", "хлеб", 215, 6.6, 1.2, 41.8, aliases=("чёрный хлеб", "ржаной хлеб")),
    Row("Бородинский хлеб", "хлеб", 208, 6.8, 1.3, 40.7),
    Row("Батон нарезной", "хлеб", 262, 7.5, 2.9, 50.9, aliases=("батон",)),
    Row("Лаваш тонкий", "хлеб", 236, 7.7, 1.2, 47.6, aliases=("лаваш",)),
    Row("Багет", "хлеб", 274, 8.5, 2.8, 55.6),
    Row("Булочка сдобная", "хлеб", 339, 7.5, 10.5, 53.3, aliases=("сдобная булка",)),
    Row("Сухари панировочные", "хлеб", 395, 10.8, 2.8, 77.0),
    Row("Блин", "хлеб", 186, 6.1, 3.0, 34.3, aliases=("блины",)),
]

SWEETS: list[Row] = [
    Row("Сахар", "сладкое", 398, 0.0, 0.0, 99.7),
    Row("Мёд", "сладкое", 329, 0.8, 0.0, 80.3),
    Row("Шоколад горький 70%", "сладкое", 539, 6.2, 35.4, 48.2, aliases=("тёмный шоколад",)),
    Row("Шоколад молочный", "сладкое", 554, 6.9, 35.7, 54.4),
    Row("Шоколад Alpen Gold молочный", "сладкое", 534, 6.0, 30.0, 58.0, brand="Alpen Gold",
        source=ProductSource.openfoodfacts, is_verified=False, confidence=0.75,
        aliases=("alpen gold", "альпен голд", "альпенгольд")),
    Row("Варенье (ассорти)", "сладкое", 271, 0.4, 0.2, 70.0, aliases=("варенье",)),
    Row("Мороженое пломбир", "сладкое", 227, 3.2, 15.0, 20.8, aliases=("пломбир",)),
    Row("Печенье овсяное", "сладкое", 437, 6.5, 14.4, 71.4),
    Row("Печенье Юбилейное", "сладкое", 450, 6.5, 16.2, 68.0, brand="Юбилейное",
        source=ProductSource.openfoodfacts, is_verified=False, confidence=0.7,
        aliases=("юбилейное",)),
    Row("Зефир", "сладкое", 304, 0.8, 0.1, 74.0),
    Row("Пастила", "сладкое", 310, 0.5, 0.2, 76.0),
    Row("Халва подсолнечная", "сладкое", 522, 11.6, 29.7, 54.0, aliases=("халва",)),
    Row("Сгущённое молоко", "сладкое", 320, 7.2, 8.5, 56.0, aliases=("сгущёнка",)),
    Row("Пряник тульский", "сладкое", 340, 5.2, 2.8, 75.0, aliases=("пряник",)),
]

SNACKS: list[Row] = [
    Row("Чипсы Lay's Сметана и зелень", "снеки", 530, 6.0, 32.0, 53.0, brand="Lay's",
        source=ProductSource.label, is_verified=False, confidence=0.8,
        aliases=("lays", "лейс", "лэйс", "lay's")),
    Row("Чипсы Lay's Паприка", "снеки", 530, 6.0, 32.0, 53.0, brand="Lay's",
        source=ProductSource.label, is_verified=False, confidence=0.8,
        aliases=("lays паприка", "лейс паприка")),
    Row("Чипсы Pringles Original", "снеки", 536, 4.0, 32.0, 53.0, brand="Pringles",
        source=ProductSource.label, is_verified=False, confidence=0.8,
        aliases=("pringles", "принглс")),
    Row("Сухарики ржаные", "снеки", 366, 16.0, 1.0, 70.0, aliases=("сухарики",)),
    Row("Арахис жареный", "снеки", 611, 26.3, 49.9, 16.0, aliases=("арахис",)),
    Row("Миндаль", "снеки", 645, 18.6, 57.7, 16.2),
    Row("Кешью", "снеки", 600, 25.7, 54.1, 13.2),
    Row("Грецкий орех", "снеки", 654, 16.2, 60.8, 11.1, aliases=("грецкие орехи",)),
    Row("Фундук", "снеки", 651, 15.0, 61.5, 9.4),
    Row("Семечки подсолнечника", "снеки", 601, 20.7, 52.9, 10.5, aliases=("семечки",)),
    Row("Изюм", "снеки", 264, 2.9, 0.6, 66.0),
    Row("Курага", "снеки", 215, 5.2, 0.3, 51.0),
    Row("Финики", "снеки", 274, 2.5, 0.5, 69.2),
]

DRINKS: list[Row] = [
    Row("Вода питьевая", "напитки", 0, 0, 0, 0, default_unit="ml", aliases=("вода",)),
    Row("Coca-Cola", "напитки", 42, 0, 0, 10.6, default_unit="ml", brand="Coca-Cola",
        source=ProductSource.label, is_verified=False, confidence=0.9,
        aliases=("coca cola", "coca-cola", "cola", "кока кола", "кока-кола", "кола", "coke")),
    Row("Coca-Cola Zero", "напитки", 0.3, 0, 0, 0, default_unit="ml", brand="Coca-Cola",
        source=ProductSource.label, is_verified=False, confidence=0.9,
        aliases=("coca cola zero", "кола зеро", "кока зеро")),
    Row("Pepsi", "напитки", 43, 0, 0, 10.8, default_unit="ml", brand="Pepsi",
        source=ProductSource.label, is_verified=False, confidence=0.85,
        aliases=("pepsi", "пепси")),
    Row("Добрый Cola", "напитки", 42, 0, 0, 10.6, default_unit="ml", brand="Добрый",
        source=ProductSource.label, is_verified=False, confidence=0.8,
        aliases=("добрый кола", "добрый cola", "добрый")),
    Row("Sprite", "напитки", 39, 0, 0, 9.5, default_unit="ml", brand="Sprite",
        source=ProductSource.label, is_verified=False, confidence=0.85,
        aliases=("спрайт", "sprite")),
    Row("Fanta Апельсин", "напитки", 48, 0, 0, 11.8, default_unit="ml", brand="Fanta",
        source=ProductSource.label, is_verified=False, confidence=0.85,
        aliases=("fanta", "фанта")),
    Row("Сок яблочный", "напитки", 46, 0.5, 0.1, 11.3, default_unit="ml", aliases=("яблочный сок",)),
    Row("Сок апельсиновый", "напитки", 45, 0.7, 0.2, 10.4, default_unit="ml", aliases=("апельсиновый сок",)),
    Row("Сок мультифрукт", "напитки", 50, 0.5, 0.1, 12.0, default_unit="ml", aliases=("мультифрукт",)),
    Row("Морс клюквенный", "напитки", 41, 0.1, 0, 10.2, default_unit="ml", aliases=("морс",)),
    Row("Компот из сухофруктов", "напитки", 60, 0.3, 0, 14.3, default_unit="ml", aliases=("компот",)),
    Row("Чай чёрный без сахара", "напитки", 0, 0, 0, 0, default_unit="ml", aliases=("чай", "чёрный чай")),
    Row("Чай зелёный без сахара", "напитки", 0, 0, 0, 0, default_unit="ml", aliases=("зелёный чай",)),
    Row("Кофе чёрный без сахара", "напитки", 2, 0.1, 0, 0.3, default_unit="ml", aliases=("кофе",)),
    Row("Капучино", "напитки", 56, 3.1, 2.8, 4.7, default_unit="ml"),
    Row("Латте", "напитки", 72, 3.8, 3.7, 5.9, default_unit="ml"),
    Row("Пиво светлое 4.5%", "напитки", 42, 0.3, 0, 4.6, default_unit="ml", aliases=("пиво",)),
    Row("Вино красное сухое", "напитки", 68, 0.2, 0, 0.3, default_unit="ml", aliases=("вино красное",)),
]

READY_MEALS: list[Row] = [
    Row("Пельмени варёные", "готовая", 248, 11.9, 12.4, 24.0, aliases=("пельмени",)),
    Row("Вареники с творогом", "готовая", 170, 7.0, 3.9, 27.0, aliases=("вареники",)),
    Row("Сосиски молочные", "готовая", 266, 11.0, 23.9, 1.6, aliases=("сосиски",)),
    Row("Колбаса докторская", "готовая", 257, 12.8, 22.2, 1.5, aliases=("докторская колбаса", "колбаса варёная")),
    Row("Колбаса сырокопчёная", "готовая", 473, 24.8, 41.5, 0.3, aliases=("сырокопчёная колбаса",)),
    Row("Котлета куриная", "готовая", 210, 16.5, 13.0, 8.0, aliases=("куриная котлета",)),
    Row("Котлета говяжья", "готовая", 260, 14.5, 18.0, 10.0, aliases=("говяжья котлета",)),
    Row("Наггетсы куриные", "готовая", 270, 13.0, 16.0, 17.0, aliases=("наггетсы", "нагетсы")),
    Row("Пицца Маргарита замороженная", "готовая", 240, 9.0, 8.5, 30.0, aliases=("пицца маргарита", "пицца")),
    Row("Плов с курицей", "готовая", 195, 8.5, 8.2, 21.0, aliases=("плов",)),
    Row("Борщ", "готовая", 49, 1.5, 2.2, 5.4),
    Row("Щи", "готовая", 39, 1.3, 1.4, 4.5),
    Row("Окрошка", "готовая", 52, 2.5, 2.1, 5.9),
    Row("Блины с мясом", "готовая", 220, 9.0, 11.0, 22.0),
    Row("Сырники со сметаной", "готовая", 260, 13.0, 15.0, 20.0, aliases=("сырники",)),
    Row("Роллы Филадельфия", "готовая", 190, 9.0, 6.0, 25.0, aliases=("филадельфия",)),
]

SAUCES: list[Row] = [
    Row("Майонез Провансаль 67%", "соусы", 624, 0.3, 67.0, 2.6, aliases=("майонез", "провансаль")),
    Row("Майонез лёгкий 30%", "соусы", 300, 0.5, 30.0, 4.0, aliases=("лёгкий майонез",)),
    Row("Кетчуп томатный", "соусы", 93, 1.6, 0.2, 22.2, aliases=("кетчуп",)),
    Row("Кетчуп Heinz Томатный", "соусы", 102, 1.2, 0.2, 23.3, brand="Heinz",
        source=ProductSource.label, is_verified=False, confidence=0.85,
        aliases=("heinz", "хайнц")),
    Row("Горчица столовая", "соусы", 143, 9.9, 5.3, 12.7, aliases=("горчица",)),
    Row("Соевый соус", "соусы", 53, 6.0, 0.1, 6.7, default_unit="ml", aliases=("соевый",)),
    Row("Томатная паста", "соусы", 92, 4.8, 0.5, 19.0),
    Row("Уксус столовый 9%", "соусы", 11, 0, 0, 2.9, default_unit="ml", aliases=("уксус",)),
    Row("Подсолнечное масло", "соусы", 899, 0, 99.9, 0, default_unit="ml", aliases=("растительное масло", "подсолнечное")),
    Row("Оливковое масло", "соусы", 898, 0, 99.8, 0, default_unit="ml", aliases=("оливковое",)),
    Row("Сливочный соус", "соусы", 170, 2.0, 15.0, 7.0),
    Row("Песто", "соусы", 419, 4.5, 41.6, 5.2),
]


ALL_ROWS: list[Row] = (
    GRAINS + MEAT_FISH_EGGS + DAIRY + VEG_FRUIT + BREAD
    + SWEETS + SNACKS + DRINKS + READY_MEALS + SAUCES
)


# Category keyword map for backfilling existing unclassified rows.
CATEGORY_KEYWORDS: list[tuple[str, str]] = [
    ("кур", "мясо"), ("говяд", "мясо"), ("свин", "мясо"), ("индей", "мясо"),
    ("ветчин", "мясо"), ("бекон", "мясо"), ("фарш", "мясо"), ("котлет", "готовая"),
    ("лосос", "рыба"), ("сёмг", "рыба"), ("тунец", "рыба"), ("минтай", "рыба"),
    ("треск", "рыба"), ("сельд", "рыба"), ("скумбри", "рыба"),
    ("яйц", "яйца"), ("омлет", "яйца"), ("яичниц", "яйца"),
    ("молок", "молочка"), ("кефир", "молочка"), ("ряженк", "молочка"),
    ("йогурт", "молочка"), ("сметан", "молочка"), ("творог", "молочка"),
    ("сыр", "молочка"), ("сливк", "молочка"), ("масло сливочн", "молочка"),
    ("гречк", "крупы"), ("рис", "крупы"), ("овсян", "крупы"),
    ("макарон", "крупы"), ("булгур", "крупы"), ("кино", "крупы"),
    ("перловк", "крупы"), ("пшён", "крупы"), ("манк", "крупы"),
    ("огурец", "овощи"), ("помидор", "овощи"), ("перец", "овощи"),
    ("капуст", "овощи"), ("морков", "овощи"), ("картоф", "овощи"),
    ("свёкл", "овощи"), ("брокколи", "овощи"), ("кабачок", "овощи"),
    ("баклажан", "овощи"), ("лук", "овощи"), ("чеснок", "овощи"),
    ("банан", "фрукты"), ("яблок", "фрукты"), ("груш", "фрукты"),
    ("апельс", "фрукты"), ("мандарин", "фрукты"), ("виноград", "фрукты"),
    ("клубник", "фрукты"), ("малин", "фрукты"), ("арбуз", "фрукты"),
    ("дын", "фрукты"), ("хурм", "фрукты"), ("киви", "фрукты"),
    ("хлеб", "хлеб"), ("батон", "хлеб"), ("лаваш", "хлеб"), ("булк", "хлеб"),
    ("шоколад", "сладкое"), ("мёд", "сладкое"), ("сахар", "сладкое"),
    ("мороженое", "сладкое"), ("печенье", "сладкое"), ("зефир", "сладкое"),
    ("халва", "сладкое"), ("варенье", "сладкое"),
    ("чипс", "снеки"), ("орех", "снеки"), ("арахис", "снеки"),
    ("миндал", "снеки"), ("семечк", "снеки"), ("изюм", "снеки"),
    ("cola", "напитки"), ("кола", "напитки"), ("pepsi", "напитки"),
    ("fanta", "напитки"), ("sprite", "напитки"), ("сок ", "напитки"),
    ("чай", "напитки"), ("кофе", "напитки"), ("морс", "напитки"),
    ("компот", "напитки"), ("пиво", "напитки"), ("вин", "напитки"),
    ("пельмен", "готовая"), ("вареник", "готовая"), ("сосиск", "готовая"),
    ("колбас", "готовая"), ("наггетс", "готовая"), ("пицц", "готовая"),
    ("майонез", "соусы"), ("кетчуп", "соусы"), ("горчиц", "соусы"),
    ("соевый", "соусы"), ("уксус", "соусы"), ("оливков", "соусы"),
    ("подсолнечн", "соусы"),
]


def _guess_category(name: str) -> str | None:
    lowered = name.lower().replace("ё", "е")
    for keyword, cat in CATEGORY_KEYWORDS:
        if keyword.lower().replace("ё", "е") in lowered:
            return cat
    return None


async def _upsert_products(session) -> tuple[int, int]:
    """Insert new rows (name+brand unique), skip existing. Returns (inserted, skipped)."""
    existing_rows = (
        await session.execute(
            select(Product).where(Product.user_id.is_(None))
        )
    ).scalars().all()
    existing_keys = {
        (normalize_product_text(p.name), normalize_product_text(p.brand or ""))
        for p in existing_rows
    }

    inserted = 0
    skipped = 0
    for row in ALL_ROWS:
        key = (
            normalize_product_text(row.name),
            normalize_product_text(row.brand or ""),
        )
        if key in existing_keys:
            skipped += 1
            continue
        product = Product(
            name=row.name,
            brand=row.brand,
            category=row.category,
            default_unit=row.default_unit,
            calories_per_100g=row.kcal,
            protein_per_100g=row.protein,
            fat_per_100g=row.fat,
            carbs_per_100g=row.carbs,
            source=row.source,
            is_verified=row.is_verified,
            confidence=row.confidence,
            user_id=None,
        )
        session.add(product)
        await session.flush()
        for alias in row.aliases:
            session.add(
                ProductAlias(
                    product_id=product.id,
                    alias=alias,
                    normalized_alias=normalize_product_text(alias),
                )
            )
        existing_keys.add(key)
        inserted += 1

    return inserted, skipped


async def _backfill_categories(session) -> int:
    """Populate category for existing system rows where still NULL."""
    rows = (
        await session.execute(
            select(Product).where(
                Product.user_id.is_(None), Product.category.is_(None)
            )
        )
    ).scalars().all()
    changed = 0
    for p in rows:
        cat = _guess_category(p.name)
        if cat:
            p.category = cat
            changed += 1
    return changed


async def _backfill_normalized_aliases(session) -> int:
    """Populate normalized_alias for rows where it's blank."""
    rows = (
        await session.execute(
            select(ProductAlias).where(ProductAlias.normalized_alias == "")
        )
    ).scalars().all()
    for a in rows:
        a.normalized_alias = normalize_product_text(a.alias)
    return len(rows)


async def seed() -> None:
    engine = create_db_engine(settings.database_url)

    if "sqlite" in settings.database_url:
        from bot.models import Base  # noqa: F401
        from bot.models.base import create_tables

        await create_tables(engine)

    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        inserted, skipped = await _upsert_products(session)
        cat_updates = await _backfill_categories(session)
        alias_updates = await _backfill_normalized_aliases(session)
        await session.commit()

    await engine.dispose()

    print(
        f"Food catalog seed: +{inserted} products, skipped {skipped} existing, "
        f"backfilled category on {cat_updates} rows, "
        f"normalized_alias on {alias_updates} aliases."
    )


if __name__ == "__main__":
    asyncio.run(seed())
