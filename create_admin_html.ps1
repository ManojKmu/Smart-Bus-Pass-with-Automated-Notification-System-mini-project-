$content = @'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Panel - Smart Bus System</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .header {
            background: white;
            padding: 20px 30px;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            margin-bottom: 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header h1 { color: #667eea; font-size: 28px; }
        .logout-btn {
            background: #e74c3c;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            text-decoration: none;
        }
        .logout-btn:hover { background: #c0392b; }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }
        .stat-card h3 { color: #666; font-size: 14px; margin-bottom: 10px; }
        .stat-card .number { font-size: 36px; font-weight: bold; color: #667eea; }
        .data-section {
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }
        .data-section h2 { color: #333; margin-bottom: 20px; font-size: 22px; }
        .table-container { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; }
        th {
            background: #667eea;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }
        td { padding: 12px; border-bottom: 1px solid #eee; }
        tr:hover { background: #f8f9fa; }
        .badge { padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }
        .badge-active { background: #d4edda; color: #155724; }
        .badge-expired { background: #f8d7da; color: #721c24; }
        .badge-google { background: #e3f2fd; color: #1565c0; }
        .badge-email { background: #fff3cd; color: #856404; }
        .search-box {
            margin-bottom: 20px;
            padding: 12px;
            width: 100%;
            max-width: 400px;
            border: 2px solid #ddd;
            border-radius: 6px;
            font-size: 14px;
        }
        .search-box:focus { outline: none; border-color: #667eea; }
        .tabs { display: flex; gap: 10px; margin-bottom: 20px; }
        .tab {
            padding: 10px 20px;
            background: #f0f0f0;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
        }
        .tab.active { background: #667eea; color: white; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 Admin Panel</h1>
            <a href="/" class="logout-btn">Logout</a>
        </div>
        <div class="stats">
            <div class="stat-card">
                <h3>Total Users</h3>
                <div class="number">{{ total_users }}</div>
            </div>
            <div class="stat-card">
                <h3>Total Passes</h3>
                <div class="number">{{ total_passes }}</div>
            </div>
            <div class="stat-card">
                <h3>Total Revenue</h3>
                <div class="number">₹{{ total_revenue }}</div>
            </div>
            <div class="stat-card">
                <h3>Active Passes</h3>
                <div class="number">{{ active_passes }}</div>
            </div>
        </div>
        <div class="tabs">
            <button class="tab active" onclick="showTab('users')">Users</button>
            <button class="tab" onclick="showTab('passes')">Passes</button>
            <button class="tab" onclick="showTab('payments')">Payments</button>
            <button class="tab" onclick="showTab('logins')">Login History</button>
        </div>
        <div id="users-tab" class="tab-content active">
            <div class="data-section">
                <h2>👥 All Users</h2>
                <input type="text" class="search-box" id="userSearch" placeholder="Search users..." onkeyup="searchTable('userSearch', 'usersTable')">
                <div class="table-container">
                    <table id="usersTable">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Email</th>
                                <th>Name</th>
                                <th>Account Type</th>
                                <th>Created At</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for user in users %}
                            <tr>
                                <td>{{ user[0] }}</td>
                                <td>{{ user[1] }}</td>
                                <td>{{ user[3] if user[3] else 'N/A' }}</td>
                                <td><span class="badge {% if user[4] == 'google' %}badge-google{% else %}badge-email{% endif %}">{{ user[4] if user[4] else 'email' }}</span></td>
                                <td>{{ user[5] if user[5] else 'N/A' }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        <div id="passes-tab" class="tab-content">
            <div class="data-section">
                <h2>🎫 All Passes</h2>
                <input type="text" class="search-box" id="passSearch" placeholder="Search passes..." onkeyup="searchTable('passSearch', 'passesTable')">
                <div class="table-container">
                    <table id="passesTable">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>User Email</th>
                                <th>Pass Type</th>
                                <th>Route</th>
                                <th>Distance</th>
                                <th>Amount</th>
                                <th>Status</th>
                                <th>Purchase Date</th>
                                <th>Expiry Date</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for pass in passes %}
                            <tr>
                                <td>{{ pass[0] }}</td>
                                <td>{{ pass[1] }}</td>
                                <td>{{ pass[2] }}</td>
                                <td>{{ pass[3] }}</td>
                                <td>{{ pass[4] }}</td>
                                <td>₹{{ pass[5] }}</td>
                                <td><span class="badge {% if pass[6] == 'active' %}badge-active{% else %}badge-expired{% endif %}">{{ pass[6] }}</span></td>
                                <td>{{ pass[7] }}</td>
                                <td>{{ pass[8] }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        <div id="payments-tab" class="tab-content">
            <div class="data-section">
                <h2>💳 All Payments</h2>
                <input type="text" class="search-box" id="paymentSearch" placeholder="Search payments..." onkeyup="searchTable('paymentSearch', 'paymentsTable')">
                <div class="table-container">
                    <table id="paymentsTable">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>User Email</th>
                                <th>Amount</th>
                                <th>Payment Method</th>
                                <th>Transaction ID</th>
                                <th>Status</th>
                                <th>Date</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for payment in payments %}
                            <tr>
                                <td>{{ payment[0] }}</td>
                                <td>{{ payment[1] }}</td>
                                <td>₹{{ payment[2] }}</td>
                                <td>{{ payment[3] }}</td>
                                <td>{{ payment[4] }}</td>
                                <td><span class="badge badge-active">{{ payment[5] }}</span></td>
                                <td>{{ payment[6] }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        <div id="logins-tab" class="tab-content">
            <div class="data-section">
                <h2>🔐 Login History</h2>
                <input type="text" class="search-box" id="loginSearch" placeholder="Search login history..." onkeyup="searchTable('loginSearch', 'loginsTable')">
                <div class="table-container">
                    <table id="loginsTable">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>User Email</th>
                                <th>IP Address</th>
                                <th>User Agent</th>
                                <th>Login Time</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for login in logins %}
                            <tr>
                                <td>{{ login[0] }}</td>
                                <td>{{ login[1] }}</td>
                                <td>{{ login[2] }}</td>
                                <td>{{ login[3][:50] }}...</td>
                                <td>{{ login[4] }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    <script>
        function showTab(tabName) {
            document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(btn => btn.classList.remove('active'));
            document.getElementById(tabName + '-tab').classList.add('active');
            event.target.classList.add('active');
        }
        function searchTable(inputId, tableId) {
            const input = document.getElementById(inputId);
            const filter = input.value.toUpperCase();
            const table = document.getElementById(tableId);
            const tr = table.getElementsByTagName('tr');
            for (let i = 1; i < tr.length; i++) {
                let found = false;
                const td = tr[i].getElementsByTagName('td');
                for (let j = 0; j < td.length; j++) {
                    if (td[j]) {
                        const txtValue = td[j].textContent || td[j].innerText;
                        if (txtValue.toUpperCase().indexOf(filter) > -1) {
                            found = true;
                            break;
                        }
                    }
                }
                tr[i].style.display = found ? '' : 'none';
            }
        }
    </script>
</body>
</html>
'@

$content | Out-File -FilePath "templates\admin.html" -Encoding UTF8
Write-Host "✅ Created admin.html"
Write-Host "File size: $((Get-Item templates\admin.html).length) bytes"
