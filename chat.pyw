import Tkinter as tk     # python 2
from ScrolledText import ScrolledText
import ttk
import Queue
from passwd import *
from time import sleep
from threading import Thread
import logging
import sqlite3 as sql
import os, sys
from copy import copy
from argparse import ArgumentParser
import ConfigParser

def path_to_temp(relative_path):
    try:
        base_path = os.path.dirname(__file__)
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class Std_redirector():
    def __init__(self, widget):
        self.widget = widget

    def write(self,string):
        self.widget.write(string)


class ThreadSafeText(ScrolledText):
    def __init__(self, master, **options):
        ScrolledText.__init__(self, master, **options)
        self.queue = Queue.Queue()
        self.update_me()

    def write(self, line):
        self.queue.put(line)

    def update_me(self):
        while not self.queue.empty():
            line = self.queue.get_nowait()
            #self.delete(0.1,tk.END)
            self.insert(tk.END, line)
            self.see(tk.END)
            self.update_idletasks()
        self.after(10, self.update_me)


class App(tk.Tk):
    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)
        container = tk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        self.title('Chat')
        datafile = "assets/icon.ico"
        if not hasattr(sys, "frozen"):
            datafile = os.path.join(os.path.dirname(__file__), datafile)
        else:
            datafile = os.path.join(sys.prefix, datafile)
        self.iconbitmap(default=datafile)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        connect()

        self.frames = {}
        for F in (StartPage, Chat):
            page_name = F.__name__
            frame = F(parent=container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("StartPage")

    def show_frame(self, page_name):
        self.currentFrame = self.frames[page_name]
        self.currentFrame.tkraise()
        try:
            self.currentFrame.chSize()
        except:
            pass

    def popup(self, message):
        p = PopUpYN(self, message)
        self.wait_window(p.top)
        return p.returns

    def cancel(self, event=None):
        logger.info("Closed main window")
        try:
            self.currentFrame.end()
        except Exception as e:
            log.info(e.message)
        self.destroy()

class PopUpYN:
    def __init__(self, parent, message):
        top = self.top = tk.Toplevel(parent)
        self.parent = parent
        top.geometry("170x70")
        top.protocol("WM_DELETE_WINDOW", self.cancel)
        container = tk.Frame(top, bg="red")
        container.pack(side="top", fill="both", expand=True)

        tk.Label(container, text=message, fg="darkred").pack(side="top", fill="both", expand=True)
        for i in xrange(3):
            container.grid_rowconfigure(i, weight=1)
            container.grid_columnconfigure(i, weight=1)

        yes = tk.Button(container, text="Yes", command=self.yes)
        yes.pack(side="left", fill="both", expand=True)
        no = tk.Button(container, text="No", command=self.no)
        no.pack(side="right", fill="both", expand=True)

    def yes(self):
        self.returns = True
        logger.info("Deletion of account")
        self.top.destroy()

    def no(self):
        self.returns = False
        logger.info("Canceled deletion")
        self.top.destroy()

    def cancel(self, event=None):
        self.returns = False
        logger.info("Canceled deletion")
        self.parent.focus_set()
        self.top.destroy()


class StartPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.svn, self.svp = tk.StringVar(), tk.StringVar()
        self.name = tk.Entry(self, textvariable=self.svn)
        self.name.pack(side="top", fill="both", expand=True)
        self.passwd = tk.Entry(self, textvariable=self.svp, show='*')
        self.passwd.pack(fill="both", expand=True)
        self.passwd.bind('<Return>', self.submit)
        self.deleteAcc = tk.Label(self, text="Forgot password", fg="darkblue", font=("Courier", 8), cursor="hand2")
        self.deleteAcc.pack()
        self.deleteAcc.bind("<Button-1>", self.deleteCallback)
        self.submit = tk.Button(self, text='Submit', command=self.submit)
        self.submit.pack(side="bottom", fill="both", expand=True)

    def chSize(self):
        self.controller.geometry('170x90')

    def deleteCallback(self, event):
        logger.debug("Deletion requested")
        #TODO Deletion of account
        if self.controller.popup("This will delete yout account!\nAre you sure?"):
            logger.info("Deleting account")
            User.delete()
        else:
            pass


    def submit(self, *args):
        global usr
        try:
            nm = self.svn.get(); pw = self.svp.get()
            usr = User(nm, pw)
            self.controller.show_frame('Chat')
        except PasswordError as e:
            logging.warning("PasswordError: " + e.message)
            try:
                self.error.winfo_exists
            except AttributeError:
                self.error = tk.Label(self, text=e.message, fg='red')
                self.error.pack(side='bottom', fill='both', expand=True)
            if e.message == 'Created User':
                self.error.after(2000,lambda: self.controller.show_frame('Chat'))
                usr = User(nm, pw)


class Chat(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller

        self.grid(sticky='nesw')
        for i in xrange(1,4):
            self.grid_rowconfigure(i,weight=1); self.grid_columnconfigure(i,weight=1)

        #Writer
        self.msgsv = tk.StringVar()
        self.msgEntry = tk.Entry(self, textvariable=self.msgsv)
        self.msgEntry.grid(row=4,column=1,columnspan=3,sticky='news')
        self.msgEntry.bind('<Return>', self.sender)
        self.btns = tk.Button(self, text='Send',command=self.sender)
        self.btns.grid(row=4,column=4,sticky='news')

        #Reader
        self.text = ThreadSafeText(self)
        self.text.grid(row=1,column=1,rowspan=3,columnspan=4,sticky='news')
        sys.stdout = Std_redirector(self.text)
        self.thr = Thread(target=self.reader)
        self.thr.daemon = True
        self.text.after(1000,self.thr.start)

    def chSize(self):
        self.controller.geometry('600x400')
        self.send("[System]", usr.name + " logged on")

    def sender(self, *args):
        tmp = self.msgsv.get()
        if tmp:
            logging.info("Sending message: " + tmp)
            self.send(usr.name, tmp)
        self.msgEntry.delete(0,'end')
        del tmp

    def send(self, user, message):
        message.decode("utf-8", "ignore")
        cursor.execute("""
            INSERT INTO chat (msg_id, name, message)
            VALUES (NULL, "{}", "{}");
            """.format(user, message))
        connection.commit()

    def end(self):
        self.send("[System]", usr.name + " logged out")

    def reader(self):
        logging.info("Thread starting")
        res = ''
        tmp2 = None
        connect = sql.connect(path_to_temp('./assets/chat.db'))
        c = connect.cursor()
        while True:
            c.execute('SELECT name, message FROM chat ORDER BY msg_id ASC;')
            tmp = c.fetchall()
            if tmp != tmp2:
                logging.info("Loading new messages")
                tmp2 = copy(tmp)
                for i in tmp:
                    for b, n in enumerate(i):
                        n.encode('utf-8', 'ignore')
                        if b == 0:
                            res += '\n' + n + ': '
                        else:
                            res += n
                try:
                    self.text.delete(1.0,tk.END)
                except:
                    pass
                sys.stdout.write(res)
                res = ''
            sleep(0.5)


def connect():
    global connection, cursor
    connection = sql.connect(path_to_temp('assets/chat.db'))
    cursor = connection.cursor()

    command = """
    CREATE TABLE chat (
    msg_id INTEGER PRIMARY KEY,
    name VARCHAR(20),
    message VARCHAR(300));"""
    try:
        cursor.execute(command)
    except Exception as e:
        logging.error(e.message)

def init_logging(outputDir, consoleLevel):
    global logger
    if not os.path.exists(outputDir):
        os.makedirs(outputDir)
    logger = logging.getLogger()
    logger.setLevel(log.DEBUG)

    #Logging to console
    handler = logging.StreamHandler()
    handler.setLevel(consoleLevel.upper())
    formatter = logging.Formatter("[%(levelname)s] - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    #Error log file
    handler = logging.FileHandler(os.path.join(outputDir, getpass.getuser() + "_error.log"), "a", encoding=None, delay="true")
    handler.setLevel(logging.WARNING)
    formatter = logging.Formatter("%(asctime)s: [%(levelname)-7s] - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    #All logging
    handler = logging.FileHandler(os.path.join(outputDir, getpass.getuser() + "_all.log"), "a")
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s: [%(levelname)-7s] - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)


if __name__ == "__main__":
    init_logging("./assets/logs", "debug")

    parser = ArgumentParser(description="Chat application")
    parser.add_argument("-a", "--admin", help="Log in as admin, password required", action="store_true")
    args = parser.parse_args()
    if(args.admin):
        logger.warning("logging in as admin")

    config = ConfigParser.RawConfigParser()
    config.read("assets/config.ini")
    log.debug("Config loaded")

    app = App()
    app.mainloop()
