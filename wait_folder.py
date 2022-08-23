# todo: 
# write what happens if folder is added or removed
# test with test folder 
# test with sleep(5 sec)
#


from config import *
import os.path
import time
import logging   

logging.basicConfig(filename='std.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s')



old_list = os.listdir(SYNC_FOLDER)


# wait until folder is created
while True: 
    logging.info('Fetching folder')
    new_list = os.listdir(SYNC_FOLDER) # fetch         #code here
    time.sleep(1)


    if len(new_list) > len(old_list): # new folder added

        # code here
        
        old_list = new_list()
    elif len(new_list) < len(old_list): # folder deleted
        # code here
        
        old_list = new_list()


    else:
        pass




    