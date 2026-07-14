import unittest

from aiminer.core.evaluator_factory import evaluation_config_from_mapping


class TestEvaluatorFactoryConfig(unittest.TestCase):
    def test_config_normalizes_profiles(self):
        config = evaluation_config_from_mapping(
            {
                "data_backend": "local",
                "market_mode": "mixed",
                "market_profile": "us_stock",
                "market_profiles": ["cn_stock", "us_stock"],
                "local_data_path": "/tmp/demo",
            }
        )
        self.assertEqual(config.data_backend, "local")
        self.assertEqual(config.market_profile, "us_stock")
        self.assertEqual(config.market_profiles[0], "us_stock")
