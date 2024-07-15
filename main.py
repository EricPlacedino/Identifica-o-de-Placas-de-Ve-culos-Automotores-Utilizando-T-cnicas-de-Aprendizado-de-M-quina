from Thread import *

def main():
    Camera = Captura_Frame('http://192.168.173.18:8080/video')
    Camera.start()

if __name__ == '__main__':
    main()