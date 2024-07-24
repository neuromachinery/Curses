import os
from os import listdir,path,remove,walk
from sys import argv
from datetime import datetime
import zipfile
import subprocess
CWD = path.dirname(argv[0])
SharedDirectory = "Shared"
Buffer = path.join(CWD,"buffer")
MARKNAME = "mark.mark"
def now():
    return datetime.now().strftime("[%d.%m.%Y@%H:%M:%S]")
def fileList(directory) -> list[str]:
    try:return [thing for thing in listdir(directory) if path.isfile(path.join(directory,thing))]
    except FileNotFoundError:return []
    except Exception as E:
        print(str(E))
        return []
def dirList(directory) -> list[str]:
    try:return [thing for thing in listdir(directory) if not path.isfile(path.join(directory,thing))]
    except FileNotFoundError:return []
    except Exception as E:
        print(str(E))
        return []
def directoryMarking(directory:str,add:bool=True) -> bool:
    try:
        filename = path.join(directory,MARKNAME)
        if not add:
            remove(filename)
            return True
        with open(filename,"w") as file:
            file.write(str(now()))
    except FileNotFoundError:
        return False
    except Exception as E:
        print(str(E))
        return False
    else:
        return True

def filePack(directory:str, size:int) -> list[str]:
    """
    Args:
        directory (str): The path to the directory to compress.
        volume_size (int): The size of each volume in bytes.
    """
    output_zip = os.path.join(Buffer, os.path.basename(directory) + '.zip')
    command = [
        '7z', 'a',
        "-aoa",
        f'-v{size}',
        output_zip,
        directory
    ]
    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,cwd=path.join(CWD,SharedDirectory))
        files = [path.abspath(path.join(Buffer,file)) for file in fileList(Buffer)]
        return files
    except subprocess.CalledProcessError as e:
        return f"Error occurred: {e.stderr.decode()}"
if __name__ == "__main__":
    print("no")