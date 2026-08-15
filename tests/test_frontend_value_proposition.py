from pathlib import Path


def test_frontend_mentions_unique_mali_value_proposition():
    html = Path(__file__).resolve().parents[1].joinpath('frontend', 'index.html').read_text(encoding='utf-8')

    assert 'Mali' in html
    assert 'marchés agricoles' in html.lower()
    assert 'coopératives' in html.lower()
