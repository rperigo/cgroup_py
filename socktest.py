import os, sys, socket

S_ADDR = "./test_socketfile"

try:
    os.unlink(S_ADDR)
except OSError:
    if os.path.exists(S_ADDR):
        print "Socket exists, cannot create!"
        sys.exit(2)

sox = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

sox.bind(S_ADDR)

while True:
    sox.listen(5)
    conn, cli = sox.accept()
    dat = ""
    while dat != "exit":
        dat = conn.recv(1024)
        spdat = dat.split(' ')
        if spdat[0] == "show":
            try:
                if spdat[1] == "me":
                    conn.sendall("The MONEY")
                elif spdat[1] == "time":
                    conn.sendall("It's like HBO but shitty!")
                elif spdat[1] == "stopper":
                    conn.sendall("Shut up, Marv Albert.")
            except IndexError:
                conn.sendall("Show what?")


        conn.sendall(dat