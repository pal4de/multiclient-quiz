import socket
import threading


class QuizClient:
    PROMPT = '> '

    def __init__(self, host, port, max_message):
        self.host = host
        self.port = port
        self.max_message = max_message

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def __del__(self):
        self.socket.close()

    def run(self):
        try:
            self.socket.connect((self.host, self.port))
        except ConnectionError:
            print('サーバに接続できませんでした')
            exit('終了します')

        thread_arg = {
            'name': 'Server Listener',
            'target': self.td_listener,
            'daemon': True
        }
        threading.Thread(**thread_arg).start()

        try:
            self.send(input('名前を入力してください: '))
            while True:
                self.show_prompt()
                self.send(input())
        except KeyboardInterrupt:
            pass
        except ConnectionError:
            pass

        self.hide_prompt()
        exit('終了します')

    def td_listener(self):
        while True:
            try:
                text = self.socket.recv(self.max_message).decode('utf-8')
            except ConnectionError:
                exit('サーバが切断しました')

            self.hide_prompt()
            print(text, end='')
            self.show_prompt()

    def send(self, text):
        self.socket.send(text.encode('utf-8'))

    def show_prompt(self):
        print()
        print(self.PROMPT, end='', flush=True)

    def hide_prompt(self):
        backspace = '\b' * len(self.PROMPT)
        print(f'{backspace}', end='', flush=True)


if __name__ == '__main__':
    client_info = {
        'host': 'localhost',
        'port': 51001,
        'max_message': 2048,
    }
    QuizClient(**client_info).run()
