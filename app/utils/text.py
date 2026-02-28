import re

def to_snake_case(s: str, allowStrip=False,allowDot=False) -> str:
    if not allowDot and not allowStrip :
        return re.sub(r'[_\W\s]+', '_', s.strip()).lower().strip('_') 
    elif allowStrip and allowDot :
        return re.sub(r'[^A-Za-z0-9\-.]+', '_', s.strip()).lower().strip('_') 
    elif allowStrip  and not allowDot:
        return re.sub(r'[^A-Za-z0-9\-]+', '_', s.strip()).lower().strip('_') 
    elif not allowStrip and allowDot:
        return re.sub(r'[^A-Za-z0-9\.]+', '_', s.strip()).lower().strip('_') 

def to_normal_text(s: str) -> str:
    return s.strip().replace("_", " ").capitalize()

def to_bool(value: str) -> bool:
    return str(value).strip().lower() in ("true", "1", "yes", "on")
