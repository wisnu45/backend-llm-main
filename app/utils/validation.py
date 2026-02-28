import re


#OPENAI_KEY_REGEX = re.compile(r"^sk-[A-Za-z0-9-]{20,}$")
OPENAI_KEY_REGEX = re.compile(r"^sk-(?:proj-)?[-A-Za-z0-9_]{40,}$")

def valid_setting_datatype(data_type):
    return data_type in ['string', 'boolean', 'integer', 'array', 'object']

def valid_setting_value(data_type, value):
    if data_type == 'boolean':
        if isinstance(value, bool):
            return True
        if str(value).lower() in ('1', 'true', '0', 'false'):
            return True
        if isinstance(value, int) and value in (0, 1):
            return True
        return False
    elif data_type == 'integer':
        try:
            int(value)
            if isinstance(value, bool):  # to exclude boolean values
                return False
            return True
        except (ValueError, TypeError):
            return False
    elif data_type == 'array':
        return isinstance(value, list) and len(value) > 0
    elif data_type == 'object':
        return isinstance(value, dict)
    elif data_type == 'string':
        return isinstance(value, str) and not isinstance(value, (list, dict, bool))
    return False


def is_openai_api_key(value):
    if not isinstance(value, str):
        return False

    candidate = value.strip()
    if len(candidate) < 24:
        return False

    return bool(OPENAI_KEY_REGEX.match(candidate))
