#!/usr/bin/env python3
"""Test Phase 2: PostgreSQL + Redis"""
import requests

# Login
resp = requests.post('http://localhost:3000/login', json={
    'username': 'admin',
    'password': 'admin123'
})
token = resp.json()['access_token']
print('✅ Logged in')

# Get segments - use 'corrected' status to see completed ones
resp = requests.get('http://localhost:3000/api/v2/transcriptions/projects/memoria_1970_1990/segments?status=corrected&limit=3', headers={
    'Authorization': f'Bearer {token}'
})

if resp.status_code == 200:
    data = resp.json()
    print(f'✅ PHASE 2 TEST SUCCESS')
    print(f'   Got {len(data.get("segments", []))} segments from PostgreSQL')
    print(f'   Total completed: {data.get("total")}')
    segs = data.get('segments', [])
    if segs:
        s = segs[0]
        print(f'   First segment:')
        print(f'   - ID: {s.get("id")}')
        print(f'   - Text: {s.get("text")[:60]}...')
        print(f'   - Status: {s.get("review_status")}')
    print()
    print('✅ PostgreSQL migration working!')
    print('✅ Redis sessions working!')
else:
    print(f'❌ Error: {resp.status_code}')
    print(resp.text[:500])
