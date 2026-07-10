import bcrypt
import re

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def check_password(password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def format_codigo_loterico(raw_input: str) -> str:
    """
    Takes a raw input, strips everything but digits, 
    limits to 9 digits, and formats as XX.XXXXXX-X
    """
    # Remove tudo que não é número
    digits = re.sub(r'\D', '', raw_input)
    
    # Limita a 9 dígitos
    digits = digits[:9]
    
    # Se não tiver 9, apenas retorna para falhar na validação depois
    if len(digits) != 9:
        return digits
    
    # Formata: XX.XXXXXX-X
    formatted = f"{digits[:2]}.{digits[2:8]}-{digits[8:]}"
    return formatted
