import pyperclip
import sqlite3

try:
    from Tkinter import *
    from ttk import *
except ImportError:  # Python 3
    from tkinter import *
    from tkinter.ttk import *
import tkMessageBox

TABLE = 'copybuf'
DATABASE = 'data.db'

def query(conn, c, query):
    c.execute(query)
    conn.commit()


class App(Frame):

    def __init__(self, parent, conn, c):
        Frame.__init__(self, parent, padding=6)
        self.parent = parent
        self.conn = conn
        self.c = c

        self.pack(expand=Y, fill=BOTH)

        self._sFrame = Frame(self)
        buf = Label(self._sFrame, text="Copy buffers and load them anytime.\nDouble-click to copy the buffer!",
                           justify='left', padding=6)
        self.status = Label(self._sFrame, text='', justify='left', padding=6)
        buf.pack(side=LEFT)
        self.status.pack(side=RIGHT)
        self._sFrame.pack(fill=BOTH)

        self._aFrame = Frame(self)
        self._aliasLabel = Label(self._aFrame, text="Alias: ", justify='left', padding=6)
        self._aliasEntryBox = Entry(self._aFrame, width=13, exportselection=True)
        self._entryLabel = Label(self._aFrame, text="Buffer: ", justify='left', padding=6)
        self._entryBox = Entry(self._aFrame, width=50)
        add_btn = Button(self._aFrame, text='Add', command=self.on_add, width=7)

        self._aliasLabel.pack(side=LEFT)
        self._aliasEntryBox.pack(side=LEFT)
        self._entryLabel.pack(side=LEFT)
        self._entryBox.pack(side=LEFT)
        add_btn.pack(side=LEFT)
        self._aFrame.pack(fill=BOTH)

        self._entryBox.bind('<Control-a>', self.callback)
        self._aliasEntryBox.bind('<Control-a>', self.callback)

        self._create_treeview(self)
        self.load_tree()

        self._cFrame = Frame(self)
        del_btn = Button(self._cFrame, text='Delete', command=self.on_delete, width=10)
        clear_btn = Button(self._cFrame, text='Clear', command=self.on_clear, width=10)
        clear_btn.pack(side=RIGHT)
        del_btn.pack(side=RIGHT)
        self._cFrame.pack(fill=BOTH, padx=20, pady=5)

    def _create_treeview(self, parent):
        f = Frame(parent, padding=6)
        f.pack(side=TOP, fill=BOTH, expand=Y)

        # create the tree and scrollbars
        self.dataCols = ('ID', 'Alias', 'Content')
        colWidth= [30, 90, 400]
        self.tree = Treeview(columns=self.dataCols, padding=4)

        ysb = Scrollbar(orient=VERTICAL, command= self.tree.yview)
        self.tree['yscroll'] = ysb.set
        self.tree['show'] = 'headings'

        for index, col in enumerate(self.dataCols):
            self.tree.heading(col,text=col,anchor='w')
            self.tree.column(col, anchor='w',stretch=NO, minwidth=0, width=colWidth[index])
            self.tree.heading(col, command=lambda col_= col: self.treeview_sort_column(self.tree, col_, False))

        # add tree and scrollbar to frame
        self.tree.grid(in_=f, row=0, column=0, sticky=NSEW)
        ysb.grid(in_=f, row=0, column=1, sticky=NS)

        # set frame resizing priorities
        f.rowconfigure(0, weight=1)
        f.columnconfigure(0, weight=1)
        self.tree.bind('<Double-1>', self.on_copy)

    def callback(self, event):
        self.after(0, self.select_all, event.widget)

    def select_all(self, widget):
        # select text
        widget.select_range(0, 'end')
        # move cursor to the end
        widget.icursor('end')

    def display_status(self, status):
        self.status.config(text=status)
        self.status.after(2500, self.clear_status)

    def clear_status(self):
        self.status.config(text='')

    def on_add(self, event=None):
        buf = self._entryBox.get()
        alias = self._aliasEntryBox.get()
        if not buf.strip() and not alias.strip():
            self.display_status('Nothing to Add!')
            return
        self.c.execute('insert into {}(alias, data) values (?, ?)'.format(TABLE), (alias, buf))
        self.conn.commit()
        self.load_tree()
        self.display_status('Added Data!')
        self._entryBox.delete(0, END)
        self._aliasEntryBox.delete(0, END)

    def on_copy(self, event):
        item = self.tree.selection()
        if not len(item):
            return
        item = item[0]

        bufnum = self.tree.item(item, "text")
        query(self.conn, self.c, 'select * from {} where id={}'.format(TABLE, bufnum))
        bufData = self.c.fetchone()[2]# 2 is data
        if bufData:
            pyperclip.copy(str(bufData))
            self.display_status('Copied Buffer!')

    def on_clear(self, event=None):
        result = tkMessageBox.askyesno("CopyBuf", "Would you like to Clear the Buffer?")
        if not result:
            return
        query(self.conn, self.c, 'delete from {}'.format(TABLE))
        self.load_tree()
        self.display_status('Cleared Buffer!')

    def on_delete(self):
        item = self.tree.selection()[0]
        bufnum = self.tree.item(item, "text")
        query(self.conn, self.c, 'delete from {} where id={}'.format(TABLE, bufnum))
        self.load_tree()
        self.display_status('Deleted Data!')

    def load_tree(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        query(self.conn, self.c, 'select * from {}'.format(TABLE))
        bufs = self.c.fetchall()
        for row_value in bufs:
            self.tree.insert('', 'end', text=row_value[0] ,values=tuple(row_value))


    def treeview_sort_column(self,tv, col, reverse):
        l = [(tv.set(k, col), k) for k in tv.get_children('')]
        try:
            l.sort(reverse=reverse, key=lambda orderForNums: int(orderForNums[0]))
        except:
            l.sort(reverse=reverse)
        # rearrange items in sorted positions
        for index, (val, k) in enumerate(l):
            tv.move(k, '', index)
        # reverse sort next time
        tv.heading(col,command=lambda: self.treeview_sort_column(tv, col, not reverse))

def main():
    # Connect to db
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    query(conn, c, 'CREATE TABLE IF NOT EXISTS {} (id INTEGER PRIMARY KEY AUTOINCREMENT, alias text, data text)'.format(TABLE))

    # GUI
    root = Tk()
    root.geometry('575x650')
    root.title("CopyBuf")
    App(root, conn, c)
    root.mainloop()

    # Close the cursor and connection
    c.close()
    conn.close()

if __name__ == '__main__':
    main()