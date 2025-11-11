# app.py
import cv2
import mediapipe as mp
import pyttsx3
import threading
import time
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import math

# -------------------------
# CONFIGURACIÓN INICIAL
# -------------------------
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine_lock = threading.Lock()

def speak(text):
    """Pronuncia texto con pyttsx3 en hilo separado."""
    def _s():
        with engine_lock:
            engine.say(text)
            engine.runAndWait()
    t = threading.Thread(target=_s, daemon=True)
    t.start()

# -------------------------
# DETECCIÓN DE SEÑAS
# -------------------------
def detect_sign(hand_landmarks):
    if not hand_landmarks or len(hand_landmarks.landmark) < 21:
        return None

    finger_tips = [4, 8, 12, 16, 20]
    finger_bases = [3, 6, 10, 14, 18]
    fingers_up = []

    # Pulgar (horizontal)
    if hand_landmarks.landmark[finger_tips[0]].x < hand_landmarks.landmark[finger_bases[0]].x:
        fingers_up.append(1)
    else:
        fingers_up.append(0)

    # Dedos restantes (verticales)
    for i in range(1, 5):
        if hand_landmarks.landmark[finger_tips[i]].y < hand_landmarks.landmark[finger_bases[i]].y:
            fingers_up.append(1)
        else:
            fingers_up.append(0)

    if len(fingers_up) < 5:
        return None

    # Clasificación básica
    if fingers_up[1:] == [1, 1, 1, 1] and fingers_up[0] == 0:
        return "HOLA 👋"
    elif fingers_up == [0, 0, 0, 0, 0]:
        return "ADIÓS 👋"
    elif fingers_up == [1, 1, 0, 0, 1]:
        return "OK 👍"
    else:
        return None

# -------------------------
# INTERFAZ PRINCIPAL
# -------------------------
class MainApp:
    def __init__(self, window, window_title):
        self.window = window
        self.window.title(window_title)
        self.window.geometry("800x600")
        self.window.configure(bg="#1e1e2f")

        # Centrar ventana
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")

        self.mode = tk.StringVar(value="voz")
        self.running = False
        self.last_sign = ""
        self.last_time = 0

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton",
                        font=("Segoe UI", 11, "bold"),
                        padding=6,
                        background="#2e2e4f",
                        foreground="white")
        style.map("TButton", background=[("active", "#414168")])
        style.configure("TRadiobutton",
                        background="#1e1e2f",
                        foreground="white",
                        font=("Segoe UI", 10))

        title = tk.Label(window, text="🤟 SignVoice AI",
                         font=("Segoe UI", 24, "bold"),
                         fg="white", bg="#1e1e2f")
        title.pack(pady=10)

        subtitle = tk.Label(window, text="Traductor de Lengua de Señas Colombiana",
                            font=("Segoe UI", 12),
                            fg="#b0b0c3", bg="#1e1e2f")
        subtitle.pack()

        frame_container = tk.Frame(window, bg="#252547", bd=2, relief="ridge")
        frame_container.pack(pady=15)
        self.video_label = tk.Label(frame_container, bg="#252547")
        self.video_label.pack()

        controls = tk.Frame(window, bg="#1e1e2f")
        controls.pack(pady=10)

        self.start_btn = ttk.Button(controls, text="▶ Iniciar cámara", command=self.start_camera)
        self.start_btn.grid(row=0, column=0, padx=10)

        self.stop_btn = ttk.Button(controls, text="⏹ Detener", command=self.stop_camera, state="disabled")
        self.stop_btn.grid(row=0, column=1, padx=10)

        ttk.Radiobutton(controls, text="Voz", variable=self.mode, value="voz").grid(row=0, column=2, padx=10)
        ttk.Radiobutton(controls, text="Texto", variable=self.mode, value="texto").grid(row=0, column=3, padx=10)

        self.label_result = tk.Label(window, text="Seña detectada: —",
                                     font=("Segoe UI", 16, "bold"),
                                     fg="#00ffaa", bg="#1e1e2f")
        self.label_result.pack(pady=10)

        hint = tk.Label(window, text="💡 Consejo: Usa buena iluminación y coloca tu mano frente a la cámara.",
                        font=("Segoe UI", 10),
                        fg="#8888aa", bg="#1e1e2f")
        hint.pack(pady=(0, 10))

        self.mp_hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.7)
        self.cap = None
        self.thread = None
        self.window.protocol("WM_DELETE_WINDOW", self._on_closing)

    def start_camera(self):
        if self.running:
            return
        self.cap = cv2.VideoCapture(0)
        self.running = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.thread = threading.Thread(target=self._camera_loop, daemon=True)
        self.thread.start()

    def stop_camera(self):
        self.running = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

    def _camera_loop(self):
        while self.running and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                break
            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.mp_hands.process(rgb)
            sign_text = None

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                    s = detect_sign(hand_landmarks)
                    if s:
                        sign_text = s
                        break

            now = time.time()
            if sign_text and sign_text != self.last_sign and now - self.last_time > 1:
                self.last_sign = sign_text
                self.last_time = now
                if self.mode.get() == "voz":
                    speak(sign_text)
                self.label_result.config(text=f"Seña detectada: {sign_text}")
            elif not sign_text:
                self.label_result.config(text="Seña detectada: —")

            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            imgtk = ImageTk.PhotoImage(image=img)
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)

        if self.cap:
            self.cap.release()
        self.running = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

    def _on_closing(self):
        self.stop_camera()
        time.sleep(0.2)
        try:
            self.window.destroy()
        except:
            pass

# -------------------------
# SPLASH SCREEN ANIMADO
# -------------------------
class SplashScreen(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Cargando...")
        self.geometry("500x350")
        self.configure(bg="#1e1e2f")
        self.overrideredirect(True)

        # Centrar
        x = (self.winfo_screenwidth() // 2) - 250
        y = (self.winfo_screenheight() // 2) - 175
        self.geometry(f"500x350+{x}+{y}")

        tk.Label(self, text="🤟 SignVoice AI",
                 font=("Segoe UI", 26, "bold"), fg="white", bg="#1e1e2f").pack(pady=40)

        tk.Label(self, text="Iniciando traductor de señas...",
                 font=("Segoe UI", 12), fg="#b0b0c3", bg="#1e1e2f").pack(pady=10)

        self.canvas = tk.Canvas(self, width=120, height=120, bg="#1e1e2f", highlightthickness=0)
        self.canvas.pack(pady=30)
        self.angle = 0
        self.animate()

        # Mostrar pantalla principal luego de 3 segundos
        self.after(3000, self.launch_main)

    def animate(self):
        self.canvas.delete("all")
        x, y, r = 60, 60, 40
        for i in range(12):
            a = math.radians(i * 30 + self.angle)
            x1 = x + r * math.cos(a)
            y1 = y + r * math.sin(a)
            color = f"#{int(255 - i * 15):02x}{int(255 - i * 10):02x}ff"
            self.canvas.create_oval(x1-6, y1-6, x1+6, y1+6, fill=color, outline=color)
        self.angle += 30
        self.after(100, self.animate)

    def launch_main(self):
        self.destroy()
        root = tk.Tk()
        app = MainApp(root, "SignVoice AI - Traductor de Lengua de Señas")
        root.mainloop()

# -------------------------
# EJECUTAR APP CON SPLASH
# -------------------------
if __name__ == "__main__":
    splash = SplashScreen()
    splash.mainloop()
