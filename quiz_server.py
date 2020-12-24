import os
import random
import socket
import threading
import csv
import textwrap
import typing


def heredoc(text: str):
    return textwrap.dedent(text).strip()


class Client:
    clients_list: typing.List['Client'] = []

    def __init__(self, conn: socket.socket, addr, max_message: int):
        self.conn = conn
        self.addr = addr
        self.max_message = max_message

        self.name = self.receive()
        self.point = 0
        Client.clients_list.append(self)

    def __del__(self):
        self.conn.close()

    def __str__(self) -> str:
        return f'{self.name} {self.addr}'

    @classmethod
    def broadcast(cls, text=''):
        for client in Client.clients_list:
            client.send(text)

    @classmethod
    def get_scoreboard(cls) -> str:
        lines = list()
        for client in cls.clients_list:
            lines.append(f'{client.name}: {client.point} pt')
        return '\n'.join(lines)

    def send(self, text=''):
        self.conn.send(f'{text}\n'.encode('utf-8'))

    def send_others(self, text=''):
        for client in Client.clients_list:
            if client is not self:
                client.send(text)

    def receive(self) -> str:
        return self.conn.recv(self.max_message).decode('utf-8')

    def close(self):
        Client.clients_list.remove(self)

    def add_point(self, point=1):
        self.point += point


class Quiz:
    def __init__(self, quiz: str, answer: str):
        self.quiz = quiz
        self.answer = answer

    def __str__(self) -> str:
        return self.quiz

    def abstract(self) -> str:
        result = self.quiz.replace('\n', ' ')[:27]
        if self.quiz[27:]:
            result += '...'
        return result


class QuizServer:
    PROMPT = '> '

    def __init__(self, host, port, max_message, num_thread):
        self.host = host
        self.port = port
        self.max_message = max_message
        self.num_thread = num_thread
        self.quiz_list: typing.List[Quiz] = []

        self.is_preparing = True
        self.current_quiz: Quiz = None

    def show_prompt(self):
        print()
        print(self.PROMPT, end='', flush=True)

    def hide_prompt(self):
        backspace = '\b' * len(self.PROMPT)
        print(f'{backspace}', end='', flush=True)

    def log(self, text: str):
        if self.is_preparing:
            self.hide_prompt()
            print(text)
            self.show_prompt()
        else:
            print(text)

    def run(self):
        try:
            thread_arg = {
                'name': 'Receptionist',
                'target': self.td_receptionist,
                'daemon': True
            }
            threading.Thread(**thread_arg).start()

            self.preparing_mode()
            Client.broadcast('クイズ大会を開始します')
            Client.broadcast()
            self.next_quiz()
            while True:
                input()  # Ctrl-C用

        except KeyboardInterrupt:
            pass

        exit('終了します')

    def td_receptionist(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((self.host, self.port))
            sock.listen(self.num_thread)

            while True:
                conn, addr = sock.accept()
                client = Client(conn, addr, self.max_message)
                thread_arg = {
                    'name': f'Client Listener ({client})',
                    'target': self.td_client_handler,
                    'args': (client,),
                    'daemon': True
                }
                threading.Thread(**thread_arg).start()

    def td_client_handler(self, client: Client):
        try:
            self.log(f'接続: {client}')
            client.send_others(f'接続: {client.name}')
            client.send(f'{client.name}さん、こんにちは')

            if self.is_preparing:
                client.send('ゲームの準備中です')
                client.send('開始までしばらくお待ちください')

            while True:
                answer = client.receive()
                Client.broadcast(f'{client.name}: {answer}')

                if self.is_preparing:
                    continue

                if answer == self.current_quiz.answer:
                    Client.broadcast('正解！')
                    client.add_point()
                    self.next_quiz()

        except ConnectionError:
            self.log(f'切断: {client}')
            client.send_others(f'切断: {client.name}')
            client.close()
            return

    def next_quiz(self):
        Client.broadcast(Client.get_scoreboard())
        Client.broadcast()

        self.current_quiz = random.choice(self.quiz_list)
        Client.broadcast('[問題]')
        Client.broadcast(self.current_quiz)

    def preparing_mode(self):
        def cmd_start(*args):
            if not self.quiz_list:
                print('エラー: 問題が登録されていません')
            else:
                print('クイズ大会を開始します')
                self.is_preparing = False

        def cmd_add(*args):
            print('[問題文を入力] (改行2回で終了)')
            quiz = ''
            while True:
                quiz_line = input()
                quiz += quiz_line + '\n'
                if not quiz_line:
                    break
            quiz = quiz.strip()
            answer = input('解答を入力: ')
            self.quiz_list.append(Quiz(quiz, answer))
            print('問題を追加しました')

        def cmd_remove(*args):
            args = list(args)

            if not cmd_list():
                return

            while True:
                try:
                    if args:
                        n = int(args.pop(0))
                    else:
                        n = int(input('削除する問題番号を入力 (範囲外で中止): ')) - 1
                    break
                except ValueError:
                    continue
            if 0 <= n < len(self.quiz_list):
                self.quiz_list.pop(n)
                print('問題を削除しました')
            else:
                print('削除を中止しました')

        def cmd_list(*args) -> bool:
            if not self.quiz_list:
                print('問題が登録されていません')
                return False

            for i, quiz in enumerate(self.quiz_list):
                print(f'{i+1}: {quiz.abstract()}')
            return True

        def cmd_load(*args):
            args = list(args)
            if args:
                filename = args.pop(0)
            else:
                print(f'現在の場所: {os.getcwd()}')
                filename = input('ファイル名を入力: ')

            try:
                file_options = {
                    'mode': 'r',
                    'encoding': 'utf_8',
                    'newline': '\n'
                }
                with open(filename, **file_options) as f:
                    print(f'読込元: {os.path.abspath(f.name)}')
                    reader = csv.reader(f)
                    for entry in reader:
                        if entry:
                            quiz = Quiz(*entry)
                            self.quiz_list.append(quiz)
                print('読み込みに成功しました')
            except FileNotFoundError:
                print('エラー: ファイルが見つかりませんでした')
            except IsADirectoryError:
                print('エラー: 指定された項目はディレクトリです')
            except csv.Error:
                print('エラー: 無効なCSVファイルです')

        def cmd_save(*args):
            args = list(args)
            if args:
                filename = args.pop(0)
            else:
                print(f'現在の場所: {os.getcwd()}')
                filename = input('ファイル名を入力: ')

            if os.path.exists(filename):
                print('警告: 既存のファイルです')
                while True:
                    if args:
                        is_ok = args.pop(0)
                    else:
                        is_ok = input('保存を続行しますか？ ([y], n): ')

                    if is_ok == 'y' or not is_ok:
                        break
                    elif is_ok == 'n':
                        return
                    else:
                        continue
            try:
                file_options = {
                    'mode': 'w',
                    'encoding': 'utf_8',
                    'newline': '\n'
                }
                with open(filename, **file_options) as f:
                    writer = csv.writer(f, lineterminator='\n')
                    for quiz in self.quiz_list:
                        writer.writerow((quiz.quiz, quiz.answer))
                    print('保存に成功しました')
                    print(f'保存先: {os.path.abspath(f.name)}')
            except IsADirectoryError:
                print('エラー: 指定の保存先は既存のディレクトリです')

        def cmd_help(*args, additional=True):
            print(heredoc('''
                [コマンド一覧]
                add    問題を追加する
                remove 問題を削除する
                list   問題の一覧を表示する
                load   問題をファイルから読み込む
                save   問題をファイルに保存する
                help   コマンド一覧を表示する
                start  クイズ大会を開始する
            '''))
            if additional:
                print()
                print(heredoc('''
                    コマンドは対話的に処理されます
                    remove, load, saveは引数による非対話的な処理に対応しています
                    Ctrl-Cで終了します
                '''))

        commands_list = {
            'start': cmd_start,
            'add': cmd_add,
            'remove': cmd_remove,
            'list': cmd_list,
            'load': cmd_load,
            'save': cmd_save,
            'help': cmd_help,
        }

        self.is_preparing = True

        print('クイズ大会の準備を行います')
        print()
        cmd_help(True)

        while self.is_preparing:
            print()
            self.show_prompt()
            command_name, *command_args = input().split()
            if command_name in commands_list:
                commands_list[command_name](*command_args)
            else:
                print('無効なコマンドです')
                cmd_help(additional=False)


if __name__ == '__main__':
    server_info = {
        'host': 'localhost',
        'port': 51001,
        'max_message': 2048,
        'num_thread': 4,
    }
    QuizServer(**server_info).run()
