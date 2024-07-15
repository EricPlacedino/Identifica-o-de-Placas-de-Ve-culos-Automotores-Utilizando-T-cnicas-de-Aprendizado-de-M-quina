import threading
import cv2
import queue
import time
from ultralytics import YOLO
import pytesseract
import csv
from opcua import Server

class Captura_Frame(threading.Thread):
    def __init__(self, video) -> None:
        threading.Thread.__init__(self)
        self.ret = False
        self.resultado = []
        self.identificacao = []
        self.cont = 0
        self.habilita = False
        self.nome_arquivo = 'C:/Users/Administrador/Documents/Ambientes/TCC/Placas_Registradas.csv'
        self.video = video
        self.Cap = cv2.VideoCapture(self.video)
        self.Qframe = queue.Queue(2)
        Buffer = threading.Thread(target=self.img_buffer, args=(), name="rtsp_read_thread")
        Buffer.daemon = True
        self.Placa_deteccao = YOLO('C:/Users/Administrador/Documents/Ambientes/TCC/best.pt')
        self.custom_config = r'--oem 1 --psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-'
        pytesseract.pytesseract.tesseract_cmd = 'C:\Program Files\Tesseract-OCR\Tesseract.exe'
        Buffer.start()
        server = Server()
        server.set_endpoint("opc.tcp://192.168.18.1:4840/freeopcua/server/")
        objects = server.register_namespace("MeuNomeDeRegistro")
        self.node_boolean = server.nodes.objects.add_variable(objects, "MinhaVariavelBooleana", False)
        self.node_string = server.nodes.objects.add_variable(objects, "MinhaVariavelString", "")
        server.start()
        self.boxes = []
        thread = threading.Thread(target=self.show_frames_with_boxes, args=())
        thread.start()

    def run(self):
        while True:
            if self.Cap.isOpened():
                if self.ret:
                    if not self.habilita:
                        self.deteccao(self.Qframe.get())
                        valor_string, valor_booleano = self.comparar_csv(self.nome_arquivo,  self.resultado)
                    else:
                        self.cont += 1
                    if valor_booleano:
                        self.habilita = True
                    if self.cont == 10:
                        self.cont = 0
                        self.habilita = False
                    self.node_boolean.set_value(valor_booleano)
                    self.node_string.set_value(valor_string)
                    self.identificacao = self.resultado
                    print(self.resultado)
                    time.sleep(1)

    def img_buffer(self):
        while True:
            if self.Cap.isOpened():
                self.ret, self.frame = self.Cap.read()
                if self.ret:
                    self.Qframe.put(self.frame)
                if self.Qframe.full():
                    self.Qframe.get()
            else:
                if not self.Qframe.empty():
                    self.Qframe.get()
                time.sleep(0.2)

    def deteccao(self, imagem):
        self.resultado.clear()
        placas = self.Placa_deteccao(imagem)[0]
        for placa in placas.boxes.data.tolist():
            x1, y1, x2, y2, score, class_id = placa
            self.boxes = [(x1, y1, x2, y2)]
            placa_cortada = imagem[int(y1):int(y2), int(x1):int(x2), :]
            self.resultado.append(pytesseract.image_to_string(placa_cortada, config = self.custom_config))

    def ler_csv(self, nome_arquivo):
        dados = []
        with open(nome_arquivo, 'r', encoding='utf-8') as arquivo:
            leitor_csv = csv.reader(arquivo)
            for linha in leitor_csv:
                dados.append(linha)
        return dados

    def comparar_csv(self, nome_arquivo, lista):
        deteccao = False
        placa = ''
        dados_csv = self.ler_csv(nome_arquivo)
        for linha in dados_csv:
            for elemento in linha:
                if str(elemento) in str(lista):
                    deteccao = True
                    placa = elemento
        return placa, deteccao

    def show_frames_with_boxes(self):
        while True:
            for (box, label) in zip(self.boxes, self.identificacao):
                x1, y1, x2, y2 = map(int, box)
                ident = label.strip()
                if self.habilita:
                    cor = (0,0,255)
                else:
                    cor = (0,255,0)
                cv2.rectangle(self.frame, (x1, y1), (x2, y2), cor, 2)
                cv2.putText(self.frame, ident, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, cor, 2)
            cv2.imshow('Frame with Boxes', self.frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        cv2.destroyAllWindows()