#!.venv/bin/python3

import contextlib
from argparse import ArgumentError
import requests
import json
from pycli import CLI

cli = CLI(prog="api.py", version="v1.0")

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

@cli.command
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

@cli.command
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

@cli.command
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

@cli.command
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

@cli.command
def deleteContent(contentsId: list, token):
    """Deletes a file.

    Args:
        contentsId (list): List of contentIds.
        token (str): User's token.
    """
    payload = {
        "contentsId": ",".join(contentsId)
    }
    print(",".join(contentsId))
    process_json(requests.delete(url=f"{baseurl}deletecontent", data=payload, params={"token": token}))
    print("File deleted.")

# -=-=-=-= Custom commands =-=-=-=-

@cli.command
def getContents(token, contentId = None):
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
        loopContents(contents["contents"], token)

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