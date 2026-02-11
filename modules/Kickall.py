import random
import threading
import time
import json
import re
from zlapi import *
from zlapi.models import *
from config import ADMIN

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Kick All",
    'power': "Admin"
}

def kickall(message, message_object, thread_id, thread_type, author_id, bot):
    if author_id not in ADMIN:
        return
        
    group = bot.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
    
    admin_ids = group.adminIds.copy()
    if group.creatorId not in admin_ids:
        admin_ids.append(group.creatorId)
    
    list_mem_group = set([member.split('_')[0] for member in group["memVerList"]])

    list_mem_group_to_kick = list_mem_group - set(admin_ids)

    for uid in list_mem_group_to_kick:
        bot.blockUsersInGroup(uid, thread_id)
        bot.kickUsersInGroup(uid, thread_id)
        
def TQD():
    return {
        'kickall': kickall
    }