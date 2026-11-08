"""Small last-seen guild indicator; no capture, polling or inferred progress."""
def guild_summary(view, enabled=True):
    if view.get('complete'):
        return 'COMPLETE · next quest', 'Last seen complete · check BDO for your next mission'
    current, target = view.get('current'), view.get('target')
    if current is not None and target:
        return f'{current:,} / {target:,}', ('Last seen' if not view.get('available') else 'Verified') + (' · reader off' if not enabled else '')
    return ('Read quest' if enabled else 'Reader off'), 'No verified quest snapshot'
