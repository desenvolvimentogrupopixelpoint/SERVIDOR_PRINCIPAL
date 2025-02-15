import subprocess
from flask import Flask, Response, render_template, request, jsonify, send_from_directory
import os
import json
from datetime import datetime


# Utility functions to handle JSON files
def load_json(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return json.load(file)
    return {}

def save_json(file_path, data):
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

# Flask app initialization
app = Flask(__name__, template_folder='templates', static_folder='static')

# File paths
GRUPOS_PATH = 'config/grupos.json'

# Load grupos JSON file
def load_grupos():
    if os.path.exists(GRUPOS_PATH):
        with open(GRUPOS_PATH, 'r') as file:
            try:
                grupos = json.load(file)
                if isinstance(grupos, list):
                    return grupos
                else:
                    return []
            except json.JSONDecodeError:
                return []
    return []


def ping(ip):
    try:
        # Realiza o PING baseado no sistema operacional
        response = subprocess.run(
            ["ping", "-c", "1", ip] if os.name != "nt" else ["ping", "-n", "1", ip],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return response.returncode == 0  # Retorna True se o PING foi bem-sucedido
    except Exception as e:
        print(f"Erro ao realizar PING: {e}")
        return False





# Save grupos JSON file
def save_grupos(data):
    save_json(GRUPOS_PATH, data)


@app.route('/send-media-stream', methods=['POST'])
def send_media_stream():
    try:
        # Obter dados enviados pelo front-end
        file = request.files['file']  # Arquivo enviado
        start_time = request.form['start_time']  # Data de início
        end_time = request.form['end_time']  # Data de fim
        dispositivos = json.loads(request.form['dispositivos'])  # IPs dos dispositivos

        # Caminho completo do arquivo enviado
        file_path = os.path.join(os.getcwd(), 'temp_uploads', file.filename)
        upload_dir = os.path.dirname(file_path)

        # Cria o diretório de upload temporário, se não existir
        os.makedirs(upload_dir, exist_ok=True)

        # Salva o arquivo no servidor temporariamente
        file.save(file_path)

        results = []
        for ip in dispositivos:
            # Executa o comando CURL para cada dispositivo
            command = [
                "curl", "-X", "POST",
                "-F", f"file=@{file_path}",
                "-F", f"start_time={start_time}",
                "-F", f"end_time={end_time}",
                f"http://{ip}:5000/upload"
            ]
            try:
                response = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                results.append({
                    "ip": ip,
                    "output": response.stdout.decode('utf-8'),
                    "error": response.stderr.decode('utf-8'),
                    "returncode": response.returncode
                })
            except Exception as e:
                results.append({"ip": ip, "error": str(e)})

        # Remove o arquivo temporário após o envio
        if os.path.exists(file_path):
            os.remove(file_path)

        return jsonify({"status": "completed", "results": results}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/grupo/<group_name>')
def detalhes_grupo(group_name):
    # Carrega os grupos do arquivo JSON
    grupos = load_grupos()
    
    # Busca o grupo pelo nome (exatamente ou insensível a maiúsculas/minúsculas)
    grupo = next((g for g in grupos if g['nome'].lower() == group_name.lower()), None)

    # Se o grupo não for encontrado, renderiza uma página de erro
    if not grupo:
        return render_template('404.html', message="Grupo não encontrado.")

    # Renderiza o template com os detalhes do grupo
    return render_template('grupo.html', grupo=grupo)



@app.route('/grupo/<group_name>/status', methods=['GET'])
def check_group_status(group_name):
    grupos = load_grupos()
    grupo = next((g for g in grupos if g['nome'] == group_name), None)

    if not grupo:
        return jsonify({"status": "error", "message": "Grupo não encontrado."}), 404

    # Pega o último dispositivo do grupo como referência
    dispositivos = grupo.get('dispositivos', [])
    if not dispositivos:
        return jsonify({"status": "INATIVO", "message": "Nenhum dispositivo encontrado."}), 200

    dispositivo_referencia = dispositivos[-1]
    ip = dispositivo_referencia.get('endereco')

    try:
        response = subprocess.run(
            ["curl", "-X", "GET", f"http://{ip}:5000/list"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if response.returncode == 0:
            medias = json.loads(response.stdout.decode('utf-8'))
            if medias.get("active"):  # Verifica se há mídias ativas
                return jsonify({"status": "ATIVO"}), 200
        return jsonify({"status": "INATIVO"}), 200
    except Exception as e:
        return jsonify({"status": "INATIVO", "message": str(e)}), 500


@app.route('/delete-media-all', methods=['POST'])
def delete_media_all():
    """
    Exclui uma mídia de todos os dispositivos conectados de um grupo específico.
    """
    data = request.json
    filename = data.get('filename')  # Nome do arquivo a ser excluído
    folder = data.get('folder')  # Pasta ('active' ou 'inactive')
    group_name = data.get('group_name')  # Nome do grupo específico

    # Validação dos parâmetros recebidos
    if not filename or not folder or not group_name:
        return jsonify({'status': 'error', 'message': 'Parâmetros inválidos fornecidos.'}), 400

    # Carrega os grupos do arquivo JSON
    grupos = load_grupos()

    # Filtra o grupo pelo nome fornecido
    grupo = next((g for g in grupos if g['nome'] == group_name), None)
    if not grupo:
        return jsonify({'status': 'error', 'message': f"Grupo '{group_name}' não encontrado."}), 404

    # Obtém os dispositivos pertencentes apenas ao grupo específico
    dispositivos = grupo.get('dispositivos', [])
    if not dispositivos:
        return jsonify({'status': 'error', 'message': 'Nenhum dispositivo conectado encontrado no grupo.'}), 404

    results = []  # Lista para armazenar os resultados das operações
    total_success = 0  # Contador de exclusões bem-sucedidas
    total_errors = 0  # Contador de exclusões que falharam

    # Itera sobre cada dispositivo do grupo e tenta excluir o arquivo
    for dispositivo in dispositivos:
        ip = dispositivo.get('endereco')  # Obtém o IP do dispositivo
        if not ip:
            continue

        try:
            # Envia o comando CURL para excluir a mídia no dispositivo remoto
            response = subprocess.run(
                [
                    "curl", "-X", "POST", "-H", "Content-Type: application/json",
                    "-d", json.dumps({"filename": filename, "folder": folder}),
                    f"http://{ip}:5000/delete"
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            if response.returncode == 0:
                # Decodifica a resposta do dispositivo
                result_message = json.loads(response.stdout.decode())
                if result_message.get('status') == 'success':
                    total_success += 1
                else:
                    total_errors += 1
                results.append({'ip': ip, 'status': 'success', 'message': result_message})
            else:
                total_errors += 1
                results.append({'ip': ip, 'status': 'error', 'message': response.stderr.decode()})
        except Exception as e:
            # Captura qualquer erro e adiciona aos resultados
            total_errors += 1
            results.append({'ip': ip, 'status': 'error', 'message': str(e)})

    # Retorna um resumo detalhado dos resultados
    return jsonify({
        'status': 'completed',
        'total_success': total_success,
        'total_errors': total_errors,
        'results': results
    }), 200






@app.route('/delete-media', methods=['POST'])
def delete_media():
    data = request.json  # Obtém os dados enviados no corpo da requisição
    name = data.get('name')  # Nome do arquivo a ser excluído
    status = data.get('status')  # Status para determinar a pasta (active/inactive)

    # Define os caminhos das pastas para mídia ativa e inativa
    active_folder = "/home/pixelpoint/videos"
    inactive_folder = "/home/pixelpoint/midias_inativas"

    # Seleciona a pasta correta com base no status
    if status == "active":
        folder = active_folder
    elif status == "inactive":
        folder = inactive_folder
    else:
        return jsonify({"status": "error", "message": "Status inválido fornecido."}), 400

    # Caminho completo do arquivo
    file_path = os.path.join(folder, name)

    try:
        # Verifica se o arquivo existe e tenta excluí-lo
        if os.path.exists(file_path):
            os.remove(file_path)
            return jsonify({"status": "success", "message": f"Mídia '{name}' excluída com sucesso."}), 200
        else:
            return jsonify({"status": "error", "message": f"Mídia '{name}' não encontrada no caminho especificado."}), 404
    except Exception as e:
        # Retorna erro em caso de falha na exclusão
        return jsonify({"status": "error", "message": f"Erro ao excluir mídia: {str(e)}"}), 500




@app.route('/list', methods=['GET'])
def list_files():
    print("Listando arquivos...")  # Log inicial
    metadata = load_metadata()
    active_files = []
    inactive_files = []

    for folder, file_list in [(UPLOAD_FOLDER, active_files), (INACTIVE_FOLDER, inactive_files)]:
        for file in os.listdir(folder):
            if file.lower().endswith('.mp4'):
                file_path = os.path.join(folder, file)
                size = round(os.path.getsize(file_path) / (1024 * 1024), 2)
                file_metadata = metadata.get(file, {})
                start_time = file_metadata.get('start_time', '-')
                end_time = file_metadata.get('end_time', '-')

                file_list.append({
                    'name': file,
                    'size': size,
                    'start_time': start_time,
                    'end_time': end_time
                })
    print("Ativos:", active_files)  # Log dos ativos
    print("Inativos:", inactive_files)  # Log dos inativos

    return jsonify({'active': active_files, 'inactive': inactive_files})

@app.route('/atualizar-midias', methods=['GET'])
def atualizar_midias():
    ip = request.args.get('ip')
    if not ip:
        return jsonify({"status": "error", "message": "IP não fornecido"}), 400
    try:
        response = subprocess.run(
            ["curl", "-X", "GET", f"http://{ip}:5000/list"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if response.returncode == 0:
            medias = json.loads(response.stdout.decode('utf-8'))
            print("Medias retornadas:", medias)  # Log para verificar os dados
            return jsonify({"status": "success", "media": medias}), 200
        else:
            return jsonify({"status": "error", "message": "Erro ao consultar mídias"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500



@app.route('/get-reference-media', methods=['GET'])
def get_reference_media():
    grupos = load_grupos()
    if not grupos:
        return jsonify({"status": "error", "message": "Nenhum grupo encontrado"}), 404

    # Seleciona o último dispositivo do último grupo
    ultimo_grupo = grupos[-1]
    dispositivos = ultimo_grupo.get('dispositivos', [])
    if not dispositivos:
        return jsonify({"status": "error", "message": "Nenhum dispositivo encontrado no grupo"}), 404

    dispositivo_referencia = dispositivos[-1]
    ip = dispositivo_referencia.get('endereco')

    # Verifica se o dispositivo está ativo
    if not ping(ip):
        return jsonify({"status": "error", "message": f"Dispositivo de referência {ip} está inativo"}), 400

    # Consulta as mídias do dispositivo de referência
    try:
        response = subprocess.run(
            ["curl", "-X", "GET", f"http://{ip}:5000/list"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if response.returncode == 0:
            medias = json.loads(response.stdout.decode('utf-8'))
            return jsonify({"status": "success", "media": medias}), 200
        else:
            return jsonify({"status": "error", "message": "Erro ao consultar mídias"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500




@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        file = request.files['file']
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        
        # Caminho para onde o arquivo será salvo
        file_path = f"/home/pixelpoint/midias_inativa/{file.filename}"
        file.save(file_path)  # Salva o arquivo no destino desejado
        
        return jsonify({"status": "success", "message": "Arquivo enviado com sucesso."}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": f"Erro ao salvar o arquivo: {str(e)}"}), 500




@app.route('/check-status', methods=['POST'])
def check_status():
    data = request.get_json()
    ip = data.get('ip')
    
    if not ip:
        return jsonify({"status": "error", "message": "IP não fornecido"}), 400
    
    is_active = ping(ip)
    status = "ATIVO" if is_active else "INATIVO"
    
    return jsonify({"status": status}), 200







@app.route('/informacoes')
def informacoes():
    return render_template('informacoes.html')


@app.route('/adicionar_grupo', methods=['POST'])
def adicionar_grupo():
    grupos = load_grupos()  # Carrega os grupos existentes
    novo_grupo = request.json  # Recebe o JSON enviado do frontend

    # Verifica se a variável 'grupos' é uma lista antes de tentar adicionar
    if isinstance(grupos, list):
        grupos.append(novo_grupo)  # Adiciona o novo grupo à lista
    else:
        return jsonify({"message": "Erro ao adicionar grupo: Estrutura de dados inválida."}), 400

    save_grupos(grupos)  # Salva no arquivo grupos.json
    return jsonify({"message": "Grupo adicionado com sucesso!"}), 201


@app.route('/editar_grupo', methods=['POST'])
def editar_grupo():
    data = request.json
    grupos = load_grupos()
    for grupo in grupos:
        if grupo['nome'] == data.get('nome_antigo'):
            grupo['nome'] = data.get('novo_nome', grupo['nome'])
            grupo['endereco'] = data.get('novo_endereco', grupo['endereco'])
            break
    else:
        return jsonify({"message": "Grupo não encontrado"}), 404

    save_grupos(grupos)
    return jsonify({"message": "Grupo editado com sucesso!"}), 200


# Add a new device to a group
@app.route('/grupo/<group_name>/add-device', methods=['POST'])
def add_device_to_group(group_name):
    data = request.json
    grupos = load_grupos()
    group = next((g for g in grupos if g['nome'] == group_name), None)

    if not group:
        return jsonify({"message": "Grupo não encontrado."}), 404

    novo_dispositivo = {
        "nome": data.get("nome"),
        "endereco": data.get("endereco"),
        "status": "Ativo"
    }

    group.setdefault('dispositivos', []).append(novo_dispositivo)
    save_grupos(grupos)

    return jsonify({"message": "Dispositivo adicionado com sucesso."}), 201

@app.route('/excluir_grupo', methods=['POST'])
def excluir_grupo():
    grupos = load_grupos()  # Carrega os grupos existentes
    group_name = request.json.get('nome')  # Obtém o nome do grupo a ser excluído

    # Filtra apenas os grupos que **não** correspondem ao nome fornecido
    novos_grupos = [grupo for grupo in grupos if grupo['nome'] != group_name]

    # Se nenhum grupo foi removido, significa que o grupo não existia
    if len(novos_grupos) == len(grupos):
        return jsonify({"message": "Grupo não encontrado!"}), 404

    save_grupos(novos_grupos)  # Salva a nova lista de grupos sem o excluído
    return jsonify({"message": f"Grupo '{group_name}' excluído com sucesso!"}), 200



# Remove a device from a group
@app.route('/grupo/<group_name>/delete-device', methods=['POST'])
def delete_device_from_group(group_name):
    data = request.json
    grupos = load_grupos()
    group = next((g for g in grupos if g['nome'] == group_name), None)

    if not group:
        return jsonify({"message": "Grupo não encontrado."}), 404

    dispositivos = group.get('dispositivos', [])
    group['dispositivos'] = [d for d in dispositivos if d['nome'] != data.get("nome")]
    save_grupos(grupos)

    return jsonify({"message": "Dispositivo removido com sucesso."}), 200

# Update the status of a device
@app.route('/grupo/<group_name>/update-device-status', methods=['POST'])
def update_device_status(group_name):
    data = request.json
    grupos = load_grupos()
    group = next((g for g in grupos if g['nome'] == group_name), None)

    if not group:
        return jsonify({"message": "Grupo não encontrado."}), 404

    dispositivos = group.get('dispositivos', [])
    for dispositivo in dispositivos:
        if dispositivo['nome'] == data.get("nome"):
            dispositivo['status'] = data.get("status", dispositivo['status'])
            break

    save_grupos(grupos)
    return jsonify({"message": "Status do dispositivo atualizado com sucesso."}), 200








# Get all grupos
@app.route('/get-grupos', methods=['GET'])
def get_grupos():
    grupos = load_grupos()

    # Atualiza o status de cada grupo
    for grupo in grupos:
        dispositivos = grupo.get('dispositivos', [])
        grupo['status'] = "INATIVO"  # Assume que está inativo por padrão

        for dispositivo in dispositivos:
            ip = dispositivo.get('endereco')
            try:
                # Consulta o dispositivo para verificar mídias ativas
                response = subprocess.run(
                    ["curl", "-X", "GET", f"http://{ip}:5000/list"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                if response.returncode == 0:
                    medias = json.loads(response.stdout.decode('utf-8'))
                    if medias.get("active"):  # Se houver mídias ativas
                        grupo['status'] = "ATIVO"
                        break  # Sai do loop, pois já sabemos que o grupo é ativo
            except Exception:
                continue  # Ignora erros e tenta o próximo dispositivo

    # Ordena os grupos: os ATIVOS primeiro
    grupos.sort(key=lambda g: g['status'] == "INATIVO")

    return jsonify(grupos)


@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5050)
