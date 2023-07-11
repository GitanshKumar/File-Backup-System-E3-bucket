import boto3, threading, sys, os, tkinter as tk
from PyQt5.QtWidgets import QApplication, QMenu, QSystemTrayIcon
from PyQt5.QtGui import QIcon
from tkinter import ttk, filedialog
from datetime import timedelta, datetime


access_key = "AKIA2ZFOWQQUWCERQYXU"
secret_key = "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"

class FBS3:
    def __init__(self, access_key:str, secret_key:str) -> None:
        #set the access key for aws e3 authentication
        self.access_key = access_key
        self.secret_key = secret_key

        #path to the directories
        self.dirs_path = os.path.join(os.getcwd(), "FBS/directories.txt")
        
        #contians the list of all the directories 
        self.directories = open(self.dirs_path, "r").readlines()
        self.path_to_icon = os.path.join(os.getcwd(), "FBS/icon.png")
        
        #flag used to check the status of GUI(tk window)
        self.ui_state = "running"
        
        #flag to check whether bucket is connected or not
        self.bucket_connected = False

        #initialize tkinter window
        self.win = tk.Tk()
        self.win.geometry("450x210")
        self.win.resizable(False, False)
        self.win.title("FBS3")
        self.win.iconphoto(False, tk.PhotoImage(file= self.path_to_icon))
        self.win.protocol("WM_DELETE_WINDOW", lambda: self.set_ui_state("closed"))

        self.days = tk.IntVar(value= 1)
        self.bucket_name = tk.StringVar()
        
        #create s3 object which will be used to connect to the bucket later
        self.s3 = boto3.resource('s3'
                            , region_name= "us-east-1"
                            , aws_access_key_id = self.access_key
                            , aws_secret_access_key = self.secret_key
                            )

        
        self.main_menu()
        now = datetime.now()

        #schedule a thread to execute backup at valid time
        self.next_backup = (timedelta(hours=24) - (now - now.replace(hour=2, minute=0, second=0, microsecond=0))).total_seconds() % (24 * 3600)
        self.timer = threading.Timer(self.next_backup, self.schedule_backup)
        self.timer.start()
        self.win.mainloop()
        
        #initialize the tray icon
        self.tray_icon()

    def connect_bucket(self, bucket_name: tk.StringVar):
        """Function used to connect to bucket"""

        #check whether the bucket exists
        if not self.s3.Bucket(bucket_name.get()).creation_date:
            bucket_name.set("Bucket does not exist!")
        else:
            #connect to the bucket
            self.bucket = self.s3.Bucket(bucket_name.get())
            self.bucket_name.set(bucket_name.get())
            self.bucket_connected = True
            self.access_panel()
    
    def upload(self, popup: tk.Toplevel, info_label: tk.Label, dirs: list[str]):
        """To upload a multiple directories on S3 bucket
        popup: to show file status on a popup
        info_label: the label on the popup which actually shows the content
        dirs: the list of directories to be uploaded on AWS
        """
        #loop over the target directories
        for directory in dirs:
            directory = directory.strip()
            
            #extract the folder name from the directory, it is used to distinguish a directory from other directories
            folder_name = directory.split("/")[-1]
            uploaded = file_count = 0

            #count the number of files in the current directory
            for root, dirss, files in os.walk(directory): #os.walk walks through all the files and subfolders
                for file in files:
                    file_count += 1
            
            #again loop over all the files in the current directory
            for root, dirss, files in os.walk(directory):
                for file in files:
                    #local_path is the full address to the file present in the current directory
                    local_path = os.path.join(root, file)

                    #remove the original directory and keep only the part from the folder
                    #example- C:/Users/you/Desktop/upload_folder/file1 -> upload_folder/file1
                    s3_path = os.path.join(folder_name + root.replace(directory, ''), file)

                    #update the GUI
                    info_label["text"] = f"{uploaded + 1}/{file_count} Uploading: " + s3_path
                    popup.update()

                    #upload the file with filename(complete local address to the file) and key(set the name of the file in S3 bucket)
                    self.bucket.upload_file(Filename= local_path, Key= s3_path)
                    uploaded += 1
        
        info_label["text"] = "Successfully Uploaded All files, You can close this window"
        popup.update()
    
    def download(self, popup: tk.Toplevel, info_label: tk.Label, download_dir: str):
        """To download data from S3 bucket
        popup: to show file status on a popup
        info_label: the label on the popup which actually shows the content
        download_dir: the directory whete the downloaded files will be stored
        """
        downloaded = 0
        #loop over all the objects(files) in the bucket
        for obj in self.bucket.objects.all():
            
            #create a directory for the file to be downloaded
            file_dir = os.path.dirname(obj.key) #obj.key gives the name of file as shown on S3 bucket

            #check if there is a path from download_dir to file_dir, if not the create that path
            if not os.path.exists(os.path.join(download_dir, file_dir)):
                os.makedirs(os.path.join(download_dir, file_dir))
            
            #the complete address of where the file will be downloaded
            file_path = os.path.join(download_dir, obj.key)

            #update the GUI
            info_label["text"] = f"{downloaded + 1}/{self.total_objs} Downloading: " + obj.key
            popup.update()

            #download the file with name obj.key to file_path(complete address)
            self.bucket.download_file(obj.key, file_path)
            downloaded += 1
        
        info_label["text"] = "Downloaded All, You can close this window"
        popup.update()
    
    def schedule_backup(self):
        """Schedule a backup, automatically called when class object is created on a different thread."""
        loading_win = tk.Tk()
        loading_win.geometry("400x50")
        
        tk.Label(loading_win, text= "Backing up files").place(x= 200, y= 10, anchor= "center")
        info = tk.Label(loading_win, text="sample")
        info.place(x= 10, y = 20)
        
        self.upload(loading_win, info, self.directories)

    def set_ui_state(self, state):
        """To update the state of the GUi, created for smooth termination of the program"""
        self.ui_state = state
        if state == "closed":
            self.win.destroy()
    
    def buildUI(self):
        """Create the basic pre-requisites for the main UI"""
        self.win = tk.Tk()
        self.win.geometry("450x210")
        self.win.resizable(False, False)
        self.win.title("FBS3")
        self.win.iconphoto(False, tk.PhotoImage(file= self.path_to_icon))
        self.win.protocol("WM_DELETE_WINDOW", lambda: self.set_ui_state("closed"))
        self.ui_state = "running"

        if not self.bucket_connected: self.main_menu() #show the main window to connect to the bucket if bucket is not connect
        else: self.access_panel() #show the access panel with options like download and upload, if the bucket is connected
        self.win.mainloop()
    
    def main_menu(self):
        """Main window screen UI design"""
        for child in self.win.winfo_children():
            child.destroy()
        self.win.geometry("450x210")

        tk.Label(self.win, text= "Welcome to FBS3", font=('Helvetica bold', 26)).place(x= 225, y = 30, anchor= "center")

        self.bucket_name = tk.StringVar()
        tk.Label(self.win, text= "Enter Bucket name: ", font= ('Helvetica bold', 12)).place(x= 100, y= 100, anchor = "center")
        tk.Entry(self.win, textvariable= self.bucket_name, font= ('Helvetica bold', 12)).place(x= 300, y= 100, anchor= "center")
        
        ttk.Button(self.win, text= "Submit", command= lambda: self.connect_bucket(self.bucket_name)).place(x= 200, y= 180, anchor= "center")
    
    def access_panel(self):
        """To show the main options of the program"""
        for child in self.win.winfo_children():
            child.destroy()
        self.win.geometry("450x210")
        
        #call show_dirs to add or delete a directory, and to backup a directory or all the directories
        ttk.Button(self.win, text= "Backup Directories", command= self.show_dirs, width= 50).place(x= 225, y= 50, anchor= "center")

        #call show_files to see uploaded files in the bucket, can also be used to delete or download a file
        ttk.Button(self.win, text= "See Backed up Files", command= self.show_files, width= 50).place(x= 225, y= 100, anchor= "center")

        #call the settings menu
        ttk.Button(self.win, text= "Settings", command= self.settings, width= 50).place(x= 225, y= 150, anchor= "center")

    def show_dirs(self):
        for child in self.win.winfo_children():
            child.destroy()
        self.win.geometry("625x210")
        ttk.Button(self.win, text= "Back", command= self.access_panel).place(x= 0, y= 0)

        def add():
            #add a new directory to the list of backup directories
            open(self.dirs_path, "a").write(filedialog.askdirectory() + "\n")
            self.directories = open(self.dirs_path, "r").readlines()
            self.show_dirs()
        
        def delete():
            #delete the selected directory
            if not tree.selection(): return
            for selected in tree.selection():
                self.directories.remove(tree.item(selected)["text"])
                tree.delete(selected)
            
            open(self.dirs_path, "w").writelines(self.directories)
        
        def perform_backup(all: bool):
            """Used to perform backup of a directory or all the available directories
            all: bool: whether to upload all directories or a single directory"""

            #set up a popup to show uploading status
            loading_win = tk.Toplevel(self.win)
            loading_win.resizable(False, False)
            loading_win.geometry("400x50")
            if not tree.selection() and not all:
                tk.Label(loading_win, text="Please select a target Directory", font= ("Helvetica", 14)).place(x= 150, y = 50, anchor= "center")
                return
            
            tk.Label(loading_win, text= "Backing up files").place(x= 200, y= 10, anchor= "center")
            info = tk.Label(loading_win, text="")
            info.place(x= 10, y = 20)
            
            if not all:
                #call upload to upload the file in the selected directory
                self.upload(loading_win, info, [tree.item(tree.selection()[0])["text"]])
            else:
                #call the upload on all the available directories
                self.upload(loading_win, info, self.directories)

        tk.Label(self.win, text= "Directories", font=('Helvetica bold', 20)).place(x= 300, y = 20, anchor= "center")
        
        #set up the tree to show the list of directories
        tree = ttk.Treeview(self.win, height= 5)
        tree.place(x= 10, y= 50)
        tree.heading("#0", text= "Dirs")
        tree.column("#0", width= 500, stretch= tk.NO)
        for directory in self.directories:
            tree.insert("", tk.END, text= directory)
        
        #buttons to perform thier respective functions
        ttk.Button(self.win, text= "Add", command= add, width= 12).place(x= 515, y= 50)
        ttk.Button(self.win, text= "Delete", command= delete, width= 12).place(x= 515, y= 80)
        ttk.Button(self.win, text= "Backup Now", command= lambda: perform_backup(0), width= 12).place(x= 515, y= 110)
        ttk.Button(self.win, text= "Backup All", command= lambda: perform_backup(1), width= 12).place(x= 515, y= 140)
    
    def show_files(self):
        """To show the files in the S3 bucket"""
        for child in self.win.winfo_children():
            child.destroy()
        self.win.geometry("625x400")
        ttk.Button(self.win, text= "Back", command= self.access_panel).place(x= 0, y= 0)

        tk.Label(self.win, text= "Files", font=('Helvetica bold', 20)).place(x= 300, y = 20, anchor= "center")
        
        def delete():
            """deletes the selected files or file"""

            #check whether at least one item is selected
            if not tree.selection(): return
            items = tree.selection()
            #iterate over the selected items and delete from the bucket
            for selected in items:
                file_obj = self.s3.Object(self.bucket_name.get(), tree.item(selected)["text"])
                file_obj.delete() #removes from the bucket
                self.total_objs -= 1
                tree.delete(selected) #removes from the tree
        
        def download_one():
            """Download a single file from the bucket"""
            if not tree.selection(): return
            #prompt the user to select the download directory
            download_path =  os.path.join(filedialog.askdirectory(), tree.item(tree.selection()[0])["text"].split("\\")[-1])

            #download the selecred file to the download path
            self.bucket.download_file(tree.item(tree.selection()[0])["text"], download_path)

            #inform the user for successfull download
            success = tk.Toplevel(self.win)
            success.geometry("200x50")
            success.resizable(False, False)
            tk.Label(success, text= "Successfuly Downloaded").place(x= 100, y= 25, anchor= "center")
        
        def download_all():
            """Download all the files in the S3 bucket"""

            #initiablize info popup
            loading_win = tk.Toplevel(self.win)
            loading_win.geometry("350x50")
            loading_win.resizable(False, False)
            
            tk.Label(loading_win, text= "Backing up files").place(x= 175, y= 10, anchor= "center")
            info = tk.Label(loading_win, text="sample")
            info.place(x= 10, y = 20)
            
            #call the download to download the files in the appropriated download directory provided by the user
            self.download(loading_win, info, filedialog.askdirectory(initialdir= os.path.join(os.path.expanduser('~'), 'Downloads')))

        
        #set up the tree view to show the user all the uploaded/backed files
        tree = ttk.Treeview(self.win, height= 15)
        tree.place(x= 20, y= 50)
        tree.heading("#0", text= "Files")
        tree.column("#0", width= 490, stretch= tk.NO)

        self.total_objs = 0
        for obj in self.bucket.objects.all():
            self.total_objs += 1
            tree.insert("", tk.END, text= obj.key)
        
        ttk.Button(self.win, text= "Delete", command= delete, width= 12).place(x= 515, y= 80)
        ttk.Button(self.win, text= "Download", command= download_one, width= 12).place(x= 515, y= 110)
        ttk.Button(self.win, text= "Download All", command= download_all, width= 12).place(x= 515, y= 140)
    
    def settings(self):
        """Settings menu"""
        for child in self.win.winfo_children():
            child.destroy()
        #self.win.geometry("450x210")
        ttk.Button(self.win, text= "Back", command= self.access_panel).place(x= 0, y= 0)
        tk.Label(self.win, text= "Settings", font=('Helvetica bold', 20)).place(x= 225, y = 30, anchor= "center")

        new_name = tk.StringVar()
        new_name.set(self.bucket_name.get())
        tk.Label(self.win, text= "Bucket name: ", font= ('Helvetica bold', 12)).place(x= 100, y= 100, anchor = "center")
        tk.Entry(self.win, textvariable= new_name, font= ('Helvetica bold', 12)).place(x= 300, y= 100, anchor= "center")

        tk.Label(self.win, text= "Backup Interval(days): ", font= ('Helvetica bold', 12)).place(x= 100, y= 130, anchor = "center")
        tk.Entry(self.win, textvariable= self.days, font= ('Helvetica bold', 12)).place(x= 300, y= 130, anchor= "center")

        ttk.Button(self.win, text= "Submit", command= lambda: self.connect_bucket(new_name)).place(x= 200, y= 180, anchor= "center")
    
    def tray_icon(self):
        def quitnow():
            app.quit()
            self.timer.cancel()
            if self.ui_state == "running": self.win.destroy()
        
        app = QApplication(sys.argv)

        tray_icon = QSystemTrayIcon(QIcon(self.path_to_icon), parent= app)
        tray_icon.setToolTip("FBS3")
        tray_icon.show()

        menu = QMenu()

        callmain = menu.addAction("Open")
        callmain.triggered.connect(self.buildUI)

        exitAction = menu.addAction("Exit")
        exitAction.triggered.connect(quitnow)

        tray_icon.setContextMenu(menu)

        sys.exit(app.exec_())

a = FBS3(access_key= access_key, secret_key= secret_key)