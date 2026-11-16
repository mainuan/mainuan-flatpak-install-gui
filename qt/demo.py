"""Inert visual states: no driver, GI import, process, network or transaction."""
from i18n import _

STATES = ('ready', 'remote', 'progress', 'success', 'error', 'cancelled')


def demo_state(phase):
    if phase not in STATES:
        raise ValueError(_('Invalid demonstration state.'))
    return {'phase': 'ready' if phase == 'remote' else phase,
            'hasFile': True, 'started': phase != 'ready',
            'iconName': 'system-software-install', 'demo': True, 'name': _('Example app'), 'id': 'org.example.App',
            'source': 'https://example.org/repo', 'scope': 'user', 'percent': 42,
            'operation': 'runtime/org.example.Platform/x86_64/stable', 'busy': False,
            'notice': _('Example source') + '\nhttps://example.org/repo',
            'message': {'success': _('Simulated result: installation completed.'),
                        'error': _('Simulated error: could not access the source.'),
                        'cancelled': _('Simulated cancellation. Completed operations may remain.'),
                        'progress': _('Downloading the current operation (simulation)…')}.get(phase, _('Demonstration without installations.')),
            'details': _('Fictitious details for visual evaluation. Real backend disabled.'),
            'installed': {}}
