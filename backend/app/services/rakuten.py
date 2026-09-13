import logging

import httpx

from app.core.config import settings

# 2026年5月の楽天API基盤刷新後の新エンドポイント。旧 app.rakuten.co.jp は同年5/13に廃止された。
ITEM_SEARCH_URL = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"

# httpx はデフォルトでリクエストURL(=applicationIdを含む)をINFOログに出す。
# accessKeyはヘッダー化して防いだが、applicationIdの不要な露出も減らすため黙らせる。
logging.getLogger("httpx").setLevel(logging.WARNING)


class RakutenAPIError(Exception):
    """楽天ウェブサービスの呼び出しに失敗した、または対象商品が見つからなかった場合。"""


async def fetch_item_price(item_code: str) -> int:
    """楽天市場の商品検索APIから、指定した商品コードの現在価格(税込・円)を取得する。"""
    if not settings.rakuten_app_id or not settings.rakuten_access_key:
        raise RakutenAPIError("RAKUTEN_APP_ID / RAKUTEN_ACCESS_KEY が設定されていません")

    # applicationId は仕様上クエリパラメータでしか受け付けない(ヘッダーだと400になる)。
    # accessKey は秘密情報なので、URL(=アクセスログやエラーメッセージに残りやすい)を避けて
    # ヘッダーで送る。
    params = {
        "applicationId": settings.rakuten_app_id,
        "itemCode": item_code,
        "hits": 1,
        "formatVersion": 2,
    }
    # ドキュメント上は Referer だが、2026年5月の新基盤では実際には Origin ヘッダーで
    # Allowed websites との一致を見ている(Refererだと REFERRER_MISSING エラーになる)。
    headers = {
        "Origin": settings.rakuten_allowed_origin,
        "accessKey": settings.rakuten_access_key,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(ITEM_SEARCH_URL, params=params, headers=headers)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            # httpx の例外メッセージ・トレースバックにはクエリパラメータ付きのURL
            # (=applicationIdを含む)がそのまま入るため、`from None` でチェーンを断ち切り、
            # ログにも呼び出し元にも漏れないようにする。
            status_code = exc.response.status_code
            raise RakutenAPIError(
                f"楽天ウェブサービスの呼び出しに失敗しました (HTTP {status_code})"
            ) from None
        except httpx.HTTPError as exc:
            raise RakutenAPIError(
                f"楽天ウェブサービスの呼び出しに失敗しました ({type(exc).__name__})"
            ) from None

    items = response.json().get("Items", [])
    if not items:
        raise RakutenAPIError(f"商品が見つかりません: {item_code}")

    return items[0]["itemPrice"]
