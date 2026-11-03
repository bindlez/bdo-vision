"""Event-only reminder decisions. A missing/hidden card never proves absence."""
import re


def explicit_absence(text):
    for line in str(text)[:6000].splitlines():
        if re.fullmatch(r'\s*(?:There (?:is|are) no (?:active )?guild missions?(?: currently)? in progress|No guild mission is currently in progress|No active guild mission)[.!]?\s*',line,re.I):
            return line.strip()[:200]
    return None


def reminder_decision(quest,activity,now,*,enabled=True,crafting=False):
    if not enabled or not crafting or activity not in ('alchemy','cooking'):return None
    stamp=quest.get('last_at');fresh=quest.get('available') and isinstance(stamp,(float,int)) and 0<=now-stamp<=35
    absent=quest.get('absence_observed') and quest.get('absence_votes')==2 and isinstance(quest.get('absence_at'),(float,int)) and 0<=now-quest['absence_at']<=35
    if absent:return {'key':'absent','sound':True,'message':'No active guild quest confirmed. Accept a '+activity+' guild quest in BDO.'}
    if quest.get('complete') and quest.get('available'):
        return {'key':'complete','sound':True,'message':'Guild quest complete. Claim it and accept the next '+activity+' quest in BDO.'}
    identity=(str(quest.get('label',''))+' '+str(quest.get('objective',''))).casefold()
    matching=activity in identity or activity=='alchemy' and re.search(r'a[li]chem[yv]',identity)
    if fresh and quest.get('current') is not None and matching:return None
    if fresh and quest.get('current') is not None:
        return {'key':'different','sound':False,'message':'A different guild quest was read. Check for an active '+activity+' guild quest.'}
    return {'key':'unverified','sound':False,'message':'Guild quest not verified for this craft. Show the matching mission and use SCAN TOOL + QUEST. A hidden card does not mean no quest is active.'}


class ReminderGate:
    def __init__(self):self.last=None;self.snoozed_until=0
    def accept(self,decision,session,now):
        if decision is None:self.last=None;return None
        key=(session,decision['key'])
        if now<self.snoozed_until or key==self.last:return None
        self.last=key;return decision
    def snooze(self,now,seconds=600):self.snoozed_until=now+seconds
