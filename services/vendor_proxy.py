import requests
from fastapi.responses import Response

CDN_CHART_URL = "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"


def get_chart_js():
    try:
        r = requests.get(CDN_CHART_URL, timeout=10)
        r.raise_for_status()
        return Response(content=r.content, media_type='application/javascript')
    except Exception as e:
        return Response(content='// Chart.js proxy unavailable', media_type='application/javascript')
