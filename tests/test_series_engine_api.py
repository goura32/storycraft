"""公開のシリーズ生成エンジン契約。"""
import unittest


class SeriesEngineApiTests(unittest.TestCase):
    def test_contracts_module_owns_contract_error(self) -> None:
        from storycraft.series_contracts import ContractError

        self.assertTrue(issubclass(ContractError, ValueError))

    def test_contracts_module_owns_deterministic_brief_validation(self) -> None:
        from storycraft.series_contracts import ContractError, ContractValidator

        with self.assertRaises(ContractError):
            ContractValidator._validate_brief({})

    def test_store_module_owns_state_store(self) -> None:
        from storycraft.series_store import StateStore

        self.assertTrue(callable(StateStore))

    def test_output_module_owns_output_writer(self) -> None:
        from storycraft.series_output import OutputWriter

        self.assertTrue(callable(OutputWriter))

    def test_workflow_module_owns_orchestration(self) -> None:
        from storycraft.series_workflow import SeriesWorkflow

        self.assertTrue(callable(SeriesWorkflow))

    def test_series_engine_exposes_service_and_contract_error(self) -> None:
        from storycraft.series_engine import ContractError, SeriesService

        self.assertTrue(issubclass(ContractError, ValueError))
        self.assertTrue(callable(SeriesService))
