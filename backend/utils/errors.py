def error_response(message, code='UNKNOWN_ERROR', status=500):
    return {'error': {'code': code, 'message': message}}, status
