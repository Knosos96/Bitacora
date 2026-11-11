import httpx
base = 'http://127.0.0.1:8000/api/v1'
r = httpx.post(f'{base}/auth/login', json={'correo':'jefe@correo.com','clave':'clave123'})
print('LOGIN:', r.status_code)
token = r.json()['token']
h = {'Authorization': f'Bearer {token}'}
r2 = httpx.post(f'{base}/eventos', json={
    'tipo': 'solicitud',
    'titulo': 'Test evento',
    'descripcion': 'Probando que funcione',
    'requiere_seguimiento': False
}, headers=h)
print('CREAR EVENTO:', r2.status_code)
if r2.status_code == 201:
    d = r2.json()
    print('  Folio:', d['folio'])
    print('  Titulo:', d['titulo'])
    print('  Estado:', d['estado'])
else:
    print(r2.text[:400])
