from django.shortcuts import render
import requests
from django.http import HttpResponse
import json
import logging
import urllib.parse
import time

# تنظیم لاگر برای دیباگ
logger = logging.getLogger(__name__)

def home_page(request):
  return render(request,'index.html')

def test_layers(request):
  return render(request,'test_layers.html')

def geoserver_proxy(request):
    """
    پروکسی برای درخواست‌های GeoServer برای حل مشکل CORS
    """
    # آدرس پایه GeoServer
    geoserver_base_url = "http://localhost:8080/geoserver"
    
    # لاگ کردن تمام هدرهای درخواست
    headers_log = {key: value for key, value in request.headers.items()}
    logger.debug(f"Request headers: {headers_log}")
    
    # بررسی نوع درخواست و تعیین آدرس کامل
    service = request.GET.get('SERVICE', '').lower()
    request_type = request.GET.get('REQUEST', '').lower()
    layers = request.GET.get('LAYERS', '')  # Don't convert to lowercase
    
    logger.debug(f"Request params - SERVICE: {service}, REQUEST: {request_type}, LAYERS: {layers}")
    
    # تعیین آدرس GeoServer بر اساس پارامترهای درخواست
    if service == 'wms':
        geoserver_url = f"{geoserver_base_url}/cite/wms"
    else:
        geoserver_url = f"{geoserver_base_url}/cite/wms"  # پیش‌فرض
    
    # دریافت تمام پارامترهای درخواست
    params = request.GET.dict()
    
    # Remove cache buster if present
    if '_cache' in params:
        del params['_cache']
    
    # Make sure LAYERS parameter is preserved exactly as sent
    if 'layers' in params and 'LAYERS' not in params:
        params['LAYERS'] = params['layers']
        del params['layers']
    
    # Ensure we have proper case for layer names
    if 'LAYERS' in params:
        layer_name = params['LAYERS']
        if layer_name.lower() == 'hospital' or layer_name.lower() == 'cite:hospital':
            params['LAYERS'] = 'cite:hospital'
        elif layer_name.lower() == '22_district' or layer_name.lower() == 'cite:22_district':
            params['LAYERS'] = 'cite:22_district'
        elif layer_name.lower() == 'kabul_area_name' or layer_name.lower() == 'cite:kabul_area_name':
            params['LAYERS'] = 'cite:Kabul_Area_name'
    
    # Ensure QUERY_LAYERS matches LAYERS if present
    if 'LAYERS' in params and 'QUERY_LAYERS' in params:
        params['QUERY_LAYERS'] = params['LAYERS']
    
    # لاگ کردن پارامترها برای دیباگ
    logger.debug(f"Proxying request to GeoServer: {geoserver_url}")
    logger.debug(f"Params: {params}")
    
    # ساخت URL کامل برای لاگ کردن
    query_string = urllib.parse.urlencode(params)
    full_url = f"{geoserver_url}?{query_string}"
    logger.debug(f"Full GeoServer URL: {full_url}")
    
    try:
        # Add timestamp for debugging
        start_time = time.time()
        
        # ارسال درخواست به GeoServer
        response = requests.get(geoserver_url, params=params, timeout=10)
        
        # Calculate request time
        request_time = time.time() - start_time
        
        # لاگ کردن کد وضعیت پاسخ
        logger.debug(f"GeoServer response status: {response.status_code}, time: {request_time:.2f}s")
        logger.debug(f"GeoServer response headers: {dict(response.headers)}")
        
        if response.status_code != 200:
            logger.error(f"GeoServer error response: {response.content}")
        else:
            # Log content type and size for debugging
            content_type = response.headers.get('Content-Type', 'unknown')
            content_length = len(response.content)
            logger.debug(f"GeoServer response: type={content_type}, size={content_length} bytes")
            
            # For image responses, log more details
            if content_type.startswith('image/'):
                logger.debug(f"Image response for layer: {params.get('LAYERS', 'unknown')}")
        
        # ایجاد پاسخ Django با محتوای دریافتی از GeoServer
        django_response = HttpResponse(
            content=response.content,
            status=response.status_code,
            content_type=response.headers.get('Content-Type', 'text/plain')
        )
        
        # اضافه کردن هدرهای CORS به پاسخ
        django_response["Access-Control-Allow-Origin"] = "*"
        django_response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        django_response["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
        
        return django_response
    
    except requests.exceptions.RequestException as e:
        # در صورت بروز خطا در ارتباط با GeoServer
        logger.error(f"Error connecting to GeoServer: {str(e)}")
        error_response = HttpResponse(
            json.dumps({"error": str(e)}),
            status=500,
            content_type="application/json"
        )
        # اضافه کردن هدرهای CORS به پاسخ خطا
        error_response["Access-Control-Allow-Origin"] = "*"
        error_response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        error_response["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
        return error_response
    
    except Exception as e:
        # در صورت بروز سایر خطاها
        logger.error(f"Unexpected error in proxy: {str(e)}")
        error_response = HttpResponse(
            json.dumps({"error": str(e)}),
            status=500,
            content_type="application/json"
        )
        # اضافه کردن هدرهای CORS به پاسخ خطا
        error_response["Access-Control-Allow-Origin"] = "*"
        error_response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        error_response["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
        return error_response

