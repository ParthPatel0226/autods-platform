"""Yahoo Finance connector via yfinance."""

import logging

import pandas as pd

from core.exceptions import DataLoadError
from data_connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class YahooFinanceConnector(BaseConnector):
    """Connector for Yahoo Finance stock/market data."""

    @property
    def connector_type(self) -> str:
        return "yahoo_finance"

    @property
    def display_name(self) -> str:
        return "Yahoo Finance"

    def validate_config(self, config: dict) -> tuple[bool, str]:
        if not config.get("tickers"):
            return False, "tickers is required (e.g. 'AAPL' or 'AAPL,MSFT,GOOG')"
        return True, ""

    def load(self, config: dict) -> pd.DataFrame:
        valid, error = self.validate_config(config)
        if not valid:
            raise DataLoadError(error)

        try:
            import yfinance as yf

            tickers = config["tickers"]
            period = config.get("period", "1y")
            interval = config.get("interval", "1d")

            if isinstance(tickers, str):
                tickers = [t.strip() for t in tickers.split(",")]

            logger.info("Fetching Yahoo Finance: %s", tickers)

            if len(tickers) == 1:
                ticker = yf.Ticker(tickers[0])
                df = ticker.history(period=period, interval=interval)
                df["Ticker"] = tickers[0]
            else:
                frames = []
                for t in tickers:
                    try:
                        hist = yf.Ticker(t).history(
                            period=period, interval=interval
                        )
                        hist["Ticker"] = t
                        frames.append(hist)
                    except Exception as e:
                        logger.warning("Failed to fetch %s: %s", t, e)
                if not frames:
                    raise DataLoadError("No data fetched for any ticker")
                df = pd.concat(frames)

            df = df.reset_index()
            logger.info("Loaded %d rows x %d columns", len(df), len(df.columns))
            return df

        except ImportError:
            raise DataLoadError("Install yfinance: pip install yfinance")
        except Exception as e:
            raise DataLoadError(f"Yahoo Finance load failed: {e}")

    def get_preview(self, config: dict, n_rows: int = 5) -> pd.DataFrame:
        return self.load(config).head(n_rows)

    def get_config_schema(self) -> list[dict]:
        return [
            {"name": "tickers", "type": "text", "label": "Ticker Symbol(s)",
             "required": True,
             "help_text": "Comma-separated (e.g. AAPL,MSFT,GOOG)"},
            {"name": "period", "type": "select", "label": "Period",
             "options": ["1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"],
             "default": "1y"},
            {"name": "interval", "type": "select", "label": "Interval",
             "options": ["1d", "1wk", "1mo"],
             "default": "1d"},
        ]
