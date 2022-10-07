import contextlib
from argparse import ArgumentError
from tkinter import ttk
import requests
import json
from pycli import CLI
import tkinter as tk
from tkinter import filedialog

# cli = CLI(prog="api.py", version="v1.0")

baseurl = "http://api.gofile.io/"

class APIExcpetion(BaseException):
    pass

# -=-=-=-= Helper Functions =-=-=-=-

def process_json(r):
    re = json.loads(r.content)
    if re["status"] != "ok":
        err = ""
        if re["status"] in ["error-auth", "error-noAuth"]:
            err = "There's something wrong with your authentification. Please try again."
        elif re["status"] == "error-wrongServer":
            err = "Please try again."
        else:
            err = "Status: {re['status']}"
        # print(r.headers)
        raise APIExcpetion(f"{err}\n{r}, {re}")
    return re["data"]

def getServer() -> str:
    """Get optimal upload server.

    Returns:
        str: Best server to use for uploads.
    """
    r = process_json(requests.get(url=f"{baseurl}getserver"))
    return r["server"]

def getContent(contentId, token):
    """Gets a piece of content from the GoFile server.

    Requires access to the full API.

    Args:
        contentId (str): The ID of the content being accessed.
        token (str): User's token

    Returns:
        dict: The contents of the file or folder accessed.
    """
    payload = {
        "token": token,
        "contentId": contentId
    }
    return process_json(requests.get(url=f"{baseurl}getcontent", params=payload))

def getAccountDetails(token: str, allDetails: bool = False):
    """Gets the details about an account.

    Args:
        token (str): User's token.
        allDetails (bool, optional): Verbose details. Defaults to False.

    Returns:
        dict: User's details.
    """
    payload = {
        "token": token
    }
    if allDetails:
        payload["allDetails"] = True
    
    return process_json(requests.get(url=f"{baseurl}getaccountdetails", params=payload))

def loopContents(contents, token, depth = "  "):
    for content in contents.values():
        print(f"{depth}{content['name']} - {content['type']}")
        if content["type"] == "folder":
            loopContents(getContent(content["id"], token)["contents"], token, f"{depth}  ")

# -=-=-=-= API Commands =-=-=-=-

# @cli.command
def uploadFile(filePath, token=None, folderId=None):
    """Uploads a file to the GoFile servers.

    Args:
        filePath (str): The path to the file being uploaded.
        token (str, optional): User's token. Defaults to a guest account.
        folderId (str, optional): ID of the folder being uploaded to. Defaults to the root folder.

    Raises:
        ArgumentError: Raised if a folderId is inputed without a token.

    Returns:
        str: Information about the file that was just uploaded.
    """
    payload = {}
    if token:
        payload["token"] = token
    if folderId:
        if not token:
            raise ArgumentError("If you input a folder ID, you need to input a token.")
        payload["folderId"] = folderId
    with open(filePath) as f:
        s = getServer()
        r = process_json(requests.post(url=f"https://{s}.gofile.io/uploadfile", params=payload, files={"file": f}))
        f.close()
        print(f"Successfully uploaded. Find your file at {r['downloadPage']}")
        return r

# @cli.command
def createFolder(folderID: str, folderName: str, token: str):
    """Create a folder.

    Args:
        folderID (str): ID of the parent folder to create the new folder in.
        folderName (str): Name of the new folder.
        token (str): User's token.
    """
    payload = {
        "token": token,
        "parentFolderId": folderID,
        "folderName": folderName
    }
    process_json(requests.put(url=f"{baseurl}createfolder", data=payload))

# @cli.command
def setFolderOption(token, folderId, option, value):
    """Set the options on a folder.

    Avaliable options:
        public
        password
        description
        expire
        tags

    Args:
        token (str): User's token.
        folderId (str): ID of the folder.
        option (str): The option to be changed.
        value (Any): The new value for the option.

    Raises:
        ArgumentError: Raised when an invalid option or value is given.
    """
    # validation code
    if option not in ["public", "password", "description", "expire", "tags"]:
        raise ArgumentError("Unrecognized option for \"option\" argument.")
    if option in ["password", "description"]:
        value = str(value)
    if option == "public" and value is not bool:
        raise ArgumentError("Invalid argument for \"public\" option.")
    if option == "expire" and value is not int:
        raise ArgumentError("Invalid argument for \"expire\" option.")
    if option == "tags" and value is not list:
        raise ArgumentError("Invalid argument for \"tags\" option.")
    payload = {
        "token": token,
        "folderId": folderId,
        "option": option,
        "value": value
    }
    process_json(requests.put(url=f"{baseurl}setfolderoption", data=payload))

# @cli.command
def copyContent(contentsId: list, folderIdDest, token):
    """Copy files or folders into another folder.

    Args:
        contentsId (list): List of content to copy.
        folderIdDest (str): Destination to copy the content to.
        token (str): User's token.
    """
    payload = {
        "token": token,
        "contentsId": ",".join(contentsId),
        "folderIdDest": folderIdDest
    }
    process_json(requests.put(url=f"{baseurl}copycontent", data=payload))

# @cli.command
def deleteContent(contentsId: list, token):
    """Deletes a file.

    Args:
        contentsId (list): List of contentIds.
        token (str): User's token.
    """
    payload = {
        "token": token,
        "contentsId": ",".join(contentsId)
    }
    process_json(requests.delete(url=f"{baseurl}deletecontent", data=payload))
    print("File deleted.")

# -=-=-=-= Custom commands =-=-=-=-

# @cli.command
def getContents(token, contentId = None, full: bool = False):
    """Gets the details of a folder or information about a file.

    Requires the full API.

    Args:
        token (str): User's token.
        contentId (str, optional): ContentId of the content being accessed. Defaults to user's root folder.

    Raises:
        ArgumentException: Raised when no token is input.
    """
    if not contentId:
        contentId = getAccountDetails(token)["rootFolder"]
    contents = getContent(contentId, token)
    print(f"[{contents['name']} - {contents['type']}]")
    if contents["type"] == "folder":
        if full:
            loopContents(contents["contents"], token)
        else:
            for content in contents["contents"].values():
                print(f"  {content['name']} - {content['type']}")

# cli.run()

# main window
window = tk.Tk()
window.title("GoFile")
window.rowconfigure(0, minsize=100, weight=1)
window.columnconfigure(1, minsize=100, weight=1)
window.configure(bg="#454D55")
window.geometry("400x400")

# lists
leftButtons = []
uploadScreen = []
filesScreen = []

# show upload screen
def openfile():
    f = filedialog.askopenfilename()
    print(f)

# show profile screen
def showProfile():
    pass

# left button area
buttonArea = tk.Frame(window, bg="#343A40")
buttonArea.grid(column=0, sticky="ns")

# upload file button
opnBtn = tk.Button(
    buttonArea, text="Upload Files",
    command=openfile
)
# opnBtn.grid(row=0, sticky="nwe", pady=2, padx=5)
leftButtons.append(opnBtn)

# profile button
out = tk.PhotoImage(file="img/id-card.png").subsample(23, 23)
prfBtn = tk.Button(
    buttonArea, text="My Profile",
    command=showProfile, image=out
)
leftButtons.append(prfBtn)

# configure all buttons
for btn in leftButtons:
    btn["width"] = 12
    btn["relief"] = tk.FLAT
    btn["compound"] = tk.LEFT
    btn["bg"] = "#343A40"
    btn["fg"] = "white"
    btn["activebackground"] = "#494E54"
    btn["activeforeground"] = "white"
    btn["highlightbackground"] = "#343A40"
    btn["highlightcolor"] = "#343A40"

for i in range(len(leftButtons)):
    # pass
    leftButtons[i].grid(row=i, sticky="nwe", pady=2, padx=5)

# files screen - WIP - needs to be generated on the fly
contentFrame = tk.Frame(window, bg="#343A40")
contentFrame.grid(row=0, column=1, padx=5, pady=5, sticky="nwe")
flair = tk.Canvas(contentFrame, bg="#3F6791", highlightbackground="#3F6791")
flair.configure(width=contentFrame["width"], height=1)
flair.pack(fill="x")
text = tk.Label(contentFrame, text="Gaming", bg=contentFrame["background"], fg="white", anchor="center")
text.pack(fill="x", padx=5, pady=5)

window.mainloop()

# [== notes ==]

# -- file dialogs --
# -- file open (get filepath) --
# filedialog.askopenfilename()

# -- file save (get folder) --
# filedialog.askdirectory()

# -- downloading files --
# r = requests.get(url=url)
# with open(<path>) as f:
#     f.write(r.content)

# -- learning tk --

# greeting = tk.Label(
#     text="Hello, World!",
#     foreground="red")
# greeting.pack()

# button = tk.Button(
#     text="Click me",
#     background="red",
#     foreground="white",
#     width=20,
#     height=5
# )
# button.pack()

# entry = tk.Entry(width=69)
# entry.pack()

# text = tk.Text()
# text.pack()

# window.columnconfigure(0, weight=2, minsize=69)
# window.columnconfigure(2, weight=1, minsize=5)

# label1 = tk.Label(text="why hello there", width=10, height=3, bg="yellow", master=window)
# label2 = tk.Label(text="wack", width=10, height=3, bg="blue", master=window)
# label3 = tk.Label(text="oml so silly", width=15, height=4, bg="red", master=window)
# label1.grid(column=0)
# label2.grid(column=1)
# label3.grid(column=2)

# die rolling:
# def roll():
#     import random
#     dieNum["text"] = random.randint(1, 6)

# dieNum = tk.Label(text="0", width=9, height=3)
# dieNum.pack()

# button = tk.Button(text="Roll", width=9, height=3, command=roll)
# button.pack()

# -- tk unpacking --
# text.pack() -- pack
# text.pack_forget() -- hide
# text.destroy() -- delete
# works with .grid() too