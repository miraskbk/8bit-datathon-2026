from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuleDefinition:
    code: str
    title: str
    prompt: str
    description: str
    document: str
    section: str
    url: str


RULES = (
    RuleDefinition(
        code="cash_handover",
        title="Передача наличных через открытую рабочую поверхность",
        prompt=(
            "a bank customer and cashier directly handing banknotes or a cash bag "
            "across an open desk"
        ),
        description=(
            "В кадре видна передача предметов, похожих на банкноты или сумку с "
            "ценностями, через открытую рабочую поверхность. Необходимо проверить "
            "оформление, пересчет и соблюдение установленного порядка операции."
        ),
        document=(
            "Правила осуществления кассовых операций, постановление Правления "
            "НБРК от 29.11.2019 № 231"
        ),
        section="Пункты 31 и 41: выдача, пересчет и проверка наличных денег",
        url="https://adilet.zan.kz/rus/docs/V1900019680",
    ),
    RuleDefinition(
        code="unattended_values",
        title="Ценности оставлены без контроля",
        prompt=(
            "an unattended bank cashier desk with cash, banknotes, documents, keys, "
            "stamps or valuables left exposed while the cashier is away"
        ),
        description=(
            "Кассир отсутствует у рабочего места, а на рабочей поверхности видны "
            "предметы, похожие на наличные деньги, документы, ключи или иные ценности. "
            "Это требует проверки соблюдения порядка хранения ценностей."
        ),
        document=(
            "Правила осуществления кассовых операций, постановление Правления "
            "НБРК от 29.11.2019 № 231"
        ),
        section="Пункт 80: внутренний порядок хранения ценностей и исключение несанкционированного использования",
        url="https://adilet.zan.kz/rus/docs/V1900019680",
    ),
    RuleDefinition(
        code="restricted_area_access",
        title="Возможный доступ постороннего в кассовую зону",
        prompt=(
            "an unauthorized customer or another person standing behind the cashier desk "
            "or inside the restricted bank cash handling area"
        ),
        description=(
            "В зоне за рабочим столом кассира находится другой человек. По видео нельзя "
            "подтвердить его полномочия, поэтому эпизод требует проверки режима доступа."
        ),
        document=(
            "Правила организации охраны и устройства помещений банков второго уровня, "
            "утвержденные постановлением Правления НБРК от 24.02.2020 № 14"
        ),
        section="Пункты 3 и 8: охрана помещений и изоляция кассового узла закрывающимся служебным входом",
        url="https://adilet.zan.kz/rus/docs/V2000020075",
    ),
    RuleDefinition(
        code="cash_exposed",
        title="Наличные или ценности находятся вне защищенного хранения",
        prompt=(
            "cash, banknotes, documents, keys or valuables exposed on a bank cashier desk "
            "outside a protected cash drawer or safe"
        ),
        description=(
            "На рабочей поверхности видны предметы, похожие на наличные деньги или "
            "ценности, находящиеся вне закрытого средства хранения. Эпизод требует "
            "проверки кассовой дисциплины."
        ),
        document=(
            "Правила осуществления кассовых операций и операций по инкассации, "
            "утвержденные постановлением Правления НБРК от 29.11.2019 № 231"
        ),
        section="Пункты 74 и 80: хранение наличных денег, ценностей, печатей и ключей",
        url="https://adilet.zan.kz/rus/docs/V1900019680",
    ),
    RuleDefinition(
        code="unlocked_workstation",
        title="Рабочее место оставлено без блокировки",
        prompt=(
            "an unattended bank cashier workstation with the computer screen left on "
            "and unlocked while the cashier is away"
        ),
        description=(
            "Рабочее место кассира оставлено без сотрудника, при этом экран компьютера "
            "остается активным. Это требует проверки блокировки рабочего места."
        ),
        document="Публичные правила организации кассовой работы QazaqPay Business",
        section="Раздел 8.4: управление доступом; блокировка компьютера при уходе с рабочего места",
        url="https://qazaqpay.kz/wp-content/uploads/2025/01/QazaqPay_Business_Rules_2025.pdf",
    ),
    RuleDefinition(
        code="food_or_drink",
        title="Еда или напиток на рабочем месте кассира",
        prompt=(
            "a bank cashier eating or drinking with food, a cup, or a bottle on the "
            "cash handling desk"
        ),
        description=(
            "На рабочей поверхности видна емкость с напитком или еда. Эпизод требует "
            "проверки локального порядка организации рабочего места кассира."
        ),
        document=(
            "Правила осуществления кассовых операций и операций по инкассации, "
            "утвержденные постановлением Правления НБРК от 29.11.2019 № 231"
        ),
        section="Пункт 80: порядок на рабочем месте определяется внутренними документами банка",
        url="https://adilet.zan.kz/rus/docs/V1900019680",
    ),
    RuleDefinition(
        code="personal_belongings",
        title="Личные вещи на рабочей поверхности",
        prompt="a personal handbag or other personal belongings placed on a bank cash handling desk",
        description=(
            "На рабочей поверхности видна личная сумка или другой предмет, не "
            "относящийся к кассовой операции. Эпизод требует проверки локального "
            "порядка организации рабочего места."
        ),
        document=(
            "Правила осуществления кассовых операций и операций по инкассации, "
            "утвержденные постановлением Правления НБРК от 29.11.2019 № 231"
        ),
        section="Пункт 80: порядок на рабочем месте определяется внутренними документами банка",
        url="https://adilet.zan.kz/rus/docs/V1900019680",
    ),
)
