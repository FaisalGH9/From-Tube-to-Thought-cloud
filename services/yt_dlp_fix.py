"""
Patch for yt-dlp LAZY_LOADER import issue
"""
import importlib
import logging

def apply_yt_dlp_fix():
    """Apply fixes for yt-dlp compatibility issues"""
    try:
        # First, check if we can import yt_dlp
        import yt_dlp
        logging.info("yt-dlp version: %s", yt_dlp.version.__version__)
        
        # Try to fix the _LAZY_LOADER issue
        try:
            # Check if the problematic module exists
            from yt_dlp.extractor import extractors
            logging.info("Successfully imported yt_dlp.extractor.extractors")
            
            # Check if _LAZY_LOADER is missing
            if not hasattr(extractors, '_LAZY_LOADER'):
                logging.info("_LAZY_LOADER not found, creating compatibility layer")
                
                # Create the missing _LAZY_LOADER
                class LazyLoader:
                    def __init__(self):
                        self.loaded = {}
                    
                    def __call__(self, name):
                        if name not in self.loaded:
                            self.loaded[name] = importlib.import_module(f'yt_dlp.extractor.{name}')
                        return self.loaded[name]
                
                # Patch the module
                extractors._LAZY_LOADER = LazyLoader()
                logging.info("Applied _LAZY_LOADER patch successfully")
                
                return True
            else:
                logging.info("_LAZY_LOADER already exists, no fix needed")
                return True
                
        except Exception as e:
            logging.error("Error applying yt-dlp fix: %s", str(e))
            return False
            
    except ImportError as e:
        logging.error("Error importing yt-dlp: %s", str(e))
        return False
