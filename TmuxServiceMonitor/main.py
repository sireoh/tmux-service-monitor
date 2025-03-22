from flask import Flask, request, jsonify, render_template_string
import subprocess

app = Flask(__name__)

# Function to execute shell commands
def run_command(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()

@app.route('/')
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>tmux service monitor</title>
        <script>
            async function fetchServices() {
                let response = await fetch('/services');
                let data = await response.json();
                document.getElementById("services").innerHTML = data.services.map(s => `
                    <li>
                        ${s} 
                        <button onclick="stopService('${s}')">Stop</button>
                        <button onclick="checkStatus('${s}')">Check Status</button>
                    </li>
                `).join('');
            }

            async function startService() {
                let name = document.getElementById("service_name").value;
                let command = document.getElementById("service_command").value;
                if (!name || !command) return alert("Enter both name and command!");
                await fetch('/start', { 
                    method: 'POST', 
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({name, command})
                });
                fetchServices();
            }

            async function stopService(name) {
                await fetch('/stop', { 
                    method: 'POST', 
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({name})
                });
                fetchServices();
            }

            async function checkStatus(name) {
                let response = await fetch('/status?name=' + name);
                let data = await response.json();
                alert("Status of " + name + ": " + data.status);
            }

            window.onload = fetchServices;
        </script>
    </head>
    <body>
        <div>Tmux Service Manager</div>
        <div>Running Services</div>
        <ul id="services">nothing atm</ul>
        <div>Start New Service</div>
        <div>
            <div>name:</div>
            <input type="text" id="service_name">
        
            <div>command:</div>
            <textarea id="service_command"></textarea>
        
            <div><button onclick="startService()">start</button></div>
        </div>
    </body>
    </html>
    """)

@app.route('/services', methods=['GET'])
def list_services():
    output = run_command("tmux list-sessions")
    services = [line.split(":")[0] for line in output.split("\n") if line]
    return jsonify({"services": services})

@app.route('/start', methods=['POST'])
def start_service():
    service_name = request.json.get("name")
    command = request.json.get("command")
    if not service_name or not command:
        return jsonify({"error": "Missing service name or command"}), 400
    run_command(f"tmux new-session -d -s {service_name} '{command}'")
    return jsonify({"message": f"Started {service_name}"}), 200

@app.route('/stop', methods=['POST'])
def stop_service():
    service_name = request.json.get("name")
    if not service_name:
        return jsonify({"error": "Missing service name"}), 400
    run_command(f"tmux kill-session -t {service_name}")
    return jsonify({"message": f"Stopped {service_name}"}), 200

@app.route('/status', methods=['GET'])
def service_status():
    service_name = request.args.get("name")
    output = run_command(f"tmux has-session -t {service_name} 2>/dev/null && echo 'running' || echo 'stopped'")
    return jsonify({"status": output})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
