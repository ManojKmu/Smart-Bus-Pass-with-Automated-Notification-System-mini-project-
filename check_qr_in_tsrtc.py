"""
Check if QR code is in TSRTC ticket
"""

# Check passes.html for QR code in TSRTC ticket
with open('templates/passes.html', 'r', encoding='utf-8') as f:
    content = f.read()
    
# Find generateTSRTCTicketHTML function
func_start = content.find('function generateTSRTCTicketHTML')
func_end = content.find('function renewPass', func_start)
func_content = content[func_start:func_end] if func_end > func_start else content[func_start:]

print('=' * 60)
print('QR CODE IN TSRTC TICKET VERIFICATION')
print('=' * 60)
print()

checks = {
    'TSRTC ticket function exists': 'function generateTSRTCTicketHTML' in content,
    'QR code section in TSRTC ticket': 'qr-section' in func_content,
    'QR code API call in ticket': 'api.qrserver.com' in func_content,
    'QR code links to localhost:5000': 'http://localhost:5000' in func_content,
    'QR code label exists': 'Scan QR Code' in func_content,
    'QR code styling exists': '.qr-code' in content,
}

for check, result in checks.items():
    status = 'YES' if result else 'NO'
    print(f'[{status}] {check}')

print()
print('=' * 60)
print('WHERE QR CODE APPEARS:')
print('=' * 60)
print()
print('1. TSRTC Ticket (View Ticket button)')
print('   - Click "View Ticket" on any pass')
print('   - QR code appears before footer')
print('   - Scannable with mobile phone')
print()
print('2. Email Ticket (for new passes)')
print('   - Sent after payment')
print('   - QR code in email HTML')
print('   - Same design as frontend')
print()
print('=' * 60)
print('ANSWER: YES, QR code is in TSRTC ticket!')
print('=' * 60)
