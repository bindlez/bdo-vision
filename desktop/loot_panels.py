"""Capture each visible feed independently; never read through covering windows."""


def capture_panels(feeds, visible, grab):
    images, errors, captured_regions = {}, {}, []
    for name, region in feeds.items():
        try:
            from loot_capture import capture_budget
            ready, reason = capture_budget(captured_regions + [region])
            if not ready:
                raise RuntimeError(reason)
            ready, reason = visible([region])
            if not ready:
                raise RuntimeError(reason)
            x, y, width, height = region
            image = grab(bbox=(x, y, x + width, y + height), all_screens=True)
            ready, reason = visible([region])
            if not ready:
                raise RuntimeError(reason)
            images[name] = image
            captured_regions.append(region)
        except Exception as exc:
            if name != 'rare':
                raise
            errors[name] = {'events': [], 'empty': False, 'recognized': 0,
                            'error': str(exc), 'debug': 'Capture unavailable: ' + str(exc)}
    return images, errors
