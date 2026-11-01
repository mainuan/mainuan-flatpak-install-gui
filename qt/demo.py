"""Inert visual states: no driver, GI import, process, network or transaction."""
STATES = ('ready', 'remote', 'progress', 'success', 'error', 'cancelled')


def demo_state(phase):
    if phase not in STATES:
        raise ValueError('Estado demonstrativo inválido.')
    return {'phase': 'ready' if phase == 'remote' else phase,
            'hasFile': True, 'started': phase != 'ready',
            'iconName': 'system-software-install', 'demo': True, 'name': 'Aplicativo de exemplo', 'id': 'org.example.App',
            'source': 'https://example.org/repo', 'scope': 'user', 'percent': 42,
            'operation': 'runtime/org.example.Platform/x86_64/stable', 'busy': False,
            'notice': 'Origem de exemplo\nhttps://example.org/repo',
            'message': {'success': 'Resultado simulado: instalação concluída.',
                        'error': 'Erro simulado: não foi possível acessar a origem.',
                        'cancelled': 'Cancelamento simulado. Operações concluídas podem permanecer.',
                        'progress': 'Baixando a operação atual (simulação)…'}.get(phase, 'Demonstração sem instalações.'),
            'details': 'Detalhes fictícios para avaliação visual. Backend real desativado.',
            'installed': {}}
