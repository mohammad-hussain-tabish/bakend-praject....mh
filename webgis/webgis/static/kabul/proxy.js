/**
 * پروکسی برای درخواست‌های OpenLayers
 * این فایل تمام درخواست‌های OpenLayers به GeoServer را از طریق پروکسی Django ارسال می‌کند
 */

// ذخیره نسخه اصلی متد fetch
const originalFetch = window.fetch;

// لیست لایه‌های موجود در GeoServer - using exact case as in GeoServer
const geoserverLayers = [
    'cite:Kabul_Area_name',
    'cite:hospital',
    'cite:22_district'
];

// Cache for tile requests to avoid duplicates
const tileCache = new Map();

// جایگزینی متد fetch با نسخه سفارشی
window.fetch = function(url, options) {
    console.log('Fetch request to:', url);
    
    // بررسی اینکه آیا URL به GeoServer اشاره می‌کند یا خیر
    if (url && typeof url === 'string' && 
       (url.includes('localhost:8080/geoserver') || 
        url.includes('GetFeatureInfo') || 
        url.includes('WMS') || 
        url.includes('wms') ||
        geoserverLayers.some(layer => url.includes(layer)))) {
        
        console.log('Intercepting GeoServer request:', url);
        
        try {
            // اگر URL از قبل با /geoserver_proxy شروع می‌شود، آن را به همان شکل استفاده کنیم
            if (url.startsWith('/geoserver_proxy')) {
                console.log('URL is already a proxy URL, using as is');
                
                // Add a cache buster for tile requests to prevent caching issues
                if (url.includes('GetMap') && !url.includes('_cache=')) {
                    const cacheBuster = `_cache=${Date.now()}`;
                    url = url + (url.includes('?') ? '&' : '?') + cacheBuster;
                    console.log('Added cache buster to URL:', url);
                }
                
                return originalFetch(url, options)
                    .then(response => {
                        console.log(`Proxy response for ${url}: status=${response.status}`);
                        if (!response.ok) {
                            console.error(`Error response from proxy: ${response.status}`);
                        }
                        return response;
                    })
                    .catch(error => {
                        console.error(`Fetch error for ${url}:`, error);
                        throw error;
                    });
            }
            
            // استخراج پارامترهای URL
            let queryParams;
            
            if (url.startsWith('http')) {
                // اگر URL کامل باشد، از URL API استفاده می‌کنیم
                const urlObj = new URL(url);
                queryParams = urlObj.searchParams.toString();
            } else {
                // اگر URL نسبی باشد، فقط بخش پارامترها را استخراج می‌کنیم
                const queryIndex = url.indexOf('?');
                if (queryIndex !== -1) {
                    queryParams = url.substring(queryIndex + 1);
                } else {
                    queryParams = '';
                }
            }
            
            // بررسی و اطمینان از وجود پارامترهای لایه
            if (!queryParams.includes('LAYERS=') && !queryParams.includes('layers=')) {
                // اضافه کردن پارامتر LAYERS به صورت خودکار اگر وجود نداشته باشد
                for (const layer of geoserverLayers) {
                    if (url.includes(layer)) {
                        if (queryParams) {
                            queryParams += `&LAYERS=${encodeURIComponent(layer)}&QUERY_LAYERS=${encodeURIComponent(layer)}`;
                        } else {
                            queryParams = `LAYERS=${encodeURIComponent(layer)}&QUERY_LAYERS=${encodeURIComponent(layer)}`;
                        }
                        console.log(`Added layer parameter: ${layer}`);
                        break;
                    }
                }
            }
            
            // Add standard WMS parameters if not present
            if (!queryParams.includes('SERVICE=')) {
                queryParams += '&SERVICE=WMS';
            }
            
            if (!queryParams.includes('VERSION=')) {
                queryParams += '&VERSION=1.3.0';
            }
            
            if (!queryParams.includes('REQUEST=') && !queryParams.includes('request=')) {
                queryParams += '&REQUEST=GetMap';
            }

            // Add format if not present
            if (!queryParams.includes('FORMAT=') && !queryParams.includes('format=')) {
                queryParams += '&FORMAT=image/png';
            }
            
            // Add transparent if not present
            if (!queryParams.includes('TRANSPARENT=') && !queryParams.includes('transparent=')) {
                queryParams += '&TRANSPARENT=true';
            }
            
            // Add cache buster for GetMap requests
            if ((queryParams.includes('GetMap') || queryParams.includes('getmap')) && !queryParams.includes('_cache=')) {
                queryParams += `&_cache=${Date.now()}`;
            }
            
            // ساخت URL جدید با استفاده از پروکسی Django
            const proxyUrl = `/geoserver_proxy/?${queryParams}`;
            console.log('Redirecting to proxy:', proxyUrl);
            
            // ارسال درخواست از طریق پروکسی
            return originalFetch(proxyUrl, options)
                .then(response => {
                    console.log(`Proxy response for ${proxyUrl}: status=${response.status}`);
                    if (!response.ok) {
                        console.error(`Error response from proxy: ${response.status}`);
                    }
                    return response;
                })
                .catch(error => {
                    console.error(`Fetch error for ${proxyUrl}:`, error);
                    throw error;
                });
        } catch (e) {
            console.error('Error in proxy redirection:', e);
            return originalFetch(url, options);
        }
    }
    
    // ارسال سایر درخواست‌ها به صورت عادی
    return originalFetch(url, options);
};

// اطلاع‌رسانی در کنسول
console.log('GeoServer proxy initialized - Version 7 (Enhanced layer support)'); 