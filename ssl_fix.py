import os
import ssl
import logging
import urllib.request
import certifi

def apply_ssl_fix():
    """Apply all possible SSL certificate verification bypasses"""
    success = False
    logging.info("Applying SSL certificate verification bypasses...")
    
    # Method 1: Set environment variable to disable certificate verification
    try:
        os.environ['PYTHONHTTPSVERIFY'] = '0'
        logging.info("Set PYTHONHTTPSVERIFY=0")
        success = True
    except Exception as e:
        logging.error(f"Failed to set PYTHONHTTPSVERIFY: {e}")
    
    # Method 2: Use unverified context
    try:
        ssl._create_default_https_context = ssl._create_unverified_context
        logging.info("Set _create_default_https_context to _create_unverified_context")
        success = True
    except Exception as e:
        logging.error(f"Failed to modify default https context: {e}")
    
    # Method 3: Monkey patch urllib.request
    try:
        old_https_handler = urllib.request.HTTPSHandler
        urllib.request.HTTPSHandler = lambda debuglevel=0, context=None, check_hostname=None: old_https_handler(debuglevel, ssl._create_unverified_context())
        logging.info("Monkey patched urllib.request.HTTPSHandler")
        success = True
    except Exception as e:
        logging.error(f"Failed to monkey patch urllib.request: {e}")
    
    # Method 4: Check if certifi is installed and try to use it
    try:
        cert_path = certifi.where()
        logging.info(f"Certifi certificates found at: {cert_path}")
        os.environ['SSL_CERT_FILE'] = cert_path
        os.environ['REQUESTS_CA_BUNDLE'] = cert_path
        logging.info(f"Set SSL_CERT_FILE and REQUESTS_CA_BUNDLE to {cert_path}")
        success = True
    except Exception as e:
        logging.error(f"Failed to set certifi path: {e}")
    
    return success
