"""Select a tested inference preset without editing private worker JSON."""
import json
import os
from pathlib import Path


def load_settings(path, environ=None):
    env = os.environ if environ is None else environ
    settings = json.loads(Path(path).read_text())
    selected = env.get('AI_MODEL', '').strip()
    if not selected:
        return settings  # Existing installations keep their configured models.
    presets = json.loads(Path(__file__).with_name('model-presets.json').read_text())
    if selected not in presets:
        raise ValueError('AI_MODEL must be one of: ' + ', '.join(presets))
    settings['models'] = {selected: presets[selected]}
    # A pending result from before a model switch keeps its original preset.
    settings['model_presets'] = presets
    return settings
