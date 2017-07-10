# coding: utf-8
'''
Created on 27 June 2017.

@author: Sanin
'''
from datetime import datetime

def printl(*args, **kwargs):
    # static variables
    if not hasattr(printl, "start"):
        printl.start = True  # it doesn't exist yet, so initialize it
    if not hasattr(printl, "folderName"):
        printl.folderName = 'logfile.log'
    
    if "folderName" in kwargs:
        printl.folderName = kwargs["folderName"]

    if "stamp" in kwargs:
        stamp = kwargs["stamp"]
    else:
        stamp = True
    
    now = datetime.now()    
    strnow = datetime.strftime(now, "%Y.%m.%d %H:%M:%S")
    
    f = open(printl.folderName, 'a')

    if printl.start:
        f.write('\nLog started at %s\n'%strnow)
        printl.start = False
    
    strout = ''
            
    for a in args :
        strout += " "
        strout += str(a)

    print(strout)

    if stamp :
        strout = strnow + ' ' + strout

    f.write(strout+'\n')
    f.close()
