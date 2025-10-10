from datetime import datetime
from typing import List
from src.providers.base import Provider
from src.models import NewsItem
from src.utils.logger import get_logger


logger = get_logger(__name__)


class DummyNewsProvider(Provider):
    name = "dummy_news"
    priority = 1

    def is_available(self) -> bool:
        return True

    def execute(self, query: str = "", count: int = 3, **kwargs) -> List[NewsItem]:
        logger.info(f"Using dummy news provider", count=count)

        return [
            NewsItem(
                title="日本経済が予想を上回る成長を記録",
                summary="最新の経済指標によると、日本経済は前四半期比で三パーセントの成長を記録しました。専門家らは、この成長が今後も続くと予想しています。",
                url="https://example.com/news/1",
                published_at=datetime.now()
            ),
            NewsItem(
                title="円相場が大きく変動、投資家が注目",
                summary="外国為替市場では円が大きく変動しています。アナリストたちは、今後の金融政策がこの動きに影響を与えると見ています。",
                url="https://example.com/news/2",
                published_at=datetime.now()
            ),
            NewsItem(
                title="新興企業の株価が急上昇",
                summary="テクノロジー分野の新興企業の株価が今週、過去最高値を記録しました。投資家たちは、同社の革新的な技術に大きな期待を寄せています。",
                url="https://example.com/news/3",
                published_at=datetime.now()
            ),
        ][:count]
