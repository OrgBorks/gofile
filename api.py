#!.venv/bin/python3

from argparse import ArgumentError
import requests
import json
from pycli import CLI
from py_dotenv import read_dotenv
import os

read_dotenv(".env")

cli = CLI(prog="api.py", version="v1.0")

baseurl = "https://api.gofile.io/"

class APIExcpetion(BaseException):
    pass

# -=-=-=-= Helper Functions =-=-=-=-

def process_json(r):
    re = json.loads(r.content)
    if re["status"] != "ok":
        err = ""
        if re["status"] in ["error-auth", "error-noAuth"]:
            err = "You do not have access to the full API."
        elif re["status"] == "error-wrongServer":
            err = "Please try again."
        else:
            err = "Status: {re['status']}"
        raise APIExcpetion(f"{err}\n{r}, {re}")
    return re["data"]

def getContent(contentId, token):
    payload = {
        "contentId": contentId,
        "token": token
    }
    return process_json(requests.get(url=f"{baseurl}getcontent", data=payload))

def getServer() -> str:
    """Get optimal upload server.

    Returns:
        str: Best server to use for uploads.
    """
    r = process_json(requests.get(url=f"{baseurl}getserver"))
    return r["server"]

def loopContents(contents, depth = "\t"):
    for content in contents:
        print(depth + content["name"])
        if content["type"] == "folder":
            loopContents(content["contents"], depth+"\t")

# -=-=-=-= CLI Commands =-=-=-=-

@cli.command
def uploadFile(filePath, token=None, folderId=None, ):
    payload = {}
    if token:
        payload["token"] = token
    if folderId:
        if not token:
            raise ArgumentError("If you input a folder ID, you need to input a token.")
        payload["folderId"] = folderId
    with open(filePath) as f:
        s = getServer()
        r = process_json(requests.post(url=f"https://{s}.gofile.io/uploadfile", data=payload, files={"file": f}))
        f.close()
        print(f"Successfully uploaded. Find your file at {r['downloadPage']}")
        return r

@cli.command
def createFolder(folderID, folderName, token):
    payload = {
        "parentFolderId": folderID,
        "folderName": folderName,
        "token": token
    }
    process_json(requests.put(url=f"{baseurl}createfolder", data=payload))

@cli.command
def setFolderOption(token, folderId, option, value):
    # validation code
    if option not in ["public", "password", "description", "expire", "tags"]:
        raise ArgumentError("Unrecognized option for \"option\" argument.")
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

@cli.command
def copyContent(contentsId: list, folderIdDest, token):
    payload = {
        "contentsId": ",".join(contentsId),
        "folderIdDest": folderIdDest,
        "token": token
    }
    process_json(requests.put(url=f"{baseurl}copycontent", data=payload))

@cli.command
def deleteContent(contentsId: list, token):
    payload = {
        "contentsId": ",".join(contentsId),
        "token": token
    }
    process_json(requests.delete(url=f"{baseurl}deletecontent", data=payload))

@cli.command
def getAccountDetails(token: str, allDetails: bool = False):
    payload = {
        "token": token
    }
    if allDetails:
        payload["allDetails"] = True
    
    return process_json(requests.get(url=f"{baseurl}getaccountdetails", data=payload))

# -=-=-=-= Custom commands =-=-=-=-

@cli.command
def getContents(token = None, contentId = None):
    if not token:
        token = os.environ.get("token")
    if not token:
        raise ArgumentException("Please input a token or put your token into a .env file.")
    if not contentId:
        contentId = getAccountDetails(token)["rootFolder"]
    contents = getContent(contentId, token)
    print(f"[{contents['name']}]")
    loopContents(contents["contents"])

cli.run()

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