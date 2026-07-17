"""公開のシリーズ生成エンジン契約。"""
import unittest


class SeriesEngineApiTests(unittest.TestCase):
    def test_series_engine_exposes_service_and_contract_error(self) -> None:
        from storycraft.series_engine import ContractError, SeriesService

        self.assertTrue(issubclass(ContractError, ValueError))
        self.assertTrue(callable(SeriesService))
