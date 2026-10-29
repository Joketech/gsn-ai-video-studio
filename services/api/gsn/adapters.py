import os
from typing import Protocol

ROLES = {
    'orchestrator': 'Plan dependencies, assign specialists, require human review before release.',
    'producer': 'Turn the brief into a production plan and bounded budget.',
    'scriptwriter': 'Draft scripts and advertising copy; flag unsupported claims.',
    'storyboard': 'Break the script into scenes and shot descriptions.',
    'character': 'Organize approved identity references; never grant consent.',
    'voice': 'Prepare approved voice references and speech direction.',
    'cinematographer': 'Propose camera movements, lenses and framing.',
    'art_director': 'Specify locations, wardrobe, lighting and visual style.',
    'render_planner': 'Prepare versioned GPU inputs and cost estimates.',
    'editor': 'Plan scene order, transitions and output formats.',
    'audio': 'Plan music, sound effects and loudness checks.',
    'quality': 'Review identity consistency, artifacts and timing.',
    'delivery': 'Prepare watermarks, metadata and human delivery checklist.'
}

class HermesAdapter(Protocol):
    def run(self, role: str, instruction: str) -> dict: ...

class MockHermes:
    def run(self, role, instruction):
        if role not in ROLES:
            raise ValueError('Unknown role')
        return {'mode': 'mock', 'role': role, 'status': 'simulated',
                'output': f'Mock task received by {role}. No language model was called.'}

class UnconfiguredHermes:
    def run(self, role, instruction):
        raise RuntimeError('Live Hermes bridge is not configured or verified. Use HERMES_MODE=mock.')

def hermes():
    return MockHermes() if os.getenv('HERMES_MODE', 'mock') == 'mock' else UnconfiguredHermes()

class GPUWorker(Protocol):
    def render(self, scene: dict) -> tuple[bytes, str]: ...

class MockGPUWorker:
    def render(self, scene):
        import json
        return json.dumps({'simulation': True, 'scene': scene,
            'message': 'Queue pipeline test only. This is not a generated video.'}).encode(), 'application/json'

class CloudGPUWorker:
    def render(self, scene):
        raise RuntimeError('Cloud GPU provider not configured or verified; rendering disabled.')

def gpu():
    return MockGPUWorker() if os.getenv('RENDER_MODE', 'mock') == 'mock' else CloudGPUWorker()
