import csv
import html
import importlib.util
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs
from dotenv import load_dotenv

from address1_where import geocode_address
from kyori import distance_between_points
from zahyou_ku import detect_kyoto_ku_from_values

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
HTML_PATH = BASE_DIR / "address.html"
APP_HTML_PATH = BASE_DIR / "app.html"
RESULT_HTML_PATH = BASE_DIR / "result.html"
STYLE_CSS_PATH = BASE_DIR / "style.css"
SCRIPT_JS_PATH = BASE_DIR / "script.js"
RESULT_CSV_PATH = BASE_DIR / "address1_result.csv"
KOKYOU_SAITAN_PATH = BASE_DIR / "dataset.kokyou_saitan.py"
HANZAI_PATH = BASE_DIR / "score" / "mini.score" / "hanzai.py"
JIKO_PATH = BASE_DIR / "score" / "mini.score" / "jiko.py"
POPULATION_PATH = BASE_DIR / "score" / "mini.score" / "population.py"
PARK_PATH = BASE_DIR / "score" / "mini.score" / "park.py"
SUPERMARKET_PATH = BASE_DIR / "score" / "mini.score" / "supermarket.py"
LIBRARY_PATH = BASE_DIR / "score" / "mini.score" / "library.py"
CITYOFFICES_PATH = BASE_DIR / "score" / "mini.score" / "cityoffices.py"
KINDERGARDEN_PATH = BASE_DIR / "score" / "mini.score" / "kindergarden.py"
ANZEN_PATH = BASE_DIR / "score" / "anzen.py"
STATION_PATH = BASE_DIR / "score" / "mini.score" / "station.mini.py"
SEIKIKA_PATH = BASE_DIR / "seikika.py"


def load_module_from_path(name: str, path: Path):
    cache_key = str(path.resolve())
    cached = _MODULE_CACHE.get(cache_key)
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _MODULE_CACHE[cache_key] = module
    return module


_MODULE_CACHE: dict[str, object] = {}


def save_result_csv(result: dict[str, object]) -> None:
    fields = [
        "address1",
        "lat1",
        "lon1",
        "ku",
        "hanzai_number",
        "mini.score_hanzai",
        "jiko_number",
        "mini.score_jiko",
        "population_number",
        "mini.score_population",
        "population_score",
        "kindergarden_number",
        "mini.score_kindergarden",
        "kindergarden_score",
        "park_name",
        "park_address",
        "park_distance_m",
        "mini.score_park",
        "park_score",
        "supermarket_name",
        "supermarket_address",
        "supermarket_distance_m",
        "mini.score_supermarket",
        "supermarket_score",
        "library_name",
        "library_address",
        "library_distance_m",
        "mini.score_library",
        "library_score",
        "cityoffices_name",
        "cityoffices_address",
        "cityoffices_distance_m",
        "mini.score_cityoffices",
        "cityoffices_score",
        "mini.number",
        "mini.score",
        "score",
        "anzen_score_sum",
        "station_name",
        "station_address",
        "station_distance_m",
        "mini.score_station",
        "lat2",
        "lon2",
        "kokyou_name",
        "kokyou_address",
        "kokyou_kyori_m",
        "error",
    ]
    with RESULT_CSV_PATH.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerow({k: result.get(k, "") for k in fields})


def render_result_page(address: str, result: dict[str, object]) -> str:
    safe = {k: html.escape(str(v)) for k, v in result.items()}
    safe_address = html.escape(address)
    error = safe.get("error", "")
    distance_text = (
        f"{safe.get('kokyou_kyori_m', '')} m"
        if str(result.get("kokyou_kyori_m", "")).strip() != ""
        else "計算できません"
    )
    hanzai_text = (
        f"{safe.get('hanzai_number', '')} 件"
        if str(result.get("hanzai_number", "")).strip() != ""
        else "取得できません"
    )
    jiko_text = (
        f"{safe.get('jiko_number', '')} 件"
        if str(result.get("jiko_number", "")).strip() != ""
        else "取得できません"
    )
    mini_score_hanzai_text = (
        str(safe.get("mini.score_hanzai", ""))
        if str(result.get("mini.score_hanzai", "")).strip() != ""
        else "取得できません"
    )
    mini_score_jiko_text = (
        str(safe.get("mini.score_jiko", ""))
        if str(result.get("mini.score_jiko", "")).strip() != ""
        else "取得できません"
    )
    station_distance_text = (
        f"{safe.get('station_distance_m', '')} m"
        if str(result.get("station_distance_m", "")).strip() != ""
        else "取得できません"
    )
    mini_score_station_text = (
        str(safe.get("mini.score_station", ""))
        if str(result.get("mini.score_station", "")).strip() != ""
        else "取得できません"
    )
    mini_number_text = (
        str(safe.get("mini.number", ""))
        if str(result.get("mini.number", "")).strip() != ""
        else "取得できません"
    )
    mini_score_total_text = (
        str(safe.get("mini.score", ""))
        if str(result.get("mini.score", "")).strip() != ""
        else "取得できません"
    )
    seikika_score_text = (
        str(safe.get("score", ""))
        if str(result.get("score", "")).strip() != ""
        else "取得できません"
    )
    anzen_sum_text = (
        str(safe.get("anzen_score_sum", ""))
        if str(result.get("anzen_score_sum", "")).strip() != ""
        else "取得できません"
    )
    error_block = f"<p style='color:#b91c1c;font-weight:600;'>error: {error}</p>" if error else ""

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Submit Result</title>
  <style>
    body {{
      font-family: "Yu Gothic", "Hiragino Kaku Gothic ProN", sans-serif;
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background: #f8fafc;
      color: #1f2937;
    }}
    .card {{
      width: min(980px, 96vw);
      background: #fff;
      border: 1px solid #e5e7eb;
      border-radius: 12px;
      padding: 24px;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.06);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 12px;
    }}
    th, td {{
      border: 1px solid #e5e7eb;
      padding: 10px;
      text-align: left;
      vertical-align: top;
    }}
    th {{ width: 280px; background: #f8fafc; }}
    .highlight {{
      margin-top: 12px;
      padding: 12px;
      border-radius: 8px;
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      color: #1e3a8a;
      font-weight: 700;
    }}
    a {{ color: #2563eb; text-decoration: none; }}
  </style>
</head>
<body>
  <main class="card">
    <h1 style="margin:0 0 8px;">submit結果</h1>
    <p style="margin:0;">住所 -> 座標 -> 区 -> 犯罪/事故件数 -> mini.score -> anzen合計 -> 最短公共施設距離</p>
    {error_block}
    <div class="highlight">最短の公共施設の距離（直線距離）: {distance_text}</div>
    <table>
      <tr><th>address (input)</th><td>{safe_address}</td></tr>
      <tr><th>address1</th><td>{safe.get("address1", "")}</td></tr>
      <tr><th>lat1</th><td>{safe.get("lat1", "")}</td></tr>
      <tr><th>lon1</th><td>{safe.get("lon1", "")}</td></tr>
      <tr><th>ku (京都市の区)</th><td>{safe.get("ku", "")}</td></tr>
      <tr><th>hanzai.number（犯罪件数）</th><td>{hanzai_text}</td></tr>
      <tr><th>mini.score_hanzai</th><td>{mini_score_hanzai_text}</td></tr>
      <tr><th>jiko.number（交通事故数）</th><td>{jiko_text}</td></tr>
      <tr><th>mini.score_jiko</th><td>{mini_score_jiko_text}</td></tr>
      <tr><th>最短駅名</th><td>{safe.get("station_name", "")}</td></tr>
      <tr><th>最短駅住所</th><td>{safe.get("station_address", "")}</td></tr>
      <tr><th>駅までの距離（m）</th><td>{station_distance_text}</td></tr>
      <tr><th>mini.score_station</th><td>{mini_score_station_text}</td></tr>
      <tr><th>mini.number（使ったmini.score数）</th><td>{mini_number_text}</td></tr>
      <tr><th>mini.score（anzen.pyの結果）</th><td>{mini_score_total_text}</td></tr>
      <tr><th>score（seikika.py 正規化後）</th><td>{seikika_score_text}</td></tr>
      <tr><th>anzen.py で足し算した結果</th><td>{anzen_sum_text}</td></tr>
      <tr><th>最短公共施設名</th><td>{safe.get("kokyou_name", "")}</td></tr>
      <tr><th>最短公共施設住所</th><td>{safe.get("kokyou_address", "")}</td></tr>
      <tr><th>lat2</th><td>{safe.get("lat2", "")}</td></tr>
      <tr><th>lon2</th><td>{safe.get("lon2", "")}</td></tr>
      <tr><th>距離</th><td>{distance_text}</td></tr>
    </table>
    <p style="margin-top:12px;">保存先: <code>{html.escape(RESULT_CSV_PATH.name)}</code></p>
    <p style="margin-top:12px;"><a href="/">戻る</a></p>
  </main>
</body>
</html>"""


def build_result_for_address(address: str) -> dict[str, object]:
    # Return a copy so callers can safely mutate/write without polluting cache.
    return dict(_build_result_for_address_cached(address.strip()))


@lru_cache(maxsize=256)
def _build_result_for_address_cached(address: str) -> dict[str, object]:
    result: dict[str, object] = {
        "address1": address,
        "lat1": "",
        "lon1": "",
        "ku": "",
        "hanzai_number": "",
        "mini.score_hanzai": "",
        "jiko_number": "",
        "mini.score_jiko": "",
        "population_number": "",
        "mini.score_population": "",
        "population_score": "",
        "kindergarden_number": "",
        "mini.score_kindergarden": "",
        "kindergarden_score": "",
        "park_name": "",
        "park_address": "",
        "park_distance_m": "",
        "mini.score_park": "",
        "park_score": "",
        "supermarket_name": "",
        "supermarket_address": "",
        "supermarket_distance_m": "",
        "mini.score_supermarket": "",
        "supermarket_score": "",
        "library_name": "",
        "library_address": "",
        "library_distance_m": "",
        "mini.score_library": "",
        "library_score": "",
        "cityoffices_name": "",
        "cityoffices_address": "",
        "cityoffices_distance_m": "",
        "mini.score_cityoffices": "",
        "cityoffices_score": "",
        "mini.number": "",
        "mini.score": "",
        "score": "",
        "station_score": "",
        "anzen_score_sum": "",
        "station_name": "",
        "station_address": "",
        "station_distance_m": "",
        "mini.score_station": "",
        "lat2": "",
        "lon2": "",
        "kokyou_name": "",
        "kokyou_address": "",
        "kokyou_kyori_m": "",
        "error": "",
    }
    try:
        geo = geocode_address(address)
        result.update(geo)
        if result.get("error") or result.get("lat1") == "" or result.get("lon1") == "":
            return result
        lat1 = float(result["lat1"])
        lon1 = float(result["lon1"])
        seikika_mod = load_module_from_path("seikika_mod", SEIKIKA_PATH)
        ku_result = detect_kyoto_ku_from_values(lat1, lon1)
        result["ku"] = ku_result.get("ku", "")
        if ku_result.get("error") and not result.get("error"):
            result["error"] = ku_result["error"]
        task_results: dict[str, dict[str, object]] = {}
        futures = {}
        with ThreadPoolExecutor(max_workers=10) as ex:
            station_mod = load_module_from_path("station_mod", STATION_PATH)
            park_mod = load_module_from_path("park_mod", PARK_PATH)
            supermarket_mod = load_module_from_path("supermarket_mod", SUPERMARKET_PATH)
            library_mod = load_module_from_path("library_mod", LIBRARY_PATH)
            cityoffices_mod = load_module_from_path("cityoffices_mod", CITYOFFICES_PATH)
            kokyou_mod = load_module_from_path("dataset_kokyou_saitan", KOKYOU_SAITAN_PATH)
            futures[ex.submit(station_mod.get_station_mini_score_by_latlon, lat1, lon1)] = "station"
            futures[ex.submit(park_mod.get_park_mini_score_by_latlon, lat1, lon1)] = "park"
            futures[ex.submit(supermarket_mod.get_supermarket_mini_score_by_latlon, lat1, lon1)] = "supermarket"
            futures[ex.submit(library_mod.get_library_mini_score_by_latlon, lat1, lon1)] = "library"
            futures[ex.submit(cityoffices_mod.get_cityoffices_mini_score_by_latlon, lat1, lon1)] = "cityoffices"
            futures[ex.submit(kokyou_mod.find_nearest_kokyou, lat1, lon1)] = "kokyou"
            if result.get("ku"):
                ku = str(result["ku"])
                hanzai_mod = load_module_from_path("hanzai_mod", HANZAI_PATH)
                jiko_mod = load_module_from_path("jiko_mod", JIKO_PATH)
                population_mod = load_module_from_path("population_mod", POPULATION_PATH)
                kindergarden_mod = load_module_from_path("kindergarden_mod", KINDERGARDEN_PATH)
                futures[ex.submit(hanzai_mod.get_hanzai_mini_score_by_ku, ku)] = "hanzai"
                futures[ex.submit(jiko_mod.get_jiko_mini_score_by_ku, ku)] = "jiko"
                futures[ex.submit(population_mod.get_population_mini_score_by_ku, ku)] = "population"
                futures[ex.submit(kindergarden_mod.get_kindergarden_mini_score_by_ku, ku)] = "kindergarden"
            for future in as_completed(futures):
                key = futures[future]
                try:
                    task_results[key] = future.result()
                except Exception as e:
                    task_results[key] = {"error": str(e)}
        if result.get("ku"):
            hanzai_result = task_results.get("hanzai", {})
            result["hanzai_number"] = hanzai_result.get("number", "")
            result["mini.score_hanzai"] = hanzai_result.get("mini.score_hanzai", "")
            if hanzai_result.get("error") and not result.get("error"):
                result["error"] = hanzai_result["error"]
            jiko_result = task_results.get("jiko", {})
            result["jiko_number"] = jiko_result.get("number", "")
            result["mini.score_jiko"] = jiko_result.get("mini.score_jiko", "")
            if jiko_result.get("error") and not result.get("error"):
                result["error"] = jiko_result["error"]
            population_result = task_results.get("population", {})
            result["population_number"] = population_result.get("number", "")
            result["mini.score_population"] = population_result.get("mini.score_population", "")
            if population_result.get("error") and not result.get("error"):
                result["error"] = population_result["error"]
            kindergarden_result = task_results.get("kindergarden", {})
            result["kindergarden_number"] = kindergarden_result.get("number", "")
            result["mini.score_kindergarden"] = kindergarden_result.get("mini.score_kindergarden", "")
            if kindergarden_result.get("error") and not result.get("error"):
                result["error"] = kindergarden_result["error"]
            try:
                h_score = int(result.get("mini.score_hanzai", "") or 0)
                j_score = int(result.get("mini.score_jiko", "") or 0)
                anzen_sum = h_score + j_score
                result["mini.number"] = 2
                result["mini.score"] = anzen_sum
                result["anzen_score_sum"] = float(anzen_sum)
            except Exception:
                anzen_mod = load_module_from_path("anzen_mod", ANZEN_PATH)
                anzen_result = anzen_mod.get_anzen_score_by_ku(str(result["ku"]))
                result["mini.number"] = anzen_result.get("mini.number", "")
                result["mini.score"] = anzen_result.get("mini.score", "")
                result["anzen_score_sum"] = anzen_result.get("anzen_score_sum", "")
                if anzen_result.get("error") and not result.get("error"):
                    result["error"] = anzen_result["error"]
            seikika_result = seikika_mod.normalize_mini_score_result(
                {"mini.number": result["mini.number"], "mini.score": result["mini.score"]}
            )
            result["score"] = seikika_result.get("score", "")
            if result.get("mini.score_population") != "":
                population_norm = seikika_mod.normalize_mini_score_result(
                    {"mini.number": 1, "mini.score": result["mini.score_population"]}
                )
                result["population_score"] = population_norm.get("score", "")
            if result.get("mini.score_kindergarden") != "":
                kindergarden_norm = seikika_mod.normalize_mini_score_result(
                    {"mini.number": 1, "mini.score": result["mini.score_kindergarden"]}
                )
                result["kindergarden_score"] = kindergarden_norm.get("score", "")
        station_result = task_results.get("station", {})
        result["station_name"] = station_result.get("station_name", "")
        result["station_address"] = station_result.get("station_address", "")
        result["station_distance_m"] = station_result.get("station_distance_m", "")
        result["mini.score_station"] = station_result.get("mini.score_station", "")
        if station_result.get("error") and not result.get("error"):
            result["error"] = station_result["error"]
        if result.get("mini.score_station") != "":
            station_norm = seikika_mod.normalize_mini_score_result(
                {"mini.number": 1, "mini.score": result["mini.score_station"]}
            )
            result["station_score"] = station_norm.get("score", "")
        park_result = task_results.get("park", {})
        result["park_name"] = park_result.get("park_name", "")
        result["park_address"] = park_result.get("park_address", "")
        result["park_distance_m"] = park_result.get("park_distance_m", "")
        result["mini.score_park"] = park_result.get("mini.score_park", "")
        if park_result.get("error") and not result.get("error"):
            result["error"] = park_result["error"]
        if result.get("mini.score_park") != "":
            park_norm = seikika_mod.normalize_mini_score_result(
                {"mini.number": 1, "mini.score": result["mini.score_park"]}
            )
            result["park_score"] = park_norm.get("score", "")
        supermarket_result = task_results.get("supermarket", {})
        result["supermarket_name"] = supermarket_result.get("supermarket_name", "")
        result["supermarket_address"] = supermarket_result.get("supermarket_address", "")
        result["supermarket_distance_m"] = supermarket_result.get("supermarket_distance_m", "")
        result["mini.score_supermarket"] = supermarket_result.get("mini.score_supermarket", "")
        if supermarket_result.get("error") and not result.get("error"):
            result["error"] = supermarket_result["error"]
        if result.get("mini.score_supermarket") != "":
            supermarket_norm = seikika_mod.normalize_mini_score_result(
                {"mini.number": 1, "mini.score": result["mini.score_supermarket"]}
            )
            result["supermarket_score"] = supermarket_norm.get("score", "")
        library_result = task_results.get("library", {})
        result["library_name"] = library_result.get("library_name", "")
        result["library_address"] = library_result.get("library_address", "")
        result["library_distance_m"] = library_result.get("library_distance_m", "")
        result["mini.score_library"] = library_result.get("mini.score_library", "")
        if library_result.get("error") and not result.get("error"):
            result["error"] = library_result["error"]
        if result.get("mini.score_library") != "":
            library_norm = seikika_mod.normalize_mini_score_result(
                {"mini.number": 1, "mini.score": result["mini.score_library"]}
            )
            result["library_score"] = library_norm.get("score", "")
        cityoffices_result = task_results.get("cityoffices", {})
        result["cityoffices_name"] = cityoffices_result.get("cityoffices_name", "")
        result["cityoffices_address"] = cityoffices_result.get("cityoffices_address", "")
        result["cityoffices_distance_m"] = cityoffices_result.get("cityoffices_distance_m", "")
        result["mini.score_cityoffices"] = cityoffices_result.get("mini.score_cityoffices", "")
        if cityoffices_result.get("error") and not result.get("error"):
            result["error"] = cityoffices_result["error"]
        if result.get("mini.score_cityoffices") != "":
            cityoffices_norm = seikika_mod.normalize_mini_score_result(
                {"mini.number": 1, "mini.score": result["mini.score_cityoffices"]}
            )
            result["cityoffices_score"] = cityoffices_norm.get("score", "")
        nearest = task_results.get("kokyou", {})
        result["lat2"] = nearest.get("lat2", "")
        result["lon2"] = nearest.get("lon2", "")
        result["kokyou_name"] = nearest.get("name1") or nearest.get("name2", "")
        result["kokyou_address"] = nearest.get("address", "")
        if nearest.get("error") and not result.get("error"):
            result["error"] = nearest["error"]
        if result["lat2"] != "" and result["lon2"] != "":
            result["kokyou_kyori_m"] = distance_between_points(
                lat1,
                lon1,
                float(result["lat2"]),
                float(result["lon2"]),
                unit="m",
                digits=1,
            )
    except Exception as e:
        result["error"] = str(e)
    return result

class Handler(BaseHTTPRequestHandler):
    def _send_bytes(self, data: bytes, content_type: str, status: int = 200) -> None:
        try:
            self.send_response(status)
            self._send_cors_headers()
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            pass

    def _send_cors_headers(self) -> None:
        origin = self.headers.get("Origin", "*")
        self.send_header("Access-Control-Allow-Origin", origin if origin else "*")
        self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_html(self, body: str, status: int = 200) -> None:
        data = body.encode("utf-8")
        try:
            self.send_response(status)
            self._send_cors_headers()
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            pass

    def _send_json(self, payload: dict[str, object], status: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        try:
            self.send_response(status)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            pass

    def do_OPTIONS(self) -> None:
        try:
            self.send_response(204)
            self._send_cors_headers()
            self.send_header("Content-Length", "0")
            self.end_headers()
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            pass

    def do_GET(self) -> None:
        static_map = {
            "/": (APP_HTML_PATH, "text/html; charset=utf-8"),
            "/app.html": (APP_HTML_PATH, "text/html; charset=utf-8"),
            "/result.html": (RESULT_HTML_PATH, "text/html; charset=utf-8"),
            "/address.html": (HTML_PATH, "text/html; charset=utf-8"),
            "/style.css": (STYLE_CSS_PATH, "text/css; charset=utf-8"),
            "/script.js": (SCRIPT_JS_PATH, "application/javascript; charset=utf-8"),
        }

        if self.path == "/favicon.ico":
            self._send_bytes(b"", "image/x-icon", status=204)
            return

        if self.path == "/config":
            self._send_json(
                {
                    "google_maps_js_api_key": os.getenv("GOOGLE_MAPS_JS_API_KEY", "").strip(),
                }
            )
            return

        info = static_map.get(self.path)
        if info is None:
            self._send_html("<h1>404 Not Found</h1>", status=404)
            return

        file_path, content_type = info
        if not file_path.exists():
            self._send_html("<h1>404 Not Found</h1>", status=404)
            return
        self._send_bytes(file_path.read_bytes(), content_type)

    def do_POST(self) -> None:
        if self.path not in ("/submit", "/submit-json"):
            self._send_html("<h1>404 Not Found</h1>", status=404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw_bytes = self.rfile.read(length)
        content_type = (self.headers.get("Content-Type", "") or "").lower()

        address = ""
        if "application/json" in content_type:
            try:
                payload = json.loads(raw_bytes.decode("utf-8"))
                address = str(payload.get("address", "")).strip()
            except Exception:
                address = ""
        else:
            raw = raw_bytes.decode("utf-8")
            form = parse_qs(raw)
            address = (form.get("address", [""])[0] or "").strip()

        if not address:
            if self.path == "/submit-json":
                self._send_json({"error": "address is required"}, status=400)
            else:
                self._send_html("<h1>address is required</h1><p><a href='/'>戻る</a></p>", status=400)
            return

        result = build_result_for_address(address)

        save_result_csv(result)
        if self.path == "/submit-json":
            self._send_json(result)
        else:
            self._send_html(render_result_page(address, result))


def main() -> None:
    host = os.getenv("ADDRESS_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("ADDRESS_SERVER_PORT", "8000"))
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"Server started: http://{host}:{port}")
    print("Open app.html or address.html via this URL to test.")
    httpd.serve_forever()


if __name__ == "__main__":
    main()

