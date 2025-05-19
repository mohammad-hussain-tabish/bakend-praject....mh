from django.shortcuts import render
import requests
from django.http import HttpResponse
import json

def home_page(request):
  return render(request,'index.html')

def geoserver_proxy(request):
    """
    پروکسی برای درخواست‌های GeoServer برای حل مشکل CORS
    """
    geoserver_url = "http://localhost:8080/geoserver/cite/wms"
    
    # دریافت تمام پارامترهای درخواست
    params = request.GET.dict()
    
    try:
        # ارسال درخواست به GeoServer
        response = requests.get(geoserver_url, params=params)
        
        # ایجاد پاسخ Django با محتوای دریافتی از GeoServer
        django_response = HttpResponse(
            content=response.content,
            status=response.status_code,
            content_type=response.headers.get('Content-Type', 'text/plain')
        )
        
        return django_response
    
    except Exception as e:
        # در صورت بروز خطا، پاسخ خطا برگردانده می‌شود
        return HttpResponse(
            json.dumps({"error": str(e)}),
            status=500,
            content_type="application/json"
        )

