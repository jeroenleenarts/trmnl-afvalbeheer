"""
Waste collectors ported from Home Assistant Afvalbeheer.

https://github.com/pippyn/Home-Assistant-Sensor-Afvalbeheer
"""
import json
import re
from datetime import date, datetime, timedelta, timezone
from http.cookiejar import CookieJar
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import HTTPCookieProcessor, Request, build_opener
from uuid import uuid4
from zoneinfo import ZoneInfo

USER_AGENT = "afvalbeheer-trmnl/0.3"
AFVALWIJZER_KEY = "5ef443e778f41c4f75c69459eea6e6ae0c2d92de729aa0fc61653815fbd6a8ca"
BURGERPORTAAL_KEY = "AIzaSyA6NkRqJypTfP-cjWzrZNFJzPUbBaGjOdk"
BURGERPORTAAL_IDS = {
    "assen": "138204213565303512",
    "bar": "138204213564933497",
    "groningen": "452048812597326549",
    "nijkerk": "138204213565304094",
    "rmn": "138204213564933597",
    "tilburg": "452048812597339353",
}

XIMMIO_IDS = {
    "acv": "f8e2844a-095e-48f9-9f98-71fceb51d2c3",
    "almere": "53d8db94-7945-42fd-9742-9bbc71dbe4c1",
    "areareiniging": "adc418da-d19b-11e5-ab30-625662870761",
    "avalex": "f7a74ad1-fdbf-4a43-9f91-44644f4d4222",
    "avri": "78cd4156-394b-413d-8936-d407e334559a",
    "blink": "252d30d0-2e74-469c-8f1e-c0e2e434eb58",
    "hellendoorn": "24434f5b-7244-412b-9306-3a2bd1e22bc1",
    "meerlanden": "800bf8d7-6dd1-4490-ba9d-b419d6dc8a45",
    "oostzaan": "6eb81e8f-ca5a-4bad-af0a-667650325511",
    "rad": "13a2cad9-36d0-4b01-b877-efcb421a864d",
    "twentemilieu": "8d97bb56-5afd-4cbc-a651-b4f7314264b4",
    "venlo": "280affe9-1428-443b-895a-b90431b8ca31",
    "waardlanden": "942abcf6-3775-400d-ae5d-7380d728b23c",
    "westland": "6fc75608-126a-4a50-9241-a002ce8c8a6c",
    "woerden": "06856f74-6826-4c6a-aabf-69bc9d20b5a6",
    "ximmio": "800bf8d7-6dd1-4490-ba9d-b419d6dc8a45",
}
XIMMIO_PROD2 = {
    "avalex", "blink", "meerlanden", "oostzaan", "rad", "westland", "woerden",
}

OPZET_URLS = {
    "alphenaandenrijn": "https://afvalkalender.alphenaandenrijn.nl",
    "afval3xbeter": "https://afval3xbeter.nl",
    "afvalstoffendienstkalender": "https://afvalstoffendienst.nl",
    "berkelland": "https://afvalkalender.gemeenteberkelland.nl",
    "cranendonck": "https://afvalkalender.cranendonck.nl",
    "cyclus": "https://cyclusnv.nl",
    "dar": "https://afvalkalender.dar.nl",
    "defryskemarren": "https://afvalkalender.defryskemarren.nl",
    "denhaag": "https://huisvuilkalender.denhaag.nl",
    "gad": "https://inzamelkalender.gad.nl",
    "hvc": "https://inzamelkalender.hvcgroep.nl",
    "lingewaard": "https://afvalwijzer.lingewaard.nl",
    "middelburg-vlissingen": "https://afvalwijzer.middelburgvlissingen.nl",
    "mijnafvalzaken": "https://mijnafvalzaken.nl",
    "montfoort": "https://cyclusnv.nl",
    "offalkalinder": "https://www.offalkalinder.nl",
    "peelenmaas": "https://afvalkalender.peelenmaas.nl",
    "prezero": "https://inzamelwijzer.prezero.nl",
    "purmerend": "https://afvalkalender.purmerend.nl",
    "rwm": "https://rwm.nl",
    "saver": "https://saver.nl",
    "schouwen-duiveland": "https://afvalkalender.schouwen-duiveland.nl",
    "sliedrecht": "https://afvalkalender.sliedrecht.nl",
    "spaarnelanden": "https://afvalwijzer.spaarnelanden.nl",
    "sudwestfryslan": "https://afvalkalender.sudwestfryslan.nl",
    "uithoorn": "https://cyclusnv.nl",
    "venray": "https://afvalkalender.venray.nl",
    "voorschoten": "https://afvalkalender.voorschoten.nl",
    "waalre": "https://afvalkalender.waalre.nl",
    "zrd": "https://www.zrd.nl",
}

COLLECTOR_NAMES = {
    "acv": "ACV",
    "afval3xbeter": "Afval3xBeter",
    "afvalstoffendienstkalender": "Afvalstoffendienstkalender",
    "almere": "Almere",
    "alphenaandenrijn": "AlphenAanDenRijn",
    "areareiniging": "AreaReiniging",
    "assen": "Assen",
    "avalex": "Avalex",
    "amsterdam": "Amsterdam",
    "avri": "Avri",
    "bar": "BAR",
    "berkelland": "Berkelland",
    "blink": "Blink",
    "circulus": "Circulus",
    "cranendonck": "Cranendonck",
    "cyclus": "Cyclus",
    "dar": "DAR",
    "deafvalapp": "DeAfvalApp",
    "defryskemarren": "DeFryskeMarren",
    "denhaag": "DenHaag",
    "gad": "GAD",
    "groningen": "Groningen",
    "hellendoorn": "Hellendoorn",
    "hvc": "HVC",
    "limburg.net": "Limburg.NET",
    "lingewaard": "Lingewaard",
    "meerlanden": "Meerlanden",
    "middelburg-vlissingen": "Middelburg-Vlissingen",
    "mijnafvalwijzer": "MijnAfvalwijzer",
    "mijnafvalzaken": "Mijnafvalzaken",
    "montfoort": "Montfoort",
    "nijkerk": "Nijkerk",
    "omrin": "Omrin",
    "offalkalinder": "Offalkalinder",
    "oostzaan": "Oostzaan",
    "peelenmaas": "PeelEnMaas",
    "prezero": "PreZero",
    "purmerend": "Purmerend",
    "rad": "RAD",
    "recycleapp": "RecycleApp",
    "rmn": "RMN",
    "rova": "ROVA",
    "rwm": "RWM",
    "saver": "Saver",
    "schouwen-duiveland": "Schouwen-Duiveland",
    "sliedrecht": "Sliedrecht",
    "spaarnelanden": "Spaarnelanden",
    "sudwestfryslan": "SudwestFryslan",
    "tilburg": "Tilburg",
    "twentemilieu": "TwenteMilieu",
    "uithoorn": "Uithoorn",
    "venlo": "Venlo",
    "venray": "Venray",
    "voorschoten": "Voorschoten",
    "waalre": "Waalre",
    "waardlanden": "Waardlanden",
    "westland": "Westland",
    "woerden": "Woerden",
    "ximmio": "Ximmio",
    "zrd": "ZRD",
}

ALIASES = {
    "cure": "mijnafvalwijzer",
    "meppel": "mijnafvalwijzer",
    "area": "areareiniging",
    "circulusberkel": "circulus",
    "alkmaar": "hvc",
    "suez": "prezero",
    "limburgnet": "limburg.net",
    "ophaalkalender": "recycleapp",
    "recycle": "recycleapp",
}

WASTE_TYPE_MAPPING = {
    "bestafr": "Bestafval",
    "branches": "Takken",
    "bulklitter": "Grofvuil",
    "bulkygardenwaste": "Tuinafval",
    "bulkyrestwaste": "PMD-Restafval",
    "chemisch": "Chemisch",
    "dhm": "Papier-PMD",
    "papier-pmd": "Papier-PMD",
    "droco": "Papier",
    "duobak": "Duobak",
    "etensresten": "GFT",
    "ga": "Grofvuil",
    "gemengde": "Plastic",
    "gft": "GFT",
    "groenafval": "Tuinafval",
    "grof": "Grofvuil",
    "groot huisvuil": "Grofvuil",
    "huisvuil": "Restafval",
    "gkbp": "PMD",
    "glas": "Glas",
    "glass": "Glas",
    "green": "GFT",
    "greengrey": "Duobak",
    "grey": "Restafval",
    "groene container": "GFT",
    "groente": "GFT",
    "grofvuil": "Grofvuil",
    "grijze container": "Restafval",
    "kca": "Chemisch",
    "kcalocatie": "Chemisch-brengen",
    "kerst": "Kerstbomen",
    "kerstb": "Kerstbomen",
    "kerstboom": "Kerstbomen",
    "kerstbomen": "Kerstbomen",
    "keukenafval": "GFT",
    "md": "PMD",
    "omb": "Restafval",
    "opk": "Papier",
    "packages": "PMD",
    "pmdrest": "PMD-Restafval",
    "pap": "Papier",
    "paper": "Papier",
    "papier": "Papier",
    "pbd": "PMD",
    "pbp": "PMD",
    "pd": "PMD",
    "plastic": "PMD",
    "pmd": "PMD",
    "remainder": "Restwagen",
    "rest": "Restafval",
    "restafval": "Restafval",
    "restafvalzakken": "Restafvalzakken",
    "restgft": "Duobak",
    "sloop": "Grofvuil",
    "snoeiafval": "Takken",
    "snoeihout": "Takken",
    "sorti": "Sortibak",
    "sortibak": "Sortibak",
    "takken": "Takken",
    "tuin- en snoeiafval": "Tuinafval",
    "zachte plastics": "Zacht plastic",
    "roze zak": "Zacht plastic",
    "ordures ménagères": "Restafval",
    "déchets résiduels": "Restafval",
    "déchets ménagers résiduels": "Restafval",
    "déchets organiques": "GFT",
    "tariefzak restafval": "Restafvalzakken",
    "textile": "Textiel",
    "textiel": "Textiel",
    "tree": "Kerstbomen",
    "tuinafval": "Tuinafval",
    "zak_blauw": "Restafval",
    "zwakra": "PMD",
}

WEEKDAYS = (
    "Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag",
)
MONTHS = (
    "januari", "februari", "maart", "april", "mei", "juni",
    "juli", "augustus", "september", "oktober", "november", "december",
)


def _collapse(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def _lookup() -> dict[str, str]:
    table = dict(ALIASES)
    for key, name in COLLECTOR_NAMES.items():
        table[_collapse(key)] = key
        table[_collapse(name)] = key
    return table


COLLECTOR_LOOKUP = _lookup()


def normalize_collector(value: str) -> str:
    return COLLECTOR_LOOKUP.get(_collapse(value), "")


def collector_name(key: str) -> str:
    return COLLECTOR_NAMES.get(key, key.title() if key else "Afvalbeheer")


def _nested(data: Any, *keys: str, default: Any = None) -> Any:
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return default if current is None else current


def field(payload: dict[str, Any], key: str, default: str = "") -> str:
    values = _nested(payload, "trmnl", "plugin_settings", "custom_fields_values", default={})
    if isinstance(values, dict) and values.get(key) not in (None, ""):
        return str(values[key]).strip()
    if payload.get(key) not in (None, ""):
        return str(payload[key]).strip()
    return default


def _last_sunday(year: int, month: int) -> date:
    last = date(year, month, 31)
    return last - timedelta(days=(last.weekday() + 1) % 7)


def europe_amsterdam_tz(at: datetime | None = None) -> timezone:
    moment = at or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    else:
        moment = moment.astimezone(timezone.utc)
    start = datetime.combine(_last_sunday(moment.year, 3), datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=1)
    end = datetime.combine(_last_sunday(moment.year, 10), datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=1)
    return timezone(timedelta(hours=2 if start <= moment < end else 1))


def today_in(payload: dict[str, Any]) -> date:
    tz_name = str(_nested(payload, "trmnl", "user", "time_zone") or "Europe/Amsterdam")
    try:
        return datetime.now(ZoneInfo(tz_name)).date()
    except Exception:
        return datetime.now(europe_amsterdam_tz()).date()


def map_waste_type(code: str) -> str:
    key = (code or "").strip().lower()
    if key in WASTE_TYPE_MAPPING:
        return WASTE_TYPE_MAPPING[key]
    for needle, label in sorted(WASTE_TYPE_MAPPING.items(), key=lambda item: len(item[0]), reverse=True):
        if needle and needle in key:
            return label
    return (code or "").strip().title() or "Afval"


def relative_label(days_until: int) -> str:
    if days_until <= 0:
        return "Vandaag"
    if days_until == 1:
        return "Morgen"
    return f"Over {days_until} dagen"


def date_label(value: date) -> str:
    return f"{value.day} {MONTHS[value.month - 1]}"


def weekday_label(value: date) -> str:
    return WEEKDAYS[value.weekday()]


def empty_result(error: str | None = None, **extra: Any) -> dict[str, Any]:
    result = {
        "collector": extra.pop("collector", "Afvalbeheer"),
        "error": error,
        "next": None,
        "upcoming": [],
        "by_type": [],
        "today": [],
        "tomorrow": [],
    }
    result.update(extra)
    return result


def http(
    url: str,
    data: dict[str, str] | None = None,
    opener=None,
    as_json: bool = True,
    timeout: int = 6,
    headers: dict[str, str] | None = None,
    json_body: Any = None,
    method: str | None = None,
) -> Any:
    if opener is None:
        opener = build_opener()
    request_headers = {"User-Agent": USER_AGENT}
    if headers:
        request_headers.update({key: value for key, value in headers.items() if value is not None})
    body = None
    if json_body is not None:
        body = json.dumps(json_body).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")
    elif data is not None:
        body = urlencode(data).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
    request = Request(url, data=body, headers=request_headers, method=method)
    with opener.open(request, timeout=timeout) as response:
        raw = response.read()
        if not raw:
            return {} if as_json else ""
        text = raw.decode("utf-8", errors="replace")
        if not as_json:
            return text
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"_raw": text}


def session_cookie(opener, name: str) -> str:
    for handler in opener.handlers:
        jar = getattr(handler, "cookiejar", None)
        if jar is None:
            continue
        for cookie in jar:
            if cookie.name == name:
                return cookie.value
    return ""


def as_items(code: str, dates: list[Any]) -> list[dict[str, str]]:
    waste_type = map_waste_type(code)
    items = []
    for raw in dates:
        text = str(raw or "").strip()
        if not text:
            continue
        items.append({"code": code, "type": waste_type, "date": text[:10]})
    return items


def fetch_circulus(postcode: str, huisnummer: str, suffix: str) -> list[dict[str, str]]:
    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    http("https://mijn.circulus.nl", opener=opener, as_json=False)
    cookie = session_cookie(opener, "CB_SESSION")
    if not cookie:
        raise RuntimeError("Geen Circulus-sessie ontvangen.")

    form = {"zipCode": postcode, "number": huisnummer}
    token = re.search(r"__AT=(.*?)&___TS=", cookie)
    if token:
        form["authenticityToken"] = token.group(1)

    registered = http("https://mijn.circulus.nl/register/zipcode.json", data=form, opener=opener)
    addresses = _nested(registered, "customData", "addresses", default=[]) or []
    if registered.get("flashMessage") and addresses:
        authentication_url = ""
        if suffix:
            pattern = re.compile(rf" {re.escape(huisnummer)} {re.escape(suffix)}", re.I)
            for address in addresses:
                if pattern.search(str(address.get("address", ""))):
                    authentication_url = address.get("authenticationUrl") or ""
                    break
        if not authentication_url:
            authentication_url = addresses[0].get("authenticationUrl") or ""
        if authentication_url:
            http("https://mijn.circulus.nl" + authentication_url, opener=opener, as_json=False)

    start = date.today() - timedelta(days=1)
    end = date.today() + timedelta(days=90)
    calendar = http(
        f"https://mijn.circulus.nl/afvalkalender.json?from={start.isoformat()}&till={end.isoformat()}",
        opener=opener,
    )
    garbage = _nested(calendar, "customData", "response", "garbage", default=[]) or []
    items = []
    for item in garbage:
        items.extend(as_items(str(item.get("code") or ""), item.get("dates") or []))
    if not items:
        raise RuntimeError("Geen ophaaldata gevonden voor dit adres.")
    return items


def fetch_ximmio(key: str, postcode: str, huisnummer: str, suffix: str) -> list[dict[str, str]]:
    base = "https://wasteprod2api.ximmio.com" if key in XIMMIO_PROD2 else "https://wasteapi.ximmio.com"
    company = XIMMIO_IDS[key]
    address_form = {
        "postCode": postcode,
        "houseNumber": huisnummer,
        "companyCode": company,
    }
    if suffix:
        address_form["HouseLetter"] = suffix
    found = http(f"{base}/api/FetchAdress", data=address_form)
    rows = found.get("dataList") or []
    if not rows:
        raise RuntimeError("Adres niet gevonden bij deze inzamelaar.")
    unique_id = rows[0].get("UniqueId")
    community = rows[0].get("Community") or ""
    calendar = http(
        f"{base}/api/GetCalendar",
        data={
            "uniqueAddressID": unique_id,
            "startDate": date.today().isoformat(),
            "endDate": (date.today() + timedelta(days=365)).isoformat(),
            "companyCode": company,
            "community": community,
        },
    )
    items = []
    for item in calendar.get("dataList") or []:
        items.extend(as_items(str(item.get("_pickupTypeText") or ""), item.get("pickupDates") or []))
    if not items:
        raise RuntimeError("Geen ophaaldata gevonden voor dit adres.")
    return items


def fetch_opzet(key: str, postcode: str, huisnummer: str, suffix: str) -> list[dict[str, str]]:
    base = OPZET_URLS[key].rstrip("/")
    matches = http(f"{base}/rest/adressen/{postcode}-{huisnummer}")
    if not isinstance(matches, list) or not matches:
        raise RuntimeError("Adres niet gevonden bij deze inzamelaar.")
    bag_id = matches[0].get("bagId")
    if suffix:
        for row in matches:
            letter = str(row.get("huisletter") or "")
            addition = str(row.get("huisnummerToevoeging") or "")
            if suffix.lower() in (letter.lower(), addition.lower()):
                bag_id = row.get("bagId")
                break
    streams = http(f"{base}/rest/adressen/{bag_id}/afvalstromen")
    items = []
    for item in streams or []:
        pickup = item.get("ophaaldatum")
        if pickup:
            items.extend(as_items(str(item.get("menu_title") or ""), [pickup]))
    if not items:
        raise RuntimeError("Geen ophaaldata gevonden voor dit adres.")
    return items


def fetch_afvalwijzer(postcode: str, huisnummer: str, suffix: str) -> list[dict[str, str]]:
    today = date.today().isoformat()
    url = (
        "https://api.mijnafvalwijzer.nl/webservices/appsinput/"
        f"?apikey={AFVALWIJZER_KEY}&method=postcodecheck&postcode={postcode}"
        f"&street=&huisnummer={huisnummer}&toevoeging={suffix}"
        f"&app_name=afvalwijzer&platform=web&afvaldata={today}&langs=nl"
    )
    payload = http(url)
    rows = []
    rows.extend(_nested(payload, "ophaaldagen", "data", default=[]) or [])
    rows.extend(_nested(payload, "ophaaldagenNext", "data", default=[]) or [])
    if isinstance(payload.get("data"), list):
        rows.extend(payload["data"])
    items = []
    for item in rows:
        if item.get("date"):
            items.extend(as_items(str(item.get("type") or ""), [item["date"]]))
    if not items:
        raise RuntimeError("Geen ophaaldata gevonden voor dit adres.")
    return items


def fetch_deafvalapp(postcode: str, huisnummer: str, suffix: str) -> list[dict[str, str]]:
    url = (
        "https://dataservice.deafvalapp.nl/dataservice/DataServiceServlet"
        f"?service=OPHAALSCHEMA&land=NL&postcode={postcode}&straatId=0"
        f"&huisnr={huisnummer}&huisnrtoev={suffix}"
    )
    text = http(url, as_json=False)
    items = []
    for line in str(text).strip().splitlines():
        parts = [part.strip() for part in line.split(";")]
        if len(parts) < 2:
            continue
        items.extend(as_items(parts[0], parts[1:-1] or parts[1:]))
    if not items:
        raise RuntimeError("Geen ophaaldata gevonden voor dit adres.")
    return items


def fetch_rova(postcode: str, huisnummer: str, suffix: str) -> list[dict[str, str]]:
    url = (
        "https://www.rova.nl/api/waste-calendar/upcoming"
        f"?houseNumber={huisnummer}&addition={suffix}&postalcode={postcode}&take=10"
    )
    payload = http(url)
    if not isinstance(payload, list):
        raise RuntimeError("Geen ophaaldata gevonden voor dit adres.")
    items = []
    for item in payload:
        title = _nested(item, "wasteType", "title", default="")
        pickup = str(item.get("date") or "")
        if title and pickup:
            items.extend(as_items(str(title), [pickup[:10]]))
    if not items:
        raise RuntimeError("Geen ophaaldata gevonden voor dit adres.")
    return items


def fetch_recycleapp(postcode: str, huisnummer: str, streetname: str) -> list[dict[str, str]]:
    if not streetname:
        raise RuntimeError("Vul een straatnaam in voor RecycleApp.")
    headers = {"x-consumer": "recycleapp.be"}
    zips = http(
        f"https://api.fostplus.be/recyclecms/public/v1/zipcodes?q={quote(postcode)}",
        headers=headers,
    )
    zip_rows = zips.get("items") if isinstance(zips, dict) else []
    if not zip_rows:
        raise RuntimeError("Postcode niet gevonden bij RecycleApp.")

    postcode_id = ""
    street_id = ""
    for zip_row in zip_rows:
        zip_id = zip_row.get("id")
        streets = http(
            "https://api.fostplus.be/recyclecms/public/v1/streets?"
            + urlencode({"q": streetname, "zipcodes": zip_id}),
            headers=headers,
        )
        street_rows = streets.get("items") if isinstance(streets, dict) else []
        if not street_rows:
            continue
        postcode_id = zip_id
        for street in street_rows:
            names = street.get("names") or {}
            if street.get("name") == streetname or names.get("nl") == streetname:
                street_id = street.get("id")
                break
        if not street_id:
            street_id = street_rows[0].get("id")
        break
    if not postcode_id or not street_id:
        raise RuntimeError("Straat niet gevonden bij RecycleApp.")

    start = date.today().isoformat()
    end = (date.today() + timedelta(days=60)).isoformat()
    payload = http(
        "https://api.fostplus.be/recyclecms/public/v1/collections?"
        + urlencode({
            "zipcodeId": postcode_id,
            "streetId": street_id,
            "houseNumber": huisnummer,
            "fromDate": start,
            "untilDate": end,
            "size": "100",
        }),
        headers=headers,
    )
    items = []
    for item in payload.get("items") or []:
        if item.get("exception") and item["exception"].get("replacedBy"):
            continue
        name = _nested(item, "fraction", "name", "nl", default="")
        stamp = str(item.get("timestamp") or "")
        if name and stamp:
            items.extend(as_items(str(name), [stamp[:10]]))
    if not items:
        raise RuntimeError("Geen ophaaldata gevonden voor dit adres.")
    return items


def fetch_limburg(postcode: str, huisnummer: str, suffix: str, streetname: str, cityname: str) -> list[dict[str, str]]:
    if not streetname or not cityname:
        raise RuntimeError("Vul straatnaam en gemeente in voor Limburg.NET.")
    base = "https://limburg.net/api-proxy/public"
    cities = http(f"{base}/afval-kalender/gemeenten/search?query={quote(cityname)}")
    if not isinstance(cities, list) or not cities or not cities[0].get("nisCode"):
        raise RuntimeError("Gemeente niet gevonden bij Limburg.NET.")
    city_id = cities[0]["nisCode"]
    streets = http(
        f"{base}/afval-kalender/gemeente/{city_id}/straten/search?query={quote(streetname)}"
    )
    if not isinstance(streets, list) or not streets or not streets[0].get("nummer"):
        raise RuntimeError("Straat niet gevonden bij Limburg.NET.")
    street_id = streets[0]["nummer"]

    items = []
    month_start = date.today().replace(day=1)
    for offset in range(2):
        year = month_start.year
        month = month_start.month
        calendar = http(
            f"{base}/kalender/{city_id}/{year}-{month}"
            f"?straatNummer={quote(str(street_id))}&huisNummer={quote(huisnummer)}"
            f"&toevoeging={quote(suffix)}"
        )
        for event in calendar.get("events") or []:
            pickup = str(event.get("date") or "")
            title = event.get("title") or ""
            if pickup and title:
                items.extend(as_items(str(title), [pickup[:10]]))
        month_start = (month_start + timedelta(days=32)).replace(day=1)
    if not items:
        raise RuntimeError("Geen ophaaldata gevonden voor dit adres.")
    return items


def fetch_omrin(postcode: str, huisnummer: str, suffix: str, email: str, password: str) -> list[dict[str, str]]:
    try:
        house_number = int(huisnummer)
    except ValueError as exc:
        raise RuntimeError("Omrin verwacht een numeriek huisnummer.") from exc
    login = http(
        "https://api.omrinafvalapp.nl/api/auth/login",
        json_body={
            "PostalCode": postcode,
            "HouseNumber": house_number,
            "HouseNumberExtension": suffix or None,
            "DeviceId": str(uuid4()),
            "Platform": "HomeAssistant",
            "AppVersion": "4.0.0 458",
            "OsVersion": "HomeAssistant",
            "Email": email or None,
            "Password": password or None,
        },
        headers={"User-Agent": "Omrin.Afvalapp.Client/1.0", "Accept": "application/json"},
    )
    token = _nested(login, "data", "accessToken", default="")
    if not login.get("success") or not token:
        raise RuntimeError("Omrin-login mislukt voor dit adres.")
    result = http(
        "https://api.omrinafvalapp.nl/graphql",
        json_body={"query": "query FetchCalendar { fetchCalendar { date type } }"},
        headers={
            "User-Agent": "GraphQL.Client/6.1.0.0",
            "Authorization": f"Bearer {token}",
        },
    )
    errors = result.get("errors") if isinstance(result, dict) else None
    if errors:
        raise RuntimeError(errors[0].get("message") or "Omrin gaf een GraphQL-fout.")
    rows = _nested(result, "data", "fetchCalendar", default=[]) or []
    items = []
    for item in rows:
        pickup = str(item.get("date") or "")
        if not pickup or pickup.startswith("0001-01-01"):
            continue
        items.extend(as_items(str(item.get("type") or ""), [pickup[:10]]))
    if not items:
        raise RuntimeError("Geen ophaaldata gevonden voor dit adres.")
    return items


def fetch_burgerportaal(key: str, postcode: str, huisnummer: str, suffix: str) -> list[dict[str, str]]:
    org_id = BURGERPORTAAL_IDS[key]
    signup = http(
        f"https://www.googleapis.com/identitytoolkit/v3/relyingparty/signupNewUser?key={BURGERPORTAAL_KEY}",
        method="POST",
    )
    token = signup.get("idToken") or signup.get("id_token")
    refresh = signup.get("refreshToken") or signup.get("refresh_token")
    if not token and refresh:
        refreshed = http(
            f"https://securetoken.googleapis.com/v1/token?key={BURGERPORTAAL_KEY}",
            data={"grant_type": "refresh_token", "refresh_token": refresh},
        )
        token = refreshed.get("id_token")
    if not token:
        raise RuntimeError("Geen Burgerportaal-sessie ontvangen.")
    base = "https://europe-west3-burgerportaal-production.cloudfunctions.net/exposed"
    addresses = http(
        f"{base}/organisations/{org_id}/address?{urlencode({'zipcode': postcode, 'housenumber': huisnummer})}",
        headers={"authorization": token},
    )
    if not isinstance(addresses, list) or not addresses:
        raise RuntimeError("Adres niet gevonden bij deze inzamelaar.")
    address_id = addresses[0].get("addressId")
    if suffix:
        for row in addresses:
            if str(row.get("addition") or "").casefold() == suffix.casefold():
                address_id = row.get("addressId")
                break
    if not address_id:
        raise RuntimeError("Adres niet gevonden bij deze inzamelaar.")
    calendar = http(
        f"{base}/organisations/{org_id}/address/{address_id}/calendar",
        headers={"authorization": token},
    )
    items = []
    for item in calendar or []:
        pickup = str(item.get("collectionDate") or "")
        fraction = item.get("fraction") or ""
        if pickup and fraction:
            items.extend(as_items(str(fraction), [pickup[:10]]))
    if not items:
        raise RuntimeError("Geen ophaaldata gevonden voor dit adres.")
    return items


AMSTERDAM_WEEKDAYS = {
    "maandag": 1,
    "dinsdag": 2,
    "woensdag": 3,
    "donderdag": 4,
    "vrijdag": 5,
    "zaterdag": 6,
    "zondag": 7,
}


def _amsterdam_day_delta(week_day: int, today: date, frequency_type: str = "") -> int:
    current_week = today.isocalendar()[1]
    current_weekday = today.isocalendar()[2]
    even_week = current_week % 2 == 0
    if frequency_type == "oneven":
        if even_week:
            return (week_day - current_weekday) + 7
        if current_weekday > week_day:
            return (week_day - current_weekday) + 14
        return week_day - current_weekday
    if frequency_type == "even":
        if not even_week:
            return (week_day - current_weekday) + 7
        if current_weekday > week_day:
            return (week_day - current_weekday) + 14
        return week_day - current_weekday
    if current_weekday > week_day:
        return (week_day - current_weekday) + 7
    return week_day - current_weekday


def _amsterdam_dates_for_year(day_delta: int, week_interval: int, today: date, even_weeks: bool) -> list[date]:
    dates: list[date] = []
    week_offset = 0
    while week_offset <= 52:
        value = today + timedelta(days=day_delta, weeks=week_offset)
        if week_interval > 1:
            iso_week = value.isocalendar()[1]
            if (iso_week % 2 == 0 and not even_weeks) or (iso_week % 2 > 0 and even_weeks):
                value = value - timedelta(weeks=1)
                if dates and dates[-1] == value:
                    value = value + timedelta(weeks=2)
                    week_offset += 1
                elif value.isocalendar()[1] % 2 > 0 and even_weeks:
                    value = value + timedelta(weeks=2)
                    week_offset += 2
                else:
                    week_offset -= 1
        dates.append(value)
        week_offset += week_interval
    return dates


def _amsterdam_parse_date(value: str, today: date) -> date | None:
    text = (value or "").strip()
    for fmt in ("%d-%m-%y", "%d-%m-%Y", "%d-%m"):
        try:
            parsed = datetime.strptime(text, fmt)
            if fmt == "%d-%m":
                return date(today.year, parsed.month, parsed.day)
            return parsed.date()
        except ValueError:
            continue
    return None


def fetch_amsterdam(postcode: str, huisnummer: str, suffix: str) -> list[dict[str, str]]:
    base = "https://api.data.amsterdam.nl/v1/afvalwijzer/afvalwijzer/"
    params = [{"postcode": postcode, "huisnummer": huisnummer}]
    if suffix:
        params = [
            {"postcode": postcode, "huisnummer": huisnummer, "huisletter": suffix.lower()},
            {"postcode": postcode, "huisnummer": huisnummer, "huisnummertoevoeging": suffix.lower()},
            {"postcode": postcode, "huisnummer": huisnummer, "huisletter": suffix.upper()},
            {"postcode": postcode, "huisnummer": huisnummer, "huisnummertoevoeging": suffix.upper()},
            {"postcode": postcode, "huisnummer": huisnummer},
        ]
    rows = []
    for query in params:
        payload = http(f"{base}?{urlencode(query)}")
        found = _nested(payload, "_embedded", "afvalwijzer", default=[]) or []
        if found:
            rows = found
            break
    if not rows:
        raise RuntimeError("Adres niet gevonden bij Amsterdam.")

    today = date.today()
    items = []
    for item in rows:
        frequency = item.get("afvalwijzerAfvalkalenderFrequentie") or ""
        where = item.get("afvalwijzerWaar") or ""
        days = item.get("afvalwijzerOphaaldagen") or ""
        code = (item.get("afvalwijzerFractieCode") or "").lower()
        if not days or not code:
            continue
        if not frequency and "stoep" not in where:
            continue
        future: list[date] = []
        for day in days.replace(" ", "").split(","):
            week_day = AMSTERDAM_WEEKDAYS.get(day)
            if not week_day:
                continue
            if not frequency:
                future.extend(_amsterdam_dates_for_year(_amsterdam_day_delta(week_day, today), 1, today, False))
            elif "week" in frequency:
                kind = frequency.replace(" weken", "").replace(" week", "")
                future.extend(
                    _amsterdam_dates_for_year(
                        _amsterdam_day_delta(week_day, today, kind),
                        2,
                        today,
                        kind == "even",
                    )
                )
            else:
                for raw in frequency.replace(" ", ".").replace("./", "").replace(".", ",").split(","):
                    parsed = _amsterdam_parse_date(raw, today)
                    if parsed and parsed >= today:
                        future.append(parsed)
        if code == "plastic":
            code = "pmdrest"
        items.extend(as_items(code, [value.isoformat() for value in future]))
    if not items:
        raise RuntimeError("Geen ophaaldata gevonden voor dit adres.")
    return items


def fetch_collections(
    key: str,
    postcode: str,
    huisnummer: str,
    suffix: str,
    streetname: str = "",
    cityname: str = "",
    email: str = "",
    password: str = "",
) -> list[dict[str, str]]:
    if key == "circulus":
        return fetch_circulus(postcode, huisnummer, suffix)
    if key == "mijnafvalwijzer":
        return fetch_afvalwijzer(postcode, huisnummer, suffix)
    if key == "deafvalapp":
        return fetch_deafvalapp(postcode, huisnummer, suffix)
    if key == "rova":
        return fetch_rova(postcode, huisnummer, suffix)
    if key == "recycleapp":
        return fetch_recycleapp(postcode, huisnummer, streetname)
    if key == "limburg.net":
        return fetch_limburg(postcode, huisnummer, suffix, streetname, cityname)
    if key == "omrin":
        return fetch_omrin(postcode, huisnummer, suffix, email, password)
    if key == "amsterdam":
        return fetch_amsterdam(postcode, huisnummer, suffix)
    if key in BURGERPORTAAL_IDS:
        return fetch_burgerportaal(key, postcode, huisnummer, suffix)
    if key in XIMMIO_IDS:
        return fetch_ximmio(key, postcode, huisnummer, suffix)
    if key in OPZET_URLS:
        return fetch_opzet(key, postcode, huisnummer, suffix)
    raise RuntimeError(f"Onbekende inzamelaar: {key}")


def parse_date(value: str) -> date | None:
    text = (value or "").strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(text[:10] if fmt == "%Y-%m-%d" else text, fmt).date()
        except ValueError:
            continue
    return None


def annotate(entry: dict[str, str], today: date) -> dict[str, Any]:
    collection_date = parse_date(entry["date"])
    days_until = (collection_date - today).days
    return {
        "type": entry["type"],
        "code": entry["code"],
        "date": collection_date.isoformat(),
        "days_until": days_until,
        "is_today": days_until == 0,
        "is_tomorrow": days_until == 1,
        "relative": relative_label(days_until),
        "weekday": weekday_label(collection_date),
        "date_label": date_label(collection_date),
        "emphasis": 3 if days_until == 0 else 2 if days_until == 1 else 1,
    }


def build_collections(raw_items: list[dict[str, str]], today: date) -> list[dict[str, Any]]:
    collections = []
    seen = set()
    for item in raw_items:
        collection_date = parse_date(item.get("date", ""))
        if collection_date is None or collection_date < today:
            continue
        key = (item.get("type"), collection_date.isoformat())
        if key in seen:
            continue
        seen.add(key)
        collections.append(annotate({**item, "date": collection_date.isoformat()}, today))
    collections.sort(key=lambda item: (item["date"], item["type"]))
    return collections


def first_by_type(collections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for item in collections:
        seen.setdefault(item["type"], item)
    return sorted(seen.values(), key=lambda item: (item["date"], item["type"]))


def next_collection(collections: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not collections:
        return None
    first_date = collections[0]["date"]
    same_day = [item for item in collections if item["date"] == first_date]
    types = [item["type"] for item in same_day]
    base = dict(same_day[0])
    base["type"] = " + ".join(types)
    base["types"] = types
    return base


def run(input):
    collector_key = normalize_collector(field(input, "collector") or "circulus")
    display = collector_name(collector_key)
    postcode = field(input, "postcode").upper().replace(" ", "")
    huisnummer = field(input, "huisnummer")
    suffix = field(input, "suffix").lower()
    streetname = field(input, "streetname")
    cityname = field(input, "cityname")
    email = field(input, "email")
    password = field(input, "password")
    address_parts = [streetname, postcode, huisnummer, suffix.upper()]
    address = " ".join(part for part in address_parts if part)
    if cityname:
        address = f"{address}, {cityname}" if address else cityname

    if not collector_key:
        return empty_result("Kies een afvalinzamelaar.", address=address, collector=display)
    if not postcode or not huisnummer:
        return empty_result("Vul een postcode en huisnummer in.", address=address, collector=display)
    if collector_key == "recycleapp" and not streetname:
        return empty_result("Vul een straatnaam in voor RecycleApp.", address=address, collector=display)
    if collector_key == "limburg.net" and (not streetname or not cityname):
        return empty_result("Vul straatnaam en gemeente in voor Limburg.NET.", address=address, collector=display)

    try:
        collections = build_collections(
            fetch_collections(
                collector_key,
                postcode,
                huisnummer,
                suffix,
                streetname=streetname,
                cityname=cityname,
                email=email,
                password=password,
            ),
            today_in(input),
        )
    except HTTPError as exc:
        return empty_result(f"{display} gaf HTTP {exc.code} terug.", address=address, collector=display)
    except URLError as exc:
        return empty_result(f"{display} is niet bereikbaar: {exc.reason}", address=address, collector=display)
    except Exception as exc:
        return empty_result(str(exc), address=address, collector=display)

    return {
        "collector": display,
        "address": address,
        "error": None,
        "next": next_collection(collections),
        "upcoming": collections[:12],
        "by_type": first_by_type(collections),
        "today": [item for item in collections if item["is_today"]],
        "tomorrow": [item for item in collections if item["is_tomorrow"]],
    }
