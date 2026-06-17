import subprocess
import os
import socket
import json

class ExecutionService:
    @staticmethod
    def run_terminal_command(command):
        """Executa um comando no terminal do macOS."""
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode
            }
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def clear_notes():
        """Apaga o conteúdo da nota mais recente ou deleta todas as notas da pasta padrão."""
        script = '''
        tell application "Notes"
            try
                set theFolder to folder "Notes"
                delete every note of theFolder
                return "Todas as notas da pasta 'Notes' foram excluídas."
            on error
                return "Não foi possível excluir as notas ou a pasta não foi encontrada."
            end try
        end tell
        '''
        return ExecutionService.run_applescript(script)

    @staticmethod
    def delete_note(title):
        """Exclui uma nota pelo título procurando nas pastas principais."""
        escaped_title = title.replace('"', '\\\\"')
        script = f'''
        tell application "Notes"
            activate
            set targetFolders to {{folder "Notes", folder "Observações"}}
            repeat with aFolder in targetFolders
                try
                    set theNotes to every note of aFolder whose name is "{escaped_title}"
                    repeat with aNote in theNotes
                        delete aNote
                    end repeat
                end try
            end repeat
            return "Busca de exclusão concluída para '{escaped_title}'."
        end tell
        '''
        return ExecutionService.run_applescript(script)

    @staticmethod
    def type_text(text):
        """Tenta digitar nativamente se for Notas, senão usa System Events."""
        # Se o app Notes estiver na frente, tenta adicionar o texto à nota atual
        script = f'''
        if application "Notes" is running then
            tell application "Notes"
                if (count of notes) > 0 then
                    set theNote to note 1 of folder "Notes"
                    set body of theNote to (body of theNote & "{text}")
                    return "Texto adicionado à nota nativamente."
                end if
            end tell
        end if
        
        # Fallback para System Events apenas se necessário
        tell application "System Events"
            set frontmost of process "Notes" to true
            delay 0.2
            keystroke "{text}"
        end tell
        '''
        return ExecutionService.run_applescript(script)

    @staticmethod
    def smart_search(query):
        """Usa o Spotlight (mdfind) para busca semântica/fuzzy no Mac."""
        try:
            print(f"SmartSearch: Buscando por '{query}'...")
            # Busca apenas em pastas de usuário para evitar lixo do sistema
            cmd = f"mdfind -onlyin ~ '{query}' | head -n 15"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if not result.stdout.strip():
                return f"Não encontrei nada relevante para '{query}' no seu Mac."
            
            return f"Encontrei estes itens que podem ser o que você procura:\n{result.stdout.strip()}"
        except Exception as e:
            return f"Erro na busca inteligente: {e}"

    @staticmethod
    def resolve_path(name):
        """Busca agressiva por um caminho no Mac que combine com o nome (case-insensitive)."""
        try:
            # 1. Busca rápida em Documents/pessoal (onde o usuário guarda a maioria dos projetos)
            search_cmd = f"find ~/Documents/pessoal -maxdepth 2 -iname '*{name}*' -type d | head -n 1"
            res = ExecutionService.run_terminal_command(search_cmd)
            path = res.get("stdout", "").strip()
            if path: return path
            
            # 2. Busca em Documents geral
            search_cmd = f"find ~/Documents -maxdepth 3 -iname '*{name}*' -type d | head -n 1"
            res = ExecutionService.run_terminal_command(search_cmd)
            path = res.get("stdout", "").strip()
            if path: return path
            
            # 3. Busca na Home (Desktop/Downloads)
            search_cmd = f"find ~ -maxdepth 2 -iname '*{name}*' -type d | head -n 1"
            res = ExecutionService.run_terminal_command(search_cmd)
            return res.get("stdout", "").strip() or None
        except:
            return None

    @staticmethod
    def open_app(app_name, path=None):
        """Abre um aplicativo, permitindo passar um caminho opcional (pasta/arquivo)."""
        if not app_name or "org.python.python" in app_name.lower():
            return {"error": "Nome de aplicativo inválido ou bloqueado."}
            
        # Se o LLM se confundir e passar uma URL no lugar do app
        if app_name.startswith("http"):
            return ExecutionService.open_url(app_name)
            
        # Mapeamento de nomes comuns
        app_map = {
            "notas": "Notes", "notes": "Notes",
            "calendário": "Calendar", "calendar": "Calendar",
            "vscode": "Visual Studio Code", "code": "Visual Studio Code",
            "visual studio code": "Visual Studio Code",
            "cursor": "Cursor", "finder": "Finder",
            "dia": "DIA"
        }
        
        target = app_map.get(app_name.lower(), app_name)
        cmd = ["open", "-a", target]
        if path:
            full_path = os.path.expanduser(path)
            cmd.append(full_path)

        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return {"stdout": f"Aplicativo {target} aberto." + (f" Caminho: {path}" if path else "")}
        except Exception as e:
            # Tenta fallback sem o '-a' se for um caminho direto ou comando
            try:
                if path:
                    subprocess.run(["open", path], check=True)
                    return {"stdout": f"Caminho {path} aberto com app padrão."}
            except: pass
            return {"error": f"Falha ao abrir {app_name}: {str(e)}"}

    @staticmethod
    def open_url(url, browser=None):
        """Abre uma URL no navegador padrão ou em um específico (ex: DIA)."""
        if not url.startswith("http"):
            url = "https://" + url
        try:
            import subprocess
            if browser:
                # Se for o browser "DIA" (provavelmente um alias ou app específico do usuário)
                target = "DIA" if browser.upper() == "DIA" else browser
                subprocess.run(["open", "-a", target, url])
                return f"Abrindo site no navegador {target}: {url}"
            else:
                subprocess.run(["open", url])
                return f"Abrindo site: {url}"
        except Exception as e:
            return f"Erro ao abrir URL: {str(e)}"

    @staticmethod
    def set_system_volume(level):
        """Define o volume do sistema (0-100)."""
        script = f"set volume output volume {level}"
        return ExecutionService.run_applescript(script)

    @staticmethod
    def add_reminder(title):
        """Adiciona um lembrete ao app Lembretes do macOS."""
        script = f'tell application "Reminders" to make new reminder with properties {{name:"{title}"}}'
        return ExecutionService.run_applescript(script)

    @staticmethod
    def get_calendar_events():
        """Lista os eventos de hoje sem trazer o app para a frente."""
        script = '''
        set appRunning to application "Calendar" is running
        tell application "Calendar"
            set today_start to (current date)
            set time of today_start to 0
            set today_end to today_start + (24 * 60 * 60)
            set out to ""
            repeat with a_cal in every calendar
                try
                    set the_events to (every event of a_cal whose start date is greater than or equal to today_start and start date is less than today_end)
                    repeat with e in the_events
                        set out to out & "[" & name of a_cal & "] " & (summary of e) & " às " & (start date of e as string) & "\\n"
                    end repeat
                end try
            end repeat
            if not appRunning then quit
            if out is "" then return "Nenhum evento agendado para hoje."
            return out
        end tell
        '''
        return ExecutionService.run_applescript(script)

    @staticmethod
    def get_reminders():
        """Lista os lembretes pendentes sem abrir a janela do app."""
        script = '''
        set appRunning to application "Reminders" is running
        tell application "Reminders"
            set out to ""
            repeat with l in every list
                set rs to (every reminder of l whose completed is false)
                repeat with r in rs
                    set out to out & "[" & name of l & "] " & (name of r)
                    try
                        set d to (due date of r)
                        set out to out & " (Vencimento: " & (d as string) & ")"
                    end try
                    set out to out & "\\n"
                end repeat
            end repeat
            if not appRunning then quit
            if out is "" then return "Nenhum lembrete pendente encontrado."
            return out
        end tell
        '''
        return ExecutionService.run_applescript(script)

    @staticmethod
    def manage_music(app_name, action):
        """Controla Spotify ou Apple Music (Music)."""
        app = "Spotify" if "spotify" in app_name.lower() else "Music"
        
        if action == "play":
            script = f'tell application "{app}" to play'
        elif action == "pause":
            script = f'tell application "{app}" to pause'
        elif action == "next":
            script = f'tell application "{app}" to next track'
        elif action == "previous":
            script = f'tell application "{app}" to previous track'
        elif action == "playpause":
            script = f'tell application "{app}" to playpause'
        else:
            return f"Ação '{action}' não suportada para {app}."
            
        return ExecutionService.run_applescript(script)

    @staticmethod
    def get_latest_emails(count=5):
        """Lê os últimos e-mails sem abrir a interface do Mail."""
        script = f'''
        set appRunning to application "Mail" is running
        tell application "Mail"
            try
                set out to ""
                set the_messages to (messages 1 thru {count} of inbox)
                repeat with msg in the_messages
                    set the_sender to sender of msg
                    set the_subject to subject of msg
                    set out to out & "De: " & the_sender & " | Assunto: " & the_subject & "\\n"
                end repeat
                if not appRunning then quit
                return out
            on error
                if not appRunning then quit
                return "Nenhum e-mail encontrado ou erro ao acessar o Mail."
            end try
        end tell
        '''
        return ExecutionService.run_applescript(script)

    @staticmethod
    def mail_unread(count=5):
        """Busca e-mails não lidos sem abrir a janela do Mail."""
        script = f'''
        set appRunning to application "Mail" is running
        tell application "Mail"
            try
                set today_start to (current date)
                set time of today_start to 0
                set unread_messages to (every message of inbox whose read status is false and date received is greater than or equal to today_start)
                set out to ""
                set m_count to count of unread_messages
                if m_count is 0 then
                    if not appRunning then quit
                    return "Nenhum e-mail não lido hoje."
                end if
                if m_count > {count} then set m_count to {count}
                
                repeat with i from 1 to m_count
                    set msg to item i of unread_messages
                    set out to out & "De: " & (sender of msg) & " | Assunto: " & (subject of msg) & "\\n"
                end repeat
                if not appRunning then quit
                return out
            on error
                if not appRunning then quit
                return "Erro ao buscar e-mails não lidos."
            end try
        end tell
        '''
        return ExecutionService.run_applescript(script)

    @staticmethod
    def mail_search(query):
        """Busca e-mails sem abrir a interface do Mail."""
        script = f'''
        set appRunning to application "Mail" is running
        tell application "Mail"
            set foundMessages to (every message of inbox whose subject contains "{query}" or sender contains "{query}")
            set out to ""
            set m_count to count of foundMessages
            if m_count > 5 then set m_count to 5

            repeat with i from 1 to m_count
                set msg to item i of foundMessages
                set out to out & "De: " & (sender of msg) & " | Assunto: " & (subject of msg) & "\\\\n"
            end repeat
            if not appRunning then quit
            return out
        end tell
        '''
        return ExecutionService.run_applescript(script)
    @staticmethod
    def send_imessage(target, message):
        """Envia uma iMessage para um contato ou número."""
        script = f'''
        tell application "Messages"
            set targetService to 1st service whose service type is iMessage
            set targetBuddy to buddy "{target}" of targetService
            send "{message}" to targetBuddy
        end tell
        '''
        return ExecutionService.run_applescript(script)

    # --- NOVAS FERRAMENTAS FASE 4 ---
    
    @staticmethod
    def finder_move_file(source, dest_folder):
        """Move um arquivo via Finder."""
        script = f'''
        tell application "Finder"
            move POSIX file "{source}" to POSIX file "{dest_folder}"
        end tell
        '''
        return ExecutionService.run_applescript(script)

    @staticmethod
    def finder_rename_file(path, new_name):
        """Renomeia um arquivo via Finder."""
        script = f'''
        tell application "Finder"
            set theFile to POSIX file "{path}" as alias
            set name of theFile to "{new_name}"
        end tell
        '''
        return ExecutionService.run_applescript(script)

    @staticmethod
    def mail_create_draft(subject, body, recipient=""):
        """Cria um rascunho de e-mail no app Mail."""
        script = f'''
        tell application "Mail"
            set newMessage to make new outgoing message with properties {{subject:"{subject}", content:"{body}", visible:true}}
            tell newMessage
                if "{recipient}" is not "" then
                    make new to recipient at end of to recipients with properties {{address:"{recipient}"}}
                end if
            end tell
            return "Rascunho criado."
        end tell
        '''
        return ExecutionService.run_applescript(script)

    @staticmethod
    def notes_search(query):
        """Busca notas sem abrir o app Notas."""
        script = f'''
        set appRunning to application "Notes" is running
        tell application "Notes"
            set foundNotes to every note whose name contains "{query}" or body contains "{query}"
            set out to ""
            repeat with aNote in foundNotes
                set out to out & (name of aNote) & "\\n"
            end repeat
            if not appRunning then quit
            return out
        end tell
        '''
        return ExecutionService.run_applescript(script)

    @staticmethod
    def get_system_info():
        """Obtém estatísticas rápidas do sistema (Bateria e Disco)."""
        try:
            # Bateria
            bat = subprocess.run("pmset -g batt | grep -o '[0-9]*%'", shell=True, capture_output=True, text=True).stdout.strip()
            # Disco (Espaço livre em GB no /)
            disk = subprocess.run("df -h / | awk 'NR==2 {print $4}'", shell=True, capture_output=True, text=True).stdout.strip()
            return f"Bateria: {bat} | Espaço Livre: {disk}"
        except:
            return "Erro ao obter info do sistema."

    @staticmethod
    def list_files(directory="."):
        """Lista arquivos em um diretório de forma detalhada."""
        try:
            full_path = os.path.expanduser(directory)
            if not os.path.exists(full_path):
                return f"Erro: Diretório {directory} não existe."
            
            # Usa 'ls -F' para indicar diretórios com '/'
            result = subprocess.run(["ls", "-F", full_path], capture_output=True, text=True)
            files = result.stdout.strip()
            return files if files else "Diretório vazio."
        except Exception as e:
            return f"Erro ao listar arquivos: {e}"

    @staticmethod
    def replace_in_file(path, old_string, new_string):
        """Edição cirúrgica: substitui uma string por outra em um arquivo."""
        try:
            full_path = os.path.expanduser(path)
            with open(full_path, 'r') as f:
                content = f.read()

            if old_string not in content:
                return f"Erro: A string original não foi encontrada no arquivo {path}"

            new_content = content.replace(old_string, new_string)
            with open(full_path, 'w') as f:
                f.write(new_content)
            return f"Sucesso: Arquivo {path} atualizado."
        except Exception as e:
            return f"Erro ao editar arquivo: {e}"

    @staticmethod
    def run_git(args):
        """Executa comandos Git (ex: status, commit, diff)."""
        command = f"git {args}"
        return ExecutionService.run_terminal_command(command)

    @staticmethod
    def execute_python(code):
        """Roda código Python arbitrário e retorna o output."""
        try:
            import sys
            import io
            # Redireciona stdout para capturar o print
            old_stdout = sys.stdout
            redirected_output = sys.stdout = io.StringIO()
            
            exec(code)
            
            sys.stdout = old_stdout
            return redirected_output.getvalue() or "Código executado com sucesso (sem output)."
        except Exception as e:
            return f"Erro na execução Python: {e}"

    @staticmethod
    def manage_clipboard(action, text=None):
        """Lê ou escreve na área de transferência."""
        import pyperclip
        if action == "write":
            pyperclip.copy(text)
            return "Texto copiado para o clipboard."
        else:
            return pyperclip.paste()

    @staticmethod
    def toggle_dark_mode(enabled=True):
        """Ativa ou desativa o Dark Mode no macOS."""
        state = "true" if enabled else "false"
        script = f'tell application "System Events" to tell appearance preferences to set dark mode to {state}'
        return ExecutionService.run_applescript(script)

    @staticmethod
    def set_dnd(enabled=True):
        """Tenta ativar o Não Perturbe via atalho de teclado ou comando de foco."""
        # No macOS Monterey/Ventura+, o DND é controlado via Focus. 
        # Uma forma robusta é via Atalhos ou AppleScript simulando clique no Menu Bar, 
        # mas vamos usar um script que alterna o estado de foco.
        script = '''
        tell application "System Events" to keystroke "d" using {command down, control down, option down, shift down}
        '''
        return ExecutionService.run_applescript(script)

    @staticmethod
    def get_vscode_current_file():
        """Tenta obter o caminho do arquivo aberto no VS Code ou Cursor via AppleScript."""
        script = '''
        tell application "System Events"
            set activeApp to name of first application process whose frontmost is true
            if activeApp contains "Visual Studio Code" or activeApp contains "Cursor" then
                tell application activeApp
                    try
                        return path of document 1
                    end try
                end tell
            end if
        end tell
        return "unknown"
        '''
        res = ExecutionService.run_applescript(script)
        return res.get("stdout", "unknown").strip()

    @staticmethod
    def manage_hardware(action, value=None):
        """Controla brilho e modo foco via AppleScript."""
        if action == "set_brightness":
            script = f'tell application "System Events" to repeat {int(value/10)} times \\n key code 14 \\n end repeat' # Simplificado
            return ExecutionService.run_applescript(script)
        elif action == "do_not_disturb":
            # Comando macOS para DND
            script = 'tell application "System Events" to keystroke "d" using {command down, control down, option down, shift down}' # Atalho comum
            return ExecutionService.run_applescript(script)
        return "Ação de hardware desconhecida."

    @staticmethod
    def run_tests(project_path="."):
        """Tenta identificar e rodar testes no projeto (pytest, npm test, etc)."""
        full_path = os.path.expanduser(project_path)
        
        # 1. Detectar tipo de projeto
        if os.path.exists(os.path.join(full_path, "package.json")):
            return ExecutionService.run_terminal_command(f"cd {full_path} && npm test")
        elif os.path.exists(os.path.join(full_path, "pytest.ini")) or \
             any(f.endswith(".py") for f in os.listdir(full_path) if "test" in f.lower()):
            return ExecutionService.run_terminal_command(f"cd {full_path} && pytest")
        elif os.path.exists(os.path.join(full_path, "Cargo.toml")):
            return ExecutionService.run_terminal_command(f"cd {full_path} && cargo test")
        
        return {"error": "Não foi possível identificar um framework de testes neste diretório."}

    @staticmethod
    def get_project_summary(path="."):
        """Gera um resumo técnico do que foi feito no projeto hoje."""
        try:
            full_path = os.path.expanduser(path)
            if not os.path.exists(full_path):
                return f"Diretório {path} não encontrado."
            
            summary = f"--- RESUMO TÉCNICO: {os.path.basename(full_path)} ---\n"
            
            # 1. Git activity today
            git_cmd = f"cd {full_path} && git log --since='today' --oneline"
            git_res = ExecutionService.run_terminal_command(git_cmd)
            if git_res.get("stdout"):
                summary += "\nCommits de Hoje:\n" + git_res["stdout"]
            else:
                summary += "\nNenhum commit realizado hoje.\n"
                
            # 2. Modified files in last 24h
            find_cmd = f"find {full_path} -mtime -1 -not -path '*/.*' -not -path '*/node_modules/*' -not -path '*/vendor/*' -type f | head -n 10"
            find_res = ExecutionService.run_terminal_command(find_cmd)
            if find_res.get("stdout"):
                summary += "\nArquivos Modificados (24h):\n" + find_res["stdout"]
                
            # 3. Look for recent logs
            log_cmd = f"find {full_path} -name '*.log' -mtime -1 | head -n 3"
            log_files = ExecutionService.run_terminal_command(log_cmd).get("stdout", "").strip().split("\n")
            if log_files and log_files[0]:
                summary += "\nAnálise de Logs Recentes:\n"
                for lf in log_files:
                    if not lf: continue
                    tail = ExecutionService.run_terminal_command(f"tail -n 5 {lf}").get("stdout", "")
                    summary += f"- {os.path.basename(lf)}: {tail[:150]}...\n"
            
            return summary
        except Exception as e:
            return f"Erro ao gerar resumo do projeto: {e}"

    @staticmethod
    def find_project(name):
        """Busca o caminho de um projeto pelo nome na pasta Documents ou Pessoal."""
        try:
            cmd = f"find ~/Documents -maxdepth 2 -name '*{name}*' -type d | head -n 1"
            res = ExecutionService.run_terminal_command(cmd)
            path = res.get("stdout", "").strip()
            if path:
                return path
            return f"Não encontrei nenhum diretório com '{name}' em Documents."
        except Exception as e:
            return f"Erro ao buscar projeto: {e}"

    @staticmethod
    def run_shortcut(name, input_text=""):
        """Executa um atalho do app Atalhos (Shortcuts) do macOS."""
        try:
            cmd = f'shortcuts run "{name}"'
            if input_text:
                # Passa entrada para o atalho via stdin se necessário
                process = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout, stderr = process.communicate(input=input_text)
                return {"stdout": stdout, "stderr": stderr}
            else:
                return ExecutionService.run_terminal_command(cmd)
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def list_shortcuts():
        """Lista todos os atalhos disponíveis no sistema."""
        return ExecutionService.run_terminal_command("shortcuts list")

    @staticmethod
    def set_focus_mode(mode_name="Não Perturbe"):
        """Tenta ativar um modo de foco via AppleScript."""
        # Nota: No macOS Ventura+, os modos de foco são mais restritos.
        # Uma forma comum é via UI Scripting no Control Center.
        script = f'''
        tell application "System Events"
            tell process "ControlCenter"
                click menu bar item "Focus" of menu bar 1
                delay 0.5
                click checkbox "{mode_name}" of group 1 of window "Control Center"
            end tell
        end tell
        '''
        # Fallback para Atalho se o usuário tiver um atalho de foco criado
        # ExecutionService.run_shortcut(f"Ativar {mode_name}")
        return ExecutionService.run_applescript(script)

    @staticmethod
    def capture_screen(output_path=None):
        """Captura a tela inteira e salva em um arquivo."""
        if not output_path:
            output_path = os.path.expanduser(f"~/Desktop/screenshot_{int(time.time())}.png")
        try:
            subprocess.run(["screencapture", "-x", output_path], check=True)
            return f"Captura de tela salva em: {output_path}"
        except Exception as e:
            return f"Erro na captura: {e}"

    @staticmethod
    def download_file(url, dest_path=None):
        """Baixa um arquivo ou imagem da internet."""
        import requests
        try:
            filename = url.split("/")[-1].split("?")[0] or "downloaded_file"
            if not dest_path:
                dest_path = os.path.expanduser(f"~/Downloads/{filename}")
            
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return f"Arquivo baixado com sucesso em: {dest_path}"
        except Exception as e:
            return f"Falha ao baixar arquivo: {e}"

    @staticmethod
    def run_applescript(script):
        """Executa um AppleScript para automação de UI no macOS."""
        try:
            # Comando osascript para rodar o script
            process = subprocess.Popen(['osascript', '-e', script], 
                                     stdout=subprocess.PIPE, 
                                     stderr=subprocess.PIPE, 
                                     text=True)
            stdout, stderr = process.communicate(timeout=30)
            return {
                "stdout": stdout,
                "stderr": stderr,
                "returncode": process.returncode
            }
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def send_command_to_swift(command_json):
        """Envia um comando JSON via BridgeService assíncrona/síncrona."""
        from core.bridge_service import bridge
        # Por padrão usamos síncrono para manter compatibilidade, 
        # mas agora com timeout e sem travar o socket principal.
        return bridge.send_sync(command_json)



    @staticmethod
    def create_file(path, content):
        """Cria ou sobrescreve um arquivo, criando pastas se necessário."""
        try:
            full_path = os.path.expanduser(path)
            # Cria os diretórios pai se houver um caminho de diretório
            dir_name = os.path.dirname(full_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"Sucesso: Arquivo {path} criado/atualizado."
        except Exception as e:
            return f"Erro ao criar arquivo: {e}"

    @staticmethod
    def generate_project(base_path, files_dict):
        """
        Cria um projeto inteiro de uma vez.
        files_dict: {"nome_arquivo": "conteudo"}
        """
        results = []
        try:
            full_base = os.path.expanduser(base_path)
            os.makedirs(full_base, exist_ok=True)
            for filename, content in files_dict.items():
                file_path = os.path.join(full_base, filename)
                res = ExecutionService.create_file(file_path, content)
                results.append(res)
            return f"Projeto em {base_path} gerado:\n" + "\n".join(results)
        except Exception as e:
            return f"Erro ao gerar projeto: {e}"

    @staticmethod
    def create_new_note(title, content):
        """Cria uma nota real no app Notas do macOS via AppleScript."""
        # Sanitização para AppleScript e conversão básica para "HTML" (que o Notas prefere)
        escaped_title = title.replace('"', '\\"').replace("'", "\\'")
        # Substitui quebras de linha por <br> para o corpo da nota
        html_content = content.replace('"', '\\"').replace("'", "\\'").replace("\n", "<br>")
        
        script = f'''
        tell application "Notes"
            try
                -- Tenta criar na conta padrão para ser mais robusto (independente de idioma)
                set theNote to make new note at default account with properties {{name:"{escaped_title}", body:"{html_content}"}}
                return "Nota '{escaped_title}' criada com sucesso."
            on error err
                return "Erro ao criar nota: " & err
            end try
        end tell
        '''
        return ExecutionService.run_applescript(script)

    @staticmethod
    def read_file(path):
        """Lê o conteúdo de um arquivo com limite de tamanho para segurança."""
        try:
            full_path = os.path.expanduser(path)
            if not os.path.exists(full_path):
                return f"Erro: Arquivo {path} não encontrado."
            
            if os.path.isdir(full_path):
                return f"Erro: {path} é um diretório. Use list_files."

            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(10000) # Limite de 10k chars
                if len(content) == 10000:
                    content += "\n... (Arquivo truncado)"
                return content
        except Exception as e:
            return f"Erro ao ler arquivo: {str(e)}"
            
    @staticmethod
    def control_app_ui(app_name, action_description):
        """Usa UI Scripting para clicar em menus ou botões de qualquer app."""
        # O LLM deve gerar o AppleScript específico para a ação
        # Ex: click menu item "New Window" of menu "File" of menu bar 1
        script = f'''
        tell application "System Events"
            tell process "{app_name}"
                set frontmost to true
                try
                    {action_description}
                on error err
                    return "Erro de UI: " & err
                end try
            end tell
        end tell
        '''
        return ExecutionService.run_applescript(script)

    @staticmethod
    def click_at(x, y):
        """Fallback: Clique físico usando PyAutoGUI."""
        import pyautogui
        try:
            pyautogui.click(x, y)
            return f"Clique realizado em {x}, {y}"
        except Exception as e:
            return f"Erro ao clicar: {str(e)}"
