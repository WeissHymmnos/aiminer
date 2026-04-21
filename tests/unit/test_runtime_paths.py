import json

from core.settings import AiminerSettings
from main import save_results


def test_save_results_uses_settings_results_dir(tmp_path):
    settings = AiminerSettings(results_dir=str(tmp_path / "custom_results"))

    save_results({"iteration": 1, "max_iterations": 1}, settings=settings)

    output_path = settings.results_path / "results.json"
    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["results"][0]["iteration"] == 1
