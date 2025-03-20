import flet as ft
import requests
import os
import sys
import asyncio
import ast
from pathlib import Path
from hiyabocut import unshort
import base64
from bs4 import BeautifulSoup
import json
from threading import Event
from requests.exceptions import Timeout

file_path= Path.home() / "Download"

headers = {"User-Agent":"Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0"}

def get_config_file():
    """Obtiene la ruta del archivo de configuración dependiendo del sistema operativo."""
    if sys.platform.startswith("win"):
        # 📌 Ruta en Windows, Linux y otros sistemas
        return Path.home() / ".downloader_config.json"
    else:
        # 📌 Almacenamiento privado de la aplicación en Android
        app_dir = Path("/storage/emulated/0/Download")
        app_dir.mkdir(parents=True, exist_ok=True)  # 📂 Asegurar que la carpeta exista
        return app_dir / "downloader_config.json"
    
def save_download_path(path):
    """Guarda la ruta de descarga en un archivo JSON."""
    config_file = get_config_file()
    try:
        with open(config_file, "w") as file:
            json.dump({"download_path": str(path)}, file)
        print(f"Configuración guardada en: {config_file}")
    except Exception as e:
        print(f"Error al guardar la configuración: {e}")

def load_download_path():
    """Carga la ruta de descarga desde el archivo JSON."""
    config_file = get_config_file()
    if config_file.exists():
        try:
            with open(config_file, "r") as file:
                config = json.load(file)
                return Path(config.get("download_path", ""))
        except Exception as e:
            print(f"Error al cargar la configuración: {e}")
    return None  # Si no hay configuración, devolver None

def make_session(dl):
    session = requests.Session()
    username = dl['u']
    password = dl['p']
    if dl['m'] == 'm':
      return session
    if dl["m"] == "uoi" or dl["m"] == "evea" or dl['m'] == 'md' or dl['m'] == 'ts':
        base64_url = "aHR0cHM6Ly9kb3duZnJlZS1hcGlkYXRhLm9ucmVuZGVyLmNvbS9zZXNzaW9u"
        decoded_url = base64.b64decode(base64_url).decode("utf-8")
        v = str(dl["id"])
        resp = requests.post(decoded_url,json={"id":v},headers={'Content-Type':'application/json'})
        data = json.loads(resp.text)
        session.cookies.update(data)
        return session
    if dl['m'] == 'moodle':
        url = dl['c']+'login/index.php'
    elif dl['m'] == 'rev2':
        url = dl['c'].split('author')[0]+"login/signIn"
    else:
      url = dl['c'].split('/$$$call$$$')[0]+ '/login/signIn'
    resp = session.get(url,headers=headers,allow_redirects=True,verify=False)
    soup = BeautifulSoup(resp.text, "html.parser")
    if dl['m'] == 'moodle':
      try:
        token = soup.find("input", attrs={"name": "logintoken"})["value"]
        payload = {"anchor": "",
        "logintoken": token,
        "username": username,
        "password": password,
        "rememberusername": 1}
      except:
        payload = {"anchor": "",
        "username": username,
        "password": password,
        "rememberusername": 1}
    elif dl['m'] == 'rev2':
        payload = {"source":"",
                   "username":username,
                   "password":password,
                   "remember":"1"}
    else:
      try:
          csrfToken = soup.find('input',{'name':'csrfToken'})['value']
          payload = {}
          payload['csrfToken'] = csrfToken
          payload['source'] = ''
          payload['username'] = username
          payload['password'] = password
          payload['remember'] = '1'
      except Exception as ex:
          print(ex)
    
    resp = session.post(url,headers=headers,data=payload,verify=False,timeout=60)
    if resp.url!=url:
        return session
    return None

class Downloader:
    def __init__(self, page: ft.Page):
        self.page = page
        self.connection_lost_event = Event() 
        self.download_queue = asyncio.Queue()
        self.pause_event = Event()
        self.stop_event = Event()
        self.downloading = False 
        self.max_retries = 5

        self.download_path = self.get_default_download_path()

        self.current_page = "downloads"  # Página actual
        self.setup_ui()
        self.page.run_task(self.start_download)

    def get_default_download_path(self):
        """Obtiene la ruta de la carpeta de descargas según el sistema operativo."""
        saved_path = load_download_path()
        if saved_path:
            return Path(saved_path)  # 📌 Asegura que sea un objeto Path
        if sys.platform.startswith("win"):
            return Path.home() / "Downloads"  # 📂 Windows
        else:
            return Path("/storage/emulated/0/Download")
        
    def setup_ui(self):
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.bgcolor = ft.Colors.GREY_900

        # Barra de navegación
        self.page.navigation_bar = ft.NavigationBar(
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icons.HOME, label="Home"),
                ft.NavigationBarDestination(icon=ft.Icons.SETTINGS, label="Settings"),
            ],
            on_change=self.change_page
        )

        # Contenido de Descargas
        self.status_label = ft.Text("Estado de descarga", size=14, text_align=ft.TextAlign.CENTER)
        self.url_input = ft.TextField(hint_text="Introduce la URL", expand=True, bgcolor=ft.Colors.GREY, border_radius=10)
        self.progress_bar = ft.ProgressBar(value=0, width=200, bgcolor=ft.Colors.GREY)
        self.progress_text = ft.Text("0 MB / 0 MB (0.0%)", size=12, color=ft.Colors.WHITE)
        self.download_list = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

        self.download_tab = ft.SafeArea(
            ft.Column([
                ft.Container(
                    content=ft.Text("📥 Down Free", size=20, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER, color=ft.Colors.CYAN_ACCENT),
                    bgcolor=ft.Colors.BLUE_GREY,
                    padding=15,
                    border_radius=12,
                    alignment=ft.alignment.center
                ),
                ft.Row([
                    self.url_input,
                    ft.IconButton(ft.Icons.DOWNLOAD, on_click=self.queue_download, icon_color=ft.Colors.CYAN_ACCENT)
                ], spacing=10, alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(
                    content=ft.Column([
                        self.progress_bar,
                        self.progress_text
                    ], alignment=ft.MainAxisAlignment.CENTER),
                    padding=10,
                    border_radius=10,
                    bgcolor=ft.Colors.GREY
                ),
                self.status_label,
                ft.Container(content=self.download_list, expand=True)
            ], spacing=15, expand=True, alignment=ft.MainAxisAlignment.CENTER)
        )

        # Contenido de Configuración
        self.download_folder_label = ft.Text(f"{self.download_path}", size=14, color=ft.Colors.WHITE)
        self.file_picker = ft.FilePicker(on_result=self.on_folder_selected)
        self.page.overlay.append(self.file_picker)
        
        self.download_path_container = ft.Container(
            content=ft.Column([
                ft.Text("📂 Guardar descargas en", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                self.download_folder_label,
            ], spacing=5),
            padding=15,
            bgcolor=ft.Colors.GREY_900,
            border_radius=10,
            ink=True,  # Agrega efecto de "clic" al tocar
            on_click=lambda _: self.file_picker.get_directory_path()  # Abre el selector de carpetas
        )

        self.storage_settings_container = ft.Container(
            content=ft.Column([
                ft.Text("⚙️ Ajustes de almacenamiento", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ft.Text("Abrir configuración del almacenamiento del sistema", size=14, color=ft.Colors.GREY_400),
            ], spacing=5),
            padding=15,
            bgcolor=ft.Colors.GREY_900,
            border_radius=10,
            ink=True,
            on_click=lambda _: self.open_storage_settings()  # Abre ajustes de almacenamiento
        )

        self.permission_button = ft.ElevatedButton(
            "📂 Solicitar permiso de almacenamiento",
            data=ft.PermissionType.STORAGE,
            on_click=self.request_permission
        )

        self.config_tab = ft.SafeArea(
            ft.Column([
                ft.Text("⚙️ Settings", size=20, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                self.download_path_container,
                self.storage_settings_container,
                self.permission_button
            ], alignment=ft.MainAxisAlignment.CENTER)
        )

        self.page.add(self.download_tab)  # Iniciar con la pestaña de descargas
        self.ph = ft.PermissionHandler()
        self.page.overlay.append(self.ph)
        self.page.update()

    def change_page(self, e):
        """Cambia entre la pestaña de descargas y configuración."""
        self.page.controls.clear()
        if e.control.selected_index == 0:
            self.page.add(self.download_tab)
        else:
            self.page.add(self.config_tab)
        self.page.update()

    def check_permission(self, e):
        o = self.ph.check_permission(e.control.data)
        self.page.add(ft.Text(f"Checked {e.control.data.name}: {o}"))

    def request_permission(self, e):
        try:
            o = self.ph.request_permission(e.control.data)
            self.page.add(ft.Text(f"Permisos Concedidos Correctamente"))
        except Exception as ex:
            self.page.add(ft.Text(f"Error al obtener Permisos: {ex}"))

    def open_storage_settings(self):
        """Abre la configuración de almacenamiento de la app en Android."""
        if self.ph.open_app_settings():
            self.page.add(ft.Text("⚙️ Abriendo configuración de la app..."))
        else:
            self.page.add(ft.Text("⚠️ No se pudo abrir la configuración."))
        self.page.update()

    def on_folder_selected(self, e: ft.FilePickerResultEvent):
        """Actualiza la carpeta de descarga si el usuario elige una."""
        if e.path:
            self.download_path = Path(e.path)
            self.download_folder_label.value = f"{self.download_path}"
            self.page.update()
            save_download_path(self.download_path)
            self.mostrar_mensaje(f"📂 Ruta seleccionada: {self.download_path}")

    def mostrar_mensaje(self, mensaje):
        """Muestra un mensaje tipo SnackBar en Flet."""
        self.page.open(ft.SnackBar(ft.Text(mensaje)))
        self.page.update()

    async def queue_download(self, e):
        url_text = self.url_input.value.strip()
        if not url_text:
            self.mostrar_error("❌ Introduce una URL válida.")
            return
        try:
            url = ast.literal_eval(url_text)  # 🔹 Convierte la cadena a un diccionario
            file_status = self.add_download(url["fn"])   # 📌 Agregar nombre del archivo a la lista UI
            url["status_text"] = file_status 
            await self.download_queue.put(url) 
            self.url_input.value = ""  # Limpiar campo
            self.page.update()
        except Exception as ex:
            if "invalid syntax" in str(ex):
                self.mostrar_error(f"❌ URL Invalida")
            else:
                self.mostrar_error(f"❌ Error en la URL: {str(ex)}")

    async def start_download(self):
        while True:
            if not self.downloading and not self.download_queue.empty():
                self.downloading = True 
                dl = await self.download_queue.get()  # 🔹 Esperar una nueva descarga
                filet = dl['fn']
                if len(filet) > 25:
                    filet = filet[:20] + "." + filet[-5:]
                if "status_text" in dl:
                    dl["status_text"].value = f"📂 {filet} - Descargando..."
                    dl["status_text"].update()  # 🔹 Forzar actualización
                    self.page.update()
                self.page.update()
                await self._download_file(dl)  # 🔹 Descargar el archivo
                self.download_queue.task_done()  # 🔹 Marcar como completada
                self.downloading = False 
                self.page.update()
            await asyncio.sleep(1)   

    async def _download_file(self, dl, ichunk=0, index=0):
        try:
            filename = dl['fn']
            self.status_label.value = f"📥 Descargando..."
            self.page.update()
            total_size = dl['fs']
            total_parts = dl["t"] * 1024 * 1024

            if dl["m"] in ["m", "ts", "md", "rev2"]:
                dl['urls'] = eval(unshort(dl["urls"]))

            total_url = len(dl["urls"])
            session = make_session(dl)
            chunk_por = index
            filet = dl['fn']
            if len(filet) > 25:
                filet = filename[:20] + "." + filename[-5:]
            # Ruta de descarga
            download_path = self.download_path / filename
            if os.path.exists(download_path):
                os.unlink(download_path)
            part_files = []
            for i, chunkur in enumerate(dl['urls']):
                part_path = f"{download_path}.part{i}"
                part_files.append(part_path)
                if os.path.exists(part_path):
                    chunk_por += os.path.getsize(part_path)
                    if os.path.getsize(part_path) >= total_parts:
                        print(f"Parte {i} ya descargada, omitiendo.")
                        continue
                chunkurl = self._get_chunk_url(dl, chunkur, filename, i)

                retries = 0
                while retries < self.max_retries:
                    try:
                        if dl['m'] in ['moodle', 'evea'] and not self._is_session_active(session, chunkurl):
                            print("Sesión inactiva, regenerando sesión...")
                            session = make_session(dl)
                        with open(part_path, "wb") as part_file:
                            resp = session.get(chunkurl, headers=headers, stream=True, verify=False)
                            resp.raise_for_status()
                            downloaded = 0
                            for chunk in resp.iter_content(chunk_size=8192):
                                downloaded += len(chunk)
                                chunk_por = sum(
                                    os.path.getsize(f"{download_path}.part{j}") for j in range(i)
                                ) + downloaded 
                                progress = chunk_por / total_size          
                                part_file.write(chunk)
                                self.update_download(filename, progress, chunk_por, total_size)
                                await asyncio.sleep(0)

                        expected_size = total_parts if (i < total_url - 1) else total_size % total_parts
                        if os.path.getsize(part_path) < expected_size:
                            print(f"Error: La parte {i} se descargó con tamaño 0 bytes.")
                            os.remove(part_path)
                            retries += 1
                            await asyncio.sleep(5)
                            continue
                        break

                    except requests.exceptions.RequestException:
                        if not self.check_connection():
                            self.mostrar_error("🔴 Sin conexión. Esperando reconexión...")
                            await self._retry_connection()
                            self.page.update()
                            while not self.check_connection():
                                await asyncio.sleep(5)
                            self.connection_lost_event.clear()
                            self.status_label.value = f"📥 Descargando..."
                            self.page.update()

                if retries >= self.max_retries:
                    self.mostrar_error(f"No se pudo completar la parte {i + 1} tras múltiples intentos.")
                    return

            downloaded_parts = [os.path.exists(part) and os.path.getsize(part) > 0 for part in part_files]
            if all(downloaded_parts) and len(downloaded_parts) == total_url:
                self._merge_parts(download_path, len(part_files))
            else:
                self.mostrar_error("Faltaron partes del archivo por descargar. Verifica la conexión y reintenta.")

            self._replace_bytes_if_needed(dl, download_path)

            self.complete_download(filet)
        except Exception as ex:
            print(f"¡Error! {str(ex)}")
            self.mostrar_error("Error de conexión: No se pudo conectar al servidor.")

    async def _retry_connection(self):
        """Reintenta la conexión hasta 5 veces antes de rendirse."""
        for _ in range(5):
            if self.check_connection():
                return True
            await asyncio.sleep(5)  # Espera sin bloquear la UI
        return False

    def check_connection(self):
        """Verifica el estado de la conexión."""
        try:
            response = requests.get('https://www.portal.nauta.cu/login', timeout=5)  # Chequea conexión
            if response.status_code == 200:
                return True
        except (requests.ConnectionError, Timeout):
            return False

    def _merge_parts(self, output_path, num_parts):
        """Une todas las partes descargadas en un único archivo."""
        try:
            with open(output_path, "wb") as final_file:
                for i in range(num_parts):
                    part_path = f"{output_path}.part{i}"
                    if not os.path.exists(part_path):
                        print(f"Parte faltante: {part_path}. No se puede completar la unión.")
                        return
                    with open(part_path, "rb") as part_file:
                        while chunk := part_file.read(8192):
                            final_file.write(chunk)
                    os.remove(part_path)  # Eliminar la parte una vez unida
            print(f"Descarga completada y unida: {output_path}")
            self.status_label.value = f"✅ Descarga finalizada: {output_path}"
            self.page.update()
        except Exception as e:
            print(f"Error al unir las partes: {e}")

    def _get_chunk_url(self, dl, chunkur, filename, i):
        """Obtiene la URL del chunk basado en el modo de descarga."""
        if dl['m'] in ['m', 'ts', 'md', 'rev2']:
            return chunkur
        elif dl["m"] == "uoi":
            return chunkur + "/.file"
        elif dl['m'] in ['moodle', 'evea']:
            draftid, fileid = chunkur.split(":")
            return f"{dl['c']}draftfile.php/{draftid}/user/draft/{fileid}/{filename.replace(' ', '%2520')}-{i}.zip"
        else:
            return dl['c'].split('^')[0] + chunkur + dl['c'].split('^')[1]

    def _replace_bytes_if_needed(self, dl, download_path):
        """Elimina ciertos bytes no deseados en algunos archivos."""
        if dl["m"] not in ["uoi", "m", "moodle", "evea", "ts"]:
            chunk_size = 1024 * 1024
            target_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xf6\x178U\x00\x00\x00\x00IEND\xaeB`\x82"
            replacement_bytes = b""
            def replace_bytes(chunk, target, replacement):
                return chunk.replace(target, replacement)
            with open(download_path, "rb") as original_file, open(download_path + ".tmp", "wb") as new_file:
                while True:
                    chunk = original_file.read(chunk_size)
                    if not chunk:
                        break
                    modified_chunk = replace_bytes(chunk, target_bytes, replacement_bytes)
                    new_file.write(modified_chunk)
            os.replace(download_path + ".tmp", download_path)
            
    def _is_session_active(self, session, test_url):
        if not isinstance(session, requests.Session):
            print("El objeto sesión no es válido.")
            return False
        try:
            resp = session.head(test_url, timeout=30, verify=False)
            return resp.status_code in {200, 204} 
        except requests.exceptions.RequestException as ex:
            print(f"Error al verificar sesión: {ex}")
            return False

    def add_download(self, filename):
        """Muestra en la UI que un archivo ha sido agregado a la cola."""
        filet = filename
        if len(filet) > 25:
            filet = filename[:20] + "." + filename[-5:]
        file_status = ft.Text(f"📂 {filet} - Conectando...", size=16)
        self.download_list.controls.append(file_status)
        self.page.update()
        return file_status

    def update_download(self, filename, progress, downloaded_mb, total_mb):
        """Actualiza el estado de descarga con progreso y velocidad."""
        percentage = progress * 100
        downloaded_str = self.sizeof_fmt(downloaded_mb)
        total_str = self.sizeof_fmt(total_mb)  
        self.progress_bar.value = progress
        self.progress_text.value = f"{downloaded_str} / {total_str} ({percentage:.2f}%)"
        self.page.update()

    def complete_download(self, filename):
        """Marca la descarga como finalizada en la UI."""
        for text_control in self.download_list.controls:
            if text_control.value.startswith(f"📂 {filename}"):
                text_control.value = f"📂 {filename} - ✅Descarga Finalizada"
                text_control.update()
                self.page.update()  # 🔹 Asegurar actualización en Flet
                return

    def mostrar_error(self, mensaje):
        """Muestra un mensaje de error en la UI."""
        self.status_label.value = f"{mensaje}"
        self.page.update()

    def sizeof_fmt(self, num, suffix='B'):
        """Formatea el tamaño de los archivos en unidades legibles (KiB, MiB, GiB, etc.)."""
        for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
            if abs(num) < 1024.0:
                if unit in ['Gi', 'Ti', 'Pi', 'Ei', 'Zi']:  # Mostrar en GB con 3 decimales
                    return f"{num:.3f} Gi{suffix}"
                return f"{num:.2f} {unit}{suffix}"  # Espacio entre número y unidad
            num /= 1024.0
        return f"{num:.2f} Yi{suffix}"
    
def main(page: ft.Page):
    page.adaptive = True
    page.on_close = lambda _: sys.exit(0)  # Cierra la app correctamente
    page.title = "Down Free"
    page.scroll = "adaptive"
    page.window.width = 400 # Ajusta el ancho de la ventana
    page.window.height = 700 # Ajusta la altura de la ventana
    page.window.resizable = False  # Permite redimensionar la ventana
    page.update()
    Downloader(page)

ft.app(target=main)
