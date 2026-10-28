# cliente_base.py
import socket
import json
import threading
import time

class ClienteBase:
    """
    Clase base que maneja la comunicación de red para cualquier tipo de cliente.
    """
    def __init__(self, host='localhost', port=5555):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        self.player_color = None
        self.game_state = None
        self.connection_status = "Desconectado"
        self.waiting_for_opponent = True
        self.on_message_received = None # Callback para manejar mensajes

    def connect(self):
        try:
            self.connection_status = "Conectando..."
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            self.connection_status = "Conectado"
            print("✅ ¡Conectado al servidor!")

            receive_thread = threading.Thread(target=self.receive_messages)
            receive_thread.daemon = True
            receive_thread.start()
            return True
        except Exception as e:
            self.connection_status = f"Error: {e}"
            print(f"❌ Error de conexión: {e}")
            return False

    def receive_messages(self):
        buffer = ""
        while self.connected:
            try:
                data = self.socket.recv(4096).decode('utf-8')
                if not data:
                    self.disconnect("Servidor cerró la conexión")
                    break
                buffer += data
                while '\n' in buffer:
                    message_str, buffer = buffer.split('\n', 1)
                    if message_str.strip():
                        message = json.loads(message_str)
                        self.handle_message(message)
            except (ConnectionResetError, BrokenPipeError):
                self.disconnect("Conexión perdida")
                break
            except Exception as e:
                if self.connected:
                    print(f"❌ Error recibiendo datos: {e}")
                break

    def handle_message(self, message):
        msg_type = message.get('type')
        print(f"📨 Mensaje recibido: {msg_type}")

        if msg_type == 'welcome':
            self.player_color = message['player_color']
            color_str = "Negro" if self.player_color == 1 else "Blanco"
            self.connection_status = f"Conectado como Jugador {color_str}"
            self.waiting_for_opponent = True
        elif msg_type == 'waiting':
            self.waiting_for_opponent = True
        elif msg_type in ['game_start', 'game_update']:
            self.game_state = message['game_state']
            self.waiting_for_opponent = False
        elif msg_type == 'opponent_disconnected':
            self.waiting_for_opponent = True
            self.connection_status = "Oponente desconectado"
        
        # Llama al callback si está definido, para que las subclases puedan reaccionar
        if self.on_message_received:
            self.on_message_received(message)

    def send_message(self, message):
        if not self.connected:
            return False
        try:
            message_str = json.dumps(message) + '\n'
            self.socket.sendall(message_str.encode('utf-8'))
            return True
        except Exception as e:
            self.disconnect(f"Error enviando mensaje: {e}")
            return False

    def send_move(self, row, col):
        print(f"✈️  Enviando movimiento: ({row}, {col})")
        return self.send_message({'type': 'move', 'row': int(row), 'col': int(col)})

    def disconnect(self, reason=""):
        if self.connected:
            self.connected = False
            self.connection_status = f"Desconectado ({reason})"
            print(f"🔌 {self.connection_status}")
            if self.socket:
                try:
                    self.socket.shutdown(socket.SHUT_RDWR)
                    self.socket.close()
                except OSError:
                    pass
            self.socket = None