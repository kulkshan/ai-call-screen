"""Deterministic paraphrases that avoid obvious trigger words."""


REWRITES = {
    'gift cards': 'store vouchers',
    'one-time code': 'number sent to your phone',
    'act now': 'before the window closes',
    'remote access': 'screen support',
    'transfer money': 'move the balance',
}


def paraphrase(text: str) -> str:
    for source, replacement in REWRITES.items():
        text = text.replace(source, replacement)
    return text
